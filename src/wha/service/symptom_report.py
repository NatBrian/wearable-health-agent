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
from datetime import date
from pathlib import Path
from typing import Any

from wha.clock import local_today
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

    NARROWED to the demo harness on 5 September 2026, and it is no longer a second
    escalation path.

    This and `wha.agent.conversation.respond` were two implementations of "check what the
    person said and escalate", and they behaved differently. "I have chest pain" typed at
    the command line came here and went straight to an ambulance; typed in the dashboard it
    opened a Marburg conversation and asked about exertion first. Same words, same system,
    two answers.

    Worse, only this one opened an episode and it opened a NEW one every time, so the live
    database holds five identical closed escalated episodes with the same dates, never
    investigated, each shown separately on History.

    `wha tell` now calls `send_message` like every other surface. What remains here is the
    deterministic half without a model, which is what the frozen scenarios need: they must
    run unattended and reproducibly, and a conversation is neither.

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
            today = local_today()
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

        # Close on the last night considered, not on the clock. Leaving this to default
        # produced closed_on earlier than opened_on for an episode opened by the detector,
        # the same inversion that broke History's date ranges and the illness-night
        # exclusion elsewhere.
        opened_row = conn.execute(
            "SELECT opened_on FROM episodes WHERE episode_id = ?", (episode_id,)
        ).fetchone()
        opened = date.fromisoformat(opened_row["opened_on"]) if opened_row else local_today()
        last_row = conn.execute(
            """SELECT MAX(night_date) AS n FROM detections
                WHERE subject_id = ? AND night_date >= ?""",
            (subject_id, opened.isoformat()),
        ).fetchone()
        closing = (
            max(opened, date.fromisoformat(last_row["n"])) if last_row and last_row["n"] else opened
        )
        close_episode(conn, episode_id, Disposition.ESCALATED, closing)

        # Tell the person, on the channel they are reachable on.
        #
        # An escalation closed the episode and recorded nothing else: no notification row
        # existed, so somebody told to seek urgent care received no message at all. The
        # guidance sat in a returned object that the caller might or might not display.
        notify_escalation(conn, subject_id, episode_id, safety)

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


def notify_escalation(
    conn: sqlite3.Connection,
    subject_id: str,
    episode_id: str,
    safety: SafetyCheckResult,
    detection: Any = None,
    reason: str = "first",
) -> None:
    """Send the escalation guidance and record that it was sent.

    Public because the nightly job now raises escalations too, from rules that read the
    data rather than what the person typed. Both go out through this one function on
    purpose: a second notification path is how the first one ended up notifying nobody.

    Never raises into the caller: a transport failure must not stop the escalation being
    recorded, and the person still sees the guidance on screen.
    """
    from wha.agent.repository import EpisodeRepository
    from wha.notify.factory import get_notifier
    from wha.notify.protocol import MessageKind

    body = "This needs medical attention.\n\n" + "\n".join(safety.guidance)

    # A repeat says which kind of repeat it is, and asks. Resending the same sentence is
    # how a warning stops being read, and somebody who is worse, or who is still far
    # outside their range days later, is being told something different each time.
    ask_how_they_are = "\n\nHow are you feeling now? Reply here and I will record what you say."
    if reason == "worse":
        body = (
            "This has got worse since I last messaged you.\n\n"
            + "\n".join(safety.guidance)
            + ask_how_they_are
        )
    elif reason == "still":
        body = (
            "This is still far outside your usual range, and has been for several "
            "nights.\n\n" + "\n".join(safety.guidance) + ask_how_they_are
        )

    try:
        notifier = get_notifier()
        delivered = notifier.send(
            recipient_id=subject_id,
            kind=MessageKind.ESCALATION,
            text=body,
            interaction_id=episode_id,
        )
    except Exception:  # noqa: BLE001
        delivered = False

    if delivered:
        try:
            repo = EpisodeRepository(conn=conn)
            channel = getattr(get_notifier(), "channel", "none")
            repo.record_notification(
                interaction_id=episode_id,
                recipient=subject_id,
                kind="ESCALATION",
                channel=channel,
                episode_id=episode_id,
                extra={
                    "robust_z": getattr(detection, "robust_z", None),
                    "residual_bpm": getattr(detection, "residual_bpm", None),
                    "night": str(getattr(detection, "night_date", "") or ""),
                }
                if detection is not None
                else None,
            )
            repo.record_notification_sent(
                subject_id=subject_id,
                episode_id=episode_id,
                kind="ESCALATION",
                channel=channel,
                text=body,
            )
        except Exception:  # noqa: BLE001, S110
            pass
