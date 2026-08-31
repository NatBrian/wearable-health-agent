"""ISO 8601 UTC timestamp conversions for storage."""

from datetime import UTC, datetime


def to_iso(dt: datetime) -> str:
    """Convert timezone-aware datetime to ISO 8601 UTC string ending in 'Z'.

    Raises ValueError if a naive datetime is passed.
    """
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError(f"Naive datetime not allowed in storage: {dt!r}")
    dt_utc = dt.astimezone(UTC)
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def from_iso(s: str) -> datetime:
    """Parse ISO 8601 string to timezone-aware UTC datetime."""
    clean_s = s.replace("Z", "+00:00")
    dt = datetime.fromisoformat(clean_s)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)
