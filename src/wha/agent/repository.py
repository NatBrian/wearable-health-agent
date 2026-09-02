"""Database adapter the agent nodes and tools read and write through.

The nodes, the tool registry and the seven tool implementations were all written
against a duck-typed ``db`` object, guarded by ``hasattr`` checks. No implementation of
that interface existed, and the graph never passed one in, so every guard was False in
production: the tools returned empty results, beliefs and interactions were never
persisted, notifications had no idempotency record, and the agent investigated with no
data at all. This module supplies that object, and :func:`wha.agent.graph.build_agent_graph`
binds it into each node.

Every read is scoped to one subject. The tool registry strips any model-supplied
``subject_id`` before a handler runs, so the identity used here is always the one the
episode was opened for.
"""

import json
import sqlite3
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from wha.db.audit_chain import append_audit as append_audit_row
from wha.db.connection import connect
from wha.db.iso import to_iso
from wha.models import AuditEvent, Baseline, BaselineRung, BeliefState, NightlyFeatures
from wha.notify.telegram import format_callback_token


def _row_to_nightly_features(row: sqlite3.Row) -> NightlyFeatures:
    """Build a NightlyFeatures model from a nightly_features row."""
    return NightlyFeatures(
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


class EpisodeRepository:
    """Subject-scoped reads and episode writes for the agent graph."""

    def __init__(
        self,
        conn: sqlite3.Connection | None = None,
        db_path: Path | None = None,
    ) -> None:
        self._conn = conn if conn is not None else connect(db_path)
        self.retrieval_index: Any = None

    @property
    def conn(self) -> sqlite3.Connection:
        """The underlying connection, exposed for callers that need a transaction."""
        return self._conn

    # -- reads used by the seven T1 tools ---------------------------------------

    def get_nightly_features(
        self,
        subject_id: str,
        start: date,
        end: date,
    ) -> list[NightlyFeatures]:
        """Derived nightly features for a subject across an inclusive date range."""
        rows = self._conn.execute(
            """SELECT * FROM nightly_features
               WHERE subject_id = ? AND night_date BETWEEN ? AND ?
               ORDER BY night_date ASC""",
            (subject_id, start.isoformat(), end.isoformat()),
        ).fetchall()
        return [_row_to_nightly_features(r) for r in rows]

    def get_baseline(self, subject_id: str, night_date: date) -> Baseline | None:
        """The most recent baseline on or before a night, or None if none exists yet."""
        row = self._conn.execute(
            """SELECT * FROM baselines
               WHERE subject_id = ? AND night_date <= ?
               ORDER BY night_date DESC LIMIT 1""",
            (subject_id, night_date.isoformat()),
        ).fetchone()
        if row is None:
            return None
        return Baseline(
            centre_bpm=row["centre_bpm"],
            scale_bpm=row["scale_bpm"],
            usable_nights=row["usable_nights"],
            rung=BaselineRung(row["rung"]),
            shrink_weight=row["shrink_weight"],
        )

    def get_baseline_rung(self, subject_id: str, night_date: date) -> BaselineRung:
        """The subject's baseline rung, defaulting to COLD when no baseline exists.

        COLD is the safe default: it gates the policy away from interrupting a person
        whose baseline is not yet established.
        """
        baseline = self.get_baseline(subject_id, night_date)
        return baseline.rung if baseline is not None else BaselineRung.COLD

    def get_known_events(
        self,
        subject_id: str,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Recorded exercise sessions and daily step totals in range.

        These are the events the person's device already knows about, which is what
        separates an explained elevation from an unexplained one.
        """
        events: list[dict[str, Any]] = []

        for row in self._conn.execute(
            """SELECT start_utc, end_utc, kind FROM exercise_sessions
               WHERE subject_id = ? AND DATE(start_utc) BETWEEN ? AND ?
               ORDER BY start_utc ASC""",
            (subject_id, start.isoformat(), end.isoformat()),
        ).fetchall():
            events.append(
                {
                    "kind": "exercise",
                    "activity": row["kind"],
                    "start_utc": row["start_utc"],
                    "end_utc": row["end_utc"],
                }
            )

        for row in self._conn.execute(
            """SELECT start_utc, count FROM step_buckets
               WHERE subject_id = ? AND DATE(start_utc) BETWEEN ? AND ?
               ORDER BY start_utc ASC""",
            (subject_id, start.isoformat(), end.isoformat()),
        ).fetchall():
            events.append(
                {
                    "kind": "steps",
                    "count": row["count"],
                    "start_utc": row["start_utc"],
                }
            )

        return events

    def find_similar_episodes(
        self,
        subject_id: str,
        pattern: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Closed past episodes for this subject, most recent first."""
        rows = self._conn.execute(
            """SELECT episode_id, opened_on, closed_on, disposition, baseline_rung
               FROM episodes
               WHERE subject_id = ? AND state = 'CLOSED' AND disposition IS NOT NULL
               ORDER BY opened_on DESC LIMIT 10""",
            (subject_id,),
        ).fetchall()
        return [
            {
                "episode_id": r["episode_id"],
                "opened_on": r["opened_on"],
                "closed_on": r["closed_on"],
                "disposition": r["disposition"],
                "baseline_rung": r["baseline_rung"],
            }
            for r in rows
        ]

    # -- policy inputs -----------------------------------------------------------

    def count_interruptions_since(self, subject_id: str, since: date) -> int:
        """Questions actually put to this person since a date, for the weekly budget."""
        row = self._conn.execute(
            """SELECT COUNT(*) AS n FROM interactions i
               JOIN episodes e ON e.episode_id = i.episode_id
               WHERE e.subject_id = ? AND DATE(i.asked_at_utc) >= ?""",
            (subject_id, since.isoformat()),
        ).fetchone()
        return int(row["n"]) if row else 0

    def has_pending_interaction(self, subject_id: str) -> bool:
        """True while a question is outstanding, so the policy does not stack another."""
        row = self._conn.execute(
            """SELECT 1 FROM interactions i
               JOIN episodes e ON e.episode_id = i.episode_id
               WHERE e.subject_id = ? AND i.status = 'PENDING' LIMIT 1""",
            (subject_id,),
        ).fetchone()
        return row is not None

    def get_answered_probe_ids(self, episode_id: str) -> list[str]:
        """Probes already put to the person in this episode, so none is asked twice."""
        rows = self._conn.execute(
            "SELECT DISTINCT probe_id FROM interactions WHERE episode_id = ?",
            (episode_id,),
        ).fetchall()
        return [r["probe_id"] for r in rows]

    # -- writes ------------------------------------------------------------------

    def append_belief(
        self,
        episode_id: str,
        subject_id: str,
        belief: BeliefState,
        trigger: str = "node_believe",
    ) -> int:
        """Append one belief revision to the episode's history and return its sequence."""
        row = self._conn.execute(
            "SELECT COALESCE(MAX(seq), 0) AS s FROM beliefs WHERE episode_id = ?",
            (episode_id,),
        ).fetchone()
        seq = int(row["s"]) + 1

        self._conn.execute(
            """INSERT INTO beliefs
                 (episode_id, seq, ts_utc, trigger, marginals_json, p_illness, state_logprob_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                episode_id,
                seq,
                to_iso(datetime.now(UTC)),
                trigger,
                json.dumps({str(k): float(v) for k, v in belief.marginals.items()}),
                float(belief.p_illness),
                json.dumps(list(belief.state_logprob)) if belief.state_logprob else None,
            ),
        )
        self._conn.commit()
        return seq

    def upsert_interaction(
        self,
        interaction_id: str,
        episode_id: str,
        subject_id: str,
        probe_id: str,
        question_text: str,
        text_source: str = "fallback",
        options: list[dict[str, Any]] | None = None,
        evsi: float = 0.0,
        interruption_cost: float = 0.0,
        rejected: list[Any] | None = None,
        channel: str = "none",
    ) -> None:
        """Record a question, idempotently. Re-running the ask node must not duplicate it."""
        self._conn.execute(
            """INSERT INTO interactions
                 (id, episode_id, probe_id, question_text, text_source, options_json,
                  evsi, interruption_cost, rejected_json, channel, asked_at_utc, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
               ON CONFLICT(id) DO UPDATE SET
                 question_text = excluded.question_text,
                 text_source = excluded.text_source,
                 options_json = excluded.options_json""",
            (
                interaction_id,
                episode_id,
                probe_id,
                question_text,
                text_source,
                json.dumps(options or []),
                float(evsi),
                float(interruption_cost),
                json.dumps(rejected or []),
                channel,
                to_iso(datetime.now(UTC)),
            ),
        )
        self._conn.commit()

    def find_interaction_by_prefix(self, token: str) -> dict[str, Any] | None:
        """Resolve a Telegram callback token back to the interaction that issued it.

        The token is a hash of the full interaction id rather than a prefix of it, because
        ids are built as ``int_{episode_id}_{probe_id}`` and any two interactions in the
        same episode share their leading characters. Matching is done over open
        interactions only, so a stale button cannot answer a closed question.
        """
        rows = self._conn.execute(
            """SELECT i.id, i.episode_id, i.probe_id, i.status, i.options_json
               FROM interactions i
               WHERE i.status = 'PENDING'"""
        ).fetchall()
        for row in rows:
            if format_callback_token(row["id"]) == token:
                return {
                    "id": row["id"],
                    "episode_id": row["episode_id"],
                    "probe_id": row["probe_id"],
                    "status": row["status"],
                    "options": json.loads(row["options_json"]) if row["options_json"] else [],
                }
        return None

    def has_notification_for(self, interaction_id: str) -> bool:
        """True when this question or measurement has already been delivered."""
        row = self._conn.execute(
            """SELECT 1 FROM notifications
               WHERE (interaction_id = ? OR measurement_id = ?) AND status = 'SENT'
               LIMIT 1""",
            (interaction_id, interaction_id),
        ).fetchone()
        return row is not None

    def record_notification(
        self,
        interaction_id: str,
        recipient: str,
        kind: str = "QUESTION",
        channel: str = "none",
        episode_id: str | None = None,
    ) -> None:
        """Record a delivered notification, so a resumed node does not send it twice."""
        self._conn.execute(
            """INSERT INTO notifications
                 (id, subject_id, episode_id, interaction_id, measurement_id, channel,
                  kind, payload_json, queued_at_utc, sent_at_utc, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'SENT')""",
            (
                f"ntf_{uuid.uuid4().hex[:12]}",
                recipient,
                episode_id,
                interaction_id if kind != "MEASUREMENT" else None,
                interaction_id if kind == "MEASUREMENT" else None,
                channel,
                kind,
                json.dumps({"interaction_id": interaction_id}),
                to_iso(datetime.now(UTC)),
                to_iso(datetime.now(UTC)),
            ),
        )
        self._conn.commit()

    def append_audit(self, event: AuditEvent) -> str:
        """Chain one audit event onto the subject's tamper-evident log."""
        event_hash = append_audit_row(self._conn, event)
        self._conn.commit()
        return event_hash
