"""The film's words have rules, and a rule nothing checks is a preference.

`tools/demo_film/script.yaml` holds every caption and card in the demo film. Three of its
rules are the sort that quietly rot: no em-dashes anywhere (the repository forbids them and
a separate test already guards README.md), captions short enough to actually be read, and
no line that tells a viewer to discount what they are watching.

The last one deserves its reason written down. The film is a portfolio piece and a course
submission, and a recording that interrupts itself every ninety seconds to disclaim what is
on screen teaches the viewer to discount all of it. The limitations are not hidden: three
whole chapters are nothing but limitations, with the measurements behind them, and the
closing card states the provenance of the data in one sentence. Said once, with evidence,
is disclosure. Said constantly, in passing, is noise.
"""

from pathlib import Path

import pytest
import yaml

SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "demo_film" / "script.yaml"

# Phrases that undercut the film mid-sentence rather than disclosing anything. The
# closing card is exempt: it is where the provenance sentence belongs.
# Deliberately narrow. An earlier version banned the word "pretend" and flagged two lines
# that mean the OPPOSITE of undercutting: "the screen says so, rather than pretending" and
# "the system tracks it and does not pretend to know". A rule that catches honest sentences
# because they contain an honest word is a worse rule than none.
UNDERCUTS = (
    "just a demo",
    "only a demo",
    "only a simulation",
    "just a simulation",
    "not real data",
    "fake data",
    "this is mock",
    "mock data",
)


@pytest.fixture(scope="module")
def script() -> dict:
    if not SCRIPT.is_file():
        pytest.skip("the film script has not been written yet")
    return yaml.safe_load(SCRIPT.read_text(encoding="utf-8"))


def _chapters(script: dict) -> list[dict]:
    return [c for act in script.get("acts", []) for c in act.get("chapters", [])]


def _all_text(chapter: dict) -> list[tuple[str, str]]:
    """Every human-readable string in a chapter, tagged with where it came from."""
    out: list[tuple[str, str]] = []
    where = f"chapter {chapter.get('id')}"
    out.append((f"{where} title", chapter.get("title", "")))
    for key in ("captions", "captions_after"):
        for i, line in enumerate(chapter.get(key) or []):
            out.append((f"{where} {key}[{i}]", line))
    card = chapter.get("card") or {}
    for key in ("heading", "body", "footer"):
        if card.get(key):
            out.append((f"{where} card.{key}", card[key]))
    return out


def test_the_script_has_no_em_dashes_or_en_dashes(script):
    """The same rule the rest of this repository lives under, applied to what is on screen."""
    offenders = [
        f"{where}: {text.strip()[:70]}"
        for chapter in _chapters(script)
        for where, text in _all_text(chapter)
        if "—" in text or "–" in text
    ]
    assert not offenders, "em-dash or en-dash in the film script:\n" + "\n".join(offenders)


def test_no_caption_is_longer_than_two_lines(script):
    """A third line is not read. It is decoration that hides the second one."""
    offenders = []
    for chapter in _chapters(script):
        for key in ("captions", "captions_after"):
            for i, line in enumerate(chapter.get(key) or []):
                if len(line) > 110:
                    offenders.append(f"chapter {chapter['id']} {key}[{i}]: {len(line)} chars")
    assert not offenders, "captions too long to read at speed:\n" + "\n".join(offenders)


def test_nothing_on_screen_tells_the_viewer_to_discount_what_they_are_watching(script):
    """Disclosure is a chapter with evidence, not an aside that undermines the frame."""
    chapters = _chapters(script)
    closing = max(c.get("id", 0) for c in chapters)
    offenders = [
        f"{where}: {phrase}"
        for chapter in chapters
        if chapter.get("id") != closing
        for where, text in _all_text(chapter)
        for phrase in UNDERCUTS
        if phrase in text.lower()
    ]
    assert not offenders, (
        "these undercut the film mid-sentence. Provenance belongs on the closing card, "
        "and limitations belong in the chapters that are about limitations:\n"
        + "\n".join(offenders)
    )


def test_the_closing_card_states_where_the_data_came_from(script):
    """Said once, plainly, at the end. Not repeated, and not omitted either."""
    closing = max(_chapters(script), key=lambda c: c.get("id", 0))
    footer = (closing.get("card") or {}).get("footer", "").lower()
    assert "watch data" in footer and "simulated" in footer, (
        "the closing card must say which nights are real and which are simulated, in one "
        f"sentence. It currently says: {footer!r}"
    )


def test_every_chapter_has_something_to_show(script):
    """A chapter with no card and no captions is a title with nothing behind it."""
    empty = [
        chapter.get("id")
        for chapter in _chapters(script)
        if not chapter.get("card") and not chapter.get("captions")
    ]
    assert not empty, f"chapters with neither a card nor captions: {empty}"
