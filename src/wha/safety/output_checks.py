"""Pre-display output validation: schema, grounding, numbers, diagnosis guard, escalation criteria, no false reassurance."""

import re
from collections.abc import Iterable

from wha.constants import DETECT_PERSISTENCE_NIGHTS, DETECT_RED_BPM, DETECT_YELLOW_BPM
from wha.errors import SafetyIntercept
from wha.models import Disposition, EpisodeOutcome
from wha.retrieve import Citation, GeneratedClaim, enforce_grounding
from wha.safety.models import RedFlagsConfig
from wha.safety.rules import load_red_flags

FALSE_REASSURANCE_PHRASES = [
    "you are fine",
    "you're fine",
    "nothing to worry about",
    "definitely not",
    "it's nothing",
    "no need to worry",
    "completely fine",
    "all clear, no issue",
    # Observed in a live chest pain conversation, written into the reply with no marker.
    # Kept in step with `never_say` in red_flags.yaml; a test asserts the two agree.
    "that's reassuring",
    "that is reassuring",
    "thats reassuring",
]

DIAGNOSIS_PHRASES = [
    "confirmed diagnosis",
    "definitive diagnosis",
    "you are diagnosed with",
    "we diagnose you with",
    "we have diagnosed",
    "diagnosis is confirmed",
]


def default_escalation_criteria(config: RedFlagsConfig | None = None) -> list[str]:
    """The two general care-pathway lines, read from `red_flags.yaml`.

    They used to be a Python list here. They now live beside the tier A and tier B rules
    they summarise, so that every care-pathway sentence in the system is in one file and
    the retrievable corpus can cite all of them.
    """
    cfg = config or load_red_flags()
    return list(cfg.outcome_guidance.default)


# Which tier B sign a leading cause corresponds to, for step 2 of the selection below.
#
# Deliberately tiny and deliberately not clever. Only causes whose relationship to a sign in
# red_flags.yaml is unambiguous appear here; everything else falls through to the defaults.
# The alternative, inferring a sign from a cause name, would be this system writing care
# guidance from an association it made up, which is the whole thing item 2 removed.
CAUSE_TO_TIER_B: dict[str, tuple[str, ...]] = {
    "infection": ("rf_fever",),
    "recovery_tail": ("rf_severe_fatigue",),
}


def select_escalation_criteria(
    disposition: Disposition,
    triggered_flags: list[str] | None = None,
    config: RedFlagsConfig | None = None,
    leading_cause: str | None = None,
) -> list[str]:
    """Choose when-to-seek-care wording. Never write it.

    The model used to write this field freely and nothing checked it. In a live run it
    produced "Seek care if fever persists beyond 72 hours or exceeds 103 degrees F
    (39.4 C)", with both thresholds invented. This is the same split the Marburg triage
    already uses and that works well: the model elicits, a rule decides.

    Every returned line is a string that already exists in `red_flags.yaml`, so this
    cannot invent a threshold. It also cannot return an empty list, so it cannot make
    `validate_and_sanitize_outcome` raise and kill the episode.

    Order is deliberate. The specific reason this person is being told to seek care comes
    first, and the general boundary follows it.

    `leading_cause` is the top of the differential, and item 2 asked for it: "infection
    leading with a reported fever selects the tier B fever wording". It was not passed for
    two days, so a tier B symptom that never met its persistence rule never escalated, its
    id never reached `triggered_flags`, and its specific wording could not be chosen. The
    practical effect was small because the second default line is itself the fever wording,
    but the selection the item describes did not exist.
    """
    cfg = config or load_red_flags()
    flags = set(triggered_flags or [])

    selected: list[str] = []

    # 1. Anything the deterministic floor actually fired on, in the words that rule uses.
    for rule in cfg.tier_a:
        if rule.id in flags:
            selected.append(rule.guidance.strip())
    for vrule in cfg.vitals:
        if vrule.id in flags and vrule.guidance:
            selected.append(" ".join(vrule.guidance.split()))
    tier_b_hit = [b for b in cfg.tier_b if b.id in flags]
    for brule in tier_b_hit:
        if brule.guidance:
            selected.append(brule.guidance.strip())
    if tier_b_hit and cfg.tier_b_guidance:
        selected.append(" ".join(cfg.tier_b_guidance.split()))

    # 2. The leading explanation, when the floor did not already speak to it.
    #
    #    Only ever ADDS a line that is already in red_flags.yaml, and only for a cause the
    #    file maps to a sign. It cannot invent wording and it cannot remove any.
    if leading_cause and not tier_b_hit:
        for brule in cfg.tier_b:
            if brule.id in CAUSE_TO_TIER_B.get(leading_cause, ()) and brule.guidance:
                selected.append(brule.guidance.strip())
                if cfg.tier_b_guidance:
                    selected.append(" ".join(cfg.tier_b_guidance.split()))
                break

    # 3. An escalated episode with no surviving flag detail still says the urgent line
    #    first, because the disposition itself is the reason.
    if disposition == Disposition.ESCALATED and not selected:
        selected.extend(default_escalation_criteria(cfg)[:1])

    # 4. The general boundary, on every outcome including LIKELY_BENIGN. A benign
    #    conclusion is the one a person is most likely to act on by doing nothing.
    selected.extend(default_escalation_criteria(cfg))

    seen: set[str] = set()
    unique: list[str] = []
    for line in selected:
        if line and line not in seen:
            seen.add(line)
            unique.append(line)
    return unique


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


def collect_allowed_numbers(
    outcome: EpisodeOutcome,
    episode_numbers: Iterable[float] | None = None,
) -> set[float]:
    """Every number this episode is entitled to mention.

    This used to blanket-permit 0 through 10, plus 14, 21, 28 and 30. That waved through
    exactly the errors worth catching: a model writing "over 5 nights" about a two night
    episode passed, and that sentence appeared in a real outcome. The allowance is now the
    episode's own numbers, supplied by the caller, plus the detection thresholds, which
    are fixed and which the prose legitimately quotes.

    0 and 1 stay. They are not plausible fabricated clinical figures, and the regex only
    sees digits, so "one night" was never matched in the first place.
    """
    allowed: set[float] = {
        float(outcome.baseline_nights),
        float(outcome.unsupported_claims),
        float(outcome.interruptions_used_this_week),
        float(outcome.depth_used_this_episode),
        float(DETECT_YELLOW_BPM),
        float(DETECT_RED_BPM),
        float(DETECT_PERSISTENCE_NIGHTS),
        0.0,
        1.0,
        995.0,  # Emergency number
    }

    for value in episode_numbers or ():
        allowed.add(float(value))
        allowed.add(float(round(value, 1)))
        allowed.add(float(round(value)))

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
    episode_numbers: Iterable[float] | None = None,
) -> EpisodeOutcome:
    """Execute all six pre-display output validation checks.

    1. Schema validation (already enforced by EpisodeOutcome type).
    2. Deterministic claim-to-source enforcement on clinical claims.
    3. No fabricated numbers in prose (unreferenced figures stripped).
    4. Regulatory check: no definitive diagnosis assertions.
    5. Escalation criteria presence (must never be empty, even for LIKELY_BENIGN).
    6. No false reassurance phrases (e.g. 'you are fine' is strictly forbidden).
    """
    # 5. Escalation criteria presence.
    #
    # This used to raise ValidationFailed for any non-benign disposition with empty
    # criteria, and the call in node_critique sits OUTSIDE its try block, so an outcome
    # that lost its criteria took the whole episode down with it. A person then got no
    # conclusion at all, which is strictly worse than getting the general lines. It now
    # fills from red_flags.yaml for every disposition and never raises.
    escalation_criteria = list(outcome.escalation_criteria)
    if not escalation_criteria:
        escalation_criteria = select_escalation_criteria(outcome.disposition)

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
    allowed_nums = collect_allowed_numbers(outcome, episode_numbers)
    sanitized_obs = sanitize_fabricated_numbers_in_prose(outcome.observation, allowed_nums)

    return outcome.model_copy(
        update={
            "observation": sanitized_obs or outcome.observation,
            "citations": citations,
            "unsupported_claims": unsupported_count,
            "escalation_criteria": escalation_criteria,
        }
    )
