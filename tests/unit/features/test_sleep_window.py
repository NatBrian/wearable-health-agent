"""A night is measured over the sleep the watch recorded, not over the clock.

The fixed local 00:00-07:00 window is the NightSignal definition, chosen for data that had
no sleep staging. Against the first real subject, who sleeps roughly 03:00 to 11:00, it
counted 2.6 to 3.6 hours of waking time as sleep and threw away 40 percent of the real
sleep, moving the readings by up to 11 bpm and inflating the night-to-night spread eightfold.
"""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from wha.db import connect
from wha.db.migrations import apply_schema
from wha.features.sleep_window import (
    group_sessions,
    is_awake_stage,
    resolve_sleep_window,
)

TZ = "Asia/Singapore"


def _db(tmp_path: Path, stages: list[tuple[str, str, str]]) -> Path:
    db_file = tmp_path / "sleep.db"
    conn = connect(db_file)
    apply_schema(conn)
    conn.execute(
        """INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
           VALUES ('me', 'me', 'live', ?, '2026-09-01T00:00:00Z')""",
        (TZ,),
    )
    for start, end, stage in stages:
        conn.execute(
            "INSERT INTO sleep_stages (subject_id, start_utc, end_utc, stage) VALUES ('me',?,?,?)",
            (start, end, stage),
        )
    conn.commit()
    conn.close()
    return db_file


def _local(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    """A moment in the subject's timezone."""
    return datetime(year, month, day, hour, minute, tzinfo=ZoneInfo(TZ))


def _span(start_local: datetime, minutes: int, stage: str) -> tuple[str, str, str]:
    """A stage expressed in Singapore local time, stored as UTC."""
    a = start_local.astimezone(UTC)
    b = a + timedelta(minutes=minutes)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return a.strftime(fmt), b.strftime(fmt), stage


def test_awake_stages_are_recognised_by_word_and_by_code() -> None:
    """Stored data carries both the bridge's words and Health Connect's numeric codes."""
    for awake in ("AWAKE", "awake", "AWAKE_IN_BED", "OUT_OF_BED", "1", "7", "0", "3"):
        assert is_awake_stage(awake) is True
    for asleep in ("LIGHT", "DEEP", "REM", "4", "5", "6", "2"):
        assert is_awake_stage(asleep) is False


def test_a_late_sleeper_is_measured_over_their_own_sleep(tmp_path: Path) -> None:
    """The real case: asleep 03:00 to 09:00, entirely outside a 00:00-07:00 assumption."""
    stages = [_span(_local(2026, 9, 2, 3, 0), 360, "DEEP")]
    db_file = _db(tmp_path, stages)

    conn = connect(db_file)
    window = resolve_sleep_window(conn, "me", date(2026, 9, 2), TZ)
    conn.close()

    assert window.source == "sleep"
    assert window.start_utc.astimezone(ZoneInfo(TZ)).hour == 3
    assert window.asleep_minutes == 360


def test_waking_spells_inside_a_session_are_excluded(tmp_path: Path) -> None:
    """Measuring session start to session end would keep the awake time it contains."""
    stages = [
        _span(_local(2026, 9, 2, 3, 0), 120, "DEEP"),
        _span(_local(2026, 9, 2, 5, 0), 30, "AWAKE"),
        _span(_local(2026, 9, 2, 5, 30), 120, "REM"),
    ]
    db_file = _db(tmp_path, stages)

    conn = connect(db_file)
    window = resolve_sleep_window(conn, "me", date(2026, 9, 2), TZ)
    conn.close()

    assert window.source == "sleep"
    assert window.asleep_minutes == 240, "the 30 awake minutes must not be measured"
    assert len(window.intervals) == 2


def test_a_nap_does_not_displace_the_main_sleep(tmp_path: Path) -> None:
    """Heart rate during naps is higher at matched stages, so the longest session wins.

    Whitehurst, Naji and Mednick 2018, Neurobiol Sleep Circadian Rhythms 5:52-57.
    """
    stages = [
        _span(_local(2026, 9, 2, 2, 0), 300, "DEEP"),  # main sleep, 5h
        _span(_local(2026, 9, 2, 14, 0), 45, "LIGHT"),  # afternoon nap
    ]
    db_file = _db(tmp_path, stages)

    conn = connect(db_file)
    window = resolve_sleep_window(conn, "me", date(2026, 9, 2), TZ)
    conn.close()

    assert window.asleep_minutes == 300, "the nap must not be pooled with overnight sleep"


def test_a_night_shift_sleeper_is_measured_over_their_daytime_sleep(tmp_path: Path) -> None:
    """Someone sleeping 08:00 to 16:00 gets almost nothing from a midnight-to-7am window."""
    stages = [_span(_local(2026, 9, 2, 8, 0), 420, "DEEP")]
    db_file = _db(tmp_path, stages)

    conn = connect(db_file)
    window = resolve_sleep_window(conn, "me", date(2026, 9, 2), TZ)
    conn.close()

    assert window.source == "sleep"
    assert window.asleep_minutes == 420


def test_no_recorded_sleep_falls_back_to_the_clock_and_says_so(tmp_path: Path) -> None:
    """Devices that never report staging must keep working, visibly on a weaker basis."""
    db_file = _db(tmp_path, [])

    conn = connect(db_file)
    window = resolve_sleep_window(conn, "me", date(2026, 9, 2), TZ)
    conn.close()

    assert window.source == "clock"
    assert window.start_utc.astimezone(ZoneInfo(TZ)).hour == 0
    assert window.end_utc.astimezone(ZoneInfo(TZ)).hour == 7


def test_a_session_of_only_awake_stages_falls_back(tmp_path: Path) -> None:
    """Time in bed is not sleep, and must not be measured as though it were."""
    stages = [_span(_local(2026, 9, 2, 2, 0), 300, "AWAKE")]
    db_file = _db(tmp_path, stages)

    conn = connect(db_file)
    window = resolve_sleep_window(conn, "me", date(2026, 9, 2), TZ)
    conn.close()

    assert window.source == "clock"


def test_sessions_are_split_on_a_gap_not_on_a_stored_identifier() -> None:
    """Stored stage rows carry no session id, so grouping is by gap."""
    rows = [
        {"start_utc": "2026-09-01T19:00:00Z", "end_utc": "2026-09-01T20:00:00Z", "stage": "DEEP"},
        {"start_utc": "2026-09-01T20:00:00Z", "end_utc": "2026-09-01T21:00:00Z", "stage": "REM"},
        {"start_utc": "2026-09-02T06:00:00Z", "end_utc": "2026-09-02T06:45:00Z", "stage": "LIGHT"},
    ]
    sessions = group_sessions(rows)
    assert len(sessions) == 2
    assert len(sessions[0]) == 2
    assert len(sessions[1]) == 1


def test_the_window_source_is_recorded_on_the_night(tmp_path: Path) -> None:
    """A health figure must be able to say how it was produced."""
    from wha.features.derivation import compute_night

    stages = [_span(_local(2026, 9, 2, 3, 0), 300, "DEEP")]
    db_file = _db(tmp_path, stages)

    conn = connect(db_file)
    features = compute_night(conn, "me", date(2026, 9, 2))
    stored = conn.execute(
        "SELECT rhr_window_source FROM nightly_features WHERE night_date = '2026-09-02'"
    ).fetchone()[0]
    conn.close()

    assert features.rhr_window_source == "sleep"
    assert stored == "sleep"
