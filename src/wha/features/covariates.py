"""Covariate derivation for previous-day steps, sleep duration, and exercise offset."""

from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from wha.constants import EXERCISE_LOOKBACK_HOURS
from wha.db import from_iso


def derive_prev_day_steps(
    step_buckets: Sequence[dict],
    night_date: date,
    tz_str: str,
) -> int | None:
    """Find step count for the local calendar day preceding night_date (night_date - 1).

    Returns None if no step bucket covers the day.
    """
    if not step_buckets:
        return None

    prev_date = night_date - timedelta(days=1)
    zone = ZoneInfo(tz_str)
    day_start_utc = datetime(
        prev_date.year, prev_date.month, prev_date.day, 0, 0, 0, tzinfo=zone
    ).astimezone(UTC)
    day_end_utc = day_start_utc + timedelta(days=1)

    best_overlap_seconds = 0.0
    best_count: int | None = None

    for bucket in step_buckets:
        b_start = (
            from_iso(bucket["start_utc"])
            if isinstance(bucket["start_utc"], str)
            else bucket["start_utc"]
        )
        b_end = (
            from_iso(bucket["end_utc"]) if isinstance(bucket["end_utc"], str) else bucket["end_utc"]
        )

        overlap_start = max(b_start, day_start_utc)
        overlap_end = min(b_end, day_end_utc)

        if overlap_end > overlap_start:
            overlap_seconds = (overlap_end - overlap_start).total_seconds()
            if overlap_seconds > best_overlap_seconds:
                best_overlap_seconds = overlap_seconds
                best_count = int(bucket["count"])

    return best_count


def derive_sleep_hours(
    sleep_stages: Sequence[dict],
    window_start_utc: datetime,
    window_end_utc: datetime,
) -> float | None:
    """Derive total hours of non-AWAKE sleep overlapping the nocturnal window.

    Returns None if no sleep stages are recorded.
    """
    if not sleep_stages:
        return None

    non_awake_seconds = 0.0
    has_overlapping_records = False

    for item in sleep_stages:
        s_start = (
            from_iso(item["start_utc"]) if isinstance(item["start_utc"], str) else item["start_utc"]
        )
        s_end = from_iso(item["end_utc"]) if isinstance(item["end_utc"], str) else item["end_utc"]
        stage = str(item["stage"]).upper()

        overlap_start = max(s_start, window_start_utc)
        overlap_end = min(s_end, window_end_utc)

        if overlap_end > overlap_start:
            has_overlapping_records = True
            if stage != "AWAKE":
                non_awake_seconds += (overlap_end - overlap_start).total_seconds()

    if not has_overlapping_records:
        return None

    return round(non_awake_seconds / 3600.0, 2)


def derive_exercise_offset(
    exercise_sessions: Sequence[dict],
    window_start_utc: datetime,
) -> float | None:
    """Derive hours between latest-ending exercise session and nocturnal window start.

    Only considers sessions ending within EXERCISE_LOOKBACK_HOURS (6h) before window start.
    Returns None if no session qualifies.
    """
    if not exercise_sessions:
        return None

    lookback_start = window_start_utc - timedelta(hours=EXERCISE_LOOKBACK_HOURS)
    qualifying_offsets: list[float] = []

    for item in exercise_sessions:
        end_utc_val = item.get("end_utc")
        if not end_utc_val:
            continue
        end_utc = from_iso(end_utc_val) if isinstance(end_utc_val, str) else end_utc_val

        if lookback_start <= end_utc <= window_start_utc:
            offset_h = (window_start_utc - end_utc).total_seconds() / 3600.0
            qualifying_offsets.append(offset_h)

    if not qualifying_offsets:
        return None

    # The latest-ending session has the smallest offset
    return round(min(qualifying_offsets), 2)
