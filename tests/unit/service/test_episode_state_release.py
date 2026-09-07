"""An episode must not sit at "waiting for you" when it is waiting for a night."""

from unittest.mock import MagicMock, patch

from wha.db import connect
from wha.db.migrations import apply_schema
from wha.service.episodes import step_episode


def _episode(state: str = "AWAITING_USER"):
    conn = connect(":memory:")
    apply_schema(conn)
    conn.execute(
        "INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc) "
        "VALUES ('sim', 'Simulated', 'synthetic', 'Asia/Singapore', '2026-07-01T00:00:00+00:00')"
    )
    conn.execute(
        """INSERT INTO episodes
           (episode_id, subject_id, thread_id, opened_on, state, baseline_nights,
            baseline_rung, step_count)
           VALUES ('ep_1', 'sim', 'ep_1', '2026-09-08', ?, 28, 'MATURE', 3)""",
        (state,),
    )
    conn.commit()
    return conn


def test_a_parked_state_is_released_when_the_graph_is_no_longer_parked() -> None:
    """The policy chose to observe, which means wait for another night, and the graph
    ended. The row still said "waiting for your answer" from when the question was sent,
    so the screen asked the person for something that no longer existed and every later
    tick ran no nodes while still counting as progress.
    """
    conn = _episode()

    with (
        patch("wha.agent.graph.get_agent_graph", return_value=MagicMock()),
        patch("wha.agent.graph.run_episode_step", return_value={}),
        patch("wha.agent.graph.get_pending_interrupt", return_value=None),
    ):
        result = step_episode("ep_1", conn=conn)

    assert result["state"] == "OPEN"
    assert (
        conn.execute("SELECT state FROM episodes WHERE episode_id='ep_1'").fetchone()[0] == "OPEN"
    )


def test_an_episode_still_parked_on_a_question_stays_parked() -> None:
    """The counterpart. Releasing a state that IS waiting on the person would hide a
    question they still need to answer."""
    conn = _episode()
    conn.execute(
        """INSERT INTO interactions
           (id, episode_id, probe_id, question_text, text_source, options_json, evsi,
            interruption_cost, rejected_json, channel, asked_at_utc, status)
           VALUES ('int_1', 'ep_1', 'probe_symptoms', 'Any symptoms?', 'llm', '[]', 0.4,
                   0.015, '[]', 'telegram', '2026-09-08T13:42:00Z', 'PENDING')"""
    )
    conn.commit()

    with (
        patch("wha.agent.graph.get_agent_graph", return_value=MagicMock()),
        patch("wha.agent.graph.run_episode_step", return_value={}),
        patch("wha.agent.graph.get_pending_interrupt", return_value=None),
    ):
        step_episode("ep_1", conn=conn)

    state = conn.execute("SELECT state FROM episodes WHERE episode_id='ep_1'").fetchone()[0]
    assert state == "AWAITING_USER"
