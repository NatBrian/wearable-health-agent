"""Unit tests for deterministic red flag rules (tiers A and B, vitals, negation guards)."""

from pathlib import Path

import pytest

from wha.errors import ConfigError
from wha.models import BaselineRung
from wha.safety import check_red_flags_deterministic, load_red_flags


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
