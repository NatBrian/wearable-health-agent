"""Belief and causal inference module."""

from collections.abc import Sequence
from typing import Any

from wha.belief.causes import load_causes
from wha.belief.inference import (
    compute_prior_logprobs,
    compute_residual_loglik,
    softmax,
)
from wha.belief.likelihood import (
    compute_answer_logfactor,
    compute_coverage_logfactor,
    compute_exercise_logfactor,
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
    luteal_applicable: bool | None = None,
) -> BeliefState:
    """Recompute belief distribution from scratch over all episode observations.

    Pure, deterministic, and exact across all 4096 states in log-space.
    """
    cause_priors = priors if priors is not None else load_causes()

    # Cycle applicability is a three-state fact, not a boolean: True, False, or not yet
    # asked. causes.yaml gives luteal base_rate 0.450 CONDITIONAL on the subject
    # menstruating, base_rate_if_not_applicable 0.0 otherwise, and its own note records
    # that this concerns "around half the population".
    #
    # Defaulting an unasked subject to applicable was wrong twice over. It is factually
    # wrong for everyone who does not menstruate, and it fails in one direction only: at
    # 3.91 bpm and a 0.450 base rate, luteal is the largest benign effect in the table, so
    # assuming it applies lets it explain away precisely the elevations this system exists
    # to investigate. Measured on the illness-onset scenario, assuming applicability holds
    # p(infection) at 0.025 and the policy never finds a question worth asking; treating
    # it as unestablished gives 0.070, and probe_symptoms becomes worth its interruption.
    #
    # Unknown therefore leaves the cause inert until probe_cycle establishes it, which is
    # the low-cost one_time setup question that exists for exactly this purpose.
    if context is not None:
        ctx_value = (
            context.get("cycle_applicable", context.get("luteal_applicable"))
            if isinstance(context, dict)
            else getattr(context, "cycle_applicable", getattr(context, "luteal_applicable", None))
        )
        if ctx_value is not None:
            luteal_applicable = bool(ctx_value)

    luteal_is_live = luteal_applicable is True

    log_post = compute_prior_logprobs(cause_priors, luteal_applicable=luteal_is_live)

    # 1. Residual likelihoods per calendar elapsed night.
    #
    # Sorted, because elapsed counts are measured from the first night and a caller
    # passing nights in any other order would produce negative offsets into the temporal
    # profiles.
    if episode_nights:
        ordered_nights = sorted(episode_nights, key=lambda d: d.night_date)
        start_date = ordered_nights[0].night_date
        for det in ordered_nights:
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

    # 4. Spot measurements were removed on 5 September 2026, with the limb that produced
    #    them. `compute_measurement_logfactor` moved weight away from sensor artifact by a
    #    hardcoded -1.5, against 0.3 the other way, and neither number came from anywhere.
    #    The `measurements` parameter is kept so an old caller still type-checks, and it
    #    now contributes nothing. See wha/policy/select.py.

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
        if cause == CauseId.LUTEAL and not luteal_is_live:
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
    "softmax",
    "update_belief",
]
