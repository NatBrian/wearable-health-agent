"""Unit tests for pre-display output validation checks."""

from datetime import date

import pytest

from wha.errors import SafetyIntercept
from wha.models import (
    BaselineRung,
    CauseId,
    DifferentialItem,
    Disposition,
    EpisodeOutcome,
)
from wha.retrieve import Citation, GeneratedClaim
from wha.safety import (
    check_no_false_reassurance,
    sanitize_fabricated_numbers_in_prose,
    validate_and_sanitize_outcome,
)


def create_base_outcome(
    disposition: Disposition = Disposition.LIKELY_ILLNESS,
    observation: str = "Heart rate elevated for 2 consecutive nights.",
    escalation_criteria: list[str] | None = None,
) -> EpisodeOutcome:
    """Helper to construct a valid base EpisodeOutcome."""
    return EpisodeOutcome(
        episode_id="ep_test_001",
        subject_id="sub_001",
        opened_on=date(2026, 9, 1),
        closed_on=date(2026, 9, 3),
        disposition=disposition,
        observation=observation,
        baseline_nights=14,
        baseline_rung=BaselineRung.MATURE,
        differential=[
            DifferentialItem(
                cause=CauseId.INFECTION,
                probability=0.85,
                supporting=["Elevated RHR without recorded activity"],
            )
        ],
        evidence_used=["rhr_elevated_2_nights"],
        ruled_out=["exertion"],
        citations=[],
        unsupported_claims=0,
        action="seek_same_day_care",
        escalation_criteria=(
            escalation_criteria
            if escalation_criteria is not None
            else ["Seek immediate care for chest pain or shortness of breath at rest."]
        ),
        confidence="high",
        interruptions_used_this_week=1,
        depth_used_this_episode=2,
    )


def test_claim_without_span_is_stripped_and_counted() -> None:
    """A claim lacking verbatim match in retrieved passages is stripped and incremented in unsupported_claims."""
    outcome = create_base_outcome()
    passages = [
        Citation(
            source_id="sg_dengue",
            title="Dengue Guide",
            text="Fever with retro-orbital pain is characteristic of dengue infection.",
        )
    ]

    claims = [
        GeneratedClaim(
            text="Patient exhibits classic dengue presentation.",
            evidence_span="retro-orbital pain is characteristic of dengue",
        ),
        GeneratedClaim(
            text="Fabricated ungrounded claim.",
            evidence_span="blood pressure dropped to 80 over 50",
        ),
    ]

    sanitized = validate_and_sanitize_outcome(outcome, passages=passages, claims=claims)
    assert sanitized.unsupported_claims == 1
    assert len(sanitized.citations) == 1
    assert sanitized.citations[0].source_id == "sg_dengue"


def test_number_in_prose_not_in_object_is_stripped() -> None:
    """Prose mentioning a fabricated numeric figure not found in structured fields is stripped."""
    allowed = {14.0, 0.85, 85.0, 2.0, 1.0}
    # "Your heart rate was 142 bpm." -> 142 is not in allowed numbers
    prose = "Heart rate was elevated for 2 consecutive nights. Your heart rate was 142 bpm."
    cleaned = sanitize_fabricated_numbers_in_prose(prose, allowed)

    assert "142" not in cleaned
    assert "Heart rate was elevated for 2 consecutive nights." in cleaned


def test_output_always_carries_escalation_criteria() -> None:
    """Every outcome, including LIKELY_BENIGN with empty criteria, carries non-empty escalation criteria."""
    benign_outcome = create_base_outcome(
        disposition=Disposition.LIKELY_BENIGN,
        escalation_criteria=[],
    )

    sanitized = validate_and_sanitize_outcome(benign_outcome)
    assert len(sanitized.escalation_criteria) > 0
    assert any("urgent" in c.lower() or "995" in c for c in sanitized.escalation_criteria)


def test_no_false_reassurance_string() -> None:
    """Any outcome text containing prohibited false reassurance ('you are fine') raises SafetyIntercept."""
    outcome = create_base_outcome(
        observation="Your resting heart rate was normal and you are fine.",
    )

    with pytest.raises(SafetyIntercept):
        validate_and_sanitize_outcome(outcome)

    with pytest.raises(SafetyIntercept):
        check_no_false_reassurance("Everything is normal, you're fine!")
