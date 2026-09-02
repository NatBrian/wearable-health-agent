"""Unit tests for Today page inbox states, last night summary, and open episodes."""

from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

from wha.models import (
    AnswerOption,
    BaselineRung,
    ComponentStatus,
    Disposition,
    EpisodeOutcome,
    MeasurementRequest,
    PendingInteraction,
    Probe,
    Question,
    SystemStatus,
)
from wha.ui.today import (
    render_inbox,
)


def test_today_nothing_pending() -> None:
    """The most-seen screen: nothing pending displays reassuring message with quiet streak."""
    status = SystemStatus(
        components=[
            ComponentStatus(
                component="bridge",
                ok=True,
                detail="Bridge operational",
                severity="ok",
                checked_at_utc=datetime.now(UTC),
            )
        ],
        last_ingest_utc=datetime.now(UTC),
        last_nightly_utc=datetime.now(UTC),
        usable_nights=28,
        rung=BaselineRung.MATURE,
        errors_24h=0,
        quiet_nights_streak=14,
    )

    with patch("streamlit.success") as mock_success:
        render_inbox(subject_id="sub_test", pending=None, status=status)
        assert mock_success.called
        msg = mock_success.call_args[0][0]
        # Asserts the meaning rather than the exact prose: the person is told nothing is
        # required of them, and the quiet streak is shown so the silence is evidently
        # deliberate rather than the system having stopped working.
        assert "Nothing needs you" in msg
        assert "14 quiet nights" in msg


def test_today_pending_question() -> None:
    """Pending question renders probe options, and submitting calls submit_answer."""
    probe = Probe(
        probe_id="probe_symptoms",
        target_cause="infection",
        answer_space=[
            AnswerOption(option_id="fever", label="Fever or chills"),
            AnswerOption(option_id="none", label="No symptoms"),
        ],
        evsi=0.45,
        interruption_cost=0.30,
        fallback_text="Do you have fever?",
    )
    question = Question(
        probe=probe,
        text="Have you noticed any fever or chills today?",
        text_source="llm",
        options=probe.answer_space,
        allows_free_text=True,
    )
    pending = PendingInteraction(
        kind="question",
        episode_id="ep_001",
        question=question,
    )

    with (
        patch("streamlit.info") as mock_info,
        patch("streamlit.button", side_effect=[True, False, False]),
        patch("streamlit.columns", return_value=[MagicMock(), MagicMock(), MagicMock()]),
        patch("streamlit.rerun"),
        patch("wha.ui.today.submit_answer") as mock_submit,
    ):
        render_inbox(subject_id="sub_test", pending=pending)
        assert mock_info.called
        assert "Have you noticed any fever" in mock_info.call_args[0][0]
        assert mock_submit.called
        call_args = mock_submit.call_args
        assert call_args[0][0] == "ep_001"
        ans = call_args[0][1]
        assert ans.option_id == "fever"
        assert ans.declined is False


def test_today_pending_measurement() -> None:
    """Pending measurement renders instruction, and clicking Done calls submit_measurement_done."""
    m_req = MeasurementRequest(
        measurement_id="meas_456",
        kind="spot_resting_hr",
        instruction="Please sit quietly for 2 minutes and log resting heart rate.",
        expires_at_utc=datetime.now(UTC),
    )
    pending = PendingInteraction(
        kind="measurement",
        episode_id="ep_001",
        measurement=m_req,
    )

    with (
        patch("streamlit.warning") as mock_warning,
        patch("streamlit.button", side_effect=[True, False]),
        patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]),
        patch("streamlit.rerun"),
        patch("wha.ui.today.submit_measurement_done") as mock_submit,
    ):
        render_inbox(subject_id="sub_test", pending=pending)
        assert mock_warning.called
        assert "sit quietly" in mock_warning.call_args[0][0]
        assert mock_submit.called
        assert mock_submit.call_args[0][0] == "meas_456"


def test_today_pending_review() -> None:
    """Pending review renders draft outcome, and clicking Approve calls submit_human_decision."""
    draft = EpisodeOutcome(
        episode_id="ep_001",
        subject_id="sub_test",
        opened_on=date(2026, 9, 1),
        closed_on=date(2026, 9, 1),
        disposition=Disposition.LIKELY_ILLNESS,
        confidence="high",
        observation="Elevated RHR observed across 2 consecutive nights with fever reported.",
        action="rest",
        escalation_criteria=["High fever persistent for > 3 days."],
        baseline_nights=28,
        baseline_rung=BaselineRung.MATURE,
        differential=[],
        evidence_used=[],
        ruled_out=[],
        citations=[],
        unsupported_claims=0,
        interruptions_used_this_week=1,
        depth_used_this_episode=1,
    )
    pending = PendingInteraction(
        kind="review",
        episode_id="ep_001",
        draft_outcome=draft,
    )

    with (
        patch("streamlit.write") as mock_write,
        patch("streamlit.button", side_effect=[True, False, False]),
        patch("streamlit.columns", return_value=[MagicMock(), MagicMock(), MagicMock()]),
        patch("streamlit.text_area", return_value="Elevated RHR observed."),
        patch("streamlit.text_input", return_value=""),
        patch("streamlit.rerun"),
        patch("wha.ui.today.submit_human_decision") as mock_decision,
    ):
        render_inbox(subject_id="sub_test", pending=pending)
        # The draft must actually reach the screen, which is a stronger check than
        # asserting that a particular Streamlit call was made to display it.
        written = " ".join(str(c[0][0]) for c in mock_write.call_args_list if c[0])
        assert "Possibly coming down with something" in written
        assert "Elevated RHR observed" in written
        assert mock_decision.called
        call_args = mock_decision.call_args
        assert call_args.kwargs["episode_id"] == "ep_001"
        assert call_args.kwargs["decision"] == "approve"
