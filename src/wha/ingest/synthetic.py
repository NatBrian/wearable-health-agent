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
# Offset into INFECTION_PROFILE at which the weight first reaches 1.0.
PEAK_INDEX = INFECTION_PROFILE.index(1.0)
ALCOHOL_PROFILE = [1.0, 0.15, 0.0]
STRESS_PROFILE = [0.8, 1.0, 1.0, 1.0, 1.0, 0.8, 0.6, 0.4, 0.0]


def resting_bpm(local_hour: float, base_bpm: float) -> float:
    """Circadian baseline shape: lowest around 04:00, highest late afternoon."""
    circadian_shift = 6.0 * math.sin((local_hour - 10.0) / 24.0 * 2 * math.pi)
    return base_bpm + circadian_shift + 6.0


class Synthetic:
    """Synthetic data source that generates payloads matching real device schema."""

    source_kind = "synthetic"

    def __init__(
        self,
        scenario: Scenario | dict[str, Any],
        seed: int | None = None,
        anchor: datetime | None = None,
    ) -> None:
        if isinstance(scenario, dict):
            self.scenario = Scenario.model_validate(scenario)
        else:
            self.scenario = scenario
        self.seed = seed if seed is not None else self.scenario.seed
        # The end of the generated window. Frozen scenarios rely on the fixed anchor, so it
        # stays the default; the mock watch bridge passes a moving anchor to advance a day
        # at a time without touching any other code path.
        self.anchor = anchor if anchor is not None else FIXED_ANCHOR_UTC

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

        now = self.anchor
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
        local_start = start + timedelta(hours=utc_offset_h)
        local_midnight_0 = local_start.replace(hour=0, minute=0, second=0, microsecond=0)
        for inj in self.scenario.injections:
            if inj.get("kind") == "exercise":
                day_idx = inj.get("day", 0)
                end_offset_h = float(inj.get("end_offset_h", 1.5))
                # Local midnight for this night (start of nocturnal window 00:00)
                night_local_midnight = local_midnight_0 + timedelta(days=day_idx + 1)
                ex_end_local = night_local_midnight - timedelta(hours=end_offset_h)
                ex_end_utc = ex_end_local - timedelta(hours=utc_offset_h)
                ex_start_utc = ex_end_utc - timedelta(hours=1)
                exercise.append(
                    {
                        "start_time": to_iso(ex_start_utc),
                        "end_time": to_iso(ex_end_utc),
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
                        # Indexed from the profile's peak, because a fixture's
                        # `amplitude_bpm` states the elevation that should be OBSERVED on
                        # the illness nights, not the underlying cause amplitude before
                        # the temporal profile is applied. illness-onset asserts a flag on
                        # day 29 with amplitude 4.6, and DETECT_RED_BPM is 4.0: indexing
                        # from the ramp start yields 2.3 and 3.68 bpm, so the night the
                        # frozen fixture requires to be RED would never leave YELLOW.
                        #
                        # The cost of this is that simulated illness is flat rather than
                        # rising, and rising is what distinguishes infection from the
                        # luteal phase in causes.yaml. See docs/DISCLOSURES.md, illness-onset.
                        idx = min(nights_since + PEAK_INDEX, len(prof) - 1)
                        weight = prof[idx]
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

        # 3. Sleep sessions matching Health Connect ultradian sleep cycle pattern
        sleep: list[dict[str, Any]] = []
        for d in range(num_days):
            night_start_local = local_midnight_0 + timedelta(days=d) - timedelta(minutes=30)
            is_sleep_nonwear = any(
                inj.get("kind") == "nonwear"
                and inj.get("start_day", inj.get("day", 0))
                <= d
                < (inj.get("start_day", inj.get("day", 0)) + inj.get("nights", 1))
                for inj in self.scenario.injections
            )
            if is_sleep_nonwear:
                continue

            session_stages = []
            curr_t = night_start_local
            cycle_pattern = ["LIGHT", "DEEP", "LIGHT", "REM"]
            for _ in range(4):
                for stg in cycle_pattern:
                    dur_min = rng.randint(18, 26)
                    stg_start = curr_t
                    stg_end = curr_t + timedelta(minutes=dur_min)
                    session_stages.append(
                        {
                            "stage": stg,
                            "start_time": to_iso(stg_start - timedelta(hours=utc_offset_h)),
                            "end_time": to_iso(stg_end - timedelta(hours=utc_offset_h)),
                            "duration_seconds": dur_min * 60,
                        }
                    )
                    curr_t = stg_end

            sleep.append(
                {
                    "session_end_time": to_iso(curr_t - timedelta(hours=utc_offset_h)),
                    "duration_seconds": int((curr_t - night_start_local).total_seconds()),
                    "stages": session_stages,
                    "metadata": {"data_origin": DATA_ORIGIN},
                }
            )

        body: dict[str, Any] = {
            "app_version": APP_VERSION,
            "timestamp": to_iso(now),
            "steps": steps,
            "heart_rate": heart_rate,
            "sleep": sleep,
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
