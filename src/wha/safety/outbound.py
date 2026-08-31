"""Outbound message validation with all six safety checks and fallback discipline."""

import re
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

from wha.constants import OUTBOUND_MAX_CHARS, TELEGRAM_CALLBACK_MAX_BYTES
from wha.errors import ConfigError
from wha.policy.probes import load_probes


class OutboundMessage(BaseModel):
    """Candidate outbound message before external delivery."""

    model_config = ConfigDict(frozen=True)

    kind: str = "QUESTION"  # "QUESTION", "OUTCOME", "NOTIFICATION", "ALERT"
    text: str
    probe_id: str | None = None
    option_labels: list[str] | None = None
    callback_data_list: list[str] | None = None
    dashboard_url: str | None = None


class OutboundValidationResult(BaseModel):
    """Result of outbound safety validation."""

    model_config = ConfigDict(frozen=True)

    valid: bool
    text_to_send: str
    text_source: str  # "generated", "fallback", or "none"
    safety_event: str | None = None
    violation_reason: str | None = None
    park_episode: bool = False


URL_REGEX = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)
HTML_TAG_REGEX = re.compile(r"<[^>]+>", re.IGNORECASE)


def validate_text_content(text: str, kind: str, allowed_url: str | None = None) -> str | None:
    """Run pure text checks: length, URLs, markup."""
    # 1. Length check
    if len(text) > OUTBOUND_MAX_CHARS:
        return f"Message length ({len(text)}) exceeds maximum allowed ({OUTBOUND_MAX_CHARS} chars)"

    # 2. URL check
    found_urls = URL_REGEX.findall(text)
    if found_urls:
        if kind == "OUTCOME" and allowed_url:
            for u in found_urls:
                if u != allowed_url:
                    return f"Unauthorized URL detected: {u}"
        else:
            return f"Outbound message contains unauthorized URL: {found_urls[0]}"

    # 3. Markup and control character check
    for char in text:
        if ord(char) < 32 and char not in ("\n", "\r", "\t"):
            return f"Prohibited control character found (ASCII {ord(char)})"

    if HTML_TAG_REGEX.search(text):
        return "Prohibited HTML/markup tags detected in text"

    return None


def validate_outbound(
    message: OutboundMessage,
    probes_cache: dict[str, Any] | None = None,
) -> OutboundValidationResult:
    """Execute all six outbound validation checks, falling back to probe fallback_text on failure."""
    probes = probes_cache
    if probes is None:
        try:
            probes_list = load_probes()
            probes = {p.probe_id: p for p in probes_list}
        except (ConfigError, FileNotFoundError, yaml.YAMLError, ValueError, TypeError):
            probes = {}

    violation = validate_text_content(message.text, message.kind, message.dashboard_url)

    # 4. Probe exists check
    probe_def = None
    if message.probe_id:
        if message.probe_id not in probes:
            violation = f"Unknown probe_id '{message.probe_id}' not found in registry"
        else:
            probe_def = probes[message.probe_id]

    # 5. Option slots check
    if not violation and probe_def is not None and message.option_labels is not None:
        expected_count = len(probe_def.answer_space)
        if len(message.option_labels) != expected_count:
            violation = (
                f"Option slot mismatch for probe '{message.probe_id}': "
                f"got {len(message.option_labels)}, expected {expected_count}"
            )

    # 6. Callback size check
    if not violation and message.callback_data_list:
        for cb in message.callback_data_list:
            cb_bytes = len(cb.encode("utf-8"))
            if cb_bytes > TELEGRAM_CALLBACK_MAX_BYTES:
                violation = (
                    f"callback_data '{cb}' is {cb_bytes} bytes, "
                    f"exceeding max {TELEGRAM_CALLBACK_MAX_BYTES} bytes"
                )

    # If valid on first pass
    if not violation:
        return OutboundValidationResult(
            valid=True,
            text_to_send=message.text,
            text_source="generated",
            safety_event=None,
            violation_reason=None,
            park_episode=False,
        )

    # Validation failed -> Attempt fallback if probe exists
    if probe_def is not None:
        fallback_text = probe_def.fallback_text
        fallback_violation = validate_text_content(
            fallback_text, message.kind, message.dashboard_url
        )

        if not fallback_violation:
            # Fallback is clean and valid -> send fallback
            return OutboundValidationResult(
                valid=True,
                text_to_send=fallback_text,
                text_source="fallback",
                safety_event="outbound_rejected",
                violation_reason=violation,
                park_episode=False,
            )

    # Fallback missing or itself unvalidatable -> park episode, do not send
    return OutboundValidationResult(
        valid=False,
        text_to_send="",
        text_source="none",
        safety_event="outbound_rejected",
        violation_reason=f"{violation}; Fallback also unvalidatable or unavailable.",
        park_episode=True,
    )
