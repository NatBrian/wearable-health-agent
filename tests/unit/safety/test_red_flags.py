"""Unit tests for deterministic red flag rules (tiers A and B, vitals, negation guards)."""

from pathlib import Path

import pytest

from wha.errors import ConfigError
from wha.models import BaselineRung
from wha.safety import check_red_flags_deterministic, load_red_flags
from wha.safety.rules import negation_scope


def test_tier_a_single_symptom_escalates() -> None:
    """Each of the six Tier A critical symptoms individually triggers immediate urgent escalation."""
    tier_a_test_cases = [
        ("I have severe crushing chest pain.", "rf_chest_pain"),
        ("I am breathless sitting on the sofa and gasping.", "rf_breathless_at_rest"),
        ("I feel drowsy and confused and disoriented.", "rf_confusion"),
        ("I passed out and fainted this morning.", "rf_syncope"),
        ("I have a stiff neck and fever.", "rf_meningism"),
        ("I have coughing up blood and uncontrolled bleeding that won't stop.", "rf_bleeding"),
    ]

    for user_text, expected_flag in tier_a_test_cases:
        res = check_red_flags_deterministic(user_text=user_text)
        assert res.escalate is True, f"Failed to escalate on: {user_text}"
        assert res.level == "urgent", f"Expected urgent level on: {user_text}"
        assert expected_flag in res.triggered_flags, (
            f"Missing flag {expected_flag} in {res.triggered_flags}"
        )


def test_tier_b_single_symptom_does_not_escalate() -> None:
    """A single Tier B symptom without persistence does not escalate (balanced posture)."""
    tier_b_single_cases = [
        "I have a mild fever today.",
        "My muscles are aching all over.",
        "I feel exhausted and wiped out.",
        "I have no appetite at all.",
        "I feel short of breath when I move around.",
        "I was throwing up once this morning.",
    ]

    for user_text in tier_b_single_cases:
        res = check_red_flags_deterministic(user_text=user_text)
        assert res.escalate is False, f"Single Tier B symptom escalated unexpectedly: {user_text}"
        assert res.level is None


def test_tier_b_two_symptoms_escalate() -> None:
    """Two or more co-occurring Tier B symptoms escalate to same_day care."""
    user_text = "I have a fever and body aches all over."
    res = check_red_flags_deterministic(user_text=user_text)

    assert res.escalate is True
    assert res.level == "same_day"
    assert "rf_fever" in res.triggered_flags
    assert "rf_body_aches" in res.triggered_flags


def test_tier_b_persistence_escalates() -> None:
    """A single Tier B symptom persisting beyond its persist_nights threshold escalates to same_day."""
    # rf_fever has persist_nights: 3. A 4th night escalates.
    res = check_red_flags_deterministic(
        user_text="I still have a fever.",
        symptom_history={"rf_fever": 4},
    )
    assert res.escalate is True
    assert res.level == "same_day"
    assert "rf_fever" in res.triggered_flags


def test_negation_guard_suppresses() -> None:
    """Negated symptoms within the negation window do not trigger safety flags."""
    negated_texts = [
        "I have no chest pain at all.",
        "Patient denies shortness of breath at rest.",
        "I haven't had any fainting spells or blackouts.",
        "Without stiff neck, just a mild headache.",
        "My fever is resolved and gone.",
    ]

    for text in negated_texts:
        res = check_red_flags_deterministic(user_text=text)
        assert res.escalate is False, f"Negation failed for: {text}"
        assert len(res.triggered_flags) == 0


def test_vitals_rule_uses_robust_z_not_absolute() -> None:
    """At established baseline rungs, vitals rule triggers on robust z > 6.0 regardless of raw bpm."""
    # Rung is MATURE. RHR 85 bpm but robust_z = 7.2 -> triggers
    res = check_red_flags_deterministic(
        robust_z=7.2,
        rhr_bpm=85.0,
        rung=BaselineRung.MATURE,
    )
    assert res.escalate is True
    assert res.level == "urgent"
    assert "rf_rhr_extreme_high" in res.triggered_flags


def test_vitals_falls_back_at_cold_rung() -> None:
    """At COLD or PRIOR_DOMINATED rungs, vitals rule uses wide absolute fallback bounds."""
    # At COLD rung, robust z is unestablished, but RHR = 105 bpm (> 100) -> triggers fallback
    res = check_red_flags_deterministic(
        robust_z=2.0,
        rhr_bpm=105.0,
        rung=BaselineRung.COLD,
    )
    assert res.escalate is True
    assert res.level == "urgent"
    assert "rf_rhr_extreme_high" in res.triggered_flags

    # Normal RHR at cold rung does not trigger
    res_normal = check_red_flags_deterministic(
        robust_z=2.0,
        rhr_bpm=72.0,
        rung=BaselineRung.COLD,
    )
    assert res_normal.escalate is False


def test_escalation_at_cold_rung_still_happens() -> None:
    """Symptoms escalate reliably even when baseline rung is completely cold."""
    res = check_red_flags_deterministic(
        user_text="I have severe crushing chest pressure.",
        rung=BaselineRung.COLD,
    )
    assert res.escalate is True
    assert res.level == "urgent"
    assert "rf_chest_pain" in res.triggered_flags


def test_red_flags_yaml_malformed_raises_at_startup(tmp_path: Path) -> None:
    """Missing or invalid red_flags.yaml raises ConfigError."""
    bad_file = tmp_path / "bad_red_flags.yaml"
    bad_file.write_text("invalid: [broken, yaml: true", encoding="utf-8")

    with pytest.raises(ConfigError):
        load_red_flags(bad_file)


def test_negation_does_not_reach_past_a_clause_boundary() -> None:
    """A negation binds to its own clause only.

    "No fever, but chest pain" denies the fever and asserts the chest pain. Suppressing
    the Tier A match here is the single most dangerous failure this layer can have.
    """
    contrast_texts = [
        "No fever, but chest pain since this morning.",
        "I have no appetite but my chest pressure is bad.",
        "No cough. Chest tightness started an hour ago.",
        "Not dizzy, however I passed out at work.",
        "I have no headache; crushing pain in my chest though.",
    ]

    for text in contrast_texts:
        res = check_red_flags_deterministic(user_text=text)
        assert res.escalate is True, f"Negation leaked past the clause boundary for: {text}"
        assert res.level == "urgent", f"Expected urgent escalation for: {text}"
        assert len(res.triggered_flags) > 0


def test_negation_scope_stops_at_boundary() -> None:
    """The scope helper discards everything up to and including the last clause boundary."""
    assert negation_scope("no fever, but ", 4) == ""
    assert negation_scope("i have no ", 4) == "i have no"
    assert negation_scope("no cough. ", 4) == ""
    assert negation_scope("patient denies ", 4) == "patient denies"


def test_every_number_in_the_safety_floor_says_where_it_came_from() -> None:
    """The standing rule, applied to the file that needs it most.

    causes.yaml and probes.yaml have carried a per-row provenance since they were written,
    validated on load and pinned by tests. red_flags.yaml carried none, and its own footer
    calls its numbers "the only place in this project where a wrong number has a real-world
    consequence". Eleven safety numbers had no source, no derivation and no ASSUMED label,
    and appeared in no disclosure anywhere.

    ASSUMED is a perfectly good answer, and eight of the ten carry it. What is not allowed
    is silence, because silence is indistinguishable on the page from a measured figure.
    """
    from wha.safety.rules import load_red_flags

    config = load_red_flags()

    for rule in config.tier_b:
        assert rule.provenance in {"CITED", "DERIVED", "ASSUMED"}, rule.id
        assert (rule.assumption or rule.derivation or rule.source or "").strip(), (
            f"{rule.id} declares {rule.provenance} and gives no basis"
        )

    for rule in config.vitals:
        assert rule.provenance in {"CITED", "DERIVED", "ASSUMED"}, rule.id
        if (
            rule.cold_rung_fallback_bpm_above is not None
            or rule.cold_rung_fallback_bpm_below is not None
        ):
            assert rule.provenance_cold_rung in {"CITED", "DERIVED", "ASSUMED"}, rule.id
            assert (rule.assumption_cold_rung or "").strip(), (
                f"{rule.id} cold rung bound has no stated assumption"
            )


def test_loading_fails_loudly_if_a_safety_number_loses_its_provenance() -> None:
    """A guard that has never fired proves nothing, so fire it."""
    import tempfile
    from pathlib import Path

    import yaml

    from wha.errors import ConfigError
    from wha.safety.rules import DEFAULT_RED_FLAGS_PATH, load_red_flags

    data = yaml.safe_load(Path(DEFAULT_RED_FLAGS_PATH).read_text(encoding="utf-8"))
    data["tier_b"][0].pop("provenance")

    stripped = Path(tempfile.mkdtemp()) / "red_flags.yaml"
    stripped.write_text(yaml.safe_dump(data), encoding="utf-8")

    with pytest.raises(ConfigError) as excinfo:
        load_red_flags(stripped)
    assert "has no provenance" in str(excinfo.value)


def test_the_assumed_safety_numbers_reach_a_screen_and_not_only_a_file() -> None:
    """ "Labelled in the docs AND on the dashboard" is the rule, and both halves count."""
    from wha.service.belief import get_safety_rule_provenance

    rows = get_safety_rule_provenance()
    assert rows, "no safety numbers exposed to the interface at all"

    assumed = [r for r in rows if r["provenance"] == "ASSUMED"]
    assert assumed, "this test proves nothing if none of them are unevidenced"
    for row in assumed:
        assert row["basis"].strip(), f"{row['rule']} is ASSUMED and states no assumption"
        assert "NO EVIDENCE FOUND" in row["basis"], (
            f"{row['rule']} does not say plainly that no evidence was found"
        )
