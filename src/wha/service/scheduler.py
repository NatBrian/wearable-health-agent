"""Background scheduler running ingestion, nightly processing, episode tick, and telegram polling."""

import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from wha.clock import local_today
from wha.config import get_settings
from wha.constants import (
    ANSWER_TIMEOUT_HOURS,
    MEASUREMENT_TIMEOUT_HOURS,
    NIGHTLY_RESCORE_DAYS,
    NIGHTLY_RESCORE_INTERVAL_HOURS,
    STARTUP_CATCHUP_DAYS,
)
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
               WHERE status = 'PENDING'"""
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

        # 3. Advance every open episode, not only the ones that timed out.
        #
        # This loop used to iterate `timed_out_episodes`, so a freshly opened episode was
        # never touched: it sat at step_count 0 until a human ran `wha episode step`. The
        # detection half therefore ran unattended and the agentic half never started.
        open_rows = conn.execute(
            "SELECT episode_id FROM episodes WHERE state != 'CLOSED'"
        ).fetchall()

        advanced: list[str] = []
        for r in open_rows:
            ep_id = r["episode_id"]
            try:
                if _advance_episode(ep_id, conn=conn, db_path=db_path):
                    advanced.append(ep_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to advance episode %s: %s", ep_id, exc)

        return {
            "timed_out_episodes": list(timed_out_episodes),
            "advanced_episodes": advanced,
        }
    finally:
        conn.close()


def _advance_episode(
    episode_id: str,
    conn: Any,
    db_path: Path | None = None,
    max_steps: int = 24,
) -> bool:
    """Run one episode forward until it closes, parks on a person, or stops progressing.

    Stepping once per tick would leave an episode needing hours of ticks to reach a
    disposition, so the tick drives it as far as it can go unattended. It stops the moment
    the graph parks on an ``interrupt()``, which is the point where the system is waiting
    on the human rather than on itself. Returns whether any progress was made.
    """
    from wha.agent.graph import get_agent_graph, get_pending_interrupt

    graph = get_agent_graph(db_path)
    progressed = False

    for _ in range(max_steps):
        row = conn.execute(
            "SELECT state, step_count FROM episodes WHERE episode_id = ?",
            (episode_id,),
        ).fetchone()
        if row is None or row["state"] == "CLOSED":
            break

        pending = get_pending_interrupt(graph, episode_id)
        resume = _resume_value(conn, episode_id, pending) if pending is not None else None
        if pending is not None and resume is None:
            # Parked on a question the person has not answered yet. Leaving it parked is
            # the correct behaviour; the answer arrives via Telegram or the dashboard, and
            # the interaction timeout above eventually releases it.
            break

        before = row["step_count"]
        step_episode(episode_id, conn=conn, resume=resume)
        after_row = conn.execute(
            "SELECT state, step_count FROM episodes WHERE episode_id = ?",
            (episode_id,),
        ).fetchone()

        # Reaching a disposition is progress even when it took no further steps, so an
        # episode that closes on its first step is not reported as having done nothing.
        if after_row["step_count"] != before or after_row["state"] == "CLOSED":
            progressed = True
        if after_row["state"] == "CLOSED":
            break

        if get_pending_interrupt(graph, episode_id) is None:
            snapshot = graph.get_state({"configurable": {"thread_id": episode_id}})
            if not getattr(snapshot, "next", ()):
                # The graph ran to a stopping point without closing and without asking
                # anyone anything, which is what an OBSERVE decision looks like: wait for
                # another night rather than act. step_count increments on every call, so
                # "did the counter move" cannot detect this, and the tick re-ran a settled
                # episode until it hit the step ceiling, spending an LLM call each time.
                break

    return progressed


def _resume_value(conn: Any, episode_id: str, pending: Any) -> dict[str, Any] | None:
    """Build the value an ``interrupt()`` is waiting for from what the person has sent.

    Returns None when the episode is parked on a question nobody has answered yet, which
    tells the caller to leave it parked. Mirrors the shape the demo harness feeds from a
    fixture oracle, so live answers and scenario answers enter the graph identically.
    """
    if not isinstance(pending, dict):
        return {"decision": "approve"}

    kind = pending.get("kind")

    if kind == "question":
        probe_id = pending.get("probe_id") or ""
        row = conn.execute(
            """SELECT answer_option_id, free_text, status FROM interactions
                WHERE episode_id = ? AND probe_id = ?
                ORDER BY asked_at_utc DESC LIMIT 1""",
            (episode_id, probe_id),
        ).fetchone()
        if row is None or row["status"] == "PENDING":
            return None
        if row["status"] == "TIMED_OUT":
            return {"timed_out": True}
        if row["status"] == "DECLINED":
            return {"probe_id": probe_id, "declined": True}

        response: dict[str, Any] = {"probe_id": probe_id}
        if row["answer_option_id"]:
            response["option_id"] = row["answer_option_id"]
        else:
            response["declined"] = True
        if row["free_text"]:
            response["free_text"] = row["free_text"]
        return response

    if kind == "measurement":
        return {"measurement_id": pending.get("interaction_id"), "declined": True}

    return {"decision": "approve"}


def poll_telegram_once(db_path: Path | None = None) -> dict[str, Any]:
    """Read replies from Telegram and record them against the questions that asked.

    Nothing in any runtime path constructed a ``TelegramReceiver``, so the system could
    ask a question and never hear the answer. This closes that half of the loop; the
    episode tick that follows resumes the graph with whatever arrived.
    """
    from wha.agent.repository import EpisodeRepository
    from wha.config import get_settings
    from wha.notify.receiver import TelegramReceiver

    settings = get_settings()
    # Mirror get_notifier's own test rather than inventing a second one: if the outbound
    # half falls back to NullNotifier, there is nothing inbound to listen for either.
    token = settings.telegram_bot_token
    secret = token.get_secret_value() if token is not None else ""
    if not secret or not settings.telegram_chat_id:
        return {"polled": False, "reason": "telegram not configured"}

    conn = connect(db_path) if db_path is not None else connect()
    apply_schema(conn)
    try:
        receiver = TelegramReceiver(
            token=secret,
            authorized_chat_id=settings.telegram_chat_id,
            db=EpisodeRepository(conn=conn),
        )
        results = receiver.poll_once()
    finally:
        conn.close()

    return {"polled": True, "updates": len(results), "results": results}


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
            "nightly", lambda: _rescore_recent(db_path=db_path), db_path=db_path
        ),
        # Not a fixed hour. A cron at 09:00 assumes the person is awake and their watch
        # has synced by then. The first real subject wakes around 11:00, so their night
        # was scored before it had finished being recorded, and never revisited. Now that
        # the window is read from the sleep session rather than the clock, the trigger
        # cannot stay on the clock either. Scoring is idempotent and cheap, so it runs on
        # an interval over a trailing window and a night settles as soon as its sleep
        # arrives, whatever time that is.
        trigger=IntervalTrigger(hours=NIGHTLY_RESCORE_INTERVAL_HOURS),
        id="nightly",
        name="Score nights as their sleep arrives",
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

    # 4. Telegram receive: poll for replies. The module docstring has always named four
    #    jobs; only three were ever registered, so the agent could ask a question and
    #    never hear the answer. getUpdates long-polls for 30s, so a 45s interval keeps a
    #    steady listener without overlapping calls.
    scheduler.add_job(
        func=lambda: safe_job_wrapper(
            "telegram_poll", lambda: poll_telegram_once(db_path=db_path), db_path=db_path
        ),
        trigger=IntervalTrigger(seconds=45),
        id="telegram_poll",
        name="Poll Telegram for replies",
        max_instances=1,
        coalesce=True,
    )

    # 5. Catch up once, immediately.
    #
    # Measured from a cold start, the jobs above first fire at: telegram 45s, episode tick
    # 15 min, ingest 30 min, nightly at 09:00 the next morning. A new user who started the
    # app at one in the morning would therefore see an empty dashboard for half an hour and
    # unprocessed nights for seven hours, with nothing on screen distinguishing that from a
    # broken install. It also forced a second, undocumented route through the CLI, so there
    # appeared to be two different ways to set the system up.
    scheduler.add_job(
        func=lambda: safe_job_wrapper(
            "startup_catchup", lambda: run_startup_catchup(db_path=db_path), db_path=db_path
        ),
        trigger=DateTrigger(run_date=datetime.now(UTC) + timedelta(seconds=1)),
        id="startup_catchup",
        name="First-run catch up: pull and process what is already on the watch",
        max_instances=1,
        coalesce=True,
    )

    return scheduler


def scheduled_job_summary(scheduler: BackgroundScheduler) -> str:
    """One line naming every job actually registered.

    The startup message listed three jobs while four were running, so the only place that
    tells an operator what happens in the background was already out of date. Reading it
    off the scheduler means it cannot drift again.
    """
    return ", ".join(sorted(j.id for j in scheduler.get_jobs()))


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
