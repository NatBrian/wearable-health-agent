"""The pipeline view: every step of one night, and an honest gap where nothing was recorded."""

from datetime import UTC, date, datetime

from streamlit.testing.v1 import AppTest

from tests.ui.conftest import page
from wha.models import (
    CANONICAL_PIPELINE_STEPS,
    DetectionLevel,
    NightPipeline,
    PipelineHeadline,
    PipelineNightRef,
    PipelineStepView,
    StepStatus,
)

PAGE = page("pages/3_The_record.py")
NIGHT = date(2026, 9, 4)


def _pipeline(
    overrides: dict[str, StepStatus] | None = None,
    figures: dict[str, str] | None = None,
    occurred: dict[str, datetime] | None = None,
) -> NightPipeline:
    statuses = overrides or {}
    return NightPipeline(
        subject_id="sim",
        night_date=NIGHT,
        episode_id="ep_1",
        headline=PipelineHeadline(
            level=DetectionLevel.RED,
            flagged=True,
            sleep_hours=6.9,
            coverage_minutes=331,
            questions_asked=1,
            sources_read=14,
        ),
        steps=[
            PipelineStepView(
                step_id=definition.step_id,
                ordinal=definition.ordinal,
                layer=definition.layer,
                status=statuses.get(definition.step_id, StepStatus.RAN),
                reason=f"reason for {definition.step_id}",
                headline_figure=(figures or {}).get(definition.step_id),
                occurred_utc=(occurred or {}).get(definition.step_id),
            )
            for definition in CANONICAL_PIPELINE_STEPS
        ],
    )


def _ready(fake_api, pipeline: NightPipeline | None = None) -> None:
    fake_api.list_pipeline_nights.return_value = [
        PipelineNightRef(night_date=NIGHT, level=DetectionLevel.RED, has_episode=True, usable=True)
    ]
    fake_api.get_night_pipeline.return_value = pipeline or _pipeline()
    fake_api.verify_hash_chain.return_value = (True, None)
    fake_api.count_audit_events.return_value = 0
    fake_api.list_plain_records.return_value = []
    fake_api.query_audit.return_value = []


def _body(app: AppTest) -> str:
    parts = [m.value for m in app.markdown]
    parts += [c.value for c in app.caption]
    parts += [i.value for i in app.info]
    parts += [w.value for w in app.warning]
    return " ".join(parts)


def test_the_page_renders_without_an_exception(fake_api) -> None:
    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert not app.exception


def test_every_step_the_service_returns_is_drawn(fake_api) -> None:
    """A step the page silently drops is a step nobody can audit."""
    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    labels = " ".join(b.label for b in app.button)
    cards = " ".join(m.value for m in app.markdown if "wha-step" in m.value)
    for definition in CANONICAL_PIPELINE_STEPS:
        assert f"Open step {definition.ordinal}" in labels, definition.step_id
        assert f"STEP {definition.ordinal}" in cards, definition.step_id


def test_a_step_that_did_not_run_shows_its_real_reason(fake_api) -> None:
    """ "Not needed" with the reason attached, never a blank card."""
    _ready(fake_api, _pipeline({"ask": StepStatus.SKIPPED}))
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    ask = next(b for b in app.button if b.label == "Open step 13")
    assert ask.proto.help == "reason for ask"


def test_an_unrecorded_step_does_not_claim_it_was_skipped(fake_api) -> None:
    """ "We did not write it down" and "it did not run" are different claims."""
    _ready(fake_api, _pipeline({"believe": StepStatus.UNRECORDED}))
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    believe = next(b for b in app.button if b.label == "Open step 11")
    believe.click().run()
    body = _body(app).lower()

    assert "not recorded" in body
    assert "gap in the record" in body


def test_clicking_a_step_opens_its_detail(fake_api) -> None:
    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    believe = next(b for b in app.button if b.label == "Open step 11")
    believe.click().run()

    assert app.session_state["pipeline_step"] == "believe"
    assert "Why this step exists" in _body(app)


def test_no_step_shows_a_time_the_pipeline_did_not_carry(fake_api) -> None:
    """Every step in this fixture has no recorded time, so no clock time may appear."""
    import re

    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    cards = " ".join(m.value for m in app.markdown if "wha-step" in m.value)
    assert cards, "no step cards rendered"
    assert not re.search(r"\b\d{2}:\d{2}\b", cards)


def test_a_recorded_time_is_shown_when_there_is_one(fake_api) -> None:
    """The counterpart to the test above: silence must be about the data, not the screen."""
    moment = datetime(2026, 9, 4, 2, 13, tzinfo=UTC)
    _ready(fake_api, _pipeline(occurred={"features": moment}))
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    cards = " ".join(m.value for m in app.markdown if "wha-step" in m.value)
    assert "02:13" in cards


def test_the_safety_floor_is_drawn_even_when_it_did_not_trigger(fake_api) -> None:
    """It runs on anything you type. Hiding it teaches the opposite."""
    _ready(fake_api, _pipeline({"safety_phrase_rules": StepStatus.NOT_APPLICABLE}))
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    cards = " ".join(m.value for m in app.markdown if "wha-step" in m.value)
    assert "Phrase rules" in cards
    assert "Always on" in _body(app)


def test_every_step_id_has_copy() -> None:
    """A step cannot ship unexplained."""
    from wha.ui import explain
    from wha.ui.components.pipeline_graph import STEP_NAMES

    for definition in CANONICAL_PIPELINE_STEPS:
        assert explain.step(definition.step_id, "what")
        assert explain.step(definition.step_id, "why")
        assert definition.step_id in STEP_NAMES


def test_a_night_that_cannot_be_loaded_is_not_reported_as_an_empty_night(fake_api) -> None:
    """A failed fetch and a quiet night must never look the same in a health record."""
    _ready(fake_api)
    fake_api.get_night_pipeline.side_effect = RuntimeError("connection refused")
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert app.error
    assert "not a statement that nothing happened" in app.error[0].value


def test_the_stepper_opens_on_a_night_there_is_something_to_explain(fake_api) -> None:
    """The most recent night is often one the watch did not measure.

    Opening on it showed twenty steps reading "did not run" to somebody who came here to
    find out what happened.
    """
    unmeasured = date(2026, 9, 6)
    _ready(fake_api)
    fake_api.list_pipeline_nights.return_value = [
        PipelineNightRef(
            night_date=unmeasured, level=DetectionLevel.NA, has_episode=False, usable=False
        ),
        PipelineNightRef(night_date=NIGHT, level=DetectionLevel.RED, has_episode=True, usable=True),
    ]

    AppTest.from_file(PAGE, default_timeout=30).run()

    fake_api.get_night_pipeline.assert_called_with("sim", NIGHT)


def test_a_window_with_no_measured_night_still_opens_something(fake_api) -> None:
    """The counterpart: preferring a measured night must not mean showing nothing."""
    unmeasured = date(2026, 9, 6)
    _ready(fake_api)
    fake_api.list_pipeline_nights.return_value = [
        PipelineNightRef(
            night_date=unmeasured, level=DetectionLevel.NA, has_episode=False, usable=False
        )
    ]

    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert not app.exception
    fake_api.get_night_pipeline.assert_called_with("sim", unmeasured)


def test_the_sleep_tile_explains_the_number_it_is_showing(fake_api) -> None:
    """The tile showed hours slept and the note explained minutes measured, which is a
    different number: ten hours of sleep beside a note about 453 minutes of coverage.
    """
    from wha.ui import explain

    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    tiles = " ".join(m.value for m in app.markdown if "wha-tile" in m.value)
    start = tiles.index('<div class="label">Your sleep</div>')
    sleep_tile = tiles[start : start + 700]

    assert explain.text("metric.sleep_hours")[:40] in sleep_tile
    assert "331 minutes" in sleep_tile, "the coverage it does mention should be named as such"
