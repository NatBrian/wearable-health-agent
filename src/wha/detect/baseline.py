"""Shrinkage baseline estimation and the maturity ladder."""

import statistics
from collections.abc import Sequence

from wha.constants import (
    BASELINE_MIN_NIGHTS_PERSONAL,
    BASELINE_SCALE_FLOOR_BPM,
    BASELINE_WINDOW_NIGHTS,
    MAD_TO_SD_FACTOR,
    POP_PRIOR_RHR_MEAN_BPM,
    RUNG_COLD_MAX_NIGHTS,
    RUNG_PERSONAL_MAX_NIGHTS,
    RUNG_PRIOR_MAX_NIGHTS,
    RUNG_SHRINKING_MAX_NIGHTS,
    SHRINKAGE_PSEUDO_NIGHTS,
    WITHIN_PERSON_SCALE_PRIOR_BPM,
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
    """Expected resting heart rate and scale from the trailing usable history.

    `history` must contain only usable nights within the trailing BASELINE_WINDOW_NIGHTS,
    excluding tonight.

    The centre is the person's own median once BASELINE_MIN_NIGHTS_PERSONAL nights exist,
    and a shrinkage estimate toward the population prior before that.

    The scale stays a shrinkage estimate throughout, and that is deliberate: it sets the
    width of the band and `robust_z`, never the level, so borrowing while little is known
    is a truthful statement of uncertainty rather than a bias in the decision. A MAD over
    seven nights of whole-number heart rates is also badly quantised, landing on multiples
    of 1.4826, and shrinkage is what smooths that.

    What it shrinks TOWARD was wrong until 5 September 2026. It was
    POP_PRIOR_RHR_SD_BPM, 8.64, which is how much 525 different adults differ from EACH
    OTHER. The band's width is how much one person differs from THEMSELVES between nights,
    a different quantity, measured at 3.71 bpm across 107 people. See
    WITHIN_PERSON_SCALE_PRIOR_BPM, which records what changed and what it cost.
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
            scale_bpm=WITHIN_PERSON_SCALE_PRIOR_BPM,
            usable_nights=0,
            rung=rung,
            shrink_weight=0.0,
        )

    rhrs = [float(night.rhr_bpm) for night in usable_history if night.rhr_bpm is not None]
    personal_median = statistics.median(rhrs)

    # Once there is enough of the person's own data, the centre IS their own median.
    #
    # The detection thresholds come from NightSignal, which measures deviations above a
    # per-individual streaming median with no population blending. Keeping a shrunk centre
    # and applying those thresholds to it leaves a permanent offset that eats the very
    # margin they measure: the trailing window caps n, so the shrink weight caps at 0.8 and
    # a fifth of the prior never washes out. See BASELINE_MIN_NIGHTS_PERSONAL.
    #
    # Below that count the shrinkage estimate is kept, because a median over one or two
    # nights is noise. Nothing is flagged there either, which is what the source does.
    if n >= BASELINE_MIN_NIGHTS_PERSONAL:
        centre_bpm = personal_median
    else:
        centre_bpm = w * personal_median + (1.0 - w) * POP_PRIOR_RHR_MEAN_BPM

    abs_devs = [abs(x - personal_median) for x in rhrs]
    mad = statistics.median(abs_devs)
    personal_sd = MAD_TO_SD_FACTOR * mad
    scale_shrunk = w * personal_sd + (1.0 - w) * WITHIN_PERSON_SCALE_PRIOR_BPM
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
