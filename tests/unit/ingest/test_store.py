"""Unit tests for storing raw payloads and normalised tables."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from wha.db import apply_schema, connect
from wha.ingest import normalise_and_store, store_raw
from wha.models import RawPayload


def test_raw_stored_before_normalise(tmp_db_path: Path) -> None:
    """Raw payload is stored even if normalisation fails due to malformed data."""
    conn = connect(tmp_db_path)
    apply_schema(conn)

    # Bad payload with naive timestamp that will fail normalise()
    bad_payload = RawPayload(
        subject_id="subj_bad",
        source_kind="synthetic",
        fetched_at_utc=datetime(2026, 9, 1, 12, 0, 0, tzinfo=UTC),
        sha256="hash_bad_001",
        body={"heart_rate": [{"time": "2026-09-01 12:00:00", "avg": 80}]},
    )

    with pytest.raises(ValueError, match="Naive timestamp"):
        normalise_and_store(conn, bad_payload)

    cursor = conn.execute(
        "SELECT subject_id, sha256 FROM raw_payloads WHERE subject_id = ?;", ("subj_bad",)
    )
    row = cursor.fetchone()
    assert row is not None
    assert row["sha256"] == "hash_bad_001"
    conn.close()


def test_raw_payload_duplicate_is_ignored(tmp_db_path: Path) -> None:
    """Duplicate sha256 payloads for the same subject are ignored without error."""
    conn = connect(tmp_db_path)
    apply_schema(conn)

    payload = RawPayload(
        subject_id="subj_dup",
        source_kind="synthetic",
        fetched_at_utc=datetime(2026, 9, 1, 12, 0, 0, tzinfo=UTC),
        sha256="same_sha256_hash",
        body={"app_version": "1.9.17", "steps": [], "heart_rate": []},
    )

    store_raw(conn, payload)
    store_raw(conn, payload)

    cursor = conn.execute("SELECT COUNT(*) FROM raw_payloads WHERE subject_id = ?;", ("subj_dup",))
    count = cursor.fetchone()[0]
    assert count == 1
    conn.close()


def test_overlapping_windows_upsert(tmp_db_path: Path) -> None:
    """Overlapping timestamp data replaces existing samples with latest values."""
    conn = connect(tmp_db_path)
    apply_schema(conn)

    p1 = RawPayload(
        subject_id="subj_overlap",
        source_kind="synthetic",
        fetched_at_utc=datetime(2026, 9, 1, 12, 0, 0, tzinfo=UTC),
        sha256="hash_p1",
        body={
            "heart_rate": [{"time": "2026-09-01T01:00:00Z", "avg": 60}],
            "steps": [
                {
                    "count": 1000,
                    "start_time": "2026-09-01T00:00:00Z",
                    "end_time": "2026-09-02T00:00:00Z",
                }
            ],
        },
    )

    p2 = RawPayload(
        subject_id="subj_overlap",
        source_kind="synthetic",
        fetched_at_utc=datetime(2026, 9, 1, 13, 0, 0, tzinfo=UTC),
        sha256="hash_p2",
        body={
            "heart_rate": [{"time": "2026-09-01T01:00:00Z", "avg": 65}],
            "steps": [
                {
                    "count": 2500,
                    "start_time": "2026-09-01T00:00:00Z",
                    "end_time": "2026-09-02T00:00:00Z",
                }
            ],
        },
    )

    normalise_and_store(conn, p1)
    normalise_and_store(conn, p2)

    cursor = conn.execute(
        "SELECT avg_bpm FROM heart_rate_samples WHERE subject_id = ?;", ("subj_overlap",)
    )
    hr_row = cursor.fetchone()
    assert hr_row["avg_bpm"] == 65.0

    cursor2 = conn.execute(
        "SELECT count FROM step_buckets WHERE subject_id = ?;", ("subj_overlap",)
    )
    step_row = cursor2.fetchone()
    assert step_row["count"] == 2500

    conn.close()
