"""Unit tests for Episode Panel: Summary and Trace tabs, belief chart, and honesty metrics."""

from datetime import date
from unittest.mock import MagicMock, patch

from wha.models import (
    BaselineRung,
    BeliefState,
    CauseId,
    DifferentialItem,
    Disposition,
    EpisodeDetail,
    EpisodeOutcome,
    EpisodeState,
    EpisodeSummary,
    PipelineStage,
    StageStatus,
)
from wha.ui.components.belief_chart import build_belief_evolution_data, render_belief_evolution
from wha.ui.components.episode_panel import render_summary_tab
from wha.ui.components.pipeline_trace import render_pipeline_trace


def test_episode_trace_shows_skipped() -> None:
    """Skipped stages in episode trace are explicitly rendered with reasons rather than hidden."""
    stages = [
        PipelineStage(
            name="preload",
            status=StageStatus.RAN,
            reason="Loaded nightly features",
            duration_ms=5,
        ),
        PipelineStage(
            name="investigate",
            status=StageStatus.RAN,
            reason="Queried calendar and workout history",
            duration_ms=15,
        ),
        PipelineStage(
            name="notify",
            status=StageStatus.SKIPPED,
            reason="Policy returned OBSERVE, no probe cleared interruption cost",
            duration_ms=0,
        ),
    ]
    detail = EpisodeDetail(
        summary=EpisodeSummary(
            episode_id="ep_001",
            opened_on=date(2026, 8, 1),
            closed_on=date(2026, 8, 2),
            state=EpisodeState.CLOSED,
            disposition=Disposition.LIKELY_BENIGN,
            night_span=(date(2026, 8, 1), date(2026, 8, 2)),
        ),
        stages=stages,
        belief_history=[],
    )

    with patch("streamlit.markdown") as mock_markdown, patch("streamlit.write") as mock_write:
        render_pipeline_trace(detail)
        # Verify markdown calls render all stages including SKIPPED
        rendered_headers = [call[0][0] for call in mock_markdown.call_args_list]
        assert any("notify" in h and "SKIPPED" in h for h in rendered_headers)
        # Verify skipped reason is written
        written_reasons = [call[0][0] for call in mock_write.call_args_list]
        assert any("Policy returned OBSERVE" in r for r in written_reasons)


def test_episode_trace_expands_tool_calls() -> None:
    """Investigate stage details expand to show individual T1 tool calls with arguments and freshness."""
    tool_calls = [
        {
            "tool_name": "query_calendar",
            "source_ref": "google_cal_01",
            "freshness": "current",
            "arguments": {"days_back": 3},
            "result": "No travel recorded",
        },
        {
            "tool_name": "retrieve_clinical_evidence",
            "source_ref": "who_knowledge_base",
            "freshness": "current",
            "arguments": {"query": "fever RHR shift"},
            "result": "Infection causes +4.5 bpm RHR elevation",
        },
    ]
    stages = [
        PipelineStage(
            name="investigate",
            status=StageStatus.RAN,
            reason="Queried context tools",
            duration_ms=25,
            detail_json={"tool_calls": tool_calls},
        )
    ]
    detail = EpisodeDetail(
        summary=EpisodeSummary(
            episode_id="ep_002",
            opened_on=date(2026, 8, 1),
            closed_on=date(2026, 8, 2),
            state=EpisodeState.CLOSED,
            disposition=Disposition.LIKELY_ILLNESS,
            night_span=(date(2026, 8, 1), date(2026, 8, 2)),
        ),
        stages=stages,
        belief_history=[],
    )

    with (
        patch("streamlit.markdown") as mock_markdown,
        patch("streamlit.write"),
        patch("streamlit.expander", return_value=MagicMock()),
        patch("streamlit.json"),
    ):
        render_pipeline_trace(detail)
        markdown_calls = [call[0][0] for call in mock_markdown.call_args_list]
        assert any("query_calendar" in m for m in markdown_calls)
        assert any("retrieve_clinical_evidence" in m for m in markdown_calls)


def test_belief_chart_labels_marginals_not_partition() -> None:
    """Belief chart labels marginal probabilities rather than a partition summing to 1."""
    marginals = {
        CauseId.INFECTION: 0.85,
        CauseId.ALCOHOL: 0.10,
        CauseId.EXERTION: 0.05,
        CauseId.SLEEP_RESTRICTION: 0.02,
        CauseId.STRESS: 0.01,
        CauseId.LUTEAL: 0.0,
        CauseId.VACCINATION: 0.0,
        CauseId.TRAVEL: 0.0,
        CauseId.MEDICATION: 0.0,
        CauseId.RECOVERY_TAIL: 0.0,
        CauseId.SENSOR_ARTIFACT: 0.0,
        CauseId.UNEXPLAINED: 0.05,
    }
    state = BeliefState(marginals=marginals, p_illness=0.85)
    belief_history = [(1, "initial", state)]

    df = build_belief_evolution_data(belief_history)
    assert "P(infection)" in df.columns
    assert "p_illness" in df.columns
    assert "decision_threshold" in df.columns

    with patch("streamlit.caption") as mock_caption, patch("streamlit.line_chart"):
        render_belief_evolution(belief_history)
        assert mock_caption.called
        caption_text = mock_caption.call_args[0][0]
        # Assert caption explains marginals do not sum to 1.0
        assert "does not sum to 1.0" in caption_text or "independent" in caption_text.lower()


def test_unsupported_claims_displayed() -> None:
    """Summary tab displays unsupported claims metric explicitly."""
    outcome = EpisodeOutcome(
        episode_id="ep_003",
        subject_id="sub_test",
        opened_on=date(2026, 8, 1),
        closed_on=date(2026, 8, 3),
        disposition=Disposition.LIKELY_ILLNESS,
        confidence="high",
        observation="Consistent nocturnal RHR deviation of +4.2 bpm.",
        action="rest",
        escalation_criteria=["Fever exceeding 38.5C"],
        baseline_nights=28,
        baseline_rung=BaselineRung.MATURE,
        differential=[
            DifferentialItem(
                cause=CauseId.INFECTION,
                probability=0.88,
                supporting=["Fever reported"],
                contradicting=[],
            )
        ],
        evidence_used=["Clinical guideline v1"],
        ruled_out=[],
        citations=[],
        unsupported_claims=0,
        interruptions_used_this_week=1,
        depth_used_this_episode=1,
    )
    detail = EpisodeDetail(
        summary=EpisodeSummary(
            episode_id="ep_003",
            opened_on=date(2026, 8, 1),
            closed_on=date(2026, 8, 3),
            state=EpisodeState.CLOSED,
            disposition=Disposition.LIKELY_ILLNESS,
            night_span=(date(2026, 8, 1), date(2026, 8, 3)),
        ),
        outcome=outcome,
        stages=[],
        belief_history=[],
    )

    with (
        patch("streamlit.metric") as mock_metric,
        patch(
            "streamlit.columns", return_value=[MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        ),
        patch("streamlit.info"),
        patch("streamlit.bar_chart"),
        patch("streamlit.dataframe"),
    ):
        render_summary_tab(detail)
        assert mock_metric.called
        labels = [call[0][0] for call in mock_metric.call_args_list]
        values = [call[0][1] for call in mock_metric.call_args_list]
        assert "Unsupported Claims" in labels
        idx = labels.index("Unsupported Claims")
        assert values[idx] == 0
