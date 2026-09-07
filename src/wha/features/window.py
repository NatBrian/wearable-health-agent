"""Nocturnal window calculation based on subject timezone."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo


def nocturnal_window(night_date: date, tz: str) -> tuple[datetime, datetime]:
    """Return the UTC instants bounding local 00:00-07:00 on night_date.

    Uses ZoneInfo to accurately account for timezone offsets and DST transitions.
    """
    zone = ZoneInfo(tz)
    local_start = datetime(night_date.year, night_date.month, night_date.day, 0, 0, 0, tzinfo=zone)
    local_end = datetime(night_date.year, night_date.month, night_date.day, 7, 0, 0, tzinfo=zone)
    return local_start.astimezone(UTC), local_end.astimezone(UTC)
