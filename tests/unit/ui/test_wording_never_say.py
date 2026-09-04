"""The interface must not say what the system forbids the model from saying.

`red_flags.yaml` carries a `never_say` list, and the phrase filter runs on what the model
writes. It does not run on the interface's own strings, and the Today page shipped
"Probably nothing to worry about" as the label for a benign conclusion, with "nothing to
worry about" sitting on that list.

The failure mode is worth naming: a rule that applies to one source of text and not to the
other is a rule that reads as universal and is not.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from wha.ui.components.wording import (
    DISPOSITION_PHRASES,
    EPISODE_STATE_PHRASES,
    LEVEL_PHRASES,
    RUNG_PHRASES,
)


def never_say() -> list[str]:
    raw = yaml.safe_load(Path("data/knowledge/red_flags.yaml").read_text(encoding="utf-8"))
    phrases = raw.get("always", {}).get("never_say", [])
    assert phrases, "red_flags.yaml has no never_say list to check against"
    return [p.lower() for p in phrases]


def test_no_interface_phrase_is_on_never_say() -> None:
    """Every label and explanation the dashboard ships, checked against the same list."""
    forbidden = never_say()
    offenders: list[str] = []

    for name, table in (
        ("DISPOSITION_PHRASES", DISPOSITION_PHRASES),
        ("LEVEL_PHRASES", LEVEL_PHRASES),
        ("EPISODE_STATE_PHRASES", EPISODE_STATE_PHRASES),
        ("RUNG_PHRASES", RUNG_PHRASES),
    ):
        for key, phrase in table.items():
            for field in (phrase.label, phrase.explanation):
                lowered = (field or "").lower()
                for banned in forbidden:
                    if banned in lowered:
                        offenders.append(f"{name}[{key}]: {banned!r} in {field!r}")

    assert not offenders, "the interface says what the model is forbidden to say:\n" + "\n".join(
        offenders
    )
