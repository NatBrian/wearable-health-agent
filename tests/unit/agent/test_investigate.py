"""Unit tests for preload and investigate graph nodes."""

from datetime import date
from unittest.mock import MagicMock

from wha.agent import (
    EpisodeState,
    FactExtractionResponse,
    InvestigateStep,
    ToolCallArgs,
    node_investigate,
    node_preload,
)
from wha.agent.nodes import DoneSignal
from wha.constants import MAX_TOOL_CALLS_PER_EPISODE
from wha.errors import LLMUnavailable
from wha.llm.client import LLMUsage
from wha.models import Detection, DetectionLevel, ExtractedFact, Forecast


def test_preload_populates_cheap_context() -> None:
    """node_preload populates preloaded dictionary with all 5 cheap context categories."""
    d1 = Detection(
        subject_id="sub_001",
        night_date=date(2026, 8, 20),
        level=DetectionLevel.YELLOW,
        flagged=False,
        residual_bpm=3.1,
        robust_z=1.8,
        forecast=Forecast(),
    )
    state: EpisodeState = {
        "episode_id": "ep_001",
        "subject_id": "sub_001",
        "nights": [d1],
        "step": 0,
    }

    result = node_preload(state)
    assert "preloaded" in result
    preloaded = result["preloaded"]
    assert "nightly_features" in preloaded
    assert "personal_baseline" in preloaded
    assert "known_events" in preloaded
    assert "data_quality" in preloaded
    assert "similar_past_episodes" in preloaded
    assert result["step"] == 1


def test_investigate_can_still_call_preloaded_tool() -> None:
    """Preloading is an optimisation: investigate can freely call any tool including preloaded ones."""
    state: EpisodeState = {
        "episode_id": "ep_001",
        "subject_id": "sub_001",
        "preloaded": {"nightly_features": []},
        "tool_calls": [],
        "evidence": [],
        "step": 1,
    }

    mock_client = MagicMock()
    mock_client.complete.side_effect = [
        (
            InvestigateStep(
                tool_call=ToolCallArgs(
                    tool_name="get_nightly_features",
                    args={"start": "2026-08-01", "end": "2026-08-10"},
                )
            ),
            LLMUsage(),
        ),
        (
            InvestigateStep(done=DoneSignal(reason="Got required features.")),
            LLMUsage(),
        ),
        (
            FactExtractionResponse(),
            LLMUsage(),
        ),
    ]

    result = node_investigate(state, llm_client=mock_client)
    assert len(result["tool_calls"]) == 1
    assert result["tool_calls"][0]["tool_name"] == "get_nightly_features"


def test_tool_call_cap_terminates_investigation() -> None:
    """Investigation loop strictly halts when MAX_TOOL_CALLS_PER_EPISODE is reached."""
    state: EpisodeState = {
        "episode_id": "ep_001",
        "subject_id": "sub_001",
        "preloaded": {},
        "tool_calls": [],
        "tool_call_count": MAX_TOOL_CALLS_PER_EPISODE,
        "evidence": [],
        "step": 1,
    }

    mock_client = MagicMock()
    # When cap reached, investigation loop doesn't invoke investigate prompt, only extract_facts if called
    mock_client.complete.return_value = (
        FactExtractionResponse(),
        LLMUsage(),
    )

    result = node_investigate(state, llm_client=mock_client)
    assert len(result["tool_calls"]) == 0
    assert result["tool_call_count"] == MAX_TOOL_CALLS_PER_EPISODE


def test_unregistered_tool_is_denied() -> None:
    """Model attempting an unregistered tool call gets permission_decision='denied' in tool_calls."""
    state: EpisodeState = {
        "episode_id": "ep_001",
        "subject_id": "sub_001",
        "preloaded": {},
        "tool_calls": [],
        "evidence": [],
        "step": 1,
    }

    mock_client = MagicMock()
    mock_client.complete.side_effect = [
        (
            InvestigateStep(
                tool_call=ToolCallArgs(
                    tool_name="open_web_search",
                    args={"query": "dengue symptoms"},
                )
            ),
            LLMUsage(),
        ),
        (
            InvestigateStep(done=DoneSignal(reason="Done.")),
            LLMUsage(),
        ),
        (
            FactExtractionResponse(),
            LLMUsage(),
        ),
    ]

    result = node_investigate(state, llm_client=mock_client)
    assert len(result["tool_calls"]) == 1
    denied_call = result["tool_calls"][0]
    assert denied_call["permission_decision"] == "denied"
    assert denied_call["ok"] is False


def test_untrusted_text_produces_typed_output_only() -> None:
    """Investigation node only outputs typed ExtractedFact objects in evidence."""
    state: EpisodeState = {
        "episode_id": "ep_001",
        "subject_id": "sub_001",
        "preloaded": {},
        "tool_calls": [],
        "evidence": [],
        "step": 1,
    }

    mock_client = MagicMock()
    extracted_fact = ExtractedFact(
        field="fever_onset",
        value="2026-08-20",
        evidence_span="fever started 2 days ago",
        source_ref="doc_123",
        confidence="stated",
    )

    mock_client.complete.side_effect = [
        (InvestigateStep(done=DoneSignal(reason="Done.")), LLMUsage()),
        (FactExtractionResponse(facts=[extracted_fact]), LLMUsage()),
    ]

    result = node_investigate(state, llm_client=mock_client)
    assert len(result["evidence"]) == 1
    fact = result["evidence"][0]
    assert isinstance(fact, ExtractedFact)
    assert fact.field == "fever_onset"
    assert fact.value == "2026-08-20"


def test_llm_unavailable_parks_not_closes() -> None:
    """When LLM raises LLMUnavailable, node_investigate parks the episode without closing."""
    state: EpisodeState = {
        "episode_id": "ep_001",
        "subject_id": "sub_001",
        "preloaded": {},
        "tool_calls": [],
        "evidence": [],
        "step": 1,
    }

    mock_client = MagicMock()
    mock_client.complete.side_effect = LLMUnavailable("Ollama connection refused on port 11434")

    result = node_investigate(state, llm_client=mock_client)
    assert result["status"] == "parked"
    assert result["step"] == 2
