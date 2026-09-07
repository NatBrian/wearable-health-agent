"""What the agent calls its own steps, and what the rest of the system calls them.

Written 8 September 2026, because the agent's node names were also, silently, a public
interface. They were spelled out in three places that no test compared: the agentic entries
of ``CANONICAL_PIPELINE_STEPS`` in ``models.py``, ``CANONICAL_STAGES`` in
``service/episodes.py``, and a hardcoded set inside ``_agent_steps_from_evidence`` in
``service/pipeline.py``. Renaming a node therefore broke two screens, and neither the graph
nor the suite would say so.

That drift has already reached a person once. ``node_measure`` was deleted and
``CANONICAL_STAGES`` was not updated, so the Trace tab went on advertising a stage of the
reader's own investigation that no longer existed and reported it permanently pending. It
was found by opening the tab, not by a test.

This module is the one place the vocabulary lives. It holds names and nothing else: no
queries, no rendering, no behaviour. ``service/pipeline.py`` keeps its SQL and
``service/episodes.py`` keeps its prose; they read the names from here.

**If you are restructuring the agent**, for instance into several agents, this is the file
to change first. Rename, split or add nodes, map each one onto the public step it reports
as, and the audit view and the dashboard keep working without being touched.
``NODE_TO_PIPELINE_STEP`` is what makes the two vocabularies independent: it is the identity
mapping today only because nothing has yet needed it not to be.

Two tests hold this together. One checks that every value in ``NODE_TO_PIPELINE_STEP`` is a
real step in ``CANONICAL_PIPELINE_STEPS``; the other checks that the nodes registered in
``build_agent_graph`` are exactly ``AGENT_NODES``, so a node added to the graph and not
named here fails the build rather than a screen.
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

# Which public pipeline step each node reports as. The identity mapping is not an accident
# waiting to be simplified away: it is the seam. Splitting `investigate` into three nodes
# means adding three rows here that all point at "investigate", and no screen changes.
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

    A name that is not a known node is dropped rather than passed through. Traces are
    written by whichever version of the graph was running at the time, so an old episode can
    name a node that no longer exists, and showing a person a step of their own
    investigation that the system can no longer explain is worse than showing them nothing.
    """
    if not isinstance(node_names, (list, tuple, set, frozenset)):
        return set()
    return {
        NODE_TO_PIPELINE_STEP[name]
        for name in node_names
        if isinstance(name, str) and name in NODE_TO_PIPELINE_STEP
    }
