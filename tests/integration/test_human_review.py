"""Nothing may approve a conclusion about a person's health on their behalf.

The system drafts a conclusion and pauses for the person to check it. A background job
answered "approve" about fifteen minutes later, and the record then said a human had
approved it. A live run took episode ep_3637eaf58033 from waiting-for-you to closed in a
single tick with nobody involved.

A record showing a decision that never happened is worse than having no checkpoint. These
tests drive the real scheduler and the real review node rather than any one function,
because the defect was that the two halves disagreed about whether anyone was waiting: the
graph parked on an interrupt while the service closed the episode with its own SQL.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

from langgraph.graph import END, START, StateGraph

from wha.agent.nodes import node_review
from wha.agent.repository import EpisodeRepository
from wha.agent.state import EpisodeState
from wha.constants import REVIEW_TIMEOUT_HOURS
from wha.db import connect
from wha.db.iso import to_iso
from wha.db.migrations import apply_schema
from wha.models import BaselineRung, Disposition, EpisodeOutcome
from wha.service.scheduler import run_episode_tick

EPISODE = "ep_review"
REVIEW_INTERRUPT = {"kind": "human_review", "draft": {}}


def _make_db(tmp_path: Path, state: str = "OPEN") -> Path:
    db_file = tmp_path / "review.db"
    conn = connect(db_file)
    apply_schema(conn)
    conn.execute(
        """INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
           VALUES ('me', 'me', 'live', 'Asia/Singapore', ?)""",
        (to_iso(datetime.now(UTC)),),
    )
    conn.execute(
        """INSERT INTO episodes
             (episode_id, subject_id, thread_id, opened_on, state, baseline_nights,
              baseline_rung, step_count, tool_call_count, depth_used)
           VALUES (?, 'me', ?, ?, ?, 28, 'MATURE', 0, 0, 0)""",
        (EPISODE, EPISODE, date(2026, 9, 1).isoformat(), state),
    )
    conn.commit()
    conn.close()
    return db_file


def _draft() -> EpisodeOutcome:
    return EpisodeOutcome(
        episode_id=EPISODE,
        subject_id="me",
        opened_on=date(2026, 9, 1),
        closed_on=date(2026, 9, 3),
        disposition=Disposition.LIKELY_BENIGN,
        observation="Two raised nights, then a return to your usual range.",
        baseline_nights=28,
        baseline_rung=BaselineRung.MATURE,
        differential=[],
        evidence_used=[],
        ruled_out=[],
        citations=[],
        unsupported_claims=0,
        action="monitor",
        escalation_criteria=["Seek urgent medical attention if you develop chest pain."],
        confidence="moderate",
        interruptions_used_this_week=0,
        depth_used_this_episode=0,
    )


def _review_rows(db_file: Path) -> list[dict]:
    conn = connect(db_file)
    try:
        return [
            dict(r)
            for r in conn.execute(
                """SELECT actor, human_decision, permission_decision, timestamp_utc
                     FROM audit_events
                    WHERE episode_id = ? AND operation = 'human_decision'
                    ORDER BY rowid""",
                (EPISODE,),
            ).fetchall()
        ]
    finally:
        conn.close()


def _review_graph(db_file: Path):
    """Just the review node, so the checkpoint exercises the interrupt and nothing else."""
    from langgraph.checkpoint.memory import MemorySaver

    repo = EpisodeRepository(db_path=db_file)
    builder = StateGraph(EpisodeState)
    builder.add_node("review", lambda s: node_review(s, db=repo))
    builder.add_edge(START, "review")
    builder.add_edge("review", END)
    return builder.compile(checkpointer=MemorySaver())


def _park(db_file: Path):
    graph = _review_graph(db_file)
    config = {"configurable": {"thread_id": EPISODE}, "recursion_limit": 10}
    graph.invoke(
        {"episode_id": EPISODE, "subject_id": "me", "draft": _draft(), "step": 0},
        config,
    )
    return graph, config


# -- the scheduler must not decide -------------------------------------------------


def test_the_scheduler_leaves_a_review_parked(tmp_path: Path) -> None:
    """The defect itself. `_resume_value` fell through to {"decision": "approve"}."""
    db_file = _make_db(tmp_path, state="AWAITING_HUMAN_REVIEW")

    conn = connect(db_file)
    EpisodeRepository(conn=conn).record_review_requested("me", EPISODE, "LIKELY_BENIGN")
    conn.close()

    stepped: list[Any] = []
    with (
        patch("wha.service.scheduler.step_episode", side_effect=lambda *a, **k: stepped.append(k)),
        patch("wha.agent.graph.get_agent_graph", return_value=object()),
        patch("wha.agent.graph.get_pending_interrupt", return_value=REVIEW_INTERRUPT),
    ):
        result = run_episode_tick(db_path=db_file)

    assert stepped == [], "a background job decided a conclusion about someone's health"
    assert result["advanced_episodes"] == []
    assert [r["human_decision"] for r in _review_rows(db_file)] == [None]


def test_an_unknown_interrupt_is_also_left_parked(tmp_path: Path) -> None:
    """The fall-through approved anything it did not recognise, not only reviews."""
    db_file = _make_db(tmp_path, state="AWAITING_HUMAN_REVIEW")

    stepped: list[Any] = []
    with (
        patch("wha.service.scheduler.step_episode", side_effect=lambda *a, **k: stepped.append(k)),
        patch("wha.agent.graph.get_agent_graph", return_value=object()),
        patch("wha.agent.graph.get_pending_interrupt", return_value="something else entirely"),
    ):
        run_episode_tick(db_path=db_file)

    assert stepped == []


def test_the_review_is_released_after_the_timeout(tmp_path: Path) -> None:
    """It must not park forever either. The release is a timeout, not a decision."""
    db_file = _make_db(tmp_path, state="AWAITING_HUMAN_REVIEW")

    conn = connect(db_file)
    EpisodeRepository(conn=conn).record_review_requested("me", EPISODE, "LIKELY_BENIGN")
    stale = datetime.now(UTC) - timedelta(hours=REVIEW_TIMEOUT_HOURS + 1)
    conn.execute(
        """UPDATE audit_events SET timestamp_utc = ?
            WHERE episode_id = ? AND operation = 'human_decision'""",
        (to_iso(stale), EPISODE),
    )
    conn.commit()
    conn.close()

    resumed: list[Any] = []

    def fake_step(episode_id: str, **kwargs: Any) -> dict[str, Any]:
        resumed.append(kwargs.get("resume"))
        conn = kwargs["conn"]
        conn.execute("UPDATE episodes SET state = 'CLOSED' WHERE episode_id = ?", (episode_id,))
        conn.commit()
        return {"status": "closed"}

    with (
        patch("wha.service.scheduler.step_episode", side_effect=fake_step),
        patch("wha.agent.graph.get_agent_graph", return_value=object()),
        patch("wha.agent.graph.get_pending_interrupt", return_value=REVIEW_INTERRUPT),
    ):
        run_episode_tick(db_path=db_file)

    assert resumed == [{"timed_out": True}], "the timeout must not send a decision"


# -- the review node itself ---------------------------------------------------------


def test_parking_puts_the_episode_where_the_dashboard_can_see_it(tmp_path: Path) -> None:
    """`get_pending_interaction` only surfaces a draft for AWAITING_HUMAN_REVIEW.

    Nothing ever set that state, so the review screen was unreachable even in principle.
    """
    db_file = _make_db(tmp_path)
    _park(db_file)

    conn = connect(db_file)
    try:
        state = conn.execute(
            "SELECT state FROM episodes WHERE episode_id = ?", (EPISODE,)
        ).fetchone()["state"]
    finally:
        conn.close()
    assert state == "AWAITING_HUMAN_REVIEW"

    rows = _review_rows(db_file)
    assert len(rows) == 1
    assert rows[0]["human_decision"] is None
    assert rows[0]["permission_decision"] == "required_approval"


def test_rejecting_makes_the_episode_unresolved(tmp_path: Path) -> None:
    """The point of the checkpoint: a person can say the conclusion is wrong."""
    db_file = _make_db(tmp_path)
    graph, config = _park(db_file)

    from langgraph.types import Command

    result = graph.invoke(Command(resume={"decision": "reject"}), config)

    assert result["draft"].disposition == Disposition.UNRESOLVED
    assert result["status"] == "unresolved"
    assert _review_rows(db_file)[-1]["human_decision"] == "reject"


def test_a_timeout_is_never_recorded_as_an_approval(tmp_path: Path) -> None:
    """An unattended close is attributed to the system, and says it was not approved."""
    db_file = _make_db(tmp_path)
    graph, config = _park(db_file)

    from langgraph.types import Command

    result = graph.invoke(Command(resume={"timed_out": True}), config)

    # The finding stands. Nobody reasoned about it, so nothing may change it either way.
    assert result["draft"].disposition == Disposition.LIKELY_BENIGN

    final = _review_rows(db_file)[-1]
    assert final["human_decision"] == "closed_unreviewed"
    assert final["actor"] == "system"
    assert "approve" not in final["human_decision"]


def test_the_request_is_recorded_once_not_once_per_resume(tmp_path: Path) -> None:
    """node_review re-runs in full on resume, so an unguarded write would duplicate it."""
    db_file = _make_db(tmp_path)
    graph, config = _park(db_file)

    from langgraph.types import Command

    graph.invoke(Command(resume={"decision": "approve"}), config)

    rows = _review_rows(db_file)
    requests = [r for r in rows if r["human_decision"] is None]
    assert len(requests) == 1, f"the review request was recorded {len(requests)} times"
    assert rows[-1]["human_decision"] == "approve"
    assert rows[-1]["actor"] == "human"


# -- the service applies the decision through the graph, not around it ---------------


def test_submitting_a_decision_resumes_the_graph(tmp_path: Path) -> None:
    """It used to close the episode with its own SQL and leave the interrupt hanging.

    Two implementations of the same four decisions, and the scheduler then found the
    abandoned interrupt and resumed it with a hardcoded approval.
    """
    from wha.service.episodes import submit_human_decision

    db_file = _make_db(tmp_path, state="AWAITING_HUMAN_REVIEW")

    resumed: list[Any] = []
    with patch(
        "wha.service.episodes.step_episode",
        side_effect=lambda *a, **k: resumed.append(k.get("resume")),
    ):
        conn = connect(db_file)
        submit_human_decision(EPISODE, decision="reject", rationale="not what happened", conn=conn)
        conn.close()

    assert resumed == [{"decision": "reject", "rationale": "not what happened"}]


def test_reworded_prose_survives_the_approve_button(tmp_path: Path) -> None:
    """The dashboard sends edited text with decision="approve" and it was being dropped.

    No button in the interface sends decision="edit", and the only branch that read
    edited_prose required it, so a person who reworded the conclusion and approved it had
    their wording discarded silently.
    """
    from wha.service.episodes import submit_human_decision

    db_file = _make_db(tmp_path, state="AWAITING_HUMAN_REVIEW")

    resumed: list[Any] = []
    with patch(
        "wha.service.episodes.step_episode",
        side_effect=lambda *a, **k: resumed.append(k.get("resume")),
    ):
        conn = connect(db_file)
        submit_human_decision(
            EPISODE,
            decision="approve",
            edited_prose="I had a late night, not an illness.",
            conn=conn,
        )
        conn.close()

    assert resumed == [
        {"decision": "edit", "edited_observation": "I had a late night, not an illness."}
    ]


def test_a_parked_episode_gives_the_review_screen_something_to_show(tmp_path: Path) -> None:
    """Item 3's own check: "the dashboard shows a draft with approve, edit, reject".

    It showed nothing. `_close_if_concluded` wrote the `outcomes` row only when the graph
    returned status "closed" or "unresolved". node_review is the only node that returns
    either, and it returns them AFTER the interrupt, so an episode WAITING for a human had
    no outcome row at all.

    `get_pending_interaction` therefore returned `PendingInteraction(kind="review",
    draft_outcome=None)`, and the Today page's branch is
    `elif pending.kind == "review" and pending.draft_outcome:` - False. Because `pending`
    was not None, the "nothing needs you right now" branch was skipped as well, so the
    inbox rendered NOTHING AT ALL: no draft, no buttons, no message. Thirty-six hours later
    the scheduler released it as closed_unreviewed.

    Item 3 removed the auto-approval, which was the defect it named, and left the
    checkpoint unusable, which is its title. The existing test here asserts only that the
    episode state is AWAITING_HUMAN_REVIEW and never looks for the draft, and it goes
    through the graph directly rather than through `step_episode`, which is where the
    outcome is written. That combination is why this survived.
    """
    from unittest.mock import patch

    from wha.service.episodes import get_pending_interaction, step_episode

    db_file = _make_db(tmp_path)

    # The graph parks: it sets the state and returns a draft with no closing status, which
    # is exactly what node_review does on the way into `interrupt()`.
    def fake_step(*_args, **_kwargs):
        conn = connect(db_file)
        try:
            conn.execute(
                "UPDATE episodes SET state = 'AWAITING_HUMAN_REVIEW' WHERE episode_id = ?",
                (EPISODE,),
            )
            conn.commit()
        finally:
            conn.close()
        return {"draft": _draft(), "status": "parked", "step": 1}

    with (
        patch("wha.agent.graph.get_agent_graph", return_value=object()),
        patch("wha.agent.graph.run_episode_step", side_effect=fake_step),
    ):
        result = step_episode(EPISODE, db_path=db_file)

    assert result["state"] == "AWAITING_HUMAN_REVIEW", "the episode should be parked"

    conn = connect(db_file)
    try:
        # The episode must NOT have been closed or given a disposition by parking.
        row = conn.execute(
            "SELECT state, disposition, closed_on FROM episodes WHERE episode_id = ?",
            (EPISODE,),
        ).fetchone()
        assert row["state"] == "AWAITING_HUMAN_REVIEW"
        assert row["disposition"] is None, "parking must not decide the episode"
        assert row["closed_on"] is None

        pending = get_pending_interaction("me", conn=conn)
    finally:
        conn.close()

    assert pending is not None
    assert pending.kind == "review"
    assert pending.draft_outcome is not None, (
        "the review screen has no draft to show, so the person sees an empty inbox"
    )
    assert pending.draft_outcome.observation
    assert pending.draft_outcome.disposition is Disposition.LIKELY_BENIGN
