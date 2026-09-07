"""Validated clinical decision rules, run from history alone. The rule decides, not the model.

A matched phrase used to be a verdict. Someone typing "chest pain" was routed straight to
an ambulance without a single confirming question, which is not what a clinician does and
not what the evidence supports.

Sutaria et al., BMC Health Serv Res 2025;25:1263, defines a red flag as a symptom that
would be **sought** to exclude serious illness, and measured online symptom checkers
seeking only 36.9 percent of the relevant ones against 71.8 percent for primary care
physicians. That paper is about symptom checkers, which is what this is, so it carries the
argument.

Downie et al., BMJ 2013;347:f7095, reviewed red flags systematically and found that "many
red flags in current guidelines provide virtually no change in probability ... or have
untested diagnostic accuracy". Individually most were uninformative; combinations carried
the information single features did not. **Read with its population attached:** that is a
review of red flags for cancer and fracture in LOW BACK PAIN. The quotation is accurate,
the finding is general in spirit, and it was not measured on chest pain or on anything
this module routes. It is cited as the reason to distrust a single matched phrase, which
is what it shows.

So the division of labour here is deliberate and is the whole point:

    the language model ELICITS the items, in conversation, in whatever words the person
    uses;
    this module's arithmetic DECIDES.

The model may raise urgency at any time. It can never lower it by reasoning. Urgency falls
only when a transcribed, published rule returns a lower band from items the person actually
supplied. Everything in ``data/knowledge/triage_rules.yaml`` is copied from its paper.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

TRIAGE_RULES_PATH = Path("data/knowledge/triage_rules.yaml")

# Ordered from most to least urgent. Used to combine bands and to refuse a downgrade.
URGENCY_ORDER: list[str] = ["urgent", "same_day", "advice"]


def urgency_rank(level: str | None) -> int:
    """Lower is more urgent. An unknown level ranks as least urgent."""
    if level in URGENCY_ORDER:
        return URGENCY_ORDER.index(level)
    return len(URGENCY_ORDER)


def more_urgent(left: str | None, right: str | None) -> str | None:
    """The more urgent of two levels. Used so combining can only ever escalate."""
    if left is None:
        return right
    if right is None:
        return left
    return left if urgency_rank(left) <= urgency_rank(right) else right


class TriageItem(BaseModel):
    """One question a rule needs answered, with what it is worth."""

    model_config = ConfigDict(frozen=True)

    id: str
    label: str
    points: int
    question_intent: str
    inverted: bool = False


class TriageBand(BaseModel):
    """A score range, the urgency it implies, and what that means in words."""

    model_config = ConfigDict(frozen=True)

    urgency: str
    meaning: str
    min_score: int | None = None
    max_score: int | None = None

    def contains(self, score: int) -> bool:
        """True when this band covers the score."""
        if self.min_score is not None and score < self.min_score:
            return False
        return not (self.max_score is not None and score > self.max_score)


class TriageRule(BaseModel):
    """A published decision rule that can be run from history alone."""

    model_config = ConfigDict(frozen=True)

    id: str
    applies_to: str
    label: str
    citation: str
    citation_plain: str
    items: list[TriageItem]
    bands: list[TriageBand]
    contraindication: str
    performance: dict[str, float] = Field(default_factory=dict)
    minimum_age_years: int | None = None


class UnconditionalGate(BaseModel):
    """A presentation where asking anything first is itself the harm."""

    model_config = ConfigDict(frozen=True)

    id: str
    label: str
    description: str = ""


class TriageConfig(BaseModel):
    """Everything in triage_rules.yaml, validated."""

    model_config = ConfigDict(frozen=True)

    unconditional: list[UnconditionalGate]
    unconditional_reason: str
    rules: list[TriageRule]
    no_validated_rule: list[str] = Field(default_factory=list)
    # Which red-flag rule id opens which discriminator conversation. A flag that is not
    # here has no validated history-only rule and stays an unconditional escalation.
    flag_presentations: dict[str, str] = Field(default_factory=dict)


class TriageOutcome(BaseModel):
    """What a rule concluded, and everything needed to show its working."""

    model_config = ConfigDict(frozen=True)

    rule_id: str | None
    urgency: str | None
    meaning: str
    score: int | None = None
    max_score: int | None = None
    # Which items were answered which way, so the person can see the arithmetic.
    item_findings: list[dict[str, Any]] = Field(default_factory=list)
    missing_items: list[str] = Field(default_factory=list)
    complete: bool = False
    citation: str = ""
    citation_plain: str = ""
    gate_triggered: str | None = None


_config_cache: TriageConfig | None = None


def load_triage_rules(path: Path | str | None = None) -> TriageConfig:
    """Read and validate the transcribed rules. Never written to by anything."""
    global _config_cache
    if _config_cache is not None and path is None:
        return _config_cache

    target = Path(path) if path is not None else TRIAGE_RULES_PATH
    data = yaml.safe_load(target.read_text(encoding="utf-8"))

    unconditional_block = data.get("unconditional", {}) or {}
    config = TriageConfig(
        unconditional=[UnconditionalGate(**g) for g in unconditional_block.get("gates", [])],
        unconditional_reason=str(unconditional_block.get("reason", "")).strip(),
        rules=[
            TriageRule(
                id=r["id"],
                applies_to=r["applies_to"],
                label=r["label"],
                citation=str(r.get("citation", "")).strip(),
                citation_plain=str(r.get("citation_plain", "")).strip(),
                contraindication=str(r.get("contraindication", "")).strip(),
                performance=r.get("performance", {}) or {},
                minimum_age_years=r.get("minimum_age_years"),
                items=[TriageItem(**i) for i in r.get("items", [])],
                bands=[TriageBand(**b) for b in r.get("bands", [])],
            )
            for r in data.get("rules", [])
        ],
        no_validated_rule=list(data.get("no_validated_rule", []) or []),
        flag_presentations=dict(data.get("flag_presentations", {}) or {}),
    )
    if path is None:
        _config_cache = config
    return config


def presentation_for_flag(flag_id: str, config: TriageConfig | None = None) -> str | None:
    """The discriminator conversation a matched red flag opens, if any exists for it."""
    cfg = config or load_triage_rules()
    return cfg.flag_presentations.get(flag_id)


def rule_for(presentation: str, config: TriageConfig | None = None) -> TriageRule | None:
    """The rule covering a presentation, or None when no validated rule exists for it."""
    cfg = config or load_triage_rules()
    for rule in cfg.rules:
        if rule.applies_to == presentation:
            return rule
    return None


def evaluate_rule(
    rule: TriageRule,
    answers: dict[str, bool | None],
) -> TriageOutcome:
    """Score a rule from the items gathered so far.

    ``answers`` maps item id to True, False, or None for not yet established. A rule with
    any item outstanding returns ``complete=False`` and no urgency, because a partial score
    is not the score the paper validated. The caller keeps asking, or falls back to the
    conservative route.
    """
    score = 0
    findings: list[dict[str, Any]] = []
    missing: list[str] = []

    for item in rule.items:
        given = answers.get(item.id)
        if given is None:
            missing.append(item.id)
            continue
        # `inverted` items score their point for a NO. Marburg's palpation item is scored
        # on the negative: pain reproducible by pressing scores zero, not reproducible
        # scores one. Transcribed as published rather than normalised, so the file can be
        # checked line by line against the paper.
        counts = (not given) if item.inverted else given
        if counts:
            score += item.points
        findings.append(
            {
                "item_id": item.id,
                "label": item.label,
                "answer": given,
                "points_awarded": item.points if counts else 0,
            }
        )

    max_score = sum(i.points for i in rule.items)

    if missing:
        return TriageOutcome(
            rule_id=rule.id,
            urgency=None,
            meaning="Not all of this rule's questions have been answered yet.",
            score=None,
            max_score=max_score,
            item_findings=findings,
            missing_items=missing,
            complete=False,
            citation=rule.citation,
            citation_plain=rule.citation_plain,
        )

    band = next((b for b in rule.bands if b.contains(score)), None)
    return TriageOutcome(
        rule_id=rule.id,
        urgency=band.urgency if band else None,
        meaning=band.meaning.strip() if band else "",
        score=score,
        max_score=max_score,
        item_findings=findings,
        missing_items=[],
        complete=True,
        citation=rule.citation,
        citation_plain=rule.citation_plain,
    )


def check_unconditional(
    gates_triggered: dict[str, bool | None],
    config: TriageConfig | None = None,
) -> UnconditionalGate | None:
    """The first gate the person has confirmed, if any.

    Checked before any rule runs. Marburg's own contraindication is "do not use in an
    emergency setting", so once a presentation looks like one, no score is computed at all
    and no number can talk it down.
    """
    cfg = config or load_triage_rules()
    for gate in cfg.unconditional:
        if gates_triggered.get(gate.id) is True:
            return gate
    return None


def triage(
    presentation: str,
    gates: dict[str, bool | None] | None = None,
    answers: dict[str, bool | None] | None = None,
    age_years: int | None = None,
    config: TriageConfig | None = None,
) -> TriageOutcome:
    """Route a presentation: unconditional gates first, then a validated rule if one exists.

    Returns an outcome with ``urgency=None`` and ``complete=False`` while items are still
    outstanding. The caller must treat that as "keep asking", never as "no problem".
    """
    cfg = config or load_triage_rules()

    gate = check_unconditional(gates or {}, cfg)
    if gate is not None:
        return TriageOutcome(
            rule_id=None,
            urgency="urgent",
            meaning=cfg.unconditional_reason,
            complete=True,
            gate_triggered=gate.id,
        )

    rule = rule_for(presentation, cfg)
    if rule is None:
        # No validated history-only rule exists for this presentation. Every candidate
        # needs an ECG, bloods or an examination. Escalating is the conservative direction
        # and it is a limitation rather than a result, stated as such on screen.
        return TriageOutcome(
            rule_id=None,
            urgency="urgent",
            meaning=(
                "No decision rule that works from history alone has been validated for "
                "this. Every published rule for it needs an ECG, blood tests or an "
                "examination, none of which this system can do, so it escalates rather "
                "than guesses."
            ),
            complete=True,
        )

    if (
        rule.minimum_age_years is not None
        and age_years is not None
        and age_years < rule.minimum_age_years
    ):
        return TriageOutcome(
            rule_id=rule.id,
            urgency="urgent",
            meaning=(
                f"{rule.label} was developed and tested only in people aged "
                f"{rule.minimum_age_years} and over, so it is not applied here."
            ),
            complete=True,
            citation=rule.citation,
            citation_plain=rule.citation_plain,
        )

    return evaluate_rule(rule, answers or {})


class OxygenBand(BaseModel):
    """A blood oxygen level and the urgency published guidance attaches to it."""

    model_config = ConfigDict(frozen=True)

    max_percent: float
    urgency: str
    meaning: str


class OxygenRule(BaseModel):
    """The blood oxygen threshold rule, and the conditions under which it may run."""

    model_config = ConfigDict(frozen=True)

    citation: str
    citation_plain: str
    min_overnight_readings: int
    bands: list[OxygenBand]
    never_reassure: str


def load_oxygen_rule(config: TriageConfig | None = None) -> OxygenRule | None:
    """The transcribed blood oxygen rule, or None when the file does not define one."""
    target = TRIAGE_RULES_PATH
    data = yaml.safe_load(target.read_text(encoding="utf-8"))
    block = (data or {}).get("oxygen")
    if not block:
        return None
    return OxygenRule(
        citation=str(block.get("citation", "")).strip(),
        citation_plain=str(block.get("citation_plain", "")).strip(),
        min_overnight_readings=int(block.get("min_overnight_readings", 0)),
        bands=[OxygenBand(**b) for b in block.get("bands", [])],
        never_reassure=str(block.get("never_reassure", "")).strip(),
    )


def assess_overnight_oxygen(
    readings: list[float],
    rule: OxygenRule | None = None,
) -> TriageOutcome | None:
    """Judge a night's blood oxygen against published thresholds.

    Returns None when there is not enough of a night to judge, which is the normal case on
    a device where overnight tracking has not been switched on. None means "no opinion",
    never "fine": the caller must not render an absence as reassurance.

    Uses the MEDIAN of the night's readings rather than the minimum. A single dip is what
    this sensor produces constantly through movement artefact; the real subject's own data
    contains an 80 percent followed by a 92 percent sixty-six seconds later. Taking the
    minimum would fire on that. The median asks whether the night as a whole sat low.
    """
    active = rule or load_oxygen_rule()
    if active is None or len(readings) < active.min_overnight_readings:
        return None

    ordered = sorted(readings)
    middle = len(ordered) // 2
    median = ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2.0

    band = next(
        (b for b in sorted(active.bands, key=lambda x: x.max_percent) if median <= b.max_percent),
        None,
    )
    if band is None:
        # Above every threshold. Explicitly not an all-clear: these sensors read high on
        # darker skin, so a genuine fall can be missed. No urgency, and the caller shows
        # the caveat rather than a reassurance.
        return TriageOutcome(
            rule_id="oxygen_threshold",
            urgency=None,
            meaning=active.never_reassure,
            score=int(median),
            complete=True,
            citation=active.citation,
            citation_plain=active.citation_plain,
        )

    return TriageOutcome(
        rule_id="oxygen_threshold",
        urgency=band.urgency,
        meaning=band.meaning.strip(),
        score=int(median),
        complete=True,
        citation=active.citation,
        citation_plain=active.citation_plain,
    )
