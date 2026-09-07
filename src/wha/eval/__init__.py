"""Evaluation suites, statistical intervals, and metric computations."""

from wha.eval.detection import run_detection_eval
from wha.eval.metrics import (
    calculate_lead_times,
    clopper_pearson_interval,
    cluster_bootstrap_ci,
    evaluate_episode_recall,
    extract_alert_events,
    permutation_test_null,
)

__all__ = [
    "calculate_lead_times",
    "clopper_pearson_interval",
    "cluster_bootstrap_ci",
    "evaluate_episode_recall",
    "extract_alert_events",
    "permutation_test_null",
    "run_detection_eval",
]
