"""The phone's job intervals must match the PC scheduler's, or the two systems drift
apart silently. Reads both sides from source: no shared constant is possible across
the Kotlin/Python boundary, so a test holds them together instead."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _kotlin_const(name: str) -> int:
    source = (ROOT / "android/app/src/main/java/dev/wha/app/jobs/Jobs.kt").read_text(
        encoding="utf-8"
    )
    match = re.search(rf"const val {name} = (\d+)L", source)
    assert match, f"{name} not found in Jobs.kt"
    return int(match.group(1))


def test_ingest_and_tick_intervals_match_the_pc_scheduler() -> None:
    scheduler = (ROOT / "src/wha/service/scheduler.py").read_text(encoding="utf-8")
    assert "IntervalTrigger(minutes=30)" in scheduler
    assert "IntervalTrigger(minutes=15)" in scheduler
    assert _kotlin_const("INGEST_MINUTES") == 30
    assert _kotlin_const("TICK_MINUTES") == 15


def test_nightly_interval_matches_the_pc_constant() -> None:
    constants = (ROOT / "src/wha/constants.py").read_text(encoding="utf-8")
    match = re.search(r"NIGHTLY_RESCORE_INTERVAL_HOURS\s*=\s*(\d+)", constants)
    assert match, "NIGHTLY_RESCORE_INTERVAL_HOURS not found in constants.py"
    assert _kotlin_const("NIGHTLY_HOURS") == int(match.group(1))
