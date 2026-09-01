"""Safety layer: red flag rules, outbound validation, injection detection, and pre-display output checks."""

from wha.safety.injection import (
    InjectionVerdict,
    scan_untrusted,
)
from wha.safety.models import (
    NegationGuards,
    RedFlagsConfig,
    SafetyCheckResult,
    TierARule,
    TierBRule,
    VitalsRule,
)
from wha.safety.outbound import (
    OutboundMessage,
    OutboundValidationResult,
    validate_outbound,
)
from wha.safety.output_checks import (
    check_no_diagnosis_language,
    check_no_false_reassurance,
    sanitize_fabricated_numbers_in_prose,
    validate_and_sanitize_outcome,
)
from wha.safety.rules import (
    check_red_flags_deterministic,
    is_phrase_negated,
    load_red_flags,
    matches_symptom,
)
from wha.safety.tier_c import (
    LLMRedFlagOutput,
    check_red_flags_with_tier_c,
)

__all__ = [
    "InjectionVerdict",
    "LLMRedFlagOutput",
    "NegationGuards",
    "OutboundMessage",
    "OutboundValidationResult",
    "RedFlagsConfig",
    "SafetyCheckResult",
    "TierARule",
    "TierBRule",
    "VitalsRule",
    "check_no_diagnosis_language",
    "check_no_false_reassurance",
    "check_red_flags_deterministic",
    "check_red_flags_with_tier_c",
    "is_phrase_negated",
    "load_red_flags",
    "matches_symptom",
    "sanitize_fabricated_numbers_in_prose",
    "scan_untrusted",
    "validate_and_sanitize_outcome",
    "validate_outbound",
]
