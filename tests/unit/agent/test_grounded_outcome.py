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
