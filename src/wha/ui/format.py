"""Turning what the application returns into what a person reads.

Kept apart from both the copy and the screens because two of the defects this dashboard
has actually shipped were formatting: a UTC hour printed to somebody in Singapore, so
data that arrived at 01:41 their time was labelled 17:41, and a night with no reading
drawn at zero, which reads as a heart rate of zero rather than as a night with no reading.

Every function here takes a value that may be missing and says so in words, because
"None" rendered into a health screen is worse than a sentence saying the figure is absent.
"""

from datetime import date, datetime
from typing import Any

ABSENT = "not measured"


def bpm(value: float | None, absent: str = ABSENT) -> str:
    """A heart rate, to the nearest whole beat. Nobody reads decimals of a pulse."""
    if value is None:
        return absent
    return f"{value:.0f} bpm"


def band(low: float | None, high: float | None) -> str:
    """The usual range, as the two numbers a person can compare their night against."""
    if low is None or high is None:
        return ABSENT
    return f"{low:.0f} to {high:.0f} bpm"


def gap(value: float | None) -> str:
    """How far above or below normal, with the direction in words rather than a sign.

    A bare "-3.0" needs the reader to know which way is bad. "3 bpm below your normal"
    does not.
    """
    if value is None:
        return ABSENT
    if abs(value) < 0.05:
        return "level with your normal"
    direction = "above" if value > 0 else "below"
    return f"{abs(value):.1f} bpm {direction} your normal"


def probability(value: float | None) -> str:
    """A probability as a percentage. Rounded, because the third digit is not knowledge."""
    if value is None:
        return "not worked out"
    return f"{value * 100:.0f}%"


def hours(value: float | None) -> str:
    """A duration in hours and minutes, which is how people read sleep."""
    if value is None:
        return ABSENT
    whole = int(value)
    minutes = round((value - whole) * 60)
    if minutes == 60:
        whole, minutes = whole + 1, 0
    return f"{whole}h {minutes:02d}m"


def minutes(value: int | None) -> str:
    if value is None:
        return ABSENT
    return f"{value} minutes"


def night(value: date | None) -> str:
    """A night, named the way a person would say it."""
    if value is None:
        return "no night selected"
    return value.strftime("%A %d %B %Y").replace(" 0", " ")


def local_time(client: Any, moment: datetime | None) -> str:
    """A timestamp in the subject's own timezone, never a raw UTC hour.

    The conversion is done by the application, not here, because the browser's clock is
    not the person's clock and this dashboard has already printed one wrong hour to a real
    user.
    """
    if moment is None:
        return "not recorded"
    try:
        return client.localise(moment).strftime("%H:%M on %d %b")
    except (AttributeError, ValueError, OSError, RuntimeError):
        # A formatting helper must never take a screen down. Saying the time cannot be
        # shown is a smaller failure than a page that will not render.
        return "time unavailable"


def status_word(status: str) -> str:
    """What a step's status is called on screen, in words a reader can act on."""
    return {
        "ran": "ran",
        "skipped": "did not run",
        "not_applicable": "not needed",
        "unrecorded": "not recorded",
    }.get(status, status)
