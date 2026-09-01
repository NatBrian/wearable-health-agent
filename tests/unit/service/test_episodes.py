"""Unit tests for episode service functions, interactive responses, and bounded Q&A."""

import json
from datetime import date

from wha.db import connect
from wha.db.migrations import apply_schema
from wha.models import (
    Answer,
    Citation,
    Disposition,
    EpisodeOutcome,
    PendingInteraction,
    StageStatus,
)
from wha.service import (
    ask_about_episode,
    get_episode,
    get_pending_interaction,
    submit_answer,
)


def _seed_sample_episode(conn) -> tuple[str, str, str]:
    """Helper to insert a sample episode, interaction, and outcome."""
    sub_id = "sub_ep_test"
    ep_id = "ep_20260815_01"
    int_id = "int_20260815_q1"

    conn.execute(
        "INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc) VALUES (?, ?, ?, ?, ?)",
        (sub_id, "Test User", "synthetic", "Asia/Singapore", "2026-08-01T00:00:00Z"),
    )

    conn.execute(
        """INSERT INTO episodes (episode_id, subject_id, thread_id, opened_on, state, disposition, baseline_nights, baseline_rung)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (ep_id, sub_id, "thread_01", "2026-08-15", "AWAITING_USER", None, 14, "PERSONAL"),
    )

    options_json = json.dumps(
        [
            {"option_id": "none", "label": "None"},
            {"option_id": "1_2", "label": "1-2 drinks"},
            {"option_id": "3plus", "label": "3+ drinks"},
        ]
    )
    rejected_json = json.dumps(
        [
            ["probe_exertion", 0.12],
            ["probe_stress", 0.08],
        ]
    )

    conn.execute(
        """INSERT INTO interactions (id, episode_id, probe_id, question_text, text_source, options_json, evsi, interruption_cost, rejected_json, channel, asked_at_utc, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            int_id,
            ep_id,
            "probe_alcohol",
            "Did you consume alcohol yesterday?",
            "llm",
            options_json,
            0.45,
            0.10,
            rejected_json,
            "telegram",
            "2026-08-15T08:00:00Z",
            "PENDING",
        ),
    )

    # Outcome
    outcome = EpisodeOutcome(
        episode_id=ep_id,
        subject_id=sub_id,
        opened_on=date(2026, 8, 15),
        closed_on=date(2026, 8, 16),
        disposition=Disposition.EXPLAINED_BY_EVENT,
        observation="Elevated RHR explained by alcohol intake prior night.",
        baseline_nights=14,
        baseline_rung="PERSONAL",
        differential=[],
        evidence_used=["probe_alcohol=3plus"],
        ruled_out=[],
        citations=[
            Citation(
                source_id="lit_alcohol_01",
                title="Alcohol and Nocturnal Heart Rate",
                uri="https://example.com/alcohol",
                passage="Alcohol intake reliably elevates nocturnal resting heart rate by 4 to 8 bpm.",
                retrieval_score=0.92,
            )
        ],
        unsupported_claims=0,
        action="rest",
        escalation_criteria=[],
        confidence="high",
        interruptions_used_this_week=1,
        depth_used_this_episode=1,
    )
    conn.execute(
        "INSERT INTO outcomes (episode_id, schema_version, payload_json, created_at_utc) VALUES (?, ?, ?, ?)",
        (ep_id, "1.0", outcome.model_dump_json(), "2026-08-16T08:00:00Z"),
    )

    # Audit event for preload and investigate ran
    conn.execute(
        """INSERT INTO audit_events (event_id, subject_id, episode_id, timestamp_utc, actor, operation, hash)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("ev_01", sub_id, ep_id, "2026-08-15T08:00:00Z", "agent", "preload", "hash01"),
    )
    conn.execute(
        """INSERT INTO audit_events (event_id, subject_id, episode_id, timestamp_utc, actor, operation, hash)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("ev_02", sub_id, ep_id, "2026-08-15T08:01:00Z", "agent", "investigate", "hash02"),
    )
    conn.commit()

    return sub_id, ep_id, int_id


def test_pending_interaction_returns_at_most_one() -> None:
    """get_pending_interaction returns at most one active interaction for a subject."""
    conn = connect(":memory:")
    apply_schema(conn)
    sub_id, ep_id, _int_id = _seed_sample_episode(conn)

    pending = get_pending_interaction(sub_id, conn=conn)
    assert pending is not None
    assert isinstance(pending, PendingInteraction)
    assert pending.kind == "question"
    assert pending.episode_id == ep_id
    assert pending.question is not None
    assert pending.question.probe.probe_id == "probe_alcohol"


def test_submit_answer_is_idempotent() -> None:
    """Submitting an answer multiple times updates once and produces no errors or duplicate states."""
    conn = connect(":memory:")
    apply_schema(conn)
    _sub_id, _ep_id, int_id = _seed_sample_episode(conn)

    ans1 = Answer(probe_id="probe_alcohol", option_id="3plus", free_text=None, declined=False)
    submit_answer(int_id, ans1, conn=conn)

    row = conn.execute(
        "SELECT status, answer_option_id FROM interactions WHERE id = ?", (int_id,)
    ).fetchone()
    assert row["status"] == "ANSWERED"
    assert row["answer_option_id"] == "3plus"

    # Second submission with different answer
    ans2 = Answer(probe_id="probe_alcohol", option_id="none", free_text=None, declined=False)
    submit_answer(int_id, ans2, conn=conn)

    row2 = conn.execute(
        "SELECT status, answer_option_id FROM interactions WHERE id = ?", (int_id,)
    ).fetchone()
    # First submission value is retained (first writer wins)
    assert row2["status"] == "ANSWERED"
    assert row2["answer_option_id"] == "3plus"


def test_submit_answer_same_path_as_telegram() -> None:
    """Answering via submit_answer puts interaction into ANSWERED status identical to telegram callback."""
    conn = connect(":memory:")
    apply_schema(conn)
    _sub_id, _ep_id, int_id = _seed_sample_episode(conn)

    ans = Answer(probe_id="probe_alcohol", option_id="1_2", free_text="2 glasses", declined=False)
    submit_answer(int_id, ans, conn=conn)

    row = conn.execute(
        "SELECT status, answer_option_id, free_text FROM interactions WHERE id = ?", (int_id,)
    ).fetchone()
    assert row["status"] == "ANSWERED"
    assert row["answer_option_id"] == "1_2"
    assert row["free_text"] == "2 glasses"


def test_answer_on_closed_episode_is_noop() -> None:
    """Submitting an answer to a question on a closed episode does nothing."""
    conn = connect(":memory:")
    apply_schema(conn)
    _sub_id, ep_id, int_id = _seed_sample_episode(conn)

    # Close episode
    conn.execute("UPDATE episodes SET state = 'CLOSED' WHERE episode_id = ?", (ep_id,))
    conn.commit()

    ans = Answer(probe_id="probe_alcohol", option_id="3plus", free_text=None, declined=False)
    submit_answer(int_id, ans, conn=conn)

    row = conn.execute("SELECT status FROM interactions WHERE id = ?", (int_id,)).fetchone()
    assert row["status"] == "PENDING"


def test_episode_detail_includes_skipped_stages() -> None:
    """EpisodeDetail contains canonical pipeline stages including SKIPPED stages with explicit reasons."""
    conn = connect(":memory:")
    apply_schema(conn)
    _sub_id, ep_id, _int_id = _seed_sample_episode(conn)

    detail = get_episode(ep_id, conn=conn)
    assert detail.summary.episode_id == ep_id
    assert len(detail.stages) == 9

    stage_map = {s.name: s for s in detail.stages}
    assert stage_map["preload"].status == StageStatus.RAN
    assert stage_map["investigate"].status == StageStatus.RAN
    # Skipped stages are present in list and have explicit reasons
    assert stage_map["review"].status == StageStatus.SKIPPED
    assert "review" in stage_map["review"].reason.lower()


def test_episode_detail_includes_rejected_probes() -> None:
    """EpisodeDetail interactions contain rejected alternatives and their scores."""
    conn = connect(":memory:")
    apply_schema(conn)
    _sub_id, ep_id, _int_id = _seed_sample_episode(conn)

    detail = get_episode(ep_id, conn=conn)
    assert len(detail.interactions) == 1
    interaction = detail.interactions[0]
    assert len(interaction.rejected) == 2
    assert interaction.rejected[0] == ("probe_exertion", 0.12)
    assert interaction.rejected[1] == ("probe_stress", 0.08)


def test_ask_about_episode_cannot_reach_corpus() -> None:
    """ask_about_episode cannot perform global retrieval and is bounded to episode evidence."""
    conn = connect(":memory:")
    apply_schema(conn)
    _sub_id, ep_id, _int_id = _seed_sample_episode(conn)

    # Querying about something outside this episode's evidence (e.g. malaria treatment)
    ans = ask_about_episode(ep_id, "What are the recommended treatments for malaria?", conn=conn)
    assert ans.refused is True
    assert ans.refusal_reason is not None
    assert "cannot be grounded" in ans.refusal_reason


def test_ask_about_episode_refuses_ungrounded() -> None:
    """Questions that have no grounding in the episode's observation or citations are refused."""
    conn = connect(":memory:")
    apply_schema(conn)
    _sub_id, ep_id, _int_id = _seed_sample_episode(conn)

    ans = ask_about_episode(ep_id, "What is the stock price of Apple?", conn=conn)
    assert ans.refused is True
    assert ans.text == ""


def test_ask_about_episode_changes_no_state() -> None:
    """ask_about_episode is strictly read-only and mutates zero tables or counters."""
    conn = connect(":memory:")
    apply_schema(conn)
    _sub_id, ep_id, _int_id = _seed_sample_episode(conn)

    before_audit_count = conn.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
    before_ep_state = conn.execute(
        "SELECT state FROM episodes WHERE episode_id = ?", (ep_id,)
    ).fetchone()[0]

    # Valid grounded query
    ans = ask_about_episode(ep_id, "Why was resting heart rate elevated?", conn=conn)
    assert ans.refused is False
    assert "alcohol" in ans.text.lower()

    after_audit_count = conn.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
    after_ep_state = conn.execute(
        "SELECT state FROM episodes WHERE episode_id = ?", (ep_id,)
    ).fetchone()[0]

    assert before_audit_count == after_audit_count
    assert before_ep_state == after_ep_state
