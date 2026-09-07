"""Ollama native LLM client (/api/chat)."""

import time
from typing import TypeVar

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


class OllamaNativeClient:
    """Ollama native provider client using /api/chat with think=False support."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = LLM_TIMEOUT_SECONDS,
    ) -> None:
        settings = get_settings()
        self.base_url = base_url or settings.llm_base_url or "http://localhost:11434"
        self.model = model or settings.llm_model
        self.timeout = timeout
        self.last_model_id = self.model
        self.last_origin = "RECORDED"

    def _call_api(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, LLMUsage]:
        url = f"{self.base_url.rstrip('/')}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": "json",
            "think": False,  # Explicitly disabled on native path
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        t0 = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            raise LLMUnavailable(f"Ollama native request failed: {e}") from e

        latency_ms = int((time.perf_counter() - t0) * 1000)

        msg = data.get("message", {})
        content = msg.get("content", "")
        if not content or not content.strip():
            raise LLMUnavailable("Ollama returned empty or whitespace-only response.")

        usage = LLMUsage(
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            latency_ms=latency_ms,
        )

        return content, usage

    def complete(
        self,
        prompt: Prompt,
        schema: type[T],
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> tuple[T, LLMUsage]:
        """Send completion request to Ollama native endpoint with one repair round."""
        if max_tokens < LLM_MAX_TOKENS_FLOOR:
            raise LLMUnavailable(
                f"Requested max_tokens={max_tokens} is below LLM_MAX_TOKENS_FLOOR={LLM_MAX_TOKENS_FLOOR}."
            )

        messages = [
            {"role": "system", "content": prompt.system},
            {"role": "user", "content": prompt.user},
        ]

        raw_content, usage = self._call_api(messages, temperature, max_tokens)
        cleaned = strip_markdown_fences(raw_content)

        try:
            parsed = schema.model_validate_json(cleaned)
            return parsed, usage
        except ValidationError as first_err:
            repair_user = build_repair_prompt(raw_content, first_err, schema)
            repair_messages = messages + [
                {"role": "assistant", "content": raw_content},
                {"role": "user", "content": repair_user},
            ]

            repaired_content, repair_usage = self._call_api(
                repair_messages, temperature, max_tokens
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
                    f"Ollama output failed Pydantic validation after {LLM_REPAIR_ATTEMPTS} repair attempt: {second_err}"
                ) from second_err
