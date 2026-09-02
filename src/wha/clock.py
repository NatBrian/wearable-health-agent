"""What day it is where the person lives.

A night is labelled with a local calendar date: the nocturnal window runs from local
midnight to local 7am, and `features/window.py` resolves it through the subject's
timezone. "Today", however, was computed as `datetime.now(UTC).date()` in a dozen places
and then compared against those local night dates.

In Singapore, UTC+8, that is a different day for the entire window between local midnight
and 8am. A user who installed at 01:41 local was recorded as having started monitoring the
previous day; an episode opened tonight closes with yesterday's date; and the dashboard
asks for a range ending yesterday, which can hide last night entirely.

Anywhere a date is compared against a night date, it has to be the local one.
"""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def local_today(tz_name: str | None = None) -> date:
    """The current calendar date in the subject's timezone.

    Falls back to the configured timezone, and to UTC only if the name cannot be
    resolved, because a wrong date is worse than a wrong offset by one day.
    """
    return local_date_of(datetime.now(UTC), tz_name)


def local_date_of(moment: datetime, tz_name: str | None = None) -> date:
    """The local calendar date a UTC instant falls on."""
    if tz_name is None:
        from wha.config import get_settings

        tz_name = get_settings().timezone

    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)

    try:
        return moment.astimezone(ZoneInfo(tz_name)).date()
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        return moment.astimezone(UTC).date()


def to_local(moment: datetime, tz_name: str | None = None) -> datetime:
    """A UTC instant expressed in the subject's timezone, for display.

    Timestamps shown to a person are read against their own clock, so a UTC hour printed
    verbatim is simply wrong for anyone not on UTC.
    """
    if tz_name is None:
        from wha.config import get_settings

        tz_name = get_settings().timezone

    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)

    try:
        return moment.astimezone(ZoneInfo(tz_name))
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        return moment.astimezone(UTC)
