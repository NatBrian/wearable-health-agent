"""Unit tests for Audit view, hash-chain verification, filtering, and export."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from wha.models import AuditEventView, AuditFilter, ControlTier
from wha.ui.audit import render_audit_table, render_hash_chain_panel


def test_audit_hash_chain_verifies() -> None:
    """Hash-chain panel shows success on clean chain, and clear error with broken link on tampered chain."""
    # 1. Clean chain that actually holds entries.
    #
    # This case previously left the entry count unmocked, so it asserted the success
    # message over an empty log. An empty chain verifies trivially, and reporting "the
    # record is intact" for zero entries is a green tick for something never checked.
    with (
        patch("wha.api.client.ApiClient.verify_hash_chain", return_value=(True, None)),
        patch("wha.api.client.ApiClient.count_audit_events", return_value=12),
        patch("streamlit.success") as mock_success,
        patch("streamlit.error") as mock_error,
    ):
        intact = render_hash_chain_panel("sub_clean")
        assert intact is True
        assert mock_success.called
        assert not mock_error.called
        assert "intact" in mock_success.call_args[0][0].lower()

    # 1b. Verified, but nothing has been written yet.
    with (
        patch("wha.api.client.ApiClient.verify_hash_chain", return_value=(True, None)),
        patch("wha.api.client.ApiClient.count_audit_events", return_value=0),
        patch("streamlit.success") as mock_success,
        patch("streamlit.error") as mock_error,
        patch("streamlit.info") as mock_info,
    ):
        intact = render_hash_chain_panel("sub_new")
        assert intact is True
        assert not mock_error.called
        assert not mock_success.called, "an empty log must not be reported as verified"
        assert mock_info.called
        assert "nothing has been recorded yet" in mock_info.call_args[0][0].lower()

    # 2. Tampered chain
    with (
        patch(
            "wha.api.client.ApiClient.verify_hash_chain", return_value=(False, "evt_tampered_004")
        ),
        patch("streamlit.success") as mock_success,
        patch("streamlit.error") as mock_error,
    ):
        intact = render_hash_chain_panel("sub_tampered")
        assert intact is False
        assert mock_error.called
        assert not mock_success.called
        err_msg = mock_error.call_args[0][0]
        # Asserts the meaning, not the exact wording: the reader is told the record
        # was altered, and where the sequence breaks.
        assert "altered" in err_msg.lower()
        assert "evt_tampered_004" in err_msg


def test_audit_filters_apply() -> None:
    """Audit table query respects filter fields and renders matching rows."""
    events = [
        AuditEventView(
            event_id="evt_01",
            timestamp_utc=datetime.now(UTC),
            episode_id="ep_01",
            step_index=1,
            actor="agent",
            operation="query_calendar",
            control_tier=ControlTier.T1,
            tool_name="query_calendar",
            permission_decision="ALLOW",
            sources=["calendar"],
            validation_status="VALID",
            human_decision=None,
            safety_event="none",
            latency_ms=12,
            hash_ok=True,
        )
    ]
    f = AuditFilter(subject_id="sub_01", episode_id="ep_01", operation="query_calendar")

    with (
        patch("wha.api.client.ApiClient.query_audit", return_value=events) as mock_query,
        patch("streamlit.dataframe") as mock_df,
    ):
        render_audit_table("sub_01", f)
        assert mock_query.called
        assert mock_query.call_args[0][0] == f
        assert mock_df.called


def test_audit_export_writes_file(tmp_path: Path) -> None:
    """Export action creates valid CSV and JSON files on disk."""
    csv_file = tmp_path / "audit_test.csv"
    json_file = tmp_path / "audit_test.json"

    events = [
        AuditEventView(
            event_id="evt_export_01",
            timestamp_utc=datetime.now(UTC),
            episode_id="ep_01",
            step_index=1,
            actor="agent",
            operation="test_op",
            control_tier=ControlTier.T1,
            tool_name="test_tool",
            permission_decision="ALLOW",
            sources=["test"],
            validation_status="VALID",
            human_decision=None,
            safety_event="none",
            latency_ms=5,
            hash_ok=True,
        )
    ]
    f = AuditFilter(subject_id="sub_export")

    with patch("wha.service.audit.query_audit", return_value=events):
        from wha.service.audit import export_audit

        export_audit(f, csv_file)
        assert csv_file.exists()
        csv_content = csv_file.read_text(encoding="utf-8")
        assert "evt_export_01" in csv_content
        assert "test_op" in csv_content

        export_audit(f, json_file)
        assert json_file.exists()
        json_content = json_file.read_text(encoding="utf-8")
        assert "evt_export_01" in json_content
