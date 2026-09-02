"""Tests for the markdown evaluation report."""

from datetime import UTC, datetime
from pathlib import Path

from wha.eval.report import render_markdown, write_report
from wha.models import EvaluationResult


def test_report_states_when_a_suite_was_not_evaluated() -> None:
    """A suite with no results must say so rather than being silently omitted.

    The detection suite needs cohort data that is not present. Reporting nothing at all
    reads as though there were nothing to report, which is how a missing measurement
    becomes an unnoticed gap.
    """
    markdown = render_markdown({})

    assert "Not evaluated" in markdown
    assert "cohort_labels.yaml" in markdown


def test_report_contains_measured_policy_numbers(tmp_path: Path) -> None:
    """The report is generated from a real run, and names every comparator."""
    written = write_report(output_path=tmp_path / "EVALUATION.md", eval_dir=tmp_path)
    markdown = written.read_text(encoding="utf-8")

    assert "Never ask" in markdown
    assert "Always ask" in markdown
    assert "EVSI (this system)" in markdown
    # The caveats matter more than the figures and must survive into the report.
    assert "not a clinical cohort" in markdown


def test_report_renders_caveats_from_the_result() -> None:
    """Caveats carried by an EvaluationResult reach the reader."""
    result = EvaluationResult(
        suite="policy",
        generated_at_utc=datetime.now(UTC),
        metrics={"evsi_mean_accuracy": 0.5, "evsi_mean_interruptions": 1.0},
        tables={},
        figures=[],
        sample_size=4,
        caveats=["A caveat that must be visible."],
    )

    markdown = render_markdown({"policy": result})

    assert "A caveat that must be visible." in markdown
