"""Synthetic data generator implementing the DataSource protocol."""

import hashlib
import json
import math
import random
from datetime import UTC, datetime, timedelta
from typing import Any

from wha.db.iso import to_iso
from wha.models import RawPayload, Scenario

DATA_ORIGIN = "com.sec.android.app.shealth"
APP_VERSION = "1.9.17"
FIXED_ANCHOR_UTC = datetime(2026, 9, 1, 8, 0, 0, tzinfo=UTC)

# Temporal profiles from data/knowledge/causes.yaml
INFECTION_PROFILE = [0.5, 0.8, 1.0, 1.0, 0.9, 0.7, 0.5, 0.3, 0.0]
ALCOHOL_PROFILE = [1.0, 0.15, 0.0]
STRESS_PROFILE = [0.8, 1.0, 1.0, 1.0, 1.0, 0.8, 0.6, 0.4, 0.0]


def resting_bpm(local_hour: float, base_bpm: float) -> float:
    """Circadian baseline shape: lowest around 04:00, highest late afternoon."""
    return base_bpm + 12.0 * math.sin((local_hour - 10.0) / 24.0 * 2 * math.pi)


class Synthetic:
    """Synthetic data source that generates payloads matching real device schema."""

    source_kind = "synthetic"

    def __init__(self, scenario: Scenario | dict[str, Any], seed: int | None = None) -> None:
        if isinstance(scenario, dict):
            self.scenario = Scenario.model_validate(scenario)
        else:
            self.scenario = scenario
        self.seed = seed if seed is not None else self.scenario.seed

    def _get_utc_offset_hours(self) -> int:
        tz = self.scenario.timezone.lower()
        if "singapore" in tz or "shanghai" in tz or "hong_kong" in tz or "taipei" in tz:
            return 8
        if "tokyo" in tz:
            return 9
        if "london" in tz or "utc" in tz or "gmt" in tz:
            return 0
        return 8

    def fetch(self, subject_id: str, days: int | None = None) -> RawPayload:
        """Generate deterministic raw payload for the scenario."""
        rng = random.Random(self.seed)
        num_days = days if days is not None else self.scenario.days
        base_bpm = self.scenario.base_bpm
        utc_offset_h = self._get_utc_offset_hours()

        now = FIXED_ANCHOR_UTC
        start = now - timedelta(days=num_days)

        # 1. Daily step buckets
        steps: list[dict[str, Any]] = []
        midnight_start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        bucket_start = midnight_start - timedelta(hours=utc_offset_h)
        for _ in range(num_days):
            bucket_end = bucket_start + timedelta(days=1)
            steps.append(
                {
                    "count": rng.randint(1500, 12000),
                    "start_time": to_iso(bucket_start),
                    "end_time": to_iso(bucket_end),
                }
            )
            bucket_start = bucket_end

        # 2. Exercise sessions from injections
        exercise: list[dict[str, Any]] = []
        for inj in self.scenario.injections:
            if inj.get("kind") == "exercise":
                day_idx = inj.get("day", 0)
                end_offset_h = float(inj.get("end_offset_h", 1.5))
                # Local midnight for this day
                local_midnight = start + timedelta(days=day_idx + 1)
                # Exercise end is end_offset_h before midnight local
                ex_end = local_midnight - timedelta(hours=utc_offset_h + end_offset_h)
                ex_start = ex_end - timedelta(hours=1)
                exercise.append(
                    {
                        "start_time": to_iso(ex_start),
                        "end_time": to_iso(ex_end),
                        "kind": "running",
                    }
                )

        # 3. Minute-level heart rate
        heart_rate: list[dict[str, Any]] = []
        total_minutes = num_days * 24 * 60

        for m in range(total_minutes):
            t = start + timedelta(minutes=m)
            local_t = t + timedelta(hours=utc_offset_h)
            current_day = int((t - start).total_seconds() // 86400)
            local_hour = local_t.hour + local_t.minute / 60.0

            # Check nonwear injections
            is_nonwear = False
            for inj in self.scenario.injections:
                if inj.get("kind") == "nonwear":
                    start_day = inj.get("start_day", inj.get("day", 0))
                    nights = inj.get("nights", 1)
                    minutes = inj.get("minutes")

                    if (
                        minutes is not None
                        and current_day == start_day
                        and 0.0 <= local_hour < (minutes / 60.0)
                    ):
                        is_nonwear = True
                        break
                    elif (
                        start_day <= current_day < (start_day + nights) and 0.0 <= local_hour < 7.0
                    ):
                        # Entire nocturnal window is nonwear
                        is_nonwear = True
                        break

            if is_nonwear:
                continue

            # Routine 2-hour charging gap in the evening if not specified
            if local_t.hour == 21 and rng.random() < 0.7:
                continue

            # Calculate injection effect offset
            offset = 0.0
            for inj in self.scenario.injections:
                kind = inj.get("kind")
                if kind == "illness":
                    start_day = inj.get("start_day", inj.get("day", 0))
                    if current_day >= start_day:
                        nights_since = current_day - start_day
                        prof = INFECTION_PROFILE
                        weight = prof[nights_since] if nights_since < len(prof) else prof[-1]
                        amplitude = float(inj.get("amplitude_bpm", 1.60))
                        offset += amplitude * weight

                elif kind == "alcohol":
                    inj_day = inj.get("day", inj.get("start_day", 0))
                    if current_day >= inj_day:
                        nights_since = current_day - inj_day
                        prof = ALCOHOL_PROFILE
                        weight = prof[nights_since] if nights_since < len(prof) else 0.0
                        amplitude = float(inj.get("amplitude_bpm", 2.60))
                        offset += amplitude * weight

                elif kind == "exercise":
                    inj_day = inj.get("day", 0)
                    if current_day == inj_day and 0.0 <= local_hour < 7.0:
                        amplitude = float(inj.get("amplitude_bpm", 4.14))
                        offset += amplitude

                elif kind == "stress":
                    inj_day = inj.get("day", inj.get("start_day", 0))
                    if current_day >= inj_day:
                        nights_since = current_day - inj_day
                        prof = STRESS_PROFILE
                        weight = prof[nights_since] if nights_since < len(prof) else 0.0
                        amplitude = float(inj.get("amplitude_bpm", 1.50))
                        offset += amplitude * weight

            centre = resting_bpm(local_hour, base_bpm) + offset
            avg = round(rng.gauss(centre, 3.0))
            spread = rng.randint(0, 4)

            heart_rate.append(
                {
                    "time": to_iso(t),
                    "avg": avg,
                    "min": avg - spread,
                    "max": avg + spread,
                    "metadata": {
                        "data_origin": DATA_ORIGIN,
                        "recording_method": "unknown",
                        "device": {"type": 0},
                    },
                }
            )

        body: dict[str, Any] = {
            "app_version": APP_VERSION,
            "timestamp": to_iso(now),
            "steps": steps,
            "heart_rate": heart_rate,
            "sleep": [],
            "exercise": exercise,
        }

        canonical_text = json.dumps(body, sort_keys=True, separators=(",", ":"))
        sha256 = hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()

        return RawPayload(
            subject_id=subject_id,
            source_kind="synthetic",
            fetched_at_utc=now,
            sha256=sha256,
            body=body,
        )
