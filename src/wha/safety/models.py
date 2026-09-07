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
    # THE STANDING RULE APPLIES HERE MOST OF ALL, and until 5 September 2026 it was not
    # applied here at all. causes.yaml and probes.yaml carry a per-row provenance and are
    # validated on load; this file carried none, so eleven safety numbers -- the two robust
    # z bounds, the two cold-rung absolute bounds, six tier B persistence windows and the
    # negation window -- had no source, no derivation and no ASSUMED label, and appeared in
    # no disclosure. The file's own footer calls them "the only place in this project where
    # a wrong number has a real-world consequence".
    #
    # CITED   a published number, with the source in `source`
    # DERIVED computed from other numbers in this repository, working in `derivation`
    # ASSUMED no published value was found. `assumption` states what was assumed and the
    #         direction it is conservative in. NOT a gap to be filled with a plausible
    #         figure later: an unevidenced number stays labelled until somebody measures it.
    provenance: str | None = None
    source: str | None = None
    derivation: str | None = None
    assumption: str | None = None


class TierBRule(BaseModel):
    """Tier B warning sign rule (escalates on 2+ co-occurring or persistence > persist_nights)."""

    model_config = ConfigDict(frozen=True)

    id: str
    match: list[str]
    persist_nights: int = 2
    guidance: str | None = None
    rationale: str | None = None
    # THE STANDING RULE APPLIES HERE MOST OF ALL, and until 5 September 2026 it was not
    # applied here at all. causes.yaml and probes.yaml carry a per-row provenance and are
    # validated on load; this file carried none, so eleven safety numbers -- the two robust
    # z bounds, the two cold-rung absolute bounds, six tier B persistence windows and the
    # negation window -- had no source, no derivation and no ASSUMED label, and appeared in
    # no disclosure. The file's own footer calls them "the only place in this project where
    # a wrong number has a real-world consequence".
    #
    # CITED   a published number, with the source in `source`
    # DERIVED computed from other numbers in this repository, working in `derivation`
    # ASSUMED no published value was found. `assumption` states what was assumed and the
    #         direction it is conservative in. NOT a gap to be filled with a plausible
    #         figure later: an unevidenced number stays labelled until somebody measures it.
    provenance: str | None = None
    source: str | None = None
    derivation: str | None = None
    assumption: str | None = None


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
    # A vitals rule carries TWO numbers with different standing: the robust z bound, which
    # is derived from figures in this repository, and the cold-rung absolute bpm bound,
    # for which no source was found. They get separate labels so the weaker one cannot
    # shelter under the stronger one's provenance.
    provenance_cold_rung: str | None = None
    assumption_cold_rung: str | None = None
    # THE STANDING RULE APPLIES HERE MOST OF ALL, and until 5 September 2026 it was not
    # applied here at all. causes.yaml and probes.yaml carry a per-row provenance and are
    # validated on load; this file carried none, so eleven safety numbers -- the two robust
    # z bounds, the two cold-rung absolute bounds, six tier B persistence windows and the
    # negation window -- had no source, no derivation and no ASSUMED label, and appeared in
    # no disclosure. The file's own footer calls them "the only place in this project where
    # a wrong number has a real-world consequence".
    #
    # CITED   a published number, with the source in `source`
    # DERIVED computed from other numbers in this repository, working in `derivation`
    # ASSUMED no published value was found. `assumption` states what was assumed and the
    #         direction it is conservative in. NOT a gap to be filled with a plausible
    #         figure later: an unevidenced number stays labelled until somebody measures it.
    provenance: str | None = None
    source: str | None = None
    derivation: str | None = None
    assumption: str | None = None


class OutcomeGuidance(BaseModel):
    """The care-pathway sentences an episode outcome may select from.

    Selection only. Nothing here is written at run time, which is the whole point: this
    field replaced a free-text field the model filled in, unchecked, with invented fever
    thresholds.
    """

    model_config = ConfigDict(frozen=True)

    default: list[str] = Field(default_factory=list)


class NegationGuards(BaseModel):
    """Negation phrases and window size."""

    model_config = ConfigDict(frozen=True)

    window_words: int = 4
    phrases: list[str] = Field(default_factory=list)
    note: str | None = None


class TrackedSymptom(BaseModel):
    """A symptom that is RECORDED over time but never escalates on its own.

    Added 7 September 2026. It exists because of a real question with no good answer under
    the previous design: dizziness. Putting it in Tier A or Tier B means asserting a
    routing threshold no source supports, and leaving it out entirely means a person can
    say "I feel dizzy", have it get worse for three nights, and have the system record
    nothing and ask nothing. Neither is acceptable.

    Tracking is a far weaker claim than escalating. It says only "this is a thing worth
    noticing that you told us about", which needs no clinical threshold to justify. A
    tracked symptom counts toward nothing in Tier B's arithmetic; what it does is keep the
    investigation from closing as benign while it is outstanding, and give the follow-up
    rule something to ask about.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    match: list[str]
    label: str
    rationale: str | None = None


class RedFlagsConfig(BaseModel):
    """Complete red flags specification loaded from data/knowledge/red_flags.yaml."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1.0"
    tier_a: list[TierARule]
    tier_b: list[TierBRule]
    vitals: list[VitalsRule]
    # Recorded, never escalated on. Defaults to empty so a config predating this section
    # still loads.
    tracked: list[TrackedSymptom] = Field(default_factory=list)
    negation_guards: NegationGuards
    tier_b_guidance: str = ""
    outcome_guidance: OutcomeGuidance = Field(default_factory=OutcomeGuidance)
    always: dict[str, Any] = Field(default_factory=dict)


class SafetyCheckResult(BaseModel):
    """Outcome of safety check evaluation."""

    model_config = ConfigDict(frozen=True)

    escalate: bool
    level: str | None = None  # "urgent", "same_day", or None
    triggered_flags: list[str] = Field(default_factory=list)
    """Every flag in play for this decision, INCLUDING ones carried from earlier nights.

    Not the same thing as "what this message said". `rules.py` adds the co-occurring
    flags from the symptom window here on purpose, because they are what the escalation
    is built on and the record has to show them. Reading this as tonight's report wrote
    every symptom still inside the window onto every night the person spoke, so a
    symptom could never expire and saying "I feel better" recorded more symptoms than
    saying nothing. Use `model_flags` for what was found in the text.
    """

    model_flags: list[str] = Field(default_factory=list)
    """What TIER C found in THIS text, and only this text.

    Empty when the model was not consulted or found nothing beyond the phrase lists.
    """

    guidance: list[str] = Field(default_factory=list)
    reason: str | None = None
