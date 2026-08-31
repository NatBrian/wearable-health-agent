"""Unit tests for the pure normalisation parser."""

import pytest

from wha.ingest import normalise


def test_normalise_matches_real_schema() -> None:
    """Payload matching real device schema parses into typed rows."""
    payload = {
        "app_version": "1.9.17",
        "timestamp": "2026-08-31T08:57:07Z",
        "steps": [
            {
                "count": 2594,
                "start_time": "2026-08-29T16:00:00Z",
                "end_time": "2026-08-30T16:00:00Z",
            }
        ],
        "heart_rate": [
            {
                "time": "2026-08-30T16:33:00Z",
                "avg": 90,
                "min": 85,
                "max": 95,
                "metadata": {"data_origin": "com.sec.android.app.shealth"},
            }
        ],
        "sleep": [],
        "exercise": [],
    }

    norm = normalise("subj_real", payload)
    assert len(norm.heart_rate_samples) == 1
    assert norm.heart_rate_samples[0].subject_id == "subj_real"
    assert norm.heart_rate_samples[0].avg_bpm == 90.0
    assert norm.heart_rate_samples[0].min_bpm == 85.0
    assert norm.heart_rate_samples[0].max_bpm == 95.0
    assert norm.heart_rate_samples[0].origin == "com.sec.android.app.shealth"
    assert norm.heart_rate_samples[0].ts_utc == "2026-08-30T16:33:00Z"

    assert len(norm.step_buckets) == 1
    assert norm.step_buckets[0].count == 2594
    assert norm.step_buckets[0].start_utc == "2026-08-29T16:00:00Z"
    assert norm.step_buckets[0].end_utc == "2026-08-30T16:00:00Z"


def test_normalise_handles_duplicate_app_version_key() -> None:
    """Raw JSON with repeated app_version key parses without error."""
    raw_json = """
    {
      "app_version": "1.9.16",
      "app_version": "1.9.17",
      "timestamp": "2026-08-31T08:57:07Z",
      "steps": [],
      "heart_rate": []
    }
    """
    norm = normalise("subj_dup", raw_json)
    assert len(norm.heart_rate_samples) == 0
    assert len(norm.step_buckets) == 0


def test_normalise_rejects_naive_timestamp() -> None:
    """Timestamps missing UTC offset or Z raise ValueError."""
    payload = {
        "heart_rate": [
            {
                "time": "2026-08-30 16:33:00",  # naive
                "avg": 70,
            }
        ]
    }
    with pytest.raises(ValueError, match="Naive timestamp not allowed"):
        normalise("subj_naive", payload)


def test_steps_are_daily_buckets() -> None:
    """Steps arrive in 24h buckets, producing 1 row per day rather than 1440."""
    payload = {
        "steps": [
            {
                "count": 8500,
                "start_time": "2026-08-29T16:00:00Z",
                "end_time": "2026-08-30T16:00:00Z",
            }
        ]
    }
    norm = normalise("subj_steps", payload)
    assert len(norm.step_buckets) == 1
    assert norm.step_buckets[0].count == 8500


def test_missing_sleep_and_exercise_is_normal() -> None:
    """Payloads omitting sleep and exercise parse cleanly with empty lists."""
    payload = {
        "heart_rate": [{"time": "2026-08-30T16:00:00Z", "avg": 65}],
        "steps": [],
    }
    norm = normalise("subj_optional", payload)
    assert len(norm.sleep_stages) == 0
    assert len(norm.exercise_sessions) == 0
    assert len(norm.heart_rate_samples) == 1


def test_implausible_hr_is_stored_not_dropped() -> None:
    """Implausible HR values (<25 or >220) are preserved by normalise for feature filtering."""
    payload = {
        "heart_rate": [
            {"time": "2026-08-30T16:00:00Z", "avg": 10},
            {"time": "2026-08-30T16:01:00Z", "avg": 250},
        ]
    }
    norm = normalise("subj_implausible", payload)
    assert len(norm.heart_rate_samples) == 2
    assert norm.heart_rate_samples[0].avg_bpm == 10.0
    assert norm.heart_rate_samples[1].avg_bpm == 250.0
