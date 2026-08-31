"""Mandatory benchmark detection baselines for evaluation."""

import random
from collections.abc import Sequence

from wha.constants import DETECT_RED_BPM
from wha.models import NightlyFeatures


def detect_random(alert_rate: float, n_days: int, rng: random.Random | None = None) -> list[bool]:
    """Alert uniformly at random, matched to the detector's alert rate."""
    r = rng if rng is not None else random.Random()
    return [r.random() < alert_rate for _ in range(n_days)]


def detect_trivial(
    nights: Sequence[NightlyFeatures | float | None], all_time_median: float
) -> list[bool]:
    """Alert whenever RHR exceeds all-time median by DETECT_RED_BPM.

    Uses no trailing window, no shrinkage, no explained variance, and no persistence.
    """
    alerts: list[bool] = []
    for item in nights:
        if isinstance(item, NightlyFeatures):
            rhr = item.rhr_bpm if item.usable else None
        else:
            rhr = item

        if rhr is not None and (rhr - all_time_median) >= DETECT_RED_BPM:
            alerts.append(True)
        else:
            alerts.append(False)

    return alerts
