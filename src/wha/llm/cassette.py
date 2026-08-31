"""Deterministic offline cassette provider loading recorded fixtures from disk."""

import json
import os
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from wha.errors import LLMUnavailable, ValidationFailed
from wha.llm.client import LLMUsage, Prompt

T = TypeVar("T", bound=BaseModel)

DEFAULT_CASSETTE_DIR = Path("tests/fixtures/llm_cassettes")


class CassetteClient:
    """Offline cassette provider.

    Resolution order:
    1. <cassette_dir>/<prompt_id>/<scenario>.json (if WHA_SCENARIO is set)
    2. <cassette_dir>/<prompt_id>/default.json
    3. Hard failure naming prompt_id, scenario, and path.
    """

    def __init__(self, cassette_dir: Path | str | None = None) -> None:
        self.cassette_dir = Path(cassette_dir) if cassette_dir is not None else DEFAULT_CASSETTE_DIR
        self._list_indices: dict[str, int] = {}
        self.last_model_id = "authored-fixture"
        self.last_origin = "AUTHORED_FIXTURE"

    def complete(
        self,
        prompt: Prompt,
        schema: type[T],
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> tuple[T, LLMUsage]:
        """Load fixture and parse response into schema without network access."""
        scenario = os.environ.get("WHA_SCENARIO", "").strip()
        prompt_dir = self.cassette_dir / prompt.prompt_id

        target_file: Path | None = None
        looked_for_paths: list[str] = []

        if scenario:
            scenario_path = prompt_dir / f"{scenario}.json"
            looked_for_paths.append(str(scenario_path))
            if scenario_path.is_file():
                target_file = scenario_path

        if target_file is None:
            default_path = prompt_dir / "default.json"
            looked_for_paths.append(str(default_path))
            if default_path.is_file():
                target_file = default_path

        if target_file is None or not target_file.is_file():
            paths_str = ", ".join(f"'{p}'" for p in looked_for_paths)
            raise LLMUnavailable(
                f"Cassette miss for prompt_id='{prompt.prompt_id}', scenario='{scenario or 'default'}'. "
                f"Looked for: {paths_str}"
            )

        try:
            content = target_file.read_text(encoding="utf-8")
            data = json.loads(content)
        except Exception as e:
            raise LLMUnavailable(f"Failed to read cassette at '{target_file}': {e}") from e

        self.last_model_id = data.get("model_id", "authored-fixture")
        self.last_origin = data.get("origin", "AUTHORED_FIXTURE")

        raw_response = data.get("response")
        key = f"{prompt.prompt_id}:{scenario or 'default'}"

        if isinstance(raw_response, list):
            idx = self._list_indices.get(key, 0)
            if idx < len(raw_response):
                item = raw_response[idx]
                self._list_indices[key] = idx + 1
            else:
                # Past end of list: return Done structure if available in schema
                item = {"tool_call": None, "done": {"reason": "Investigation complete."}}
        else:
            item = raw_response

        usage_dict = data.get("usage", {})
        usage = LLMUsage(
            prompt_tokens=usage_dict.get("prompt_tokens", 0),
            completion_tokens=usage_dict.get("completion_tokens", 0),
            latency_ms=usage_dict.get("latency_ms", 0),
        )

        try:
            if isinstance(item, dict):
                obj = schema.model_validate(item)
            elif isinstance(item, str):
                obj = schema.model_validate_json(item)
            else:
                obj = schema.model_validate(item)
            return obj, usage
        except ValidationError as e:
            raise ValidationFailed(
                f"Cassette at '{target_file}' failed Pydantic schema validation for {schema.__name__}: {e}"
            ) from e
