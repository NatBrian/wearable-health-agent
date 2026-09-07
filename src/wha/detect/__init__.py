"""Detection and baseline models."""

from wha.detect.baseline import (
    compute_baseline,
    compute_baseline_truncated,
    rung_for,
)
from wha.detect.baselines import (
    detect_random,
    detect_trivial,
)
from wha.detect.detector import (
    compute_detection_for_features,
    detect_night,
    detect_range,
)
from wha.detect.explained import explained_bpm

__all__ = [
    "compute_baseline",
    "compute_baseline_truncated",
    "compute_detection_for_features",
    "detect_night",
    "detect_random",
    "detect_range",
    "detect_trivial",
    "explained_bpm",
    "rung_for",
]
