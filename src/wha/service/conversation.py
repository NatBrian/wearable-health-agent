"""Conversation, for the interface layer.

The engine and its safety checks live in :mod:`wha.agent.conversation`. This is the thin
seam the dashboard and the CLI talk to, so neither reaches into the agent directly.
"""

import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from wha.agent.conversation import ConversationReply, load_transcript, respond
from wha.agent.conversation import established_urgency as _established_urgency
from wha.db.connection import connect
from wha.db.migrations import apply_schema
from wha.retrieve.attribution import ATTRIBUTION_NOTE, is_external, source_label


def _open(conn: sqlite3.Connection | None, db_path: Path | None) -> tuple[sqlite3.Connection, bool]:
    if conn is not None:
        return conn, False
    opened = connect(db_path)
    apply_schema(opened)
    return opened, True


def get_transcript(
    subject_id: str,
    limit: int = 40,
    conn: sqlite3.Connection | None = None,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Every turn of the conversation, oldest first."""
    connection, close = _open(conn, db_path)
    try:
        return load_transcript(connection, subject_id, limit=limit)
    finally:
        if close:
            connection.close()


def get_conversation_sessions(
    subject_id: str,
    limit_turns: int = 400,
    since_night: date | None = None,
    conn: sqlite3.Connection | None = None,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """The conversation split into the consultations it actually was, newest first.

    The agent has always had this notion: `_turns_this_session` ends a session after a gap
    of CONVERSATION_SESSION_GAP_HOURS, so picking the phone up the next morning starts a
    new one. The screen did not, and showed the last forty turns whatever night they came
    from, so a question about Sunday sat under Monday's verdict reading as though it were
    about Monday.

    Grouped here rather than in a screen, and by the same constant the agent uses, so the
    two cannot end up disagreeing about where a conversation stopped.

    `since_night` additionally drops everything that happened before that night began in
    the person's own timezone. A conversation about Sunday is about Sunday: once Monday
    has been measured it belongs to the record rather than under Monday's verdict, and six
    hours of silence is not the same boundary as a new night.
    """
    from datetime import timedelta
    from zoneinfo import ZoneInfo

    from wha.constants import CONVERSATION_SESSION_GAP_HOURS
    from wha.db.iso import from_iso

    connection, close = _open(conn, db_path)
    try:
        turns = load_transcript(connection, subject_id, limit=limit_turns)
    finally:
        if close:
            connection.close()

    gap = timedelta(hours=CONVERSATION_SESSION_GAP_HOURS)
    sessions: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    previous = None

    for turn in turns:  # oldest first
        try:
            stamp = from_iso(turn["created_at_utc"])
        except (TypeError, ValueError, KeyError):
            stamp = None
        if current and previous is not None and stamp is not None and (stamp - previous) > gap:
            sessions.append({"started_utc": current[0].get("created_at_utc"), "turns": current})
            current = []
        current.append(turn)
        if stamp is not None:
            previous = stamp

    if current:
        sessions.append({"started_utc": current[0].get("created_at_utc"), "turns": current})

    sessions.reverse()

    if since_night is None:
        return sessions

    connection, close = _open(conn, db_path)
    try:
        row = connection.execute(
            "SELECT timezone FROM subjects WHERE subject_id = ?", (subject_id,)
        ).fetchone()
    finally:
        if close:
            connection.close()

    tz_name = (row["timezone"] if row and row["timezone"] else None) or "UTC"
    try:
        zone = ZoneInfo(tz_name)
    except Exception:  # noqa: BLE001 - a bad timezone must not hide a conversation
        zone = ZoneInfo("UTC")

    boundary = datetime(
        since_night.year, since_night.month, since_night.day, 0, 0, tzinfo=zone
    ).astimezone(UTC)

    # A conversation still in progress is kept whatever night it started under.
    #
    # Scoping on the night boundary alone hid a reply the moment it was written: the night
    # on screen can begin after the conversation about it. That is guaranteed while the
    # watch is being simulated forward, where the newest night is dated tomorrow, and it
    # happens in ordinary use too whenever somebody asks about a night late in the evening.
    # A person typing a question and watching nothing appear is the worst outcome here, so
    # a live session wins over the boundary.
    now = datetime.now(UTC)
    live_after = now - gap

    kept = []
    for index, session in enumerate(sessions):
        last = session["turns"][-1].get("created_at_utc")
        stamp = None
        try:
            stamp = from_iso(last) if last else None
        except (TypeError, ValueError):
            stamp = None

        # The live exception exists for one case: something said moments ago, which must
        # never be filed as history before the person has seen the reply. So it applies
        # only to the newest conversation, and only when that conversation really is
        # recent by the wall clock.
        #
        # Both bounds matter. Without the upper one, a record dated ahead of the clock,
        # which is what a simulated watch produces, makes every conversation look live.
        # Without the "newest only" rule, an old conversation that happens to sit inside
        # the window surfaces under a night it has nothing to do with.
        live = index == 0 and stamp is not None and live_after <= stamp <= now
        if stamp is None or stamp >= boundary or live:
            kept.append(session)
    return kept


def latest_urgency(
    subject_id: str,
    conn: sqlite3.Connection | None = None,
    db_path: Path | None = None,
) -> str | None:
    """The most urgent level any rule has reached. Monotone: it never falls."""
    connection, close = _open(conn, db_path)
    try:
        return _established_urgency(connection, subject_id)
    finally:
        if close:
            connection.close()


def urgency_banner(
    subject_id: str,
    conn: sqlite3.Connection | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """What to show above the page: the urgency, when it was set, and how old it is."""
    from wha.agent.conversation import urgency_state

    connection, close = _open(conn, db_path)
    try:
        return urgency_state(connection, subject_id)
    finally:
        if close:
            connection.close()


def acknowledge_urgency(
    subject_id: str,
    conn: sqlite3.Connection | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """The person says they have seen somebody. Stops the banner, keeps the record."""
    from wha.agent.conversation import urgency_state
    from wha.audit.monitor import record_urgency_acknowledged

    connection, close = _open(conn, db_path)
    try:
        state = urgency_state(connection, subject_id)
        if state["urgency"] is not None:
            record_urgency_acknowledged(
                connection, subject_id, str(state["urgency"]), state["set_on"]
            )
        return urgency_state(connection, subject_id)
    finally:
        if close:
            connection.close()


def latest_urgency_reason(
    subject_id: str,
    conn: sqlite3.Connection | None = None,
    db_path: Path | None = None,
) -> str:
    """What the rule that set the urgency actually said, in its own published words."""
    connection, close = _open(conn, db_path)
    try:
        row = connection.execute(
            """SELECT triggered_flags_json, urgency FROM conversation_turns
                WHERE subject_id = ? AND urgency IS NOT NULL
                ORDER BY seq DESC LIMIT 1""",
            (subject_id,),
        ).fetchone()
        if row is None:
            return ""

        from wha.safety.triage import load_triage_rules, rule_for

        answers = connection.execute(
            "SELECT presentation FROM triage_answers WHERE subject_id = ? LIMIT 1",
            (subject_id,),
        ).fetchone()
        if answers is None:
            return ""

        rule = rule_for(answers["presentation"], load_triage_rules())
        if rule is None:
            return ""
        return (
            f"This used the {rule.label}, a decision rule for this that works from what "
            f"you can tell it, with no tests. It comes from {rule.citation_plain.strip()}."
        )
    finally:
        if close:
            connection.close()


def send_message(
    subject_id: str,
    text: str,
    episode_id: str | None = None,
    episode_summary: str = "",
    age_years: int | None = None,
    conn: sqlite3.Connection | None = None,
    db_path: Path | None = None,
    notify_on_escalation: bool = True,
) -> ConversationReply:
    """One turn of conversation, with every deterministic check applied around the model.

    When the rules raise the urgency, the phone is told, whichever surface the person was
    typing on. Someone who reaches an escalation in the dashboard and then closes the laptop
    should not be the only place that escalation exists.
    """
    connection, close = _open(conn, db_path)
    try:
        before = _established_urgency(connection, subject_id)
        reply = respond(
            connection,
            subject_id=subject_id,
            user_message=text,
            episode_id=episode_id,
            episode_summary=episode_summary,
            age_years=age_years,
        )
        if notify_on_escalation and reply.urgency is not None and reply.urgency != before:
            _push_escalation(subject_id, reply)
        return reply
    finally:
        if close:
            connection.close()


def _push_escalation(subject_id: str, reply: ConversationReply) -> None:
    """Tell the phone that the urgency changed. Never raises into the conversation."""
    try:
        from wha.notify import get_notifier
        from wha.notify.protocol import MessageKind

        get_notifier().send(
            recipient_id=subject_id,
            kind=MessageKind.ESCALATION,
            text=format_for_telegram(reply),
        )
    except Exception:  # noqa: BLE001
        # A transport failure must not stop the conversation or lose the reply. The
        # urgency is already recorded on the turn, so the dashboard still shows it.
        return


def format_for_telegram(reply: ConversationReply, max_chars: int = 900) -> str:
    """One phone message carrying the reply, its urgency and what has no source.

    The uncited marker travels with the text. On a phone there is no amber panel to put it
    in, and a sentence the model made up must not arrive looking the same as one with a
    study behind it. Draelos et al. 2025 measured 5 to 13 percent of unguarded
    frontier-model answers to patient questions as outright unsafe.
    """
    # Split by what must survive a trim. A phone message is short and something has to go
    # first; deciding that by position is how a cut once landed inside the amber block,
    # keeping its label and losing the warning it carried.
    essential: list[str] = []
    parts: list[str] = []

    if reply.urgency == "urgent":
        essential.append("THIS NEEDS MEDICAL ATTENTION TODAY.")
    elif reply.urgency == "same_day":
        essential.append("You should see a doctor today.")

    essential.append(reply.text)

    if reply.uncited:
        # Essential. A sentence the model invented must not arrive looking like one with a
        # study behind it, and dropping this block is exactly that.
        essential.append(
            "Not from a cited source (the AI's own general knowledge, worth checking): "
            + " ".join(reply.uncited)
        )
    if reply.citations:
        # Name the source in words, not just the topic title. The dashboard labels a quoted
        # passage "MedlinePlus, National Library of Medicine"; this path said
        # `Sources: Fever`, which credits nobody, under a licence that is
        # attribution-only. The labels used to live under ui/, which this module correctly
        # refuses to import, so the phone had no way to reach them.
        named: dict[str, list[str]] = {}
        for citation in reply.citations:
            named.setdefault(source_label(citation.source_id), []).append(citation.title)
        parts.append(
            "Sources: "
            + "; ".join(
                f"{title} ({label})"
                for label, titles in named.items()
                for title in dict.fromkeys(titles)
            )
        )
        if any(is_external(c.source_id) for c in reply.citations):
            parts.append(ATTRIBUTION_NOTE)
    if reply.urgency:
        parts.append("Decided by a fixed rule from what you told it. The AI cannot lower it.")

    return _trim_to_whole_sentences(essential, parts, max_chars)


# The amber block travels as one piece or not at all. A trim that lands inside it turns a
# warning that a sentence has no source behind it into a sentence that reads as sourced,
# which is what happened in a real message.
_UNCITED_MARKER = "Not from a cited source"


def _trim_to_whole_sentences(essential: list[str], optional: list[str], max_chars: int) -> str:
    """Fit the message by dropping optional blocks, then whole sentences. Never mid-word.

    Messages were cut at 900 characters wherever that fell. In one real message the cut
    landed inside the "not from a cited source" block, so its label survived and the
    warning it carried did not, which is the one trim this must never make.

    Nothing in `essential` is dropped: the urgency line, the reply itself, and the amber
    block all survive. If those alone do not fit, the REPLY is cut back to a sentence
    boundary and the blocks around it stay whole.
    """
    must = [p for p in essential if p]
    extra = [p for p in optional if p]

    while extra and len("\n\n".join(must + extra)) > max_chars:
        extra.pop()

    text = "\n\n".join(must + extra)
    if len(text) <= max_chars or not must:
        return text[:max_chars] if len(text) > max_chars else text

    # Only the essential blocks are left and they still do not fit. The reply is the last
    # of them unless the amber block is present, in which case it is the one before.
    reply_at = len(must) - 2 if len(must) >= 2 and _UNCITED_MARKER in must[-1] else len(must) - 1
    around = "\n\n".join(must[:reply_at] + must[reply_at + 1 :])
    budget = max_chars - len(around) - (2 if around else 0)

    # Three characters reserved for the ellipsis. A message that just stops reads as a
    # delivery failure; one that ends "..." says plainly that there was more.
    cut = must[reply_at][: max(0, budget - 3)]
    boundary = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    trimmed = (cut[: boundary + 1] if boundary > 0 else cut.rstrip()).strip()
    must[reply_at] = f"{trimmed}..."
    return "\n\n".join(p for p in must if p)


def converse_over_telegram(
    text: str,
    subject_id: str | None = None,
    conn: sqlite3.Connection | None = None,
    db_path: Path | None = None,
) -> tuple[ConversationReply, str]:
    """A turn that arrived from the phone, and the message to send back to it.

    Free text with no pending question used to be answered with "Please check your health
    dashboard for episode status and history." The phone is where the person actually is,
    and that reply is a brush-off rather than a conversation.
    """
    from wha.config import get_subject

    reply = send_message(
        subject_id=subject_id or get_subject(),
        text=text,
        conn=conn,
        db_path=db_path,
    )
    return reply, format_for_telegram(reply)
