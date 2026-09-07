"""Integration tests for background scheduler thread, job isolation, and first-run handling."""

import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from wha.db import connect
from wha.db.migrations import apply_schema
from wha.models import BaselineRung
from wha.scheduler import run_episode_tick, safe_job_wrapper
from wha.service.status import get_system_status
from wha.service.subjects import list_subjects


def test_scheduler_job_failure_does_not_kill_thread(tmp_path: Path) -> None:
    """A job raising an exception records an error status row without crashing the scheduler thread."""
    db_file = tmp_path / "sched_test.db"
    conn = connect(db_file)
    apply_schema(conn)
    conn.close()

    def failing_fn() -> None:
        raise RuntimeError("Simulated network timeout during scheduled job")

    # Execute failing job via wrapper
    safe_job_wrapper("test_failing_job", failing_fn, db_path=db_file)

    # Verify status was written
    status = get_system_status(db_path=db_file)
    assert any(
        c.component == "scheduler" and not c.ok and "Simulated network timeout" in c.detail
        for c in status.components
    )


def test_scheduler_jobs_do_not_overlap() -> None:
    """Concurrent scheduler jobs are serialized under the shared lock with max_instances=1."""
    execution_order: list[str] = []

    def slow_job_1() -> None:
        execution_order.append("start_1")
        time.sleep(0.05)
        execution_order.append("end_1")

    def slow_job_2() -> None:
        execution_order.append("job_2")

    # Start slow job 1 and attempt concurrent job 2
    import threading

    t1 = threading.Thread(target=lambda: safe_job_wrapper("slow_1", slow_job_1))
    t1.start()
    time.sleep(0.01)

    # Job 2 should be skipped because lock is held
    safe_job_wrapper("slow_2", slow_job_2)

    t1.join()

    assert "start_1" in execution_order
    assert "end_1" in execution_order
    # job_2 should NOT have executed concurrently while lock was held
    assert "job_2" not in execution_order


def test_episode_tick_expires_timed_out_interaction(tmp_path: Path) -> None:
    """Interactions older than ANSWER_TIMEOUT_HOURS are transitioned to TIMED_OUT by episode_tick."""
    db_file = tmp_path / "timeout_test.db"
    conn = connect(db_file)
    apply_schema(conn)

    # Insert subject, episode, interaction older than 36h
    now = datetime.now(UTC)
    old_time = now - timedelta(hours=40)

    conn.execute(
        """INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
           VALUES ('sub_t', 'Test Subject', 'synthetic', 'UTC', ?)""",
        (now.isoformat(),),
    )
    conn.execute(
        """INSERT INTO episodes (
               episode_id, subject_id, thread_id, opened_on, state, step_count,
               baseline_nights, baseline_rung
           ) VALUES (
               'ep_timeout_01', 'sub_t', 'th_01', '2026-08-01', 'AWAITING_USER', 1,
               14, 'PERSONAL'
           )"""
    )
    conn.execute(
        """INSERT INTO interactions (
               id, episode_id, probe_id, question_text, text_source, options_json,
               evsi, interruption_cost, channel, status, asked_at_utc, rejected_json
           ) VALUES (
               'int_old_01', 'ep_timeout_01', 'probe_sym', 'Are you feeling sick?', 'llm',
               '[{"option_id": "yes", "label": "Yes"}]', 0.5, 0.3, 'none', 'PENDING', ?, '[]'
           )""",
        (old_time.isoformat(),),
    )
    conn.commit()
    conn.close()

    # Run episode tick
    with patch("wha.service.scheduler.step_episode") as mock_step:
        res = run_episode_tick(db_path=db_file)
        assert "ep_timeout_01" in res["timed_out_episodes"]
        assert mock_step.called

    # Verify interaction status updated in database
    conn2 = connect(db_file)
    row = conn2.execute("SELECT status FROM interactions WHERE id = 'int_old_01'").fetchone()
    assert row["status"] == "TIMED_OUT"
    conn2.close()


def test_first_run_produces_insufficient_data(tmp_path: Path) -> None:
    """Empty database produces sensible 'learning your normal' / reassuring state without crashing."""
    db_file = tmp_path / "fresh.db"
    conn = connect(db_file)
    apply_schema(conn)
    conn.close()

    # Querying subjects on empty db returns empty list cleanly
    subjects = list_subjects(db_path=db_file)
    assert subjects == []

    # System status returns clean view
    status = get_system_status(db_path=db_file)
    assert status.usable_nights == 0
    assert status.rung == BaselineRung.COLD

    # The Today page used to be rendered here by importing it and patching service
    # functions. It is now an HTTP client of the API, so a screen test that patched the
    # service layer would prove nothing about what the page fetches. The same assertion,
    # that an empty dashboard tells a person nothing is required of them rather than
    # showing a blank page, is made against the real script in
    # tests/ui/test_today.py::test_an_empty_dashboard_says_nothing_is_required_of_you.
