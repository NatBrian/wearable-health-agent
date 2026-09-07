"""Expected Value of Sample Information (EVSI) and utility calculations."""

import logging
from typing import Any

import numpy as np

from wha.belief.inference import softmax
from wha.belief.states import CAUSE_ORDER, PRESENT
from wha.constants import (
    POLICY_COST_PER_INTERRUPT,
    UTILITY_FALSE_ALARM,
    UTILITY_MISS_ILLNESS,
)
from wha.models import BeliefState, CauseId, Probe
from wha.policy.probes import ProbeDefinition

logger = logging.getLogger(__name__)

# Indifference threshold P* = |U_FALSE_ALARM| / (|U_FALSE_ALARM| + |U_MISS_ILLNESS|) = 1 / (1 + 9) = 0.10
DERIVED_TREATMENT_THRESHOLD = abs(UTILITY_FALSE_ALARM) / (
    abs(UTILITY_FALSE_ALARM) + abs(UTILITY_MISS_ILLNESS)
)


def compute_eu_now(p_illness: float) -> float:
    """Compute expected utility of acting right now without further information."""
    eu_illness = UTILITY_FALSE_ALARM * (1.0 - p_illness)
    eu_benign = UTILITY_MISS_ILLNESS * p_illness
    return max(eu_illness, eu_benign)


def evsi(
    belief: BeliefState,
    probe: Probe | ProbeDefinition | dict[str, Any],
) -> float:
    """Compute Expected Value of Sample Information for a probe given current belief.

    Always >= 0.0. Exactly 0.0 when no answer could change the decision.
    """
    p_inf = belief.p_illness
    eu_now = compute_eu_now(p_inf)

    # Extract probe properties
    if isinstance(probe, dict):
        target_cause_raw = probe.get("target_cause")
        answer_space = probe.get("answer_space", [])
        lik_pres = probe.get("likelihood_present", probe.get("likelihood", {}).get("present", {}))
        lik_abs = probe.get("likelihood_absent", probe.get("likelihood", {}).get("absent", {}))
    elif isinstance(probe, ProbeDefinition):
        target_cause_raw = probe.target_cause
        answer_space = probe.answer_space
        lik_pres = probe.likelihood_present
        lik_abs = probe.likelihood_absent
    else:
        target_cause_raw = probe.target_cause
        answer_space = probe.answer_space
        lik_pres = {}
        lik_abs = {}

    target_cause = CauseId(str(target_cause_raw)) if target_cause_raw else CauseId.INFECTION

    # If state_logprob is available and valid, compute exact expected utility over 4096 states
    if len(belief.state_logprob) == 4096 and target_cause in CAUSE_ORDER:
        target_idx = CAUSE_ORDER.index(target_cause)
        inf_idx = CAUSE_ORDER.index(CauseId.INFECTION)
        curr_state_post = softmax(np.array(belief.state_logprob))

        eu_expected = 0.0

        for opt in answer_space:
            opt_id = opt.option_id if hasattr(opt, "option_id") else opt.get("option_id")
            p_pres = float(lik_pres.get(str(opt_id), 0.5))
            p_abs = float(lik_abs.get(str(opt_id), 0.5))

            # Likelihood of this answer per state
            lik_per_state = np.where(PRESENT[:, target_idx], p_pres, p_abs)
            p_ans = float(np.sum(curr_state_post * lik_per_state))

            if p_ans <= 1e-12:
                continue

            # Update posterior given answer
            log_lik_ans = np.log(np.maximum(lik_per_state, 1e-12))
            post_ans = softmax(np.array(belief.state_logprob) + log_lik_ans)
            p_inf_after = float(np.sum(post_ans * PRESENT[:, inf_idx]))

            eu_after = compute_eu_now(p_inf_after)
            eu_expected += p_ans * eu_after

        val = eu_expected - eu_now
        return max(0.0, round(float(val), 6))

    # Fast 1D projection fallback.
    #
    # This branch cannot represent explaining-away: for any probe that does not target
    # infection it leaves p_illness unchanged, so EVSI is exactly zero and the probe is
    # never worth its interruption cost. That is a silent, total loss of the policy's
    # reason to ask about alcohol, exercise, stress or sleep, so a belief that reaches
    # here with no joint state at all is reported rather than quietly degraded.
    if not belief.state_logprob and target_cause != CauseId.INFECTION:
        logger.warning(
            "EVSI for probe targeting %s computed without a joint log-posterior. "
            "The projection cannot represent explaining-away and will score 0.0, so "
            "this probe will not be asked. A belief loaded from storage should carry "
            "beliefs.state_logprob_json.",
            target_cause,
        )

    p_target = belief.marginals.get(target_cause, p_inf)
    eu_expected = 0.0

    for opt in answer_space:
        opt_id = opt.option_id if hasattr(opt, "option_id") else opt.get("option_id")
        p_pres = float(lik_pres.get(str(opt_id), 0.5))
        p_abs = float(lik_abs.get(str(opt_id), 0.5))

        p_ans = p_target * p_pres + (1.0 - p_target) * p_abs
        if p_ans <= 1e-12:
            continue

        p_target_after = (p_target * p_pres) / p_ans
        # For infection probe, p_inf_after = p_target_after
        p_inf_after = p_target_after if target_cause == CauseId.INFECTION else p_inf
        eu_after = compute_eu_now(p_inf_after)
        eu_expected += p_ans * eu_after

    val = eu_expected - eu_now
    return max(0.0, round(float(val), 6))


def score_probe(
    belief: BeliefState,
    probe: Probe | ProbeDefinition,
    cost_per_interrupt: float = POLICY_COST_PER_INTERRUPT,
) -> float:
    """Compute net decision value of asking a probe: EVSI minus interruption cost."""
    gain = evsi(belief, probe)
    cost = probe.interruption_cost * cost_per_interrupt
    return round(gain - cost, 6)
