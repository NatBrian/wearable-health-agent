"""Exact enumeration inference in log-space over 4096 causal states."""

from collections.abc import Sequence

import numpy as np

from wha.belief.states import CAUSE_ORDER, PRESENT
from wha.constants import RESIDUAL_OBS_SD_BPM
from wha.models import CauseId, CausePrior


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

        prof = cp.profile
        # Clamped at BOTH ends. Only the upper bound was applied here, while the duplicate
        # copy in likelihood.py clamped both, and the copy with the weaker guard was the
        # live one. A negative elapsed count, which arises the moment nights are not in
        # ascending order, indexed the profile from its tail: prof[-1] is the
        # fully-resolved weight, so an out-of-order night silently asserted that every
        # cause had already run its course.
        idx = max(0, min(elapsed_nights, len(prof) - 1))
        w_t_list.append(prof[idx])

    mu_eff = np.array(mu_eff_list, dtype=np.float64)
    sd_eff = np.array(sd_eff_list, dtype=np.float64)
    w_t = np.array(w_t_list, dtype=np.float64)

    # State mean and variance
    mu = (PRESENT * (mu_eff * w_t)).sum(axis=1)  # (4096,)
    var = (RESIDUAL_OBS_SD_BPM**2) + (PRESENT * ((sd_eff * w_t) ** 2)).sum(axis=1)  # (4096,)

    # Gaussian log-density: -0.5 * (log(2*pi*var) + (r - mu)^2 / var)
    return -0.5 * (np.log(2.0 * np.pi * var) + ((residual_bpm - mu) ** 2) / var)
