"""Unit tests for believe and decide graph nodes, including unidirectional LLM veto."""

from datetime import date
from unittest.mock import MagicMock

from wha.agent import (
    EpisodeState,
    VetoCheckResponse,
    node_believe,
    node_decide,
)
from wha.belief import load_causes
from wha.llm.client import LLMUsage
from wha.models import (
    ActionKind,
    BeliefState,
    CauseId,
    Detection,
    DetectionLevel,
    Forecast,
)

_cached_priors = load_causes()
_base_marginals = {p.cause: p.base_rate for p in _cached_priors}


def _make_belief(p_inf: float) -> BeliefState:
    marginals = dict(_base_marginals)
    marginals[CauseId.INFECTION] = p_inf
    return BeliefState(
        marginals=marginals,
        p_illness=p_inf,
    )


def test_veto_cannot_authorise() -> None:
    """The model cannot authorise an ask or action that policy did not select; veto is strictly unidirectional."""
    # When policy decides OBSERVE or CONCLUDE, LLM veto prompt cannot change action to ASK
    state: EpisodeState = {
        "episode_id": "ep_001",
        "subject_id": "sub_001",
        "nights": [],
        "evidence": [],
        "depth_used": 0,
        "step": 1,
        # Belief that yields OBSERVE or CONCLUDE (p=0.01 is below the testing threshold)
        "belief": _make_belief(0.01),
    }

    mock_client = MagicMock()
    # Attempt to supply a veto payload that tries to force an ask
    mock_client.complete.return_value = (
        VetoCheckResponse(veto=False, reason="Want to ask user"),
        LLMUsage(),
    )

    result = node_decide(state, llm_client=mock_client)
    # Action remains OBSERVE / CONCLUDE, never forced to ASK
    assert result["action"].kind in (ActionKind.OBSERVE, ActionKind.CONCLUDE)
    assert result["action"].kind != ActionKind.ASK


def test_llm_veto_does_not_consume_budget() -> None:
    """When an authorised ASK is vetoed by the model, depth budget is not consumed and veto is recorded."""
    # Belief with p_illness=0.12 inside the uncertainty band with high EVSI probe
    state: EpisodeState = {
        "episode_id": "ep_001",
        "subject_id": "sub_001",
        "nights": [
            Detection(
                subject_id="sub_001",
                night_date=date(2026, 8, 20),
                level=DetectionLevel.YELLOW,
                flagged=False,
                residual_bpm=3.5,
                robust_z=2.0,
                forecast=Forecast(),
            )
        ],
        "evidence": [],
        "depth_used": 1,
        "step": 2,
        "belief": _make_belief(0.12),
    }

    mock_client = MagicMock()
    # Model vetos the proposed ask
    mock_client.complete.return_value = (
        VetoCheckResponse(veto=True, reason="User already logged alcohol consumption."),
        LLMUsage(),
    )

    result = node_decide(state, llm_client=mock_client)
    # The ASK was vetoed -> converted to OBSERVE
    assert result["action"].kind == ActionKind.OBSERVE
    assert "Vetoed" in result["action"].rationale
    # Depth budget was NOT consumed
    assert result["depth_used"] == 1


def test_belief_row_written_with_trigger() -> None:
    """node_believe recomputes belief and writes a row with trigger='node_believe'."""
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
        "step": 1,
    }

    mock_db = MagicMock()
    result = node_believe(state, db=mock_db)

    assert "belief" in result
    assert isinstance(result["belief"], BeliefState)
    assert mock_db.append_belief.called
    call_kwargs = mock_db.append_belief.call_args.kwargs
    assert call_kwargs.get("trigger") == "node_believe"
    assert call_kwargs.get("episode_id") == "ep_001"
