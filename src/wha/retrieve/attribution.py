"""Naming the source a quoted passage came from, in words rather than in an identifier.

The strings themselves live in :mod:`wha.constants`, so `/config` serves them and the
dashboard reads them over HTTP like every other public constant. This module is what the
service and Telegram paths use, where there is no HTTP hop to make.

The reason both need it: a MedlinePlus passage arrived on a real phone labelled
`Sources: Fever`. A topic title is not a credit, and the licence is attribution-only.
"""

from wha.constants import (
    ATTRIBUTION_NOTE,
    EXTERNAL_SOURCE_PREFIX,
    MEDLINEPLUS_LABEL,
    SOURCE_LABEL_FALLBACK,
    SOURCE_LABEL_PREFIXES,
)


def source_label(source_id: str) -> str:
    """A human name for where a passage came from. Falls back to the repository."""
    for prefix, label in SOURCE_LABEL_PREFIXES.items():
        if source_id.startswith(prefix):
            return label
    return SOURCE_LABEL_FALLBACK


def is_external(source_id: str) -> bool:
    """True when the passage is fetched text rather than something rendered here."""
    return source_id.startswith(EXTERNAL_SOURCE_PREFIX)


__all__ = [
    "ATTRIBUTION_NOTE",
    "MEDLINEPLUS_LABEL",
    "is_external",
    "source_label",
]
