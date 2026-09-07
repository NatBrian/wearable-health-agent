"""Tests for the markdown evaluation report."""

from datetime import UTC, datetime
from pathlib import Path

from wha.eval.report import render_markdown, write_report
from wha.models import EvaluationResult


def test_the_detection_section_reports_the_measurement() -> None:
    """It said "Not evaluated" for the life of the project, and the data was never missing.

    CORRECTED 5 September 2026. The old text blamed absent cohorts and an unauthored
    `cohort_labels.yaml`. Both were a public download away: the Mishra 2020 wearable
    release is 378 MB with no registration, and the symptom onset dates are in that same
    paper's supplementary spreadsheet, shifted the same way as the wearable files. It took
    under an hour.

    The section is now rendered from `experiments/detection/detection-results.json`, which
    `experiments/detection/cohort/report.py` writes, so there is one implementation of the scoring and the
    378 MB cohort does not have to be present to render the report.
    """
    markdown = render_markdown({})

    assert "Not evaluated" not in markdown
    assert "cohort_labels.yaml" not in markdown

    assert "## Detection" in markdown
    assert "Published NightSignal" in markdown
    # The chance floor is not optional. A sensitivity quoted without it is not a finding.
    assert "Random, same rate" in markdown
    assert "What these numbers do not show" in markdown


def test_the_detection_section_says_how_to_produce_it_when_it_is_missing(
    tmp_path: Path, monkeypatch
) -> None:
    """A checkout without the summary must say how to get it, not claim nothing is known."""
    import wha.eval.report as report_module

    monkeypatch.setattr(report_module, "DETECTION_RESULTS", tmp_path / "absent.json")
    markdown = render_markdown({})

    assert "Not measured in this checkout" in markdown
    assert "experiments/detection/cohort/fetch.py" in markdown


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
