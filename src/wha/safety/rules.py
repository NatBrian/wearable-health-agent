"""Deterministic safety floor matcher and red_flags.yaml loader."""

import re
from pathlib import Path
from typing import Any

import yaml

from wha.errors import ConfigError
from wha.models import BaselineRung
from wha.safety.models import RedFlagsConfig, SafetyCheckResult

DEFAULT_RED_FLAGS_PATH = Path("data/knowledge/red_flags.yaml")

# A negation reaches forward only as far as the end of its own clause. In
# "no fever, but chest pain" the "no" denies the fever and asserts the chest pain,
# so the guard must stop at the comma and at "but" rather than suppressing the
# Tier A match that follows. This is the termination half of the standard NegEx
# rule, kept as a fixed list rather than a parser to preserve the "deliberately
# simple" posture recorded in red_flags.yaml. Suppressing a Tier A symptom is the
# one direction this layer must never fail in.
NEGATION_SCOPE_TERMINATORS = (
    "but",
    "however",
    "although",
    "though",
    "except",
    "aside from",
    "apart from",
    "other than",
    "still",
    "yet",
)

_CLAUSE_PUNCTUATION = re.compile(r"[,;.!?]")


def negation_scope(preceding_text: str, window_words: int) -> str:
    """Return the span of text in which a negation still applies to the phrase that follows.

    Everything up to and including the last clause boundary is discarded, then the
    configured word window is applied to what remains.
    """
    cut = 0
    for match in _CLAUSE_PUNCTUATION.finditer(preceding_text):
        cut = max(cut, match.end())
    for terminator in NEGATION_SCOPE_TERMINATORS:
        for match in re.finditer(rf"\b{re.escape(terminator)}\b", preceding_text):
            cut = max(cut, match.end())

    words = preceding_text[cut:].split()
    return " ".join(words[-window_words:]) if words else ""


def load_red_flags(path: Path | str | None = None) -> RedFlagsConfig:
    """Load and validate red_flags.yaml configuration, raising ConfigError if malformed."""
    file_path = Path(path) if path is not None else DEFAULT_RED_FLAGS_PATH
    if not file_path.is_file():
        raise ConfigError(f"Red flags configuration file not found: {file_path}")

    try:
        content = file_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            raise ConfigError(f"Invalid root structure in {file_path}")
        config = RedFlagsConfig.model_validate(data)
    except Exception as e:
        raise ConfigError(f"Failed to load red flags config from '{file_path}': {e}") from e

    _assert_every_number_declares_where_it_came_from(config, file_path)
    return config


VALID_PROVENANCE = {"CITED", "DERIVED", "ASSUMED"}


def _assert_every_number_declares_where_it_came_from(
    config: RedFlagsConfig, file_path: Path
) -> None:
    """Every number in the safety floor must say where it came from, or loading fails.

    causes.yaml and probes.yaml have been validated this way since they were written. This
    file was not, and it is the one the file's own footer calls "the only place in this
    project where a wrong number has a real-world consequence". Eleven numbers sat here
    with no source, no derivation and no ASSUMED label.

    ASSUMED is a perfectly good answer and six of these carry it. What is not allowed is
    silence, because silence is indistinguishable on the page from a measured figure.
    """
    problems: list[str] = []

    def check(rule_id: str, label: str, provenance: str | None, backing: str | None) -> None:
        if provenance is None:
            problems.append(f"{rule_id}: {label} has no provenance")
        elif provenance not in VALID_PROVENANCE:
            problems.append(
                f"{rule_id}: {label} provenance {provenance!r} is not one of "
                f"{sorted(VALID_PROVENANCE)}"
            )
        elif provenance != "CITED" and not (backing or "").strip():
            problems.append(
                f"{rule_id}: {label} is {provenance} and states no derivation or assumption"
            )

    for rule in config.tier_b:
        check(rule.id, "persist_nights", rule.provenance, rule.assumption or rule.derivation)

    for rule in config.vitals:
        check(rule.id, "robust z bound", rule.provenance, rule.derivation or rule.assumption)
        if rule.cold_rung_fallback_bpm_above is not None or (
            rule.cold_rung_fallback_bpm_below is not None
        ):
            check(
                rule.id,
                "cold rung bpm bound",
                rule.provenance_cold_rung,
                rule.assumption_cold_rung,
            )

    if problems:
        joined = (chr(10) + "  ").join(problems)
        raise ConfigError(
            f"{file_path} has safety numbers that do not say where they came from:"
            + chr(10)
            + "  "
            + joined
        )


# Words that report a symptom ENDING, and therefore read naturally AFTER it rather than
# before: "the fever has gone", not "gone fever". Both already appear in
# `negation_guards.phrases`, so this changes no clinical content and adds no new word.
#
# Added 7 September 2026. The guard looked backwards only, so "no fever" was understood
# and "the fever has gone" was recorded as a report of fever. That failed in the SAFE
# direction, because an undetected retraction leaves the symptom on the record and keeps
# an investigation open, which is why the fix is narrow rather than generous.
_RESOLUTION_WORDS = ("gone", "resolved")

# Only these may stand between the symptom and the resolution word. Anything else means
# the resolution belongs to a different symptom, and a naive forward window gets this
# catastrophically wrong: in "I still have a fever, the vomiting has gone", four words
# forward from "fever" reaches "gone" and retracts the fever the person just said they
# still have. A FALSE retraction is the dangerous direction, because a resolved symptom is
# the one thing that lets an investigation close as benign.
_AUXILIARIES = frozenset(
    {
        "is",
        "are",
        "was",
        "were",
        "has",
        "have",
        "had",
        "s",
        "all",
        "now",
        "already",
        "finally",
        "completely",
        "totally",
        "entirely",
    }
)


def _is_phrase_resolved(text: str, target_phrase: str, window_words: int) -> bool:
    """Whether every occurrence of the phrase is immediately followed by a resolution."""
    lower_text = text.lower()
    lower_target = target_phrase.lower()
    matches = list(re.finditer(re.escape(lower_target), lower_text))
    if not matches:
        return False

    for match in matches:
        following = re.findall(r"[a-z']+", lower_text[match.end() :])[:window_words]
        resolved = False
        for word in following:
            cleaned = word.replace("'", "")
            if cleaned in _RESOLUTION_WORDS:
                resolved = True
                break
            if cleaned not in _AUXILIARIES:
                break
        if not resolved:
            return False
    return True


def is_phrase_negated(
    text: str,
    target_phrase: str,
    negation_phrases: list[str],
    window_words: int = 4,
) -> bool:
    """Whether every occurrence of the phrase is negated, before it or right after it.

    Before: "no fever", "denies chest pain". After: "the fever has gone", which the
    backward-only version read as a report of fever.
    """
    lower_text = text.lower()
    lower_target = target_phrase.lower()

    # Find all start indices of target_phrase in lower_text
    matches = [m.start() for m in re.finditer(re.escape(lower_target), lower_text)]
    if not matches:
        return False

    has_unnegated_match = False
    for start_idx in matches:
        preceding_text = lower_text[:start_idx]
        window_text = negation_scope(preceding_text, window_words)

        is_negated = any(
            re.search(rf"\b{re.escape(neg)}\b", window_text) for neg in negation_phrases
        )

        if not is_negated:
            has_unnegated_match = True
            break

    if not has_unnegated_match:
        return True
    # Backward negation did not cover every occurrence. Try the forward form, which is a
    # FALLBACK and not a replacement: an earlier version returned the forward result
    # unconditionally and broke "no fever today", which the backward guard had always
    # handled correctly.
    return _is_phrase_resolved(text, target_phrase, window_words)


def matches_symptom(
    text: str,
    patterns: list[str],
    negation_phrases: list[str],
    window_words: int = 4,
) -> bool:
    """Return True if at least one pattern matches unnegated in text."""
    lower_text = text.lower()
    for pattern in patterns:
        lower_pat = pattern.lower()
        if lower_pat in lower_text and not is_phrase_negated(
            lower_text, lower_pat, negation_phrases, window_words
        ):
            return True
    return False


def check_red_flags_deterministic(
    user_text: str | None = None,
    robust_z: float | None = None,
    rhr_bpm: float | None = None,
    rung: BaselineRung | str | None = None,
    symptom_history: dict[str, int] | None = None,
    recent_tier_b: list[str] | None = None,
    config: RedFlagsConfig | None = None,
) -> SafetyCheckResult:
    """Evaluate deterministic safety floor (Tier A, Tier B, and Vitals rules).

    `symptom_history` maps a rule id to how many nights that symptom has been running.
    Until 7 September 2026 nothing passed it, so the persistence half of Tier B had never
    fired: the default of 1 is never greater than any persist_nights value. Build it with
    `wha.service.symptoms.symptom_history`.

    `recent_tier_b` is the Tier B ids seen on other nights inside the co-occurrence
    window. "Two or more co-occurring" was implemented as two or more in the same
    message, which is not what the word means, and it is the case of a person whose
    symptoms EVOLVE across nights that it failed hardest on.
    """
    cfg = config or load_red_flags()
    text = (user_text or "").strip()
    history = symptom_history or {}
    neg_phrases = cfg.negation_guards.phrases
    neg_window = cfg.negation_guards.window_words

    triggered_flags: list[str] = []
    guidance_list: list[str] = []
    escalate_urgent = False
    escalate_same_day = False
    reasons: list[str] = []

    # 1. Tier A Checks (one is enough -> urgent)
    if text:
        for rule in cfg.tier_a:
            if matches_symptom(text, rule.match, neg_phrases, neg_window):
                if rule.requires_also:
                    if matches_symptom(text, rule.requires_also, neg_phrases, neg_window):
                        triggered_flags.append(rule.id)
                        guidance_list.append(rule.guidance)
                        escalate_urgent = True
                        reasons.append(f"Tier A symptom matched: {rule.id}")
                else:
                    triggered_flags.append(rule.id)
                    guidance_list.append(rule.guidance)
                    escalate_urgent = True
                    reasons.append(f"Tier A symptom matched: {rule.id}")

    # 2. Vitals Checks
    rung_str = rung.value if isinstance(rung, BaselineRung) else str(rung or "").upper()
    is_cold_rung = rung_str in ("COLD", "PRIOR_DOMINATED")

    for vrule in cfg.vitals:
        if is_cold_rung:
            if rhr_bpm is not None:
                if (
                    vrule.cold_rung_fallback_bpm_above is not None
                    and rhr_bpm > vrule.cold_rung_fallback_bpm_above
                ):
                    triggered_flags.append(vrule.id)
                    guidance_list.append(vrule.guidance)
                    escalate_urgent = True
                    reasons.append(f"Vitals extreme high at cold rung ({rhr_bpm} bpm)")
                elif (
                    vrule.cold_rung_fallback_bpm_below is not None
                    and rhr_bpm < vrule.cold_rung_fallback_bpm_below
                ):
                    triggered_flags.append(vrule.id)
                    guidance_list.append(vrule.guidance)
                    escalate_urgent = True
                    reasons.append(f"Vitals extreme low at cold rung ({rhr_bpm} bpm)")
        else:
            if robust_z is not None:
                if vrule.robust_z_above is not None and robust_z > vrule.robust_z_above:
                    triggered_flags.append(vrule.id)
                    guidance_list.append(vrule.guidance)
                    escalate_urgent = True
                    reasons.append(f"Vitals robust z > {vrule.robust_z_above} (z={robust_z:.1f})")
                elif vrule.robust_z_below is not None and robust_z < vrule.robust_z_below:
                    triggered_flags.append(vrule.id)
                    guidance_list.append(vrule.guidance)
                    escalate_urgent = True
                    reasons.append(f"Vitals robust z < {vrule.robust_z_below} (z={robust_z:.1f})")

    # 3. Tier B Checks (two or more co-occurring, OR one persisting > persist_nights)
    tier_b_matched: list[str] = []
    if text:
        for brule in cfg.tier_b:
            if matches_symptom(text, brule.match, neg_phrases, neg_window):
                tier_b_matched.append(brule.id)
                # Check persistence for this symptom
                duration = history.get(brule.id, 1)
                if duration > brule.persist_nights:
                    triggered_flags.append(brule.id)
                    escalate_same_day = True
                    reasons.append(
                        f"Tier B symptom '{brule.id}' persisted {duration} nights > {brule.persist_nights}"
                    )

    # Co-occurrence spans the window, not the sentence. A fever on Monday and vomiting on
    # Tuesday co-occur in any ordinary reading of the word; scoring them as two unrelated
    # singletons is what let an evolving illness pass unnoticed night after night.
    cooccurring = sorted(set(tier_b_matched) | set(recent_tier_b or []))
    if len(cooccurring) >= 2:
        for bid in cooccurring:
            if bid not in triggered_flags:
                triggered_flags.append(bid)
        escalate_same_day = True
        across_nights = len(cooccurring) > len(tier_b_matched)
        reasons.append(
            f"Multiple Tier B symptoms co-occurred ({len(cooccurring)} symptoms"
            + (" across recent nights)" if across_nights else ")")
        )

    if escalate_same_day and not escalate_urgent and cfg.tier_b_guidance:
        guidance_list.append(cfg.tier_b_guidance)

    if escalate_urgent:
        level = "urgent"
    elif escalate_same_day:
        level = "same_day"
    else:
        level = None

    return SafetyCheckResult(
        escalate=(escalate_urgent or escalate_same_day),
        level=level,
        triggered_flags=triggered_flags,
        guidance=guidance_list,
        reason="; ".join(reasons) if reasons else None,
    )


def check_overnight_oxygen(
    conn: Any,
    subject_id: str,
    window_start_utc: Any,
    window_end_utc: Any,
) -> SafetyCheckResult | None:
    """Judge the night's blood oxygen against published thresholds, if there is a night of it.

    Returns None when the device supplied too few readings inside the sleep window, which
    is the normal case until overnight tracking is switched on in the phone app. None means
    no opinion. It must never be rendered as reassurance.

    This is a threshold rule for ACTION, not evidence about cause. No published study
    relates a wearable blood oxygen reading to any of the twelve causes in causes.yaml, so
    it gets no likelihood there; writing one would be inventing clinical content. What does
    exist is NHS England's COVID Oximetry @home pathway on when a level warrants care
    rather than home management (corrected 5 September 2026 from an earlier attribution to
    WHO, which recommends using home oximetry but publishes no such levels), and
    documented "silent hypoxia" in COVID, where oxygen falls while the person still feels
    well. That is the pre-symptomatic window this system exists for, and heart rate alone
    cannot see it.
    """
    from wha.db.iso import to_iso
    from wha.safety.triage import assess_overnight_oxygen

    # ts_utc is TEXT in the "%Y-%m-%dT%H:%M:%SZ" form every writer uses, and this compared
    # it against whatever sqlite3 makes of a datetime, which is "YYYY-MM-DD HH:MM:SS+00:00".
    # A space where a T should be, and an offset where a Z should be, so the range test was
    # a lexical comparison between two different formats and matched nothing. The rule had
    # no caller, so this never showed: connecting it would have returned zero readings on
    # every night and reported "no opinion" forever, which reads exactly like a device that
    # is not recording.
    start = to_iso(window_start_utc) if hasattr(window_start_utc, "tzinfo") else window_start_utc
    end = to_iso(window_end_utc) if hasattr(window_end_utc, "tzinfo") else window_end_utc

    rows = conn.execute(
        """SELECT percentage FROM oxygen_saturation_samples
            WHERE subject_id = ? AND ts_utc >= ? AND ts_utc <= ?""",
        (subject_id, start, end),
    ).fetchall()
    readings = [float(r["percentage"]) for r in rows if r["percentage"] is not None]

    outcome = assess_overnight_oxygen(readings)
    if outcome is None:
        return None

    return SafetyCheckResult(
        escalate=outcome.urgency in ("urgent", "same_day"),
        level=outcome.urgency,
        triggered_flags=["rf_overnight_oxygen"] if outcome.urgency else [],
        guidance=[outcome.meaning] if outcome.meaning else [],
        reason=(
            f"Overnight blood oxygen median {outcome.score} percent across "
            f"{len(readings)} readings. {outcome.citation}"
        ),
    )
