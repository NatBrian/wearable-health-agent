"""Unsolicited symptom reports.

Every route into the safety floor ran through a question the agent had chosen to ask,
and the agent only asks inside an open episode, which only opens when the detector
flags a night. So a person could report crushing chest pain on a night their heart rate
looked ordinary and nothing whatsoever would happen.

That is backwards. The deterministic floor exists precisely because it must not depend
on the system having already decided something was wrong. A report of a Tier A symptom
escalates on its own, regardless of what the sensors saw.
"""

import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from wha.db import apply_schema, connect
from wha.models import Disposition
from wha.safety.models import SafetyCheckResult
from wha.safety.tier_c import check_red_flags_with_tier_c
from wha.service.episode_lifecycle import close_episode, get_open_episode


@dataclass(frozen=True)
class SymptomReportResult:
    """Outcome of a person volunteering how they feel."""

    subject_id: str
    text: str
    escalated: bool
    level: str | None
    triggered_flags: list[str] = field(default_factory=list)
    guidance: list[str] = field(default_factory=list)
    episode_id: str | None = None
    disposition: str | None = None


def report_symptoms(
    subject_id: str,
    text: str,
    conn: sqlite3.Connection | None = None,
    db_path: Path | None = None,
) -> SymptomReportResult:
    """Run a free-text symptom report through the deterministic floor and Tier C.

    An escalation closes any open episode as ESCALATED and records one, so the outcome is
    visible in history rather than existing only as a message the person has to remember.
    """
    close_conn = False
    if conn is None:
        conn = connect(db_path) if db_path is not None else connect()
        apply_schema(conn)
        close_conn = True

    try:
        safety: SafetyCheckResult = check_red_flags_with_tier_c(user_text=text)

        if not safety.escalate:
            return SymptomReportResult(
                subject_id=subject_id,
                text=text,
                escalated=False,
                level=None,
            )

        existing = get_open_episode(conn, subject_id)
        if existing is not None:
            episode_id = str(existing["episode_id"])
        else:
            episode_id = f"ep_{uuid.uuid4().hex[:12]}"
            today = datetime.now(UTC).date()
            baseline = conn.execute(
                """SELECT usable_nights, rung FROM baselines
                   WHERE subject_id = ? ORDER BY night_date DESC LIMIT 1""",
                (subject_id,),
            ).fetchone()
            conn.execute(
                """INSERT INTO episodes
                     (episode_id, subject_id, thread_id, opened_on, state,
                      baseline_nights, baseline_rung, step_count, tool_call_count, depth_used)
                   VALUES (?, ?, ?, ?, 'OPEN', ?, ?, 0, 0, 0)""",
                (
                    episode_id,
                    subject_id,
                    episode_id,
                    today.isoformat(),
                    int(baseline["usable_nights"]) if baseline else 0,
                    str(baseline["rung"]) if baseline else "COLD",
                ),
            )
            conn.commit()

        close_episode(conn, episode_id, Disposition.ESCALATED)

        return SymptomReportResult(
            subject_id=subject_id,
            text=text,
            escalated=True,
            level=safety.level,
            triggered_flags=list(safety.triggered_flags),
            guidance=list(safety.guidance),
            episode_id=episode_id,
            disposition=Disposition.ESCALATED.value,
        )
    finally:
        if close_conn:
            conn.close()
