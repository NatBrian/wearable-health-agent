"""Conversation, for the interface layer.

The engine and its safety checks live in :mod:`wha.agent.conversation`. This is the thin
seam the dashboard and the CLI talk to, so neither reaches into the agent directly.
"""

import sqlite3
from pathlib import Path
from typing import Any

from wha.agent.conversation import ConversationReply, load_transcript, respond
from wha.agent.conversation import established_urgency as _established_urgency
from wha.db.connection import connect
from wha.db.migrations import apply_schema


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
    parts: list[str] = []
    if reply.urgency == "urgent":
        parts.append("THIS NEEDS MEDICAL ATTENTION TODAY.")
    elif reply.urgency == "same_day":
        parts.append("You should see a doctor today.")

    parts.append(reply.text)

    if reply.uncited:
        parts.append(
            "Not from a cited source (the AI's own general knowledge, worth checking): "
            + " ".join(reply.uncited)
        )
    if reply.citations:
        titles = ", ".join(dict.fromkeys(c.title for c in reply.citations))
        parts.append(f"Sources: {titles}")
    if reply.urgency:
        parts.append("Decided by a fixed rule from what you told it. The AI cannot lower it.")

    text = "\n\n".join(p for p in parts if p)
    if len(text) > max_chars:
        text = text[: max_chars - 3].rstrip() + "..."
    return text


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
