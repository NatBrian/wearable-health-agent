"""The validated decision rules, and the boundaries they are not allowed to cross."""

import pytest

from wha.safety.triage import (
    evaluate_rule,
    load_triage_rules,
    more_urgent,
    rule_for,
    triage,
    urgency_rank,
)

_ALL_NO = {
    "mhs_age_sex": False,
    "mhs_known_vascular": False,
    "mhs_worse_with_exercise": False,
    "mhs_reproducible_by_palpation": True,  # pressing DOES reproduce it, so no point
    "mhs_patient_assumes_cardiac": False,
}


def test_the_transcribed_rule_matches_the_published_one() -> None:
    """Five items, one point each, cut-off 3. Checked against Bosner CMAJ 2010."""
    rule = rule_for("chest_pain")
    assert rule is not None
    assert rule.id == "marburg_heart_score"
    assert {i.id for i in rule.items} == {
        "mhs_age_sex",
        "mhs_known_vascular",
        "mhs_worse_with_exercise",
        "mhs_reproducible_by_palpation",
        "mhs_patient_assumes_cardiac",
    }
    assert sum(i.points for i in rule.items) == 5
    assert rule.performance["cutoff"] == 3
    assert rule.performance["sensitivity"] == pytest.approx(0.871)
    assert rule.performance["specificity"] == pytest.approx(0.808)
    assert rule.minimum_age_years == 35


def test_the_palpation_item_scores_on_the_negative_as_published() -> None:
    """Pain reproduced by pressing scores zero; not reproducible scores one.

    The stored answer is the literal answer to the question asked. Getting this backwards
    inverts the score for every person who presses their chest, which is the single most
    likely transcription error in the whole rule.
    """
    rule = rule_for("chest_pain")
    assert rule is not None

    reproducible = evaluate_rule(rule, {**_ALL_NO, "mhs_reproducible_by_palpation": True})
    not_reproducible = evaluate_rule(rule, {**_ALL_NO, "mhs_reproducible_by_palpation": False})

    assert reproducible.score == 0
    assert not_reproducible.score == 1


def test_a_low_score_routes_to_a_same_day_appointment_not_an_ambulance() -> None:
    """This is the behaviour change: a phrase match is no longer a verdict."""
    outcome = triage("chest_pain", answers=_ALL_NO, age_years=40)

    assert outcome.complete
    assert outcome.score == 0
    assert outcome.urgency == "same_day"
    assert "not an emergency department" in outcome.meaning
    # It still names what the number rests on, rather than asserting reassurance.
    assert "98" in outcome.meaning


def test_the_cut_off_is_three() -> None:
    """Two points is same-day, three is urgent. The published threshold, unchanged."""
    two = triage(
        "chest_pain",
        answers={**_ALL_NO, "mhs_age_sex": True, "mhs_worse_with_exercise": True},
        age_years=70,
    )
    three = triage(
        "chest_pain",
        answers={
            **_ALL_NO,
            "mhs_age_sex": True,
            "mhs_worse_with_exercise": True,
            "mhs_reproducible_by_palpation": False,
        },
        age_years=70,
    )

    assert two.score == 2
    assert two.urgency == "same_day"
    assert three.score == 3
    assert three.urgency == "urgent"


def test_an_unconditional_gate_stops_the_rule_running_at_all() -> None:
    """Marburg's own contraindication is "do not use in an emergency setting".

    Once the presentation looks like one, no score is computed and no number can talk it
    down. This is the property that keeps the deterministic floor unreasonable-past.
    """
    for gate in ("gate_ongoing_severe", "gate_collapse", "gate_cannot_speak", "gate_autonomic"):
        outcome = triage("chest_pain", gates={gate: True}, answers=_ALL_NO, age_years=40)
        assert outcome.urgency == "urgent", gate
        assert outcome.gate_triggered == gate
        assert outcome.score is None, "a score was computed for a presentation that excludes it"


def test_a_rule_is_not_applied_outside_the_population_it_was_tested_in() -> None:
    """Marburg was derived and validated in people aged 35 and over."""
    outcome = triage("chest_pain", answers=_ALL_NO, age_years=22)
    assert outcome.urgency == "urgent"
    assert "35 and over" in outcome.meaning


def test_a_partial_answer_set_yields_no_urgency_at_all() -> None:
    """A partial score is not the score the paper validated.

    The caller must read this as "keep asking", never as "nothing found". Returning a
    low urgency from half the items would be inventing a rule the evidence does not
    support.
    """
    outcome = triage("chest_pain", answers={"mhs_age_sex": False}, age_years=40)

    assert outcome.complete is False
    assert outcome.urgency is None
    assert len(outcome.missing_items) == 4


def test_a_presentation_with_no_validated_rule_escalates_rather_than_guesses() -> None:
    """Syncope, meningism and the rest need an ECG or bloods that this system cannot do."""
    config = load_triage_rules()
    assert "syncope" in config.no_validated_rule

    outcome = triage("syncope", answers={})
    assert outcome.urgency == "urgent"
    assert "escalates rather than guesses" in outcome.meaning


def test_combining_urgencies_can_only_escalate() -> None:
    """Nothing that combines two findings may end up less urgent than either."""
    assert urgency_rank("urgent") < urgency_rank("same_day") < urgency_rank("advice")
    assert more_urgent("same_day", "urgent") == "urgent"
    assert more_urgent("urgent", "advice") == "urgent"
    assert more_urgent(None, "same_day") == "same_day"
    assert more_urgent("advice", None) == "advice"


def test_every_rule_carries_its_citation_and_its_contraindication() -> None:
    """A rule without its source and its limits is an assertion, not a transcription."""
    for rule in load_triage_rules().rules:
        assert rule.citation.strip(), rule.id
        assert rule.citation_plain.strip(), rule.id
        assert rule.contraindication.strip(), rule.id
        assert rule.performance, rule.id


# --- blood oxygen: a cited threshold, never an invented likelihood -------------------


def test_a_handful_of_spot_readings_yields_no_opinion() -> None:
    """One spot check is not a night, and no opinion must never render as reassurance.

    This is the real device's actual data: six readings across four days, including an 80
    percent followed by a 92 percent sixty-six seconds later. Judging a night on that
    would be judging movement artefact.
    """
    from wha.safety.triage import assess_overnight_oxygen

    assert assess_overnight_oxygen([94, 92, 94, 80, 92, 92]) is None


def test_a_sustained_low_night_reaches_the_published_threshold() -> None:
    """WHO guidance: below 93 percent warrants medical attention rather than home care."""
    from wha.safety.triage import assess_overnight_oxygen

    outcome = assess_overnight_oxygen([91, 92, 90, 92, 91, 93, 91, 92, 90, 92, 91, 92])

    assert outcome is not None
    assert outcome.urgency == "urgent"
    assert outcome.citation, "a threshold without its source is an assertion"


def test_the_median_is_used_so_one_artefact_cannot_fire_the_rule() -> None:
    """The minimum would fire on every movement artefact this sensor produces."""
    from wha.safety.triage import assess_overnight_oxygen

    # A normal night containing one implausible dip, which is what the real data looks like.
    outcome = assess_overnight_oxygen([97, 98, 97, 80, 98, 97, 98, 97, 98, 97, 98, 97])

    assert outcome is not None
    assert outcome.urgency is None, "a single artefact fired the rule"


def test_a_normal_night_is_explicitly_not_an_all_clear() -> None:
    """These sensors read high on darker skin, so a genuine fall can be missed.

    Pooled mean bias 0.70 percent light, 0.27 medium, 1.27 dark pigmentation (systematic
    review and meta-analysis, J Med Internet Res 2024;26:e62769), and occult hypoxaemia
    went undetected roughly three times more often in Black patients during COVID. A
    reading above the threshold therefore carries a caveat rather than a reassurance.
    """
    from wha.safety.triage import assess_overnight_oxygen

    outcome = assess_overnight_oxygen([97, 98, 97, 98, 97, 98, 97, 98, 97, 98, 97, 98])

    assert outcome is not None
    assert outcome.urgency is None
    assert "NOT an all-clear" in outcome.meaning


def test_blood_oxygen_never_became_a_belief_likelihood() -> None:
    """No published study relates a wearable SpO2 reading to any of the twelve causes.

    It is a threshold rule for action, not evidence about cause. If a likelihood ever
    appears in causes.yaml it needs a citation, and this test should be the thing that
    notices it did not have one.
    """
    from wha.belief.causes import load_causes

    for cause in load_causes():
        assert "oxygen" not in cause.citation.lower() or "WHO" in cause.citation
