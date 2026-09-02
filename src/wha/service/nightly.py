"""Deterministic nightly batch calculation service."""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from wha.config import get_settings
from wha.constants import INGEST_STALE_REFUSE_HOURS
from wha.db import apply_schema, connect
from wha.detect import detect_range
from wha.features.derivation import compute_range
from wha.models import Detection, NightlyFeatures
from wha.service.episode_lifecycle import (
    check_close_conditions,
    get_open_episode,
    open_episodes_for_flagged_nights,
)


def parse_date_range(range_str: str | None, tz_name: str = "Asia/Singapore") -> tuple[date, date]:
    """Parse a range string 'YYYY-MM-DD:YYYY-MM-DD' or single date, or default to last 7 nights."""
    if range_str is None:
        local_today = datetime.now(ZoneInfo(tz_name)).date()
        end_d = local_today
        start_d = end_d - timedelta(days=6)
        return start_d, end_d

    if ":" in range_str:
        start_part, end_part = range_str.split(":", 1)
        return date.fromisoformat(start_part.strip()), date.fromisoformat(end_part.strip())

    single_d = date.fromisoformat(range_str.strip())
    return single_d, single_d


def run_nightly(
    subject_id: str | None = None,
    date_or_range: str | None = None,
    db_path: Path | None = None,
    no_ingest: bool = True,
) -> list[Detection]:
    """Execute nightly feature calculation, baseline update, and anomaly detection."""
    settings = get_settings()
    subj = subject_id if subject_id is not None else settings.subject
    target_db = db_path if db_path is not None else settings.db_path

    target_db.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(target_db)
    apply_schema(conn)

    # Resolve subject timezone
    row = conn.execute("SELECT timezone FROM subjects WHERE subject_id = ?", (subj,)).fetchone()
    tz_name = row[0] if row else settings.timezone

    start_date, end_date = parse_date_range(date_or_range, tz_name)

    # Check for raw samples
    sample_count = conn.execute(
        "SELECT COUNT(*) FROM heart_rate_samples WHERE subject_id = ?", (subj,)
    ).fetchone()[0]

    # Only derive features from raw samples if raw samples exist for subject
    if sample_count > 0:
        features_list = compute_range(conn, subj, start_date, end_date)
    else:
        # If nightly_features were directly inserted in tests or precomputed, query them
        feat_rows = conn.execute(
            """
            SELECT night_date, rhr_bpm, coverage_minutes, usable
            FROM nightly_features
            WHERE subject_id = ? AND night_date >= ? AND night_date <= ?
            ORDER BY night_date ASC
            """,
            (subj, start_date.isoformat(), end_date.isoformat()),
        ).fetchall()

        features_list = [
            NightlyFeatures(
                subject_id=subj,
                night_date=date.fromisoformat(r[0]),
                rhr_bpm=r[1],
                coverage_minutes=r[2],
                usable=bool(r[3]),
            )
            for r in feat_rows
        ]

    # Check staleness: if latest sample is older than INGEST_STALE_REFUSE_HOURS
    last_sample_row = conn.execute(
        "SELECT MAX(ts_utc) FROM heart_rate_samples WHERE subject_id = ?",
        (subj,),
    ).fetchone()
    if last_sample_row and last_sample_row[0]:
        try:
            last_sample_dt = datetime.fromisoformat(last_sample_row[0])
            for feat in features_list:
                feat_midnight = datetime(
                    feat.night_date.year,
                    feat.night_date.month,
                    feat.night_date.day,
                    tzinfo=UTC,
                )
                if (feat_midnight - last_sample_dt) > timedelta(hours=INGEST_STALE_REFUSE_HOURS):
                    conn.execute(
                        """
                        UPDATE nightly_features
                        SET usable = 0
                        WHERE subject_id = ? AND night_date = ?
                        """,
                        (subj, feat.night_date.isoformat()),
                    )
        except (ValueError, TypeError):
            pass

    # Run detection
    detections = detect_range(conn, subj, start_date, end_date)

    # Open the investigation. Detection previously ended here, so a flagged night set a
    # boolean and nothing ever acted on it: no episode existed for the agent to advance,
    # and the link between the monitor and the investigation was absent entirely.
    open_episodes_for_flagged_nights(conn, subj, detections)

    open_episode = get_open_episode(conn, subj)
    if open_episode is not None:
        check_close_conditions(conn, str(open_episode["episode_id"]), detections)

    conn.close()
    return detections
