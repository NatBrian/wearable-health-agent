"""Detection and baseline models."""

from wha.detect.baseline import (
    compute_baseline,
    compute_baseline_truncated,
    rung_for,
)
from wha.detect.explained import explained_bpm

__all__ = [
    "compute_baseline",
    "compute_baseline_truncated",
    "explained_bpm",
    "rung_for",
]
