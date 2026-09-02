"""Deterministic safety floor matcher and red_flags.yaml loader."""

import re
from pathlib import Path

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
        return RedFlagsConfig.model_validate(data)
    except Exception as e:
        raise ConfigError(f"Failed to load red flags config from '{file_path}': {e}") from e


def is_phrase_negated(
    text: str,
    target_phrase: str,
    negation_phrases: list[str],
    window_words: int = 4,
) -> bool:
    """Check if all occurrences of target_phrase in text are preceded by a negation phrase."""
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

    return not has_unnegated_match


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
    config: RedFlagsConfig | None = None,
) -> SafetyCheckResult:
    """Evaluate deterministic safety floor (Tier A, Tier B, and Vitals rules)."""
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

    if len(tier_b_matched) >= 2:
        for bid in tier_b_matched:
            if bid not in triggered_flags:
                triggered_flags.append(bid)
        escalate_same_day = True
        reasons.append(f"Multiple Tier B symptoms co-occurred ({len(tier_b_matched)} symptoms)")

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
