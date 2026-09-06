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
    PipelineStepView,
    StepLayer,
    StepStatus,
)

MEASURED = date(2026, 8, 1)
UNMEASURED = date(2026, 7, 4)
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
