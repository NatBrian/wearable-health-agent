"""OpenAI-compatible LLM client (/v1/chat/completions)."""

import time
from typing import TypeVar
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ValidationError

from wha.config import get_settings
from wha.constants import (
    LLM_MAX_TOKENS_FLOOR,
    LLM_REPAIR_ATTEMPTS,
    LLM_TIMEOUT_SECONDS,
)
from wha.errors import LLMUnavailable, ValidationFailed
from wha.llm.client import LLMUsage, Prompt
from wha.llm.repair import build_repair_prompt, strip_markdown_fences

T = TypeVar("T", bound=BaseModel)


class OpenAICompatClient:
    """OpenAI-compatible provider client."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = LLM_TIMEOUT_SECONDS,
    ) -> None:
        settings = get_settings()
        self.base_url = base_url or settings.llm_base_url or "https://api.openai.com/v1"
        self.api_key = api_key or (
            settings.llm_api_key.get_secret_value() if settings.llm_api_key else ""
        )
        self.model = model or settings.llm_model
        self.timeout = timeout
        self.last_model_id = self.model
        self.last_origin = "RECORDED"

    def _call_api(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        reasoning_effort: str | None = None,
    ) -> tuple[str, LLMUsage, str | None]:
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        if reasoning_effort is not None:
            payload["reasoning_effort"] = reasoning_effort

        t0 = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            raise LLMUnavailable(f"OpenAI-compatible request failed: {e}") from e

        latency_ms = int((time.perf_counter() - t0) * 1000)

        choices = data.get("choices", [])
        if not choices:
            raise LLMUnavailable("OpenAI-compatible returned empty choices array.")

        choice = choices[0]
        finish_reason = choice.get("finish_reason")
        if finish_reason == "length":
            raise LLMUnavailable(
                "Model returned finish_reason='length' (exceeded token budget before completing response)."
            )

        msg = choice.get("message", {})
        content = msg.get("content", "")
        if not content or not content.strip():
            raise LLMUnavailable("Model returned empty or whitespace-only response.")

        usage_data = data.get("usage", {})
        usage = LLMUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            latency_ms=latency_ms,
        )

        return content, usage, finish_reason

    def complete(
        self,
        prompt: Prompt,
        schema: type[T],
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> tuple[T, LLMUsage]:
        """Send completion request with schema validation and one repair round."""
        if max_tokens < LLM_MAX_TOKENS_FLOOR:
            raise LLMUnavailable(
                f"Requested max_tokens={max_tokens} is below LLM_MAX_TOKENS_FLOOR={LLM_MAX_TOKENS_FLOOR}."
            )

        messages = [
            {"role": "system", "content": prompt.system},
            {"role": "user", "content": prompt.user},
        ]

        use_low_effort = (
            prompt.prompt_id == "converse"
            and self.model.startswith("deepseek/")
            and urlsplit(self.base_url).hostname == "openrouter.ai"
        )
        reasoning_effort = "none" if use_low_effort else None

        raw_content, usage, _ = self._call_api(
            messages, temperature, max_tokens, reasoning_effort=reasoning_effort
        )
        cleaned = strip_markdown_fences(raw_content)

        try:
            parsed = schema.model_validate_json(cleaned)
            return parsed, usage
        except ValidationError as first_err:
            # Exactly one repair round
            repair_user = build_repair_prompt(raw_content, first_err, schema)
            repair_messages = messages + [
                {"role": "assistant", "content": raw_content},
                {"role": "user", "content": repair_user},
            ]

            repaired_content, repair_usage, _ = self._call_api(
                repair_messages,
                temperature,
                max_tokens,
                reasoning_effort=reasoning_effort,
            )
            repaired_cleaned = strip_markdown_fences(repaired_content)

            total_usage = LLMUsage(
                prompt_tokens=usage.prompt_tokens + repair_usage.prompt_tokens,
                completion_tokens=usage.completion_tokens + repair_usage.completion_tokens,
                latency_ms=usage.latency_ms + repair_usage.latency_ms,
            )

            try:
                parsed = schema.model_validate_json(repaired_cleaned)
                return parsed, total_usage
            except ValidationError as second_err:
                raise ValidationFailed(
                    f"LLM output failed Pydantic validation after {LLM_REPAIR_ATTEMPTS} repair attempt: {second_err}"
                ) from second_err
