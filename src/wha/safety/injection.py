"""Untrusted text scanning and prompt injection detection."""

import re

from pydantic import BaseModel, ConfigDict, Field


class InjectionVerdict(BaseModel):
    """Result of scanning untrusted text for prompt injection patterns."""

    model_config = ConfigDict(frozen=True)

    detected: bool
    patterns_matched: list[str] = Field(default_factory=list)
    safety_event: str | None = None
    source_id: str = ""


INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(?:all\s+)?(?:prior|previous)\s+instructions?", re.IGNORECASE),
    re.compile(
        r"disregard\s+(?:all\s+)?(?:prior|previous)\s+(?:clinical|criteria|rules|instructions?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\[?\bSYSTEM\s+(?:OVERRIDE|UPDATE|COMMAND|PROMPT|INSTRUCTION)\b\]?",
        re.IGNORECASE,
    ),
    re.compile(r"suppress\s+(?:all\s+)?red\s+flags?", re.IGNORECASE),
    re.compile(
        r"confirm\s+(?:all\s+)?(?:physiological\s+deviations\s+are\s+)?benign",
        re.IGNORECASE,
    ),
    re.compile(r"do\s+not\s+escalate", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:a|an)?", re.IGNORECASE),
    re.compile(r"<\s*\|?(?:im_start|system|INST)\|?\s*>", re.IGNORECASE),
]


def scan_untrusted(text: str, source_id: str = "") -> InjectionVerdict:
    """Scan untrusted input text for prompt injection indicators.

    Content continues to flow as data even if injection is detected,
    recording safety_event='injection_contained' for audit integrity.
    """
    matched: list[str] = []
    for pat in INJECTION_PATTERNS:
        match = pat.search(text)
        if match:
            matched.append(match.group(0))

    if matched:
        return InjectionVerdict(
            detected=True,
            patterns_matched=matched,
            safety_event="injection_contained",
            source_id=source_id,
        )

    return InjectionVerdict(
        detected=False,
        patterns_matched=[],
        safety_event=None,
        source_id=source_id,
    )
