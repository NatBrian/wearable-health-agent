"""Unit tests for Settings view, secret non-echoing, policy audit logging, and delete-all confirmation."""

from unittest.mock import MagicMock, patch

from wha.models import SettingsPatch
from wha.ui.settings import (
    render_connection_section,
    render_data_privacy_section,
    render_llm_section,
    render_policy_section,
)


def test_settings_secrets_not_echoed() -> None:
    """Secret fields render as type='password' with empty initial value and are never echoed back."""
    with (
        patch("streamlit.text_input") as mock_input,
        patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]),
        patch("streamlit.button"),
        patch("streamlit.expander", return_value=MagicMock()),
    ):
        render_connection_section("sub_01")
        # Asserts the property rather than a label: every masked field on this section is
        # a password input that starts empty, so renaming a field cannot quietly turn a
        # secret into a plain text box that echoes it back.
        secret_calls = [
            call for call in mock_input.call_args_list if call[1].get("type") == "password"
        ]
        assert len(secret_calls) == 1
        for call in secret_calls:
            assert call[1].get("value") == ""

    with (
        patch("streamlit.text_input") as mock_input,
        patch("streamlit.selectbox"),
        patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]),
        patch("streamlit.button"),
    ):
        render_llm_section("sub_01")
        secret_calls = [
            call for call in mock_input.call_args_list if call[1].get("type") == "password"
        ]
        assert len(secret_calls) == 1
        for call in secret_calls:
            assert call[1].get("value") == ""


def test_policy_change_logged() -> None:
    """Saving policy adjustments calls update_settings which writes an audit event."""
    with (
        patch("streamlit.number_input", side_effect=[4, 5, 0.35]),
        patch("streamlit.columns", return_value=[MagicMock(), MagicMock(), MagicMock()]),
        patch("streamlit.button", return_value=True),
        patch("streamlit.session_state", {}),
        patch("wha.ui.settings.update_settings") as mock_update,
        patch("streamlit.success"),
    ):
        render_policy_section("sub_01")
        assert mock_update.called
        patch_arg = mock_update.call_args[0][0]
        assert isinstance(patch_arg, SettingsPatch)
        assert patch_arg.interruption_budget_per_week == 4
        assert patch_arg.depth_budget_per_episode == 5
        assert patch_arg.policy_cost_weight == 0.35


def test_delete_all_requires_typed_confirmation() -> None:
    """Delete all action strictly requires typing 'DELETE' and rejects anything else."""
    # 1. Incorrect text -> does not call delete
    with (
        patch("streamlit.text_input", return_value="delete"),  # lowercase, invalid
        patch("streamlit.button", return_value=True),
        patch("wha.ui.settings.delete_all_subject_data") as mock_delete,
        patch("streamlit.warning") as mock_warn,
    ):
        render_data_privacy_section("sub_test")
        assert not mock_delete.called
        assert mock_warn.called
        # The message must make clear nothing happened, without matching exact prose.
        assert "nothing was deleted" in mock_warn.call_args[0][0].lower()

    # 2. Correct text 'DELETE' -> calls delete
    with (
        patch("streamlit.text_input", return_value="DELETE"),
        patch("streamlit.button", return_value=True),
        patch("wha.ui.settings.delete_all_subject_data") as mock_delete,
        patch("streamlit.error") as mock_err,
    ):
        render_data_privacy_section("sub_test")
        assert mock_delete.called
        assert mock_delete.call_args[0][0] == "sub_test"
        assert mock_err.called
        assert "deleted" in mock_err.call_args[0][0].lower()
