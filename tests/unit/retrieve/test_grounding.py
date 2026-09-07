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


def test_grounding_checks_the_quoted_span_and_not_the_sentence_around_it() -> None:
    """The limit of this check, pinned so nobody reads it as more than it is.

    `enforce_grounding` verifies that the span the model SAYS it took from a passage
    appears verbatim in one. It does not compare the model's own sentence against that
    passage, and it cannot: "does this sentence follow from that paragraph" is the
    judgement the model is already making, which is why this check deliberately avoids it.

    The consequence is real and was seen live on 5 September 2026. Asked "why was last
    night flagged, and what is my baseline", retrieval returned exactly the right two
    method passages, and the reply shown on the dashboard said the baseline is an
    "average" (it is the median) and that a night is "flagged" at 3 bpm (3 bpm is
    elevated; flagging needs two consecutive nights at 4). Both sentences carried a
    verbatim span, so both were reported as grounded and cited.

    This test asserts the CURRENT behaviour, including the part that is a limitation. If a
    future check compares claim text as well as span, these assertions should fail and be
    rewritten with the new behaviour measured. Do not delete it to make something pass.
    """
    passage = (
        "# What counts as an elevated night A night is called elevated when the resting "
        "heart rate measured during sleep sits at least 3 bpm above the person's own "
        "baseline, and is called RED at 4 bpm above it. An investigation opens only when "
        "2 consecutive nights are RED. That is the published rule exactly, and one RED "
        "night on its own never opens anything."
    )

    # The sentence a person was actually shown. "flagged" at 3 bpm is wrong: 3 bpm is
    # elevated, and flagging needs two consecutive RED nights at 4.
    misdescribes = GeneratedClaim(
        text="Last night was flagged if your resting heart rate was at least 3 bpm above "
        "that baseline.",
        evidence_span="at least 3 bpm above the person's own baseline",
    )

    # The limit case: a sentence that states the OPPOSITE of the span it quotes.
    contradicts = GeneratedClaim(
        text="A single night at 3 bpm above baseline opens an investigation.",
        evidence_span="An investigation opens only when 2 consecutive nights are RED",
    )

    grounded, unsupported = enforce_grounding([misdescribes, contradicts], [passage])

    assert unsupported == 0, "neither is caught, and that is the point of this test"
    assert len(grounded) == 2
    assert all(c.citation for c in grounded), "both are attributed to the passage"

    # What the check DOES catch, so the value of it is not understated either: a span that
    # is not in any passage at all, which is what an invented figure looks like.
    invented = GeneratedClaim(
        text="Seek care if your temperature exceeds 103 F.",
        evidence_span="seek care if your temperature exceeds 103 F",
    )
    grounded, unsupported = enforce_grounding([invented], [passage])
    assert unsupported == 1
    assert grounded == []
    assert invented.citation is None
