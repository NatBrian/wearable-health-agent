"""Naming the source of a quoted passage, which the MedlinePlus licence requires."""

from wha.ui.components.citations import is_external, source_label


def test_medlineplus_passages_name_the_library_not_just_an_identifier() -> None:
    """The licence is attribution-only, so the identifier alone is not attribution."""
    assert source_label("medlineplus_4744") == "MedlinePlus, National Library of Medicine"
    assert is_external("medlineplus_4744")


def test_authored_passages_are_distinguishable_from_fetched_ones() -> None:
    """A person reading advice needs to know whether a passage is a rule about them.

    General background about a condition and a safety rule this system applies to them
    look identical when both are rendered as a title and a quote.
    """
    assert source_label("escalation_rf_chest_pain") == "this system's safety rules"
    assert source_label("method_detection_thresholds") == "how this system measures you"
    assert source_label("confounder_alcohol").startswith("the evidence behind")
    assert not is_external("escalation_rf_chest_pain")


def test_an_unrecognised_source_is_still_attributed_somewhere() -> None:
    """A new corpus layer must not render as a bare identifier by default."""
    assert source_label("something_new") == "this repository's own knowledge"
