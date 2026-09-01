"""Graph execution nodes for preloading context and running LLM investigation."""

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from wha.agent.state import EpisodeState
from wha.agent.tools.impl import create_default_tool_registry
from wha.agent.tools.registry import ToolContext, ToolRegistry
from wha.constants import MAX_TOOL_CALLS_PER_EPISODE
from wha.errors import LLMUnavailable, PermissionDenied, ValidationFailed
from wha.llm.client import LLMClient, get_llm_client
from wha.llm.prompts import get_prompt_definition
from wha.models import ExtractedFact


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
