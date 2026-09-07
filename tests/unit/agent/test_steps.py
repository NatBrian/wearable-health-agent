"""The agent's node names are a public interface, so they are checked like one.

They were written out in four places that nothing compared: the agentic entries of
`CANONICAL_PIPELINE_STEPS`, `CANONICAL_STAGES` in `service/episodes.py`, a hardcoded set in
`service/pipeline.py`, and the graph itself. The drift that gap allows has already reached a
person once, when `node_measure` was deleted and the Trace tab went on advertising the stage
to readers as permanently pending.

`wha.agent.steps` is now the one place the names live. These tests are what make that true
rather than merely intended.
"""

from wha.agent.graph import build_agent_graph
from wha.agent.steps import (
    AGENT_NODES,
    NODE_TO_PIPELINE_STEP,
    PRELOAD_TOOLS,
    pipeline_steps_that_ran,
)
from wha.models import CANONICAL_PIPELINE_STEPS, StepLayer


def test_every_node_maps_to_a_real_pipeline_step() -> None:
    """A node reporting as a step the dashboard does not have renders nothing, silently."""
    real = {s.step_id for s in CANONICAL_PIPELINE_STEPS}
    unknown = {
        node: step for node, step in NODE_TO_PIPELINE_STEP.items() if step not in real
    }
    assert not unknown, f"nodes mapped to steps that do not exist: {unknown}"


def test_every_node_is_mapped() -> None:
    """An unmapped node is dropped from the audit view rather than reported."""
    assert set(AGENT_NODES) == set(NODE_TO_PIPELINE_STEP), (
        "AGENT_NODES and NODE_TO_PIPELINE_STEP disagree: "
        f"{set(AGENT_NODES) ^ set(NODE_TO_PIPELINE_STEP)}"
    )


def test_the_graph_registers_exactly_the_nodes_declared_here() -> None:
    """The check that makes the rest of this file worth anything.

    Adding a node to the graph without naming it here would leave it invisible to the
    pipeline view: the investigation would run a step that no screen could report. Reading
    the compiled graph rather than the source means the assertion cannot be satisfied by
    updating a list and forgetting the wiring, or the reverse.
    """
    graph = build_agent_graph()
    registered = {name for name in graph.nodes if not name.startswith("__")}

    assert registered == set(AGENT_NODES), (
        "the graph and wha.agent.steps disagree about which nodes exist. "
        f"only in the graph: {sorted(registered - set(AGENT_NODES))}; "
        f"only in AGENT_NODES: {sorted(set(AGENT_NODES) - registered)}"
    )


def test_agent_nodes_are_all_agentic_steps() -> None:
    """`answer` is the person's step and `deliver` has no node. Neither may appear here."""
    layers = {s.step_id: s.layer for s in CANONICAL_PIPELINE_STEPS}
    misfiled = {
        node: layers[step].value
        for node, step in NODE_TO_PIPELINE_STEP.items()
        if layers.get(step) is not StepLayer.AGENTIC
    }
    assert not misfiled, f"nodes reporting as non-agentic steps: {misfiled}"


def test_a_trace_naming_a_node_that_no_longer_exists_is_dropped() -> None:
    """Traces outlive the graph that wrote them.

    An episode investigated by an older graph can name a node this one does not have.
    Showing a person a step of their own investigation that the system can no longer
    explain is worse than showing them nothing, so it is dropped rather than passed
    through. "measure" is the real example: `node_measure` was deleted on 5 September 2026
    and episodes recorded before that still name it.
    """
    assert pipeline_steps_that_ran(["preload", "measure", "believe"]) == {
        "preload",
        "believe",
    }


def test_a_missing_or_malformed_trace_field_yields_no_steps() -> None:
    """`nodes_ran` is JSON out of a database column, so it is not guaranteed to be a list."""
    assert pipeline_steps_that_ran(None) == set()
    assert pipeline_steps_that_ran("preload") == set()
    assert pipeline_steps_that_ran([]) == set()


def test_the_preload_tools_are_the_ones_preload_actually_calls() -> None:
    """The set was written out twice, here and in the node, and nothing compared them.

    A tool added to `node_preload` and not to `PRELOAD_TOOLS` would be read by the pipeline
    view as evidence that the model had chosen it, which reports an investigation loop that
    never ran.
    """
    from pathlib import Path

    source = Path("src/wha/agent/nodes/preload.py").read_text(encoding="utf-8")
    missing = [tool for tool in PRELOAD_TOOLS if f'"{tool}"' not in source]
    assert not missing, f"named in PRELOAD_TOOLS but not called by node_preload: {missing}"
