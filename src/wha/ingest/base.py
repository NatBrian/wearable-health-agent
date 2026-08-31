"""DataSource protocol, normalised data shapes, and pure normalisation function."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

from wha.db.iso import to_iso
from wha.models import RawPayload

SLEEP_STAGE_MAP = {
    "AWAKE": "AWAKE",
    "LIGHT": "LIGHT",
    "DEEP": "DEEP",
    "REM": "REM",
}


@dataclass(frozen=True)
class NormalisedHeartRate:
    subject_id: str
    ts_utc: str
    avg_bpm: float
    min_bpm: float | None
    max_bpm: float | None
    origin: str | None


@dataclass(frozen=True)
class NormalisedStepBucket:
    subject_id: str
    start_utc: str
    end_utc: str
    count: int


@dataclass(frozen=True)
class NormalisedSleepStage:
    subject_id: str
    start_utc: str
    end_utc: str
    stage: str


@dataclass(frozen=True)
class NormalisedExerciseSession:
    subject_id: str
    start_utc: str
    end_utc: str
    kind: str | None


@dataclass(frozen=True)
class NormalisedData:
    heart_rate_samples: list[NormalisedHeartRate]
    step_buckets: list[NormalisedStepBucket]
    sleep_stages: list[NormalisedSleepStage]
    exercise_sessions: list[NormalisedExerciseSession]


class DataSource(Protocol):
    source_kind: Literal["live", "synthetic", "cohort"]

    def fetch(self, subject_id: str, days: int) -> RawPayload: ...


def _parse_iso_utc(ts_str: str) -> str:
    """Validate and format ISO 8601 string to canonical UTC string.

    Raises ValueError if naive.
    """
    clean = ts_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(clean)
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError(f"Naive timestamp not allowed: {ts_str}")
    return to_iso(dt.astimezone(UTC))


def normalise(subject_id: str, payload_input: dict[str, Any] | str) -> NormalisedData:
    """Pure function to convert raw bridge JSON payload into typed domain rows.

    Performs no IO. Rejects naive timestamps. Preserves implausible heart rates for
    feature layer filtering.
    """
    if isinstance(payload_input, str):
        payload = json.loads(payload_input)
    else:
        payload = payload_input

    # 1. Heart rate samples
    hr_samples: list[NormalisedHeartRate] = []
    for item in payload.get("heart_rate", []):
        ts_utc = _parse_iso_utc(item["time"])
        avg_bpm = float(item["avg"])
        min_bpm = float(item["min"]) if item.get("min") is not None else None
        max_bpm = float(item["max"]) if item.get("max") is not None else None
        metadata = item.get("metadata")
        origin = metadata.get("data_origin") if isinstance(metadata, dict) else None

        hr_samples.append(
            NormalisedHeartRate(
                subject_id=subject_id,
                ts_utc=ts_utc,
                avg_bpm=avg_bpm,
                min_bpm=min_bpm,
                max_bpm=max_bpm,
                origin=origin,
            )
        )

    # 2. Daily step buckets
    step_buckets: list[NormalisedStepBucket] = []
    for item in payload.get("steps", []):
        start_utc = _parse_iso_utc(item["start_time"])
        end_utc = _parse_iso_utc(item["end_time"])
        count = int(item["count"])

        step_buckets.append(
            NormalisedStepBucket(
                subject_id=subject_id,
                start_utc=start_utc,
                end_utc=end_utc,
                count=count,
            )
        )

    # 3. Sleep stages
    sleep_stages: list[NormalisedSleepStage] = []
    for item in payload.get("sleep", []):
        start_utc = _parse_iso_utc(item["start_time"])
        end_utc = _parse_iso_utc(item["end_time"])
        raw_stage = str(item.get("stage", "")).upper()
        stage = SLEEP_STAGE_MAP.get(raw_stage, raw_stage)

        sleep_stages.append(
            NormalisedSleepStage(
                subject_id=subject_id,
                start_utc=start_utc,
                end_utc=end_utc,
                stage=stage,
            )
        )

    # 4. Exercise sessions
    exercise_sessions: list[NormalisedExerciseSession] = []
    for item in payload.get("exercise", []):
        start_utc = _parse_iso_utc(item["start_time"])
        end_utc = _parse_iso_utc(item["end_time"])
        kind = str(item["kind"]) if item.get("kind") is not None else None

        exercise_sessions.append(
            NormalisedExerciseSession(
                subject_id=subject_id,
                start_utc=start_utc,
                end_utc=end_utc,
                kind=kind,
            )
        )

    return NormalisedData(
        heart_rate_samples=hr_samples,
        step_buckets=step_buckets,
        sleep_stages=sleep_stages,
        exercise_sessions=exercise_sessions,
    )
