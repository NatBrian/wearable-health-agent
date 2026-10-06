from wha.service.belief import get_safety_rule_provenance


def test_overnight_oxygen_disclosures_include_the_source_and_non_reassurance_limit() -> None:
    """A spot sample must not hide the scope or population behind the overnight rule."""
    rows = [row for row in get_safety_rule_provenance() if row["rule"] == "oxygen_threshold"]
    assert any("overnight readings" in row["number"] for row in rows)
    assert any("COVID-19" in row["basis"] for row in rows)
    assert any("all-clear" in row["basis"] for row in rows)


def test_chest_pain_rule_source_and_age_gate_reach_the_interface() -> None:
    row = next(row for row in get_safety_rule_provenance() if row["rule"] == "marburg_heart_score")
    assert row["provenance"] == "CITED"
    assert row["minimum_age_years"] == 35
    assert "CMAJ" in row["basis"]
    assert "Br J Gen Pract" in row["basis"]
