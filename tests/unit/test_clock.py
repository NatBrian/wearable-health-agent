"""A night is a local calendar date, so "today" has to be one too.

`datetime.now(UTC).date()` was used in a dozen places and compared against night dates.
In Singapore, UTC+8, those differ for the whole window between local midnight and 8am,
which is exactly when someone installs a sleep monitor and looks at last night.
"""

import os
from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import patch

from wha.clock import clock_offset_days, local_date_of, local_today, now_utc


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


# ---------------------------------------------------------------------------
# The offset. Added 7 September 2026 so a twelve night timeline can be walked
# through in an afternoon without any part of `src/wha` behaving differently.
#
# The default is the whole point: with the variable unset, `now_utc()` is
# `datetime.now(UTC)` and nothing has changed.
# ---------------------------------------------------------------------------


def test_without_the_variable_now_is_simply_now() -> None:
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("WHA_CLOCK_OFFSET_DAYS", None)
        before = datetime.now(UTC)
        moment = now_utc()
        after = datetime.now(UTC)
    assert before <= moment <= after


def test_a_positive_offset_moves_the_clock_forward_by_whole_days() -> None:
    with patch.dict(os.environ, {"WHA_CLOCK_OFFSET_DAYS": "5"}):
        shifted = now_utc()
    elapsed = (shifted - datetime.now(UTC)).total_seconds()
    assert round(elapsed / 86400) == 5


def test_a_negative_offset_moves_the_clock_back() -> None:
    with patch.dict(os.environ, {"WHA_CLOCK_OFFSET_DAYS": "-3"}):
        shifted = now_utc()
    elapsed = (datetime.now(UTC) - shifted).total_seconds()
    assert round(elapsed / 86400) == 3


def test_local_today_follows_the_offset() -> None:
    """The reason the offset exists at all: night dates are compared against today."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("WHA_CLOCK_OFFSET_DAYS", None)
        real = local_today("Asia/Singapore")
    with patch.dict(os.environ, {"WHA_CLOCK_OFFSET_DAYS": "9"}):
        shifted = local_today("Asia/Singapore")
    assert (shifted - real).days == 9


def test_an_unparseable_offset_is_ignored_rather_than_raising() -> None:
    """A malformed environment variable must not take the pipeline down."""
    with patch.dict(os.environ, {"WHA_CLOCK_OFFSET_DAYS": "tomorrow please"}):
        moment = now_utc()
    assert abs((moment - datetime.now(UTC)).total_seconds()) < 5


def test_the_offset_is_reported_so_it_cannot_be_mistaken_for_production() -> None:
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("WHA_CLOCK_OFFSET_DAYS", None)
        assert clock_offset_days() == 0
    with patch.dict(os.environ, {"WHA_CLOCK_OFFSET_DAYS": "12"}):
        assert clock_offset_days() == 12


def test_nothing_outside_this_module_reads_the_wall_clock() -> None:
    """The offset is worthless if any call site bypasses it.

    This is the same shape as the defect found on 7 September, where
    `check_red_flags_deterministic` accepted a symptom history that no production caller
    ever passed: code that exists, is referenced, and is never reached. A shifted clock
    that reaches the night labels but not the audit rows would be exactly that again,
    and it would only show up on camera.

    `date.today()` and `datetime.today()` are banned for the same reason, and because they
    are naive: they return local time with no timezone attached.
    """
    root = Path(__file__).resolve().parents[2] / "src" / "wha"
    banned = ("datetime.now(", "date.today()", "datetime.today()")
    offenders: list[str] = []

    for path in sorted(root.rglob("*.py")):
        if path.name == "clock.py":
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            code = line.split("#", 1)[0]
            if any(token in code for token in banned):
                offenders.append(f"{path.relative_to(root)}:{lineno}: {line.strip()}")

    assert not offenders, "call wha.clock.now_utc() instead:\n" + "\n".join(offenders)
