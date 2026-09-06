"""The night pipeline: every step of the journey, for every night, or an honest gap."""

import json
from datetime import UTC, date, datetime, timedelta

import pytest

from wha.db import connect
from wha.db.audit_chain import append_audit
from wha.db.migrations import apply_schema
from wha.models import (
    CANONICAL_PIPELINE_STEPS,
    AuditEvent,
    CauseId,
    DetectionLevel,
    PipelineStepView,
    StepLayer,
    StepStatus,
)

MEASURED = date(2026, 8, 1)
UNMEASURED = date(2026, 7, 4)
FLAGGED = date(2026, 8, 2)
FEATURES_COMPUTED_AT = "2026-08-01T02:13:00+00:00"
INGESTED_AT = "2026-08-01T01:12:00+00:00"


@pytest.fixture
def seeded_db():
    """One measured night, one night the watch never reported, and nothing else.

    Built by hand rather than through the ingest path so a test can state exactly which
    rows exist. The two nights are the two cases the pipeline has to tell apart: a night
    that was measured and found unremarkable, and a night with no reading at all.
    """
    conn = connect(":memory:")
    apply_schema(conn)

    conn.execute(
        "INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc) "
        "VALUES ('sim', 'Simulated', 'synthetic', 'Asia/Singapore', '2026-07-01T00:00:00+00:00')"
    )

    # Asia/Singapore is UTC+8, so local 01:00-07:00 on 1 August is 17:00-23:00 UTC on
    # 31 July. Every timestamp below is UTC, as every timestamp in the database is.
    sleep_start = datetime(2026, 7, 31, 17, 0, tzinfo=UTC)
    sleep_end = datetime(2026, 7, 31, 23, 0, tzinfo=UTC)
    conn.execute(
        "INSERT INTO sleep_stages (subject_id, start_utc, end_utc, stage) VALUES (?, ?, ?, ?)",
        ("sim", sleep_start.isoformat(), sleep_end.isoformat(), "DEEP"),
    )

    moment = sleep_start
    while moment < sleep_end:
        conn.execute(
            "INSERT INTO heart_rate_samples (subject_id, ts_utc, avg_bpm) VALUES (?, ?, ?)",
            ("sim", moment.isoformat(), 46.0),
        )
        moment += timedelta(minutes=5)

    conn.execute(
        "INSERT INTO raw_payloads (subject_id, fetched_at_utc, source_kind, sha256, payload_json) "
        "VALUES ('sim', ?, 'bridge', 'abc123', '{}')",
        (INGESTED_AT,),
    )

    conn.execute(
        """INSERT INTO nightly_features
           (subject_id, night_date, rhr_bpm, coverage_minutes, implausible_dropped, usable,
            steps_prev_day, sleep_hours, exercise_end_offset_h, rhr_window_source, computed_at_utc)
           VALUES ('sim', ?, 46.0, 340, 0, 1, 8200, 6.0, NULL, 'sleep', ?)""",
        (MEASURED.isoformat(), FEATURES_COMPUTED_AT),
    )
    conn.execute(
        """INSERT INTO baselines
           (subject_id, night_date, centre_bpm, scale_bpm, usable_nights, rung, shrink_weight)
           VALUES ('sim', ?, 45.0, 3.7, 28, 'MATURE', 0.0)""",
        (MEASURED.isoformat(),),
    )
    conn.execute(
        """INSERT INTO detections
           (subject_id, night_date, deviation_bpm, robust_z, explained_bpm, residual_bpm,
            level, flagged, reasons_json)
           VALUES ('sim', ?, 1.0, 0.27, 0.0, 1.0, 'GREEN', 0, ?)""",
        (MEASURED.isoformat(), json.dumps(["within your usual range"])),
    )

    # Written through the real appender so the row carries a valid chain hash. A raw
    # INSERT here would seed a record that the integrity check reports as tampered.
    append_audit(
        conn,
        AuditEvent(
            event_id="evt_ingest",
            subject_id="sim",
            timestamp_utc=datetime.fromisoformat(INGESTED_AT),
            actor="system",
            operation="ingest",
        ),
    )
    conn.commit()
    return conn


def _add_flagged_night(conn, night: date) -> None:
    """A second night, this one raised enough to be worth looking into."""
    conn.execute(
        """INSERT INTO nightly_features
           (subject_id, night_date, rhr_bpm, coverage_minutes, implausible_dropped, usable,
            steps_prev_day, sleep_hours, exercise_end_offset_h, rhr_window_source, computed_at_utc)
           VALUES ('sim', ?, 53.0, 320, 0, 1, 6100, 5.5, NULL, 'sleep', ?)""",
        (night.isoformat(), FEATURES_COMPUTED_AT),
    )
    conn.execute(
        """INSERT INTO baselines
           (subject_id, night_date, centre_bpm, scale_bpm, usable_nights, rung, shrink_weight)
           VALUES ('sim', ?, 45.0, 3.7, 28, 'MATURE', 0.0)""",
        (night.isoformat(),),
    )
    conn.execute(
        """INSERT INTO detections
           (subject_id, night_date, deviation_bpm, robust_z, explained_bpm, residual_bpm,
            level, flagged, reasons_json)
           VALUES ('sim', ?, 8.0, 2.16, 0.0, 8.0, 'RED', 1, ?)""",
        (night.isoformat(), json.dumps(["8.0 bpm above your normal", "second raised night"])),
    )


def _add_episode(conn, night: date, *, with_trace: bool) -> str:
    """An investigation over that night, with or without the trace the graph writes."""
    episode_id = "ep_test"
    conn.execute(
        """INSERT INTO episodes
           (episode_id, subject_id, thread_id, opened_on, closed_on, state, disposition,
            baseline_nights, baseline_rung, step_count, tool_call_count, depth_used)
           VALUES (?, 'sim', 'thread_test', ?, NULL, 'AWAITING_USER', NULL, 28, 'MATURE', 5, 6, 2)""",
        (episode_id, night.isoformat()),
    )
    conn.execute(
        """INSERT INTO beliefs (episode_id, seq, ts_utc, trigger, marginals_json, p_illness)
           VALUES (?, 1, ?, 'night', ?, 0.42)""",
        (
            episode_id,
            FEATURES_COMPUTED_AT,
            json.dumps({"infection": 0.42, "exertion": 0.11, "sensor_artifact": 0.07}),
        ),
    )
    conn.execute(
        """INSERT INTO interactions
           (id, episode_id, probe_id, question_text, text_source, options_json, evsi,
            interruption_cost, rejected_json, answer_option_id, channel, asked_at_utc,
            answered_at_utc, status)
           VALUES ('int_1', ?, 'fever', 'Any illness symptoms yesterday?', 'llm', ?, 0.031,
                   0.015, '[]', 'no', 'telegram', ?, ?, 'ANSWERED')""",
        (
            episode_id,
            json.dumps([{"option_id": "yes", "label": "Yes"}, {"option_id": "no", "label": "No"}]),
            FEATURES_COMPUTED_AT,
            FEATURES_COMPUTED_AT,
        ),
    )

    if with_trace:
        conn.execute(
            """INSERT INTO episode_traces (episode_id, payload_json, updated_at_utc)
               VALUES (?, ?, ?)""",
            (
                episode_id,
                json.dumps(
                    {
                        "nodes_ran": [
                            "preload",
                            "investigate",
                            "believe",
                            "decide",
                            "ask",
                            "conclude",
                        ],
                        "tool_calls": [{"tool_name": "retrieve_clinical_evidence", "ok": True}],
                        "tool_call_count": 6,
                        "questions_asked": 1,
                        "stripped_claims": ["one claim with no source"],
                    }
                ),
                FEATURES_COMPUTED_AT,
            ),
        )
    conn.commit()
    return episode_id


@pytest.fixture
def seeded_db_with_episode(seeded_db):
    """A flagged night that opened an investigation, and the trace the graph wrote."""
    _add_flagged_night(seeded_db, FLAGGED)
    _add_episode(seeded_db, FLAGGED, with_trace=True)
    return seeded_db


@pytest.fixture
def seeded_db_with_untraced_episode(seeded_db):
    """The same investigation, from before the system recorded which nodes ran."""
    _add_flagged_night(seeded_db, FLAGGED)
    _add_episode(seeded_db, FLAGGED, with_trace=False)
    return seeded_db


def test_the_canonical_steps_are_ordered_and_unique() -> None:
    """The order on screen is the order the system ran, and no id appears twice."""
    ordinals = [s.ordinal for s in CANONICAL_PIPELINE_STEPS]
    ids = [s.step_id for s in CANONICAL_PIPELINE_STEPS]
    assert ordinals == sorted(ordinals)
    assert len(set(ids)) == len(ids)


def test_the_agentic_ids_match_the_stage_names_the_agent_already_uses() -> None:
    """Two vocabularies for one pipeline is how a screen comes to contradict the record.

    The agent's own stage names are the ones written into `episode_traces`. If the screen
    invented a second set, a step could be drawn as skipped while the record it was built
    from said it ran.
    """
    from wha.service.episodes import CANONICAL_STAGES

    step_ids = {s.step_id for s in CANONICAL_PIPELINE_STEPS}
    for name, _description in CANONICAL_STAGES:
        assert name in step_ids, f"agent stage {name} has no pipeline step"


def test_a_step_view_needs_nothing_it_cannot_know() -> None:
    """A step with no recorded time and no headline figure is a legal step.

    Making either mandatory would force a caller to invent one, which is the failure this
    whole module exists to avoid.
    """
    step = PipelineStepView(
        step_id="detect",
        ordinal=7,
        layer=StepLayer.DETERMINISTIC,
        status=StepStatus.RAN,
        reason="Compared the reading against your own band.",
    )
    assert step.occurred_utc is None
    assert step.headline_figure is None


def test_a_quiet_night_still_has_the_first_seven_steps(seeded_db) -> None:
    """The screen exists to explain every night, not only the alarming ones.

    Sixty-eight of seventy-two nights in the sample opened no investigation. If those
    nights render as an empty page, the page says nothing on the nights the person is
    most likely to look at it.
    """
    from wha.service.pipeline import get_night_pipeline

    pipeline = get_night_pipeline("sim", MEASURED, conn=seeded_db)

    deterministic = [s for s in pipeline.steps if s.layer == StepLayer.DETERMINISTIC]
    assert [s.step_id for s in deterministic] == [
        "collect",
        "store",
        "sleep_window",
        "features",
        "baseline",
        "subtract_explained",
        "detect",
    ]
    ran_or_not_applicable = {StepStatus.RAN, StepStatus.NOT_APPLICABLE}
    assert all(s.status in ran_or_not_applicable for s in deterministic)


def test_the_step_that_found_the_sleep_window_says_which_window_it_used(seeded_db) -> None:
    """The page must not assert "because no sleep was recorded" on a night that recorded it.

    `rhr_window_source` reached NightlyFeatures and not NightRow, so both pages read it
    with a default of "clock" and stated the wrong thing on 44 of 72 nights.
    """
    from wha.service.pipeline import get_night_pipeline

    pipeline = get_night_pipeline("sim", MEASURED, conn=seeded_db)
    window = next(s for s in pipeline.steps if s.step_id == "sleep_window")

    assert window.outputs["window_source"] == "sleep"


def test_no_step_carries_a_timestamp_the_database_does_not_hold(seeded_db) -> None:
    """A clock time nobody recorded is an invented number, which this project does not add."""
    from wha.service.pipeline import get_night_pipeline

    recorded = {FEATURES_COMPUTED_AT, INGESTED_AT}
    pipeline = get_night_pipeline("sim", MEASURED, conn=seeded_db)

    for step in pipeline.steps:
        if step.occurred_utc is not None:
            assert step.occurred_utc.isoformat() in recorded, step.step_id


def test_a_night_with_no_reading_says_so_rather_than_reporting_a_number(seeded_db) -> None:
    """A missing night is missing data, never a quiet night."""
    from wha.service.pipeline import get_night_pipeline

    pipeline = get_night_pipeline("sim", UNMEASURED, conn=seeded_db)
    features = next(s for s in pipeline.steps if s.step_id == "features")

    assert features.status in {StepStatus.SKIPPED, StepStatus.UNRECORDED}
    assert features.headline_figure is None


def test_the_night_list_covers_every_calendar_night_in_the_window(seeded_db) -> None:
    """Including the nights with nothing in them, which are the ones worth noticing."""
    from wha.service.pipeline import list_pipeline_nights

    refs = list_pipeline_nights("sim", days=30, conn=seeded_db)

    assert len(refs) == 31
    assert [r.night_date for r in refs] == sorted(r.night_date for r in refs)


def test_a_quiet_night_explains_why_no_investigation_opened(seeded_db) -> None:
    """Silence has a reason, and the reason is the interesting part.

    A page that renders nothing on a quiet night teaches the person that the system only
    works when something is wrong, which is the opposite of what it does.
    """
    from wha.service.pipeline import get_night_pipeline

    pipeline = get_night_pipeline("sim", MEASURED, conn=seeded_db)
    opened = next(s for s in pipeline.steps if s.step_id == "episode_open")

    assert opened.status == StepStatus.NOT_APPLICABLE
    assert opened.reason
    assert pipeline.episode_id is None

    later = [
        s
        for s in pipeline.steps
        if s.ordinal > 8 and s.layer in {StepLayer.AGENTIC, StepLayer.USER}
    ]
    assert all(s.status == StepStatus.NOT_APPLICABLE for s in later)


def test_an_investigated_night_carries_every_step(seeded_db_with_episode) -> None:
    """All twenty, in order, so nothing about the night is off screen."""
    from wha.service.pipeline import get_night_pipeline

    pipeline = get_night_pipeline("sim", FLAGGED, conn=seeded_db_with_episode)

    assert pipeline.episode_id == "ep_test"
    assert [s.ordinal for s in pipeline.steps] == list(range(1, 21))

    believe = next(s for s in pipeline.steps if s.step_id == "believe")
    assert believe.status == StepStatus.RAN
    assert believe.outputs["top_cause"] == "infection"


def test_a_step_the_graph_did_not_reach_is_skipped_with_its_reason(
    seeded_db_with_episode,
) -> None:
    """`critique` and `review` run after the trace is written and record themselves.

    This episode never reached them, so they are reported as not yet reached rather than
    as having been declined.
    """
    from wha.service.pipeline import get_night_pipeline

    pipeline = get_night_pipeline("sim", FLAGGED, conn=seeded_db_with_episode)
    review = next(s for s in pipeline.steps if s.step_id == "review")

    assert review.status == StepStatus.SKIPPED
    assert review.reason


def test_an_episode_with_no_stored_trace_is_unrecorded_not_skipped(
    seeded_db_with_untraced_episode,
) -> None:
    """ "We did not write it down" and "it did not run" are different claims.

    Reporting the first as the second is what made every episode's trace read "Ask probe
    not selected by EVSI optimizer" directly above a chart showing the probability moving
    because a question had been answered.
    """
    from wha.service.pipeline import get_night_pipeline

    pipeline = get_night_pipeline("sim", FLAGGED, conn=seeded_db_with_untraced_episode)
    agentic = [
        s for s in pipeline.steps if s.layer == StepLayer.AGENTIC and s.step_id != "episode_open"
    ]

    assert agentic
    assert all(s.status == StepStatus.UNRECORDED for s in agentic)


def test_the_headline_counts_what_actually_happened(seeded_db_with_episode) -> None:
    """Every tile is assembled from stored rows, so none of them can be a guess."""
    from wha.service.pipeline import get_night_pipeline

    pipeline = get_night_pipeline("sim", FLAGGED, conn=seeded_db_with_episode)
    head = pipeline.headline

    assert head.level == DetectionLevel.RED
    assert head.flagged is True
    assert head.questions_asked == 1
    assert head.primary_cause == CauseId.INFECTION
    assert head.primary_probability == 0.42
    assert head.sources_read == len({c.source_id for s in pipeline.steps for c in s.sources})


def test_the_safety_floor_is_shown_even_when_it_did_not_trigger(seeded_db) -> None:
    """The floor runs on anything the person types, not only on flagged nights.

    Hiding it when it stayed quiet would teach the person it only exists during an
    investigation, which is exactly the opposite of what it is for.
    """
    from wha.service.pipeline import get_night_pipeline

    pipeline = get_night_pipeline("sim", MEASURED, conn=seeded_db)
    safety = [s for s in pipeline.steps if s.layer == StepLayer.SAFETY]

    assert [s.step_id for s in safety] == ["safety_phrase_rules", "safety_triage"]
    assert all(s.reason for s in safety)
