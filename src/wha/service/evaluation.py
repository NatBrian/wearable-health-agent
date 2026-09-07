"""Evaluation service for executing evaluation suites and retrieving cached evaluation reports."""

import json
import logging
from pathlib import Path

from wha.clock import now_utc
from wha.errors import ConfigError
from wha.eval.detection import run_detection_eval
from wha.models import EvaluationResult

logger = logging.getLogger(__name__)


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
    elif suite_clean == "adversarial":
        from wha.eval.adversarial import run_adversarial_eval

        return run_adversarial_eval(eval_dir=eval_dir)

    raise ConfigError(
        f"Unknown evaluation suite '{suite}'. Valid suites: detection, baseline-age, policy, ablation, adversarial"
    )


def get_evaluation_results(suite: str, eval_dir: Path | None = None) -> EvaluationResult:
    """Retrieve precomputed evaluation results for a suite.

    If missing, returns an empty EvaluationResult with an explanatory caveat naming the command.
    """
    target_dir = eval_dir or Path("data/eval")
    suite_normalized = suite.lower().replace("-", "_")
    target_file = target_dir / f"{suite_normalized}.json"

    if target_file.exists():
        try:
            data = json.loads(target_file.read_text(encoding="utf-8"))
            return EvaluationResult.model_validate(data)
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            logger.warning("Failed to load evaluation file %s: %s", target_file, exc)

    return EvaluationResult(
        suite=suite,
        generated_at_utc=now_utc(),
        metrics={},
        tables={},
        figures=[],
        sample_size=0,
        caveats=[
            f"Evaluation results missing for suite '{suite}'. Run 'uv run wha eval run {suite}' to generate."
        ],
    )


def write_evaluation_report(
    output_path: Path | None = None,
    eval_dir: Path | None = None,
) -> Path:
    """Run the offline evaluation suites and write the markdown report."""
    from wha.eval.report import write_report

    return write_report(output_path=output_path, eval_dir=eval_dir)
