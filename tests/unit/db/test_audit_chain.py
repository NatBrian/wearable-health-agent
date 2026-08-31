"""Unit tests for the audit hash chain."""

from datetime import UTC, datetime
from pathlib import Path

from wha.db import append_audit, apply_schema, connect, verify_chain
from wha.models import AuditEvent, ControlTier


def _make_event(subject_id: str, index: int) -> AuditEvent:
    return AuditEvent(
        event_id=f"evt_{subject_id}_{index:03d}",
        subject_id=subject_id,
        episode_id="ep_001" if index > 0 else None,
        step_index=index,
        timestamp_utc=datetime(2026, 9, 1, 12, index, 0, tzinfo=UTC),
        actor="system",
        operation="nightly",
        control_tier=ControlTier.T0,
        input={"step": index},
        output={"status": "ok"},
        safety_event="none",
    )


def test_first_row_has_null_prev_hash(tmp_db_path: Path) -> None:
    """The first row for a subject has prev_hash = None and verifies cleanly."""
    conn = connect(tmp_db_path)
    apply_schema(conn)

    evt = _make_event("subj_test", 0)
    h = append_audit(conn, evt)
    conn.commit()

    cursor = conn.execute(
        "SELECT prev_hash, hash FROM audit_events WHERE event_id = ?;", (evt.event_id,)
    )
    row = cursor.fetchone()
    assert row["prev_hash"] is None
    assert row["hash"] == h

    ok, bad_id = verify_chain(conn, "subj_test")
    assert ok is True
    assert bad_id is None
    conn.close()


def test_hash_chain_verifies_clean(tmp_db_path: Path) -> None:
    """A series of ten appended events verifies as valid and intact."""
    conn = connect(tmp_db_path)
    apply_schema(conn)

    for i in range(10):
        append_audit(conn, _make_event("subj_clean", i))
    conn.commit()

    ok, bad_id = verify_chain(conn, "subj_clean")
    assert ok is True
    assert bad_id is None
    conn.close()


def test_hash_chain_detects_tamper(tmp_db_path: Path) -> None:
    """Modifying a stored event's output_json breaks the chain and returns that event's id."""
    conn = connect(tmp_db_path)
    apply_schema(conn)

    for i in range(5):
        append_audit(conn, _make_event("subj_tamper", i))
    conn.commit()

    # Tamper with row 2
    bad_event_id = "evt_subj_tamper_002"
    conn.execute(
        "UPDATE audit_events SET output_json = ? WHERE event_id = ?;",
        ('{"status":"tampered"}', bad_event_id),
    )
    conn.commit()

    ok, reported_bad_id = verify_chain(conn, "subj_tamper")
    assert ok is False
    assert reported_bad_id == bad_event_id
    conn.close()


def test_hash_chain_is_stable_across_runs(tmp_path: Path) -> None:
    """The same sequence of events inserted into two separate databases yields identical hashes."""
    db1 = tmp_path / "db1.sqlite"
    db2 = tmp_path / "db2.sqlite"

    conn1 = connect(db1)
    conn2 = connect(db2)
    apply_schema(conn1)
    apply_schema(conn2)

    hashes1 = []
    hashes2 = []

    for i in range(5):
        evt = _make_event("subj_stable", i)
        hashes1.append(append_audit(conn1, evt))
        hashes2.append(append_audit(conn2, evt))

    conn1.commit()
    conn2.commit()

    assert hashes1 == hashes2
    assert len(hashes1) == 5

    conn1.close()
    conn2.close()
