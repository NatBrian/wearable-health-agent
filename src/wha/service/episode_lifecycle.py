"""Opening and appending episodes from flagged nights.

Nothing in the application created an episode. Detection ran, set ``flagged`` on the
night a persistent run reached length, and returned; no code path anywhere took that
flag and opened an investigation. ``step_episode`` could only advance an episode row
that tests had inserted by hand, so in a real run the agent had nothing to advance and
the detect-to-investigate link did not exist.

The rules implemented here come from ``docs/CONTRACTS.md``:

* at most one non-CLOSED episode per subject, ever, asserted rather than assumed
* a night flagged while an episode is open is appended to it, not given a new episode
* an episode closes on a disposition, on EPISODE_MAX_NIGHTS elapsed, on the step or
  tool-call ceiling, or on a quiet run of DETECT_PERSISTENCE_NIGHTS green nights
"""

import sqlite3
import uuid
from datetime import date, datetime
from pathlib import Path

from wha.clock import local_date_of, local_today
from wha.constants import (
    DETECT_PERSISTENCE_NIGHTS,
    EPISODE_MAX_NIGHTS,
    EPISODE_RECURRENCE_LINK_DAYS,
)
from wha.db import apply_schema, connect
from wha.errors import ConfigError
from wha.models import BaselineRung, Detection, Disposition


class EpisodeConcurrencyError(ConfigError):
    """Raised when a second concurrent episode would be opened for one subject."""


def get_open_episode(conn: sqlite3.Connection, subject_id: str) -> sqlite3.Row | None:
    """The subject's single non-closed episode, or None."""
    return conn.execute(
        """SELECT * FROM episodes
           WHERE subject_id = ? AND state != 'CLOSED'
           ORDER BY opened_on DESC LIMIT 1""",
        (subject_id,),
    ).fetchone()


def _baseline_at(conn: sqlite3.Connection, subject_id: str, night: date) -> tuple[int, str]:
    """Usable night count and rung on or before a night, defaulting to a cold baseline."""
    row = conn.execute(
        """SELECT usable_nights, rung FROM baselines
           WHERE subject_id = ? AND night_date <= ?
           ORDER BY night_date DESC LIMIT 1""",
        (subject_id, night.isoformat()),
    ).fetchone()
    if row is None:
        return 0, BaselineRung.COLD.value
    return int(row["usable_nights"]), str(row["rung"])


def open_or_append_episode(
    conn: sqlite3.Connection,
    subject_id: str,
    trigger_night: date,
) -> str:
    """Open an episode for a flagged night, or append the night to the open one.

    Returns the episode id in both cases. Concurrency is asserted here, not left to
    convention: two open episodes would double-spend the interruption budget, split the
    evidence between them and make the differential meaningless.
    """
    existing = get_open_episode(conn, subject_id)
    if existing is not None:
        # Appending is represented by the episode simply continuing to cover later
        # nights; the belief model re-runs over the whole night sequence on the next tick.
        return str(existing["episode_id"])

    baseline_nights, rung = _baseline_at(conn, subject_id, trigger_night)
    episode_id = f"ep_{uuid.uuid4().hex[:12]}"

    # A recurrence is not a first-ever investigation, and this used to open one as though
    # it were. Somebody whose readings settled, whose episode closed, and who was flagged
    # again four days later got an agent that started from the same prior with no idea it
    # had met them the week before. That is exactly the information a clinician would want
    # first, and the system threw it away at the episode boundary.
    previous, gap_days = _preceding_episode(conn, subject_id, trigger_night)

    conn.execute(
        """INSERT INTO episodes
             (episode_id, subject_id, thread_id, opened_on, state,
              baseline_nights, baseline_rung, step_count, tool_call_count, depth_used,
              preceded_by_episode_id, days_since_previous)
           VALUES (?, ?, ?, ?, 'OPEN', ?, ?, 0, 0, 0, ?, ?)""",
        (
            episode_id,
            subject_id,
            episode_id,
            trigger_night.isoformat(),
            baseline_nights,
            rung,
            previous,
            gap_days,
        ),
    )
    conn.commit()

    # The assertion the contract asks for, checked after the write so a concurrent
    # opener cannot slip a second row past it unnoticed.
    open_count = conn.execute(
        "SELECT COUNT(*) AS n FROM episodes WHERE subject_id = ? AND state != 'CLOSED'",
        (subject_id,),
    ).fetchone()["n"]
    if open_count > 1:
        raise EpisodeConcurrencyError(
            f"Subject '{subject_id}' has {open_count} non-closed episodes. "
            "At most one is permitted."
        )

    return episode_id


def _preceding_episode(
    conn: sqlite3.Connection,
    subject_id: str,
    trigger_night: date,
) -> tuple[str | None, int | None]:
    """The investigation this one continues, if it is close enough to be the same illness.

    THE THRESHOLD IS EPISODE_RECURRENCE_LINK_DAYS AND IT IS CITED. Respiratory illness
    surveillance conventionally separates two illnesses into distinct episodes when they
    are at least seven symptom-free days apart. That is the illness class this system
    targets: the NightSignal, DETECT and Mishra cohorts are all respiratory.

    Checked against a second, independent case rather than taken on one source. Saddleback
    dengue is defined as defervescence of at least one day followed by a second fever peak
    one to two days later, and the second peak is the dangerous one. Seven days contains
    that gap comfortably, so a biphasic fever is scored as ONE illness recurring rather
    than as two unrelated events, which is the whole point.

    THE CLOCK RUNS ON SYMPTOMS WHERE THERE ARE ANY. The source counts symptom-free days,
    not reading-normal days, and substituting one for the other would be reading the
    citation to suit the data that happens to be on hand. Where no symptom was ever
    reported there is nothing else to count, so the gap falls back to the close date.

    A linked episode is still a separate row. Merging would break the one-open-episode
    invariant and rewrite a closed episode's disposition, and neither is worth it: what
    was missing is CONTEXT, and a pointer carries context.
    """
    row = conn.execute(
        """SELECT episode_id, closed_on FROM episodes
            WHERE subject_id = ? AND state = 'CLOSED' AND closed_on IS NOT NULL
            ORDER BY closed_on DESC LIMIT 1""",
        (subject_id,),
    ).fetchone()
    if row is None:
        return None, None

    try:
        closed = date.fromisoformat(str(row["closed_on"]))
    except (TypeError, ValueError):
        return None, None

    # Symptom-free days, where symptoms exist to count. The last night the person reported
    # anything is the end of the previous illness far more faithfully than the date an
    # algorithm closed a row.
    last_symptom: date | None = None
    try:
        srow = conn.execute(
            """SELECT MAX(night_date) AS n FROM symptom_observations
                WHERE subject_id = ? AND present = 1 AND night_date <= ?""",
            (subject_id, trigger_night.isoformat()),
        ).fetchone()
        if srow and srow["n"]:
            last_symptom = date.fromisoformat(str(srow["n"]))
    except sqlite3.Error:
        last_symptom = None

    reference = max(closed, last_symptom) if last_symptom is not None else closed
    gap = (trigger_night - reference).days
    if gap < 0 or gap >= EPISODE_RECURRENCE_LINK_DAYS:
        return None, None
    return str(row["episode_id"]), gap


def close_episode(
    conn: sqlite3.Connection,
    episode_id: str,
    disposition: Disposition | str,
    closed_on: date | None = None,
) -> None:
    """Close an episode with a disposition."""
    value = disposition.value if isinstance(disposition, Disposition) else str(disposition)
    conn.execute(
        """UPDATE episodes
           SET state = 'CLOSED', disposition = ?, closed_on = ?
           WHERE episode_id = ?""",
        (value, (closed_on or local_today()).isoformat(), episode_id),
    )
    conn.commit()


def _outstanding_symptom_ids(conn: sqlite3.Connection, subject_id: str, as_of: date) -> list[str]:
    """Symptoms the person reported and has never said were better. Never raises."""
    try:
        from wha.service.symptoms import outstanding_symptoms, symptom_as_of

        # The latest night on record, never earlier than today. A simulation dates nights
        # ahead and a first sync can too, and keying on the calendar alone makes an
        # outstanding symptom invisible, which lets an investigation close over it.
        return [
            run.flag_id
            for run in outstanding_symptoms(
                conn, subject_id, max(as_of, symptom_as_of(conn, subject_id))
            )
        ]
    except Exception:  # noqa: BLE001
        # A failure here must not hold an investigation open forever, so it degrades to
        # the previous behaviour rather than to a stuck episode.
        return []


def _announce_close(
    conn: sqlite3.Connection,
    episode_id: str,
    subject_id: str,
    disposition: Disposition,
    note: str | None = None,
) -> None:
    """Tell the person their investigation ended, and what it concluded.

    A time-based close notified NOBODY. The only code that ever messaged anyone about an
    outcome is the agent's conclude node, and neither of the closes in this file goes
    through it, so an investigation somebody had been messaged about could run its ten
    nights and end in total silence. They would find out by opening a dashboard, if they
    thought to look.

    That is not a cosmetic gap. This project's own rule is that silence after a warning is
    read as an all clear, and UNRESOLVED means the opposite: it went away without being
    explained. Saying nothing communicates the reassuring reading of an unreassuring
    outcome.

    Never raises: a transport failure must not leave an episode half closed.
    """
    from wha.notify.factory import get_notifier
    from wha.notify.protocol import MessageKind
    from wha.service.phrasing import disposition_message

    try:
        body = disposition_message(disposition, note)
        notifier = get_notifier()
        delivered = notifier.send(
            recipient_id=subject_id,
            kind=MessageKind.OUTCOME,
            text=body,
            interaction_id=episode_id,
        )
        if not delivered:
            return
        from wha.agent.repository import EpisodeRepository

        repo = EpisodeRepository(conn=conn)
        repo.record_notification_sent(
            subject_id=subject_id,
            episode_id=episode_id,
            kind="OUTCOME",
            channel=getattr(notifier, "channel", "none"),
            text=body,
        )
    except Exception:  # noqa: BLE001, S110
        pass


def check_close_conditions(
    conn: sqlite3.Connection,
    episode_id: str,
    detections: list[Detection] | None = None,
) -> str | None:
    """Close an episode on elapsed nights or on a quiet run. Returns the disposition used.

    A disposition reached by the agent closes the episode through the conclude node.
    These are the two time-based conditions, which nothing else checks.
    """
    row = conn.execute(
        "SELECT subject_id, opened_on, state FROM episodes WHERE episode_id = ?",
        (episode_id,),
    ).fetchone()
    if row is None or row["state"] == "CLOSED":
        return None

    # A person is looking at this conclusion right now. Do not close it under them.
    #
    # A pending QUESTION is already handled below, because it is a row in `interactions`.
    # A pending REVIEW is a parked graph interrupt and nothing here was looking for it, so
    # a quiet run closed an investigation as LIKELY_BENIGN while its draft was waiting to
    # be checked. The review then vanished: no decision in the audit trail, and no
    # `closed_unreviewed` either, leaving a record that showed a review requested and
    # never resolved.
    #
    # This is the second time a background job has walked through this checkpoint. The
    # first resumed the interrupt with a hardcoded "approve" and the record said a human
    # had done it. Nothing gets stuck by refusing here: REVIEW_TIMEOUT_HOURS still releases
    # the draft, and that path records that nobody approved it.
    if row["state"] == "AWAITING_HUMAN_REVIEW":
        return None

    opened = date.fromisoformat(row["opened_on"])
    today = local_today()
    # The night an episode closes ON comes from the data, not from the clock the code
    # happens to run under. Using today's date produced closed_on earlier than opened_on,
    # which made History read "2026-10-04 to 2026-09-03" and silently broke the rule that
    # excludes illness nights from a baseline, because `night_date BETWEEN opened_on AND
    # closed_on` matched an inverted range.
    last_row = conn.execute(
        """SELECT MAX(night_date) AS n FROM detections
            WHERE subject_id = ? AND night_date >= ?""",
        (row["subject_id"], row["opened_on"]),
    ).fetchone()
    closing = (
        max(opened, date.fromisoformat(last_row["n"])) if last_row and last_row["n"] else opened
    )

    if (today - opened).days >= EPISODE_MAX_NIGHTS:
        close_episode(conn, episode_id, Disposition.UNRESOLVED, closing)
        # AND SAY SO. This closed an investigation and told nobody: close_episode writes a
        # row, and the only code that notifies anyone is the agent's conclude node, which
        # a timeout close never reaches. So an investigation the person had been messaged
        # about ran for ten nights and ended in complete silence, discoverable only by
        # opening the dashboard and noticing. Silence after a warning reads as an all
        # clear, which is the opposite of what UNRESOLVED means.
        _announce_close(
            conn,
            episode_id,
            row["subject_id"],
            Disposition.UNRESOLVED,
            note=(
                f"It ran for {EPISODE_MAX_NIGHTS} nights without reaching an answer, which "
                "is as long as an investigation here is allowed to run. That is not an all "
                "clear. If you still feel unwell, tell me or see a doctor."
            ),
        )
        return Disposition.UNRESOLVED.value

    # A quiet run since the last flag closes the episode as benign, provided nothing is
    # still waiting on the person.
    pending = conn.execute(
        "SELECT 1 FROM interactions WHERE episode_id = ? AND status = 'PENDING' LIMIT 1",
        (episode_id,),
    ).fetchone()
    if pending is not None:
        return None

    recent = conn.execute(
        """SELECT level FROM detections
           WHERE subject_id = ? AND night_date >= ?
           ORDER BY night_date DESC LIMIT ?""",
        (row["subject_id"], opened.isoformat(), DETECT_PERSISTENCE_NIGHTS),
    ).fetchall()

    if len(recent) >= DETECT_PERSISTENCE_NIGHTS and all(r["level"] == "GREEN" for r in recent):
        # "Probably nothing to worry about" is a claim, and a claim needs looking.
        #
        # An episode that was never stepped, and so never gathered evidence or formed a
        # belief, used to close with the same reassuring disposition as one the agent had
        # actually investigated. In the simulation an episode opened, was stepped zero
        # times, and told the person their raised nights were probably nothing. Where
        # nothing was examined, the honest answer is that it went away without being
        # investigated, which is what UNRESOLVED means.
        step_row = conn.execute(
            "SELECT step_count FROM episodes WHERE episode_id = ?", (episode_id,)
        ).fetchone()
        investigated = step_row is not None and int(step_row["step_count"]) > 0

        # GREEN NIGHTS ARE NOT RECOVERY, and this is the line where that mattered most.
        #
        # A quiet run closed the investigation as "probably nothing" no matter what the
        # person had said about how they felt. Three separate findings say that inference
        # does not hold:
        #
        #   * In dengue the CRITICAL PHASE BEGINS AT DEFERVESCENCE. WHO and CDC both teach
        #     that patients may appear to improve exactly as they enter the dangerous
        #     window. Dengue is endemic where this system is used.
        #   * Faget's sign: relative bradycardia in typhoid, dengue, Legionella, Q fever
        #     and yellow fever. An ordinary pulse does not exclude an active infection.
        #   * Radin et al. measured resting heart rate taking 79 days on average to return
        #     to baseline after COVID symptom onset, against 24 for sleep. A reading that
        #     settles within two nights is not the signature of somebody recovering from an
        #     infection at all.
        #
        # So a green run is good evidence about the READING and close to none about the
        # PERSON. It may close the detection. It may not close the symptom.
        # AS OF TODAY, not as of `closing`. `closing` is the last night that has DATA,
        # which is the right date to stamp on the episode and the wrong one to ask this
        # question of: somebody who said this morning that their symptom had gone would
        # have had that retraction ignored, because it fell after the last scored night,
        # and their investigation would be held open on a symptom they had already
        # withdrawn. The person's latest word is what counts here.
        outstanding = _outstanding_symptom_ids(conn, str(row["subject_id"]), today)
        if outstanding:
            # Hold the investigation open so the follow-up rule gets its chance to ask.
            # EPISODE_MAX_NIGHTS still ends it, so this cannot park forever, and it ends
            # as UNRESOLVED rather than as an all clear.
            return None

        disposition = Disposition.LIKELY_BENIGN if investigated else Disposition.UNRESOLVED
        close_episode(conn, episode_id, disposition, closing)
        _announce_close(conn, episode_id, row["subject_id"], disposition)
        return disposition.value

    return None


def monitoring_since(conn: sqlite3.Connection, subject_id: str) -> date | None:
    """The date this subject's first sync happened, or None if the subject is unknown.

    The subject row is written on first ingest, so ``created_at_utc`` is the moment the
    person started being monitored. Nights before it are history the system was given, not
    nights it was watching.

    That column is UTC and night dates are local, so the two are only comparable after a
    conversion. Taking the first ten characters of the timestamp put a subject who
    installed at 01:41 in Singapore a whole day early, and the night before they installed
    was treated as one the system had been watching.
    """
    row = conn.execute(
        "SELECT created_at_utc, timezone FROM subjects WHERE subject_id = ?", (subject_id,)
    ).fetchone()
    if row is None or not row[0]:
        return None
    try:
        moment = datetime.fromisoformat(str(row[0]))
    except ValueError:
        return None
    return local_date_of(moment, row["timezone"])


def open_episodes_for_flagged_nights(
    conn: sqlite3.Connection,
    subject_id: str,
    detections: list[Detection],
) -> list[str]:
    """Open or append an episode for every flagged night the system was actually watching.

    This is the link between the deterministic monitor and the investigation.

    A first sync backfills weeks of history, and this ran over all of it with no notion of
    when monitoring began. Two elevated nights anywhere in that history opened an episode
    and the agent messaged the person about a night from before they owned the system.
    Those nights are still scored, because that is how the baseline learns the person, but
    they cannot raise an investigation.
    """
    started = monitoring_since(conn, subject_id)
    episode_ids: list[str] = []
    for detection in sorted(detections, key=lambda d: d.night_date):
        if not detection.flagged:
            continue
        if started is not None and detection.night_date < started:
            continue
        episode_id = open_or_append_episode(conn, subject_id, detection.night_date)
        if episode_id not in episode_ids:
            episode_ids.append(episode_id)
    return episode_ids


def open_episodes_for_subject(
    subject_id: str,
    detections: list[Detection],
    db_path: Path | None = None,
) -> list[str]:
    """Convenience wrapper that manages its own connection."""
    conn = connect(db_path) if db_path is not None else connect()
    apply_schema(conn)
    try:
        return open_episodes_for_flagged_nights(conn, subject_id, detections)
    finally:
        conn.close()
