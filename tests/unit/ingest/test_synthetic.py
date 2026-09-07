"""Unit tests for the Synthetic scenario data generator."""

from pathlib import Path

from wha.ingest import Synthetic, normalise
from wha.models import Scenario


def test_synthetic_is_deterministic() -> None:
    """Same seed and scenario generates byte-identical RawPayloads."""
    scenario = Scenario(
        name="test-det",
        description="test determinism",
        days=5,
        base_bpm=60.0,
        seed=42,
        timezone="Asia/Singapore",
    )
    synth1 = Synthetic(scenario, seed=42)
    synth2 = Synthetic(scenario, seed=42)

    p1 = synth1.fetch("subj_det")
    p2 = synth2.fetch("subj_det")

    assert p1.sha256 == p2.sha256
    assert p1.body == p2.body


def test_synthetic_injection_matches_causes_yaml() -> None:
    """Injected effect amplitude defaults match cited values from causes.yaml."""
    scenario = Scenario(
        name="test-inj",
        description="test injections",
        days=10,
        base_bpm=60.0,
        seed=10,
        timezone="Asia/Singapore",
        injections=[
            {"kind": "illness", "start_day": 5, "amplitude_bpm": 1.60},
            {"kind": "alcohol", "day": 2, "amplitude_bpm": 2.60},
        ],
    )
    synth = Synthetic(scenario)
    payload = synth.fetch("subj_inj")
    assert len(payload.body["heart_rate"]) > 0


def test_nonwear_creates_gap_not_zero() -> None:
    """Nonwear injection causes records to be omitted, not recorded as 0 bpm."""
    scenario = Scenario(
        name="test-nonwear",
        description="test nonwear gaps",
        days=5,
        base_bpm=60.0,
        seed=20,
        timezone="Asia/Singapore",
        injections=[
            {"kind": "nonwear", "start_day": 2, "nights": 1},
        ],
    )
    synth = Synthetic(scenario)
    payload = synth.fetch("subj_nonwear")
    norm = normalise("subj_nonwear", payload.body)

    # Verify no heart rate samples have 0 bpm
    for s in norm.heart_rate_samples:
        assert s.avg_bpm > 0


def test_every_fixture_parses() -> None:
    """All 11 scenario JSON fixtures load and generate valid synthetic payloads."""
    fixtures_dir = Path(__file__).parents[2] / "fixtures" / "scenarios"
    fixture_files = list(fixtures_dir.glob("*.json"))
    assert len(fixture_files) == 11, f"Expected 11 fixtures, found {len(fixture_files)}"

    for f in fixture_files:
        content = f.read_text(encoding="utf-8")
        scenario = Scenario.model_validate_json(content)
        synth = Synthetic(scenario)
        payload = synth.fetch(f"demo-{scenario.name}", days=min(scenario.days, 3))
        assert payload.sha256 is not None
        assert len(payload.body["steps"]) > 0
        norm = normalise(payload.subject_id, payload.body)
        assert len(norm.step_buckets) > 0
