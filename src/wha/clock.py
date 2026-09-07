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

This module is also the ONLY place in `src/wha` allowed to read the wall clock. A test
enforces that, because the second reason this file exists is `WHA_CLOCK_OFFSET_DAYS`.

Walking a twelve night illness through the real pipeline takes twelve days of wall clock
unless the whole system can be told to believe it is a different day. Shifting only the
night labels is not enough: the audit rows, the episode ticks and the date handed to the
model in its own prompt all come from `datetime.now`, and a system that scores a night as
Tuesday while telling the person it is Thursday is broken in a way that shows.

The variable is unset in production, and unset means `datetime.now(UTC)` exactly. It is
loaded from a separate `demo.env`, never from `.env`, and `wha doctor` reports it as a
warning whenever it is not zero, so a shifted clock cannot be mistaken for a real one.
"""

import os
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

OFFSET_ENV_VAR = "WHA_CLOCK_OFFSET_DAYS"


def clock_offset_days() -> int:
    """Whole days the clock is shifted by. Zero in production.

    An unparseable value is treated as zero rather than raised, because a malformed
    environment variable must not be able to take the pipeline down. `wha doctor` is
    where a bad value gets reported.
    """
    raw = os.environ.get(OFFSET_ENV_VAR, "").strip()
    if not raw:
        return 0
    try:
        return int(raw)
    except ValueError:
        return 0


def now_utc() -> datetime:
    """The current instant, shifted if the demo clock is active.

    Every timestamp in this system comes from here. Nothing else in `src/wha` calls
    `datetime.now`.
    """
    offset = clock_offset_days()
    if offset == 0:
        return datetime.now(UTC)
    return datetime.now(UTC) + timedelta(days=offset)


def local_today(tz_name: str | None = None) -> date:
    """The current calendar date in the subject's timezone.

    Falls back to the configured timezone, and to UTC only if the name cannot be
    resolved, because a wrong date is worse than a wrong offset by one day.
    """
    return local_date_of(now_utc(), tz_name)


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
