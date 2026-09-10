"""The scheduler's job functions without the scheduler.

``service/scheduler.py`` couples these to APScheduler at module top, which the phone
does not install. They are plain functions over the service layer, so they live here
with no apscheduler import; the scheduler and the phone facade both call them.
"""

import logging
from datetime import timedelta
from pathlib import Path
from typing import Any

from wha.clock import local_today
from wha.config import get_settings
from wha.constants import NIGHTLY_RESCORE_DAYS, STARTUP_CATCHUP_DAYS
from wha.service.ingest import run_ingest
from wha.service.nightly import run_nightly

logger = logging.getLogger(__name__)


def _rescore_recent(db_path: Path | None = None) -> list[Any]:
    """Re-score the last few nights, so a night settles when its sleep data arrives.

    Recomputation is idempotent: features, baseline and detection are all derived, and
    re-running over a night the watch has since filled in simply replaces a provisional
    reading with a complete one.
    """
    settings = get_settings()
    end = local_today(settings.timezone)
    start = end - timedelta(days=NIGHTLY_RESCORE_DAYS)
    return run_nightly(date_or_range=f"{start.isoformat()}:{end.isoformat()}", db_path=db_path)


def run_startup_catchup(db_path: Path | None = None) -> dict[str, Any]:
    """Pull from the source and process every night it returned, once, at startup."""
    settings = get_settings()
    stored = run_ingest(db_path=db_path)
    end = local_today(settings.timezone)
    start = end - timedelta(days=STARTUP_CATCHUP_DAYS)
    dets = run_nightly(date_or_range=f"{start.isoformat()}:{end.isoformat()}", db_path=db_path)
    logger.info(
        "Startup catch up stored %d samples and scored %d nights (%s to %s).",
        stored,
        len(dets),
        start,
        end,
    )
    return {"stored": stored, "nights": len(dets), "start": start, "end": end}
