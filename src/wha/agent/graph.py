"""Agent state graph construction, checkpointer configuration, and execution loop."""

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from wha.agent.nodes import (
    node_ask,
    node_believe,
    node_decide,
    node_investigate,
    node_measure,
    node_preload,
)
from wha.agent.state import EpisodeState
from wha.constants import EPISODE_MAX_STEPS
from wha.models import ActionKind


def route_after_decide(state: EpisodeState) -> str:
    """Route graph to next execution step based on selected ActionKind."""
    action = state.get("action")
    if action is None:
        return END

    if action.kind == ActionKind.ASK:
        return "ask"
    elif action.kind == ActionKind.MEASURE:
        return "measure"
    else:
        # OBSERVE, CONCLUDE, ESCALATE terminate graph step
        return END


def build_agent_graph(
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Construct and compile the agent StateGraph."""
    saver = checkpointer if checkpointer is not None else MemorySaver()

    builder = StateGraph(EpisodeState)

    builder.add_node("preload", node_preload)
    builder.add_node("investigate", node_investigate)
    builder.add_node("believe", node_believe)
    builder.add_node("decide", node_decide)
    builder.add_node("ask", node_ask)
    builder.add_node("measure", node_measure)

    builder.add_edge(START, "preload")
    builder.add_edge("preload", "investigate")
    builder.add_edge("investigate", "believe")
    builder.add_edge("believe", "decide")

    builder.add_conditional_edges(
        "decide",
        route_after_decide,
        {
            "ask": "ask",
            "measure": "measure",
            END: END,
        },
    )

    builder.add_edge("ask", "believe")
    builder.add_edge("measure", "believe")

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
