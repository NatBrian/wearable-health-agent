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
    get_episode,
    get_pending_interaction,
    submit_answer,
)
from wha.service.episodes import CANONICAL_STAGES


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

    # What the agent did, as node_conclude records it.
    #
    # This used to insert audit rows with operation "preload" and "investigate", which the
    # AuditEvent model does not permit: the column holds ten fixed values and neither of
    # those is one of them. So the fixture built a database state production can never
    # produce, and that is why the Trace tab reporting every stage as skipped on every
    # real episode went unnoticed by a passing test.
    conn.execute(
        """INSERT INTO episode_traces (episode_id, payload_json, updated_at_utc)
           VALUES (?, ?, ?)""",
        (
            ep_id,
            json.dumps(
                {
                    "nodes_ran": ["preload", "investigate", "believe", "decide"],
                    "tool_calls": [{"tool_name": "get_nightly_features", "args": {}, "ok": True}],
                    "tool_call_count": 1,
                    "depth_used": 0,
                    "stripped_claims": ["An unsupported sentence."],
                    "questions_asked": 1,
                }
            ),
            "2026-08-15T08:01:00Z",
        ),
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

    # Was `== 9`, which counted the deleted `measure` limb. The graph has eight nodes and
    # `test_the_trace_advertises_exactly_the_stages_the_graph_has` is what holds that to
    # the graph, so this asserts every canonical stage is present rather than a number
    # that has to be remembered when a node is added or removed.
    assert len(detail.stages) == len(CANONICAL_STAGES)
    assert [s.name for s in detail.stages] == [name for name, _ in CANONICAL_STAGES]

    stage_map = {s.name: s for s in detail.stages}
    assert stage_map["preload"].status == StageStatus.RAN
    assert stage_map["investigate"].status == StageStatus.RAN
    # Skipped stages are present in list and have explicit reasons
    assert stage_map["review"].status == StageStatus.SKIPPED
    assert "review" in stage_map["review"].reason.lower()

    # The expander in wha/ui/components/pipeline_trace.py is written and has never had
    # anything to render, because detail_json was always an empty dict.
    assert stage_map["investigate"].detail_json["tool_calls"], "the tool calls are not shown"

    # And the panel that shows what the grounding check removed had a green tick on every
    # episode, because stripped_claims was assigned an empty list and never filled.
    assert detail.stripped_claims == ["An unsupported sentence."]


def test_an_episode_with_no_trace_is_pending_rather_than_skipped() -> None:
    """ "We did not write it down" is a different claim from "it did not run".

    Episodes closed before the trace record existed must not be reported as having
    skipped every stage, which is what the old inference did to every episode.
    """
    conn = connect(":memory:")
    apply_schema(conn)
    _sub_id, ep_id, _int_id = _seed_sample_episode(conn)
    conn.execute("DELETE FROM episode_traces WHERE episode_id = ?", (ep_id,))
    conn.commit()

    detail = get_episode(ep_id, conn=conn)
    assert {s.status for s in detail.stages} == {StageStatus.PENDING}


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


def test_the_trace_advertises_exactly_the_stages_the_graph_has() -> None:
    """A name in CANONICAL_STAGES that the graph lacks is shown as permanently pending.

    That is what a person sees on the Trace tab: a stage of their own investigation with a
    description of what it does and a reason it did not happen. "measure" sat there after
    `node_measure` was deleted, saying "Request spot resting heart rate or overnight wear"
    and "No spot reading was requested", for a limb that no longer existed. Found by
    opening the tab. Nothing failed, because nothing compared the two lists.

    Read from the compiled graph rather than a hand-written list, so adding a node without
    telling the Trace tab fails here too, in the other direction.
    """
    import ast
    from pathlib import Path

    graph_src = Path(__file__).resolve().parents[3] / "src" / "wha" / "agent" / "graph.py"
    tree = ast.parse(graph_src.read_text(encoding="utf-8"))

    in_graph: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_node"
            and node.args
            and isinstance(node.args[0], ast.Constant)
        ):
            in_graph.append(str(node.args[0].value))

    assert in_graph, "no add_node calls found, so this test proves nothing"

    advertised = [name for name, _ in CANONICAL_STAGES]
    assert advertised == in_graph, (
        f"the Trace tab and the graph disagree.\n"
        f"  advertised but not in the graph: {sorted(set(advertised) - set(in_graph))}\n"
        f"  in the graph but never shown:    {sorted(set(in_graph) - set(advertised))}\n"
        f"  order advertised: {advertised}\n"
        f"  order in graph:   {in_graph}"
    )
