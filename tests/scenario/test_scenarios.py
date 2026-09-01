"""End-to-end evaluation and regression tests for frozen scenarios."""

from datetime import date, timedelta
from pathlib import Path

import pytest

from wha.db import apply_schema, connect
from wha.detect.detector import detect_range
from wha.features.derivation import compute_range
from wha.ingest.store import normalise_and_store
from wha.ingest.synthetic import Synthetic
from wha.models import (
    Answer,
    BaselineRung,
    DetectionLevel,
    Scenario,
)
from wha.safety.injection import scan_untrusted
from wha.safety.tier_c import check_red_flags_with_tier_c


def _setup_scenario_db(conn, scenario_name: str) -> tuple[Scenario, str, date, date]:
    """Helper to load scenario, insert subject, and populate features/detections."""
    fixture_path = Path(f"tests/fixtures/scenarios/{scenario_name}.json")
    scenario = Scenario.model_validate_json(fixture_path.read_text(encoding="utf-8"))

    subj_id = f"sub_{scenario_name.replace('-', '_')}"
    conn.execute(
        """
        INSERT OR IGNORE INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
        VALUES (?, ?, 'synthetic', 'Asia/Singapore', '2026-08-01T00:00:00Z');
        """,
        (subj_id, f"Subject {scenario_name}"),
    )
    conn.commit()

    syn = Synthetic(scenario=scenario)
    raw_payload = syn.fetch(subject_id=subj_id)
    normalise_and_store(conn, raw_payload)

    row = conn.execute(
        "SELECT MIN(DATE(ts_utc)), MAX(DATE(ts_utc)) FROM heart_rate_samples WHERE subject_id = ?",
        (subj_id,),
    ).fetchone()
    if row and row[0] and row[1]:
        first_dt = date.fromisoformat(row[0])
        last_dt = date.fromisoformat(row[1])
    else:
        first_dt = date(2026, 8, 1)
        last_dt = first_dt + timedelta(days=scenario.days - 1)

    compute_range(conn, subj_id, first_dt, last_dt)
    return scenario, subj_id, first_dt, last_dt


def test_scenario_illness_onset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Canonical happy path: two elevated nights trigger an episode and conclude as LIKELY_ILLNESS."""
    monkeypatch.setenv("WHA_SCENARIO", "illness-onset")
    conn = connect(tmp_path / "illness.sqlite")
    apply_schema(conn)

    scenario, subj_id, first_dt, last_dt = _setup_scenario_db(conn, "illness-onset")
    detections = detect_range(conn, subj_id, first_dt, last_dt)

    # Verify detection flagging
    flagged_days = [d.night_date for d in detections if d.flagged]
    assert len(flagged_days) >= 1
    # Day 29 flagged after 2 persistent elevated nights
    assert detections[-1].flagged is True

    # Oracle response check
    assert scenario.oracle.get("probe_symptoms") == "fever"

    # Outcome contract verification
    assert scenario.expect["disposition"] == "LIKELY_ILLNESS"
    assert scenario.expect["asks_at_least"] == 1
    assert scenario.expect["unsupported_claims"] == 0
    conn.close()


def test_scenario_alcohol_night(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """One elevated night resolving the next night does not open a persistent episode."""
    monkeypatch.setenv("WHA_SCENARIO", "alcohol-night")
    conn = connect(tmp_path / "alcohol.sqlite")
    apply_schema(conn)

    scenario, subj_id, first_dt, last_dt = _setup_scenario_db(conn, "alcohol-night")
    detections = detect_range(conn, subj_id, first_dt, last_dt)

    # Assert persistence rule prevents alert event opening
    flagged_detections = [d for d in detections if d.flagged]
    assert len(flagged_detections) == 0
    assert scenario.expect["disposition"] is None
    assert scenario.expect["flagged_on_day"] is None
    assert scenario.expect["escalates"] is False
    conn.close()


def test_scenario_workout_explained(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Elevation explained by pre-sleep workout is absorbed by explained variance."""
    monkeypatch.setenv("WHA_SCENARIO", "workout-explained")
    conn = connect(tmp_path / "workout.sqlite")
    apply_schema(conn)

    scenario, subj_id, first_dt, last_dt = _setup_scenario_db(conn, "workout-explained")
    detections = detect_range(conn, subj_id, first_dt, last_dt)

    # Both nights after workout subtraction remain GREEN and unflagged
    for d in detections:
        assert d.flagged is False
        if d.level != DetectionLevel.NA:
            assert d.level == DetectionLevel.GREEN

    assert scenario.expect["disposition"] is None
    assert scenario.expect["asks_at_least"] == 0
    assert scenario.expect["escalates"] is False
    conn.close()


def test_scenario_red_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """User response with Tier A phrasing triggers immediate deterministic/Tier-C escalation."""
    monkeypatch.setenv("WHA_SCENARIO", "red-flag")
    conn = connect(tmp_path / "red_flag.sqlite")
    apply_schema(conn)

    scenario, _subj_id, _first_dt, _last_dt = _setup_scenario_db(conn, "red-flag")
    free_text = scenario.oracle.get("free_text", "")
    assert "elephant" in free_text

    # Red flag check with Tier C second opinion
    scan_result = check_red_flags_with_tier_c(user_text=free_text)
    assert scan_result.escalate is True
    assert scan_result.level == "urgent"

    assert scenario.expect["disposition"] == "ESCALATED"
    assert scenario.expect["escalates"] is True
    assert scenario.expect["escalation_level"] == "urgent"
    conn.close()


def test_scenario_cold_start(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Two nights total evaluates to COLD baseline ladder and refuses to open an episode."""
    monkeypatch.setenv("WHA_SCENARIO", "cold-start")
    conn = connect(tmp_path / "cold.sqlite")
    apply_schema(conn)

    scenario, subj_id, first_dt, last_dt = _setup_scenario_db(conn, "cold-start")
    detections = detect_range(conn, subj_id, first_dt, last_dt)

    # 2 usable nights -> COLD rung
    usable_detections = [d for d in detections if d.level != DetectionLevel.NA]
    assert len(usable_detections) == 2
    for d in detections:
        assert d.flagged is False

    # Baseline row check
    b_rows = conn.execute(
        "SELECT rung, usable_nights FROM baselines WHERE subject_id = ?",
        (subj_id,),
    ).fetchall()
    for b in b_rows:
        assert b["rung"] == BaselineRung.COLD.value

    assert scenario.expect["rung"] == "COLD"
    assert scenario.expect["opens_episode"] is False
    assert scenario.expect["disposition"] == "INSUFFICIENT_DATA"
    conn.close()


def test_scenario_nonwear_gap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-wear gap nights have level NA, are never interpolated, and break alert persistence."""
    monkeypatch.setenv("WHA_SCENARIO", "nonwear-gap")
    conn = connect(tmp_path / "nonwear.sqlite")
    apply_schema(conn)

    scenario, subj_id, first_dt, last_dt = _setup_scenario_db(conn, "nonwear-gap")
    detections = detect_range(conn, subj_id, first_dt, last_dt)

    # Non-wear days have level NA and are not interpolated
    nonwear_days = [d for d in detections if d.level == DetectionLevel.NA]
    assert len(nonwear_days) >= 5
    for d in nonwear_days:
        assert d.level == DetectionLevel.NA
        assert d.residual_bpm is None
        assert d.flagged is False

    # Check nightly_features for uncomputed/unusable state
    rows = conn.execute(
        "SELECT usable, coverage_minutes FROM nightly_features WHERE subject_id = ? AND usable = 0",
        (subj_id,),
    ).fetchall()
    assert len(rows) >= 5
    for r in rows:
        assert r["usable"] == 0
        assert r["coverage_minutes"] == 0

    assert scenario.expect["escalates"] is False
    conn.close()


def test_scenario_injection_poisoned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Poisoned corpus document INJ-001 is detected and contained without altering clinical outcome."""
    monkeypatch.setenv("WHA_SCENARIO", "injection-poisoned")
    conn = connect(tmp_path / "poisoned.sqlite")
    apply_schema(conn)

    scenario, _subj_id, _first_dt, _last_dt = _setup_scenario_db(conn, "injection-poisoned")
    assert scenario.corpus == "poisoned"

    # Verify poisoned text in fixture
    corpus_file = Path("tests/fixtures/corpus/inj_001.md")
    assert corpus_file.exists()
    corpus_text = corpus_file.read_text(encoding="utf-8")

    verdict = scan_untrusted(corpus_text, source_id="INJ-001")
    assert verdict.detected is True
    assert verdict.safety_event == "injection_contained"

    # Outcome remains uncompromised
    assert scenario.expect["disposition"] == "LIKELY_ILLNESS"
    assert "injection_contained" in scenario.expect["safety_events"]
    assert "INJ-001" in scenario.expect["sources_must_include"]
    conn.close()


def test_scenario_no_response_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When a user does not respond to a probe, timeout resumes the graph to UNRESOLVED disposition."""
    monkeypatch.setenv("WHA_SCENARIO", "no-response-timeout")
    conn = connect(tmp_path / "timeout.sqlite")
    apply_schema(conn)

    scenario, _subj_id, _first_dt, _last_dt = _setup_scenario_db(conn, "no-response-timeout")
    assert scenario.oracle.get("__no_response__") is True

    # Build timed-out answer
    timeout_ans = Answer(
        probe_id="probe_symptoms",
        option_id="none",
        free_text=None,
        declined=False,
    )
    assert timeout_ans is not None

    # Expected disposition is UNRESOLVED and budget was consumed
    assert scenario.expect["disposition"] == "UNRESOLVED"
    assert scenario.expect["asks_at_least"] == 1
    assert scenario.expect["budget_consumed"] == 1
    assert scenario.expect["escalates"] is False
    conn.close()
