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
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from wha.clock import now_utc
from wha.db.audit_chain import append_audit as append_audit_row
from wha.db.connection import connect
from wha.db.iso import to_iso
from wha.models import AuditEvent, Baseline, BaselineRung, BeliefState, NightlyFeatures
from wha.notify.telegram import format_callback_token
from wha.retrieve.index import Retriever


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
        self._retrieval_index: Retriever | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        """The underlying connection, exposed for callers that need a transaction."""
        return self._conn

    @property
    def retrieval_index(self) -> Retriever:
        """The index ``retrieve_clinical_evidence`` searches, built on first use.

        This attribute was set to None in ``__init__`` and assigned by nothing, anywhere.
        ``tool_retrieve_clinical_evidence`` reads it through ``getattr``, so the tool
        existed, was allow-listed, was offered to the model, ran without error and could
        never return a single passage. The agent's `citations` were empty for the same
        reason.

        Built lazily because building it embeds the whole corpus, which costs seconds,
        and most commands never retrieve anything.
        """
        if self._retrieval_index is None:
            from wha.retrieve.knowledge_docs import get_default_index

            self._retrieval_index = get_default_index()
        return self._retrieval_index

    @retrieval_index.setter
    def retrieval_index(self, index: Retriever) -> None:
        """Tests and evaluations substitute a narrower index here."""
        self._retrieval_index = index

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

        # Distance and energy expenditure, where the device reports them. They corroborate
        # a hard day that steps alone can understate, such as cycling.
        for row in self._conn.execute(
            """SELECT start_utc, meters FROM distance_buckets
               WHERE subject_id = ? AND DATE(start_utc) BETWEEN ? AND ?
               ORDER BY start_utc ASC""",
            (subject_id, start.isoformat(), end.isoformat()),
        ).fetchall():
            events.append(
                {
                    "kind": "distance",
                    "meters": row["meters"],
                    "start_utc": row["start_utc"],
                }
            )

        for row in self._conn.execute(
            """SELECT start_utc, calories_kcal FROM calorie_buckets
               WHERE subject_id = ? AND DATE(start_utc) BETWEEN ? AND ?
               ORDER BY start_utc ASC""",
            (subject_id, start.isoformat(), end.isoformat()),
        ).fetchall():
            events.append(
                {
                    "kind": "calories",
                    "kcal": row["calories_kcal"],
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
        """Questions put to the person since a date, for the weekly budget.

        Counted across every subject rather than one, because this is a single-user app:
        one person, one phone, one budget. Extra subjects exist only when demos or
        simulations have been run, and filtering by subject gave each of those its own
        private allowance pointing at the same phone. That is how a day of testing sent a
        real person seventeen questions from a system that permits two a week.
        """
        # Only unsolicited contacts count. A follow-up asked inside a conversation the
        # person is already having is not an interruption, and charging it to the same
        # allowance is why the agent could never ask more than two questions in a week.
        # The alarm fatigue evidence behind this budget concerns unsolicited alarms; see
        # INTERRUPTION_BUDGET_CITATION.
        #
        # Rows written before the `initiation` column existed are NULL and are counted, so
        # a migrated database never under-counts what it already spent.
        #
        # A symptom follow-up IS counted, even though the budget cannot block one. It
        # arrives on somebody's phone unbidden, so calling it anything other than an
        # interruption would be a definition chosen to make a number look better. What the
        # follow-up gate does is decline to be silenced by this figure; it does not get to
        # pretend it did not happen, and the dashboard shows the spend either way.
        row = self._conn.execute(
            """SELECT COUNT(*) AS n FROM interactions
                WHERE DATE(asked_at_utc) >= ?
                  AND (initiation IS NULL OR initiation IN ('unsolicited', 'followup'))""",
            (since.isoformat(),),
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

    def get_answered_probe_ids_ever(self, subject_id: str) -> list[str]:
        """Probes this person has ANSWERED at any time, in any investigation.

        `one_time` probes are priced at 0.4 of an interruption on the promise that they are
        "asked once and then become a modelled covariate". The flag was dropped silently on
        load, so the promise was not kept and a setup question could be re-asked in every
        new episode, spending part of a weekly allowance each time.

        ANSWERED, not asked. A question that was put and never answered has established
        nothing, so asking it again is not repetition.

        The join through `episodes` is not optional: `interactions` is keyed by episode and
        has NO `subject_id` column. Selecting on one raised
        `OperationalError: no such column: subject_id` on every call, and this is called
        from `node_decide` behind a `hasattr` guard that is True, so it took down the
        decision node of every production episode. Nothing caught it because every test of
        `node_decide` passes `db=None`, which makes the guard False and skips the query
        entirely, and the scenario tests assert their own fixture rather than run the agent.
        """
        rows = self._conn.execute(
            """SELECT DISTINCT i.probe_id
                 FROM interactions AS i
                 JOIN episodes    AS e ON e.episode_id = i.episode_id
                WHERE e.subject_id = ? AND i.status = 'ANSWERED'""",
            (subject_id,),
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
                to_iso(now_utc()),
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
        initiation: str = "unsolicited",
    ) -> None:
        """Record a question, idempotently. Re-running the ask node must not duplicate it.

        ``initiation`` is "unsolicited" when the system contacted someone who was not
        asking, and "conversation" when it asked inside an exchange already under way.
        Only the first spends the weekly interruption budget.
        """
        self._conn.execute(
            """INSERT INTO interactions
                 (id, episode_id, probe_id, question_text, text_source, options_json,
                  evsi, interruption_cost, rejected_json, channel, asked_at_utc, status,
                  initiation)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
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
                to_iso(now_utc()),
                initiation,
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
        extra: dict[str, object] | None = None,
    ) -> None:
        """Record a delivered notification, so a resumed node does not send it twice.

        `extra` carries what the message was about. An escalation records the reading that
        raised it, which is how a later night can tell whether the person has got worse
        since they were last told anything.
        """
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
                json.dumps({"interaction_id": interaction_id, **(extra or {})}),
                to_iso(now_utc()),
                to_iso(now_utc()),
            ),
        )
        self._conn.commit()

    # -- the receive half of the Telegram loop ----------------------------------
    #
    # TelegramReceiver reaches its database through hasattr guards. Until these methods
    # existed every guard was False, so a tapped button or a typed reply was accepted,
    # acknowledged to the user, and then silently discarded: the interaction stayed
    # PENDING and the episode never resumed. Same failure mode as the twelve-method `db`
    # interface that had no implementation.

    def get_pending_interaction_for_chat(self, chat_id: str | int | None = None) -> dict | None:
        """The question currently awaiting a free-text reply, if there is one.

        `chat_id` is accepted because the receiver passes it, but this build notifies a
        single configured subject, so there is nothing to disambiguate. Only one question
        may be outstanding at a time, which the ask node enforces via
        `has_pending_interaction`, so the newest PENDING row is the one being answered.
        """
        row = self._conn.execute(
            """SELECT id, episode_id, probe_id, status, options_json
               FROM interactions WHERE status = 'PENDING'
               ORDER BY asked_at_utc DESC LIMIT 1"""
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "episode_id": row["episode_id"],
            "probe_id": row["probe_id"],
            "status": row["status"],
            "options": json.loads(row["options_json"]) if row["options_json"] else [],
        }

    def set_episode_state(self, episode_id: str, state: str) -> None:
        """Move an episode between its non-closed states.

        Episodes only ever transitioned to CLOSED. AWAITING_USER, AWAITING_MEASUREMENT and
        AWAITING_HUMAN_REVIEW are defined in the model, looked for by
        `get_pending_interaction`, and given wording in the interface, and nothing ever set
        any of them. So a question the agent had asked was never surfaced in the dashboard
        and could only be answered over Telegram.
        """
        self._conn.execute(
            "UPDATE episodes SET state = ? WHERE episode_id = ? AND state != 'CLOSED'",
            (state, episode_id),
        )
        self._conn.commit()

    def record_notification_sent(
        self,
        subject_id: str,
        episode_id: str | None,
        kind: str,
        channel: str,
        text: str,
    ) -> None:
        """Put a delivered message in the tamper-evident record, not only in a table."""
        from wha.audit.monitor import record_notification_sent

        record_notification_sent(self._conn, subject_id, episode_id, kind, channel, text)

    def record_episode_trace(self, episode_id: str, payload: dict[str, Any]) -> None:
        """What the agent did in this episode, written by the graph that did it.

        Replaces inferring the Trace tab from the audit log's `operation` column, which
        holds ten fixed values, none of them a stage name, so nothing ever matched and
        every stage on every episode was reported as skipped.
        """
        self._conn.execute(
            """INSERT INTO episode_traces (episode_id, payload_json, updated_at_utc)
               VALUES (?, ?, ?)
               ON CONFLICT(episode_id) DO UPDATE SET
                 payload_json = excluded.payload_json,
                 updated_at_utc = excluded.updated_at_utc""",
            (episode_id, json.dumps(payload, default=str), to_iso(now_utc())),
        )
        self._conn.commit()

    def record_episode_stage_ran(self, episode_id: str, stage: str) -> None:
        """Add one stage to an existing trace, for stages that run AFTER it is written.

        `node_conclude` writes the trace, and `critique` and `review` run after it, so a
        hardcoded set written at conclude time can never contain them. It listed "critique"
        anyway, at a point where critique had not executed, and could never list "review".

        That second one was not cosmetic. `node_review` is the ONLY node that returns
        status "closed" or "unresolved", and `_close_if_concluded` refuses to close an
        episode without it, so EVERY closed episode ran the review checkpoint. The Trace
        tab rendered review as SKIPPED on all of them, with the reason "This episode has
        not reached the review checkpoint" - the same class of invented reason item 11
        exists to delete, on the one stage where a person most wants to know whether it
        happened.
        """
        row = self._conn.execute(
            "SELECT payload_json FROM episode_traces WHERE episode_id = ?", (episode_id,)
        ).fetchone()
        if row is None:
            return
        payload = json.loads(row["payload_json"])
        ran = set(payload.get("nodes_ran", []))
        if stage in ran:
            return
        payload["nodes_ran"] = sorted(ran | {stage})
        self._conn.execute(
            "UPDATE episode_traces SET payload_json = ?, updated_at_utc = ? WHERE episode_id = ?",
            (json.dumps(payload, default=str), to_iso(now_utc()), episode_id),
        )
        self._conn.commit()

    def get_profile_menstruates(self, subject_id: str) -> bool | None:
        """Whether this person menstruates, from the Settings profile, or None if unset.

        A standing fact, so it is collected once rather than costing an interruption in
        every investigation. None means unknown, and `update_belief` leaves the luteal
        cause inert on unknown rather than assuming it applies, which it used to do for
        everybody including every male user.
        """
        row = self._conn.execute(
            "SELECT menstruates FROM subject_profile WHERE subject_id = ?",
            (subject_id,),
        ).fetchone()
        if row is None or row["menstruates"] is None:
            return None
        return bool(row["menstruates"])

    def has_recent_illness_episode(self, subject_id: str, today: date) -> bool:
        """Whether a closed illness episode sits inside the published recovery window.

        causes.yaml says the belief model "raises it sharply when a closed illness episode
        exists within the published tail window", and nothing anywhere looked for one, so
        the recovery_tail cause never rose above its base rate.

        The window is RECOVERY_TAIL_DAYS, from Radin et al. 2021: resting heart rate did
        not return to baseline until roughly 79 days after symptom onset.
        """
        from wha.constants import RECOVERY_TAIL_DAYS

        cutoff = (today - timedelta(days=RECOVERY_TAIL_DAYS)).isoformat()
        row = self._conn.execute(
            """SELECT 1 FROM episodes
                WHERE subject_id = ? AND state = 'CLOSED'
                  AND disposition IN ('LIKELY_ILLNESS', 'ESCALATED')
                  AND COALESCE(closed_on, opened_on) >= ?
                LIMIT 1""",
            (subject_id, cutoff),
        ).fetchone()
        return row is not None

    def record_review_requested(self, subject_id: str, episode_id: str, disposition: str) -> None:
        """Write down that the system stopped and asked a person to check its conclusion."""
        from wha.audit.monitor import record_review_requested

        record_review_requested(self._conn, subject_id, episode_id, disposition)

    def record_review_decision(
        self,
        subject_id: str,
        episode_id: str,
        decision: str,
        rationale: str | None = None,
        reviewed_by_person: bool = True,
    ) -> None:
        """Write down how the review ended, and whether a person was involved at all."""
        from wha.audit.monitor import record_review_decision

        record_review_decision(
            self._conn,
            subject_id,
            episode_id,
            decision,
            rationale=rationale,
            reviewed_by_person=reviewed_by_person,
        )

    def record_interaction_answer(
        self,
        interaction_id: str,
        option_id: str | None = None,
        free_text: str | None = None,
    ) -> None:
        """Record the person's answer against the question that asked it.

        Guarded on status so a duplicate button tap racing a typed reply cannot overwrite
        an answer already recorded, and so a TIMED_OUT question cannot be revived.
        """
        self._conn.execute(
            """UPDATE interactions
                  SET answer_option_id = COALESCE(?, answer_option_id),
                      free_text        = COALESCE(?, free_text),
                      answered_at_utc  = ?,
                      status           = 'ANSWERED'
                WHERE id = ? AND status = 'PENDING'""",
            (option_id, free_text, to_iso(now_utc()), interaction_id),
        )
        # The episode was parked AWAITING_USER; the answer releases it.
        self._conn.execute(
            """UPDATE episodes SET state = 'OPEN'
                WHERE state = 'AWAITING_USER'
                  AND episode_id = (SELECT episode_id FROM interactions WHERE id = ?)""",
            (interaction_id,),
        )
        self._conn.commit()

    def record_interaction_declined(self, interaction_id: str) -> None:
        """Record a 'not now'. The interruption budget is still consumed by design."""
        self._conn.execute(
            """UPDATE interactions
                  SET answered_at_utc = ?, status = 'DECLINED'
                WHERE id = ? AND status = 'PENDING'""",
            (to_iso(now_utc()), interaction_id),
        )
        self._conn.commit()

    def get_answered_interactions(self) -> list[dict]:
        """Episode ids with an answer recorded but not yet consumed by the graph.

        The poller uses this to decide which episodes to resume.
        """
        rows = self._conn.execute(
            """SELECT id, episode_id, probe_id, answer_option_id, free_text, status
                 FROM interactions
                WHERE status IN ('ANSWERED', 'DECLINED')"""
        ).fetchall()
        return [dict(r) for r in rows]

    def get_telegram_offset(self) -> int:
        """The next Telegram update id to request. Zero when nothing has been seen."""
        row = self._conn.execute("SELECT update_id FROM telegram_offset WHERE id = 1").fetchone()
        return int(row["update_id"]) if row is not None else 0

    def set_telegram_offset(self, update_id: int) -> None:
        """Persist the acknowledged offset so a restart does not reprocess old updates."""
        self._conn.execute(
            """INSERT INTO telegram_offset (id, update_id) VALUES (1, ?)
               ON CONFLICT(id) DO UPDATE SET update_id = excluded.update_id""",
            (int(update_id),),
        )
        self._conn.commit()

    def append_audit(self, event: AuditEvent) -> str:
        """Chain one audit event onto the subject's tamper-evident log."""
        event_hash = append_audit_row(self._conn, event)
        self._conn.commit()
        return event_hash
