"""Evaluation service for executing evaluation suites."""

from pathlib import Path

from wha.errors import ConfigError
from wha.eval.detection import run_detection_eval
from wha.models import EvaluationResult


def run_evaluation_suite(suite: str, eval_dir: Path | None = None) -> EvaluationResult:
    """Run an evaluation suite and persist results."""
    suite_clean = suite.lower().strip()
    if suite_clean == "detection":
        return run_detection_eval(eval_dir=eval_dir)
    elif suite_clean in {"baseline-age", "baseline_age"}:
        from wha.eval.baseline_age import run_baseline_age_eval

        return run_baseline_age_eval(eval_dir=eval_dir)
    elif suite_clean == "policy":
        from wha.eval.policy_oracle import run_policy_eval

        return run_policy_eval(eval_dir=eval_dir)
    elif suite_clean == "ablation":
        from wha.eval.ablation import run_ablation_eval

        return run_ablation_eval(eval_dir=eval_dir)

    raise ConfigError(
        f"Unknown evaluation suite '{suite}'. Valid suites: detection, baseline-age, policy, ablation"
    )
