"""Every limitation the app creates is disclosed, and names the screen that shows it."""

from pathlib import Path

DISCLOSURES = Path("docs/DISCLOSURES.md").read_text(encoding="utf-8")

REQUIRED = {
    "no model provider configured": "Today",
    "general health information is not yet available": "Today",
    "provider unreachable": "Today",
    "webhook unreachable": "Today",
    "replay pacing": "Record",
    "webhook app serves without authentication": "Settings",
    "background work may be delayed by the phone": "Settings",
    "escalation stays until acknowledged": "Settings",
}


def test_every_android_limitation_is_disclosed_with_its_screen() -> None:
    lowered = DISCLOSURES.lower()
    missing = [k for k in REQUIRED if k not in lowered]
    assert not missing, f"docs/DISCLOSURES.md lacks: {missing}"
    for phrase, screen in REQUIRED.items():
        start = lowered.index(phrase)
        window = DISCLOSURES[start : start + 600]
        assert screen in window, f"{phrase!r} does not name the {screen} screen within its entry"
