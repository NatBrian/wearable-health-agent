"""Drafting the outcome, with every clinical claim traced to a source."""

import json
from typing import Any, Literal

from wha.agent.differential import ground_differential
from wha.agent.nodes.context import (
    _episode_context,
    _interruptions_this_week,
    _summarise_answers,
)
from wha.agent.nodes.evidence import (
    _citations_for,
    _enforce_claims,
    _passages_for_prompt,
    _retrieved_passages,
)
from wha.agent.nodes.schemas import WriteOutcomeResponse
from wha.agent.state import EpisodeState
from wha.belief import update_belief
from wha.clock import local_today
from wha.errors import LLMUnavailable, ValidationFailed
from wha.llm.client import LLMClient, get_llm_client
from wha.llm.prompts import get_prompt_definition
from wha.models import (
    BaselineRung,
    Disposition,
    EpisodeOutcome,
)
from wha.policy import determine_disposition
from wha.safety.output_checks import (
    select_escalation_criteria,
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
