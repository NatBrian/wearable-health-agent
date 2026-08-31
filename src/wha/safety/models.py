"""Data models for red flag rules, safety intercepts, and outbound validation."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TierARule(BaseModel):
    """Tier A critical red flag rule (single symptom escalates immediately to urgent)."""

    model_config = ConfigDict(frozen=True)

    id: str
    match: list[str]
    guidance: str
    rationale: str | None = None
    requires_also: list[str] | None = None


class TierBRule(BaseModel):
    """Tier B warning sign rule (escalates on 2+ co-occurring or persistence > persist_nights)."""

    model_config = ConfigDict(frozen=True)

    id: str
    match: list[str]
    persist_nights: int = 2
    guidance: str | None = None
    rationale: str | None = None


class VitalsRule(BaseModel):
    """Vitals-based safety rule using robust z with cold rung fallback."""

    model_config = ConfigDict(frozen=True)

    id: str
    robust_z_above: float | None = None
    robust_z_below: float | None = None
    guidance: str = ""
    rationale: str | None = None
    cold_rung_fallback_bpm_above: float | None = None
    cold_rung_fallback_bpm_below: float | None = None
    cold_rung_note: str | None = None


class NegationGuards(BaseModel):
    """Negation phrases and window size."""

    model_config = ConfigDict(frozen=True)

    window_words: int = 4
    phrases: list[str] = Field(default_factory=list)
    note: str | None = None


class RedFlagsConfig(BaseModel):
    """Complete red flags specification loaded from data/knowledge/red_flags.yaml."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1.0"
    tier_a: list[TierARule]
    tier_b: list[TierBRule]
    vitals: list[VitalsRule]
    negation_guards: NegationGuards
    tier_b_guidance: str = ""
    always: dict[str, Any] = Field(default_factory=dict)


class SafetyCheckResult(BaseModel):
    """Outcome of safety check evaluation."""

    model_config = ConfigDict(frozen=True)

    escalate: bool
    level: str | None = None  # "urgent", "same_day", or None
    triggered_flags: list[str] = Field(default_factory=list)
    guidance: list[str] = Field(default_factory=list)
    reason: str | None = None
