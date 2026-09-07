"""Nightly feature computation and storage orchestration."""

import sqlite3
from datetime import date, timedelta

from wha.clock import now_utc
from wha.db import to_iso, transaction
from wha.features.covariates import (
    derive_exercise_offset,
    derive_prev_day_steps,
    derive_sleep_hours,
)
from wha.features.rhr import compute_nocturnal_rhr
from wha.features.sleep_window import resolve_sleep_window
from wha.models import NightlyFeatures


def compute_night(conn: sqlite3.Connection, subject_id: str, night_date: date) -> NightlyFeatures:
    """Compute features for one night and upsert into the nightly_features table."""
    # 1. Subject timezone
    cur = conn.execute("SELECT timezone FROM subjects WHERE subject_id = ?;", (subject_id,))
    row = cur.fetchone()
    tz_str = row["timezone"] if row else "Asia/Singapore"

    # 2. The window this night is measured over. Read from the watch's own sleep session
    #    where it recorded one, because a clock window measures whoever happens to sleep
    #    between midnight and 7am and measures waking heart rate for everyone else.
    window = resolve_sleep_window(conn, subject_id, night_date, tz_str)
    w_start, w_end = window.start_utc, window.end_utc
    w_start_str, w_end_str = to_iso(w_start), to_iso(w_end)

    # 3. Heart rate samples, taken only from the spans the person was actually asleep.
    #    A sleep session contains waking spells; reading across them would reintroduce in
    #    miniature the error this window removes.
    hr_samples: list = []
    for a, b in window.intervals:
        hr_samples.extend(
            conn.execute(
                """
                SELECT ts_utc, avg_bpm, min_bpm, max_bpm, origin
                FROM heart_rate_samples
                WHERE subject_id = ? AND ts_utc >= ? AND ts_utc < ?
                ORDER BY ts_utc ASC;
                """,
                (subject_id, to_iso(a), to_iso(b)),
            ).fetchall()
        )
    rhr_bpm, coverage_min, implausible_dropped, usable = compute_nocturnal_rhr(hr_samples)

    # 4. Covariates: previous-day steps
    cur = conn.execute(
        "SELECT start_utc, end_utc, count FROM step_buckets WHERE subject_id = ?;",
        (subject_id,),
    )
    step_rows = cur.fetchall()
    steps_prev_day = derive_prev_day_steps(step_rows, night_date, tz_str)

    # Covariates: sleep hours
    cur = conn.execute(
        """
        SELECT start_utc, end_utc, stage
        FROM sleep_stages
        WHERE subject_id = ? AND start_utc < ? AND end_utc > ?;
        """,
        (subject_id, w_end_str, w_start_str),
    )
    sleep_rows = cur.fetchall()
    sleep_hours = derive_sleep_hours(sleep_rows, w_start, w_end)

    # Covariates: exercise offset
    cur = conn.execute(
        "SELECT start_utc, end_utc, kind FROM exercise_sessions WHERE subject_id = ?;",
        (subject_id,),
    )
    exercise_rows = cur.fetchall()
    exercise_offset_h = derive_exercise_offset(exercise_rows, w_start)

    features = NightlyFeatures(
        subject_id=subject_id,
        night_date=night_date,
        rhr_bpm=rhr_bpm,
        coverage_minutes=coverage_min,
        implausible_dropped=implausible_dropped,
        usable=usable,
        steps_prev_day=steps_prev_day,
        sleep_hours=sleep_hours,
        exercise_end_offset_h=exercise_offset_h,
        rhr_window_source=window.source,
    )

    now_str = to_iso(now_utc())
    with transaction(conn):
        conn.execute(
            """
            INSERT OR REPLACE INTO nightly_features (
                subject_id, night_date, rhr_bpm, coverage_minutes,
                implausible_dropped, usable, steps_prev_day, sleep_hours,
                exercise_end_offset_h, rhr_window_source, computed_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                features.subject_id,
                features.night_date.isoformat(),
                features.rhr_bpm,
                features.coverage_minutes,
                features.implausible_dropped,
                1 if features.usable else 0,
                features.steps_prev_day,
                features.sleep_hours,
                features.exercise_end_offset_h,
                features.rhr_window_source,
                now_str,
            ),
        )

    return features


def compute_range(
    conn: sqlite3.Connection, subject_id: str, start: date, end: date
) -> list[NightlyFeatures]:
    """Compute features for a date range [start, end] inclusive."""
    out: list[NightlyFeatures] = []
    curr = start
    while curr <= end:
        out.append(compute_night(conn, subject_id, curr))
        curr += timedelta(days=1)
    return out
