"""One night's journey, assembled from what was stored rather than re-run.

The deterministic half of this system leaves its working behind in four tables:
`heart_rate_samples`, `nightly_features`, `baselines` and `detections`. Nothing before this
module put those together and told the story of a single night, so an interface could
explain an investigation and could not explain the sixty-eight nights out of seventy-two
where no investigation happened. Those are the nights a person actually looks at.

Nothing here recalculates a result. Every figure is read from the row the deterministic
half wrote, so this module cannot disagree with the detector. Where a row records when it
was computed, that time is reported; where none was recorded, none is reported. A
plausible clock time is exactly the kind of invented figure this project refuses to add,
and `StepStatus.UNRECORDED` exists so that "we did not write it down" never has to be
dressed up as "it did not run".

The one thing this module does compute is the sleep window, through the same resolver the
features step used. That is a read of the same stored sleep stages rather than a second
opinion, and where its answer disagrees with the `rhr_window_source` stored on the night,
the stored value wins and the disagreement is reported.
"""

import json
import sqlite3
from datetime import date, datetime, timedelta

from wha.clock import local_today
from wha.db import connect
from wha.db.migrations import apply_schema
from wha.models import (
    CANONICAL_PIPELINE_STEPS,
    DetectionLevel,
    NightPipeline,
    PipelineHeadline,
    PipelineNightRef,
    PipelineStepView,
    StepStatus,
)
from wha.service.nights import get_night_detail, list_nights

# How long after a night a data pull can still be the one that carried it. Watch data is
# pulled every thirty minutes, so the pull covering a night lands within hours of it; a
# day of slack covers a phone that was off overnight without reaching into next week.
_INGEST_GRACE = timedelta(days=1)


def _subject_timezone(conn: sqlite3.Connection, subject_id: str) -> str:
    row = conn.execute(
        "SELECT timezone FROM subjects WHERE subject_id = ?", (subject_id,)
    ).fetchone()
    if row is not None and row["timezone"]:
        return str(row["timezone"])

    from wha.config import get_settings

    return get_settings().timezone


def _moment(value: object) -> datetime | None:
    """A stored timestamp, or nothing. Never a substitute for a missing one."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _step(
    step_id: str,
    status: StepStatus,
    reason: str,
    **kwargs: object,
) -> PipelineStepView:
    """Build one step, taking its ordinal and layer from the canonical list.

    Position and layer are properties of the pipeline, not of a night, so a caller cannot
    place a step out of order or colour it as the wrong kind of machine.
    """
    definition = next(s for s in CANONICAL_PIPELINE_STEPS if s.step_id == step_id)
    return PipelineStepView(
        step_id=definition.step_id,
        ordinal=definition.ordinal,
        layer=definition.layer,
        status=status,
        reason=reason,
        **kwargs,  # type: ignore[arg-type]
    )


def _collect_step(
    conn: sqlite3.Connection,
    subject_id: str,
    window_start: datetime,
    window_end: datetime,
) -> PipelineStepView:
    """Did the phone hand over data covering this night, and when.

    Ingest records itself only when something newer than last time arrived, because a poll
    every thirty minutes that re-fetches the same window would otherwise fill the record
    with cron ticks. So a night with no ingest event is not a night with no data: it is a
    night whose data arrived inside a pull recorded against another night, or before the
    system started writing these events at all. The step says that rather than implying
    the watch was silent.
    """
    horizon = (window_end + _INGEST_GRACE).isoformat()
    event = conn.execute(
        """SELECT timestamp_utc FROM audit_events
           WHERE subject_id = ? AND operation = 'ingest'
             AND timestamp_utc >= ? AND timestamp_utc <= ?
           ORDER BY timestamp_utc ASC LIMIT 1""",
        (subject_id, window_start.isoformat(), horizon),
    ).fetchone()

    payload = conn.execute(
        """SELECT fetched_at_utc, source_kind FROM raw_payloads
           WHERE subject_id = ? AND fetched_at_utc >= ? AND fetched_at_utc <= ?
           ORDER BY fetched_at_utc ASC LIMIT 1""",
        (subject_id, window_start.isoformat(), horizon),
    ).fetchone()

    if event is None and payload is None:
        return _step(
            "collect",
            StepStatus.UNRECORDED,
            "No data pull covering this night was written down. That does not mean none "
            "happened: a pull that finds nothing new is not recorded.",
        )

    occurred = _moment(event["timestamp_utc"] if event is not None else None) or _moment(
        payload["fetched_at_utc"] if payload is not None else None
    )
    outputs: dict[str, object] = {}
    if payload is not None:
        outputs["source"] = payload["source_kind"]

    return _step(
        "collect",
        StepStatus.RAN,
        "Your phone was asked for the readings your watch had recorded, and it sent them.",
        occurred_utc=occurred,
        outputs=outputs,
    )


def _store_step(
    conn: sqlite3.Connection,
    subject_id: str,
    window_start: datetime,
    window_end: datetime,
) -> PipelineStepView:
    """How much the watch actually recorded across the window this night was measured over."""
    samples = conn.execute(
        """SELECT COUNT(*) AS n FROM heart_rate_samples
           WHERE subject_id = ? AND ts_utc >= ? AND ts_utc < ?""",
        (subject_id, window_start.isoformat(), window_end.isoformat()),
    ).fetchone()["n"]

    stages = conn.execute(
        """SELECT COUNT(*) AS n FROM sleep_stages
           WHERE subject_id = ? AND end_utc > ? AND start_utc < ?""",
        (subject_id, window_start.isoformat(), window_end.isoformat()),
    ).fetchone()["n"]

    if samples == 0:
        return _step(
            "store",
            StepStatus.SKIPPED,
            "Your watch recorded no heart rate across this night, so there was nothing to store.",
            outputs={"heart_rate_samples": 0, "sleep_stage_rows": stages},
        )

    return _step(
        "store",
        StepStatus.RAN,
        "The readings were stored exactly as they arrived. Nothing is edited or "
        "smoothed at this point.",
        headline_figure=f"{samples} readings",
        outputs={"heart_rate_samples": samples, "sleep_stage_rows": stages},
    )


def _sleep_window_step(
    conn: sqlite3.Connection,
    subject_id: str,
    night_date: date,
    tz_name: str,
    stored_source: str | None,
) -> PipelineStepView:
    """Which stretch of time the night's reading was taken over, and where that came from.

    The window is resolved through the same code the features step used, but the authority
    on what actually happened is `nightly_features.rhr_window_source`. Where the two
    disagree, the stored value is reported and the disagreement is stated: sleep stages
    can arrive after a night was scored, and a screen that quietly re-derives would show a
    window the reading was never taken over.
    """
    from wha.features.sleep_window import resolve_sleep_window

    window = resolve_sleep_window(conn, subject_id, night_date, tz_name)
    source = stored_source or window.source

    outputs: dict[str, object] = {
        "window_source": source,
        "start_utc": window.start_utc.isoformat(),
        "end_utc": window.end_utc.isoformat(),
        "asleep_minutes": round(window.asleep_minutes, 1),
    }
    if stored_source is not None and stored_source != window.source:
        outputs["disagreement"] = (
            f"This night was measured over the {stored_source} window. Re-reading the "
            f"stored sleep now gives {window.source}, which means sleep data arrived "
            "after the night was scored."
        )

    if source == "sleep":
        reason = (
            "Your watch recorded when you slept, so the reading was taken over your "
            "actual sleep, with the waking spells inside it left out."
        )
    else:
        reason = (
            "Your watch recorded no sleep for this night, so the reading was taken over "
            "midnight to 7am local time instead."
        )

    if stored_source is None:
        return _step(
            "sleep_window",
            StepStatus.SKIPPED,
            "No reading was taken for this night, so no window was needed.",
            outputs=outputs,
        )

    return _step(
        "sleep_window",
        StepStatus.RAN,
        reason,
        headline_figure=f"{window.asleep_minutes / 60:.1f} h measured",
        outputs=outputs,
    )


def _features_step(conn: sqlite3.Connection, subject_id: str, night_date: date) -> PipelineStepView:
    """The one number a whole night is reduced to, and when it was worked out."""
    row = conn.execute(
        "SELECT * FROM nightly_features WHERE subject_id = ? AND night_date = ?",
        (subject_id, night_date.isoformat()),
    ).fetchone()

    if row is None:
        return _step(
            "features",
            StepStatus.SKIPPED,
            "There was no reading for this night, so nothing was worked out from it.",
        )

    outputs = {
        "rhr_bpm": row["rhr_bpm"],
        "coverage_minutes": row["coverage_minutes"],
        "sleep_hours": row["sleep_hours"],
        "usable": bool(row["usable"]),
        "implausible_dropped": row["implausible_dropped"],
    }
    occurred = _moment(row["computed_at_utc"])

    if row["rhr_bpm"] is None:
        return _step(
            "features",
            StepStatus.RAN,
            "Too little of the night was measured to take a resting heart rate from it.",
            occurred_utc=occurred,
            outputs=outputs,
        )

    return _step(
        "features",
        StepStatus.RAN,
        "The middle value of your heart rate across the window was taken as your "
        "resting heart rate for the night. The middle value is used rather than the "
        "average so that a few odd readings cannot drag it.",
        headline_figure=f"{row['rhr_bpm']:.0f} bpm",
        occurred_utc=occurred,
        outputs=outputs,
    )


def _baseline_step(conn: sqlite3.Connection, subject_id: str, night_date: date) -> PipelineStepView:
    """What normal means for this person, on this night."""
    row = conn.execute(
        "SELECT * FROM baselines WHERE subject_id = ? AND night_date = ?",
        (subject_id, night_date.isoformat()),
    ).fetchone()

    if row is None:
        return _step(
            "baseline",
            StepStatus.SKIPPED,
            "Your normal was not worked out for this night, which happens when the night "
            "had no reading of its own.",
        )

    return _step(
        "baseline",
        StepStatus.RAN,
        "Your own middle value over the previous nights, with a band around it for how "
        "much you vary from night to night. This is your normal, not anybody else's.",
        headline_figure=f"{row['centre_bpm']:.0f} bpm",
        outputs={
            "centre_bpm": row["centre_bpm"],
            "scale_bpm": row["scale_bpm"],
            "usable_nights": row["usable_nights"],
            "rung": row["rung"],
            "shrink_weight": row["shrink_weight"],
        },
    )


def _detection_row(
    conn: sqlite3.Connection, subject_id: str, night_date: date
) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM detections WHERE subject_id = ? AND night_date = ?",
        (subject_id, night_date.isoformat()),
    ).fetchone()


def _subtract_step(detection: sqlite3.Row | None) -> PipelineStepView:
    """Anything about the night that already has an explanation is taken off first."""
    if detection is None:
        return _step(
            "subtract_explained",
            StepStatus.SKIPPED,
            "Nothing was compared for this night, so there was nothing to subtract from.",
        )

    explained = detection["explained_bpm"] or 0.0
    if not explained:
        return _step(
            "subtract_explained",
            StepStatus.NOT_APPLICABLE,
            "Nothing to subtract: no evening workout was recorded for this night.",
            outputs={"explained_bpm": 0.0},
        )

    return _step(
        "subtract_explained",
        StepStatus.RAN,
        "A recorded evening workout raises resting heart rate for a while afterwards. "
        "That much was taken off before anything was judged, so exercise is not mistaken "
        "for illness.",
        headline_figure=f"-{explained:.1f} bpm",
        outputs={"explained_bpm": explained, "residual_bpm": detection["residual_bpm"]},
    )


def _detect_step(detection: sqlite3.Row | None) -> PipelineStepView:
    """Green, yellow or red, and whether that was enough to look into."""
    if detection is None:
        return _step(
            "detect",
            StepStatus.SKIPPED,
            "This night was never compared against your normal, which happens when it "
            "had no usable reading.",
        )

    reasons = json.loads(detection["reasons_json"]) if detection["reasons_json"] else []
    level = detection["level"]
    flagged = bool(detection["flagged"])

    if level == "NA":
        reason = "There was not enough of this night measured to judge it either way."
    elif flagged:
        reason = (
            "This night was far enough above your own normal, for long enough, to be "
            "worth looking into. Opening an investigation is the only thing this decides."
        )
    else:
        reason = (
            "This night was compared against your own band and did not meet the bar for "
            "looking into further."
        )

    return _step(
        "detect",
        StepStatus.RAN,
        reason,
        headline_figure=level,
        outputs={
            "level": level,
            "flagged": flagged,
            "deviation_bpm": detection["deviation_bpm"],
            "residual_bpm": detection["residual_bpm"],
            "robust_z": detection["robust_z"],
            "reasons": reasons,
        },
    )


def get_night_pipeline(
    subject_id: str,
    night_date: date,
    conn: sqlite3.Connection | None = None,
) -> NightPipeline:
    """Every step of one night, in the order it happened.

    Returns a pipeline for any night in range, including nights with no reading and
    nights nothing looked at, because those are the nights a screen currently cannot
    explain at all.
    """
    close_conn = False
    if conn is None:
        conn = connect()
        apply_schema(conn)
        close_conn = True

    try:
        tz_name = _subject_timezone(conn, subject_id)
        detail = get_night_detail(subject_id, night_date, conn=conn)
        detection = _detection_row(conn, subject_id, night_date)

        from wha.features.sleep_window import resolve_sleep_window

        window = resolve_sleep_window(conn, subject_id, night_date, tz_name)

        features_row = conn.execute(
            "SELECT rhr_window_source FROM nightly_features "
            "WHERE subject_id = ? AND night_date = ?",
            (subject_id, night_date.isoformat()),
        ).fetchone()
        stored_source = features_row["rhr_window_source"] if features_row is not None else None

        steps = [
            _collect_step(conn, subject_id, window.start_utc, window.end_utc),
            _store_step(conn, subject_id, window.start_utc, window.end_utc),
            _sleep_window_step(conn, subject_id, night_date, tz_name, stored_source),
            _features_step(conn, subject_id, night_date),
            _baseline_step(conn, subject_id, night_date),
            _subtract_step(detection),
            _detect_step(detection),
        ]

        headline = PipelineHeadline(
            level=detail.row.level,
            flagged=bool(detection["flagged"]) if detection is not None else False,
            sleep_hours=detail.features.sleep_hours,
            coverage_minutes=detail.features.coverage_minutes,
        )

        return NightPipeline(
            subject_id=subject_id,
            night_date=night_date,
            episode_id=detail.row.episode_id,
            headline=headline,
            steps=steps,
        )
    finally:
        if close_conn:
            conn.close()


def list_pipeline_nights(
    subject_id: str,
    days: int = 60,
    conn: sqlite3.Connection | None = None,
) -> list[PipelineNightRef]:
    """Just enough about each night to draw the stepper.

    Built from `list_nights` rather than from its own query, so the stepper and the
    History table can never disagree about which nights exist.
    """
    end = local_today()
    start = end - timedelta(days=days)
    rows = list_nights(subject_id, start=start, end=end, conn=conn)
    return [
        PipelineNightRef(
            night_date=row.night_date,
            level=row.level or DetectionLevel.NA,
            has_episode=row.episode_id is not None,
            usable=row.usable,
        )
        for row in rows
    ]
