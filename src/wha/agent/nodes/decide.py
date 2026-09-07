"""The policy step: whether a question is worth the interruption."""

import json
import logging
from datetime import timedelta
from typing import Any

from wha.agent.nodes.context import _episode_context
from wha.agent.nodes.schemas import VetoCheckResponse
from wha.agent.state import EpisodeState
from wha.belief import update_belief
from wha.clock import local_today
from wha.constants import SYMPTOM_FOLLOWUP_PROBE_ID
from wha.errors import LLMUnavailable, ValidationFailed
from wha.llm.client import LLMClient, get_llm_client
from wha.llm.prompts import get_prompt_definition
from wha.models import (
    Action,
    ActionKind,
    BaselineRung,
)
from wha.policy.select import select_action

logger = logging.getLogger(__name__)


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

    # A symptom the person reported and has never said was better, and how many times this
    # investigation has already followed one up. Read here rather than in the policy so
    # that select_action stays a pure function of its arguments and can still be tested
    # without a database.
    outstanding_symptom: str | None = None
    followups_sent = 0
    followup_sent_tonight = False
    conn = getattr(db, "conn", None)
    if conn is not None and subject_id:
        try:
            from wha.service.symptoms import outstanding_symptoms, symptom_as_of

            runs = outstanding_symptoms(conn, subject_id, symptom_as_of(conn, subject_id))
            # The longest-running one. If several are outstanding it is the one that has
            # been going on the longest that the person most needs asking about.
            if runs:
                outstanding_symptom = max(runs, key=lambda r: r.nights).flag_id
            row = conn.execute(
                """SELECT COUNT(*) AS n FROM interactions
                    WHERE episode_id = ? AND probe_id = ? AND initiation = 'followup'""",
                (episode_id, SYMPTOM_FOLLOWUP_PROBE_ID),
            ).fetchone()
            followups_sent = int(row["n"]) if row else 0
            # And whether one has already gone out TONIGHT. The count above cannot answer
            # that: follow-up rows are keyed by night, so ten follow-ups on one night are
            # one row and `followups_sent` sits at 1 all day. Reading the same key the ask
            # node writes is what makes this exact rather than approximate.
            followup_sent_tonight = (
                conn.execute(
                    "SELECT 1 FROM interactions WHERE id = ? LIMIT 1",
                    (f"int_{episode_id}_{SYMPTOM_FOLLOWUP_PROBE_ID}_{local_today().isoformat()}",),
                ).fetchone()
                is not None
            )
        except Exception:
            # Never let this cost the episode its decision. A failure here means the
            # follow-up does not fire, which is the behaviour that existed before it, so
            # it degrades to the old system rather than to no system.
            logger.exception("Could not read outstanding symptoms for %s", subject_id)

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
        # Overrides the arithmetic. See select_action step 3b.
        outstanding_symptom=outstanding_symptom,
        episode_followups_sent=followups_sent,
        followup_sent_tonight=followup_sent_tonight,
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
