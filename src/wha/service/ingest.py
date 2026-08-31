"""Ingestion service for pulling, storing, and normalising wearable data."""

from datetime import UTC, datetime
from pathlib import Path

from wha.config import get_settings
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
    now_utc = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT OR IGNORE INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
        VALUES (?, ?, ?, ?, ?);
        """,
        (
            subj,
            subj,
            "synthetic" if not settings.bridge_url else "live_bridge",
            settings.timezone,
            now_utc,
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
        conn.close()
        return len(norm.heart_rate_samples)

    # Fallback to deterministic synthetic source
    scenario = Scenario(scenario_id="default_ingest", name="Default Ingest", days=days)
    syn = Synthetic(scenario=scenario)
    raw_payload = syn.fetch(subject_id=subj)
    norm = normalise_and_store(conn, raw_payload)
    conn.close()
    return len(norm.heart_rate_samples)
