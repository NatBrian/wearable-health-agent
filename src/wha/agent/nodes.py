"""Graph execution nodes for preloading, investigation, belief, decision, asking, measuring, and outcome lifecycle."""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Literal

from langgraph.types import interrupt
from pydantic import BaseModel, Field

from wha.agent.differential import ground_differential
from wha.agent.state import EpisodeState
from wha.agent.tools.impl import create_default_tool_registry
from wha.agent.tools.registry import ToolContext, ToolRegistry, describe_tools
from wha.belief import update_belief
from wha.clock import local_today
from wha.constants import MAX_TOOL_CALLS_PER_EPISODE
from wha.errors import LLMUnavailable, PermissionDenied, ValidationFailed
from wha.llm.client import LLMClient, get_llm_client
from wha.llm.prompts import get_prompt_definition
from wha.models import (
    Action,
    ActionKind,
    Answer,
    BaselineRung,
    Citation,
    Disposition,
    EpisodeContext,
    EpisodeOutcome,
    ExtractedFact,
    Question,
)
from wha.notify.protocol import MessageKind
from wha.policy import determine_disposition
from wha.policy.select import select_action
from wha.retrieve.grounding import enforce_grounding
from wha.retrieve.models import Citation as RetrievedPassage
from wha.retrieve.models import GeneratedClaim
from wha.safety.output_checks import (
    DIAGNOSIS_PHRASES,
    FALSE_REASSURANCE_PHRASES,
    select_escalation_criteria,
    validate_and_sanitize_outcome,
)
from wha.safety.tier_c import check_red_flags_with_tier_c

logger = logging.getLogger(__name__)


class ToolCallArgs(BaseModel):
    """Tool invocation payload from model."""

    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)
    called_at_utc: datetime | None = None


class DoneSignal(BaseModel):
    """Completion signal with rationale."""

    reason: str


class InvestigateStep(BaseModel):
    """Single turn of the investigation loop."""

    tool_call: ToolCallArgs | None = None
    done: DoneSignal | None = None


class FactExtractionResponse(BaseModel):
    """Typed structured facts extracted by LLM from investigation artifacts."""

    facts: list[ExtractedFact] = Field(default_factory=list)


class VetoCheckResponse(BaseModel):
    """Unidirectional redundant question veto decision from model."""

    veto: bool = False
    reason: str = ""
    suggested_alternative: str | None = None


class QuestionDraftResponse(BaseModel):
    """Drafted question text and option labels from LLM."""

    text: str
    option_labels: list[str] = Field(default_factory=list)
    rationale: str | None = None


class OutcomeClaim(BaseModel):
    """One clinical assertion, with the passage span the model says supports it.

    ``claims`` was a bare ``list[str]``, so there was nothing to check a claim against and
    the claim-to-source enforcement in ``docs/CONTRACTS.md`` section 11.3 could not run
    even in principle. The span is what makes the check a deterministic containment test
    rather than a second opinion.
    """

    text: str
    evidence_span: str = ""


class WriteOutcomeResponse(BaseModel):
    """Synthesized outcome prose from the model.

    `escalation_criteria` was here and has been removed. It was the when-to-seek-care
    text, the sentence a person is most likely to act on, and the only field in the
    system that went through no check at all. A live run produced "Seek care if fever
    persists beyond 72 hours or exceeds 103 degrees F (39.4 C)", invented. It is now
    selected from `red_flags.yaml` by `select_escalation_criteria`, so there is nothing
    left to guard.
    """

    observation: str
    claims: list[OutcomeClaim] = Field(default_factory=list)
    action_text: str = ""


class CritiqueResponse(BaseModel):
    """Subtractive output critique response from LLM."""

    approved: bool = True
    stripped_claims: list[str] = Field(default_factory=list)
    modified_text: str = ""
    critique_notes: str = ""


def node_preload(
    state: EpisodeState,
    db: Any = None,
    registry: ToolRegistry | None = None,
) -> dict[str, Any]:
    """Deterministically populate cheap T1 reads into state['preloaded']."""
    subject_id = state.get("subject_id", "default_subject")
    nights = state.get("nights", [])
    if nights:
        dates = [d.night_date for d in nights]
        start_d = min(dates) - timedelta(days=7)
        end_d = max(dates)
    else:
        end_d = local_today()
        start_d = end_d - timedelta(days=14)

    start_str = start_d.isoformat()
    end_str = end_d.isoformat()

    context = ToolContext(
        subject_id=subject_id,
        episode_id=state.get("episode_id"),
        step_index=state.get("step", 0),
    )

    reg = registry or create_default_tool_registry()
    preloaded: dict[str, Any] = {}

    # 1. get_nightly_features
    res_feat = reg.invoke(
        "get_nightly_features",
        {"start": start_str, "end": end_str},
        context,
        db=db,
    )
    preloaded["nightly_features"] = res_feat.value

    # 2. get_personal_baseline
    res_base = reg.invoke(
        "get_personal_baseline",
        {"night_date": end_str},
        context,
        db=db,
    )
    preloaded["personal_baseline"] = res_base.value

    # 3. get_known_events
    res_events = reg.invoke(
        "get_known_events",
        {"start": start_str, "end": end_str},
        context,
        db=db,
    )
    preloaded["known_events"] = res_events.value

    # 4. get_data_quality
    res_qual = reg.invoke(
        "get_data_quality",
        {"start": start_str, "end": end_str},
        context,
        db=db,
    )
    preloaded["data_quality"] = res_qual.value

    # 5. find_similar_past_episodes
    res_hist = reg.invoke("find_similar_past_episodes", {}, context, db=db)
    preloaded["similar_past_episodes"] = res_hist.value

    return {
        "preloaded": preloaded,
        "step": state.get("step", 0) + 1,
    }


# Character budgets for the investigate prompt. PromptDefinition.render raises rather
# than truncating once the whole prompt passes PROMPT_MAX_CHARS, and an LLMUnavailable
# there parks the episode. The loop now re-renders on every turn and re-enters after every
# answer, so the two growing fields are bounded here instead.
_INVESTIGATE_HISTORY_CHARS = 3000
_INVESTIGATE_CALLS_CHARS = 4000
_INVESTIGATE_CALL_VALUE_CHARS = 400


def _compact_json(value: Any, limit: int) -> str:
    """Serialise to JSON, cut to ``limit`` characters, and say so when cut."""
    text = json.dumps(value, default=str)
    if len(text) <= limit:
        return text
    return f"{text[:limit]} ...[truncated, {len(text)} chars total]"


def _summarise_tool_calls(calls: list[dict[str, Any]]) -> str:
    """One line per call: what was asked, whether it worked, and a clipped result.

    The model needs to know what it has already tried so it does not repeat itself. It
    does not need every nightly feature row it has already been handed; those are in
    ``preloaded`` and in the extracted facts.
    """
    if not calls:
        return "[]"

    lines: list[str] = []
    for call in calls:
        name = call.get("tool_name", "unknown")
        args = json.dumps(call.get("args", {}), default=str)
        ok = call.get("ok", True)
        if not ok:
            detail = call.get("error") or call.get("note") or "failed"
        else:
            detail = _compact_json(call.get("value"), _INVESTIGATE_CALL_VALUE_CHARS)
        lines.append(f"- {name}({args}) -> {'ok' if ok else 'REFUSED'}: {detail}")

    # Newest calls matter most, so trim from the front when the budget bites.
    text = "\n".join(lines)
    while len(text) > _INVESTIGATE_CALLS_CHARS and len(lines) > 1:
        lines.pop(0)
        text = f"[{len(calls) - len(lines)} earlier calls omitted]\n" + "\n".join(lines)
    return text


def _summarise_answers(answers: list[Answer]) -> str:
    """What the person has actually said, which is what re-investigation is for."""
    if not answers:
        return "None yet. The person has not been asked anything in this episode."

    lines: list[str] = []
    for answer in answers:
        if answer.declined:
            lines.append(f"- {answer.probe_id}: declined to answer")
            continue
        parts = [p for p in (answer.option_id, answer.free_text) if p]
        lines.append(f"- {answer.probe_id}: {' / '.join(parts) if parts else 'no content'}")
    return "\n".join(lines)


def node_investigate(
    state: EpisodeState,
    llm_client: LLMClient | None = None,
    registry: ToolRegistry | None = None,
    db: Any = None,
) -> dict[str, Any]:
    """LLM-driven investigation loop over closed T1 tools returning typed ExtractedFacts."""
    client = llm_client or get_llm_client()
    reg = registry or create_default_tool_registry()
    subject_id = state.get("subject_id", "default_subject")
    episode_id = state.get("episode_id", "ep_default")
    current_calls = list(state.get("tool_calls", []))
    call_count = state.get("tool_call_count", len(current_calls))

    context = ToolContext(
        subject_id=subject_id,
        episode_id=episode_id,
        step_index=state.get("step", 0),
        tool_call_count=call_count,
    )

    prompt_def = get_prompt_definition("investigate")
    tool_catalogue = describe_tools(reg.list_tools())
    history_summary = _compact_json(state.get("preloaded", {}), _INVESTIGATE_HISTORY_CHARS)
    answers_so_far = _summarise_answers(state.get("answers", []))

    while True:
        if context.tool_call_count >= MAX_TOOL_CALLS_PER_EPISODE:
            break

        # Rendered inside the loop, not once before it. The model was asked the same
        # question after every call, with `previous_calls` frozen at whatever it held on
        # entry, so it could not see the result it had just obtained. At temperature 0
        # that means it asks for the same tool again, which is why one run recorded 101
        # calls to get_nightly_features. Summarised rather than dumped whole because
        # PromptDefinition.render refuses to truncate and raises past its character
        # budget, which would park the episode.
        prompt = prompt_def.render(
            {
                "tool_catalogue": tool_catalogue,
                "episode_id": episode_id,
                "history_summary": history_summary,
                "previous_calls": _summarise_tool_calls(current_calls),
                "answers_so_far": answers_so_far,
            }
        )

        try:
            step_res, _ = client.complete(
                prompt,
                schema=InvestigateStep,
                temperature=prompt_def.temperature,
            )
        except LLMUnavailable:
            # LLMUnavailable parks the episode: state checkpointed, no advancement, no closure!
            return {
                "status": "parked",
                "step": state.get("step", 0) + 1,
            }

        if step_res.tool_call is not None:
            tool_name = step_res.tool_call.tool_name
            tool_args = step_res.tool_call.args
            try:
                result = reg.invoke(tool_name, tool_args, context, db=db)
                current_calls.append(result.model_dump())
            except PermissionDenied as e:
                # Denial is recorded and logged
                current_calls.append(
                    {
                        "tool_name": tool_name,
                        "args": tool_args,
                        "ok": False,
                        "error": str(e),
                        "permission_decision": "denied",
                    }
                )

        if step_res.done is not None or step_res.tool_call is None:
            break

    # Structured extraction of typed facts (untrusted text has nowhere to go).
    #
    # Only over calls made on this pass. `evidence` concatenates across nodes, so
    # re-extracting from the whole history on every re-entry would add a second copy of
    # every fact already gathered, and the differential would then count one observation
    # as several. When nothing new was gathered there is nothing to extract.
    new_calls = current_calls[len(state.get("tool_calls", [])) :]
    facts: list[ExtractedFact] = []
    if new_calls:
        try:
            fact_def = get_prompt_definition("extract_facts")
            fact_prompt = fact_def.render(
                {
                    "user_response": _compact_json(new_calls, _INVESTIGATE_CALLS_CHARS),
                    "relevant_probes": "[]",
                }
            )
            fact_res, _ = client.complete(
                fact_prompt,
                schema=FactExtractionResponse,
                temperature=fact_def.temperature,
            )
            if isinstance(fact_res, FactExtractionResponse) or hasattr(fact_res, "facts"):
                facts.extend(fact_res.facts)
        except (
            LLMUnavailable,
            ValidationFailed,
            KeyError,
            TypeError,
            ValueError,
            AttributeError,
            StopIteration,
        ):
            facts = []

    return {
        # Only the new calls. `tool_calls` reduces by concatenation, so returning the
        # accumulated list appends a second copy of everything already in state. Harmless
        # while investigate ran exactly once per episode; with the ask -> investigate edge
        # it would double the record the audit trail is built from on every re-entry.
        "tool_calls": new_calls,
        "tool_call_count": context.tool_call_count,
        "evidence": facts,
        "step": state.get("step", 0) + 1,
    }


def node_believe(
    state: EpisodeState,
    db: Any = None,
) -> dict[str, Any]:
    """Deterministically recompute belief distribution across 4096 states."""
    nights = state.get("nights", [])
    features = state.get("features", [])
    answers = state.get("answers", [])
    measurements = state.get("measurements", [])

    belief = update_belief(
        episode_nights=nights,
        features=features,
        answers=answers,
        measurements=measurements,
        context=_episode_context(state, db, answers),
    )

    if db is not None:
        if hasattr(db, "append_belief"):
            db.append_belief(
                episode_id=state.get("episode_id"),
                subject_id=state.get("subject_id"),
                belief=belief,
                trigger="node_believe",
            )
        elif hasattr(db, "insert_belief"):
            db.insert_belief(
                episode_id=state.get("episode_id"),
                subject_id=state.get("subject_id"),
                belief=belief,
            )

    return {
        "belief": belief,
        "step": state.get("step", 0) + 1,
    }


def node_decide(
    state: EpisodeState,
    llm_client: LLMClient | None = None,
    db: Any = None,
) -> dict[str, Any]:
    """Deterministically select action via EVSI policy, with unidirectional LLM veto on ask actions."""
    belief = state.get("belief")
    if belief is None:
        belief = update_belief(
            episode_nights=state.get("nights", []),
            features=state.get("features", []),
            answers=state.get("answers", []),
            measurements=state.get("measurements", []),
            context=_episode_context(state, db, state.get("answers", [])),
        )

    depth_used = state.get("depth_used", 0)
    step = state.get("step", 0)
    nights = state.get("nights", [])
    subject_id = state.get("subject_id", "")
    episode_id = state.get("episode_id", "")
    answers = state.get("answers", [])

    # These were previously left to their permissive defaults, which disabled the weekly
    # interruption budget, bypassed cold-start rung gating, and allowed the same probe to
    # be asked repeatedly. They are policy inputs, not optional decoration.
    weekly_used = 0
    pending = False
    rung = BaselineRung.MATURE
    asked_probe_ids = [a.probe_id for a in answers]
    answered_ever: list[str] = []

    if db is not None:
        today = local_today()
        if hasattr(db, "count_interruptions_since"):
            weekly_used = db.count_interruptions_since(subject_id, today - timedelta(days=7))
        if hasattr(db, "has_pending_interaction"):
            pending = db.has_pending_interaction(subject_id)
        if hasattr(db, "get_baseline_rung"):
            rung = db.get_baseline_rung(subject_id, today)
        if hasattr(db, "get_answered_probe_ids"):
            asked_probe_ids = sorted(
                set(asked_probe_ids) | set(db.get_answered_probe_ids(episode_id))
            )
        if hasattr(db, "get_answered_probe_ids_ever"):
            answered_ever = sorted(db.get_answered_probe_ids_ever(subject_id))

    has_symptoms_evidence = any(a.probe_id == "probe_symptoms" and not a.declined for a in answers)

    action = select_action(
        belief=belief,
        weekly_interruptions_used=weekly_used,
        episode_questions_asked=depth_used,
        rung=rung,
        steps_in_episode=step,
        nights_in_episode=len(nights) if nights else 1,
        has_pending_interaction=pending,
        already_asked_probe_ids=asked_probe_ids,
        answered_probe_ids_ever=answered_ever,
        has_symptoms_evidence=has_symptoms_evidence,
        # One spot check per episode. Asking twice for the same hand-taken reading is not
        # more information, it is nagging.
        already_measured=bool(state.get("measurements")),
        # Questions asked that were never answered, including timeouts. Silence must not
        # produce a reassuring conclusion.
        unanswered_questions=sum(1 for a in answers if a.declined),
    )

    client = llm_client or get_llm_client()

    # VETO CHECK: Only on ASK actions
    veto_applied = False
    if action.kind == ActionKind.ASK:
        try:
            veto_def = get_prompt_definition("veto_check")
            probe_id = (
                action.question.probe.probe_id
                if action.question and hasattr(action.question, "probe")
                else "general"
            )
            question_text = (
                action.question.text
                if action.question and hasattr(action.question, "text")
                else "Proposed inquiry"
            )
            veto_prompt = veto_def.render(
                {
                    "probe_id": probe_id,
                    "question_text": question_text,
                    "known_facts": json.dumps(
                        [e.model_dump() for e in state.get("evidence", [])], default=str
                    ),
                }
            )
            veto_res, _ = client.complete(
                veto_prompt,
                schema=VetoCheckResponse,
                temperature=veto_def.temperature,
            )
            if veto_res.veto:
                veto_applied = True
                # Redundant question cancelled: convert to OBSERVE without consuming depth budget
                action = Action(
                    kind=ActionKind.OBSERVE,
                    disposition=action.disposition,
                    rationale=f"Vetoed redundant inquiry: {veto_res.reason}",
                    rejected=action.rejected,
                )
        except (
            LLMUnavailable,
            ValidationFailed,
            KeyError,
            TypeError,
            ValueError,
            AttributeError,
            StopIteration,
        ):
            pass

    if action.kind == ActionKind.ASK and not veto_applied:
        new_depth = depth_used + 1
    else:
        new_depth = depth_used

    # Write the decision down, including the decision to stay quiet.
    #
    # An episode that asked recorded the question and the probes it rejected. An episode
    # that decided asking was not worth the interruption recorded nothing at all, so
    # neither the screen nor anybody reading the record afterwards could say why the
    # system had gone quiet. That is the decision a person is most likely to want
    # explained, because it is the difference between being interrupted and not.
    #
    # Never raises into the graph: a failure to write the reasoning must not stop the
    # reasoning.
    if db is not None and hasattr(db, "conn"):
        try:
            from wha.audit.monitor import record_policy_decision

            question = getattr(action, "question", None)
            record_policy_decision(
                db.conn,
                subject_id=state.get("subject_id", "default_subject"),
                episode_id=state.get("episode_id", "ep_default"),
                action_kind=action.kind.value,
                rationale=action.rationale or "",
                chosen_probe=question.probe.probe_id if question else None,
                chosen_value=question.probe.evsi if question else None,
                interruption_cost=question.probe.interruption_cost if question else None,
                candidates=list(action.rejected or []),
            )
        except Exception as exc:  # noqa: BLE001
            # The reasoning matters more than the note about it, so this never raises into
            # the graph. It is logged rather than swallowed, because silence here would
            # mean the record quietly stopped explaining decisions.
            logger.warning("Could not record the policy decision: %s", exc)

    return {
        "action": action,
        "depth_used": new_depth,
        "step": step + 1,
    }


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
            # Whether the model wrote this sentence or the canned one was used. The
            # column defaults to "fallback" and nothing ever passed anything, so every
            # question in the record claimed the canned wording had been used, including
            # the ones the model wrote. That is the single field the Audit page uses to
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


def _retrieved_passages(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every passage `retrieve_clinical_evidence` returned in this episode, deduped."""
    passages: list[dict[str, Any]] = []
    seen: set[str] = set()
    for call in tool_calls:
        if call.get("tool_name") != "retrieve_clinical_evidence" or not call.get("ok"):
            continue
        for passage in call.get("value") or []:
            if not isinstance(passage, dict):
                continue
            chunk_id = str(passage.get("chunk_id", ""))
            if not chunk_id or chunk_id in seen:
                continue
            seen.add(chunk_id)
            passages.append(passage)
    return passages


def _passages_for_prompt(passages: list[dict[str, Any]]) -> str:
    """The retrieved passages, laid out so the model can quote a span out of one."""
    if not passages:
        return (
            "No passages were retrieved in this episode. Return an empty claims list: "
            "there is nothing to ground a claim against."
        )
    blocks = [f"[{p.get('chunk_id')}] {p.get('title', '')}\n{p.get('text', '')}" for p in passages]
    return _compact_json(blocks, _INVESTIGATE_CALLS_CHARS)


def _citations_for(passages: list[dict[str, Any]]) -> list[Citation]:
    """The retrieved passages, in the shape an EpisodeOutcome records."""
    return [
        Citation(
            source_id=str(p.get("chunk_id", "")),
            title=str(p.get("title", "")),
            uri=str(p.get("source_url") or p.get("doc_id") or "") or None,
            passage=str(p.get("text", "")),
            retrieval_score=float(p.get("score") or 0.0),
        )
        for p in passages
    ]


def _enforce_claims(
    claims: list[OutcomeClaim],
    passages: list[dict[str, Any]],
    observation: str,
) -> tuple[str, list[Citation], int, list[str]]:
    """Check each claim against the retrieved text, and strip the ones that fail.

    Returns the observation with unsupported claims removed, the citations that actually
    support what remains, the count of claims that failed, and their text. Attribution is
    decided by :func:`enforce_grounding` from where the span was found, not by what the
    model said.
    """
    if not claims:
        return observation, [], 0, []

    # Two Citation models exist. wha.retrieve.models.Citation is what the grounding check
    # searches; wha.models.Citation is what an EpisodeOutcome records. Conflating them
    # raises at the model boundary, which is the only reason this distinction is visible.
    searchable = [
        RetrievedPassage(
            source_id=str(p.get("chunk_id", "")),
            title=str(p.get("title", "")),
            uri=str(p.get("source_url") or p.get("doc_id") or ""),
            text=str(p.get("text", "")),
        )
        for p in passages
    ]

    generated = [GeneratedClaim(text=c.text, evidence_span=c.evidence_span or None) for c in claims]
    grounded, unsupported = enforce_grounding(generated, searchable)

    grounded_texts = {c.text for c in grounded}
    cleaned = observation
    stripped: list[str] = []
    for claim in claims:
        if claim.text and claim.text not in grounded_texts:
            # Stripped before display, per the contract. A claim whose span is not in any
            # retrieved passage does not get to appear in the prose a person reads.
            #
            # Recorded as well as removed. The episode view assigned `stripped_claims` an
            # empty list and never filled it, so the panel whose whole job is to show what
            # was taken out showed a green tick even on episodes where something was.
            stripped.append(claim.text)
            if claim.text in cleaned:
                cleaned = cleaned.replace(claim.text, "").strip()

    cited_ids = {c.citation for c in grounded if c.citation}
    supporting = _citations_for([p for p in passages if str(p.get("chunk_id", "")) in cited_ids])
    return cleaned or observation, supporting, unsupported, stripped


def _episode_numbers(state: EpisodeState) -> set[float]:
    """Every number this episode is genuinely entitled to quote in its prose.

    The fabricated-number filter used to blanket-permit 0 through 10, which waved through
    a real outcome saying "over 5 nights" about a two night episode. The blanket is gone,
    so the true numbers have to be supplied instead: how many nights, how far each sat
    above the person's own baseline, that baseline itself, and the nightly readings.
    """
    nights = state.get("nights", [])
    numbers: set[float] = {float(len(nights))}

    for detection in nights:
        for value in (
            detection.residual_bpm,
            detection.deviation_bpm,
            detection.robust_z,
            detection.explained_bpm,
        ):
            if value is not None:
                numbers.add(float(value))
                numbers.add(float(round(value, 1)))
                numbers.add(float(abs(round(value))))

    for feature in state.get("features", []):
        if feature.rhr_bpm is not None:
            numbers.add(float(feature.rhr_bpm))
            numbers.add(float(round(feature.rhr_bpm)))
        if feature.coverage_minutes is not None:
            numbers.add(float(feature.coverage_minutes))

    # The baseline centre, which no state field carries directly but every night implies.
    for detection in nights:
        if detection.deviation_bpm is not None:
            for feature in state.get("features", []):
                if feature.night_date == detection.night_date and feature.rhr_bpm is not None:
                    centre = feature.rhr_bpm - detection.deviation_bpm
                    numbers.add(float(round(centre, 1)))
                    numbers.add(float(round(centre)))

    return numbers


def _interruptions_this_week(db: Any, subject_id: str) -> int:
    """How many questions have been asked in the last seven days, across the whole app.

    Counted across subjects rather than per subject. This is a single-user application,
    one person and one phone, and a per-subject count let demo and simulation subjects
    each carry a private allowance pointing at the same chat.
    """
    if db is None or not hasattr(db, "count_interruptions_since"):
        return 0
    try:
        return int(db.count_interruptions_since(subject_id, local_today() - timedelta(days=7)))
    except (TypeError, ValueError, AttributeError):
        return 0


def _cycle_applicability(answers: list[Answer]) -> bool | None:
    """Three-state, from the one-time probe_cycle answer. None means never established."""
    for answer in answers:
        if answer.probe_id != "probe_cycle" or answer.declined:
            continue
        if answer.option_id == "na":
            return False
        if answer.option_id in {"recent", "older"}:
            return True
    return None


def _episode_context(state: EpisodeState, db: Any, answers: list[Answer]) -> EpisodeContext:
    """The two facts `update_belief` reads from context and nothing ever supplied.

    Both were dead wires. `luteal_applicable` was never passed by any caller, so the
    menstrual cycle cause sat at exactly 0.0 for every episode and answering the question
    changed nothing. `has_recent_illness` was read by name inside `update_belief` and was
    not even a field on `EpisodeContext`, so a correctly constructed context would still
    have failed the `hasattr` check.

    Cycle applicability comes from the Settings profile first, because it is a standing
    fact about a person and not worth spending an interruption on. An already-answered
    `probe_cycle` is honoured as a fallback so a person who answered it before the profile
    existed is not asked to repeat themselves.
    """
    subject_id = state.get("subject_id", "")

    cycle: bool | None = None
    if db is not None and hasattr(db, "get_profile_menstruates"):
        cycle = db.get_profile_menstruates(subject_id)
    if cycle is None:
        cycle = _cycle_applicability(answers)

    recent_illness = False
    if db is not None and hasattr(db, "has_recent_illness_episode"):
        recent_illness = db.has_recent_illness_episode(subject_id, local_today())

    nights = state.get("nights", [])
    return EpisodeContext(
        subject_id=subject_id,
        episode_opened_on=min((d.night_date for d in nights), default=local_today()),
        rung=BaselineRung.COLD,
        usable_nights=len(nights),
        cycle_applicable=cycle,
        has_recent_illness=recent_illness,
    )


def node_conclude(
    state: EpisodeState,
    llm_client: LLMClient | None = None,
    db: Any = None,
) -> dict[str, Any]:
    """Draft episode outcome findings, disposition, differential, and action."""
    nights = state.get("nights", [])
    now_d = local_today()
    opened_on = min(d.night_date for d in nights) if nights else now_d
    closed_on = max(d.night_date for d in nights) if nights else now_d

    belief = state.get("belief")
    if belief is None:
        belief = update_belief(
            episode_nights=nights,
            features=state.get("features", []),
            answers=state.get("answers", []),
            measurements=state.get("measurements", []),
            context=_episode_context(state, db, state.get("answers", [])),
        )

    answers = state.get("answers", [])

    # The subject's real baseline, fetched once. The rung decides the disposition, and both
    # figures go into the outcome, where they were hardcoded to 28 nights and MATURE.
    #
    # Assuming a mature baseline let a cold-start subject be given a confident disposition
    # off two nights of data, which is precisely what INSUFFICIENT_DATA exists to prevent.
    conclude_rung = BaselineRung.MATURE
    conclude_nights = len(nights)
    if db is not None and hasattr(db, "get_baseline"):
        stored = db.get_baseline(state.get("subject_id", ""), local_today())
        if stored is not None:
            conclude_rung = stored.rung
            conclude_nights = stored.usable_nights
    elif db is not None and hasattr(db, "get_baseline_rung"):
        conclude_rung = db.get_baseline_rung(state.get("subject_id", ""), local_today())

    action_model = state.get("action")
    if action_model is not None and action_model.disposition is not None:
        disposition = action_model.disposition
    else:
        disposition = determine_disposition(
            belief,
            rung=conclude_rung,
            unanswered_questions=sum(1 for a in answers if a.declined),
        )

    # Every entry used to carry a probability with `supporting: []` and
    # `contradicting: []`, so a ranked list of causes appeared with no reason attached to
    # any of them.
    differential = ground_differential(
        belief=belief,
        nights=nights,
        features=state.get("features", []),
        answers=answers,
        measurements=state.get("measurements", []),
        cycle_applicable=_episode_context(state, db, answers).cycle_applicable,
    )

    # The passages the agent actually retrieved during this episode. `citations` was
    # hardcoded empty, which silently disabled the claim-to-source enforcement the
    # contract specifies and made the grounding check unreachable.
    passages = _retrieved_passages(state.get("tool_calls", []))

    observation = f"Observed {len(nights)} nights. Primary finding: {disposition.value}."
    # An ESCALATED episode used to record its recommended action as "monitor", because the
    # expression here was a two-way choice over a five-way disposition. The record then
    # said the system had told somebody to keep an eye on it, on the one occasion it had
    # told them to seek care now.
    action_by_disposition: dict[Disposition, str] = {
        Disposition.ESCALATED: "seek_urgent_care",
        Disposition.LIKELY_ILLNESS: "rest",
        Disposition.UNRESOLVED: "monitor",
        Disposition.LIKELY_BENIGN: "monitor",
        Disposition.EXPLAINED_BY_EVENT: "monitor",
        Disposition.INSUFFICIENT_DATA: "monitor",
    }
    action_val: Literal["rest", "monitor", "seek_same_day_care", "seek_urgent_care"] = (
        action_by_disposition.get(disposition, "monitor")  # type: ignore[assignment]
    )
    # Selected, never written. The two lines that used to sit here duplicated the general
    # wording in red_flags.yaml, and the first of them asserted a ">3 nights" threshold
    # that appears in no source.
    escalation_criteria = select_escalation_criteria(
        disposition=disposition,
        triggered_flags=list(state.get("triggered_flags", [])),
        # The top of the differential, which item 2 asked for and which was never passed.
        # `differential` is ordered by how far this episode MOVED each cause, so the first
        # entry is the explanation the evidence actually argued for rather than the one
        # with the largest base rate.
        leading_cause=(differential[0].cause.value if differential else None),
    )

    # Everything this episode looked up, whether or not a sentence ended up quoting it.
    # This is what the Evidence tab shows, and the honest answer to "what did it read".
    # Which sentences survived grounding is reported separately as unsupported_claims.
    citations = _citations_for(passages)
    unsupported_claims = 0
    stripped_claims: list[str] = []

    client = llm_client or get_llm_client()
    try:
        outcome_def = get_prompt_definition("write_outcome")
        outcome_prompt = outcome_def.render(
            {
                "summary": f"{len(nights)} nights observed",
                "disposition": disposition.value,
                "top_causes": json.dumps({c.value: p for c, p in belief.top(3)}),
                "facts": json.dumps(
                    [e.model_dump() for e in state.get("evidence", [])], default=str
                ),
                # What the person actually said. Without it the model wrote "No specific
                # symptoms were reported" into the outcome of an episode in which the
                # person had answered "Feverish or chills", which is not a wording problem
                # but a false statement about their own report.
                "answers": _summarise_answers(answers),
                "passages": _passages_for_prompt(passages),
            }
        )
        outcome_res, _ = client.complete(
            outcome_prompt,
            schema=WriteOutcomeResponse,
            temperature=outcome_def.temperature,
        )
        if outcome_res.observation:
            observation = outcome_res.observation
        # Claim-to-source enforcement, which the contract specifies as a deterministic
        # verbatim containment test rather than a judgement. The model's claims were
        # parsed and then dropped on the floor, so this never ran on anything.
        observation, _, unsupported_claims, stripped_claims = _enforce_claims(
            claims=outcome_res.claims,
            passages=passages,
            observation=observation,
        )
    except (
        LLMUnavailable,
        ValidationFailed,
        KeyError,
        TypeError,
        ValueError,
        AttributeError,
        StopIteration,
    ):
        pass

    draft = EpisodeOutcome(
        episode_id=state.get("episode_id", "ep_default"),
        subject_id=state.get("subject_id", "sub_default"),
        opened_on=opened_on,
        closed_on=closed_on,
        disposition=disposition,
        observation=observation,
        # The real figures, which this function already fetched a few lines above to
        # decide the disposition. These were hardcoded, so every outcome ever written
        # claimed 28 nights and a fully established baseline, including outcomes for
        # subjects with four.
        baseline_nights=conclude_nights,
        baseline_rung=conclude_rung,
        differential=differential,
        # Both the facts extracted from tool output and the passages that were actually
        # cited. Naming only the fact fields described where a number came from and never
        # what the reasoning about it rested on.
        evidence_used=sorted(
            {e.field for e in state.get("evidence", [])} | {c.source_id for c in citations}
        ),
        ruled_out=[],
        citations=citations,
        unsupported_claims=unsupported_claims,
        action=action_val,
        escalation_criteria=escalation_criteria,
        confidence="moderate" if disposition != Disposition.UNRESOLVED else "low",
        # Hardcoded to 0, so the one line that tells a person how much of their weekly
        # allowance this episode spent always said none of it.
        interruptions_used_this_week=_interruptions_this_week(db, state.get("subject_id", "")),
        depth_used_this_episode=state.get("depth_used", 0),
    )

    # What the agent actually did, written by the graph that did it. The Trace tab used to
    # infer this by matching stage names against the audit log's `operation` column, which
    # holds ten fixed values and none of them is a stage name, so every stage on every
    # episode was reported as skipped with an invented reason.
    if db is not None and hasattr(db, "record_episode_trace"):
        db.record_episode_trace(
            episode_id=state.get("episode_id", ""),
            payload={
                # The stages that have ACTUALLY run by the time this line executes.
                # "critique" was in this set and had not run yet; "review" could never be
                # in it, because both run after conclude. They record themselves now,
                # through `record_episode_stage_ran`.
                "nodes_ran": sorted(
                    {"preload", "investigate", "believe", "decide", "conclude"}
                    | ({"ask"} if answers else set())
                ),
                # THE FIELD NAMES ARE THE ONES THE EXPANDER READS. It rendered
                # "(Source: `None`, Freshness: `current`)" with an empty `{}` of arguments
                # on every call, because it read source_ref/arguments/result and this wrote
                # tool_name/args/ok/note. Both sides now use ToolResult's own names, and
                # `source_ids` and `freshness` are carried rather than dropped: they are
                # what tell a reader whether the tool answered from fresh data.
                #
                # `value` is summarised rather than stored. The full result is already in
                # the audit log, and a retrieval call returns several passages, so copying
                # them here would put the corpus in the trace of every episode.
                "tool_calls": [
                    {
                        "tool_name": call.get("tool_name"),
                        "args": call.get("args", {}),
                        "ok": call.get("ok", True),
                        "source_ids": call.get("source_ids", []),
                        "freshness": call.get("freshness"),
                        "as_of_utc": call.get("as_of_utc"),
                        "result_summary": _summarise_tool_value(call.get("value")),
                        "note": call.get("note") or call.get("error"),
                    }
                    for call in state.get("tool_calls", [])
                ],
                "tool_call_count": state.get("tool_call_count", 0),
                "depth_used": state.get("depth_used", 0),
                "stripped_claims": stripped_claims,
                "questions_asked": len(answers),
            },
        )

    return {
        "draft": draft,
        "step": state.get("step", 0) + 1,
    }


def _summarise_tool_value(value: Any) -> str:
    """One readable line about what a tool returned, without copying the corpus into it."""
    if value is None:
        return ""
    if isinstance(value, list):
        return f"{len(value)} item{'s' if len(value) != 1 else ''}"
    if isinstance(value, dict):
        return ", ".join(f"{k}={str(v)[:40]}" for k, v in list(value.items())[:6])
    return str(value)[:200]


def _record_stage_ran(db: Any, state: EpisodeState, stage: str) -> None:
    """Note that a stage ran, for the stages that execute after the trace is written.

    Never raises into the graph: a trace that is missing a stage is a worse screen, and a
    graph that dies recording one is a worse system.
    """
    if db is None or not hasattr(db, "record_episode_stage_ran"):
        return
    try:
        db.record_episode_stage_ran(state.get("episode_id", ""), stage)
    except Exception:  # noqa: BLE001
        return


def node_critique(
    state: EpisodeState,
    llm_client: LLMClient | None = None,
    db: Any = None,
) -> dict[str, Any]:
    """Run deterministic grounding first, followed by subtractive LLM critique."""
    draft = state.get("draft")
    if draft is None:
        return {"step": state.get("step", 0) + 1}

    obs = draft.observation
    # Deterministic phrase cleaning for false reassurance & diagnosis language
    for phrase in FALSE_REASSURANCE_PHRASES:
        if phrase in obs.lower():
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            obs = pattern.sub("", obs).strip()

    for phrase in DIAGNOSIS_PHRASES:
        if phrase in obs.lower():
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            obs = pattern.sub("", obs).strip()

    cleaned_draft = draft.model_copy(update={"observation": obs})

    # Step A: Deterministic grounding & sanitization
    sanitized_draft = validate_and_sanitize_outcome(
        cleaned_draft,
        episode_numbers=_episode_numbers(state),
    )

    # Step B: LLM Critique Pass (Subtractive only)
    client = llm_client or get_llm_client()
    try:
        critique_def = get_prompt_definition("critique")
        critique_prompt = critique_def.render(
            {
                "draft_text": sanitized_draft.observation,
                "sources": json.dumps(sanitized_draft.evidence_used),
                "facts": json.dumps(
                    [e.model_dump() for e in state.get("evidence", [])], default=str
                ),
            }
        )
        critique_res, _ = client.complete(
            critique_prompt,
            schema=CritiqueResponse,
            temperature=critique_def.temperature,
        )
        current_text = sanitized_draft.observation
        # Strip any ungrounded claims identified by the model
        for stripped in critique_res.stripped_claims:
            if stripped and stripped in current_text:
                current_text = current_text.replace(stripped, "").strip()

        # If model proposed a shorter / sanitized modified_text, use it if it doesn't inflate length
        if critique_res.modified_text and len(critique_res.modified_text) <= len(
            sanitized_draft.observation
        ):
            current_text = critique_res.modified_text

        sanitized_draft = sanitized_draft.model_copy(update={"observation": current_text})
    except (
        LLMUnavailable,
        ValidationFailed,
        KeyError,
        TypeError,
        ValueError,
        AttributeError,
        StopIteration,
    ):
        pass

    _record_stage_ran(db, state, "critique")

    return {
        "draft": sanitized_draft,
        "step": state.get("step", 0) + 1,
    }


def node_review(
    state: EpisodeState,
    db: Any = None,
) -> dict[str, Any]:
    """Human review checkpoint. Resumed by approve, edit, reject, escalate or a timeout.

    This is the one place a person can say "no, that is wrong" before the system commits
    to a conclusion about their health, and it had never once been possible. A background
    job answered "approve" on their behalf about fifteen minutes later and the record then
    said a human had approved it. A record showing a decision that never happened is worse
    than no checkpoint at all.

    Two things had to change for a person to reach this screen. The episode is now parked
    in AWAITING_HUMAN_REVIEW, which `get_pending_interaction` requires before it will show
    a draft at all, and the scheduler no longer supplies a decision.

    Everything before the `interrupt()` runs again on resume, so it has to be idempotent.
    `record_review_requested` writes at most one row per episode for that reason.
    """
    draft = state.get("draft")
    if draft is None:
        return {"step": state.get("step", 0) + 1}

    episode_id = state.get("episode_id", "")
    if db is not None and hasattr(db, "set_episode_state"):
        db.set_episode_state(episode_id, "AWAITING_HUMAN_REVIEW")
    if db is not None and hasattr(db, "record_review_requested"):
        db.record_review_requested(
            subject_id=state.get("subject_id", ""),
            episode_id=episode_id,
            disposition=draft.disposition.value,
        )

    raw_response = interrupt(
        {
            "kind": "human_review",
            "draft": draft.model_dump(),
        }
    )

    status = "closed"
    final_draft = draft
    decision = "approve"
    reviewed_by_person = True

    if isinstance(raw_response, dict):
        # Nobody looked at it inside the time allowed. Close it, and record that it closed
        # unreviewed. Do not record an approval, and do not silently change the finding:
        # the draft the agent produced is what it produced.
        if raw_response.get("timed_out"):
            decision = "closed_unreviewed"
            reviewed_by_person = False
        else:
            decision = raw_response.get("decision", "approve")
            if decision == "reject":
                final_draft = draft.model_copy(update={"disposition": Disposition.UNRESOLVED})
                status = "unresolved"
            elif decision == "edit":
                edited_obs = raw_response.get("edited_observation", draft.observation)
                # Machine fields (disposition, differential, baseline) are preserved
                final_draft = draft.model_copy(update={"observation": edited_obs})
            elif decision == "escalate":
                final_draft = draft.model_copy(
                    update={"disposition": Disposition.ESCALATED, "action": "seek_urgent_care"}
                )

    if db is not None and hasattr(db, "record_review_decision"):
        db.record_review_decision(
            subject_id=state.get("subject_id", ""),
            episode_id=episode_id,
            decision=decision,
            rationale=(raw_response.get("rationale") if isinstance(raw_response, dict) else None),
            reviewed_by_person=reviewed_by_person,
        )

    _record_stage_ran(db, state, "review")

    return {
        "draft": final_draft,
        "status": status,
        "step": state.get("step", 0) + 1,
    }
