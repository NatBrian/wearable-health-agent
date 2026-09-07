"""Unit tests for storage schema, connection pragmas, transactions, and timestamp helpers."""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from wha.db import apply_schema, connect, from_iso, to_iso, transaction


def test_apply_schema_is_idempotent(tmp_db_path: Path) -> None:
    """Calling apply_schema multiple times creates tables safely without error."""
    conn = connect(tmp_db_path)
    apply_schema(conn)
    apply_schema(conn)
    apply_schema(conn)

    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}
    assert "subjects" in tables
    assert "heart_rate_samples" in tables
    assert "audit_events" in tables
    conn.close()


def test_foreign_keys_are_enforced(tmp_db_path: Path) -> None:
    """Inserting a child record with missing parent foreign key raises IntegrityError."""
    conn = connect(tmp_db_path)
    apply_schema(conn)

    # raw_payloads references subjects(subject_id)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO raw_payloads (subject_id, fetched_at_utc, source_kind, sha256, payload_json)
            VALUES (?, ?, ?, ?, ?);
            """,
            ("nonexistent_subj", "2026-09-01T00:00:00Z", "synthetic", "abc123hash", "{}"),
        )
    conn.close()


def test_transaction_rolls_back_on_error(tmp_db_path: Path) -> None:
    """Exception inside transaction block rolls back all writes made in the block."""
    conn = connect(tmp_db_path)
    apply_schema(conn)

    conn.execute(
        """
        INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
        VALUES (?, ?, ?, ?, ?);
        """,
        ("sub1", "Subject 1", "synthetic", "Asia/Singapore", "2026-09-01T00:00:00Z"),
    )
    conn.commit()

    with pytest.raises(ValueError, match="simulated failure"), transaction(conn):
        conn.execute(
            """
            INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
            VALUES (?, ?, ?, ?, ?);
            """,
            ("sub2", "Subject 2", "synthetic", "Asia/Singapore", "2026-09-01T00:00:00Z"),
        )
        raise ValueError("simulated failure")

    cursor = conn.execute("SELECT subject_id FROM subjects;")
    ids = [row[0] for row in cursor.fetchall()]
    assert "sub1" in ids
    assert "sub2" not in ids
    conn.close()


def test_transaction_commits_on_success(tmp_db_path: Path) -> None:
    """Clean exit from transaction commits writes visible to new connections."""
    conn = connect(tmp_db_path)
    apply_schema(conn)

    with transaction(conn):
        conn.execute(
            """
            INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
            VALUES (?, ?, ?, ?, ?);
            """,
            ("sub_committed", "Committed", "synthetic", "Asia/Singapore", "2026-09-01T00:00:00Z"),
        )

    conn2 = connect(tmp_db_path)
    cursor = conn2.execute(
        "SELECT subject_id FROM subjects WHERE subject_id = ?;", ("sub_committed",)
    )
    assert cursor.fetchone() is not None
    conn.close()
    conn2.close()


def test_to_iso_rejects_naive_datetime() -> None:
    """to_iso raises ValueError when passed a naive datetime without tzinfo."""
    naive_dt = datetime.fromisoformat("2026-09-01T12:00:00")
    with pytest.raises(ValueError, match="Naive datetime not allowed"):
        to_iso(naive_dt)


def test_from_iso_returns_aware_utc() -> None:
    """from_iso parses ISO string and returns a timezone-aware UTC datetime."""
    iso_str = "2026-09-01T12:00:00Z"
    dt = from_iso(iso_str)
    assert dt.tzinfo is not None
    assert dt.utcoffset() == UTC.utcoffset(dt)
    assert to_iso(dt) == iso_str
