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

from pathlib import Path

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
    raw = yaml.safe_load(Path("data/knowledge/red_flags.yaml").read_text(encoding="utf-8"))
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


def test_the_two_reassurance_lists_do_not_drift_apart() -> None:
    """`never_say` in the YAML and FALSE_REASSURANCE_PHRASES in code must agree.

    Item 17 asked for "that's reassuring" to be added, because the model wrote it straight
    into a live chest pain reply with no amber marker. It was added to neither list, so the
    exact phrase the item quotes went on passing the deterministic filter. It is not an
    all-clear in form, which is why a list built from all-clear phrasings missed it, and
    why a person reads it as one anyway.
    """
    from wha.safety.output_checks import FALSE_REASSURANCE_PHRASES
    from wha.safety.rules import load_red_flags

    never_say = {p.lower() for p in load_red_flags().always["never_say"]}
    in_code = {p.lower() for p in FALSE_REASSURANCE_PHRASES}

    assert "that's reassuring" in never_say
    assert "that's reassuring" in in_code
    assert not (never_say - in_code), (
        "phrases the knowledge file forbids that the code filter does not catch: "
        f"{sorted(never_say - in_code)}"
    )


def test_the_oxygen_thresholds_are_not_credited_to_who() -> None:
    """A specific numeric threshold credited to the wrong body is as bad as inventing it.

    92 and 94 percent are NHS England's COVID Oximetry @home levels, with the upper bound
    from the British Thoracic Society. WHO's January 2021 guidance recommends USING home
    pulse oximetry and publishes no such numbers, so a reader who followed the old citation
    would have found nothing.

    docs/KNOWLEDGE-CHANGELOG.md recorded the correction on 5 September 2026 while the
    original sentence was still standing, in the present tense, 28 lines above its own
    retraction in the same YAML file, and in the docstring of the rule that applies it.
    """
    import re
    from pathlib import Path

    repo = Path(__file__).resolve().parents[3]
    targets = [
        repo / "data" / "knowledge" / "triage_rules.yaml",
        repo / "src" / "wha" / "safety" / "rules.py",
        repo / "src" / "wha" / "safety" / "triage.py",
    ]

    offenders = []
    for path in targets:
        if not path.exists():
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            # "NOT WHO" and similar corrections are the point, so only flag lines that
            # present WHO as the source of the levels.
            if re.search(r"WHO guidance[, ]", line) and "NOT WHO" not in line:
                offenders.append(f"{path.relative_to(repo)}:{i}: {line.strip()[:80]}")

    assert not offenders, "the levels are still credited to WHO:\n  " + "\n  ".join(offenders)


def test_the_leading_cause_selects_its_own_wording() -> None:
    """Item 2 asked for selection "from the disposition, the triggered flags AND the top of
    the differential", with "infection leading with a reported fever selects the tier B
    fever wording". The differential was never passed, so that half did not exist.

    It mattered less than it looks, because the second default line is itself the fever
    wording, but a selection the plan describes and the code does not do is still a
    selection that does not happen. The route also had a second block: `triggered_flags` is
    written in exactly one place and only inside the `if safety.escalate` branch, so a tier
    B symptom that never met its persistence rule never reached the state at all.
    """
    from wha.safety.output_checks import CAUSE_TO_TIER_B

    plain = select_escalation_criteria(Disposition.LIKELY_ILLNESS)
    led = select_escalation_criteria(Disposition.LIKELY_ILLNESS, leading_cause="infection")

    assert len(led) > len(plain), "the leading cause added nothing"
    assert any("See a doctor today." == line for line in led)

    # It may only ADD, and only wording that already exists in the file.
    assert set(plain) <= set(led), "the leading cause removed a line"
    sentences = reviewed_sentences()
    for line in led:
        assert " ".join(line.split()) in sentences, f"not from red_flags.yaml: {line!r}"

    # An unmapped cause changes nothing, rather than guessing at a sign.
    assert select_escalation_criteria(Disposition.LIKELY_ILLNESS, leading_cause="stress") == plain
    assert "stress" not in CAUSE_TO_TIER_B


def test_the_care_pathway_sentences_can_be_retrieved_and_cited() -> None:
    """Item 2 moved these into red_flags.yaml "so the corpus can cite it", and no generator
    read them.

    They are the most action-guiding text the system produces, attached to every outcome
    including LIKELY_BENIGN, and they were the only care guidance in the system that could
    not be retrieved. The agent could cite the tier A list, the tier B list and the vitals
    bounds, and not the two sentences a person actually reads at the end.
    """
    from wha.retrieve.knowledge_docs import generate_layer_3_escalation_docs

    docs = {d.doc_id: d for d in generate_layer_3_escalation_docs()}
    assert "escalation_outcome_guidance" in docs, (
        "the outcome guidance is still absent from the corpus: " + ", ".join(sorted(docs))
    )

    passage = docs["escalation_outcome_guidance"]
    for line in default_escalation_criteria():
        assert line in passage.text, f"missing from the retrievable passage: {line!r}"

    assert not passage.title.startswith("rf_")
    assert passage.metadata.get("topic") == "escalation"
