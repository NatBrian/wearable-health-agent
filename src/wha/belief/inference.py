"""Exact enumeration inference in log-space over 4096 causal states."""

from collections.abc import Sequence

import numpy as np

from wha.belief.causes import load_causes
from wha.belief.states import CAUSE_ORDER, PRESENT
from wha.constants import RESIDUAL_OBS_SD_BPM
from wha.models import BeliefState, CauseId, CausePrior, Detection


def softmax(log_probs: np.ndarray) -> np.ndarray:
    """Stable softmax using max-subtraction to prevent overflow and underflow."""
    max_val = np.max(log_probs)
    exp_shifted = np.exp(log_probs - max_val)
    return exp_shifted / np.sum(exp_shifted)


def compute_prior_logprobs(
    priors: Sequence[CausePrior],
    luteal_applicable: bool = True,
) -> np.ndarray:
    """Compute prior log-probabilities over all 4096 states from cause base rates."""
    prior_map = {p.cause: p for p in priors}
    base_rates: list[float] = []

    for cause in CAUSE_ORDER:
        if cause == CauseId.LUTEAL and not luteal_applicable:
            base_rates.append(1e-12)
        else:
            base_rates.append(prior_map[cause].base_rate)

    p = np.array(base_rates, dtype=np.float64)
    # Clip to avoid log(0)
    p = np.clip(p, 1e-12, 1.0 - 1e-12)

    log_p = np.log(p)
    log_not_p = np.log(1.0 - p)

    # PRESENT @ log_p + (~PRESENT) @ log_not_p of shape (4096,)
    return PRESENT @ log_p + (~PRESENT) @ log_not_p


def compute_residual_loglik(
    residual_bpm: float,
    elapsed_nights: int,
    priors: Sequence[CausePrior],
) -> np.ndarray:
    """Compute log-likelihood vector of shape (4096,) for an observed residual on night t."""
    prior_map = {p.cause: p for p in priors}

    mu_eff_list: list[float] = []
    sd_eff_list: list[float] = []
    w_t_list: list[float] = []

    for cause in CAUSE_ORDER:
        cp = prior_map[cause]
        mu_eff_list.append(cp.effect_mean_bpm)
        sd_eff_list.append(cp.effect_sd_bpm)

        # Profile lookup: last value repeats for t >= len(profile)
        prof = cp.profile
        idx = min(elapsed_nights, len(prof) - 1)
        w_t_list.append(prof[idx])

    mu_eff = np.array(mu_eff_list, dtype=np.float64)
    sd_eff = np.array(sd_eff_list, dtype=np.float64)
    w_t = np.array(w_t_list, dtype=np.float64)

    # State mean and variance
    mu = (PRESENT * (mu_eff * w_t)).sum(axis=1)  # (4096,)
    var = (RESIDUAL_OBS_SD_BPM**2) + (PRESENT * ((sd_eff * w_t) ** 2)).sum(axis=1)  # (4096,)

    # Gaussian log-density: -0.5 * (log(2*pi*var) + (r - mu)^2 / var)
    return -0.5 * (np.log(2.0 * np.pi * var) + ((residual_bpm - mu) ** 2) / var)


def run_exact_inference(
    detections: Sequence[Detection] = (),
    extra_log_factors: Sequence[np.ndarray] = (),
    priors: Sequence[CausePrior] | None = None,
    luteal_applicable: bool | None = None,
) -> BeliefState:
    """Perform exact Bayesian enumeration over 4096 states and return marginals.

    Pure and deterministic. Always operates in log-space.

    ``luteal_applicable`` is three-state and defaults to unknown, matching update_belief.
    Defaulting it to True here while update_belief treated unknown as inert made the two
    entry points return different posteriors for identical input.
    """
    cause_priors = priors if priors is not None else load_causes()
    luteal_is_live = luteal_applicable is True
    log_post = compute_prior_logprobs(cause_priors, luteal_applicable=luteal_is_live)

    # Add residual likelihoods from each detection.
    #
    # Indexed by calendar nights elapsed, matching update_belief. This used the position
    # in the list, so a sequence with a gap in it gave the two entry points different
    # posteriors for identical data: a cause three days into its course was treated as
    # being on its second night.
    ordered = sorted(detections, key=lambda d: d.night_date)
    if ordered:
        first_night = ordered[0].night_date
        for det in ordered:
            if det.residual_bpm is not None and det.level != "NA":
                log_lik_t = compute_residual_loglik(
                    residual_bpm=det.residual_bpm,
                    elapsed_nights=(det.night_date - first_night).days,
                    priors=cause_priors,
                )
                log_post = log_post + log_lik_t

    # Add external evidence log-factors (answers, sensor quality, etc.)
    for factor in extra_log_factors:
        log_post = log_post + factor

    post = softmax(log_post)  # (4096,)
    marginals_arr = PRESENT.T @ post  # (12,)

    marginals_dict: dict[CauseId, float] = {
        cause: float(marginals_arr[i]) for i, cause in enumerate(CAUSE_ORDER)
    }

    p_illness = marginals_dict[CauseId.INFECTION]

    return BeliefState(
        marginals=marginals_dict,
        p_illness=round(p_illness, 4),
        state_logprob=log_post.tolist(),
    )
