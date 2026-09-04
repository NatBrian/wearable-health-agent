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
