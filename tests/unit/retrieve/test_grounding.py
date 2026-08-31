"""Unit tests for deterministic claim-to-source grounding enforcement."""

from wha.retrieve import Citation, GeneratedClaim, enforce_grounding


def test_grounding_accepts_verbatim_span() -> None:
    """Grounding accepts claims whose evidence span matches a passage verbatim."""
    passages = [
        Citation(
            source_id="sg_dengue_guidance",
            title="Dengue Guidance",
            text="Warning signs typically appear around the time of defervescence (days 3 to 7 of illness).",
        )
    ]

    claims = [
        GeneratedClaim(
            text="Dengue warning signs appear around days 3 to 7 of illness.",
            evidence_span="appear around the time of defervescence (days 3 to 7 of illness)",
        )
    ]

    grounded, unsupported = enforce_grounding(claims, passages)
    assert len(grounded) == 1
    assert unsupported == 0
    assert grounded[0].citation == "sg_dengue_guidance"


def test_grounding_rejects_paraphrased_span() -> None:
    """Grounding strictly rejects paraphrased evidence spans that do not appear verbatim."""
    passages = [
        Citation(
            source_id="statpearls_pharyngitis",
            title="Pharyngitis",
            text="Tonsillar exudates or swelling adds one point to the Centor score.",
        )
    ]

    # Paraphrased span (not verbatim)
    claims = [
        GeneratedClaim(
            text="Swollen tonsils increase the diagnostic Centor score.",
            evidence_span="swollen tonsils add a single point to the score",
        )
    ]

    grounded, unsupported = enforce_grounding(claims, passages)
    assert len(grounded) == 0
    assert unsupported == 1


def test_grounding_normalises_whitespace_and_case() -> None:
    """Grounding succeeds across varied casing and whitespace/newlines."""
    passages = [
        Citation(
            source_id="medline_fever",
            title="Fever Guide",
            text="Contact a healthcare provider if your temperature is 39.4 C (103 F) or higher.\n\nSeek immediate help for stiff neck.",
        )
    ]

    # Different casing and whitespace
    claims = [
        GeneratedClaim(
            text="High fever above 39.4 C requires medical contact.",
            evidence_span="TEMPERATURE IS 39.4   C (103 F)  OR HIGHER",
        )
    ]

    grounded, unsupported = enforce_grounding(claims, passages)
    assert len(grounded) == 1
    assert unsupported == 0


def test_stripped_claims_are_counted() -> None:
    """Claims failing grounding have citation stripped and count toward unsupported_claims."""
    passages = [
        Citation(
            source_id="doc_1",
            title="Doc 1",
            text="Resting heart rate elevation was observed.",
        )
    ]

    claims = [
        GeneratedClaim(
            text="Valid claim",
            evidence_span="resting heart rate elevation was observed",
        ),
        GeneratedClaim(
            text="Ungrounded fabricated claim",
            evidence_span="patient has severe pneumonia requiring hospital admission",
        ),
        GeneratedClaim(
            text="Empty evidence span",
            evidence_span="",
        ),
    ]

    grounded, unsupported = enforce_grounding(claims, passages)
    assert len(grounded) == 1
    assert unsupported == 2
    assert grounded[0].text == "Valid claim"
