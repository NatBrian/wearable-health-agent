"""Agent state graph construction, checkpointer configuration, and execution loop."""

import functools
import inspect
import sqlite3
from pathlib import Path
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from wha.agent.nodes import (
    node_ask,
    node_believe,
    node_conclude,
    node_critique,
    node_decide,
    node_investigate,
    node_preload,
    node_review,
)
from wha.agent.state import EpisodeState
from wha.config import get_db_path
from wha.constants import EPISODE_MAX_STEPS, MAX_TOOL_CALLS_PER_EPISODE
from wha.models import ActionKind


def route_after_ask(state: EpisodeState) -> str:
    """Route an answer back through investigation so the agent can look things up.

    A safety escalation goes straight to the outcome. red_flags.yaml requires the
    deterministic floor to be unreachable by reasoning, so an answer that trips it must
    not be handed to the belief model or the policy.

    Otherwise the answer re-enters ``investigate``. This edge is what makes the loop
    hypothesis-driven rather than single-shot. Before it existed, evidence was gathered
    exactly once, before the person had said anything, so ``retrieve_clinical_evidence``
    had nothing to look up and fired zero times in 145 tool calls, and after an answer the
    agent could only re-run arithmetic over the same facts.

    ``MAX_TOOL_CALLS_PER_EPISODE`` is the ceiling that keeps this bounded. Once it is
    reached the answer goes straight to ``believe``: re-entering investigation would run
    no tools and spend an LLM round trip to learn that.
    """
    action = state.get("action")
    if action is not None and action.kind == ActionKind.ESCALATE:
        return "conclude"
    if state.get("tool_call_count", 0) >= MAX_TOOL_CALLS_PER_EPISODE:
        return "believe"
    return "investigate"


def route_after_decide(state: EpisodeState) -> str:
    """Route graph to next execution step based on selected ActionKind."""
    action = state.get("action")
    if action is None:
        return "conclude"

    if action.kind == ActionKind.ASK:
        return "ask"
    elif action.kind == ActionKind.OBSERVE:
        return END
    else:
        # CONCLUDE or ESCALATE routes to outcome drafting
        return "conclude"


_CHECKPOINT_SAVERS: dict[Path, SqliteSaver] = {}
_GRAPH_CACHE: dict[Path, CompiledStateGraph] = {}


def get_sqlite_checkpointer(db_path: Path | None = None) -> SqliteSaver:
    """Return the durable checkpointer for a database, opening it once per path.

    Episode state must outlive the process. An episode parks on an ``interrupt()``
    waiting for a human answer that may take hours or days, and the scheduler runs it
    in ticks. An in-memory saver discards that state the moment the call returns, so
    the interrupt could never be resumed and every tick would restart from START.
    Checkpoints live in the application database so that deleting it removes the agent's
    memory of a subject along with their data.
    """
    path = db_path if db_path is not None else get_db_path()
    saver = _CHECKPOINT_SAVERS.get(path)
    if saver is None:
        path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False: the scheduler thread and the dashboard share this saver.
        conn = sqlite3.connect(str(path), check_same_thread=False)
        saver = SqliteSaver(conn)
        saver.setup()
        _CHECKPOINT_SAVERS[path] = saver
    return saver


def get_agent_graph(
    db_path: Path | None = None,
    notifier: Any = None,
) -> CompiledStateGraph:
    """Return the compiled graph for a database, built once and reused across ticks."""
    path = db_path if db_path is not None else get_db_path()
    graph = _GRAPH_CACHE.get(path)
    if graph is None:
        from wha.agent.repository import EpisodeRepository
        from wha.notify import get_notifier

        graph = build_agent_graph(
            checkpointer=get_sqlite_checkpointer(path),
            db=EpisodeRepository(db_path=path),
            notifier=notifier if notifier is not None else get_notifier(),
        )
        _GRAPH_CACHE[path] = graph
    return graph


def build_agent_graph(
    checkpointer: BaseCheckpointSaver | None = None,
    db: Any = None,
    notifier: Any = None,
) -> CompiledStateGraph:
    """Construct and compile the agent StateGraph.

    Callers that need durability across process restarts should pass a checkpointer, or
    use :func:`get_agent_graph`. The in-memory default exists only for tests that build
    and drive a graph within a single process.

    ``db`` and ``notifier`` are bound into the nodes here. LangGraph calls a node with
    state alone, so a node's remaining parameters keep their defaults unless they are
    bound at build time. Leaving them unbound meant every node ran with ``db=None``, the
    tools read no data, and nothing the agent produced was ever persisted.
    """
    saver = checkpointer if checkpointer is not None else MemorySaver()

    builder = StateGraph(EpisodeState)

    def bind(node: Any) -> Any:
        """Bind the shared dependencies a node accepts, leaving its signature intact."""
        kwargs: dict[str, Any] = {}
        parameters = inspect.signature(node).parameters
        if "db" in parameters and db is not None:
            kwargs["db"] = db
        if "notifier" in parameters and notifier is not None:
            kwargs["notifier"] = notifier
        return functools.partial(node, **kwargs) if kwargs else node

    builder.add_node("preload", bind(node_preload))
    builder.add_node("investigate", bind(node_investigate))
    builder.add_node("believe", bind(node_believe))
    builder.add_node("decide", bind(node_decide))
    builder.add_node("ask", bind(node_ask))
    builder.add_node("conclude", bind(node_conclude))
    builder.add_node("critique", bind(node_critique))
    builder.add_node("review", bind(node_review))

    builder.add_edge(START, "preload")
    builder.add_edge("preload", "investigate")
    builder.add_edge("investigate", "believe")
    builder.add_edge("believe", "decide")

    builder.add_conditional_edges(
        "decide",
        route_after_decide,
        {
            "ask": "ask",
            "conclude": "conclude",
            END: END,
        },
    )

    builder.add_conditional_edges(
        "ask",
        route_after_ask,
        {"conclude": "conclude", "believe": "believe", "investigate": "investigate"},
    )
    builder.add_edge("conclude", "critique")
    builder.add_edge("critique", "review")
    builder.add_edge("review", END)

    return builder.compile(checkpointer=saver)


def _has_checkpoint(graph: CompiledStateGraph, config: dict[str, Any]) -> bool:
    """True when this thread already has saved state to resume from.

    An unknown thread yields an empty snapshot with ``created_at`` unset rather than
    raising, so absence and presence are distinguished by that field alone.
    """
    snapshot = graph.get_state(config)
    return snapshot is not None and snapshot.created_at is not None


def get_pending_interrupt(
    graph: CompiledStateGraph,
    episode_id: str,
) -> Any | None:
    """The payload of the interrupt this episode is parked on, or None if it is running."""
    snapshot = graph.get_state({"configurable": {"thread_id": episode_id}})
    for task in getattr(snapshot, "tasks", ()) or ():
        for pending in getattr(task, "interrupts", ()) or ():
            return pending.value
    return None


def run_episode_step(
    graph: CompiledStateGraph,
    episode_id: str,
    initial_state: dict[str, Any] | None = None,
    recursion_limit: int = EPISODE_MAX_STEPS,
    resume: Any = None,
    restart: bool = False,
) -> dict[str, Any]:
    """Execute graph steps under configured recursion limit, closing as unresolved on recursion limit.

    ``resume`` supplies the value an ``interrupt()`` is waiting for, which is how an
    answer, a measurement or a review decision re-enters the graph.
    """
    config = {
        "configurable": {"thread_id": episode_id},
        "recursion_limit": recursion_limit,
    }

    # A thread that already holds a checkpoint must be resumed, not restarted. Passing a
    # state dict re-enters the graph at START, which discards the interrupt the episode is
    # parked on and loses every belief, answer and piece of evidence gathered so far.
    payload: Any = initial_state or {}
    if resume is not None:
        payload = Command(resume=resume)
    elif restart:
        # Deliberately re-enter at START with the evidence as it now stands. An episode
        # that chose OBSERVE parks with no pending interrupt and nothing left to run, so
        # invoking it again with None executes no nodes and the belief never moves however
        # many further nights arrive. Answers already given are read back from the database
        # by the nodes, so nothing the person told us is lost by starting the graph again.
        payload = initial_state or {}
    elif _has_checkpoint(graph, config):
        payload = None

    try:
        result = graph.invoke(payload, config=config)
        return dict(result)
    except GraphRecursionError:
        # GraphRecursionError caught and handled: mark episode status as unresolved
        return {
            "episode_id": episode_id,
            "status": "unresolved",
            "step": recursion_limit,
        }
