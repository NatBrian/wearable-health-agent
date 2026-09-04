"""Naming the source a quoted passage came from, in words rather than in an identifier.

A citation rendered as ``(medlineplus_4744#c0)`` is traceable but not readable, and the
MedlinePlus licence is attribution-only: the National Library of Medicine has to be named
wherever its text is shown, not implied by an identifier prefix. The same labelling also
tells a person at a glance whether they are reading general background about a condition
or a rule this system applies to them, which is the distinction that matters most when
the passage is sitting underneath a piece of health advice.
"""

MEDLINEPLUS_LABEL = "MedlinePlus, National Library of Medicine"

_PREFIX_LABELS: tuple[tuple[str, str], ...] = (
    ("medlineplus", MEDLINEPLUS_LABEL),
    ("escalation", "this system's safety rules"),
    ("method", "how this system measures you"),
    ("evidence", "the evidence behind a question it asks"),
    ("confounder", "the evidence behind a competing explanation"),
)


def source_label(source_id: str) -> str:
    """A human name for where a passage came from. Falls back to the repository."""
    for prefix, label in _PREFIX_LABELS:
        if source_id.startswith(prefix):
            return label
    return "this repository's own knowledge"


def is_external(source_id: str) -> bool:
    """True when the passage is fetched text rather than something authored here."""
    return source_id.startswith("medlineplus")


ATTRIBUTION_NOTE = (
    "Passages from MedlinePlus come from the National Library of Medicine and are used "
    "with attribution. They are general information about a condition, not about you, "
    "and say nothing about your own readings."
)
