"""Unit tests for the adversarial prompt injection evaluation suite."""

from pathlib import Path

from wha.eval.adversarial import run_adversarial_eval
from wha.models import EvaluationResult


def test_adversarial_suite_reports_success_rate(tmp_path: Path) -> None:
    """Adversarial evaluation suite reports total cases, detection rate, and attack success rate."""
    result = run_adversarial_eval(eval_dir=tmp_path)

    assert isinstance(result, EvaluationResult)
    assert result.suite == "adversarial"
    assert "attack_success_rate" in result.metrics
    assert "detection_rate" in result.metrics
    assert "total_cases" in result.metrics
    assert result.metrics["total_cases"] >= 15
    assert 0.0 <= result.metrics["attack_success_rate"] <= 1.0


def test_control_run_included(tmp_path: Path) -> None:
    """Side-by-side clean control run is included and compared against poisoned attacks."""
    result = run_adversarial_eval(eval_dir=tmp_path)

    assert "side_by_side" in result.tables
    side_by_side = result.tables["side_by_side"]
    assert len(side_by_side) >= 15

    for entry in side_by_side:
        assert "clean_text" in entry
        assert "poisoned_text" in entry
        assert "clean_detected" in entry
        assert "poisoned_detected" in entry
        # Clean control text should not trigger injection false alarms
        assert entry["clean_detected"] is False


def test_unmatched_injection_case_present_and_reported(tmp_path: Path) -> None:
    """Adversarial suite includes an unmatched evasion case and discloses it in caveats."""
    result = run_adversarial_eval(eval_dir=tmp_path)

    assert result.metrics["missed_cases_count"] >= 1
    assert result.metrics["detection_rate"] < 1.0
    assert len(result.caveats) >= 1
    assert any("unmatched evasion case" in c for c in result.caveats)
