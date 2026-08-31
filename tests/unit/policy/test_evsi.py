"""Unit tests for Expected Value of Sample Information (EVSI) and policy gates."""

import random

from wha.belief import load_causes
from wha.models import (
    BaselineRung,
    BeliefState,
    CauseId,
)
from wha.policy import (
    DERIVED_TREATMENT_THRESHOLD,
    check_all_ask_gates,
    check_depth_budget_gate,
    check_interruption_budget_gate,
    check_rung_gate,
    compute_eu_now,
    evsi,
    load_probes,
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


def test_threshold_derived_from_utilities() -> None:
    """Indifference threshold sits exactly at p = 0.10 where EU_illness == EU_benign."""
    assert abs(DERIVED_TREATMENT_THRESHOLD - 0.10) < 1e-9

    # At p = 0.10: EU_illness = -(1 - 0.10) = -0.90, EU_benign = -9 * 0.10 = -0.90
    eu_at_threshold = compute_eu_now(0.10)
    assert abs(eu_at_threshold - (-0.90)) < 1e-9

    # Below 0.10, benign has higher utility; above 0.10, illness has higher utility
    eu_low = compute_eu_now(0.05)  # max(-0.95, -0.45) = -0.45 (benign)
    assert abs(eu_low - (-0.45)) < 1e-9

    eu_high = compute_eu_now(0.20)  # max(-0.80, -1.80) = -0.80 (illness)
    assert abs(eu_high - (-0.80)) < 1e-9


def test_evsi_never_negative() -> None:
    """EVSI is strictly non-negative across 1000 randomized belief states."""
    probes = load_probes()
    symptoms_probe = next(p for p in probes if p.probe_id == "probe_symptoms")

    rng = random.Random(42)
    for _ in range(1000):
        p_val = rng.random()
        belief = _make_belief(p_val)
        val = evsi(belief, symptoms_probe)
        assert val >= 0.0


def test_evsi_zero_when_decision_cannot_change() -> None:
    """EVSI is exactly 0.0 at extreme probabilities (p=0.01 and p=0.95) where decision is fixed."""
    probes = load_probes()
    symptoms_probe = next(p for p in probes if p.probe_id == "probe_symptoms")

    # Far below threshold: always conclude benign
    assert evsi(_make_belief(0.01), symptoms_probe) == 0.0

    # Far above threshold: always conclude illness
    assert evsi(_make_belief(0.95), symptoms_probe) == 0.0


def test_quiet_band_emerges_without_a_constant() -> None:
    """The system stays silent at both low and high p_illness purely through EVSI vanishing."""
    probes = load_probes()
    symptoms_probe = next(p for p in probes if p.probe_id == "probe_symptoms")

    # Inside uncertainty band around 0.10: EVSI is positive
    val_mid = evsi(_make_belief(0.12), symptoms_probe)
    assert val_mid > 0.0

    # Outside uncertainty band: EVSI goes to 0
    val_low = evsi(_make_belief(0.005), symptoms_probe)
    val_high = evsi(_make_belief(0.98), symptoms_probe)
    assert val_low == 0.0
    assert val_high == 0.0


def test_budget_blocks_ask() -> None:
    """Weekly budget exhaustion blocks further questions."""
    gate = check_interruption_budget_gate(weekly_interruptions_used=2)
    assert not gate.allowed
    assert "Weekly interruption budget exhausted" in (gate.reason or "")

    gate_ok = check_interruption_budget_gate(weekly_interruptions_used=1)
    assert gate_ok.allowed


def test_decline_consumes_budget() -> None:
    """A declined interaction is counted against weekly interruptions."""
    # When 1 question was answered and 1 was declined, total used is 2 (exhausted)
    used = 1 + 1
    gate = check_interruption_budget_gate(weekly_interruptions_used=used)
    assert not gate.allowed


def test_cold_rung_never_asks() -> None:
    """Cold rung blocks asking questions."""
    gate = check_rung_gate(BaselineRung.COLD)
    assert not gate.allowed
    assert "COLD" in (gate.reason or "")


def test_prior_dominated_rung_never_asks() -> None:
    """Prior dominated rung blocks asking questions."""
    gate = check_rung_gate(BaselineRung.PRIOR_DOMINATED)
    assert not gate.allowed
    assert "PRIOR_DOMINATED" in (gate.reason or "")


def test_depth_budget_ends_interview() -> None:
    """Reaching the per-episode depth budget stops questioning."""
    gate = check_depth_budget_gate(episode_questions_asked=5)
    assert not gate.allowed
    assert "Episode depth budget exhausted" in (gate.reason or "")

    all_gates = check_all_ask_gates(
        rung=BaselineRung.MATURE,
        weekly_interruptions=0,
        episode_questions=5,
    )
    assert not all_gates.allowed
