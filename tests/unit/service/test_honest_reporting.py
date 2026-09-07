"""What the system tells the person has to be true.

Four separate places said something reassuring that the data did not support: nights with
no reading counted as quiet ones, a three-night baseline was described as the person's own
usual range, the chart caption promised an investigation for nights below the band, and an
empty audit log reported itself intact.
"""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from wha.db import connect
from wha.db.iso import to_iso
from wha.db.migrations import apply_schema
from wha.models import BaselineRung, DetectionLevel
from wha.service.audit import count_audit_events, verify_hash_chain
from wha.service.status import get_system_status
from wha.ui.explain import level as level_phrase


def _db_with_detections(tmp_path: Path, levels: list[tuple[date, str, int]]) -> Path:
    db_file = tmp_path / "honest.db"
    conn = connect(db_file)
    apply_schema(conn)
    conn.execute(
        """INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
           VALUES ('me', 'me', 'live', 'Asia/Singapore', ?)""",
        (to_iso(datetime.now(UTC)),),
    )
    for night, level, flagged in levels:
        conn.execute(
            """INSERT INTO detections
                 (subject_id, night_date, level, flagged, explained_bpm, forecast_status,
                  reasons_json)
               VALUES ('me', ?, ?, ?, 0.0, 'NOT_RUN', '[]')""",
            (night.isoformat(), level, flagged),
        )
    conn.commit()
    conn.close()
    return db_file


# -- nights nobody measured are not quiet nights -------------------------------------


def test_nights_with_no_reading_do_not_count_toward_the_quiet_streak(tmp_path: Path) -> None:
    """The real case: 3 nights of data out of 7, reported as "7 quiet nights in a row"."""
    base = date(2026, 9, 3)
    rows = [
        (base - timedelta(days=0), "NA", 0),
        (base - timedelta(days=1), "GREEN", 0),
        (base - timedelta(days=2), "GREEN", 0),
        (base - timedelta(days=3), "GREEN", 0),
        (base - timedelta(days=4), "NA", 0),
        (base - timedelta(days=5), "NA", 0),
        (base - timedelta(days=6), "NA", 0),
    ]
    db_file = _db_with_detections(tmp_path, rows)

    status = get_system_status("me", db_path=db_file)

    assert status.quiet_nights_streak == 0, "the most recent night had no reading at all"
    assert status.unmeasured_recent_nights == 4


def test_a_run_of_measured_clear_nights_still_counts(tmp_path: Path) -> None:
    base = date(2026, 9, 3)
    rows = [(base - timedelta(days=n), "GREEN", 0) for n in range(5)]
    db_file = _db_with_detections(tmp_path, rows)

    status = get_system_status("me", db_path=db_file)

    assert status.quiet_nights_streak == 5
    assert status.unmeasured_recent_nights == 0


def test_a_flagged_night_ends_the_streak(tmp_path: Path) -> None:
    base = date(2026, 9, 3)
    rows = [
        (base, "GREEN", 0),
        (base - timedelta(days=1), "RED", 1),
        (base - timedelta(days=2), "GREEN", 0),
    ]
    db_file = _db_with_detections(tmp_path, rows)

    assert get_system_status("me", db_path=db_file).quiet_nights_streak == 1


# -- "your usual range" is a claim that has to be earned -----------------------------


def test_an_immature_baseline_does_not_claim_a_personal_range() -> None:
    """Today said "in your usual range" under a tile reading "baseline: Learning"."""
    for rung in (BaselineRung.COLD, BaselineRung.PRIOR_DOMINATED):
        sentence = level_phrase(DetectionLevel.GREEN.value, rung=rung.value)
        assert "your usual range" not in sentence
        assert "typical adult" in sentence


def test_a_mature_baseline_keeps_the_personal_wording() -> None:
    for rung in (BaselineRung.SHRINKING, BaselineRung.PERSONAL, BaselineRung.MATURE):
        sentence = level_phrase(DetectionLevel.GREEN.value, rung=rung.value)
        assert "your usual range" in sentence


def test_a_night_with_no_reading_is_worded_the_same_either_way() -> None:
    """ "Not enough data" makes no claim about a range, so it needs no qualification."""
    cold = level_phrase(DetectionLevel.NA.value, rung=BaselineRung.COLD.value)
    mature = level_phrase(DetectionLevel.NA.value, rung=BaselineRung.MATURE.value)
    assert cold == mature


def test_omitting_the_rung_leaves_the_wording_untouched() -> None:
    assert level_phrase(DetectionLevel.GREEN.value) == (
        level_phrase(DetectionLevel.GREEN.value, rung=BaselineRung.MATURE.value)
    )


# -- an empty record is not a verified one -------------------------------------------


def test_an_empty_audit_log_verifies_but_holds_nothing(tmp_path: Path) -> None:
    """verify_hash_chain returns intact for zero entries, so callers must ask the count."""
    db_file = tmp_path / "empty_audit.db"
    conn = connect(db_file)
    apply_schema(conn)

    intact, bad = verify_hash_chain("me", conn=conn)
    count = count_audit_events("me", conn=conn)
    conn.close()

    assert intact is True
    assert bad is None
    assert count == 0, "the page must be able to tell 'intact' from 'nothing recorded'"


def test_the_rung_the_screen_reads_marks_exactly_the_alerting_floor() -> None:
    """The screen suppresses reassurance below PRIOR_DOMINATED. That has to mean the floor.

    Today used to check `usable_nights < BASELINE_MIN_NIGHTS_PERSONAL` directly. It now
    reads the rung, which is the same boundary only for as long as the ladder puts it
    there, and a night can only be called quiet if it could have been anything else.
    """
    from wha.constants import (
        BASELINE_MIN_NIGHTS_PERSONAL,
        RUNG_PRIOR_MAX_NIGHTS,
    )

    assert RUNG_PRIOR_MAX_NIGHTS + 1 == BASELINE_MIN_NIGHTS_PERSONAL
