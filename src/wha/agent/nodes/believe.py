"""The Bayesian update over the twelve causes."""

from typing import Any

from wha.agent.nodes.context import _episode_context
from wha.agent.state import EpisodeState
from wha.belief import update_belief


def node_believe(
    state: EpisodeState,
    db: Any = None,
) -> dict[str, Any]:
    """Deterministically recompute belief distribution across 4096 states."""
    nights = state.get("nights", [])
    features = state.get("features", [])
    answers = state.get("answers", [])
    measurements = state.get("measurements", [])

    belief = update_belief(
        episode_nights=nights,
        features=features,
        answers=answers,
        measurements=measurements,
        context=_episode_context(state, db, answers),
    )

    if db is not None:
        if hasattr(db, "append_belief"):
            db.append_belief(
                episode_id=state.get("episode_id"),
                subject_id=state.get("subject_id"),
                belief=belief,
                trigger="node_believe",
            )
        elif hasattr(db, "insert_belief"):
            db.insert_belief(
                episode_id=state.get("episode_id"),
                subject_id=state.get("subject_id"),
                belief=belief,
            )

    return {
        "belief": belief,
        "step": state.get("step", 0) + 1,
    }
