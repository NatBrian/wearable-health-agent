"""Unit tests for conclude, critique, and human review graph nodes."""

from datetime import date
from unittest.mock import MagicMock, patch

from wha.agent import (
    CritiqueResponse,
    EpisodeState,
    node_critique,
    node_review,
)
from wha.errors import LLMUnavailable
from wha.llm.client import LLMUsage
from wha.models import (
    BaselineRung,
    CauseId,
    DifferentialItem,
    Disposition,
    EpisodeOutcome,
)


def _make_dummy_draft(obs: str = "Elevated heart rate observed.") -> EpisodeOutcome:
    return EpisodeOutcome(
        episode_id="ep_conclude_test",
        subject_id="sub_001",
        opened_on=date(2026, 8, 20),
        closed_on=date(2026, 8, 21),
        disposition=Disposition.LIKELY_ILLNESS,
        observation=obs,
        baseline_nights=28,
        baseline_rung=BaselineRung.MATURE,
        differential=[
            DifferentialItem(
                cause=CauseId.INFECTION,
                probability=0.45,
                supporting=[],
                contradicting=[],
            )
        ],
        evidence_used=["heart_rate"],
        ruled_out=[],
        citations=[],
        unsupported_claims=0,
        action="rest",
        escalation_criteria=["Seek care if fever persists."],
        confidence="moderate",
        interruptions_used_this_week=0,
        depth_used_this_episode=0,
    )


def test_deterministic_grounding_runs_before_llm_critique() -> None:
    """Deterministic grounding cleans false reassurance or ungrounded assertions prior to LLM critique."""
    # Draft with prohibited false reassurance phrases from FALSE_REASSURANCE_PHRASES
    raw_obs = "No need to worry, you are completely fine. Heart rate elevated."
    draft = _make_dummy_draft(obs=raw_obs)
    state: EpisodeState = {
        "episode_id": "ep_ground_test",
        "subject_id": "sub_001",
        "draft": draft,
        "step": 1,
    }

    mock_client = MagicMock()
    mock_client.complete.return_value = (
        CritiqueResponse(approved=True, stripped_claims=[], modified_text=""),
        LLMUsage(),
    )

    res = node_critique(state, llm_client=mock_client)
    res_draft = res["draft"]
    # False reassurance was deterministically stripped
    assert "No need to worry" not in res_draft.observation
    assert "completely fine" not in res_draft.observation


def test_critique_can_only_strip_more() -> None:
    """The LLM critique pass can remove or shorten claims, but can never inject new ungrounded claims."""
    raw_obs = "Elevated heart rate observed with mild cough."
    draft = _make_dummy_draft(obs=raw_obs)
    state: EpisodeState = {
        "episode_id": "ep_strip_test",
        "subject_id": "sub_001",
        "draft": draft,
        "step": 1,
    }

    mock_client = MagicMock()
    # Model strips 'with mild cough'
    mock_client.complete.return_value = (
        CritiqueResponse(
            approved=False,
            stripped_claims=["with mild cough"],
            modified_text="Elevated heart rate observed.",
        ),
        LLMUsage(),
    )

    res = node_critique(state, llm_client=mock_client)
    assert "mild cough" not in res["draft"].observation
    assert res["draft"].observation == "Elevated heart rate observed."


def test_llm_unavailable_in_critique_still_grounds() -> None:
    """When LLM is down, deterministic grounding still runs and succeeds without raising."""
    raw_obs = "You are fine. Elevated heart rate observed."
    draft = _make_dummy_draft(obs=raw_obs)
    state: EpisodeState = {
        "episode_id": "ep_llm_down_critique",
        "subject_id": "sub_001",
        "draft": draft,
        "step": 1,
    }

    mock_client = MagicMock()
    mock_client.complete.side_effect = LLMUnavailable("Ollama is offline")

    res = node_critique(state, llm_client=mock_client)
    assert res["draft"] is not None
    assert "You are fine" not in res["draft"].observation


def test_human_reject_closes_unresolved() -> None:
    """When human review rejects the draft, outcome is marked unresolved."""
    draft = _make_dummy_draft()
    state: EpisodeState = {
        "episode_id": "ep_review_reject",
        "subject_id": "sub_001",
        "draft": draft,
        "step": 1,
    }

    with patch("wha.agent.nodes.review.interrupt", return_value={"decision": "reject"}):
        res = node_review(state)

    assert res["status"] == "unresolved"
    assert res["draft"].disposition == Disposition.UNRESOLVED


def test_human_edit_preserves_machine_fields() -> None:
    """When human edits observation prose, machine fields (disposition, differential, baseline) are preserved."""
    draft = _make_dummy_draft(obs="Original machine text")
    state: EpisodeState = {
        "episode_id": "ep_review_edit",
        "subject_id": "sub_001",
        "draft": draft,
        "step": 1,
    }

    with patch(
        "wha.agent.nodes.review.interrupt",
        return_value={
            "decision": "edit",
            "edited_observation": "Clinician edited observation note.",
        },
    ):
        res = node_review(state)

    assert res["status"] == "closed"
    assert res["draft"].observation == "Clinician edited observation note."
    # Machine fields preserved exactly
    assert res["draft"].disposition == draft.disposition
    assert res["draft"].differential == draft.differential
    assert res["draft"].baseline_nights == draft.baseline_nights
    assert res["draft"].baseline_rung == draft.baseline_rung
