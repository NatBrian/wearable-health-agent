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
    node_conclude,
    node_critique,
    node_decide,
    node_investigate,
    node_measure,
    node_preload,
    node_review,
)
from wha.agent.state import EpisodeState
from wha.constants import EPISODE_MAX_STEPS
from wha.models import ActionKind


def route_after_decide(state: EpisodeState) -> str:
    """Route graph to next execution step based on selected ActionKind."""
    action = state.get("action")
    if action is None:
        return "conclude"

    if action.kind == ActionKind.ASK:
        return "ask"
    elif action.kind == ActionKind.MEASURE:
        return "measure"
    elif action.kind == ActionKind.OBSERVE:
        return END
    else:
        # CONCLUDE or ESCALATE routes to outcome drafting
        return "conclude"


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
    builder.add_node("conclude", node_conclude)
    builder.add_node("critique", node_critique)
    builder.add_node("review", node_review)

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
            "conclude": "conclude",
            END: END,
        },
    )

    builder.add_edge("ask", "believe")
    builder.add_edge("measure", "believe")
    builder.add_edge("conclude", "critique")
    builder.add_edge("critique", "review")
    builder.add_edge("review", END)

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
