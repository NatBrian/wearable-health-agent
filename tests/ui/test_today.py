"""Today, as the person meets it: what happened last night, and where it came from."""

from datetime import UTC, date, datetime

from streamlit.testing.v1 import AppTest

from tests.ui.conftest import page
from wha.models import (
    AnswerOption,
    Baseline,
    BaselineRung,
    CauseId,
    Detection,
    DetectionLevel,
    Forecast,
    NightDetail,
    NightlyFeatures,
    NightRow,
    PendingInteraction,
    Probe,
    Question,
)

PAGE = page("pages/1_Today.py")
NIGHT = date(2026, 9, 4)


def _row(level: DetectionLevel, rhr: float | None, window_source: str) -> NightRow:
    return NightRow(
        night_date=NIGHT,
        rhr_bpm=rhr,
        centre_bpm=45.0,
        band_lo=39.0,
        band_hi=51.0,
        deviation_bpm=7.0,
        explained_bpm=0.0,
        residual_bpm=7.0,
        coverage_minutes=331,
        usable=rhr is not None,
        level=level,
        rhr_window_source=window_source,
    )


def _detail(
    level: DetectionLevel = DetectionLevel.GREEN,
    rhr: float | None = 52.0,
    window_source: str = "sleep",
) -> NightDetail:
    return NightDetail(
        row=_row(level, rhr, window_source),
        features=NightlyFeatures(
            subject_id="sim",
            night_date=NIGHT,
            rhr_bpm=rhr,
            coverage_minutes=331,
            usable=rhr is not None,
            sleep_hours=6.9,
            rhr_window_source=window_source,
        ),
        baseline=Baseline(
            centre_bpm=45.0,
            scale_bpm=6.0,
            usable_nights=28,
            rung=BaselineRung.MATURE,
            shrink_weight=0.0,
        ),
        detection=Detection(
            subject_id="sim",
            night_date=NIGHT,
            deviation_bpm=7.0,
            level=level,
            flagged=level is DetectionLevel.RED,
            forecast=Forecast(),
        ),
    )


def _question() -> PendingInteraction:
    options = [
        AnswerOption(option_id="yes", label="Yes"),
        AnswerOption(option_id="no", label="No"),
    ]
    probe = Probe(
        probe_id="fever",
        target_cause=CauseId.INFECTION,
        answer_space=options,
        evsi=0.031,
        interruption_cost=0.015,
        fallback_text="Any illness symptoms yesterday?",
    )
    return PendingInteraction(
        kind="question",
        episode_id="ep_1",
        question=Question(
            probe=probe,
            text="Any illness symptoms yesterday?",
            text_source="llm",
            options=options,
            allows_free_text=True,
        ),
    )


def _ready(fake_api, detail: NightDetail | None = None, pending=None) -> None:
    fake_api.get_pending_interaction.return_value = pending
    fake_api.list_nights.return_value = [(detail or _detail()).row]
    fake_api.get_night_detail.return_value = detail or _detail()
    fake_api.list_episodes.return_value = []
    fake_api.get_transcript.return_value = []


def _body(app: AppTest) -> str:
    parts = [m.value for m in app.markdown]
    parts += [c.value for c in app.caption]
    parts += [s.value for s in app.subheader]
    parts += [i.value for i in app.info]
    parts += [s.value for s in app.success]
    parts += [w.value for w in app.warning]
    return " ".join(parts)


def test_the_page_renders_without_an_exception(fake_api) -> None:
    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert not app.exception


def test_a_pending_question_comes_before_last_night(fake_api) -> None:
    """Anything needing the person outranks anything reporting to them."""
    _ready(fake_api, pending=_question())
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    headings = [s.value for s in app.subheader]
    assert headings.index("One question for you") < headings.index("Last night")


def test_the_reassurance_is_never_drawn_while_something_is_pending(fake_api) -> None:
    """ "Nothing needs you" under a live question is the defect this ordering prevents."""
    _ready(fake_api, pending=_question())
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert not app.success


def test_a_person_whose_normal_is_not_yet_known_is_not_told_they_are_fine(fake_api) -> None:
    """Below the alerting floor nothing can be flagged, so reassurance is not earned."""
    status = fake_api.get_system_status.return_value
    fake_api.get_system_status.return_value = status.model_copy(
        update={"rung": BaselineRung.COLD, "usable_nights": 2}
    )
    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert not app.success
    assert "learning your normal" in _body(app).lower()


def test_the_verdict_shows_the_level_the_system_recorded(fake_api) -> None:
    """The screen and the record must use the same word for the same night."""
    _ready(fake_api, detail=_detail(level=DetectionLevel.RED))
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert "RED" in _body(app)


def test_every_number_on_the_verdict_card_has_an_explanation(fake_api) -> None:
    """A number with no explanation is the defect this rewrite exists to fix."""
    from wha.ui import explain

    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()
    body = _body(app)

    for key in ("metric.rhr", "metric.baseline", "metric.gap", "metric.coverage"):
        assert explain.text(key) in body, key


def test_a_night_measured_over_recorded_sleep_does_not_claim_otherwise(fake_api) -> None:
    """The old pages asserted the clock window on all 72 nights, wrongly on 44 of them."""
    _ready(fake_api, detail=_detail(window_source="sleep"))
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert "recorded no sleep" not in _body(app).lower()


def test_a_night_measured_over_the_clock_fallback_says_so(fake_api) -> None:
    _ready(fake_api, detail=_detail(window_source="clock"))
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert "recorded no sleep" in _body(app).lower()


def test_no_measured_night_is_missing_data_not_a_result(fake_api) -> None:
    """An empty screen and a healthy person must never look the same."""
    _ready(fake_api)
    fake_api.list_nights.return_value = [_row(DetectionLevel.NA, None, "clock")]
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert "missing data, not a result" in _body(app)


def test_the_doctor_summary_shows_what_it_will_copy(fake_api) -> None:
    """A copy control that sends something the person never saw is not consent."""
    _ready(fake_api)
    fake_api.build_handover.return_value = {
        "text": "SITUATION: raised resting heart rate over two nights."
    }
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    prepare = next(b for b in app.button if "Prepare" in b.label)
    prepare.click().run()

    assert any("SITUATION" in block.value for block in app.code)


def test_asking_a_question_sends_it_and_shows_the_stored_transcript(fake_api) -> None:
    """The reply is read back from the record, not rendered from the response."""
    _ready(fake_api)
    fake_api.get_transcript.return_value = [
        {"role": "user", "text": "I feel tired", "citations_json": "[]", "uncited_json": "[]"},
        {
            "role": "assistant",
            "text": "Your last night was above your usual range.",
            "citations_json": "[]",
            "uncited_json": "[]",
            "urgency": None,
        },
    ]
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert not app.exception
    assert any("above your usual range" in m.value for m in app.markdown)


def test_an_uncited_sentence_is_flagged_and_the_flagging_is_not_promised_complete(
    fake_api,
) -> None:
    """The model sorts its own sentences, so an absence of warnings proves nothing."""
    _ready(fake_api)
    fake_api.get_transcript.return_value = [
        {
            "role": "assistant",
            "text": "That is reassuring.",
            "citations_json": "[]",
            "uncited_json": '["That is reassuring."]',
        }
    ]
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert app.warning
    assert "not from a source" in app.warning[0].value.lower()
    assert "can miss things" in _body(app)


def test_the_timestamp_is_the_persons_own_clock(fake_api) -> None:
    """A UTC hour printed to somebody in Singapore is simply the wrong time."""
    _ready(fake_api)
    AppTest.from_file(PAGE, default_timeout=30).run()

    fake_api.localise.assert_called()
    assert isinstance(fake_api.localise.call_args[0][0], datetime | type(None))
    assert datetime.now(UTC).tzinfo is UTC


def test_no_quiet_streak_is_claimed_while_the_system_cannot_flag(fake_api) -> None:
    """A night can only be quiet if it could have been anything else.

    Below the alerting floor nothing can be flagged, so a streak claims reassurance the
    system is not in a position to give, directly above a notice saying it is not watching
    yet. `test_the_rung_the_screen_reads_marks_exactly_the_alerting_floor` ties the rung
    this reads to that floor.
    """
    status = fake_api.get_system_status.return_value
    fake_api.get_system_status.return_value = status.model_copy(
        update={"rung": BaselineRung.PRIOR_DOMINATED, "usable_nights": 4}
    )
    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert not app.success, "reassurance was drawn before the system could flag anything"
    assert "learning your normal" in _body(app).lower()


def test_a_quiet_streak_is_said_once_the_system_can_flag(fake_api) -> None:
    """The counterpart: silence must be about the system's position, not the screen's."""
    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert app.success
    assert "14 measured nights" in _body(app)


def test_an_empty_dashboard_says_nothing_is_required_of_you(fake_api) -> None:
    """A blank page and a working one that has nothing to say must not look the same."""
    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert any("nothing needs you" in s.value.lower() for s in app.success)
