"""The tool-calling loop where the model gathers evidence."""

import json
from typing import Any

from wha.agent.nodes.context import (
    _INVESTIGATE_CALL_VALUE_CHARS,
    _INVESTIGATE_CALLS_CHARS,
    _INVESTIGATE_HISTORY_CHARS,
    _compact_json,
    _summarise_answers,
)
from wha.agent.nodes.schemas import FactExtractionResponse, InvestigateStep
from wha.agent.state import EpisodeState
from wha.agent.tools.impl import create_default_tool_registry
from wha.agent.tools.registry import ToolContext, ToolRegistry, describe_tools
from wha.constants import MAX_TOOL_CALLS_PER_EPISODE
from wha.errors import LLMUnavailable, PermissionDenied, ValidationFailed
from wha.llm.client import LLMClient, get_llm_client
from wha.llm.prompts import get_prompt_definition
from wha.models import (
    ExtractedFact,
)


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
