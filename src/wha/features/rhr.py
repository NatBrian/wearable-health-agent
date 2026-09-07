"""Derivation of nocturnal resting heart rate and data coverage metrics."""

import statistics
from collections.abc import Sequence
from datetime import datetime

from wha.constants import HR_PLAUSIBLE_MAX_BPM, HR_PLAUSIBLE_MIN_BPM, MIN_NOCTURNAL_MINUTES
from wha.db import from_iso
from wha.models import HeartRateSample


def compute_nocturnal_rhr(
    samples: Sequence[HeartRateSample | dict],
) -> tuple[float | None, int, int, bool]:
    """Derive nocturnal resting heart rate and quality metrics from samples inside the window.

    Returns:
        (rhr_bpm, coverage_minutes, implausible_dropped, usable)
    """
    plausible_values: list[float] = []
    distinct_minutes: set[str] = set()
    implausible_dropped = 0

    for item in samples:
        if isinstance(item, HeartRateSample):
            ts = item.ts_utc
            avg_bpm = item.avg_bpm
        else:
            ts = from_iso(item["ts_utc"]) if isinstance(item["ts_utc"], str) else item["ts_utc"]
            avg_bpm = float(item["avg_bpm"])

        if HR_PLAUSIBLE_MIN_BPM <= avg_bpm <= HR_PLAUSIBLE_MAX_BPM:
            plausible_values.append(avg_bpm)
            # Minute-level key
            if isinstance(ts, datetime):
                minute_key = ts.strftime("%Y-%m-%dT%H:%M")
            else:
                minute_key = str(ts)[:16]
            distinct_minutes.add(minute_key)
        else:
            implausible_dropped += 1

    coverage_minutes = len(distinct_minutes)
    rhr_bpm: float | None = float(statistics.median(plausible_values)) if plausible_values else None
    usable = bool(coverage_minutes >= MIN_NOCTURNAL_MINUTES and rhr_bpm is not None)

    return rhr_bpm, coverage_minutes, implausible_dropped, usable


def nocturnal_rhr(samples: Sequence[HeartRateSample | dict]) -> float | None:
    """Return median resting heart rate from plausible samples, or None if none exist."""
    rhr, _, _, _ = compute_nocturnal_rhr(samples)
    return rhr
