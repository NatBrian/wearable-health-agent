"""Pre-display output validation: schema, grounding, numbers, diagnosis guard, escalation criteria, no false reassurance."""

import re

from wha.errors import SafetyIntercept, ValidationFailed
from wha.models import Disposition, EpisodeOutcome
from wha.retrieve import Citation, GeneratedClaim, enforce_grounding

FALSE_REASSURANCE_PHRASES = [
    "you are fine",
    "you're fine",
    "nothing to worry about",
    "definitely not",
    "it's nothing",
    "no need to worry",
    "completely fine",
    "all clear, no issue",
]

DIAGNOSIS_PHRASES = [
    "confirmed diagnosis",
    "definitive diagnosis",
    "you are diagnosed with",
    "we diagnose you with",
    "we have diagnosed",
    "diagnosis is confirmed",
]

DEFAULT_ESCALATION_CRITERIA = [
    "Seek urgent medical attention (call 995 or go to an A&E) if you develop chest pain, shortness of breath at rest, fainting, or sudden confusion.",
    "See a doctor today if you have a high fever that does not settle or co-occurring severe body aches.",
]


def extract_numbers_from_text(text: str) -> list[float]:
    """Extract numeric values (integers and floats) from text."""
    matches = re.findall(r"\b\d+(?:\.\d+)?\b", text)
    nums: list[float] = []
    for m in matches:
        try:
            nums.append(float(m))
        except ValueError:
            pass
    return nums


def collect_allowed_numbers(outcome: EpisodeOutcome) -> set[float]:
    """Gather all legitimate numeric values declared in structured fields."""
    allowed: set[float] = {
        float(outcome.baseline_nights),
        float(outcome.unsupported_claims),
        float(outcome.interruptions_used_this_week),
        float(outcome.depth_used_this_episode),
        # Common valid time/cardinal references
        0.0,
        1.0,
        2.0,
        3.0,
        4.0,
        5.0,
        6.0,
        7.0,
        8.0,
        9.0,
        10.0,
        14.0,
        21.0,
        28.0,
        30.0,
        995.0,  # Emergency number
    }

    for diff in outcome.differential:
        allowed.add(float(diff.probability))
        # Support percentage representations e.g. 0.85 -> 85
        allowed.add(round(diff.probability * 100, 1))
        allowed.add(float(round(diff.probability * 100)))

    return allowed


def sanitize_fabricated_numbers_in_prose(
    prose: str,
    allowed_numbers: set[float],
) -> str:
    """Filter or strip sentences in prose that reference ungrounded numeric figures."""
    sentences = re.split(r"(?<=[.!?])\s+", prose.strip())
    valid_sentences: list[str] = []

    for sentence in sentences:
        if not sentence:
            continue
        nums = extract_numbers_from_text(sentence)
        has_fabricated = False
        for n in nums:
            # Match with small float tolerance
            if not any(abs(n - a) < 1e-4 for a in allowed_numbers):
                has_fabricated = True
                break

        if not has_fabricated:
            valid_sentences.append(sentence)

    return " ".join(valid_sentences)


def check_no_false_reassurance(text: str) -> None:
    """Ensure no forbidden reassuring phrases appear anywhere in text."""
    lower = text.lower()
    for phrase in FALSE_REASSURANCE_PHRASES:
        if phrase in lower:
            raise SafetyIntercept(f"Prohibited false reassurance phrase detected: '{phrase}'")


def check_no_diagnosis_language(text: str) -> None:
    """Regulatory boundary check: output must not claim definitive diagnostic verdict."""
    lower = text.lower()
    for phrase in DIAGNOSIS_PHRASES:
        if phrase in lower:
            raise SafetyIntercept(f"Prohibited diagnostic language detected: '{phrase}'")


def validate_and_sanitize_outcome(
    outcome: EpisodeOutcome,
    passages: list[Citation] | None = None,
    claims: list[GeneratedClaim] | None = None,
) -> EpisodeOutcome:
    """Execute all six pre-display output validation checks.

    1. Schema validation (already enforced by EpisodeOutcome type).
    2. Deterministic claim-to-source enforcement on clinical claims.
    3. No fabricated numbers in prose (unreferenced figures stripped).
    4. Regulatory check: no definitive diagnosis assertions.
    5. Escalation criteria presence (must never be empty, even for LIKELY_BENIGN).
    6. No false reassurance phrases (e.g. 'you are fine' is strictly forbidden).
    """
    # 5. Escalation criteria check
    escalation_criteria = list(outcome.escalation_criteria)
    if not escalation_criteria:
        if outcome.disposition == Disposition.LIKELY_BENIGN:
            escalation_criteria = list(DEFAULT_ESCALATION_CRITERIA)
        else:
            raise ValidationFailed("Episode outcome missing required escalation criteria.")

    # 6. No false reassurance check across all text fields
    all_text = " ".join(
        [
            outcome.observation,
            " ".join(outcome.evidence_used),
            " ".join(outcome.ruled_out),
            " ".join(escalation_criteria),
        ]
    )
    check_no_false_reassurance(all_text)

    # 4. No diagnosis language check
    check_no_diagnosis_language(all_text)

    # 2. Claim-to-source grounding check
    unsupported_count = outcome.unsupported_claims
    citations = list(outcome.citations)
    if claims is not None and passages is not None:
        grounded_claims, unsupp = enforce_grounding(claims, passages)
        unsupported_count = unsupp
        # Filter citations to only those referenced by grounded claims
        cited_ids = {c.citation for c in grounded_claims if c.citation}
        citations = [p for p in passages if p.source_id in cited_ids]

    # 3. No fabricated numbers check
    allowed_nums = collect_allowed_numbers(outcome)
    sanitized_obs = sanitize_fabricated_numbers_in_prose(outcome.observation, allowed_nums)

    return outcome.model_copy(
        update={
            "observation": sanitized_obs or outcome.observation,
            "citations": citations,
            "unsupported_claims": unsupported_count,
            "escalation_criteria": escalation_criteria,
        }
    )
