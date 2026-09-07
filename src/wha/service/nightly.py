"""Deterministic nightly batch calculation service."""

import json
import sqlite3
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from wha.audit.monitor import record_data_safety_escalation
from wha.clock import local_date_of, now_utc
from wha.config import get_settings
from wha.constants import INGEST_STALE_REFUSE_HOURS
from wha.db import apply_schema, connect
from wha.detect import detect_range
from wha.features.derivation import compute_range
from wha.models import Detection, DetectionLevel, NightlyFeatures
from wha.safety.models import SafetyCheckResult
from wha.safety.rules import check_overnight_oxygen, check_red_flags_deterministic
from wha.service.episode_lifecycle import (
    check_close_conditions,
    get_open_episode,
    monitoring_since,
    open_episodes_for_flagged_nights,
    open_or_append_episode,
)


def _should_escalate_again(
    conn: sqlite3.Connection,
    episode_id: str,
    detection: Detection,
) -> str | None:
    """Whether to escalate again, and which kind of repeat it would be.

    Once per investigation was the rule, for a good reason: night scoring re-runs every
    few hours and a first sync backfills weeks, so an unguarded send repeats the same
    message endlessly.

    It also meant two silences that should not exist. Somebody already being escalated
    about who then got materially WORSE heard nothing. And somebody whose reading simply
    STAYED far outside their own range, night after night, heard nothing either, which
    reads as "nothing new" when it means "still far outside your range".

    Returns "first", "worse", "still", or None for stay quiet.
    """
    from wha.constants import ESCALATION_REPEAT_NIGHTS, ESCALATION_REPEAT_ROBUST_Z_RISE

    rows = conn.execute(
        """SELECT payload_json FROM notifications
            WHERE episode_id = ? AND kind = 'ESCALATION'
            ORDER BY queued_at_utc DESC""",
        (episode_id,),
    ).fetchall()
    if not rows:
        return "first"

    current = abs(detection.robust_z) if detection.robust_z is not None else None
    if current is None:
        return None

    previous: float | None = None
    last_night: date | None = None
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except (TypeError, ValueError):
            continue
        value = payload.get("robust_z")
        if value is not None:
            previous = abs(float(value))
            try:
                last_night = date.fromisoformat(str(payload.get("night") or ""))
            except ValueError:
                last_night = None
            break

    if previous is None:
        # Escalations sent before this was recorded carry no reading to compare against.
        # Not sending cannot spam, but it is also how somebody stops hearing about getting
        # worse, so it is recorded as a limitation rather than treated as correct.
        return None

    if (current - previous) >= ESCALATION_REPEAT_ROBUST_Z_RISE:
        return "worse"

    # Still extreme, and long enough since anything was said. A reading that holds at this
    # level is not good news, and silence after a warning reads as though it were.
    # "Still" has to mean still. A reading that has come down by a full deviation is not
    # the same situation, even if it has not come all the way down, and telling somebody it
    # is still far outside their range when it is improving would be false.
    improved = (previous - current) >= ESCALATION_REPEAT_ROBUST_Z_RISE
    if (
        not improved
        and last_night is not None
        and (detection.night_date - last_night).days >= ESCALATION_REPEAT_NIGHTS
    ):
        return "still"

    return None


def parse_date_range(range_str: str | None, tz_name: str = "Asia/Singapore") -> tuple[date, date]:
    """Parse a range string 'YYYY-MM-DD:YYYY-MM-DD' or single date, or default to last 7 nights."""
    if range_str is None:
        end_d = local_date_of(now_utc(), tz_name)
        start_d = end_d - timedelta(days=6)
        return start_d, end_d

    if ":" in range_str:
        start_part, end_part = range_str.split(":", 1)
        return date.fromisoformat(start_part.strip()), date.fromisoformat(end_part.strip())

    single_d = date.fromisoformat(range_str.strip())
    return single_d, single_d


def run_nightly(
    subject_id: str | None = None,
    date_or_range: str | None = None,
    db_path: Path | None = None,
    no_ingest: bool = True,
) -> list[Detection]:
    """Execute nightly feature calculation, baseline update, and anomaly detection."""
    settings = get_settings()
    subj = subject_id if subject_id is not None else settings.subject
    target_db = db_path if db_path is not None else settings.db_path

    target_db.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(target_db)
    apply_schema(conn)

    # Resolve subject timezone
    row = conn.execute("SELECT timezone FROM subjects WHERE subject_id = ?", (subj,)).fetchone()
    tz_name = row[0] if row else settings.timezone

    start_date, end_date = parse_date_range(date_or_range, tz_name)

    # Check for raw samples
    sample_count = conn.execute(
        "SELECT COUNT(*) FROM heart_rate_samples WHERE subject_id = ?", (subj,)
    ).fetchone()[0]

    # Only derive features from raw samples if raw samples exist for subject
    if sample_count > 0:
        features_list = compute_range(conn, subj, start_date, end_date)
    else:
        # If nightly_features were directly inserted in tests or precomputed, query them
        feat_rows = conn.execute(
            """
            SELECT night_date, rhr_bpm, coverage_minutes, usable
            FROM nightly_features
            WHERE subject_id = ? AND night_date >= ? AND night_date <= ?
            ORDER BY night_date ASC
            """,
            (subj, start_date.isoformat(), end_date.isoformat()),
        ).fetchall()

        features_list = [
            NightlyFeatures(
                subject_id=subj,
                night_date=date.fromisoformat(r[0]),
                rhr_bpm=r[1],
                coverage_minutes=r[2],
                usable=bool(r[3]),
            )
            for r in feat_rows
        ]

    # Check staleness: if latest sample is older than INGEST_STALE_REFUSE_HOURS
    last_sample_row = conn.execute(
        "SELECT MAX(ts_utc) FROM heart_rate_samples WHERE subject_id = ?",
        (subj,),
    ).fetchone()
    if last_sample_row and last_sample_row[0]:
        try:
            last_sample_dt = datetime.fromisoformat(last_sample_row[0])
            for feat in features_list:
                feat_midnight = datetime(
                    feat.night_date.year,
                    feat.night_date.month,
                    feat.night_date.day,
                    tzinfo=UTC,
                )
                if (feat_midnight - last_sample_dt) > timedelta(hours=INGEST_STALE_REFUSE_HOURS):
                    conn.execute(
                        """
                        UPDATE nightly_features
                        SET usable = 0
                        WHERE subject_id = ? AND night_date = ?
                        """,
                        (subj, feat.night_date.isoformat()),
                    )
        except (ValueError, TypeError):
            pass

    # Run detection
    detections = detect_range(conn, subj, start_date, end_date)

    # The safety floor, over the DATA rather than only over what the person typed.
    #
    # Three rules were written, tested on their own and connected to nothing. Line coverage
    # over a full production run showed src/wha/safety/rules.py lines 162 to 178 and 253 to
    # 266 never executing. All three places that ran the safety check passed only free
    # text, so `robust_z` was always None and the two extreme heart rate branches were
    # skipped, and `check_overnight_oxygen` had no caller at all.
    #
    # A floor that only fires on what you say is not a floor on your data.
    run_data_safety_floor(conn, subj, detections, tz_name)

    # Open the investigation. Detection previously ended here, so a flagged night set a
    # boolean and nothing ever acted on it: no episode existed for the agent to advance,
    # and the link between the monitor and the investigation was absent entirely.
    open_episodes_for_flagged_nights(conn, subj, detections)

    open_episode = get_open_episode(conn, subj)
    if open_episode is not None:
        check_close_conditions(conn, str(open_episode["episode_id"]), detections)

    conn.close()
    return detections


def get_monitoring_since(subject_id: str | None = None, db_path: Path | None = None) -> date | None:
    """When monitoring began for a subject, for callers that need to label history."""
    settings = get_settings()
    subj = subject_id if subject_id is not None else settings.subject
    conn = connect(db_path) if db_path is not None else connect()
    apply_schema(conn)
    try:
        return monitoring_since(conn, subj)
    finally:
        conn.close()


def run_data_safety_floor(
    conn: sqlite3.Connection,
    subject_id: str,
    detections: list[Detection],
    tz_name: str,
) -> list[SafetyCheckResult]:
    """Run the deterministic rules that judge the DATA, not the person's words.

    Three rules had never executed in production. Two need `robust_z` and the baseline
    rung, which only the detector has; the third needs a night of blood oxygen readings
    inside the sleep window, and nothing anywhere called it.

    Measured before connecting it, because this is the one change that can newly wake
    somebody at three in the morning. Across 7,079 scorable nights of the Mishra 2020
    cohort, `abs(robust_z) > 6` fires on 33 of them, which is one alert per 31
    person-weeks. Reproduce with `uv run python experiments/detection/cohort/band_width.py`. That rate is
    a rare event rather than a stream, and the rules' own guidance is conditional
    same-day advice, not an ambulance.

    Returns what fired, for the caller and for tests. Never raises: a failure here must
    not cost the night's reading.
    """
    from wha.features.sleep_window import resolve_sleep_window
    from wha.service.symptom_report import notify_escalation

    fired: list[SafetyCheckResult] = []

    for detection in sorted(detections, key=lambda d: d.night_date):
        if detection.level == DetectionLevel.NA or detection.robust_z is None:
            continue

        row = conn.execute(
            """SELECT b.rung AS rung, f.rhr_bpm AS rhr_bpm
                 FROM baselines b
                 LEFT JOIN nightly_features f
                   ON f.subject_id = b.subject_id AND f.night_date = b.night_date
                WHERE b.subject_id = ? AND b.night_date = ?""",
            (subject_id, detection.night_date.isoformat()),
        ).fetchone()
        rung = row["rung"] if row is not None else None
        # The night's actual reading, not the deviation. The cold-rung fallback in
        # red_flags.yaml compares an absolute bpm, so handing it a residual would compare
        # a 5 bpm rise against a 100 bpm bound and never fire.
        rhr_bpm = row["rhr_bpm"] if row is not None else None

        results: list[SafetyCheckResult] = []

        # The two extreme heart rate rules. No free text: this is the data speaking.
        vitals = check_red_flags_deterministic(
            user_text=None,
            robust_z=detection.robust_z,
            rhr_bpm=rhr_bpm,
            rung=rung,
        )
        if vitals.escalate:
            results.append(vitals)

        # Blood oxygen, over the same window the night's heart rate was measured over.
        # It gets no likelihood in causes.yaml because no published study relates a
        # wearable reading to any of the twelve causes, so it lives here as a cited
        # threshold that can raise urgency and never lower it.
        try:
            window = resolve_sleep_window(conn, subject_id, detection.night_date, tz_name)
            oxygen = check_overnight_oxygen(conn, subject_id, window.start_utc, window.end_utc)
        except Exception:  # noqa: BLE001
            oxygen = None
        if oxygen is not None and oxygen.escalate:
            results.append(oxygen)

        for result in results:
            fired.append(result)
            episode_id = open_or_append_episode(conn, subject_id, detection.night_date)
            record_data_safety_escalation(conn, subject_id, episode_id, detection, result)

            # One notification path, the one that already exists, so an escalation raised
            # by the data reaches the person the same way one raised by their own words
            # does. A second path is how the first one ended up notifying nobody.
            #
            # Once per episode, not once per night. A first sync backfills weeks of
            # history and this job re-scores a rolling window every few hours, so an
            # unguarded send would put the same escalation on somebody's phone repeatedly.
            reason = _should_escalate_again(conn, episode_id, detection)
            if reason:
                notify_escalation(
                    conn, subject_id, episode_id, result, detection=detection, reason=reason
                )

    return fired
