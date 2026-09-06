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
    fake_api.get_conversation_sessions.return_value = []


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
    fake_api.get_conversation_sessions.return_value = [
        {
            "started_utc": "2026-09-05T22:00:00+00:00",
            "turns": [
                {
                    "role": "user",
                    "text": "I feel tired",
                    "citations_json": "[]",
                    "uncited_json": "[]",
                },
                {
                    "role": "assistant",
                    "text": "Your last night was above your usual range.",
                    "citations_json": "[]",
                    "uncited_json": "[]",
                    "urgency": None,
                },
            ],
        }
    ]
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert not app.exception
    assert any("above your usual range" in m.value for m in app.markdown)


def test_an_uncited_sentence_is_flagged_and_the_flagging_is_not_promised_complete(
    fake_api,
) -> None:
    """The model sorts its own sentences, so an absence of warnings proves nothing."""
    _ready(fake_api)
    fake_api.get_conversation_sessions.return_value = [
        {
            "started_utc": "2026-09-05T22:00:00+00:00",
            "turns": [
                {
                    "role": "assistant",
                    "text": "That is reassuring.",
                    "citations_json": "[]",
                    "uncited_json": '["That is reassuring."]',
                }
            ],
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

    assert any("nothing is waiting for you" in s.value.lower() for s in app.success)


def test_the_reassurance_is_about_the_inbox_not_about_health(fake_api) -> None:
    """It sat directly above a RED night with an investigation running underneath it.

    "Nothing needs you right now" over a night the system judged clearly raised reads as a
    verdict on the person. The sentence describes what is waiting for them to answer.
    """
    _ready(fake_api, detail=_detail(level=DetectionLevel.RED))
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    said = " ".join(s.value.lower() for s in app.success)
    assert "waiting for you to answer" in said
    assert "nothing needs you" not in said


def test_one_control_opens_the_pipeline_not_two(fake_api) -> None:
    """Two buttons under different names opened the same night's steps.

    The verdict card's control and the investigation card's control both landed on the
    record screen for the same night whenever the investigation covered last night, which
    is the usual case.
    """
    from datetime import date

    from wha.models import EpisodeState, EpisodeSummary

    _ready(fake_api)
    fake_api.list_episodes.return_value = [
        EpisodeSummary(
            episode_id="ep_1",
            opened_on=NIGHT,
            state=EpisodeState.OPEN,
            night_span=(date(2026, 9, 3), NIGHT),
        )
    ]
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    openers = [b for b in app.button if "step" in b.label.lower()]
    assert len(openers) == 1, [b.label for b in openers]
    assert openers[0].label == "See every step of this night"


def test_the_investigation_says_which_nights_it_covers(fake_api) -> None:
    """What the verdict card cannot tell you is the span, so that is what replaced it."""
    from datetime import date

    from wha.models import EpisodeState, EpisodeSummary

    _ready(fake_api)
    fake_api.list_episodes.return_value = [
        EpisodeSummary(
            episode_id="ep_1",
            opened_on=NIGHT,
            state=EpisodeState.OPEN,
            night_span=(date(2026, 9, 3), NIGHT),
        )
    ]
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert "covers the nights of Thursday 3 September 2026 to Friday 4 September 2026" in _body(app)


def test_a_one_night_investigation_is_not_described_as_several(fake_api) -> None:
    """ "Every step of any of those nights" over a single night is simply wrong English."""
    from wha.models import EpisodeState, EpisodeSummary

    _ready(fake_api)
    fake_api.list_episodes.return_value = [
        EpisodeSummary(
            episode_id="ep_1",
            opened_on=NIGHT,
            state=EpisodeState.OPEN,
            night_span=(NIGHT, NIGHT),
        )
    ]
    app = AppTest.from_file(PAGE, default_timeout=30).run()
    body = _body(app)

    assert "is about the night of Friday 4 September 2026" in body
    assert "those nights" not in body


def test_today_shows_the_newest_measured_night_even_if_it_postdates_the_calendar(
    fake_api,
) -> None:
    """Found in simulation: a RED night existed and Today showed the green one before it.

    The screen asked for a window ending today, so a night dated tomorrow was excluded. It
    now asks for a number of nights and lets the application decide where the record ends.
    """
    _ready(fake_api)
    AppTest.from_file(PAGE, default_timeout=30).run()

    kwargs = fake_api.list_nights.call_args.kwargs
    assert "end" not in kwargs, "the screen is still deciding where the record ends"
    assert kwargs.get("days") == 7


def test_the_chat_starts_fresh_when_a_new_night_arrives(fake_api) -> None:
    """Reported by the user: the chat was not cleared for the new night.

    Six hours of silence is the agent's rule for ending a consultation. It is not the same
    boundary as a new night, and a question about Sunday under Monday's verdict reads as
    though it were about Monday.
    """
    _ready(fake_api)
    AppTest.from_file(PAGE, default_timeout=30).run()

    scoped = [
        c for c in fake_api.get_conversation_sessions.call_args_list if c.kwargs.get("since_night")
    ]
    assert scoped, "the chat asked for every conversation regardless of the night shown"
    assert scoped[0].kwargs["since_night"] == NIGHT


def test_only_the_current_conversation_is_shown(fake_api) -> None:
    """A question about Sunday sat under Monday's verdict and read as though it were
    about Monday. The agent already ends a consultation after a gap of several hours; the
    screen showed the last forty turns whatever night they came from.
    """
    _ready(fake_api)
    fake_api.get_conversation_sessions.return_value = [
        {
            "started_utc": "2026-09-05T22:00:00+00:00",
            "turns": [
                {
                    "role": "user",
                    "text": "tonight's question",
                    "citations_json": "[]",
                    "uncited_json": "[]",
                }
            ],
        },
        {
            "started_utc": "2026-09-01T09:00:00+00:00",
            "turns": [
                {
                    "role": "user",
                    "text": "a question from last week",
                    "citations_json": "[]",
                    "uncited_json": "[]",
                },
                {
                    "role": "agent",
                    "text": "an answer from last week",
                    "citations_json": "[]",
                    "uncited_json": "[]",
                },
            ],
        },
    ]
    app = AppTest.from_file(PAGE, default_timeout=30).run()
    body = _body(app)

    assert "tonight's question" in body
    assert "a question from last week" not in body
    assert "2 earlier turns are kept on the record screen" in body
    assert "conversation about this night" in body


def test_an_escalation_from_an_earlier_conversation_is_still_in_force(fake_api) -> None:
    """Urgency is monotone by design. Reading only the current session would drop it."""
    _ready(fake_api)
    fake_api.get_conversation_sessions.return_value = [
        {
            "started_utc": "2026-09-05T22:00:00+00:00",
            "turns": [
                {"role": "user", "text": "hello", "citations_json": "[]", "uncited_json": "[]"}
            ],
        },
        {
            "started_utc": "2026-09-01T09:00:00+00:00",
            "turns": [
                {
                    "role": "agent",
                    "text": "seek care",
                    "citations_json": "[]",
                    "uncited_json": "[]",
                    "urgency": "urgent",
                }
            ],
        },
    ]
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert not app.exception


def test_a_night_nobody_has_talked_about_says_so(fake_api) -> None:
    """ "This is your current conversation" over an empty one is not a sentence."""
    _ready(fake_api)
    fake_api.get_conversation_sessions.side_effect = lambda subject_id, since_night=None, **kw: (
        []
        if since_night
        else [
            {
                "started_utc": "2026-09-01T09:00:00+00:00",
                "turns": [
                    {
                        "role": "user",
                        "text": "an old question",
                        "citations_json": "[]",
                        "uncited_json": "[]",
                    }
                ],
            }
        ]
    )
    app = AppTest.from_file(PAGE, default_timeout=30).run()
    body = _body(app)

    assert "Nothing has been said about this night yet" in body
    assert "an old question" not in body


def test_a_raised_night_says_what_happens_now(fake_api) -> None:
    """RED with no next step read as a warning nobody could act on.

    A person seeing it asked whether they were ill and what they were meant to do. The
    card now says what the system is doing, what would change that, and that a colour is
    not a diagnosis.
    """
    from wha.ui import explain

    _ready(fake_api, detail=_detail(level=DetectionLevel.RED))
    app = AppTest.from_file(PAGE, default_timeout=30).run()
    body = _body(app) + " ".join(i.value for i in app.info)

    assert explain.text("level.RED.next") in body
    assert explain.text("level.not_a_diagnosis") in body


def test_a_night_under_investigation_says_that_instead(fake_api) -> None:
    """Telling somebody nothing is being looked into while it is would be worse."""
    from wha.ui import explain

    detail = _detail(level=DetectionLevel.RED)
    investigated = detail.model_copy(
        update={"row": detail.row.model_copy(update={"episode_id": "ep_1"})}
    )
    _ready(fake_api, detail=investigated)
    app = AppTest.from_file(PAGE, default_timeout=30).run()
    body = " ".join(i.value for i in app.info)

    assert explain.text("level.investigating") in body
    assert explain.text("level.RED.next") not in body


def test_an_answer_given_on_the_phone_shows_on_the_screen(fake_api) -> None:
    """Answering from Telegram recorded the answer and showed nothing in the dashboard.

    Somebody who replied on their phone and then opened Today saw the question gone, no
    chat, and no sign anywhere that what they said had arrived.
    """
    from datetime import UTC, datetime

    from wha.models import (
        EpisodeDetail,
        EpisodeState,
        EpisodeSummary,
        InteractionView,
    )

    _ready(fake_api)
    summary = EpisodeSummary(
        episode_id="ep_1",
        opened_on=NIGHT,
        state=EpisodeState.OPEN,
        night_span=(NIGHT, NIGHT),
    )
    fake_api.list_episodes.return_value = [summary]
    fake_api.get_episode.return_value = EpisodeDetail(
        summary=summary,
        interactions=[
            InteractionView(
                id="int_1",
                probe_id="probe_symptoms",
                question_text="Have you noticed any unusual symptoms today?",
                text_source="llm",
                options=[],
                evsi=0.417,
                interruption_cost=0.015,
                free_text="I feel a bit dizzy",
                status="ANSWERED",
                asked_at_utc=datetime(2026, 9, 6, 13, 42, tzinfo=UTC),
                answered_at_utc=datetime(2026, 9, 6, 13, 53, tzinfo=UTC),
            )
        ],
    )

    app = AppTest.from_file(PAGE, default_timeout=30).run()
    body = _body(app)

    assert "Have you noticed any unusual symptoms today?" in body
    assert "I feel a bit dizzy" in body
