"""Storage operations for raw and normalised health data."""

import json
import sqlite3

from wha.clock import now_utc
from wha.db import to_iso, transaction
from wha.ingest.base import NormalisedData, normalise
from wha.models import RawPayload


def ensure_subject_exists(
    conn: sqlite3.Connection,
    subject_id: str,
    source_kind: str = "synthetic",
    timezone: str = "Asia/Singapore",
) -> None:
    """Ensure subject record exists in the subjects table."""
    now_str = to_iso(now_utc())
    conn.execute(
        """
        INSERT OR IGNORE INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
        VALUES (?, ?, ?, ?, ?);
        """,
        (subject_id, subject_id, source_kind, timezone, now_str),
    )


def store_raw(conn: sqlite3.Connection, payload: RawPayload) -> None:
    """Store raw payload verbatim with sha256 before any normalisation.

    Uses INSERT OR IGNORE so identical payloads fetched multiple times produce one row.
    """
    ensure_subject_exists(conn, payload.subject_id, source_kind=payload.source_kind)
    ts_str = to_iso(payload.fetched_at_utc)
    body_json = json.dumps(payload.body, sort_keys=True, separators=(",", ":"))

    conn.execute(
        """
        INSERT OR IGNORE INTO raw_payloads (
            subject_id, fetched_at_utc, source_kind, sha256, payload_json
        ) VALUES (?, ?, ?, ?, ?);
        """,
        (payload.subject_id, ts_str, payload.source_kind, payload.sha256, body_json),
    )
    conn.commit()


def normalise_and_store(conn: sqlite3.Connection, payload: RawPayload) -> NormalisedData:
    """Store raw payload first, then normalise and upsert typed rows into database tables."""
    # 1. Raw is stored before normalisation, ALWAYS.
    store_raw(conn, payload)

    # 2. Normalise pure function (may raise on invalid data)
    norm = normalise(payload.subject_id, payload.body)

    # 3. Upsert normalised rows
    with transaction(conn):
        for hr in norm.heart_rate_samples:
            conn.execute(
                """
                INSERT OR REPLACE INTO heart_rate_samples (
                    subject_id, ts_utc, avg_bpm, min_bpm, max_bpm, origin
                ) VALUES (?, ?, ?, ?, ?, ?);
                """,
                (hr.subject_id, hr.ts_utc, hr.avg_bpm, hr.min_bpm, hr.max_bpm, hr.origin),
            )

        for step in norm.step_buckets:
            conn.execute(
                """
                INSERT OR REPLACE INTO step_buckets (
                    subject_id, start_utc, end_utc, count
                ) VALUES (?, ?, ?, ?);
                """,
                (step.subject_id, step.start_utc, step.end_utc, step.count),
            )

        for spo2 in norm.oxygen_saturation_samples:
            conn.execute(
                """
                INSERT OR REPLACE INTO oxygen_saturation_samples (
                    subject_id, ts_utc, percentage, origin
                ) VALUES (?, ?, ?, ?);
                """,
                (spo2.subject_id, spo2.ts_utc, spo2.percentage, spo2.origin),
            )

        for dist in norm.distance_buckets:
            conn.execute(
                """
                INSERT OR REPLACE INTO distance_buckets (
                    subject_id, start_utc, end_utc, meters
                ) VALUES (?, ?, ?, ?);
                """,
                (dist.subject_id, dist.start_utc, dist.end_utc, dist.meters),
            )

        for cal in norm.calorie_buckets:
            conn.execute(
                """
                INSERT OR REPLACE INTO calorie_buckets (
                    subject_id, start_utc, end_utc, calories_kcal
                ) VALUES (?, ?, ?, ?);
                """,
                (cal.subject_id, cal.start_utc, cal.end_utc, cal.calories_kcal),
            )

        for slp in norm.sleep_stages:
            conn.execute(
                """
                INSERT OR REPLACE INTO sleep_stages (
                    subject_id, start_utc, end_utc, stage
                ) VALUES (?, ?, ?, ?);
                """,
                (slp.subject_id, slp.start_utc, slp.end_utc, slp.stage),
            )

        for ex in norm.exercise_sessions:
            conn.execute(
                """
                INSERT OR REPLACE INTO exercise_sessions (
                    subject_id, start_utc, end_utc, kind
                ) VALUES (?, ?, ?, ?);
                """,
                (ex.subject_id, ex.start_utc, ex.end_utc, ex.kind),
            )

    return norm
