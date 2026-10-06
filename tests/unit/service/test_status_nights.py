"""Unit tests for status, connection checks, subjects, and nights services."""

from datetime import date, timedelta
from unittest.mock import MagicMock

import httpx

from wha.db import connect
from wha.db.migrations import apply_schema
from wha.models import BaselineRung, ConnectionCheck, SystemStatus
from wha.service import (
    get_night_detail,
    get_system_status,
    list_nights,
    list_subjects,
)
from wha.service import (
    test_bridge_connection as svc_test_bridge_connection,
)
from wha.service import (
    test_telegram_connection as svc_test_telegram_connection,
)


def test_every_function_handles_empty_database() -> None:
    """Every service function executes cleanly on an empty database without raising exceptions."""
    conn = connect(":memory:")
    apply_schema(conn)

    # 1. get_system_status on empty DB
    status = get_system_status("sub_empty", conn=conn)
    assert isinstance(status, SystemStatus)
    assert len(status.components) == 6
    assert status.usable_nights == 0
    assert status.rung == BaselineRung.COLD

    # 2. list_subjects on empty DB
    subs = list_subjects(conn=conn)
    assert subs == []

    # 3. list_nights on empty DB for 7-day range
    start_d = date(2026, 8, 1)
    end_d = date(2026, 8, 7)
    nights = list_nights("sub_empty", start=start_d, end=end_d, conn=conn)
    assert len(nights) == 7
    for n in nights:
        assert n.rhr_bpm is None
        assert n.usable is False

    # 4. get_night_detail on empty DB
    detail = get_night_detail("sub_empty", night_date=start_d, conn=conn)
    assert detail.row.night_date == start_d
    assert detail.features.usable is False


def test_status_is_cheap() -> None:
    """get_system_status reads from DB tables only and makes no external network calls."""
    conn = connect(":memory:")
    apply_schema(conn)

    mock_client = MagicMock()
    # If get_system_status tried to use httpx or network, mock would be touched
    status = get_system_status("sub_test", conn=conn)
    assert isinstance(status, SystemStatus)
    assert not mock_client.get.called
    assert not mock_client.post.called


def test_connection_checks_never_return_secrets() -> None:
    """Connection checks never expose or echo back secrets in their detail string."""
    secret_bridge_token = "SUPER_SECRET_BEARER_TOKEN_999"
    secret_tg_token = "123456:SECRET_BOT_TOKEN_XYZ"

    mock_http = MagicMock()
    mock_http.get.side_effect = httpx.ConnectError("Simulated network drop")

    # Bridge check
    bridge_res = svc_test_bridge_connection(
        bridge_host="http://localhost:8080",
        bridge_token=secret_bridge_token,
        client=mock_http,
    )
    assert isinstance(bridge_res, ConnectionCheck)
    assert secret_bridge_token not in bridge_res.detail

    # Telegram check
    tg_res = svc_test_telegram_connection(token=secret_tg_token, client=mock_http)
    assert isinstance(tg_res, ConnectionCheck)
    assert secret_tg_token not in tg_res.detail


def test_list_nights_includes_empty_nights() -> None:
    """A 30-day range with 12 nights of data returns exactly 30 NightRow items, preserving date continuity."""
    conn = connect(":memory:")
    apply_schema(conn)

    subject_id = "sub_gap_test"
    conn.execute(
        "INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc) VALUES (?, ?, ?, ?, ?)",
        (subject_id, "Test Subject", "synthetic", "Asia/Singapore", "2026-08-01T00:00:00Z"),
    )

    start_d = date(2026, 8, 1)
    end_d = start_d + timedelta(days=29)  # 30-day range

    # Insert 12 nights of data
    for i in range(12):
        d_str = (start_d + timedelta(days=i)).isoformat()
        conn.execute(
            """INSERT INTO nightly_features (subject_id, night_date, rhr_bpm, coverage_minutes, usable, computed_at_utc)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (subject_id, d_str, 58.5 + i * 0.2, 480, 1, "2026-08-01T08:00:00Z"),
        )
        conn.execute(
            """INSERT INTO baselines (subject_id, night_date, centre_bpm, scale_bpm, usable_nights, rung, shrink_weight)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (subject_id, d_str, 58.0, 2.5, i + 1, "SHRINKING", 0.5),
        )

    nights = list_nights(subject_id, start=start_d, end=end_d, conn=conn)

    # Exactly 30 rows returned
    assert len(nights) == 30

    # First 12 have data and populated baseline band
    for i in range(12):
        n = nights[i]
        assert n.rhr_bpm is not None
        assert n.usable is True
        assert n.band_lo is not None
        assert n.band_hi is not None
        assert n.band_lo == 58.0 - 2.5
        assert n.band_hi == 58.0 + 2.5

    # Last 18 are empty rows with gaps
    for i in range(12, 30):
        n = nights[i]
        assert n.rhr_bpm is None
        assert n.usable is False
        assert n.band_lo is None
        assert n.band_hi is None


def test_dashboard_summary_uses_latest_samples_and_a_calendar_steps_window() -> None:
    from wha.service.nights import get_dashboard_summary

    conn = connect(":memory:")
    apply_schema(conn)
    entries = [
        ("2026-09-01", 900, 7.0, 1),
        ("2026-09-03", 300, None, 1),
        ("2026-09-04", 500, 6.25, 0),
    ]
    for night_date, steps, sleep_hours, usable in entries:
        conn.execute(
            """INSERT INTO nightly_features
                 (subject_id, night_date, rhr_bpm, coverage_minutes, usable,
                  steps_prev_day, sleep_hours, computed_at_utc)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("summary-subject", night_date, 60, 400, usable, steps, sleep_hours, "2026-09-05T00:00:00Z"),
        )

    summary = get_dashboard_summary(
        "summary-subject",
        end=date(2026, 9, 5),
        steps_window_days=3,
        conn=conn,
    )

    assert summary.latest_sleep_hours == 6.25
    assert summary.latest_sleep_night == date(2026, 9, 4)
    assert summary.latest_steps == 500
    assert summary.latest_steps_night == date(2026, 9, 4)
    assert summary.steps_average == 400
    assert summary.steps_window_start == date(2026, 9, 3)
    assert summary.steps_window_end == date(2026, 9, 5)


def test_dashboard_summary_distinguishes_no_samples_from_zero_steps() -> None:
    from wha.service.nights import get_dashboard_summary

    conn = connect(":memory:")
    apply_schema(conn)

    summary = get_dashboard_summary(
        "empty-subject",
        end=date(2026, 9, 5),
        steps_window_days=3,
        conn=conn,
    )

    assert summary.latest_sleep_hours is None
    assert summary.latest_sleep_night is None
    assert summary.latest_steps is None
    assert summary.latest_steps_night is None
    assert summary.steps_average is None
    assert summary.steps_window_start == date(2026, 9, 3)
    assert summary.steps_window_end == date(2026, 9, 5)


def test_band_is_none_without_baseline() -> None:
    """When a night has feature data but no baseline record, band_lo and band_hi are None."""
    conn = connect(":memory:")
    apply_schema(conn)

    subject_id = "sub_nobase"
    d = date(2026, 8, 15)
    d_str = d.isoformat()

    conn.execute(
        """INSERT INTO nightly_features (subject_id, night_date, rhr_bpm, coverage_minutes, usable, computed_at_utc)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (subject_id, d_str, 62.0, 450, 1, "2026-08-15T08:00:00Z"),
    )

    nights = list_nights(subject_id, start=d, end=d, conn=conn)
    assert len(nights) == 1
    n = nights[0]
    assert n.rhr_bpm == 62.0
    assert n.centre_bpm is None
    assert n.band_lo is None
    assert n.band_hi is None


def test_the_night_row_says_which_window_it_was_measured_over() -> None:
    """Both screens state this in words, so a dead branch here states a falsehood.

    Today and History both say either "over the sleep your watch recorded" or "between
    midnight and 7am, because no sleep was recorded". The flag that chooses between them
    lived on NightlyFeatures and NOT on NightRow, and both pages read it with
    `getattr(n, "rhr_window_source", "clock")`, so the default always won. Every night was
    described as having no recorded sleep, including the 44 of 72 in the real database
    where sleep was recorded. That is a stronger false claim than the vague wording it
    replaced: it asserts something untrue about the person's own watch.

    The `getattr` defaults are gone with it. A field that must reach the screen should
    break loudly when renamed, not fall back to the wrong sentence.
    """
    from datetime import date

    from wha.db.connection import connect
    from wha.db.migrations import apply_schema
    from wha.service.nights import get_night_detail, list_nights

    conn = connect(":memory:")
    apply_schema(conn)
    conn.execute(
        "INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc) "
        "VALUES (?, ?, ?, ?, ?)",
        ("s_win", "W", "synthetic", "Asia/Singapore", "2026-09-01T00:00:00Z"),
    )
    for day, source in (("2026-09-01", "sleep"), ("2026-09-02", "clock")):
        conn.execute(
            """INSERT INTO nightly_features
                 (subject_id, night_date, rhr_bpm, coverage_minutes, usable,
                  computed_at_utc, rhr_window_source)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("s_win", day, 60.0, 400, 1, f"{day}T08:00:00Z", source),
        )
    conn.commit()

    rows = {
        r.night_date.isoformat(): r
        for r in list_nights("s_win", start=date(2026, 9, 1), end=date(2026, 9, 2), conn=conn)
    }

    # Both values must survive onto the row the screens actually read.
    assert rows["2026-09-01"].rhr_window_source == "sleep"
    assert rows["2026-09-02"].rhr_window_source == "clock"

    # And onto the features object the History detail panel reads.
    assert (
        get_night_detail("s_win", date(2026, 9, 1), conn=conn).features.rhr_window_source == "sleep"
    )
    assert (
        get_night_detail("s_win", date(2026, 9, 2), conn=conn).features.rhr_window_source == "clock"
    )


def test_no_screen_reads_the_window_source_through_a_defaulting_getattr() -> None:
    """`getattr(x, "rhr_window_source", "clock")` is what hid the dead branch for a week."""
    import re
    from pathlib import Path

    ui = Path(__file__).resolve().parents[3] / "src" / "wha" / "ui"
    offenders = [
        f"{p.relative_to(ui.parents[2])}:{i}"
        for p in ui.rglob("*.py")
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
        if re.search(r"getattr\([^,]+,\s*[\"']rhr_window_source[\"']", line)
    ]
    assert not offenders, "read the field directly so a rename breaks loudly: " + ", ".join(
        offenders
    )
