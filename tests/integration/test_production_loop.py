"""The three links that turn detection and the agent into one closed production loop.

Each test here corresponds to a defect where the code existed and never ran: an episode
that opened and was never stepped, a Telegram reply that was never read, and an answer
that was accepted and then dropped because the repository lacked the method the receiver
reached for through ``hasattr``.
"""

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from wha.agent.repository import EpisodeRepository
from wha.db import connect
from wha.db.iso import to_iso
from wha.db.migrations import apply_schema
from wha.service.scheduler import create_scheduler, poll_telegram_once, run_episode_tick


def _make_db(tmp_path: Path) -> Path:
    db_file = tmp_path / "loop.db"
    conn = connect(db_file)
    apply_schema(conn)
    conn.execute(
        """INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
           VALUES ('me', 'me', 'live', 'Asia/Singapore', ?)""",
        (to_iso(datetime.now(UTC)),),
    )
    conn.commit()
    conn.close()
    return db_file


def _open_episode(db_file: Path, episode_id: str = "ep_test") -> None:
    conn = connect(db_file)
    conn.execute(
        """INSERT INTO episodes
             (episode_id, subject_id, thread_id, opened_on, state, baseline_nights,
              baseline_rung, step_count, tool_call_count, depth_used)
           VALUES (?, 'me', ?, ?, 'OPEN', 28, 'MATURE', 0, 0, 0)""",
        (episode_id, episode_id, date(2026, 9, 5).isoformat()),
    )
    conn.commit()
    conn.close()


def _add_interaction(db_file: Path, episode_id: str, probe_id: str, int_id: str) -> None:
    conn = connect(db_file)
    conn.execute(
        """INSERT INTO interactions
             (id, episode_id, probe_id, question_text, text_source, options_json, evsi,
              interruption_cost, rejected_json, channel, asked_at_utc, status)
           VALUES (?, ?, ?, 'Any fever?', 'fallback', '[]', 0.2, 0.15, '[]', 'telegram',
                   ?, 'PENDING')""",
        (int_id, episode_id, probe_id, to_iso(datetime.now(UTC))),
    )
    conn.commit()
    conn.close()


# -- 1. a freshly opened episode is advanced, not left at step_count 0 ---------------


def test_episode_tick_advances_an_open_episode_that_never_timed_out(tmp_path: Path) -> None:
    """The tick used to iterate only timed-out episodes, so a new one was never stepped."""
    db_file = _make_db(tmp_path)
    _open_episode(db_file)

    stepped: list[str] = []

    def fake_step(episode_id: str, **kwargs: Any) -> dict[str, Any]:
        stepped.append(episode_id)
        conn = kwargs.get("conn")
        assert conn is not None
        conn.execute(
            "UPDATE episodes SET state = 'CLOSED', disposition = 'BENIGN' WHERE episode_id = ?",
            (episode_id,),
        )
        conn.commit()
        return {"status": "ok"}

    with (
        patch("wha.service.scheduler.step_episode", side_effect=fake_step),
        patch("wha.agent.graph.get_agent_graph", return_value=object()),
        patch("wha.agent.graph.get_pending_interrupt", return_value=None),
    ):
        result = run_episode_tick(db_path=db_file)

    assert stepped == ["ep_test"], "a newly opened episode must be advanced by the tick"
    assert result["advanced_episodes"] == ["ep_test"]


def test_episode_tick_leaves_an_unanswered_question_parked(tmp_path: Path) -> None:
    """Waiting on the person is correct. The tick must not answer on their behalf."""
    db_file = _make_db(tmp_path)
    _open_episode(db_file)
    _add_interaction(db_file, "ep_test", "fever", "int_1")

    stepped: list[str] = []

    with (
        patch("wha.service.scheduler.step_episode", side_effect=lambda *a, **k: stepped.append(1)),
        patch("wha.agent.graph.get_agent_graph", return_value=object()),
        patch(
            "wha.agent.graph.get_pending_interrupt",
            return_value={"kind": "question", "probe_id": "fever"},
        ),
    ):
        result = run_episode_tick(db_path=db_file)

    assert stepped == [], "an unanswered question must stay parked"
    assert result["advanced_episodes"] == []


def test_episode_tick_resumes_once_the_answer_is_recorded(tmp_path: Path) -> None:
    """An answer recorded by the receiver is what un-parks the graph."""
    db_file = _make_db(tmp_path)
    _open_episode(db_file)
    _add_interaction(db_file, "ep_test", "fever", "int_1")

    conn = connect(db_file)
    EpisodeRepository(conn=conn).record_interaction_answer("int_1", option_id="yes")
    conn.close()

    resumed: list[Any] = []

    def fake_step(episode_id: str, **kwargs: Any) -> dict[str, Any]:
        resumed.append(kwargs.get("resume"))
        c = kwargs["conn"]
        c.execute("UPDATE episodes SET state = 'CLOSED' WHERE episode_id = ?", (episode_id,))
        c.commit()
        return {"status": "ok"}

    with (
        patch("wha.service.scheduler.step_episode", side_effect=fake_step),
        patch("wha.agent.graph.get_agent_graph", return_value=object()),
        patch(
            "wha.agent.graph.get_pending_interrupt",
            return_value={"kind": "question", "probe_id": "fever"},
        ),
    ):
        run_episode_tick(db_path=db_file)

    assert resumed == [{"probe_id": "fever", "option_id": "yes"}]


# -- 2. the receive half of Telegram is registered and reachable ---------------------


def test_scheduler_registers_a_telegram_polling_job() -> None:
    """Three jobs were registered while the docstring named four; the listener was absent."""
    scheduler = create_scheduler()
    try:
        job_ids = {j.id for j in scheduler.get_jobs()}
    finally:
        scheduler.shutdown(wait=False) if scheduler.running else None
    assert {"ingest", "nightly", "episode_tick", "telegram_poll"} <= job_ids


def test_poll_telegram_is_a_no_op_when_telegram_is_not_configured(tmp_path: Path) -> None:
    """A missing token must degrade to 'not polled', never raise inside a scheduler job."""
    db_file = _make_db(tmp_path)

    class _Settings:
        telegram_bot_token = None
        telegram_chat_id = None

    with patch("wha.config.get_settings", return_value=_Settings()):
        result = poll_telegram_once(db_path=db_file)

    assert result["polled"] is False


# -- 3. the repository implements what the receiver reaches for ----------------------


@pytest.mark.parametrize(
    "method",
    [
        "get_pending_interaction_for_chat",
        "record_interaction_answer",
        "record_interaction_declined",
        "get_telegram_offset",
        "set_telegram_offset",
    ],
)
def test_repository_implements_every_method_the_receiver_probes(method: str) -> None:
    """TelegramReceiver guards each of these with hasattr, so a missing one fails silently."""
    assert hasattr(EpisodeRepository, method), f"TelegramReceiver would silently skip {method}"


def test_recording_an_answer_marks_the_interaction_answered(tmp_path: Path) -> None:
    db_file = _make_db(tmp_path)
    _open_episode(db_file)
    _add_interaction(db_file, "ep_test", "fever", "int_1")

    conn = connect(db_file)
    repo = EpisodeRepository(conn=conn)

    pending = repo.get_pending_interaction_for_chat("8404206541")
    assert pending is not None and pending["id"] == "int_1"

    repo.record_interaction_answer("int_1", free_text="felt hot last night")
    row = conn.execute("SELECT status, free_text FROM interactions WHERE id = 'int_1'").fetchone()
    assert row["status"] == "ANSWERED"
    assert row["free_text"] == "felt hot last night"

    # A second answer must not overwrite the first: the guard is on status = 'PENDING'.
    repo.record_interaction_answer("int_1", free_text="changed my mind")
    row = conn.execute("SELECT free_text FROM interactions WHERE id = 'int_1'").fetchone()
    assert row["free_text"] == "felt hot last night"
    assert repo.get_pending_interaction_for_chat() is None
    conn.close()


def test_declining_consumes_the_interruption_without_recording_an_answer(tmp_path: Path) -> None:
    db_file = _make_db(tmp_path)
    _open_episode(db_file)
    _add_interaction(db_file, "ep_test", "fever", "int_1")

    conn = connect(db_file)
    EpisodeRepository(conn=conn).record_interaction_declined("int_1")
    row = conn.execute(
        "SELECT status, answer_option_id FROM interactions WHERE id = 'int_1'"
    ).fetchone()
    assert row["status"] == "DECLINED"
    assert row["answer_option_id"] is None
    conn.close()


def test_telegram_offset_survives_a_restart(tmp_path: Path) -> None:
    """An in-memory offset meant every restart reprocessed the same updates."""
    db_file = _make_db(tmp_path)

    conn = connect(db_file)
    repo = EpisodeRepository(conn=conn)
    assert repo.get_telegram_offset() == 0
    repo.set_telegram_offset(41)
    repo.set_telegram_offset(42)
    conn.close()

    conn = connect(db_file)
    assert EpisodeRepository(conn=conn).get_telegram_offset() == 42
    conn.close()


def test_episode_tick_stops_when_the_agent_decides_to_observe(tmp_path: Path) -> None:
    """OBSERVE leaves the graph settled with nothing next and nobody to wait on.

    step_count increments on every call, so a "did the counter move" check cannot see
    this: the tick re-ran a settled episode until it hit the step ceiling, spending an
    LLM call each time.
    """
    db_file = _make_db(tmp_path)
    _open_episode(db_file)

    calls: list[int] = []

    def fake_step(episode_id: str, **kwargs: Any) -> dict[str, Any]:
        calls.append(1)
        c = kwargs["conn"]
        c.execute(
            "UPDATE episodes SET step_count = step_count + 1 WHERE episode_id = ?",
            (episode_id,),
        )
        c.commit()
        return {"status": "ok"}

    class _SettledGraph:
        def get_state(self, _config: Any) -> Any:
            return type("Snap", (), {"next": (), "tasks": ()})()

    with (
        patch("wha.service.scheduler.step_episode", side_effect=fake_step),
        patch("wha.agent.graph.get_agent_graph", return_value=_SettledGraph()),
        patch("wha.agent.graph.get_pending_interrupt", return_value=None),
    ):
        run_episode_tick(db_path=db_file)

    assert len(calls) == 1, f"a settled episode must be stepped once, not {len(calls)} times"
