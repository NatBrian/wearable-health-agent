"""Episode state schema and reducers for the LangGraph agent."""

from collections.abc import Sequence
from typing import Annotated, Any, Literal, TypedDict

from wha.models import (
    Action,
    Answer,
    BeliefState,
    Detection,
    EpisodeOutcome,
    ExtractedFact,
    MeasurementResult,
    NightlyFeatures,
)


def add_nights(
    left: Sequence[Detection] | None,
    right: Sequence[Detection] | None,
) -> list[Detection]:
    """Reducer that combines detection nights and dedupes by night_date."""
    combined: list[Detection] = list(left or [])
    existing_dates = {d.night_date for d in combined}
    for item in right or []:
        if item.night_date not in existing_dates:
            combined.append(item)
            existing_dates.add(item.night_date)
    return combined


def add_items(
    left: Sequence[Any] | None,
    right: Sequence[Any] | None,
) -> list[Any]:
    """Reducer for list concatenation."""
    return list(left or []) + list(right or [])


class EpisodeState(TypedDict, total=False):
    """LangGraph state representing an early warning episode across multiple turns."""

    episode_id: str
    subject_id: str
    nights: Annotated[list[Detection], add_nights]
    features: list[NightlyFeatures]
    preloaded: dict[str, Any]
    tool_calls: Annotated[list[dict[str, Any]], add_items]
    evidence: Annotated[list[ExtractedFact], add_items]
    answers: Annotated[list[Answer], add_items]
    measurements: Annotated[list[MeasurementResult], add_items]
    belief: BeliefState | None
    action: Action | None
    draft: EpisodeOutcome | None
    step: int
    tool_call_count: int
    depth_used: int
    status: Literal["active", "parked", "closed", "unresolved"]
    safety_event: str | None
    escalation_level: str | None
    # Which deterministic rules fired, by id. node_conclude selects the when-to-seek-care
    # wording from these, so the outcome quotes the rule that fired rather than a
    # sentence the model wrote.
    triggered_flags: Annotated[list[str], add_items]
