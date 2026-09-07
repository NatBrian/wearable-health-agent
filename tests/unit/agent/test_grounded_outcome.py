"""Citations, claim-to-source enforcement, and the reasons behind the differential."""

from datetime import date
from unittest.mock import MagicMock

from wha.agent.differential import ground_differential
from wha.agent.nodes import OutcomeClaim, WriteOutcomeResponse, node_conclude
from wha.agent.state import EpisodeState
from wha.belief import update_belief
from wha.llm.client import LLMUsage
from wha.models import (
    Answer,
    CauseId,
    Detection,
    DetectionLevel,
    Forecast,
    NightlyFeatures,
)

_PASSAGE_TEXT = "Per-drink RHR +2.8 bpm (99.9% CI 2.7-2.9) in females, +2.4 (2.3-2.4) in males."


def _night(day: int, residual: float = 4.2) -> Detection:
    return Detection(
        subject_id="sub_001",
        night_date=date(2026, 9, day),
        level=DetectionLevel.RED,
        flagged=True,
        residual_bpm=residual,
        robust_z=2.6,
        forecast=Forecast(),
    )


def _state_with_retrieval() -> EpisodeState:
    return {
        "episode_id": "ep_ground",
        "subject_id": "sub_001",
        "nights": [_night(4), _night(5)],
        "features": [],
        "answers": [],
        "evidence": [],
        "tool_calls": [
            {
                "tool_name": "retrieve_clinical_evidence",
                "args": {"query": "alcohol"},
                "ok": True,
                "value": [
                    {
                        "chunk_id": "confounder_alcohol#c0",
                        "doc_id": "confounder_alcohol",
                        "title": "Confounder evidence: Alcohol",
                        "text": _PASSAGE_TEXT,
                        "layer": 4,
                    }
                ],
            }
        ],
        "step": 5,
    }


def test_a_claim_whose_span_is_in_a_passage_is_kept_and_cited() -> None:
    """citations was hardcoded to [], which disabled claim-to-source enforcement entirely."""
    client = MagicMock()
    client.complete.return_value = (
        WriteOutcomeResponse(
            observation="Your heart rate rose on two nights.",
            claims=[
                OutcomeClaim(
                    text="Alcohol raises resting heart rate by roughly 2.8 bpm per drink.",
                    evidence_span="Per-drink RHR +2.8 bpm",
                )
            ],
            escalation_criteria=["Seek care if this persists."],
        ),
        LLMUsage(),
    )

    draft = node_conclude(_state_with_retrieval(), llm_client=client)["draft"]

    assert draft.unsupported_claims == 0
    assert [c.source_id for c in draft.citations] == ["confounder_alcohol#c0"]
    assert "confounder_alcohol#c0" in draft.evidence_used


def test_a_claim_with_no_supporting_passage_is_counted_and_stripped() -> None:
    """The check is verbatim containment in code, so a paraphrase cannot pass it."""
    client = MagicMock()
    invented = "Your immune system is fighting an infection."
    client.complete.return_value = (
        WriteOutcomeResponse(
            observation=f"Your heart rate rose on two nights. {invented}",
            claims=[
                OutcomeClaim(
                    text=invented,
                    evidence_span="infections raise heart rate substantially",
                )
            ],
            escalation_criteria=["Seek care if this persists."],
        ),
        LLMUsage(),
    )

    draft = node_conclude(_state_with_retrieval(), llm_client=client)["draft"]

    assert draft.unsupported_claims == 1
    assert invented not in draft.observation
    # The passage is still listed. `citations` answers "what did this episode read", which
    # is what the Evidence tab shows and is true regardless of whether a sentence quoted
    # it. Whether the prose was supported is reported separately, by the count above and
    # by the claim being stripped.
    assert [c.source_id for c in draft.citations] == ["confounder_alcohol#c0"]


def test_the_differential_carries_reasons_not_just_probabilities() -> None:
    """Every entry used to arrive with supporting: [] and contradicting: []."""
    nights = [_night(4), _night(5)]
    belief = update_belief(episode_nights=nights)

    items = ground_differential(belief=belief, nights=nights)

    assert items
    for item in items:
        assert item.supporting or item.contradicting, (
            f"{item.cause.value} was given a probability with no reason attached"
        )


def test_an_answer_moves_the_reason_to_the_side_the_likelihood_moves_the_belief() -> None:
    """The reason shown and the arithmetic applied must never disagree.

    "Feverish or chills" has likelihood 0.25 if an infection is contributing against 0.03
    if it is not, so it belongs under supporting for infection. "Nothing unusual" is 0.15
    against 0.80, so it belongs under contradicting.
    """
    nights = [_night(4)]
    belief = update_belief(episode_nights=nights)

    febrile = ground_differential(
        belief=belief,
        nights=nights,
        answers=[Answer(probe_id="probe_symptoms", option_id="fever")],
        top_n=12,
    )
    infection = next(i for i in febrile if i.cause is CauseId.INFECTION)
    assert any("Feverish or chills" in s for s in infection.supporting)

    quiet = ground_differential(
        belief=belief,
        nights=nights,
        answers=[Answer(probe_id="probe_symptoms", option_id="none")],
        top_n=12,
    )
    infection_quiet = next(i for i in quiet if i.cause is CauseId.INFECTION)
    assert any("Nothing unusual" in c for c in infection_quiet.contradicting)


def test_short_sleep_recorded_by_the_watch_supports_sleep_restriction() -> None:
    """Feature reasons mirror the log-factor conditions in wha.belief.likelihood."""
    nights = [_night(4)]
    belief = update_belief(episode_nights=nights)
    features = [
        NightlyFeatures(
            subject_id="sub_001",
            night_date=date(2026, 9, 4),
            rhr_bpm=65.0,
            coverage_minutes=400,
            implausible_dropped=0,
            usable=True,
            sleep_hours=4.5,
        )
    ]

    items = ground_differential(belief=belief, nights=nights, features=features, top_n=12)
    item = next(i for i in items if i.cause is CauseId.SLEEP_RESTRICTION)
    assert any("4.5 hours of sleep" in s for s in item.supporting)


def test_luteal_says_plainly_that_applicability_was_never_established() -> None:
    """The largest benign effect in the table must not look silently ruled out."""
    nights = [_night(4)]
    belief = update_belief(episode_nights=nights)

    items = ground_differential(belief=belief, nights=nights, cycle_applicable=None, top_n=12)
    item = next(i for i in items if i.cause is CauseId.LUTEAL)
    assert any("has not been established" in c for c in item.contradicting)


def test_the_outcome_is_written_knowing_what_the_person_said() -> None:
    """The prose must not contradict the person's own report.

    A production run concluded "No specific symptoms were reported" for an episode in
    which the person had answered "Feverish or chills". The answer was in state and in the
    belief, and simply was not in the prompt that wrote the sentence.
    """
    client = MagicMock()
    client.complete.return_value = (
        WriteOutcomeResponse(observation="Two raised nights.", escalation_criteria=["Rest."]),
        LLMUsage(),
    )

    state = _state_with_retrieval()
    state["answers"] = [Answer(probe_id="probe_symptoms", option_id="fever")]
    node_conclude(state, llm_client=client)

    prompt = client.complete.call_args_list[0].args[0]
    assert "probe_symptoms" in prompt.user
    assert "fever" in prompt.user


def test_node_conclude_actually_writes_the_trace_the_screen_reads() -> None:
    """The Trace tab's data must be written by the graph, through a real repository.

    `episode_traces` was added with a writer at the end of `node_conclude`, guarded by
    `hasattr(db, "record_episode_trace")`. That is the exact guard that once made every
    tool in this system a no-op: no implementation of the `db` interface existed, so every
    such guard was False and the code behind it never ran while everything stayed green.

    Nothing exercised this one. The tests for the Trace tab INSERT rows into
    `episode_traces` directly, so they would pass with the writer deleted, and on 5
    September 2026 the live database had zero rows in that table. This drives the real
    node with a real EpisodeRepository and asserts the row lands, so "the screen shows
    every stage as pending because nothing ever wrote a trace" cannot come back silently.
    """
    import json
    import sqlite3

    from wha.agent.repository import EpisodeRepository
    from wha.db.migrations import apply_schema

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    apply_schema(conn)

    client = MagicMock()
    client.complete.return_value = (
        WriteOutcomeResponse(
            observation="Your heart rate rose on two nights.",
            claims=[
                OutcomeClaim(
                    text="Alcohol raises resting heart rate by roughly 2.8 bpm per drink.",
                    evidence_span="Per-drink RHR +2.8 bpm",
                )
            ],
            escalation_criteria=["Seek care if this persists."],
        ),
        LLMUsage(),
    )

    state = _state_with_retrieval()
    repo = EpisodeRepository(conn=conn)
    node_conclude(state, llm_client=client, db=repo)

    rows = conn.execute(
        "SELECT episode_id, payload_json FROM episode_traces WHERE episode_id = ?",
        (state["episode_id"],),
    ).fetchall()
    assert len(rows) == 1, "node_conclude wrote no trace, so the Trace tab has nothing to read"

    payload = json.loads(rows[0]["payload_json"])
    ran = set(payload["nodes_ran"])

    # The stages that genuinely ran are named, and "measure" is not among them: that limb
    # was deleted, and a trace naming it would put a permanently pending stage back on the
    # screen. See test_the_trace_advertises_exactly_the_stages_the_graph_has.
    assert {"preload", "investigate", "believe", "decide", "conclude"} <= ran
    assert "measure" not in ran
    assert "ask" not in ran, "no answers in this state, so nothing was asked"

    # conclude runs BEFORE critique and review, so it must not claim either has run. It
    # claimed "critique" at a point where critique had not executed, and could never claim
    # "review" at all.
    assert "critique" not in ran, "conclude cannot know critique ran; critique runs after it"
    assert "review" not in ran, "conclude cannot know review ran; review runs after it"

    # The later stages append themselves, and review is the one that mattered: node_review
    # is the ONLY node returning status "closed", and _close_if_concluded refuses to close
    # without it, so EVERY closed episode ran review. The Trace tab reported it SKIPPED on
    # all of them with "This episode has not reached the review checkpoint", the invented
    # reason item 11 exists to delete.
    def stages() -> list[str]:
        return json.loads(
            conn.execute(
                "SELECT payload_json FROM episode_traces WHERE episode_id = ?",
                (state["episode_id"],),
            ).fetchone()["payload_json"]
        )["nodes_ran"]

    repo.record_episode_stage_ran(state["episode_id"], "critique")
    repo.record_episode_stage_ran(state["episode_id"], "review")
    assert {"critique", "review"} <= set(stages())

    # Idempotent, because nodes re-run on resume after an interrupt.
    repo.record_episode_stage_ran(state["episode_id"], "review")
    assert stages().count("review") == 1

    # The tool calls travel under the names the expander actually reads. It read
    # source_ref / arguments / result while this wrote tool_name / args / ok / note, so
    # every call rendered as "(Source: `None`, Freshness: `current`)" over an empty {}.
    assert any(call["tool_name"] == "retrieve_clinical_evidence" for call in payload["tool_calls"])
    for call in payload["tool_calls"]:
        for field in ("tool_name", "args", "ok", "source_ids", "freshness", "result_summary"):
            assert field in call, f"the expander reads {field} and the trace does not carry it"


def test_the_differential_ranks_by_movement_over_every_cause_not_the_largest_five() -> None:
    """Item 33's own check: answer "feverish" and infection must be at the top.

    Two things stopped that. The candidate set was `belief.top(top_n)`, the five LARGEST,
    which were then reordered by movement; a cause the evidence moved hard but left small
    could never appear at all. And on a raised night the common-and-small causes are always
    large, so "large" is the one criterion guaranteed not to be informative, which is the
    whole argument of the item.
    """
    from wha.belief import update_belief

    nights = [_night(4), _night(5)]
    answers = [Answer(probe_id="probe_symptoms", option_id="fever", declined=False)]
    belief = update_belief(episode_nights=nights, answers=answers, luteal_applicable=None)

    items = ground_differential(belief, nights=nights, answers=answers, top_n=5)

    assert items[0].cause is CauseId.INFECTION, (
        "the cause the evidence moved should lead: "
        + ", ".join(f"{i.cause.value}({i.moved:+.3f})" for i in items)
    )

    # Ordered by movement, and NOT by probability. Both matter: if it happened to be
    # ordered by probability this would pass by accident, so assert the ordering property
    # directly and assert that it differs from the probability ordering on this episode.
    moved = [abs(i.moved) for i in items]
    assert moved == sorted(moved, reverse=True), "not ordered by movement"

    by_probability = sorted(items, key=lambda i: -i.probability)
    assert [i.cause for i in items] != [i.cause for i in by_probability], (
        "this episode should rank differently by movement than by size, or the test proves "
        "nothing about which one is being used"
    )

    # The number the chart draws has to be on the item, not inferred from prose.
    assert items[0].moved > 0.1
    assert "moved it from" in items[0].supporting[0]
