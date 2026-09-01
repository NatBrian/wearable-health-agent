"""Agent state graph construction, checkpointer configuration, and execution loop."""

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from wha.agent.state import EpisodeState
from wha.constants import EPISODE_MAX_STEPS


def node_stub_preload(state: EpisodeState) -> dict[str, Any]:
    """Stub preload node for graph compilation."""
    return {"preloaded": state.get("preloaded", {})}


def node_stub_investigate(state: EpisodeState) -> dict[str, Any]:
    """Stub investigate node for graph compilation."""
    return {"step": state.get("step", 0) + 1}


def build_agent_graph(
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Construct and compile the agent StateGraph."""
    saver = checkpointer if checkpointer is not None else MemorySaver()

    builder = StateGraph(EpisodeState)

    builder.add_node("preload", node_stub_preload)
    builder.add_node("investigate", node_stub_investigate)

    builder.add_edge(START, "preload")
    builder.add_edge("preload", "investigate")
    builder.add_edge("investigate", END)

    return builder.compile(checkpointer=saver)


def run_episode_step(
    graph: CompiledStateGraph,
    episode_id: str,
    initial_state: dict[str, Any] | None = None,
    recursion_limit: int = EPISODE_MAX_STEPS,
) -> dict[str, Any]:
    """Execute graph steps under configured recursion limit, closing as unresolved on recursion limit."""
    config = {
        "configurable": {"thread_id": episode_id},
        "recursion_limit": recursion_limit,
    }

    try:
        result = graph.invoke(initial_state or {}, config=config)
        return dict(result)
    except GraphRecursionError:
        # GraphRecursionError caught and handled: mark episode status as unresolved
        return {
            "episode_id": episode_id,
            "status": "unresolved",
            "step": recursion_limit,
        }
