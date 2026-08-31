"""Shrinkage baseline estimation and the maturity ladder."""

import statistics
from collections.abc import Sequence

from wha.constants import (
    BASELINE_SCALE_FLOOR_BPM,
    BASELINE_WINDOW_NIGHTS,
    MAD_TO_SD_FACTOR,
    POP_PRIOR_RHR_MEAN_BPM,
    POP_PRIOR_RHR_SD_BPM,
    RUNG_COLD_MAX_NIGHTS,
    RUNG_PERSONAL_MAX_NIGHTS,
    RUNG_PRIOR_MAX_NIGHTS,
    RUNG_SHRINKING_MAX_NIGHTS,
    SHRINKAGE_PSEUDO_NIGHTS,
)
from wha.models import Baseline, BaselineRung, NightlyFeatures


def rung_for(usable_nights: int) -> BaselineRung:
    """Return the maturity rung corresponding to the number of usable baseline nights."""
    if usable_nights <= RUNG_COLD_MAX_NIGHTS:
        return BaselineRung.COLD
    elif usable_nights <= RUNG_PRIOR_MAX_NIGHTS:
        return BaselineRung.PRIOR_DOMINATED
    elif usable_nights <= RUNG_SHRINKING_MAX_NIGHTS:
        return BaselineRung.SHRINKING
    elif usable_nights <= RUNG_PERSONAL_MAX_NIGHTS:
        return BaselineRung.PERSONAL
    else:
        return BaselineRung.MATURE


def compute_baseline(history: Sequence[NightlyFeatures]) -> Baseline:
    """Shrinkage estimate of expected resting heart rate and scale from trailing usable history.

    `history` must contain only usable nights within the trailing BASELINE_WINDOW_NIGHTS,
    excluding tonight.
    """
    usable_history = [night for night in history if night.usable and night.rhr_bpm is not None][
        -BASELINE_WINDOW_NIGHTS:
    ]

    n = len(usable_history)
    w = n / (n + SHRINKAGE_PSEUDO_NIGHTS)
    rung = rung_for(n)

    if n == 0:
        return Baseline(
            centre_bpm=POP_PRIOR_RHR_MEAN_BPM,
            scale_bpm=POP_PRIOR_RHR_SD_BPM,
            usable_nights=0,
            rung=rung,
            shrink_weight=0.0,
        )

    rhrs = [float(night.rhr_bpm) for night in usable_history if night.rhr_bpm is not None]
    personal_median = statistics.median(rhrs)
    centre_bpm = w * personal_median + (1.0 - w) * POP_PRIOR_RHR_MEAN_BPM

    abs_devs = [abs(x - personal_median) for x in rhrs]
    mad = statistics.median(abs_devs)
    personal_sd = MAD_TO_SD_FACTOR * mad
    scale_shrunk = w * personal_sd + (1.0 - w) * POP_PRIOR_RHR_SD_BPM
    scale_bpm = max(scale_shrunk, BASELINE_SCALE_FLOOR_BPM)

    return Baseline(
        centre_bpm=round(centre_bpm, 3),
        scale_bpm=round(scale_bpm, 3),
        usable_nights=n,
        rung=rung,
        shrink_weight=round(w, 4),
    )


def compute_baseline_truncated(history: Sequence[NightlyFeatures], max_nights: int) -> Baseline:
    """Compute baseline truncated to at most max_nights of history for evaluation."""
    usable_history = [night for night in history if night.usable and night.rhr_bpm is not None]
    truncated = usable_history[-max_nights:] if max_nights > 0 else []
    return compute_baseline(truncated)
