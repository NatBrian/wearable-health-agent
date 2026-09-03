"""Graph execution nodes for preloading, investigation, belief, decision, asking, measuring, and outcome lifecycle."""

import json
import re
from datetime import datetime, timedelta
from typing import Any, Literal

from langgraph.types import interrupt
from pydantic import BaseModel, Field

from wha.agent.state import EpisodeState
from wha.agent.tools.impl import create_default_tool_registry
from wha.agent.tools.registry import ToolContext, ToolRegistry
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
    DifferentialItem,
    Disposition,
    EpisodeOutcome,
    ExtractedFact,
    MeasurementResult,
    Question,
)
from wha.notify.protocol import MessageKind
from wha.policy import determine_disposition
from wha.policy.select import select_action
from wha.safety.output_checks import (
    DIAGNOSIS_PHRASES,
    FALSE_REASSURANCE_PHRASES,
    validate_and_sanitize_outcome,
)
from wha.safety.tier_c import check_red_flags_with_tier_c


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


class WriteOutcomeResponse(BaseModel):
    """Synthesized outcome prose and escalation criteria from model."""

    observation: str
    claims: list[str] = Field(default_factory=list)
    action_text: str = ""
    escalation_criteria: list[str] = Field(default_factory=list)


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
    prompt = prompt_def.render(
        {
            "episode_id": episode_id,
            "history_summary": json.dumps(state.get("preloaded", {}), default=str),
            "previous_calls": json.dumps(current_calls, default=str),
        }
    )

    while True:
        if context.tool_call_count >= MAX_TOOL_CALLS_PER_EPISODE:
            break

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

    # Structured extraction of typed facts (untrusted text has nowhere to go)
    facts: list[ExtractedFact] = []
    try:
        fact_def = get_prompt_definition("extract_facts")
        fact_prompt = fact_def.render(
            {
                "user_response": json.dumps(current_calls, default=str),
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
        "tool_calls": current_calls,
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
        has_symptoms_evidence=has_symptoms_evidence,
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
                "step": state.get("step", 0) + 1,
            }

    return {
        "answers": [answer],
        "step": state.get("step", 0) + 1,
    }


def node_measure(
    state: EpisodeState,
    notifier: Any = None,
    db: Any = None,
) -> dict[str, Any]:
    """Measure node with idempotent pre-interrupt execution."""
    action = state.get("action")
    episode_id = state.get("episode_id", "ep_default")
    measurement_id = (
        action.measurement.measurement_id
        if action and action.measurement
        else f"meas_{episode_id}_{state.get('step', 0)}"
    )

    # 1. Idempotent check & notify
    already_sent = False
    if db is not None and hasattr(db, "has_notification_for"):
        already_sent = db.has_notification_for(measurement_id)

    if not already_sent and notifier is not None:
        delivered = notifier.send(
            recipient_id=state.get("subject_id"),
            kind=MessageKind.MEASUREMENT,
            text="Please perform spot measurement.",
            interaction_id=measurement_id,
        )
        if delivered and db is not None and hasattr(db, "record_notification"):
            db.record_notification(interaction_id=measurement_id, recipient=state.get("subject_id"))

    # 2. Interrupt
    raw_response = interrupt(
        {
            "kind": "measurement",
            "interaction_id": measurement_id,
        }
    )

    # 3. Post-interrupt parsing
    if isinstance(raw_response, MeasurementResult):
        meas_res = raw_response
    elif isinstance(raw_response, dict):
        meas_res = MeasurementResult(
            measurement_id=measurement_id,
            kind=raw_response.get("kind", "spot_resting_hr"),
            value=raw_response.get("value"),
            observed_at_utc=raw_response.get("observed_at_utc"),
            satisfied=raw_response.get("satisfied", False),
        )
    else:
        meas_res = MeasurementResult(
            measurement_id=measurement_id,
            kind="spot_resting_hr",
            satisfied=False,
        )

    return {
        "measurements": [meas_res],
        "step": state.get("step", 0) + 1,
    }


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
        )

    action_model = state.get("action")
    if action_model is not None and action_model.disposition is not None:
        disposition = action_model.disposition
    else:
        # The subject's real rung, not an assumed MATURE. Assuming a mature baseline here
        # let a cold-start subject be given a confident disposition off two nights of data,
        # which is precisely what INSUFFICIENT_DATA exists to prevent.
        conclude_rung = BaselineRung.MATURE
        if db is not None and hasattr(db, "get_baseline_rung"):
            conclude_rung = db.get_baseline_rung(state.get("subject_id", ""), local_today())
        disposition = determine_disposition(belief, rung=conclude_rung)

    differential = [
        DifferentialItem(
            cause=c,
            probability=round(p, 4),
            supporting=[],
            contradicting=[],
        )
        for c, p in belief.top(5)
    ]

    observation = f"Observed {len(nights)} nights. Primary finding: {disposition.value}."
    action_val: Literal["rest", "monitor", "seek_same_day_care", "seek_urgent_care"] = (
        "rest" if disposition == Disposition.LIKELY_ILLNESS else "monitor"
    )
    escalation_criteria = [
        "Seek care if elevated heart rate persists >3 nights without confounders.",
        "Seek immediate emergency care if experiencing chest pain or severe shortness of breath.",
    ]

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
            }
        )
        outcome_res, _ = client.complete(
            outcome_prompt,
            schema=WriteOutcomeResponse,
            temperature=outcome_def.temperature,
        )
        if outcome_res.observation:
            observation = outcome_res.observation
        if outcome_res.escalation_criteria:
            escalation_criteria = outcome_res.escalation_criteria
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
        baseline_nights=28,
        baseline_rung=BaselineRung.MATURE,
        differential=differential,
        evidence_used=[e.field for e in state.get("evidence", [])],
        ruled_out=[],
        citations=[],
        unsupported_claims=0,
        action=action_val,
        escalation_criteria=escalation_criteria,
        confidence="moderate" if disposition != Disposition.UNRESOLVED else "low",
        interruptions_used_this_week=0,
        depth_used_this_episode=state.get("depth_used", 0),
    )

    return {
        "draft": draft,
        "step": state.get("step", 0) + 1,
    }


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
    sanitized_draft = validate_and_sanitize_outcome(cleaned_draft)

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

    return {
        "draft": sanitized_draft,
        "step": state.get("step", 0) + 1,
    }


def node_review(
    state: EpisodeState,
    db: Any = None,
) -> dict[str, Any]:
    """Human review checkpoint. Resumed by approve, edit, reject, or escalate."""
    draft = state.get("draft")
    if draft is None:
        return {"step": state.get("step", 0) + 1}

    raw_response = interrupt(
        {
            "kind": "human_review",
            "draft": draft.model_dump(),
        }
    )

    status = "closed"
    final_draft = draft

    if isinstance(raw_response, dict):
        decision = raw_response.get("decision", "approve")
        if decision == "reject":
            final_draft = draft.model_copy(update={"disposition": Disposition.UNRESOLVED})
            status = "unresolved"
        elif decision == "edit":
            edited_obs = raw_response.get("edited_observation", draft.observation)
            # Machine fields (disposition, differential, baseline) are preserved
            final_draft = draft.model_copy(update={"observation": edited_obs})
            status = "closed"
        elif decision == "escalate":
            final_draft = draft.model_copy(
                update={"disposition": Disposition.ESCALATED, "action": "seek_urgent_care"}
            )
            status = "closed"
        else:
            final_draft = draft
            status = "closed"

    return {
        "draft": final_draft,
        "status": status,
        "step": state.get("step", 0) + 1,
    }
