"""Markdown fence stripping and JSON schema repair utilities."""

import re

from pydantic import BaseModel, ValidationError


def strip_markdown_fences(text: str) -> str:
    """Strip ```json ... ``` or ``` ... ``` markdown fences from raw text."""
    trimmed = text.strip()
    pattern = r"^```(?:json)?\s*\n?([\s\S]*?)\n?```$"
    match = re.match(pattern, trimmed, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return trimmed


def build_repair_prompt[T: BaseModel](
    raw_text: str, error: ValidationError, schema: type[T]
) -> str:
    """Build a targeted repair prompt explaining the validation error."""
    schema_json = schema.model_json_schema()
    return (
        f"The previous output failed validation with the following errors:\n{error}\n\n"
        f"Required JSON schema:\n{schema_json}\n\n"
        f"Original output:\n{raw_text}\n\n"
        "Please provide ONLY the corrected valid JSON conforming to the schema with no markdown formatting or commentary."
    )
