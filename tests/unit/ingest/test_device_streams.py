"""Tests for the three streams the device returns beyond heart rate and steps.

Field names here are copied from a live probe of the Health Connect bridge on
2026-09-02, not guessed. The three types below were present; respiratory rate and skin
temperature were not, and are deliberately unsupported.
"""

from pathlib import Path

from wha.db import apply_schema, connect
from wha.ingest.base import normalise
from wha.ingest.store import normalise_and_store
from wha.models import RawPayload

# Shaped exactly as the bridge returns it.
LIVE_SHAPED_PAYLOAD = {
    "app_version": "1.9.17",
    "heart_rate": [],
    "steps": [],
    "sleep": [],
    "exercise": [],
    "oxygen_saturation": [
        {
            "percentage": 94.0,
            "time": "2026-08-30T19:04:00Z",
            "metadata": {"data_origin": "com.sec.android.app.shealth"},
        },
        {
            "percentage": 92.0,
            "time": "2026-08-31T19:39:00Z",
            "metadata": {"data_origin": "com.sec.android.app.shealth"},
        },
    ],
    "distance": [
        {
            "meters": 4210.5,
            "start_time": "2026-08-31T16:00:00Z",
            "end_time": "2026-09-01T16:00:00Z",
        }
    ],
    "total_calories": [
        {
            "calories": 2180.0,
            "start_time": "2026-08-31T16:00:00Z",
            "end_time": "2026-09-01T16:00:00Z",
            "metadata": {"data_origin": "com.sec.android.app.shealth"},
        }
    ],
}


def test_normalises_the_streams_the_device_actually_sends() -> None:
    """Blood oxygen, distance and calories parse from the real payload shape."""
    norm = normalise("me", LIVE_SHAPED_PAYLOAD)

    assert len(norm.oxygen_saturation_samples) == 2
    assert norm.oxygen_saturation_samples[0].percentage == 94.0
    assert norm.oxygen_saturation_samples[0].origin == "com.sec.android.app.shealth"

    assert len(norm.distance_buckets) == 1
    assert norm.distance_buckets[0].meters == 4210.5

    assert len(norm.calorie_buckets) == 1
    assert norm.calorie_buckets[0].calories_kcal == 2180.0


def test_absent_streams_yield_empty_lists_not_errors() -> None:
    """A payload without these keys is normal and must not raise.

    Sleep and exercise may never arrive from this device, and blood oxygen is sparse
    enough that most fetches contain none.
    """
    norm = normalise("me", {"heart_rate": [], "steps": []})

    assert norm.oxygen_saturation_samples == []
    assert norm.distance_buckets == []
    assert norm.calorie_buckets == []


def test_streams_are_persisted(tmp_path: Path) -> None:
    """The normalised rows reach the database.

    The previous attempt at these streams added the tables and the dataclasses but never
    updated the writer, so the columns could only ever be empty.
    """
    db_file = tmp_path / "streams.sqlite"
    conn = connect(db_file)
    apply_schema(conn)

    payload = RawPayload(
        subject_id="me",
        source_kind="live",
        fetched_at_utc=__import__("datetime").datetime(
            2026, 9, 2, tzinfo=__import__("datetime").UTC
        ),
        sha256="0" * 64,
        body=LIVE_SHAPED_PAYLOAD,
    )
    normalise_and_store(conn, payload)

    assert conn.execute("SELECT COUNT(*) FROM oxygen_saturation_samples").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM distance_buckets").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM calorie_buckets").fetchone()[0] == 1

    stored = conn.execute(
        "SELECT percentage FROM oxygen_saturation_samples ORDER BY ts_utc"
    ).fetchall()
    assert [r[0] for r in stored] == [94.0, 92.0]
    conn.close()


def test_deleting_a_subject_removes_the_new_streams(tmp_path: Path) -> None:
    """A purge must not leave biometric rows behind in the newly added tables."""
    from wha.service.settings import delete_all_subject_data

    db_file = tmp_path / "purge.sqlite"
    conn = connect(db_file)
    apply_schema(conn)
    conn.execute(
        """INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
           VALUES ('me', 'Me', 'live', 'Asia/Singapore', '2026-09-01T00:00:00Z')"""
    )
    payload = RawPayload(
        subject_id="me",
        source_kind="live",
        fetched_at_utc=__import__("datetime").datetime(
            2026, 9, 2, tzinfo=__import__("datetime").UTC
        ),
        sha256="0" * 64,
        body=LIVE_SHAPED_PAYLOAD,
    )
    normalise_and_store(conn, payload)
    assert conn.execute("SELECT COUNT(*) FROM oxygen_saturation_samples").fetchone()[0] == 2

    delete_all_subject_data("me", conn=conn)

    for table in ("oxygen_saturation_samples", "distance_buckets", "calorie_buckets"):
        assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    conn.close()
