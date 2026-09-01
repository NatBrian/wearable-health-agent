"""Unit tests for Evaluation view, caveats rendering, mandatory baselines, and negative Chronos findings."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from wha.models import EvaluationResult
from wha.ui.evaluation import (
    render_baseline_age_panel,
    render_caveats_and_sample_size,
    render_detection_panel,
    render_evaluation_page,
)


def test_evaluation_renders_caveats() -> None:
    """Evaluation panels print sample size and explicitly render all caveats."""
    res = EvaluationResult(
        suite="detection",
        generated_at_utc=datetime.now(UTC),
        metrics={"recall": 0.85},
        tables={},
        figures=[],
        sample_size=42,
        caveats=["Sample underpowered for subgroup analysis", "Self-reported illness labels"],
    )

    with (
        patch("streamlit.caption") as mock_caption,
        patch("streamlit.warning") as mock_warning,
    ):
        render_caveats_and_sample_size(res)
        assert mock_caption.called
        assert "42" in mock_caption.call_args[0][0]
        assert mock_warning.call_count == 2
        warn_texts = [call[0][0] for call in mock_warning.call_args_list]
        assert any("underpowered" in w for w in warn_texts)
        assert any("Self-reported" in w for w in warn_texts)


def test_evaluation_shows_both_mandatory_baselines() -> None:
    """Detection panel explicitly documents and displays both mandatory baseline comparators."""
    res = EvaluationResult(
        suite="detection",
        generated_at_utc=datetime.now(UTC),
        metrics={"recall": 0.88, "far_per_week": 0.12},
        tables={
            "baselines": [
                {"name": "random", "recall": 0.20},
                {"name": "fixed_threshold", "recall": 0.65},
            ]
        },
        figures=[],
        sample_size=100,
        caveats=[],
    )

    with (
        patch("wha.ui.evaluation.get_evaluation_results", return_value=res),
        patch("streamlit.caption"),
        patch(
            "streamlit.columns", return_value=[MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        ),
        patch("streamlit.metric"),
        patch("streamlit.markdown") as mock_markdown,
        patch("streamlit.dataframe") as mock_df,
    ):
        render_detection_panel()
        md_calls = [call[0][0] for call in mock_markdown.call_args_list]
        # Both mandatory baselines mentioned
        assert any("Random Detector" in m for m in md_calls)
        assert any("Fixed-Threshold Rule" in m for m in md_calls)
        assert mock_df.called


def test_evaluation_never_computes_on_load() -> None:
    """Evaluation page strictly retrieves precomputed results without triggering run_evaluation_suite."""
    with (
        patch("wha.service.evaluation.run_evaluation_suite") as mock_run,
        patch("wha.ui.evaluation.get_evaluation_results") as mock_get,
        patch("streamlit.tabs", return_value=[MagicMock() for _ in range(5)]),
        patch("streamlit.title"),
        patch("streamlit.caption"),
    ):
        mock_get.return_value = EvaluationResult(
            suite="dummy",
            generated_at_utc=datetime.now(UTC),
            sample_size=10,
            caveats=[],
        )
        render_evaluation_page()
        assert not mock_run.called
        assert mock_get.called


def test_negative_chronos_result_is_stated_plainly() -> None:
    """Baseline maturity panel plainly states the negative Chronos empirical finding."""
    res = EvaluationResult(
        suite="baseline_age",
        generated_at_utc=datetime.now(UTC),
        metrics={},
        tables={},
        figures=[],
        sample_size=50,
        caveats=[],
    )

    with (
        patch("wha.ui.evaluation.get_evaluation_results", return_value=res),
        patch("streamlit.caption"),
        patch("streamlit.info") as mock_info,
    ):
        render_baseline_age_panel()
        assert mock_info.called
        info_text = mock_info.call_args[0][0]
        assert "did not extend usable detection" in info_text or "Chronos" in info_text
