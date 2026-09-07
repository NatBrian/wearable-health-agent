"""Wording the question, sending it, and parking the graph on the answer."""

import json
import logging
from typing import Any

from langgraph.types import interrupt

from wha.agent.nodes.schemas import QuestionDraftResponse
from wha.agent.state import EpisodeState
from wha.clock import local_today
from wha.errors import LLMUnavailable, ValidationFailed
from wha.llm.client import LLMClient, get_llm_client
from wha.llm.prompts import get_prompt_definition
from wha.models import (
    Action,
    ActionKind,
    Answer,
    Disposition,
    Question,
)
from wha.notify.protocol import MessageKind
from wha.safety.tier_c import check_red_flags_with_tier_c

logger = logging.getLogger(__name__)


def node_ask(
    state: EpisodeState,
    llm_client: LLMClient | None = None,
    notifier: Any = None,
    db: Any = None,
) -> dict[str, Any]:
    """Ask node with strict interrupt discipline and idempotent pre-interrupt execution."""
    action = state.get("action")
    if action is None or action.question is None:
        return {"step": state.get("step", 0) + 1}

    question = action.question
    probe_id = question.probe.probe_id
    episode_id = state.get("episode_id", "ep_default")
    # A follow-up gets its own id per night. Without the date it would collide with the
    # question it is following up, because the id is built from the episode and the probe,
    # and upsert_interaction would UPDATE that row rather than insert a new one. The
    # previous question would be silently overwritten, the per-episode follow-up cap would
    # count one forever and never trip, and an uncapped follow-up is a nightly alarm.
    #
    # Keying on the night also gives idempotency for free: re-running a night re-asks
    # nothing.
    if action.followup_for:
        interaction_id = f"int_{episode_id}_{probe_id}_{local_today().isoformat()}"
    else:
        interaction_id = f"int_{episode_id}_{probe_id}"

    # 1. Prepare Question Text (with fallback if LLM is unavailable)
    question_text = question.text
    text_source = question.text_source

    if text_source == "llm":
        client = llm_client or get_llm_client()
        try:
            draft_def = get_prompt_definition("write_question")
            draft_prompt = draft_def.render(
                {
                    "probe_id": probe_id,
                    "target_cause": question.probe.target_cause.value,
                    "fallback_text": question.probe.fallback_text,
                    "options": json.dumps([o.model_dump() for o in question.options], default=str),
                }
            )
            draft_res, _ = client.complete(
                draft_prompt,
                schema=QuestionDraftResponse,
                temperature=draft_def.temperature,
            )
            question_text = draft_res.text
        except (LLMUnavailable, ValidationFailed, KeyError, TypeError, ValueError, StopIteration):
            question_text = question.probe.fallback_text
            text_source = "fallback"

    updated_question = Question(
        probe=question.probe,
        text=question_text,
        text_source=text_source,
        options=question.options,
        allows_free_text=question.allows_free_text,
    )

    # 2. Idempotent write / upsert of interaction
    if db is not None and hasattr(db, "upsert_interaction"):
        db.upsert_interaction(
            interaction_id=interaction_id,
            episode_id=episode_id,
            subject_id=state.get("subject_id"),
            probe_id=probe_id,
            question_text=updated_question.text,
            # The answer space and the transport were both dropped on the floor here, so
            # the stored row said a question with no options had been asked over no
            # channel. The dashboard renders the answer choices from this row, and the
            # audit trail is meant to show what the person was actually offered.
            options=[opt.model_dump() for opt in updated_question.options],
            channel=getattr(notifier, "channel", "none"),
            # Every question was stored with evsi 0.0, interruption_cost 0.0 and no
            # rejected list, so the row could not evidence the one claim the system makes:
            # that this interruption was worth more than it cost, and which alternatives
            # it beat. All three are on the action the policy already chose.
            evsi=question.probe.evsi,
            interruption_cost=question.probe.interruption_cost,
            rejected=list(action.rejected),
            # Marks a question asked BY RULE rather than by expected information gain, so
            # the per-episode cap on follow-ups has something to count. Its evsi is stored
            # unchanged and is usually near zero, which is the honest record: this question
            # was not worth asking by the arithmetic, and was asked anyway, on purpose.
            initiation="followup" if action.followup_for else "unsolicited",
            # Whether the model wrote this sentence or the canned one was used. The
            # column defaults to "fallback" and nothing ever passed anything, so every
            # question in the record claimed the canned wording had been used, including
            # the ones the model wrote. That is the single field the audit trail uses to
            # show which words came from where.
            text_source=updated_question.text_source,
        )

    # 3. Idempotent send notification: check if already sent
    already_sent = False
    if db is not None:
        if hasattr(db, "has_notification_for"):
            already_sent = db.has_notification_for(interaction_id)
        elif hasattr(db, "get_notifications_for_interaction"):
            already_sent = bool(db.get_notifications_for_interaction(interaction_id))

    if not already_sent and notifier is not None:
        # Record delivery only if the transport reported success. Recording it
        # unconditionally marked questions as delivered that were never sent, leaving the
        # episode parked forever on an answer the person was never asked for.
        delivered = notifier.send(
            recipient_id=state.get("subject_id"),
            kind=MessageKind.QUESTION,
            text=updated_question.text,
            interaction_id=interaction_id,
            probe_id=probe_id,
            options=updated_question.options,
        )
        if delivered and db is not None and hasattr(db, "record_notification"):
            # The channel was left at its default, so the record said a question had been
            # delivered over "none" while the interaction row said telegram.
            db.record_notification(
                interaction_id=interaction_id,
                recipient=state.get("subject_id"),
                channel=getattr(notifier, "channel", "none"),
                episode_id=episode_id,
            )
            # And in the audit chain, under the `notify` operation the contract reserves
            # and nothing had ever written. The notifications table knew; the page that
            # claims everything is written down reads the chain.
            if hasattr(db, "record_notification_sent"):
                db.record_notification_sent(
                    subject_id=state.get("subject_id", ""),
                    episode_id=episode_id,
                    kind="QUESTION",
                    channel=getattr(notifier, "channel", "none"),
                    text=updated_question.text,
                )

    # Park the episode where the interface can see it. `get_pending_interaction` only
    # surfaces a question for an episode in AWAITING_USER, and nothing ever set that state,
    # so a question the agent had asked never appeared in the dashboard at all and could
    # only be answered over Telegram.
    if db is not None and hasattr(db, "set_episode_state"):
        db.set_episode_state(episode_id, "AWAITING_USER")

    # 4. Interrupt for human response
    raw_response = interrupt(
        {
            "kind": "question",
            "interaction_id": interaction_id,
            "probe_id": probe_id,
            "text": updated_question.text,
            "options": [opt.model_dump() for opt in updated_question.options],
        }
    )

    # 5. Post-interrupt resumption logic
    if isinstance(raw_response, Answer):
        answer = raw_response
    elif isinstance(raw_response, dict):
        if raw_response.get("timed_out") or raw_response.get("status") == "timed_out":
            # Timeout answer
            answer = Answer(
                probe_id=probe_id,
                option_id=None,
                free_text=None,
                declined=True,
            )
        else:
            answer = Answer(
                probe_id=raw_response.get("probe_id", probe_id),
                option_id=raw_response.get("option_id"),
                free_text=raw_response.get("free_text"),
                declined=raw_response.get("declined", False),
            )
    else:
        answer = Answer(
            probe_id=probe_id,
            option_id=None,
            free_text=str(raw_response),
            declined=False,
        )

    # 6. Deterministic safety floor over the person's own words.
    #
    # Free text was collected and never checked. A person answering "feels like an
    # elephant is sitting on my chest" had that stored as evidence and passed to the
    # belief model, when the contract requires it to escalate on the RULES and never
    # reach the belief or policy nodes at all.
    if answer.free_text:
        # With the person's symptom history, not just tonight's sentence.
        #
        # The history argument existed on this call from the beginning and nothing ever
        # passed it, so the persistence half of Tier B never fired for anybody. The
        # fallback below is the OLD behaviour and is deliberately narrow: with no
        # connection there is no history to have, which is a different thing from
        # choosing to ignore one. It is logged so it cannot become the quiet default.
        from wha.service.symptoms import observe_and_check

        conn = getattr(db, "conn", None)
        subject_id = state.get("subject_id", "")
        if conn is not None and subject_id:
            safety = observe_and_check(conn, subject_id, answer.free_text)
        else:
            logger.warning(
                "Safety floor ran on episode %s with no symptom history: db=%s subject=%r",
                episode_id,
                type(db).__name__,
                subject_id,
            )
            safety = check_red_flags_with_tier_c(user_text=answer.free_text)
        if safety.escalate:
            return {
                "answers": [answer],
                "action": Action(
                    kind=ActionKind.ESCALATE,
                    disposition=Disposition.ESCALATED,
                    rationale=(
                        f"Deterministic safety floor triggered on the answer text: "
                        f"{', '.join(safety.triggered_flags)}"
                    ),
                    rejected=[],
                ),
                "safety_event": "red_flag_escalation",
                "escalation_level": safety.level,
                "triggered_flags": list(safety.triggered_flags),
                "step": state.get("step", 0) + 1,
            }

    return {
        "answers": [answer],
        "step": state.get("step", 0) + 1,
    }
