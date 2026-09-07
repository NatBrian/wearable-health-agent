"""Unit tests for Notifier protocol, Telegram transport, and callback data packing."""

from unittest.mock import MagicMock

import httpx

from wha.agent.tools.impl import create_default_tool_registry
from wha.constants import TELEGRAM_CALLBACK_MAX_BYTES
from wha.models import AnswerOption
from wha.notify import (
    MessageKind,
    TelegramNotifier,
    format_callback_data,
    format_callback_token,
)
from wha.policy.probes import load_probes


def test_callback_data_within_limit() -> None:
    """Every probe and every option generates a callback_data under TELEGRAM_CALLBACK_MAX_BYTES (64)."""
    probes = load_probes()
    interaction_id = "int_20260901_very_long_test_interaction_id_12345"

    for probe in probes:
        for opt in probe.answer_space:
            cb = format_callback_data(interaction_id, opt.option_id)
            cb_bytes = len(cb.encode("utf-8"))
            assert cb_bytes <= TELEGRAM_CALLBACK_MAX_BYTES
            assert cb.startswith("a:")
            # Verifies structure: a:<short_id>:<option_id>
            parts = cb.split(":")
            assert len(parts) == 3
            assert parts[1] == format_callback_token(interaction_id)
            assert parts[2] == opt.option_id


def test_callback_token_distinguishes_interactions_in_one_episode() -> None:
    """Two questions in the same episode must produce different callback tokens.

    Interaction ids are f"int_{episode_id}_{probe_id}", so for any episode id starting
    "ep_2" the first eight characters are the constant "int_ep_2". Truncating to a prefix
    made every question in an episode share a token, and a button answer could be
    recorded against a different probe entirely.
    """
    first = format_callback_token("int_ep_20260901abcd_probe_symptoms")
    second = format_callback_token("int_ep_20260901abcd_probe_alcohol")

    assert first != second


def test_outbound_rejects_url() -> None:
    """When question text contains an unauthorized URL, outbound validation falls back to probe.fallback_text."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_client.post.return_value = mock_resp

    notifier = TelegramNotifier(
        token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        chat_id="12345678",
        client=mock_client,
    )

    options = [
        AnswerOption(option_id="none", label="None"),
        AnswerOption(option_id="1_2", label="1-2 drinks"),
        AnswerOption(option_id="3plus", label="3+ drinks"),
    ]

    # Attempt to send question containing a URL
    malicious_text = "Did you drink alcohol? Check out https://suspicious-phish.com"
    success = notifier.send(
        recipient_id="sub_001",
        kind=MessageKind.QUESTION,
        text=malicious_text,
        interaction_id="int_001",
        probe_id="probe_alcohol",
        options=options,
    )

    assert success is True
    assert mock_client.post.called
    call_payload = mock_client.post.call_args.kwargs.get("json", {})
    # The URL was rejected and replaced by the probe's clean fallback text!
    assert "https://suspicious-phish.com" not in call_payload.get("text", "")
    assert "alcohol" in call_payload.get("text", "").lower()


def test_send_failure_does_not_raise() -> None:
    """When HTTP transport fails with network or server error, send returns False without raising into caller."""
    mock_client = MagicMock()
    mock_client.post.side_effect = httpx.ConnectError("Network unreachable")

    notifier = TelegramNotifier(
        token="fake_token",
        chat_id="12345678",
        client=mock_client,
    )

    # Must return False, not raise
    success = notifier.send(
        recipient_id="sub_001",
        kind=MessageKind.SYSTEM,
        text="System alert.",
    )
    assert success is False


def test_notifier_is_not_in_tool_registry() -> None:
    """The notifier is a system service, not an LLM tool, and must never appear in the tool registry."""
    registry = create_default_tool_registry()
    registered_tools = registry.list_tools()

    for tool in registered_tools:
        assert "notify" not in tool.lower()
        assert "telegram" not in tool.lower()
        assert "send_message" not in tool.lower()
