"""The night as a grid of numbered steps you can click.

A diagram you cannot click tells you the shape of the system. What a person actually wants
is the step that produced the number they are looking at, so every card here is a button.

Colour carries which machine ran the step, because the three halves behave differently when
they are wrong: arithmetic is wrong the same way every time, a language model is not, and
the safety floor can only ever raise urgency. Steps that did not run are dimmed and keep
their reason on the card, since "nothing here" and "this did not need to happen" are
different things.
"""

import streamlit as st

from wha.models import NightPipeline, PipelineStepView, StepLayer, StepStatus
from wha.ui import design, explain, format
from wha.ui.components.api import api

COLUMNS = 5

STEP_NAMES: dict[str, str] = {
    "collect": "Collect from watch",
    "store": "Store the readings",
    "sleep_window": "Find your sleep",
    "features": "One number for the night",
    "baseline": "Your normal",
    "subtract_explained": "Subtract what is explained",
    "detect": "Judge the night",
    "safety_floor": "Check what you told us",
    "episode_open": "Open an investigation",
    "preload": "Fixed first readings",
    "investigate": "AI gathers evidence",
    "believe": "Weigh twelve causes",
    "decide": "Worth asking you?",
    "ask": "Ask you",
    "answer": "Your answer",
    "conclude": "Draft a conclusion",
    "critique": "Remove unsourced claims",
    "review": "A person checks it",
    "deliver": "Send and save",
    "safety_phrase_rules": "Phrase rules",
    "safety_triage": "Published checklist",
}


def step_name(step_id: str) -> str:
    return STEP_NAMES.get(step_id, step_id.replace("_", " "))


def _meta(step: PipelineStepView, client) -> str:
    """The one line under a card: when it happened, or what its status means."""
    if step.occurred_utc is not None:
        return format.local_time(client, step.occurred_utc)
    if step.status is StepStatus.RAN:
        return "no time recorded"
    return format.status_word(str(step.status))


def render_headline(pipeline: NightPipeline) -> None:
    """The tiles above the graph. Every value is assembled from stored rows."""
    head = pipeline.headline
    level = str(head.level)

    tiles = [
        ("What this night was", level, explain.level(level, str(head.rung) if head.rung else None)),
        (
            "Most likely explanation",
            str(head.primary_cause).replace("_", " ") if head.primary_cause else "not worked out",
            "Only worked out for nights that were investigated."
            if head.primary_cause is None
            else f"{format.probability(head.primary_probability)} likely on the evidence so far.",
        ),
        # The note used to explain coverage while the tile showed hours slept, so it
        # described a different number from the one above it.
        (
            "Your sleep",
            format.hours(head.sleep_hours),
            (
                f"{explain.text('metric.sleep_hours')} Your watch measured "
                f"{format.minutes(head.coverage_minutes)} of it."
            ),
        ),
        (
            "Questions asked",
            str(head.questions_asked),
            "You are only asked where your answer would change the outcome.",
        ),
        (
            "Sources read",
            str(head.sources_read),
            "Passages quoted while working this night out.",
        ),
    ]

    columns = st.columns(len(tiles))
    for column, (label, value, note) in zip(columns, tiles, strict=True):
        with column:
            tone = level if label == "What this night was" else "muted"
            st.markdown(design.tile(label, value, note, tone=tone), unsafe_allow_html=True)


def render(pipeline: NightPipeline) -> str | None:
    """Draw the grid. Returns the step id the reader has open, if any."""
    client = api()
    st.caption(explain.text("pipeline.how_to_read"))

    main = [s for s in pipeline.steps if s.layer is not StepLayer.SAFETY]
    safety = [s for s in pipeline.steps if s.layer is StepLayer.SAFETY]

    grid, side = st.columns([4, 1])

    with grid:
        for start in range(0, len(main), COLUMNS):
            row = main[start : start + COLUMNS]
            columns = st.columns(COLUMNS)
            for column, step in zip(columns[: len(row)], row, strict=True):
                with column:
                    _render_step(step, client)

    with side:
        st.markdown(
            design.chip("Always on", "safety") + " <strong>Safety floor</strong>",
            unsafe_allow_html=True,
        )
        st.caption("Runs on anything you type, before the AI sees it, and can only raise urgency.")
        for step in safety:
            _render_step(step, client)

    return st.session_state.get("pipeline_step")


def _render_step(step: PipelineStepView, client) -> None:
    dim = step.status is not StepStatus.RAN
    st.markdown(
        design.step_card(
            ordinal=step.ordinal,
            name=step_name(step.step_id),
            layer=str(step.layer),
            figure=step.headline_figure,
            meta=_meta(step, client),
            dim=dim,
        ),
        unsafe_allow_html=True,
    )
    # The card carries the number and the name. The button used to repeat both, so the
    # grid said every step name twice.
    if st.button(
        f"Open step {step.ordinal}",
        key=f"step_{step.step_id}",
        use_container_width=True,
        help=step.reason,
    ):
        st.session_state["pipeline_step"] = step.step_id
        st.rerun()
