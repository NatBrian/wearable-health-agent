"""Unit tests for live LLM providers (ollama_native, openai_compatible) with mocked transport."""

from unittest.mock import MagicMock, patch

import httpx
import pytest
from pydantic import BaseModel

from wha.errors import LLMUnavailable, ValidationFailed
from wha.llm import (
    OllamaNativeClient,
    OpenAICompatClient,
    Prompt,
    strip_markdown_fences,
)


class ExpectedOutput(BaseModel):
    decision: str
    confidence: float


def test_max_tokens_floor_enforced() -> None:
    """Requesting max_tokens below LLM_MAX_TOKENS_FLOOR raises LLMUnavailable before sending."""
    client = OpenAICompatClient()
    prompt = Prompt(prompt_id="test", prompt_version="1", user="hi")

    with pytest.raises(LLMUnavailable) as exc_info:
        client.complete(prompt, ExpectedOutput, max_tokens=50)

    assert "below LLM_MAX_TOKENS_FLOOR" in str(exc_info.value)


def test_empty_content_is_unavailable() -> None:
    """A 200 HTTP response with empty or whitespace-only content raises LLMUnavailable."""
    client = OpenAICompatClient()
    prompt = Prompt(prompt_id="test", prompt_version="1", user="hi")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "   "}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 0},
    }

    with (
        patch("httpx.Client.post", return_value=mock_resp),
        pytest.raises(LLMUnavailable) as exc_info,
    ):
        client.complete(prompt, ExpectedOutput, max_tokens=250)

    assert "empty or whitespace" in str(exc_info.value)


def test_finish_reason_length_is_unavailable() -> None:
    """Response with finish_reason='length' raises LLMUnavailable."""
    client = OpenAICompatClient()
    prompt = Prompt(prompt_id="test", prompt_version="1", user="hi")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": '{"decision": "conclude"'}, "finish_reason": "length"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 250},
    }

    with (
        patch("httpx.Client.post", return_value=mock_resp),
        pytest.raises(LLMUnavailable) as exc_info,
    ):
        client.complete(prompt, ExpectedOutput, max_tokens=250)

    assert "finish_reason='length'" in str(exc_info.value)


def test_openrouter_deepseek_conversation_disables_optional_reasoning() -> None:
    """A chat turn reserves its output budget for the structured answer, not hidden reasoning."""
    client = OpenAICompatClient(
        base_url="https://openrouter.ai/api/v1",
        api_key="test-key",
        model="deepseek/deepseek-v4-flash-0731",
    )
    prompt = Prompt(prompt_id="converse", prompt_version="4", user="Reply as JSON.")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"decision": "answer", "confidence": 0.9}'
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 12},
    }

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        client.complete(prompt, ExpectedOutput, max_tokens=4096)

    payload = mock_post.call_args.kwargs["json"]
    assert payload["max_tokens"] == 4096
    assert payload["reasoning_effort"] == "none"


def test_openrouter_deepseek_non_conversation_keeps_provider_default_reasoning() -> None:
    """Other DeepSeek operations retain their configured provider reasoning behavior."""
    client = OpenAICompatClient(
        base_url="https://openrouter.ai/api/v1",
        api_key="test-key",
        model="deepseek/deepseek-v4-flash-0731",
    )
    prompt = Prompt(prompt_id="extract_facts", user="Extract facts as JSON.")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"decision": "answer", "confidence": 0.9}'
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 12},
    }

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        client.complete(prompt, ExpectedOutput, max_tokens=1024)

    assert "reasoning_effort" not in mock_post.call_args.kwargs["json"]


def test_one_repair_round_then_raises() -> None:
    """Pydantic validation failure triggers exactly one repair call, then raises ValidationFailed."""
    client = OpenAICompatClient()
    prompt = Prompt(prompt_id="test", prompt_version="1", user="hi")

    # Both initial and repair response return invalid schema
    invalid_resp = MagicMock()
    invalid_resp.status_code = 200
    invalid_resp.json.return_value = {
        "choices": [{"message": {"content": '{"invalid": "data"}'}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }

    with (
        patch("httpx.Client.post", return_value=invalid_resp) as mock_post,
        pytest.raises(ValidationFailed) as exc_info,
    ):
        client.complete(prompt, ExpectedOutput, max_tokens=250)

    assert mock_post.call_count == 2
    assert "after 1 repair attempt" in str(exc_info.value)


def test_markdown_fence_stripped() -> None:
    """Markdown ```json ... ``` fences are cleanly stripped before validation."""
    raw = '```json\n{"decision": "conclude", "confidence": 0.95}\n```'
    stripped = strip_markdown_fences(raw)
    parsed = ExpectedOutput.model_validate_json(stripped)
    assert parsed.decision == "conclude"
    assert parsed.confidence == 0.95


def test_never_trusts_provider_schema() -> None:
    """Client always validates raw content against Pydantic schema regardless of provider assertions."""
    client = OpenAICompatClient()
    prompt = Prompt(prompt_id="test", prompt_version="1", user="hi")

    # Missing required float field 'confidence'
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": '{"decision": "ask"}'}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }

    with patch("httpx.Client.post", return_value=mock_resp), pytest.raises(ValidationFailed):
        client.complete(prompt, ExpectedOutput, max_tokens=250)


def test_think_false_only_on_native_path() -> None:
    """Ollama native client passes think=False in payload options; OpenAI compat does not."""
    ollama_client = OllamaNativeClient()
    prompt = Prompt(prompt_id="test", prompt_version="1", user="hi")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "message": {"content": '{"decision": "ask", "confidence": 0.8}'},
        "prompt_eval_count": 10,
        "eval_count": 10,
    }

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        ollama_client.complete(prompt, ExpectedOutput, max_tokens=250)
        call_json = mock_post.call_args.kwargs["json"]
        assert call_json.get("think") is False


def test_unavailable_does_not_fabricate() -> None:
    """When endpoint is unreachable, client raises LLMUnavailable and never returns fabricated fallback."""
    client = OpenAICompatClient()
    prompt = Prompt(prompt_id="test", prompt_version="1", user="hi")

    with (
        patch("httpx.Client.post", side_effect=httpx.ConnectError("Connection refused")),
        pytest.raises(LLMUnavailable),
    ):
        client.complete(prompt, ExpectedOutput, max_tokens=250)
