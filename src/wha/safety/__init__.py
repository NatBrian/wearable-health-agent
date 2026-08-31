"""Safety layer: red flag rules, outbound validation, and injection detection."""

from wha.safety.models import (
    NegationGuards,
    RedFlagsConfig,
    SafetyCheckResult,
    TierARule,
    TierBRule,
    VitalsRule,
)
from wha.safety.rules import (
    check_red_flags_deterministic,
    is_phrase_negated,
    load_red_flags,
    matches_symptom,
)

__all__ = [
    "NegationGuards",
    "RedFlagsConfig",
    "SafetyCheckResult",
    "TierARule",
    "TierBRule",
    "VitalsRule",
    "check_red_flags_deterministic",
    "is_phrase_negated",
    "load_red_flags",
    "matches_symptom",
]
