"""When-to-seek-care wording is selected from red_flags.yaml, never written by a model.

This was the single least checked thing this system put in front of a person, and the one
most likely to make them act. A live run produced:

    "Seek care if fever persists beyond 72 hours or exceeds 103 degrees F (39.4 C)"

Both thresholds came out of the model. They happen to sit near mainstream advice, which is
luck rather than sourcing, and is exactly why this class of error survives a read-through.

Breaking one of these tests means either that the model can write this text again, or that
a sentence is being shown that no reviewed file contains.
"""

from __future__ import annotations

import pytest
import yaml

from wha.agent.nodes import WriteOutcomeResponse
from wha.models import Disposition
from wha.safety.output_checks import (
    default_escalation_criteria,
    select_escalation_criteria,
)
from wha.safety.rules import load_red_flags


def reviewed_sentences() -> set[str]:
    """Every care-pathway sentence that exists in red_flags.yaml, normalised."""
    raw = yaml.safe_load(open("data/knowledge/red_flags.yaml", encoding="utf-8"))
    out: set[str] = set()
    for rule in raw["tier_a"] + raw.get("vitals", []):
        if rule.get("guidance"):
            out.add(" ".join(rule["guidance"].split()))
    for rule in raw["tier_b"]:
        if rule.get("guidance"):
            out.add(" ".join(rule["guidance"].split()))
    out.add(" ".join(raw["tier_b_guidance"].split()))
    for line in raw["outcome_guidance"]["default"]:
        out.add(" ".join(line.split()))
    return out


@pytest.mark.parametrize("disposition", list(Disposition))
def test_every_selected_line_exists_in_the_reviewed_file(disposition: Disposition) -> None:
    """Nothing is composed. Every line is a string a person can find in red_flags.yaml."""
    reviewed = reviewed_sentences()
    for flags in ([], ["rf_chest_pain"], ["rf_fever"], ["rf_rhr_extreme_high"]):
        selected = select_escalation_criteria(disposition, flags)
        for line in selected:
            assert " ".join(line.split()) in reviewed, (
                f"{disposition.value} with {flags} produced a line that is in no "
                f"reviewed file: {line!r}"
            )


@pytest.mark.parametrize("disposition", list(Disposition))
def test_selection_is_never_empty(disposition: Disposition) -> None:
    """An empty list used to raise inside a node that does not catch it, killing the episode."""
    assert select_escalation_criteria(disposition, [])


def test_the_rule_that_fired_is_quoted_first() -> None:
    """A person told to seek care should read the reason before the general boundary."""
    selected = select_escalation_criteria(Disposition.ESCALATED, ["rf_chest_pain"])
    chest_pain = next(r for r in load_red_flags().tier_a if r.id == "rf_chest_pain")
    assert selected[0] == chest_pain.guidance
    # The general lines still follow, so the boundary is never dropped.
    for line in default_escalation_criteria():
        assert line in selected


def test_a_benign_outcome_still_states_the_boundary() -> None:
    """The conclusion a person is most likely to act on by doing nothing needs it most."""
    selected = select_escalation_criteria(Disposition.LIKELY_BENIGN, [])
    assert selected == default_escalation_criteria()
    assert any("995" in line for line in selected)


def test_lines_are_not_repeated() -> None:
    """A tier B hit must not print the same sentence twice."""
    selected = select_escalation_criteria(Disposition.LIKELY_ILLNESS, ["rf_fever", "rf_body_aches"])
    assert len(selected) == len(set(selected))


def test_the_model_cannot_write_this_field_any_more() -> None:
    """The field is gone from the response schema, so there is nothing left to guard."""
    assert "escalation_criteria" not in WriteOutcomeResponse.model_fields

    # A model that emits it anyway is ignored rather than trusted.
    response = WriteOutcomeResponse.model_validate(
        {
            "observation": "Two raised nights.",
            "escalation_criteria": ["Seek care if fever exceeds 103 degrees F (39.4 C)"],
        }
    )
    assert not hasattr(response, "escalation_criteria")


def test_the_default_lines_live_in_the_knowledge_file_not_in_python() -> None:
    """They were a Python list. They now sit beside the rules they summarise."""
    from_yaml = load_red_flags().outcome_guidance.default
    assert from_yaml, "red_flags.yaml has no outcome_guidance.default"
    assert default_escalation_criteria() == list(from_yaml)
