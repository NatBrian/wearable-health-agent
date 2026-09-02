"""Deterministic detection of heart rate anomalies and alert persistence."""

import json
import sqlite3
from collections.abc import Sequence
from datetime import date, timedelta

from wha.constants import (
    BASELINE_SCALE_FLOOR_BPM,
    BASELINE_WINDOW_NIGHTS,
    DETECT_PERSISTENCE_NIGHTS,
    DETECT_RED_BPM,
    DETECT_YELLOW_BPM,
)
from wha.db import transaction
from wha.detect.baseline import compute_baseline
from wha.detect.explained import explained_bpm
from wha.features import compute_night
from wha.models import (
    Baseline,
    Detection,
    DetectionLevel,
    Forecast,
    ForecastStatus,
    NightlyFeatures,
)


def compute_detection_for_features(
    features: NightlyFeatures,
    baseline: Baseline,
    preceding_consecutive_levels: Sequence[DetectionLevel | str] = (),
    forecast: Forecast | None = None,
) -> Detection:
    """Pure calculation of Detection metrics for a given night's features and baseline.

    Args:
        features: Tonight's NightlyFeatures
        baseline: Pre-computed baseline from historical nights (excluding tonight)
        preceding_consecutive_levels: Sequence of levels from immediately preceding consecutive
            calendar days [yesterday, day_before_yesterday, ...] that were YELLOW or RED.
        forecast: Optional Chronos forecast model (defaults to NOT_RUN status)
    """
    fc = forecast or Forecast(status=ForecastStatus.NOT_RUN)

    if not features.usable or features.rhr_bpm is None:
        return Detection(
            subject_id=features.subject_id,
            night_date=features.night_date,
            level=DetectionLevel.NA,
            flagged=False,
            deviation_bpm=None,
            explained_bpm=0.0,
            residual_bpm=None,
            robust_z=None,
            forecast=fc,
            reasons=[],
        )

    deviation_bpm = round(features.rhr_bpm - baseline.centre_bpm, 3)
    exp_bpm, reasons = explained_bpm(features)
    residual_bpm = round(deviation_bpm - exp_bpm, 3)

    scale = max(baseline.scale_bpm, BASELINE_SCALE_FLOOR_BPM)
    robust_z = round(residual_bpm / scale, 3)

    # Determine level from residual_bpm
    if residual_bpm < DETECT_YELLOW_BPM:
        level = DetectionLevel.GREEN
    elif residual_bpm < DETECT_RED_BPM:
        level = DetectionLevel.YELLOW
    else:
        level = DetectionLevel.RED

    # Determine flagged status from persistence run
    flagged = False
    if level in (DetectionLevel.YELLOW, DetectionLevel.RED):
        # Current run of consecutive elevated nights ending tonight
        current_run = [level] + list(preceding_consecutive_levels or [])
        if len(current_run) >= DETECT_PERSISTENCE_NIGHTS and any(
            lvl in (DetectionLevel.RED, "RED") for lvl in current_run
        ):
            flagged = True

    return Detection(
        subject_id=features.subject_id,
        night_date=features.night_date,
        level=level,
        flagged=flagged,
        deviation_bpm=deviation_bpm,
        explained_bpm=exp_bpm if exp_bpm > 0 else 0.0,
        residual_bpm=residual_bpm,
        robust_z=robust_z,
        forecast=fc,
        reasons=reasons,
    )


def detect_night(
    conn: sqlite3.Connection,
    subject_id: str,
    night_date: date,
    forecast: Forecast | None = None,
) -> Detection:
    """Compute detection for a single night and persist into baselines and detections tables."""
    # 1. Fetch or compute features for tonight
    cur = conn.execute(
        """
        SELECT subject_id, night_date, rhr_bpm, coverage_minutes,
               implausible_dropped, usable, steps_prev_day, sleep_hours,
               exercise_end_offset_h
        FROM nightly_features
        WHERE subject_id = ? AND night_date = ?;
        """,
        (subject_id, night_date.isoformat()),
    )
    row = cur.fetchone()
    if row is None:
        features = compute_night(conn, subject_id, night_date)
    else:
        features = NightlyFeatures(
            subject_id=row["subject_id"],
            night_date=date.fromisoformat(row["night_date"]),
            rhr_bpm=row["rhr_bpm"],
            coverage_minutes=row["coverage_minutes"],
            implausible_dropped=row["implausible_dropped"],
            usable=bool(row["usable"]),
            steps_prev_day=row["steps_prev_day"],
            sleep_hours=row["sleep_hours"],
            exercise_end_offset_h=row["exercise_end_offset_h"],
        )

    # 2. Fetch baseline history (strictly preceding nights < night_date)
    # Exclude closed episodes with LIKELY_ILLNESS or ESCALATED
    cur = conn.execute(
        """
        SELECT nf.subject_id, nf.night_date, nf.rhr_bpm, nf.coverage_minutes,
               nf.implausible_dropped, nf.usable, nf.steps_prev_day, nf.sleep_hours,
               nf.exercise_end_offset_h
        FROM nightly_features nf
        WHERE nf.subject_id = ? AND nf.night_date < ? AND nf.usable = 1
          AND NOT EXISTS (
              SELECT 1 FROM episodes e
              WHERE e.subject_id = nf.subject_id AND e.state = 'CLOSED'
                AND e.disposition IN ('LIKELY_ILLNESS', 'ESCALATED')
                AND nf.night_date BETWEEN e.opened_on
                                      AND COALESCE(e.closed_on, e.opened_on)
          )
        ORDER BY nf.night_date ASC;
        """,
        (subject_id, night_date.isoformat()),
    )
    history_rows = cur.fetchall()
    history = [
        NightlyFeatures(
            subject_id=r["subject_id"],
            night_date=date.fromisoformat(r["night_date"]),
            rhr_bpm=r["rhr_bpm"],
            coverage_minutes=r["coverage_minutes"],
            implausible_dropped=r["implausible_dropped"],
            usable=bool(r["usable"]),
            steps_prev_day=r["steps_prev_day"],
            sleep_hours=r["sleep_hours"],
            exercise_end_offset_h=r["exercise_end_offset_h"],
        )
        for r in history_rows
    ][-BASELINE_WINDOW_NIGHTS:]

    baseline = compute_baseline(history)

    # 3. Fetch preceding consecutive elevated nights
    preceding_levels: list[DetectionLevel] = []
    prev_d = night_date - timedelta(days=1)
    while True:
        cur = conn.execute(
            "SELECT level FROM detections WHERE subject_id = ? AND night_date = ?;",
            (subject_id, prev_d.isoformat()),
        )
        det_row = cur.fetchone()
        if det_row is None:
            break

        prev_level_str = det_row["level"]
        if prev_level_str in ("YELLOW", "RED"):
            preceding_levels.append(DetectionLevel(prev_level_str))
            prev_d -= timedelta(days=1)
        else:
            break

    # 4. Compute detection
    fc = forecast or Forecast(status=ForecastStatus.NOT_RUN)
    detection = compute_detection_for_features(features, baseline, preceding_levels, fc)

    # 5. Persist baseline and detection
    reasons_json = json.dumps(detection.reasons)
    with transaction(conn):
        conn.execute(
            """
            INSERT OR REPLACE INTO baselines (
                subject_id, night_date, centre_bpm, scale_bpm, usable_nights, rung, shrink_weight
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                subject_id,
                night_date.isoformat(),
                baseline.centre_bpm,
                baseline.scale_bpm,
                baseline.usable_nights,
                baseline.rung.value,
                baseline.shrink_weight,
            ),
        )

        conn.execute(
            """
            INSERT OR REPLACE INTO detections (
                subject_id, night_date, deviation_bpm, robust_z, explained_bpm, residual_bpm,
                level, flagged, forecast_bpm, forecast_lo_bpm, forecast_hi_bpm, forecast_z,
                forecast_status, reasons_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                detection.subject_id,
                detection.night_date.isoformat(),
                detection.deviation_bpm,
                detection.robust_z,
                detection.explained_bpm,
                detection.residual_bpm,
                detection.level.value,
                1 if detection.flagged else 0,
                detection.forecast.predicted_bpm,
                detection.forecast.lo_bpm,
                detection.forecast.hi_bpm,
                detection.forecast.forecast_z,
                detection.forecast.status.value,
                reasons_json,
            ),
        )

    return detection


def detect_range(
    conn: sqlite3.Connection, subject_id: str, start: date, end: date
) -> list[Detection]:
    """Compute and store detections sequentially for date range [start, end]."""
    out: list[Detection] = []
    curr = start
    while curr <= end:
        out.append(detect_night(conn, subject_id, curr))
        curr += timedelta(days=1)
    return out
