"""Service functions for calendar nightly time-series and night inspection."""

import json
import sqlite3
from datetime import date, timedelta

from wha.clock import now_utc
from wha.constants import DASHBOARD_STEPS_AVERAGE_DAYS
from wha.db import connect
from wha.db.iso import from_iso, to_iso
from wha.db.migrations import apply_schema
from wha.models import (
    Baseline,
    BaselineRung,
    DashboardSummary,
    Detection,
    DetectionLevel,
    Forecast,
    ForecastStatus,
    NightDetail,
    NightlyFeatures,
    NightRow,
    OxygenReading,
)


def filter_history_nights(
    nights: list[NightRow],
    levels: list[DetectionLevel] | None = None,
    investigated_only: bool = False,
) -> list[NightRow]:
    """Apply the History table's requested filters without changing chart data."""
    requested_levels = set(levels or [])
    return [
        night
        for night in nights
        if (not requested_levels or night.level in requested_levels)
        and (not investigated_only or night.episode_id is not None)
    ]


def get_dashboard_summary(
    subject_id: str,
    end: date,
    steps_window_days: int = DASHBOARD_STEPS_AVERAGE_DAYS,
    conn: sqlite3.Connection | None = None,
) -> DashboardSummary:
    """Return observation dates and a steps average over a fixed calendar window."""
    if steps_window_days < 1:
        raise ValueError("steps_window_days must be at least one")

    close_conn = False
    if conn is None:
        conn = connect()
        apply_schema(conn)
        close_conn = True

    window_start = end - timedelta(days=steps_window_days - 1)
    try:
        latest_sleep = conn.execute(
            """SELECT night_date, sleep_hours FROM nightly_features
               WHERE subject_id = ? AND sleep_hours IS NOT NULL
               ORDER BY night_date DESC LIMIT 1""",
            (subject_id,),
        ).fetchone()
        latest_steps = conn.execute(
            """SELECT night_date, steps_prev_day FROM nightly_features
               WHERE subject_id = ? AND steps_prev_day IS NOT NULL
               ORDER BY night_date DESC LIMIT 1""",
            (subject_id,),
        ).fetchone()
        window_steps = conn.execute(
            """SELECT steps_prev_day FROM nightly_features
               WHERE subject_id = ? AND night_date >= ? AND night_date <= ?
                 AND steps_prev_day IS NOT NULL
               ORDER BY night_date""",
            (subject_id, window_start.isoformat(), end.isoformat()),
        ).fetchall()
        values = [int(row["steps_prev_day"]) for row in window_steps]
        average = round(sum(values) / len(values)) if values else None
        return DashboardSummary(
            latest_sleep_hours=float(latest_sleep["sleep_hours"]) if latest_sleep else None,
            latest_sleep_night=date.fromisoformat(latest_sleep["night_date"]) if latest_sleep else None,
            latest_steps=int(latest_steps["steps_prev_day"]) if latest_steps else None,
            latest_steps_night=date.fromisoformat(latest_steps["night_date"]) if latest_steps else None,
            steps_average=average,
            steps_window_start=window_start,
            steps_window_end=end,
        )
    finally:
        if close_conn:
            conn.close()


def list_nights(
    subject_id: str,
    start: date,
    end: date,
    conn: sqlite3.Connection | None = None,
) -> list[NightRow]:
    """Retrieve calendar nights between start and end inclusive, including empty rows for data gaps.

    For example, a 30-day range with 12 nights of data returns exactly 30 rows.
    When no baseline exists, band_lo and band_hi are None.
    Handles empty database cleanly.
    """
    close_conn = False
    if conn is None:
        conn = connect()
        apply_schema(conn)
        close_conn = True

    try:
        start_str = start.isoformat()
        end_str = end.isoformat()

        # Load features, baselines, and detections in range
        feat_rows = conn.execute(
            """SELECT * FROM nightly_features
               WHERE subject_id = ? AND night_date >= ? AND night_date <= ?""",
            (subject_id, start_str, end_str),
        ).fetchall()
        feat_map = {r["night_date"]: r for r in feat_rows}

        base_rows = conn.execute(
            """SELECT * FROM baselines
               WHERE subject_id = ? AND night_date >= ? AND night_date <= ?""",
            (subject_id, start_str, end_str),
        ).fetchall()
        base_map = {r["night_date"]: r for r in base_rows}

        det_rows = conn.execute(
            """SELECT * FROM detections
               WHERE subject_id = ? AND night_date >= ? AND night_date <= ?""",
            (subject_id, start_str, end_str),
        ).fetchall()
        det_map = {r["night_date"]: r for r in det_rows}

        # Find episode id if night was part of an episode
        ep_rows = conn.execute(
            """SELECT episode_id, opened_on, closed_on FROM episodes
               WHERE subject_id = ?""",
            (subject_id,),
        ).fetchall()

        night_rows: list[NightRow] = []
        cur_date = start
        while cur_date <= end:
            d_str = cur_date.isoformat()
            feat = feat_map.get(d_str)
            base = base_map.get(d_str)
            det = det_map.get(d_str)

            # Match episode
            ep_id = None
            for ep in ep_rows:
                ep_opened = date.fromisoformat(ep["opened_on"])
                ep_closed = (
                    date.fromisoformat(ep["closed_on"])
                    if ep["closed_on"]
                    else ep_opened + timedelta(days=14)
                )
                if ep_opened <= cur_date <= ep_closed:
                    ep_id = ep["episode_id"]
                    break

            if feat is not None:
                rhr_bpm = feat["rhr_bpm"]
                cov_min = int(feat["coverage_minutes"])
                usable = bool(feat["usable"])
            else:
                rhr_bpm = None
                cov_min = 0
                usable = False

            if base is not None:
                centre_bpm = float(base["centre_bpm"])
                scale_bpm = float(base["scale_bpm"])
                band_lo = centre_bpm - scale_bpm
                band_hi = centre_bpm + scale_bpm
            else:
                centre_bpm = None
                band_lo = None
                band_hi = None

            if det is not None:
                dev_bpm = det["deviation_bpm"]
                exp_bpm = float(det["explained_bpm"])
                res_bpm = det["residual_bpm"]
                lvl = DetectionLevel(det["level"])
            else:
                dev_bpm = None
                exp_bpm = 0.0
                res_bpm = None
                lvl = DetectionLevel.NA

            night_rows.append(
                NightRow(
                    night_date=cur_date,
                    rhr_bpm=rhr_bpm,
                    centre_bpm=centre_bpm,
                    band_lo=band_lo,
                    band_hi=band_hi,
                    deviation_bpm=dev_bpm,
                    explained_bpm=exp_bpm,
                    residual_bpm=res_bpm,
                    coverage_minutes=cov_min,
                    usable=usable,
                    level=lvl,
                    episode_id=ep_id,
                    rhr_window_source=(
                        (feat["rhr_window_source"] or "clock") if feat is not None else "clock"
                    ),
                    forecast_bpm=det["forecast_bpm"] if det is not None else None,
                    forecast_lo_bpm=det["forecast_lo_bpm"] if det is not None else None,
                    forecast_hi_bpm=det["forecast_hi_bpm"] if det is not None else None,
                    forecast_status=det["forecast_status"] if det is not None else None,
                    sleep_hours=feat["sleep_hours"] if feat is not None else None,
                    steps_prev_day=feat["steps_prev_day"] if feat is not None else None,
                )
            )
            cur_date += timedelta(days=1)

        return night_rows
    finally:
        if close_conn:
            conn.close()


def latest_recorded_night(
    subject_id: str,
    conn: sqlite3.Connection | None = None,
) -> date | None:
    """The newest night this person has a reading for, whatever its date.

    Usually earlier than today. It can be later: the mock watch advances the cursor past
    the wall clock, which the simulation runbook documents, and a night that exists in the
    record has to be visible on the screens or the record and the screen disagree.
    """
    close_conn = False
    if conn is None:
        conn = connect()
        apply_schema(conn)
        close_conn = True
    try:
        row = conn.execute(
            "SELECT MAX(night_date) AS newest FROM nightly_features WHERE subject_id = ?",
            (subject_id,),
        ).fetchone()
        return date.fromisoformat(row["newest"]) if row and row["newest"] else None
    finally:
        if close_conn:
            conn.close()


def get_night_detail(
    subject_id: str,
    night_date: date,
    conn: sqlite3.Connection | None = None,
) -> NightDetail:
    """Retrieve detailed view models for a single night."""
    rows = list_nights(subject_id, start=night_date, end=night_date, conn=conn)
    row = rows[0]

    close_conn = False
    if conn is None:
        conn = connect()
        apply_schema(conn)
        close_conn = True

    try:
        d_str = night_date.isoformat()
        feat_r = conn.execute(
            "SELECT * FROM nightly_features WHERE subject_id = ? AND night_date = ?",
            (subject_id, d_str),
        ).fetchone()

        if feat_r is not None:
            features = NightlyFeatures(
                subject_id=subject_id,
                night_date=night_date,
                rhr_bpm=feat_r["rhr_bpm"],
                coverage_minutes=feat_r["coverage_minutes"],
                implausible_dropped=feat_r["implausible_dropped"],
                usable=bool(feat_r["usable"]),
                steps_prev_day=feat_r["steps_prev_day"],
                sleep_hours=feat_r["sleep_hours"],
                exercise_end_offset_h=feat_r["exercise_end_offset_h"],
                rhr_window_source=feat_r["rhr_window_source"] or "clock",
            )
        else:
            features = NightlyFeatures(
                subject_id=subject_id,
                night_date=night_date,
                rhr_bpm=None,
                coverage_minutes=0,
                implausible_dropped=0,
                usable=False,
                steps_prev_day=None,
                sleep_hours=None,
                exercise_end_offset_h=None,
            )

        base_r = conn.execute(
            "SELECT * FROM baselines WHERE subject_id = ? AND night_date = ?",
            (subject_id, d_str),
        ).fetchone()

        if base_r is not None:
            baseline = Baseline(
                centre_bpm=base_r["centre_bpm"],
                scale_bpm=base_r["scale_bpm"],
                usable_nights=base_r["usable_nights"],
                rung=BaselineRung(base_r["rung"]),
                shrink_weight=base_r["shrink_weight"],
            )
        else:
            baseline = Baseline(
                centre_bpm=60.0,
                scale_bpm=3.0,
                usable_nights=0,
                rung=BaselineRung.COLD,
                shrink_weight=0.0,
            )

        det_r = conn.execute(
            "SELECT * FROM detections WHERE subject_id = ? AND night_date = ?",
            (subject_id, d_str),
        ).fetchone()

        if det_r is not None:
            reasons = json.loads(det_r["reasons_json"]) if det_r["reasons_json"] else []
            forecast = Forecast(
                predicted_bpm=det_r["forecast_bpm"],
                lo_bpm=det_r["forecast_lo_bpm"],
                hi_bpm=det_r["forecast_hi_bpm"],
                forecast_z=det_r["forecast_z"],
                status=ForecastStatus(det_r["forecast_status"]),
            )
            detection = Detection(
                subject_id=subject_id,
                night_date=night_date,
                deviation_bpm=det_r["deviation_bpm"],
                robust_z=det_r["robust_z"],
                explained_bpm=det_r["explained_bpm"],
                residual_bpm=det_r["residual_bpm"],
                level=DetectionLevel(det_r["level"]),
                flagged=bool(det_r["flagged"]),
                forecast=forecast,
                reasons=reasons,
            )
        else:
            detection = Detection(
                subject_id=subject_id,
                night_date=night_date,
                deviation_bpm=None,
                robust_z=None,
                explained_bpm=0.0,
                residual_bpm=None,
                level=DetectionLevel.NA,
                flagged=False,
                forecast=Forecast(
                    predicted_bpm=None,
                    lo_bpm=None,
                    hi_bpm=None,
                    forecast_z=None,
                    status=ForecastStatus.NOT_RUN,
                ),
                reasons=[],
            )

        return NightDetail(
            row=row,
            features=features,
            baseline=baseline,
            detection=detection,
        )
    finally:
        if close_conn:
            conn.close()


def list_oxygen_readings(
    subject_id: str,
    days: int = 7,
    conn: sqlite3.Connection | None = None,
) -> list[OxygenReading]:
    """Spot SpO2 samples in the last `days`, oldest first.

    Sparse and unbaselined on purpose: a night frequently has none, per
    docs/DESIGN-DATA-CHANNELS.md. Same table and query shape as the safety floor's own
    overnight check in wha.safety.rules, so a spot-check panel and the rule that acts on the
    same readings can never disagree about which rows exist.
    """
    close_conn = False
    if conn is None:
        conn = connect()
        apply_schema(conn)
        close_conn = True

    try:
        since = to_iso(now_utc() - timedelta(days=days))
        rows = conn.execute(
            """SELECT ts_utc, percentage FROM oxygen_saturation_samples
               WHERE subject_id = ? AND ts_utc >= ?
               ORDER BY ts_utc ASC""",
            (subject_id, since),
        ).fetchall()
        return [
            OxygenReading(ts_utc=from_iso(r["ts_utc"]), percentage=float(r["percentage"]))
            for r in rows
            if r["percentage"] is not None
        ]
    finally:
        if close_conn:
            conn.close()
