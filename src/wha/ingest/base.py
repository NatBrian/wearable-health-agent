"""DataSource protocol, normalised data shapes, and pure normalisation function."""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

from wha.db.iso import to_iso
from wha.models import RawPayload

SLEEP_STAGE_MAP = {
    "AWAKE": "AWAKE",
    "LIGHT": "LIGHT",
    "DEEP": "DEEP",
    "REM": "REM",
    "STAGE_TYPE_AWAKE": "AWAKE",
    "STAGE_TYPE_LIGHT": "LIGHT",
    "STAGE_TYPE_DEEP": "DEEP",
    "STAGE_TYPE_REM": "REM",
    "STAGE_TYPE_OUT_OF_BED": "AWAKE",
    "STAGE_TYPE_SLEEPING": "LIGHT",
    "1": "AWAKE",
    "2": "LIGHT",
    "3": "AWAKE",
    "4": "LIGHT",
    "5": "DEEP",
    "6": "REM",
    1: "AWAKE",
    2: "LIGHT",
    3: "AWAKE",
    4: "LIGHT",
    5: "DEEP",
    6: "REM",
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
class NormalisedOxygenSaturation:
    """A spot blood oxygen reading. The device sends these individually, not as a stream."""

    subject_id: str
    ts_utc: str
    percentage: float
    origin: str | None


@dataclass(frozen=True)
class NormalisedDistance:
    subject_id: str
    start_utc: str
    end_utc: str
    meters: float


@dataclass(frozen=True)
class NormalisedCalories:
    subject_id: str
    start_utc: str
    end_utc: str
    calories_kcal: float


@dataclass(frozen=True)
class NormalisedData:
    heart_rate_samples: list[NormalisedHeartRate]
    step_buckets: list[NormalisedStepBucket]
    sleep_stages: list[NormalisedSleepStage]
    exercise_sessions: list[NormalisedExerciseSession]
    # Verified present on the live bridge on 2026-09-02. Respiratory rate and skin
    # temperature are not returned by this device and are deliberately absent.
    oxygen_saturation_samples: list[NormalisedOxygenSaturation] = field(default_factory=list)
    distance_buckets: list[NormalisedDistance] = field(default_factory=list)
    calorie_buckets: list[NormalisedCalories] = field(default_factory=list)


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
    hr_raw = (
        payload.get("heart_rate")
        or payload.get("heartRate")
        or payload.get("heart_rate_records")
        or []
    )
    hr_samples: list[NormalisedHeartRate] = []
    for item in hr_raw:
        t_val = (
            item.get("time")
            or item.get("start_time")
            or item.get("startTime")
            or item.get("timestamp")
        )
        if not t_val:
            continue
        ts_utc = _parse_iso_utc(str(t_val))
        avg_bpm = float(
            item.get("avg")
            or item.get("bpm")
            or item.get("beats_per_minute")
            or item.get("value")
            or 0.0
        )
        min_bpm = float(item["min"]) if item.get("min") is not None else None
        max_bpm = float(item["max"]) if item.get("max") is not None else None
        metadata = item.get("metadata")
        origin = metadata.get("data_origin") if isinstance(metadata, dict) else item.get("origin")

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
    steps_raw = (
        payload.get("steps") or payload.get("step_buckets") or payload.get("steps_records") or []
    )
    step_buckets: list[NormalisedStepBucket] = []
    for item in steps_raw:
        st_val = item.get("start_time") or item.get("startTime")
        et_val = item.get("end_time") or item.get("endTime")
        if not st_val or not et_val:
            continue
        start_utc = _parse_iso_utc(str(st_val))
        end_utc = _parse_iso_utc(str(et_val))
        count = int(item.get("count") or item.get("steps") or 0)

        step_buckets.append(
            NormalisedStepBucket(
                subject_id=subject_id,
                start_utc=start_utc,
                end_utc=end_utc,
                count=count,
            )
        )

    # 3. Sleep stages
    sleep_raw = (
        payload.get("sleep") or payload.get("sleep_stages") or payload.get("sleep_sessions") or []
    )
    sleep_stages: list[NormalisedSleepStage] = []
    for item in sleep_raw:
        # Check if item contains nested stages (Health Connect SleepSessionRecord)
        nested_stages = item.get("stages") or item.get("stages_records")
        if isinstance(nested_stages, list) and nested_stages:
            for n_stg in nested_stages:
                st_val = n_stg.get("start_time") or n_stg.get("startTime")
                et_val = n_stg.get("end_time") or n_stg.get("endTime")
                if not st_val or not et_val:
                    continue
                start_utc = _parse_iso_utc(str(st_val))
                end_utc = _parse_iso_utc(str(et_val))
                raw_stage = str(n_stg.get("stage") or n_stg.get("stage_type") or "").upper()
                stage = SLEEP_STAGE_MAP.get(raw_stage, raw_stage)
                sleep_stages.append(
                    NormalisedSleepStage(
                        subject_id=subject_id,
                        start_utc=start_utc,
                        end_utc=end_utc,
                        stage=stage,
                    )
                )
        else:
            st_val = item.get("start_time") or item.get("startTime")
            et_val = item.get("end_time") or item.get("endTime")
            if not st_val or not et_val:
                continue
            start_utc = _parse_iso_utc(str(st_val))
            end_utc = _parse_iso_utc(str(et_val))
            raw_stage = str(item.get("stage") or item.get("stage_type") or "").upper()
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
    ex_raw = (
        payload.get("exercise") or payload.get("exercise_sessions") or payload.get("workouts") or []
    )
    exercise_sessions: list[NormalisedExerciseSession] = []
    for item in ex_raw:
        st_val = item.get("start_time") or item.get("startTime")
        et_val = item.get("end_time") or item.get("endTime")
        if not st_val or not et_val:
            continue
        start_utc = _parse_iso_utc(str(st_val))
        end_utc = _parse_iso_utc(str(et_val))
        kind = (
            str(
                item.get("kind")
                or item.get("type")
                or item.get("exercise_type")
                or item.get("title")
                or ""
            )
            or None
        )

        exercise_sessions.append(
            NormalisedExerciseSession(
                subject_id=subject_id,
                start_utc=start_utc,
                end_utc=end_utc,
                kind=kind,
            )
        )

    # 5. Blood oxygen. Field names read off the live bridge rather than guessed: the
    #    payload key is "oxygen_saturation" and each record carries "percentage" and
    #    "time". These arrive as a handful of spot readings, not a continuous stream.
    spo2_samples: list[NormalisedOxygenSaturation] = []
    for item in payload.get("oxygen_saturation") or []:
        ts_val = item.get("time")
        pct = item.get("percentage")
        if not ts_val or pct is None:
            continue
        origin = None
        if isinstance(item.get("metadata"), dict):
            origin = item["metadata"].get("data_origin")
        spo2_samples.append(
            NormalisedOxygenSaturation(
                subject_id=subject_id,
                ts_utc=_parse_iso_utc(str(ts_val)),
                percentage=float(pct),
                origin=origin,
            )
        )

    # 6. Distance covered, in daily buckets like steps.
    distance_buckets: list[NormalisedDistance] = []
    for item in payload.get("distance") or []:
        start_val = item.get("start_time")
        end_val = item.get("end_time")
        meters = item.get("meters")
        if not start_val or not end_val or meters is None:
            continue
        distance_buckets.append(
            NormalisedDistance(
                subject_id=subject_id,
                start_utc=_parse_iso_utc(str(start_val)),
                end_utc=_parse_iso_utc(str(end_val)),
                meters=float(meters),
            )
        )

    # 7. Energy expenditure.
    calorie_buckets: list[NormalisedCalories] = []
    for item in payload.get("total_calories") or []:
        start_val = item.get("start_time")
        end_val = item.get("end_time")
        calories = item.get("calories")
        if not start_val or not end_val or calories is None:
            continue
        calorie_buckets.append(
            NormalisedCalories(
                subject_id=subject_id,
                start_utc=_parse_iso_utc(str(start_val)),
                end_utc=_parse_iso_utc(str(end_val)),
                calories_kcal=float(calories),
            )
        )

    return NormalisedData(
        heart_rate_samples=hr_samples,
        step_buckets=step_buckets,
        sleep_stages=sleep_stages,
        exercise_sessions=exercise_sessions,
        oxygen_saturation_samples=spo2_samples,
        distance_buckets=distance_buckets,
        calorie_buckets=calorie_buckets,
    )
