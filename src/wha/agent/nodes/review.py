"""The human checkpoint before anything reaches the person."""

from typing import Any

from langgraph.types import interrupt

from wha.agent.nodes.context import _record_stage_ran
from wha.agent.state import EpisodeState
from wha.models import (
    Disposition,
)


def node_review(
    state: EpisodeState,
    db: Any = None,
) -> dict[str, Any]:
    """Human review checkpoint. Resumed by approve, edit, reject, escalate or a timeout.

    This is the one place a person can say "no, that is wrong" before the system commits
    to a conclusion about their health, and it had never once been possible. A background
    job answered "approve" on their behalf about fifteen minutes later and the record then
    said a human had approved it. A record showing a decision that never happened is worse
    than no checkpoint at all.

    Two things had to change for a person to reach this screen. The episode is now parked
    in AWAITING_HUMAN_REVIEW, which `get_pending_interaction` requires before it will show
    a draft at all, and the scheduler no longer supplies a decision.

    Everything before the `interrupt()` runs again on resume, so it has to be idempotent.
    `record_review_requested` writes at most one row per episode for that reason.
    """
    draft = state.get("draft")
    if draft is None:
        return {"step": state.get("step", 0) + 1}

    episode_id = state.get("episode_id", "")
    if db is not None and hasattr(db, "set_episode_state"):
        db.set_episode_state(episode_id, "AWAITING_HUMAN_REVIEW")
    if db is not None and hasattr(db, "record_review_requested"):
        db.record_review_requested(
            subject_id=state.get("subject_id", ""),
            episode_id=episode_id,
            disposition=draft.disposition.value,
        )

    raw_response = interrupt(
        {
            "kind": "human_review",
            "draft": draft.model_dump(),
        }
    )

    status = "closed"
    final_draft = draft
    decision = "approve"
    reviewed_by_person = True

    if isinstance(raw_response, dict):
        # Nobody looked at it inside the time allowed. Close it, and record that it closed
        # unreviewed. Do not record an approval, and do not silently change the finding:
        # the draft the agent produced is what it produced.
        if raw_response.get("timed_out"):
            decision = "closed_unreviewed"
            reviewed_by_person = False
        else:
            decision = raw_response.get("decision", "approve")
            if decision == "reject":
                final_draft = draft.model_copy(update={"disposition": Disposition.UNRESOLVED})
                status = "unresolved"
            elif decision == "edit":
                edited_obs = raw_response.get("edited_observation", draft.observation)
                # Machine fields (disposition, differential, baseline) are preserved
                final_draft = draft.model_copy(update={"observation": edited_obs})
            elif decision == "escalate":
                final_draft = draft.model_copy(
                    update={"disposition": Disposition.ESCALATED, "action": "seek_urgent_care"}
                )

    if db is not None and hasattr(db, "record_review_decision"):
        db.record_review_decision(
            subject_id=state.get("subject_id", ""),
            episode_id=episode_id,
            decision=decision,
            rationale=(raw_response.get("rationale") if isinstance(raw_response, dict) else None),
            reviewed_by_person=reviewed_by_person,
        )

    _record_stage_ran(db, state, "review")

    return {
        "draft": final_draft,
        "status": status,
        "step": state.get("step", 0) + 1,
    }
