"""The five fixed reads that open an investigation."""

import logging
from datetime import timedelta
from typing import Any

from wha.agent.state import EpisodeState
from wha.agent.tools.impl import create_default_tool_registry
from wha.agent.tools.registry import ToolContext, ToolRegistry
from wha.clock import local_today

logger = logging.getLogger(__name__)


def node_preload(
    state: EpisodeState,
    db: Any = None,
    registry: ToolRegistry | None = None,
) -> dict[str, Any]:
    """Deterministically populate cheap T1 reads into state['preloaded']."""
    subject_id = state.get("subject_id", "default_subject")
    nights = state.get("nights", [])
    if nights:
        dates = [d.night_date for d in nights]
        start_d = min(dates) - timedelta(days=7)
        end_d = max(dates)
    else:
        end_d = local_today()
        start_d = end_d - timedelta(days=14)

    start_str = start_d.isoformat()
    end_str = end_d.isoformat()

    context = ToolContext(
        subject_id=subject_id,
        episode_id=state.get("episode_id"),
        step_index=state.get("step", 0),
    )

    reg = registry or create_default_tool_registry()
    preloaded: dict[str, Any] = {}

    # 1. get_nightly_features
    res_feat = reg.invoke(
        "get_nightly_features",
        {"start": start_str, "end": end_str},
        context,
        db=db,
    )
    preloaded["nightly_features"] = res_feat.value

    # 2. get_personal_baseline
    res_base = reg.invoke(
        "get_personal_baseline",
        {"night_date": end_str},
        context,
        db=db,
    )
    preloaded["personal_baseline"] = res_base.value

    # 3. get_known_events
    res_events = reg.invoke(
        "get_known_events",
        {"start": start_str, "end": end_str},
        context,
        db=db,
    )
    preloaded["known_events"] = res_events.value

    # 4. get_data_quality
    res_qual = reg.invoke(
        "get_data_quality",
        {"start": start_str, "end": end_str},
        context,
        db=db,
    )
    preloaded["data_quality"] = res_qual.value

    # 5. find_similar_past_episodes
    res_hist = reg.invoke("find_similar_past_episodes", {}, context, db=db)
    preloaded["similar_past_episodes"] = res_hist.value

    # 6. What the person has actually told us, and whether this is a recurrence.
    #
    # Both go into `preloaded`, which the investigate prompt renders as its history
    # summary, so the model reasons with them without a new prompt slot. Neither existed
    # before: the agent could see every reading and none of the words, and it opened a
    # recurrence four days after the last episode closed with no idea it had met this
    # person before.
    #
    # Deliberately facts, not conclusions. "Reported dizziness on 3 consecutive nights,
    # not reported as settled" is something the model can reason from and a reader can
    # check. It is not a diagnosis and does not name one.
    conn = getattr(db, "conn", None)
    if conn is not None:
        try:
            from wha.service.symptoms import symptom_as_of, symptom_runs

            preloaded["reported_symptoms"] = [
                {
                    "symptom": run.flag_id,
                    "first_reported": run.first_night.isoformat(),
                    "last_reported": run.last_night.isoformat(),
                    "nights": run.nights,
                    "still_outstanding": run.outstanding,
                    "their_words": run.last_text[:200],
                }
                for run in symptom_runs(conn, subject_id, symptom_as_of(conn, subject_id))
            ]
            erow = conn.execute(
                """SELECT preceded_by_episode_id, days_since_previous FROM episodes
                    WHERE episode_id = ?""",
                (state.get("episode_id"),),
            ).fetchone()
            if erow is not None and erow["preceded_by_episode_id"]:
                preloaded["recurrence"] = {
                    "continues_episode": erow["preceded_by_episode_id"],
                    "days_since_previous_ended": erow["days_since_previous"],
                    "note": (
                        "This is a recurrence within the window that respiratory illness "
                        "surveillance treats as the same illness, not a new one."
                    ),
                }
        except Exception:
            logger.exception("Could not preload symptom history for %s", subject_id)

    return {
        "preloaded": preloaded,
        "step": state.get("step", 0) + 1,
    }
