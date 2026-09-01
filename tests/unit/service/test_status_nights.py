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
