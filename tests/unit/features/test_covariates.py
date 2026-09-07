"""Unit tests for covariate extraction and feature recomputation."""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from wha.db import apply_schema, connect
from wha.features import (
    compute_night,
    derive_exercise_offset,
    derive_prev_day_steps,
    derive_sleep_hours,
    nocturnal_window,
)


def test_missing_covariate_is_none_not_zero() -> None:
    """Missing step buckets, sleep stages, or workouts return None, never coerced to 0."""
    night = date(2026, 9, 2)
    w_start, w_end = nocturnal_window(night, "Asia/Singapore")

    steps = derive_prev_day_steps([], night, "Asia/Singapore")
    assert steps is None

    sleep = derive_sleep_hours([], w_start, w_end)
    assert sleep is None

    exercise = derive_exercise_offset([], w_start)
    assert exercise is None


def test_latest_exercise_session_wins() -> None:
    """When multiple workouts fall within the 6h lookback, the latest-ending session sets the offset."""
    # Window start is 2026-09-01 16:00:00 UTC
    w_start = datetime(2026, 9, 1, 16, 0, 0, tzinfo=UTC)

    sessions = [
        # Session 1: Ended 4 hours before window start (12:00 UTC)
        {"start_utc": "2026-09-01T11:00:00Z", "end_utc": "2026-09-01T12:00:00Z"},
        # Session 2: Ended 1.5 hours before window start (14:30 UTC)
        {"start_utc": "2026-09-01T13:30:00Z", "end_utc": "2026-09-01T14:30:00Z"},
    ]

    offset = derive_exercise_offset(sessions, w_start)
    assert offset == 1.5


def test_exercise_beyond_lookback_is_ignored() -> None:
    """Workouts ending >6 hours before window start are ignored (return None)."""
    w_start = datetime(2026, 9, 1, 16, 0, 0, tzinfo=UTC)

    sessions = [
        # Ended 7 hours before window start (09:00 UTC)
        {"start_utc": "2026-09-01T08:00:00Z", "end_utc": "2026-09-01T09:00:00Z"}
    ]

    offset = derive_exercise_offset(sessions, w_start)
    assert offset is None


def test_sleep_spanning_midnight_counts_only_window_portion() -> None:
    """Sleep stages starting before 00:00 count only the portion inside 00:00 to 07:00."""
    # Local window in Asia/Singapore is 16:00Z to 23:00Z (00:00 to 07:00 local)
    w_start = datetime(2026, 9, 1, 16, 0, 0, tzinfo=UTC)
    w_end = datetime(2026, 9, 1, 23, 0, 0, tzinfo=UTC)

    # Sleep started at 15:00Z (23:00 local) and ended at 22:00Z (06:00 local) -> 7h total, but 6h in window
    sleep_stages = [
        {"start_utc": "2026-09-01T15:00:00Z", "end_utc": "2026-09-01T22:00:00Z", "stage": "DEEP"}
    ]

    hours = derive_sleep_hours(sleep_stages, w_start, w_end)
    assert hours == 6.0


def test_recompute_is_idempotent(tmp_db_path: Path) -> None:
    """Recomputing features for a night produces identical rows and does not duplicate."""
    conn = connect(tmp_db_path)
    apply_schema(conn)

    # Insert subject
    conn.execute(
        """
        INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
        VALUES ('subj_cov', 'Subject Cov', 'synthetic', 'Asia/Singapore', '2026-09-01T00:00:00Z');
        """
    )
    # Insert 200 samples in window (2026-09-01 16:00Z to 23:00Z)
    w_start = datetime(2026, 9, 1, 16, 0, 0, tzinfo=UTC)
    for i in range(200):
        conn.execute(
            """
            INSERT INTO heart_rate_samples (subject_id, ts_utc, avg_bpm, min_bpm, max_bpm, origin)
            VALUES ('subj_cov', ?, 58.0, 56.0, 60.0, 'shealth');
            """,
            ((w_start + timedelta(minutes=i)).strftime("%Y-%m-%dT%H:%M:%SZ"),),
        )
    conn.commit()

    night = date(2026, 9, 2)
    f1 = compute_night(conn, "subj_cov", night)
    f2 = compute_night(conn, "subj_cov", night)

    assert f1.rhr_bpm == f2.rhr_bpm
    assert f1.coverage_minutes == f2.coverage_minutes
    assert f1.usable is True

    cursor = conn.execute("SELECT COUNT(*) FROM nightly_features WHERE subject_id = 'subj_cov';")
    count = cursor.fetchone()[0]
    assert count == 1

    conn.close()


def test_overlapping_sleep_records_are_merged_not_added() -> None:
    """A person cannot sleep two hours in one hour.

    Each stage's overlap with the window used to be added separately, so any minute covered
    by more than one record was counted more than once. A live database held nights
    reporting "42.9 h sleep", which is not merely wrong but impossible, and that figure
    reached a document written for a clinician.
    """
    from datetime import UTC, datetime

    from wha.features.covariates import derive_sleep_hours

    window_start = datetime(2026, 9, 1, 0, 0, tzinfo=UTC)
    window_end = datetime(2026, 9, 1, 7, 0, tzinfo=UTC)

    # Three records covering the same two hours, as a re-ingested night produces.
    duplicated = [
        {
            "start_utc": datetime(2026, 9, 1, 1, 0, tzinfo=UTC),
            "end_utc": datetime(2026, 9, 1, 3, 0, tzinfo=UTC),
            "stage": "DEEP",
        }
    ] * 3

    assert derive_sleep_hours(duplicated, window_start, window_end) == 2.0


def test_sleep_hours_can_never_exceed_the_window_it_was_measured_over() -> None:
    """Merging bounds the answer by construction, whatever the source data does."""
    from datetime import UTC, datetime, timedelta

    from wha.features.covariates import derive_sleep_hours

    window_start = datetime(2026, 9, 1, 0, 0, tzinfo=UTC)
    window_end = datetime(2026, 9, 1, 7, 0, tzinfo=UTC)

    # Fifty overlapping records, each spanning the whole window.
    piled_up = [
        {
            "start_utc": window_start - timedelta(hours=2),
            "end_utc": window_end + timedelta(hours=2),
            "stage": "LIGHT",
        }
        for _ in range(50)
    ]

    hours = derive_sleep_hours(piled_up, window_start, window_end)
    assert hours == 7.0


def test_separate_sleep_blocks_still_add_up() -> None:
    """Merging must not collapse genuinely separate stretches of sleep."""
    from datetime import UTC, datetime

    from wha.features.covariates import derive_sleep_hours

    window_start = datetime(2026, 9, 1, 0, 0, tzinfo=UTC)
    window_end = datetime(2026, 9, 1, 7, 0, tzinfo=UTC)

    blocks = [
        {
            "start_utc": datetime(2026, 9, 1, 0, 0, tzinfo=UTC),
            "end_utc": datetime(2026, 9, 1, 2, 0, tzinfo=UTC),
            "stage": "LIGHT",
        },
        {
            "start_utc": datetime(2026, 9, 1, 3, 0, tzinfo=UTC),
            "end_utc": datetime(2026, 9, 1, 6, 0, tzinfo=UTC),
            "stage": "DEEP",
        },
    ]

    assert derive_sleep_hours(blocks, window_start, window_end) == 5.0
