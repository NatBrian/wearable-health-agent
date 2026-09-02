"""A night is a local calendar date, so "today" has to be one too.

`datetime.now(UTC).date()` was used in a dozen places and compared against night dates.
In Singapore, UTC+8, those differ for the whole window between local midnight and 8am,
which is exactly when someone installs a sleep monitor and looks at last night.
"""

from datetime import UTC, date, datetime
from unittest.mock import patch

from wha.clock import local_date_of, local_today


def test_a_utc_evening_is_already_tomorrow_in_singapore() -> None:
    """The instant the real subject row was written: 2026-09-02T17:41:38Z."""
    moment = datetime(2026, 9, 2, 17, 41, 38, tzinfo=UTC)
    assert moment.date() == date(2026, 9, 2)
    assert local_date_of(moment, "Asia/Singapore") == date(2026, 9, 3)


def test_a_utc_morning_is_the_same_day_in_singapore() -> None:
    moment = datetime(2026, 9, 2, 6, 0, tzinfo=UTC)
    assert local_date_of(moment, "Asia/Singapore") == date(2026, 9, 2)


def test_a_naive_timestamp_is_read_as_utc() -> None:
    moment = datetime(2026, 9, 2, 17, 41, 38)  # noqa: DTZ001 - naive on purpose
    assert local_date_of(moment, "Asia/Singapore") == date(2026, 9, 3)


def test_a_western_timezone_can_be_a_day_behind_utc() -> None:
    moment = datetime(2026, 9, 3, 2, 0, tzinfo=UTC)
    assert local_date_of(moment, "America/New_York") == date(2026, 9, 2)


def test_an_unresolvable_timezone_falls_back_to_utc_rather_than_raising() -> None:
    """A diagnostic must never crash the pipeline over a bad timezone string."""
    moment = datetime(2026, 9, 2, 17, 41, 38, tzinfo=UTC)
    assert local_date_of(moment, "Not/AZone") == date(2026, 9, 2)


def test_local_today_reads_the_configured_timezone() -> None:
    class _Settings:
        timezone = "Asia/Singapore"

    with patch("wha.config.get_settings", return_value=_Settings()):
        assert local_today() == local_date_of(datetime.now(UTC), "Asia/Singapore")
