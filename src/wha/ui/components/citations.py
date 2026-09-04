"""Naming a passage's source on screen, from the labels the API serves.

The labels are constants, so `/config` carries them and this module never imports below
the API. They are not duplicated here: a second copy would drift, and the phone and the
dashboard disagreeing about who wrote a passage is the defect this replaced.
"""

from wha.ui.components.api import config


def source_label(source_id: str) -> str:
    """A human name for where a passage came from. Falls back to the repository."""
    prefixes: dict[str, str] = config().get("SOURCE_LABEL_PREFIXES", {})
    for prefix, label in prefixes.items():
        if source_id.startswith(prefix):
            return label
    return str(config().get("SOURCE_LABEL_FALLBACK", "this repository's own knowledge"))


def is_external(source_id: str) -> bool:
    """True when the passage is fetched text rather than something rendered here."""
    return source_id.startswith(str(config().get("EXTERNAL_SOURCE_PREFIX", "medlineplus")))


def medlineplus_label() -> str:
    """The credit the licence requires, in the words the constant carries."""
    return str(config().get("MEDLINEPLUS_LABEL", "MedlinePlus, National Library of Medicine"))


def attribution_note() -> str:
    """Why an external passage carries a credit, shown wherever one is."""
    return str(config().get("ATTRIBUTION_NOTE", ""))
