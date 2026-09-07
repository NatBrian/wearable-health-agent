"""Ingestion service for pulling, storing, and normalising wearable data."""

from pathlib import Path
from typing import Any

from wha.audit.monitor import record_ingest
from wha.config import get_settings
from wha.constants import (
    DEFAULT_SYNTHETIC_BASE_BPM,
    DEFAULT_SYNTHETIC_SEED,
    STARTUP_CATCHUP_DAYS,
)

# How many days a manual `wha ingest` pulls. Exposed here rather than read from
# wha.constants by the CLI, which is only permitted to import from config and service.
# It matches the startup catch up so both routes give the same result from one watch.
DEFAULT_INGEST_DAYS = STARTUP_CATCHUP_DAYS
from wha.clock import now_utc
from wha.db import apply_schema, connect
from wha.errors import SourceUnavailable
from wha.ingest.live_bridge import LiveBridge
from wha.ingest.store import normalise_and_store
from wha.ingest.synthetic import Synthetic
from wha.models import Scenario


def run_ingest(
    subject_id: str | None = None,
    days: int = 7,
    db_path: Path | None = None,
) -> int:
    """Pull samples from configured data source and store normalised records."""
    settings = get_settings()
    subj = subject_id if subject_id is not None else settings.subject
    target_db = db_path if db_path is not None else settings.db_path

    target_db.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(target_db)
    apply_schema(conn)

    # Ensure subject exists
    fetched_at = now_utc().isoformat()
    conn.execute(
        """
        INSERT OR IGNORE INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
        VALUES (?, ?, ?, ?, ?);
        """,
        (
            subj,
            subj,
            "live" if settings.bridge_url else "synthetic",
            settings.timezone,
            fetched_at,
        ),
    )
    conn.commit()

    if settings.bridge_url:
        token = settings.bridge_token.get_secret_value() if settings.bridge_token else None
        bridge = LiveBridge(base_url=settings.bridge_url, token=token)
        try:
            raw_payloads = bridge.fetch(subject_id=subj, days=days)
        except Exception as e:
            conn.close()
            raise SourceUnavailable(f"Failed to fetch from LiveBridge: {e}") from e

        norm = normalise_and_store(conn, raw_payloads)
        stored = len(norm.heart_rate_samples)
        # The newest sample now on record, so a poll that re-fetched the same window
        # writes nothing rather than another identical line.
        record_ingest(conn, subj, stored, "your watch", _newest_sample(conn, subj))
        conn.close()
        return stored

    # Fallback to deterministic synthetic source
    # Scenario forbids extra fields and requires all five of these. The previous call
    # passed a scenario_id the model does not define and omitted description, base_bpm,
    # seed and timezone, so this path raised ValidationError on every run without a live
    # bridge, which is the default path.
    scenario = Scenario(
        name="default-ingest",
        description="Deterministic synthetic fallback when no live bridge is configured.",
        days=days,
        base_bpm=DEFAULT_SYNTHETIC_BASE_BPM,
        seed=DEFAULT_SYNTHETIC_SEED,
        timezone=settings.timezone,
    )
    syn = Synthetic(scenario=scenario)
    raw_payload = syn.fetch(subject_id=subj)
    norm = normalise_and_store(conn, raw_payload)
    stored = len(norm.heart_rate_samples)
    record_ingest(conn, subj, stored, "simulated data", _newest_sample(conn, subj))
    conn.close()
    return stored


def _newest_sample(conn: Any, subject_id: str) -> str | None:
    """The most recent heart rate sample timestamp on record for this subject."""
    row = conn.execute(
        "SELECT MAX(ts_utc) AS newest FROM heart_rate_samples WHERE subject_id = ?",
        (subject_id,),
    ).fetchone()
    return row["newest"] if row is not None and row["newest"] else None


def describe_device_capability(
    subject_id: str | None = None,
    db_path: Path | None = None,
) -> str:
    """Report what the subject's device sends and how far each channel travels.

    Reads the most recent stored raw payload rather than calling the bridge, so it works
    offline and describes what was actually received.
    """
    import json

    from wha.ingest.capability import describe_payload, format_report

    settings = get_settings()
    subj = subject_id if subject_id is not None else settings.subject
    conn = connect(db_path) if db_path is not None else connect()
    apply_schema(conn)
    try:
        row = conn.execute(
            """SELECT payload_json FROM raw_payloads
               WHERE subject_id = ? ORDER BY fetched_at_utc DESC LIMIT 1""",
            (subj,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return (
            f"No data has been received for '{subj}' yet. "
            "Run 'uv run wha ingest' with the phone bridge reachable."
        )

    return format_report(describe_payload(json.loads(row["payload_json"])))
