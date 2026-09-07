"""State the nodes share: episode context, counters, and prompt budgets."""

import json
from datetime import timedelta
from typing import Any

from wha.agent.state import EpisodeState
from wha.clock import local_today
from wha.models import (
    Answer,
    BaselineRung,
    EpisodeContext,
)

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
