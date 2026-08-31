"""Belief and causal inference module."""

from collections.abc import Sequence
from typing import Any

from wha.belief.causes import load_causes
from wha.belief.inference import (
    compute_prior_logprobs,
    compute_residual_loglik,
    run_exact_inference,
    softmax,
)
from wha.belief.likelihood import (
    compute_answer_logfactor,
    compute_coverage_logfactor,
    compute_exercise_logfactor,
    compute_measurement_logfactor,
    compute_sleep_logfactor,
)
from wha.belief.states import CAUSE_ORDER, NUM_CAUSES, NUM_STATES, PRESENT
from wha.models import (
    Answer,
    BeliefState,
    CauseId,
    CausePrior,
    Detection,
    EpisodeContext,
    MeasurementResult,
    NightlyFeatures,
)


def update_belief(
    episode_nights: Sequence[Detection],
    features: Sequence[NightlyFeatures] = (),
    answers: Sequence[Answer | dict[str, Any]] = (),
    measurements: Sequence[MeasurementResult | dict[str, Any]] = (),
    context: EpisodeContext | dict[str, Any] | None = None,
    priors: Sequence[CausePrior] | None = None,
    luteal_applicable: bool = True,
) -> BeliefState:
    """Recompute belief distribution from scratch over all episode observations.

    Pure, deterministic, and exact across all 4096 states in log-space.
    """
    cause_priors = priors if priors is not None else load_causes()

    # Check luteal config in context
    if context is not None:
        if isinstance(context, dict):
            if context.get("luteal_applicable") is False:
                luteal_applicable = False
        elif hasattr(context, "luteal_applicable") and context.luteal_applicable is False:
            luteal_applicable = False

    log_post = compute_prior_logprobs(cause_priors, luteal_applicable=luteal_applicable)

    # 1. Residual likelihoods per calendar elapsed night
    if episode_nights:
        start_date = episode_nights[0].night_date
        for det in episode_nights:
            elapsed_t = (det.night_date - start_date).days
            if det.level != "NA" and det.residual_bpm is not None:
                log_lik_t = compute_residual_loglik(
                    residual_bpm=det.residual_bpm,
                    elapsed_nights=elapsed_t,
                    priors=cause_priors,
                )
                log_post = log_post + log_lik_t

    # 2. Sensor and physiological covariates
    if features:
        ex_factor = compute_exercise_logfactor(features)
        if ex_factor is not None:
            log_post = log_post + ex_factor

        slp_factor = compute_sleep_logfactor(features)
        if slp_factor is not None:
            log_post = log_post + slp_factor

        cov_factor = compute_coverage_logfactor(features)
        if cov_factor is not None:
            log_post = log_post + cov_factor

    # 3. User answers
    for ans in answers:
        ans_factor = compute_answer_logfactor(ans)
        if ans_factor is not None:
            log_post = log_post + ans_factor

    # 4. Spot measurements
    for meas in measurements:
        meas_factor = compute_measurement_logfactor(meas)
        if meas_factor is not None:
            log_post = log_post + meas_factor

    # 5. Prior illness tail from context
    if context is not None:
        has_prior_illness = False
        if isinstance(context, dict):
            has_prior_illness = bool(context.get("has_recent_illness", False))
        elif hasattr(context, "has_recent_illness"):
            has_prior_illness = bool(context.has_recent_illness)

        if has_prior_illness:
            idx = CAUSE_ORDER.index(CauseId.RECOVERY_TAIL)
            log_post = log_post + (PRESENT[:, idx] * 2.0 + (~PRESENT[:, idx]) * (-0.2))

    post = softmax(log_post)
    marginals_arr = PRESENT.T @ post

    # If luteal is not applicable, enforce exact 0.0 without manual renormalization
    marginals_dict: dict[CauseId, float] = {}
    for i, cause in enumerate(CAUSE_ORDER):
        if cause == CauseId.LUTEAL and not luteal_applicable:
            marginals_dict[cause] = 0.0
        else:
            marginals_dict[cause] = round(float(marginals_arr[i]), 4)

    p_illness = marginals_dict[CauseId.INFECTION]

    return BeliefState(
        marginals=marginals_dict,
        p_illness=round(p_illness, 4),
        state_logprob=log_post.tolist(),
    )


__all__ = [
    "CAUSE_ORDER",
    "NUM_CAUSES",
    "NUM_STATES",
    "PRESENT",
    "compute_prior_logprobs",
    "compute_residual_loglik",
    "load_causes",
    "run_exact_inference",
    "softmax",
    "update_belief",
]
