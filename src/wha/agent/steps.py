"""The agent's node names, and the public pipeline steps they report as.

The graph's node names are a public interface: the audit view and the Trace tab both render
them. This module is the single place they are declared, so that restructuring the agent
does not require edits in ``models.py``, ``service/pipeline.py`` and ``service/episodes.py``,
which previously each held their own copy.

It holds names only: no queries, no rendering, no behaviour. ``service/pipeline.py`` keeps
its SQL and ``service/episodes.py`` keeps its stage descriptions, and both read the names
from here.

**To restructure the agent**, change this file first. Rename, split or add nodes and map each
onto the public step it reports as; ``NODE_TO_PIPELINE_STEP`` keeps the two vocabularies
independent, so the screens are unaffected.

``tests/unit/agent/test_steps.py`` checks that every mapped step exists in
``CANONICAL_PIPELINE_STEPS`` and that the nodes registered in ``build_agent_graph`` are
exactly ``AGENT_NODES``, so a node added to the graph but not declared here fails the build.
"""

# The graph's nodes, in execution order. `deliver` is deliberately absent: it is a pipeline
# step with no node behind it, and describes what happens after the graph finishes. `answer`
# is absent for the same reason from the other side, being what the person does rather than
# what the agent does.
AGENT_NODES: tuple[str, ...] = (
    "preload",
    "investigate",
    "believe",
    "decide",
    "ask",
    "conclude",
    "critique",
    "review",
)

# Which public pipeline step each node reports as. The mapping is currently the identity,
# but it is the seam and should not be simplified away: splitting `investigate` into three
# nodes means three rows here all pointing at "investigate", and no screen changes.
NODE_TO_PIPELINE_STEP: dict[str, str] = {
    "preload": "preload",
    "investigate": "investigate",
    "believe": "believe",
    "decide": "decide",
    "ask": "ask",
    "conclude": "conclude",
    "critique": "critique",
    "review": "review",
}

# The five fixed reads `node_preload` performs before the model chooses anything. The
# pipeline view uses these to tell preload apart from investigation when an episode is still
# running and has not yet written its trace: any tool outside this set was chosen by the
# model, which means the investigation loop ran.
PRELOAD_TOOLS: frozenset[str] = frozenset(
    {
        "get_nightly_features",
        "get_personal_baseline",
        "get_known_events",
        "get_data_quality",
        "find_similar_past_episodes",
    }
)


def pipeline_steps_that_ran(node_names: object) -> set[str]:
    """Translate the node names in an episode trace into public pipeline step ids.

    Unknown names are dropped rather than passed through. A trace is written by whichever
    version of the graph produced it, so an older episode may name a node that no longer
    exists, and the screens cannot describe a step the system no longer has.
    """
    if not isinstance(node_names, (list, tuple, set, frozenset)):
        return set()
    return {
        NODE_TO_PIPELINE_STEP[name]
        for name in node_names
        if isinstance(name, str) and name in NODE_TO_PIPELINE_STEP
    }
