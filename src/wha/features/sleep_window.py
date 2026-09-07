"""When a person actually slept, read from the watch rather than assumed from the clock.

The window a night is measured over used to be local 00:00 to 07:00, which is the
NightSignal definition (Alavi et al. 2022). That study used a clock window because its
data had no sleep staging. This build has staging, and keeping the clock window while
holding the better signal copies a limitation rather than a method.

The cost is not theoretical. The first real subject slept 03:04 to 10:05, 03:39 to 10:55
and 02:37 to 11:18 on three consecutive nights. Against a midnight-to-7am window that is
2.6 to 3.6 hours of lying awake counted as sleep, and 40 percent of the actual sleep
discarded. Waking heart rate is both higher and more variable, so the error inflates the
baseline's scale, which widens the detection band and makes the system LESS sensitive to
the illness it exists to find. Because the amount of awake time varies from night to
night, it also injects noise straight into the residual.

Naps are deliberately not pooled with overnight sleep. See NAP_EXCLUSION_CITATION.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from wha.constants import SLEEP_SESSION_GAP_MINUTES
from wha.db import from_iso
from wha.features.window import nocturnal_window

AWAKE_STAGES = {"AWAKE", "AWAKE_IN_BED", "OUT_OF_BED", "1", "0"}

# Health Connect numeric stage codes, from the Android SleepSessionRecord.Stage constants.
# 0 unknown, 1 awake, 2 sleeping, 3 out of bed, 4 light, 5 deep, 6 REM, 7 awake in bed.
_NUMERIC_AWAKE = {"0", "1", "3", "7"}


@dataclass(frozen=True)
class SleepWindow:
    """The intervals a night's heart rate is measured over, and where they came from."""

    start_utc: datetime
    end_utc: datetime
    # Non-AWAKE spans inside the session. Heart rate is read from these, not from
    # start..end, because a session contains waking spells and measuring across them
    # reintroduces the same error in miniature.
    intervals: tuple[tuple[datetime, datetime], ...]
    source: str  # "sleep" when read from the watch, "clock" when it reported none

    @property
    def asleep_minutes(self) -> float:
        return sum((b - a).total_seconds() for a, b in self.intervals) / 60.0


def is_awake_stage(stage: object) -> bool:
    """Whether a stage label means the person was not asleep.

    Both the word forms the bridge sends and the Health Connect numeric codes appear in
    stored data, so both are recognised.
    """
    value = str(stage).strip().upper()
    if value in _NUMERIC_AWAKE:
        return True
    return value in AWAKE_STAGES


def group_sessions(
    stages: Sequence[dict],
) -> list[list[dict]]:
    """Split stage rows into sleep sessions on a gap.

    The stored rows carry no session identifier. Within a Health Connect session the
    stages abut one another, and separate sessions are hours apart, so a gap threshold
    separates them without needing the payload's session boundaries or a migration.
    """
    rows = sorted(
        (
            {
                "start": from_iso(r["start_utc"])
                if isinstance(r["start_utc"], str)
                else r["start_utc"],
                "end": from_iso(r["end_utc"]) if isinstance(r["end_utc"], str) else r["end_utc"],
                "stage": r["stage"],
            }
            for r in stages
        ),
        key=lambda r: r["start"],
    )

    sessions: list[list[dict]] = []
    current: list[dict] = []
    gap = timedelta(minutes=SLEEP_SESSION_GAP_MINUTES)

    for row in rows:
        if current and (row["start"] - current[-1]["end"]) > gap:
            sessions.append(current)
            current = []
        current.append(row)
    if current:
        sessions.append(current)
    return sessions


def _asleep_intervals(session: Sequence[dict]) -> tuple[tuple[datetime, datetime], ...]:
    """The non-AWAKE spans of a session, merged where they touch."""
    spans = [(r["start"], r["end"]) for r in session if not is_awake_stage(r["stage"])]
    if not spans:
        return ()

    merged: list[list[datetime]] = [[spans[0][0], spans[0][1]]]
    for start, end in spans[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return tuple((a, b) for a, b in merged)


def resolve_sleep_window(
    conn: sqlite3.Connection,
    subject_id: str,
    night_date: date,
    tz_str: str,
) -> SleepWindow:
    """The window for one night: the person's main sleep, or the clock if none was recorded.

    A night is named for the day the person woke, which the contract already states, so the
    session chosen is the one whose end falls on ``night_date`` in local time. Where more
    than one qualifies, the one with the most sleep in it wins: a nap is not pooled with
    overnight sleep because heart rate during naps is measurably higher at matched sleep
    stages, and pooling would bias the night by however much the person happened to nap.
    """
    clock_start, clock_end = nocturnal_window(night_date, tz_str)

    # Look either side of the clock window by a day, so a session that starts before
    # midnight or ends late in the morning is still found.
    rows = conn.execute(
        """SELECT start_utc, end_utc, stage FROM sleep_stages
           WHERE subject_id = ? AND end_utc > ? AND start_utc < ?
           ORDER BY start_utc ASC""",
        (
            subject_id,
            (clock_start - timedelta(days=1)).isoformat().replace("+00:00", "Z"),
            (clock_end + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
        ),
    ).fetchall()

    if rows:
        from wha.clock import local_date_of

        best: tuple[float, SleepWindow] | None = None
        for session in group_sessions([dict(r) for r in rows]):
            intervals = _asleep_intervals(session)
            if not intervals:
                continue
            session_end = max(b for _, b in intervals)
            if local_date_of(session_end, tz_str) != night_date:
                continue
            asleep = sum((b - a).total_seconds() for a, b in intervals)
            candidate = SleepWindow(
                start_utc=min(a for a, _ in intervals),
                end_utc=session_end,
                intervals=intervals,
                source="sleep",
            )
            if best is None or asleep > best[0]:
                best = (asleep, candidate)

        if best is not None:
            return best[1]

    # The watch reported no sleep for this night. Falling back keeps working for devices
    # that never report staging, and the night is labelled so the weaker basis is visible
    # rather than silently assumed.
    return SleepWindow(
        start_utc=clock_start,
        end_utc=clock_end,
        intervals=((clock_start, clock_end),),
        source="clock",
    )
