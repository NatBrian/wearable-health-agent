"""Background scheduler running ingestion, nightly processing, episode tick, and telegram polling."""

import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from wha.constants import ANSWER_TIMEOUT_HOURS, MEASUREMENT_TIMEOUT_HOURS
from wha.db import connect
from wha.db.migrations import apply_schema
from wha.models import ComponentStatus
from wha.service.episodes import step_episode
from wha.service.ingest import run_ingest
from wha.service.nightly import run_nightly
from wha.service.status import record_component_status

logger = logging.getLogger(__name__)

# Shared execution lock to prevent overlapping jobs
_SCHEDULER_LOCK = threading.Lock()


def safe_job_wrapper(job_name: str, fn: Callable[[], Any], db_path: Path | None = None) -> None:
    """Execute a scheduler job under the shared lock.

    Catches any exception, records a system_status row, and never kills the thread.
    """
    acquired = _SCHEDULER_LOCK.acquire(blocking=False)
    if not acquired:
        logger.warning(
            "Job %s skipped because another scheduler job holds the execution lock.", job_name
        )
        return

    try:
        fn()
        record_component_status(
            ComponentStatus(
                component="scheduler",
                ok=True,
                detail=f"Job '{job_name}' completed successfully.",
                checked_at_utc=datetime.now(UTC),
                severity="ok",
            ),
            db_path=db_path,
        )
    except Exception as exc:
        logger.exception("Job %s failed", job_name)
        record_component_status(
            ComponentStatus(
                component="scheduler",
                ok=False,
                detail=f"Job '{job_name}' failed: {exc}",
                checked_at_utc=datetime.now(UTC),
                severity="error",
            ),
            db_path=db_path,
        )
    finally:
        _SCHEDULER_LOCK.release()


def run_episode_tick(db_path: Path | None = None) -> dict[str, Any]:
    """Check for timed-out human interactions/measurements and step open episodes."""
    conn = connect(db_path) if db_path is not None else connect()
    apply_schema(conn)

    now = datetime.now(UTC)
    answer_cutoff = now - timedelta(hours=ANSWER_TIMEOUT_HOURS)
    meas_cutoff = now - timedelta(hours=MEASUREMENT_TIMEOUT_HOURS)

    timed_out_episodes: set[str] = set()

    try:
        # 1. Expire timed out interactions
        int_rows = conn.execute(
            """SELECT id, episode_id, asked_at_utc FROM interactions
               WHERE status IN ('PENDING', 'ASKED')"""
        ).fetchall()
        for r in int_rows:
            asked_at = datetime.fromisoformat(r["asked_at_utc"])
            if asked_at < answer_cutoff:
                conn.execute(
                    "UPDATE interactions SET status = 'TIMED_OUT' WHERE id = ?",
                    (r["id"],),
                )
                timed_out_episodes.add(r["episode_id"])

        # 2. Expire timed out measurements
        meas_rows = conn.execute(
            """SELECT id, episode_id, requested_at_utc FROM measurements
               WHERE status = 'REQUESTED'"""
        ).fetchall()
        for r in meas_rows:
            req_at = datetime.fromisoformat(r["requested_at_utc"])
            if req_at < meas_cutoff:
                conn.execute(
                    "UPDATE measurements SET status = 'TIMED_OUT' WHERE id = ?",
                    (r["id"],),
                )
                timed_out_episodes.add(r["episode_id"])

        conn.commit()

        # 3. Advance episodes that had timeouts or are active
        for ep_id in timed_out_episodes:
            try:
                step_episode(ep_id, conn=conn)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to step episode %s after timeout: %s", ep_id, exc)

        return {"timed_out_episodes": list(timed_out_episodes)}
    finally:
        conn.close()


def create_scheduler(db_path: Path | None = None) -> BackgroundScheduler:
    """Configure and build APScheduler with 4 canonical background jobs."""
    scheduler = BackgroundScheduler()

    # 1. Ingestion: Every 30 minutes
    scheduler.add_job(
        func=lambda: safe_job_wrapper(
            "ingest", lambda: run_ingest(db_path=db_path), db_path=db_path
        ),
        trigger=IntervalTrigger(minutes=30),
        id="ingest",
        name="Pull & normalise wearable data",
        max_instances=1,
        coalesce=True,
    )

    # 2. Nightly batch: Daily at 09:00 local time
    scheduler.add_job(
        func=lambda: safe_job_wrapper(
            "nightly", lambda: run_nightly(db_path=db_path), db_path=db_path
        ),
        trigger=CronTrigger(hour=9, minute=0),
        id="nightly",
        name="Run nightly detection batch",
        max_instances=1,
        coalesce=True,
    )

    # 3. Episode tick: Every 15 minutes
    scheduler.add_job(
        func=lambda: safe_job_wrapper(
            "episode_tick", lambda: run_episode_tick(db_path=db_path), db_path=db_path
        ),
        trigger=IntervalTrigger(minutes=15),
        id="episode_tick",
        name="Check interaction timeouts and step episodes",
        max_instances=1,
        coalesce=True,
    )

    return scheduler
