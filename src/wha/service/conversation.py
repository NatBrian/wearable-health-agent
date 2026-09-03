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
) -> ConversationReply:
    """One turn of conversation, with every deterministic check applied around the model."""
    connection, close = _open(conn, db_path)
    try:
        return respond(
            connection,
            subject_id=subject_id,
            user_message=text,
            episode_id=episode_id,
            episode_summary=episode_summary,
            age_years=age_years,
        )
    finally:
        if close:
            connection.close()
