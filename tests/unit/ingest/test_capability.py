"""Tests for the device capability report.

The case that matters is the second one: a person whose watch records more than the
developer's. Before this existed, their extra channels were stored and then silently
ignored, with nothing anywhere telling them so.
"""

from wha.ingest.capability import (
    RECOGNISED_KEYS,
    describe_payload,
    format_report,
)

# Shaped as the live bridge returns it for a device populating seven types.
OBSERVED_PAYLOAD = {
    "app_version": "1.9.17",
    "timestamp": "2026-09-02T15:47:57Z",
    "heart_rate": [{"time": "2026-09-01T00:00:00Z", "avg": 52, "min": 50, "max": 55}],
    "steps": [
        {
            "count": 6000,
            "start_time": "2026-08-31T16:00:00Z",
            "end_time": "2026-09-01T16:00:00Z",
        }
    ],
    "sleep": [
        {
            "session_end_time": "2026-09-01T00:00:00Z",
            "duration_seconds": 20000,
            "stages": [
                {
                    "stage": "DEEP",
                    "start_time": "2026-08-31T18:00:00Z",
                    "end_time": "2026-08-31T19:00:00Z",
                }
            ],
        }
    ],
    "exercise": [
        {
            "type": "running",
            "start_time": "2026-08-31T10:00:00Z",
            "end_time": "2026-08-31T11:00:00Z",
        }
    ],
    "oxygen_saturation": [{"percentage": 94.0, "time": "2026-08-31T19:39:00Z"}],
    "distance": [
        {
            "meters": 4210.0,
            "start_time": "2026-08-31T16:00:00Z",
            "end_time": "2026-09-01T16:00:00Z",
        }
    ],
    "total_calories": [
        {
            "calories": 2180.0,
            "start_time": "2026-08-31T16:00:00Z",
            "end_time": "2026-09-01T16:00:00Z",
        }
    ],
}


def test_separates_what_decides_from_what_is_merely_stored() -> None:
    """A channel that cannot move the belief must not be reported as if it could."""
    report = describe_payload(OBSERVED_PAYLOAD)

    assert set(report.used_in_decision) == {"heart_rate", "steps", "sleep", "exercise"}
    assert set(report.stored_only) == {"oxygen_saturation", "distance", "total_calories"}
    assert report.unrecognised == []


def test_names_channels_a_richer_device_sends_that_we_do_not_parse() -> None:
    """The whole point: another person's watch may send more than this developer's.

    Heart rate variability, respiratory rate and skin temperature are the channels the
    research corpus calls the strongest published feature set for illness detection. A
    device sending them must not have that pass unremarked.
    """
    richer = dict(OBSERVED_PAYLOAD)
    richer["heart_rate_variability"] = [{"heartRateVariabilityMillis": 42.0}]
    richer["respiratory_rate"] = [{"rate": 14.2}]
    richer["skin_temperature"] = [{"deltas": [0.3]}]

    report = describe_payload(richer)

    assert set(report.unrecognised) == {
        "heart_rate_variability",
        "respiratory_rate",
        "skin_temperature",
    }
    assert report.has_unused_data

    rendered = format_report(report)
    assert "does not parse" in rendered
    assert "heart_rate_variability" in rendered
    # The reader must be told the data is recoverable, not discarded.
    assert "raw payload is kept" in rendered


def test_empty_channels_are_not_reported_as_provided() -> None:
    """A key present but empty means the device sent nothing, not that it supports it."""
    report = describe_payload({"heart_rate": [], "steps": [{"count": 1}]})

    assert report.provided == ["steps"]
    assert "heart_rate" not in report.provided


def test_structural_keys_are_not_treated_as_health_data() -> None:
    """app_version and timestamp describe the payload, not the person."""
    report = describe_payload(OBSERVED_PAYLOAD)

    assert "app_version" not in report.provided
    assert "timestamp" not in report.provided


def test_recognised_keys_match_the_normaliser() -> None:
    """The report must describe what the normaliser actually parses.

    If these drift apart the report becomes another confidently wrong description of the
    system, which is the failure this whole exercise removed.
    """
    from wha.ingest.base import normalise

    richer = dict(OBSERVED_PAYLOAD)
    norm = normalise("me", richer)

    parsed_something = {
        "heart_rate": bool(norm.heart_rate_samples),
        "steps": bool(norm.step_buckets),
        "sleep": bool(norm.sleep_stages),
        "exercise": bool(norm.exercise_sessions),
        "oxygen_saturation": bool(norm.oxygen_saturation_samples),
        "distance": bool(norm.distance_buckets),
        "total_calories": bool(norm.calorie_buckets),
    }

    assert set(parsed_something) == set(RECOGNISED_KEYS)
    for key, parsed in parsed_something.items():
        assert parsed, f"capability claims '{key}' is recognised but normalise ignored it"
