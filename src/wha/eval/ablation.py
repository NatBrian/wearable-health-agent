"""Ablation evaluation suite measuring value of individual pipeline components."""

import random
from pathlib import Path
from typing import Any

import numpy as np

from wha.errors import ConfigError
from wha.models import EvaluationResult

ABLATION_COMPONENTS = [
    "explained_variance",
    "persistence_rule",
    "chronos_evidence",
    "temporal_profiles",
    "shrinkage_ladder",
    "policy_asking",
]


def paired_bootstrap_difference(
    baseline_scores: dict[str, float],
    ablated_scores: dict[str, float],
    n_resamples: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Paired cluster bootstrap over participants calculating (ablated - baseline) difference CI."""
    participants = list(baseline_scores.keys())
    if not participants:
        return 0.0, 0.0, 0.0

    rng = random.Random(seed)
    n = len(participants)
    diffs: list[float] = []

    for _ in range(n_resamples):
        sample_p = [rng.choice(participants) for _ in range(n)]
        b_mean = np.mean([baseline_scores[p] for p in sample_p])
        a_mean = np.mean([ablated_scores[p] for p in sample_p])
        diffs.append(float(a_mean - b_mean))

    mean_diff = float(np.mean(diffs))
    alpha = 1.0 - confidence
    lower = float(np.percentile(diffs, alpha / 2.0 * 100))
    upper = float(np.percentile(diffs, (1.0 - alpha / 2.0) * 100))

    return round(mean_diff, 4), round(lower, 4), round(upper, 4)


def run_ablation_eval(
    labels: dict[str, Any] | None = None,
    eval_dir: Path | None = None,
) -> EvaluationResult:
    """REFUSES. No ablation has ever been run, and this reported one for years.

    Every number this produced was invented. The participants were `p_01` to `p_32`, made
    up. Their baseline scores were `random.Random(42).uniform(0.75, 0.95)`. The effect of
    removing each component was a hardcoded dict: explained_variance -0.07, persistence
    rule -0.12, temporal profiles -0.09, and so on. Nothing was ablated and nothing was
    measured, and `wha eval ablation` printed the results as
    "diff_persistence_rule: -0.1182" with a paired bootstrap interval around a constant.

    This is the identical defect that `run_policy_eval` had, which STATUS records as one of
    the original catastrophic findings: it "returned hardcoded accuracy constants no policy
    had produced". That one was fixed by making it run the real policies through the real
    belief model. This one was not touched, and it still reported a contribution for the
    Chronos forecast three days after the forecast was deleted from the codebase.

    Refusing is the honest state until somebody writes the real experiment. A suite that
    reports invented effect sizes is worse than no suite, because a reader cannot tell.

    The synthetic body is deleted rather than kept behind this raise. Dead code that exists,
    is referenced and is never reached is the defect shape this repository produces most,
    and leaving it as a monument to itself would be an odd way to mark the occasion. The
    diff has it if anyone wants to see it.
    """
    raise ConfigError(
        "No ablation has ever been run. This suite reported hardcoded effect sizes over "
        "32 invented participants with scores from random.Random(42), including a "
        "contribution for the Chronos forecast after it was deleted. It is disabled "
        "rather than left printing numbers nobody measured. The measurements that ARE "
        "real are the policy suite (uv run wha eval policy), which runs the real policies "
        "through the real belief model, and experiments/detection/cohort/ for detection accuracy."
    )
