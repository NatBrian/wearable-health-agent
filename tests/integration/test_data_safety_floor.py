"""The safety floor must fire on the data, not only on what the person types.

Three rules were written, tested on their own, and connected to nothing. Line coverage over
a full production run showed `src/wha/safety/rules.py` lines 162 to 178 and 253 to 266
never executing:

- `check_overnight_oxygen` had no caller anywhere, in `src/` or in `tests/`.
- The two extreme heart rate rules need `robust_z`, and all three places that ran the
  safety check passed only free text, so the number was always `None` and the branch was
  always skipped.

A night far outside your own range therefore raised nothing at all unless you
independently typed a warning phrase. A floor that only fires on what you say is not a
floor on your data.

These tests run `run_nightly`, the real job the scheduler calls, and read what came out.
A unit test on `check_red_flags_deterministic` would have passed throughout.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from wha.db import connect
from wha.db.iso import to_iso
from wha.db.migrations import apply_schema
from wha.service.nightly import run_nightly

SUBJECT = "me"
FIRST = date(2026, 8, 1)


def _make_db(tmp_path: Path, nights: list[float], oxygen: list[float] | None = None) -> Path:
    """A subject with `nights` of overnight readings, one per day from FIRST."""
    db_file = tmp_path / "floor.db"
    conn = connect(db_file)
    apply_schema(conn)
    conn.execute(
        """INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
           VALUES (?, 'me', 'synthetic', 'Asia/Singapore', ?)""",
        (SUBJECT, to_iso(datetime(2026, 7, 1, tzinfo=UTC))),
    )
    for offset, rhr in enumerate(nights):
        night = FIRST + timedelta(days=offset)
        conn.execute(
            """INSERT INTO nightly_features
                 (subject_id, night_date, rhr_bpm, coverage_minutes, usable, computed_at_utc)
               VALUES (?, ?, ?, 420, 1, ?)""",
            (SUBJECT, night.isoformat(), rhr, f"{night.isoformat()}T08:00:00+00:00"),
        )
    if oxygen:
        last = FIRST + timedelta(days=len(nights) - 1)
        # Inside the clock fallback window for that night, which is local 00:00 to 07:00.
        base = datetime(last.year, last.month, last.day, 0, 0, tzinfo=UTC) - timedelta(hours=8)
        for index, percentage in enumerate(oxygen):
            conn.execute(
                """INSERT INTO oxygen_saturation_samples
                     (subject_id, ts_utc, percentage, origin)
                   VALUES (?, ?, ?, 'device')""",
                (SUBJECT, to_iso(base + timedelta(minutes=10 * index)), percentage),
            )
    conn.commit()
    conn.close()
    return db_file


def _events(db_file: Path, safety_event: str) -> list[dict]:
    conn = connect(db_file)
    try:
        return [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM audit_events WHERE safety_event = ? ORDER BY rowid",
                (safety_event,),
            ).fetchall()
        ]
    finally:
        conn.close()


def _episodes(db_file: Path) -> list[dict]:
    conn = connect(db_file)
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM episodes ORDER BY rowid").fetchall()]
    finally:
        conn.close()


def test_a_steady_person_is_left_alone(tmp_path: Path) -> None:
    """The control. Twenty ordinary nights must raise nothing at all."""
    readings = [60.0, 61.0, 59.0, 60.0, 62.0, 58.0, 61.0, 60.0, 59.0, 61.0] * 2
    db_file = _make_db(tmp_path, readings)

    run_nightly(SUBJECT, f"{FIRST.isoformat()}:{(FIRST + timedelta(days=19)).isoformat()}", db_file)

    assert _events(db_file, "red_flag_vitals") == []
    assert _episodes(db_file) == []


def test_a_night_far_outside_your_own_range_escalates_with_nobody_typing_anything(
    tmp_path: Path,
) -> None:
    """The defect. This rule had never executed in production.

    Nothing is reported, nothing is typed. The night itself is the input.
    """
    # Nineteen steady nights, then one a long way above them.
    readings = [60.0, 61.0, 59.0, 60.0, 62.0, 58.0, 61.0, 60.0, 59.0, 61.0] * 2
    readings[-1] = 95.0
    db_file = _make_db(tmp_path, readings)

    last = FIRST + timedelta(days=19)
    run_nightly(SUBJECT, f"{FIRST.isoformat()}:{last.isoformat()}", db_file)

    fired = _events(db_file, "red_flag_vitals")
    assert fired, "a night 35 bpm above this person's own median raised nothing"

    conn = connect(db_file)
    try:
        detection = conn.execute(
            "SELECT robust_z FROM detections WHERE subject_id = ? AND night_date = ?",
            (SUBJECT, last.isoformat()),
        ).fetchone()
    finally:
        conn.close()
    assert detection["robust_z"] > 6.0, "the rule fired on something other than the z rule"

    # It opens an investigation, so the escalation is on the record rather than only in a
    # notification that may or may not have been delivered.
    assert _episodes(db_file), "the escalation raised no episode"


def test_the_reading_the_rule_sees_is_the_reading_and_not_the_deviation(
    tmp_path: Path,
) -> None:
    """The cold-rung fallback compares an absolute bpm, so it needs the absolute bpm.

    Passing `deviation_bpm` would compare a five beat rise against a hundred beat bound and
    silently never fire, which is the same shape of defect this whole item is about.
    """
    # Three nights only, so the baseline is COLD and the fallback branch is the live one.
    db_file = _make_db(tmp_path, [110.0, 112.0, 115.0])

    run_nightly(SUBJECT, f"{FIRST.isoformat()}:{(FIRST + timedelta(days=2)).isoformat()}", db_file)

    fired = _events(db_file, "red_flag_vitals")
    assert fired, "a cold-rung night above 100 bpm did not reach the fallback bound"


def test_blood_oxygen_is_judged_over_the_night(tmp_path: Path) -> None:
    """`check_overnight_oxygen` had no caller anywhere in src/ or tests/."""
    readings = [60.0, 61.0, 59.0, 60.0, 62.0, 58.0, 61.0, 60.0, 59.0, 61.0]
    # A night's worth of low readings, well above the ten-reading minimum the rule needs.
    db_file = _make_db(tmp_path, readings, oxygen=[88.0] * 20)

    last = FIRST + timedelta(days=9)
    run_nightly(SUBJECT, f"{FIRST.isoformat()}:{last.isoformat()}", db_file)

    fired = _events(db_file, "red_flag_vitals")
    assert fired, "a night of 88 percent blood oxygen raised nothing"


def test_too_few_oxygen_readings_is_no_opinion_not_an_all_clear(tmp_path: Path) -> None:
    """The real device gave six readings across four days. That must not read as fine."""
    readings = [60.0, 61.0, 59.0, 60.0, 62.0, 58.0, 61.0, 60.0, 59.0, 61.0]
    db_file = _make_db(tmp_path, readings, oxygen=[88.0, 87.0, 89.0])

    last = FIRST + timedelta(days=9)
    run_nightly(SUBJECT, f"{FIRST.isoformat()}:{last.isoformat()}", db_file)

    # Silence, not reassurance. Nothing is recorded either way.
    assert _events(db_file, "red_flag_vitals") == []


@pytest.mark.parametrize("readings", [[60.0] * 8, [60.0, 61.0, 59.0]])
def test_the_nightly_job_still_returns_its_detections(
    tmp_path: Path, readings: list[float]
) -> None:
    """A failure inside the floor must never cost the night's reading."""
    db_file = _make_db(tmp_path, readings)
    last = FIRST + timedelta(days=len(readings) - 1)

    detections = run_nightly(SUBJECT, f"{FIRST.isoformat()}:{last.isoformat()}", db_file)

    assert len(detections) == len(readings)
