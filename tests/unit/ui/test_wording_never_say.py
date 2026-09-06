"""The interface must not say what the system forbids the model from saying.

`red_flags.yaml` carries a `never_say` list, and the phrase filter runs on what the model
writes. It does not run on the interface's own strings, and the Today page shipped
"Probably nothing to worry about" as the label for a benign conclusion, with "nothing to
worry about" sitting on that list.

The failure mode is worth naming: a rule that applies to one source of text and not to the
other is a rule that reads as universal and is not.
"""

from __future__ import annotations

import json
import re
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

    from wha.ui.explain import TEXT

    for key, sentence in TEXT.items():
        lowered = sentence.lower()
        for banned in forbidden:
            if banned in lowered:
                offenders.append(f"explain.TEXT[{key}]: {banned!r} in {sentence!r}")

    assert not offenders, "the interface says what the model is forbidden to say:\n" + "\n".join(
        offenders
    )


def test_the_sweep_actually_covers_the_copy_module() -> None:
    """A sweep that reads an empty table passes and proves nothing.

    The four phrase tables above are being retired as the screens are rewritten. If this
    sweep silently ended up checking nothing, every forbidden phrase in the interface
    would pass unnoticed, so the size of what it reads is asserted rather than assumed.
    """
    from wha.ui.explain import TEXT

    assert len(TEXT) > 30, "explain.TEXT is smaller than the interface it is meant to cover"


def test_the_record_does_not_say_from_the_your_watch_source() -> None:
    """Ingest lines are read by a person, so the sentence has to be a sentence.

    `record_ingest` takes a phrase a caller has already written for a reader ("your watch",
    "simulated data") and used to wrap it in "the ... source", which produced "arrived from
    the your watch source" on every ingest entry of the record. Found by reading the Audit
    page, which is the only place this string is ever seen.
    """
    import sqlite3

    from wha.audit.monitor import record_ingest
    from wha.db.migrations import apply_schema

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    apply_schema(conn)
    conn.execute(
        "INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc) "
        "VALUES (?, ?, ?, ?, ?)",
        ("sub_wording", "Wording", "live", "Asia/Singapore", "2026-09-05T00:00:00Z"),
    )
    conn.commit()

    for phrase in ("your watch", "simulated data"):
        record_ingest(conn, "sub_wording", 9785, phrase, f"2026-09-05T0{len(phrase) % 9}:00:00Z")

    summaries = [
        json.loads(r["output_json"])["summary"]
        for r in conn.execute(
            "SELECT output_json FROM audit_events WHERE operation = 'ingest' ORDER BY rowid"
        )
    ]
    assert summaries, "no ingest entry was written, so this test proves nothing"

    for summary in summaries:
        assert "the your" not in summary, summary
        assert "the simulated data source" not in summary, summary
        assert summary.startswith("9785 heart rate samples arrived from "), summary
        assert summary.endswith("."), summary


def test_no_screen_or_constant_quotes_a_superseded_alert_rate() -> None:
    """The Audit page told the user a number the repository had already retracted.

    "once every 3.6 weeks" is 1/0.272, the alert rate under the LOOSER persistence rule
    that item 8 removed. The measured rate under the published two-consecutive-RED rule is
    0.203 per person-week, one investigation every 4.9 weeks, and that is what
    docs/detection-results.json and data/cohort/report.txt say. The figure survived in
    constants.py twice and in the Audit page's own prose, so a person reading "how often
    will this interrupt me" was given a retracted number.

    Asserted against the published JSON rather than a literal, so this fails if either
    side moves.
    """
    import json as _json
    from pathlib import Path as _Path

    repo = _Path(__file__).resolve().parents[3]
    results = _json.loads((repo / "docs" / "detection-results.json").read_text(encoding="utf-8"))
    weeks = results["alert_burden"]["wha_clock"]["one_every_weeks"]
    current = f"{weeks:.1f} weeks"
    superseded = f"{results['alert_burden']['nightsignal']['one_every_weeks']:.1f} weeks"

    searched = list((repo / "src" / "wha").rglob("*.py"))
    assert searched, "found no source to search"

    hits = []
    for path in searched:
        text = path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            if "weeks" not in line:
                continue
            for m in re.finditer(r"every (\d\.\d) weeks", line):
                if f"{m.group(1)} weeks" not in (current, superseded):
                    hits.append(f"{path.relative_to(repo)}:{i}: {line.strip()[:90]}")

    assert not hits, (
        f"an alert rate other than the published {current} is quoted in the code:\n  "
        + "\n  ".join(hits)
    )
