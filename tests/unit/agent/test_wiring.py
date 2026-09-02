"""Tests for the dependency wiring the agent graph depends on to function at all.

Each of these covers a defect that left the agent running and silently hollow: it
compiled, executed, produced output and passed every other test, while reading no data,
persisting nothing and forgetting its state between ticks.
"""

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from wha.agent.graph import build_agent_graph, get_agent_graph, get_sqlite_checkpointer
from wha.agent.nodes import node_preload
from wha.agent.repository import EpisodeRepository
from wha.db import apply_schema, connect
from wha.models import BaselineRung


@pytest.fixture
def seeded_db(tmp_path):
    """A database with one subject, three nights of features and a baseline."""
    db_file = tmp_path / "wiring.sqlite"
    conn = connect(db_file)
    apply_schema(conn)
    conn.execute(
        """INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
           VALUES ('sub_wire', 'Wiring', 'synthetic', 'Asia/Singapore', '2026-08-01T00:00:00Z')"""
    )
    # Dated relative to today, because node_preload defaults its read window to the last
    # fourteen days when the state carries no nights.
    today = datetime.now(UTC).date()
    nights = [today - timedelta(days=offset) for offset in (3, 2, 1)]
    for night, rhr in zip(nights, (58.0, 59.0, 63.0), strict=True):
        conn.execute(
            """INSERT INTO nightly_features
                 (subject_id, night_date, rhr_bpm, coverage_minutes, usable,
                  steps_prev_day, sleep_hours, exercise_end_offset_h, computed_at_utc)
               VALUES ('sub_wire', ?, ?, 300, 1, 6000, 7.0, NULL, '2026-08-04T00:00:00Z')""",
            (night.isoformat(), rhr),
        )
    conn.execute(
        """INSERT INTO baselines
             (subject_id, night_date, centre_bpm, scale_bpm, usable_nights, rung, shrink_weight)
           VALUES ('sub_wire', ?, 58.5, 1.2, 3, 'PRIOR_DOMINATED', 0.4)""",
        (nights[-1].isoformat(),),
    )
    conn.commit()
    return db_file, conn, nights


def test_checkpoint_survives_a_new_graph_instance(tmp_path) -> None:
    """State written by one graph must be visible to the next.

    step_episode builds a graph per tick. With an in-memory saver every tick began from
    an empty checkpoint, so an episode parked on an interrupt could never be resumed.
    """
    db_file = tmp_path / "cp.sqlite"
    config = {"configurable": {"thread_id": "ep_persist"}}

    first = build_agent_graph(checkpointer=get_sqlite_checkpointer(db_file))
    first.update_state(config, {"episode_id": "ep_persist", "step": 7})

    # A genuinely separate saver and graph over the same file, as a later process would build.
    reopened = build_agent_graph(
        checkpointer=type(get_sqlite_checkpointer(db_file))(
            sqlite3.connect(str(db_file), check_same_thread=False)
        )
    )
    restored = reopened.get_state(config)

    assert restored.values.get("step") == 7
    assert restored.created_at is not None


def test_graph_binds_a_repository_into_its_nodes(tmp_path) -> None:
    """get_agent_graph must supply the db object the nodes and tools read through."""
    graph = get_agent_graph(tmp_path / "bound.sqlite")

    preload = graph.nodes["preload"]
    bound = getattr(preload, "bound", None) or getattr(preload, "runnable", None)
    assert bound is not None, "preload node exposes no bound callable"

    keywords = getattr(bound, "keywords", None) or getattr(
        getattr(bound, "func", None), "keywords", {}
    )
    assert keywords, "no dependencies bound into the preload node"
    assert keywords.get("db") is not None, "db was not bound, so every tool reads nothing"


def test_repository_reads_real_rows(seeded_db) -> None:
    """The adapter returns the subject's actual data, not the empty default."""
    _db_file, conn, nights = seeded_db
    repo = EpisodeRepository(conn=conn)

    features = repo.get_nightly_features("sub_wire", nights[0], nights[-1])
    assert len(features) == 3
    assert features[-1].rhr_bpm == 63.0

    baseline = repo.get_baseline("sub_wire", nights[-1])
    assert baseline is not None
    assert baseline.rung == BaselineRung.PRIOR_DOMINATED
    assert repo.get_baseline_rung("sub_wire", nights[-1]) == BaselineRung.PRIOR_DOMINATED

    # An unknown subject must degrade to COLD, never to an assumed mature baseline.
    assert repo.get_baseline_rung("nobody", nights[-1]) == BaselineRung.COLD


def test_preload_reads_data_when_given_a_repository(seeded_db) -> None:
    """With a repository bound, preload returns real features rather than an empty read."""
    _db_file, conn, _nights = seeded_db
    repo = EpisodeRepository(conn=conn)

    result = node_preload({"subject_id": "sub_wire", "episode_id": "ep_wire", "step": 0}, db=repo)
    preloaded = result["preloaded"]

    assert preloaded["nightly_features"], "preload read no features despite rows existing"
    assert preloaded["personal_baseline"] is not None


def test_belief_round_trip_keeps_the_joint_state(seeded_db) -> None:
    """A stored belief must return with its joint log-posterior.

    Without it, EVSI falls back to a projection that scores every non-infection probe at
    exactly zero, so the policy silently stops asking about alcohol, exercise or stress.
    """
    from wha.belief import update_belief
    from wha.service.episodes import get_episode

    _db_file, conn, nights = seeded_db
    repo = EpisodeRepository(conn=conn)

    belief = update_belief(episode_nights=[], features=[], answers=[], measurements=[])
    assert len(belief.state_logprob) == 4096

    conn.execute(
        """INSERT INTO episodes
             (episode_id, subject_id, thread_id, opened_on, state,
              baseline_nights, baseline_rung, step_count)
           VALUES ('ep_belief', 'sub_wire', 'ep_belief', ?, 'OPEN',
                   3, 'PRIOR_DOMINATED', 1)""",
        (nights[-1].isoformat(),),
    )
    conn.commit()
    repo.append_belief("ep_belief", "sub_wire", belief, trigger="test")

    detail = get_episode("ep_belief", conn=conn)
    _seq, _trigger, restored = detail.belief_history[0]
    assert len(restored.state_logprob) == 4096
