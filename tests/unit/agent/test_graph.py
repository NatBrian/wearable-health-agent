"""Unit tests for agent graph compilation, state reducers, and recursion limits."""

from datetime import date

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph

from wha.agent import (
    EpisodeState,
    add_nights,
    build_agent_graph,
    run_episode_step,
)
from wha.models import Detection, DetectionLevel, Forecast


def test_graph_compiles_with_checkpointer() -> None:
    """Agent graph compiles successfully with checkpointer and thread-scoped state."""
    saver = MemorySaver()
    graph = build_agent_graph(checkpointer=saver)

    initial_state = {
        "episode_id": "ep_test_compile",
        "subject_id": "sub_001",
        "step": 0,
    }

    result = run_episode_step(graph, "ep_test_compile", initial_state)
    assert result["step"] >= 1


def test_state_reducers_dedupe_nights() -> None:
    """add_nights reducer merges new detections and dedupes by night_date."""
    d1 = Detection(
        subject_id="sub_001",
        night_date=date(2026, 8, 20),
        level=DetectionLevel.YELLOW,
        flagged=False,
        residual_bpm=3.1,
        robust_z=1.8,
        forecast=Forecast(),
    )
    d2 = Detection(
        subject_id="sub_001",
        night_date=date(2026, 8, 21),
        level=DetectionLevel.RED,
        flagged=True,
        residual_bpm=4.5,
        robust_z=2.6,
        forecast=Forecast(),
    )
    d2_duplicate = Detection(
        subject_id="sub_001",
        night_date=date(2026, 8, 21),
        level=DetectionLevel.RED,
        flagged=True,
        residual_bpm=4.6,
        robust_z=2.7,
        forecast=Forecast(),
    )
    d3 = Detection(
        subject_id="sub_001",
        night_date=date(2026, 8, 22),
        level=DetectionLevel.RED,
        flagged=True,
        residual_bpm=4.2,
        robust_z=2.5,
        forecast=Forecast(),
    )

    left = [d1, d2]
    right = [d2_duplicate, d3]

    merged = add_nights(left, right)
    assert len(merged) == 3
    assert [d.night_date for d in merged] == [
        date(2026, 8, 20),
        date(2026, 8, 21),
        date(2026, 8, 22),
    ]


def test_recursion_limit_closes_unresolved() -> None:
    """When graph loop hits recursion limit, GraphRecursionError is caught and status set to unresolved."""
    # Create an infinite looping graph
    builder = StateGraph(EpisodeState)

    def loop_node_a(state: EpisodeState) -> dict:
        return {"step": state.get("step", 0) + 1}

    def loop_node_b(state: EpisodeState) -> dict:
        return {"step": state.get("step", 0) + 1}

    builder.add_node("node_a", loop_node_a)
    builder.add_node("node_b", loop_node_b)

    builder.add_edge("node_a", "node_b")
    builder.add_edge("node_b", "node_a")
    builder.set_entry_point("node_a")

    saver = MemorySaver()
    looping_graph = builder.compile(checkpointer=saver)

    # Set low recursion limit of 4 to test catch & unresolved closure
    result = run_episode_step(
        looping_graph,
        episode_id="ep_recursion_test",
        initial_state={"step": 0},
        recursion_limit=4,
    )

    assert result["status"] == "unresolved"
    assert result["episode_id"] == "ep_recursion_test"
