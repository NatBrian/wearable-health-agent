"""Graph execution nodes for preloading, investigation, belief update, policy decision, asking, and measuring."""

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from langgraph.types import interrupt
from pydantic import BaseModel, Field

from wha.agent.state import EpisodeState
from wha.agent.tools.impl import create_default_tool_registry
from wha.agent.tools.registry import ToolContext, ToolRegistry
from wha.belief import update_belief
from wha.constants import MAX_TOOL_CALLS_PER_EPISODE
from wha.errors import LLMUnavailable, PermissionDenied, ValidationFailed
from wha.llm.client import LLMClient, get_llm_client
from wha.llm.prompts import get_prompt_definition
from wha.models import (
    Action,
    ActionKind,
    Answer,
    ExtractedFact,
    MeasurementResult,
    Question,
)
from wha.policy.select import select_action


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
        end_d = datetime.now(UTC).date()
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

    action = select_action(
        belief=belief,
        episode_questions_asked=depth_used,
        steps_in_episode=step,
        nights_in_episode=len(nights) if nights else 1,
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
        )

    # 3. Idempotent send notification: check if already sent
    already_sent = False
    if db is not None:
        if hasattr(db, "has_notification_for"):
            already_sent = db.has_notification_for(interaction_id)
        elif hasattr(db, "get_notifications_for_interaction"):
            already_sent = bool(db.get_notifications_for_interaction(interaction_id))

    if not already_sent and notifier is not None:
        if hasattr(notifier, "send_message"):
            notifier.send_message(
                recipient_id=state.get("subject_id"),
                text=updated_question.text,
                interaction_id=interaction_id,
                options=[opt.model_dump() for opt in updated_question.options],
            )
        if db is not None and hasattr(db, "record_notification"):
            db.record_notification(interaction_id=interaction_id, recipient=state.get("subject_id"))

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
        if hasattr(notifier, "send_message"):
            notifier.send_message(
                recipient_id=state.get("subject_id"),
                text="Please perform spot measurement.",
                interaction_id=measurement_id,
            )
        if db is not None and hasattr(db, "record_notification"):
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
