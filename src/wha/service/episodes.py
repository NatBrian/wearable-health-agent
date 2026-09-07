"""Service functions for episode management, interactive submissions, and bounded Q&A."""

import json
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from wha.agent.steps import AGENT_NODES, pipeline_steps_that_ran
from wha.clock import local_today, now_utc
from wha.db import connect, to_iso
from wha.db.migrations import apply_schema
from wha.errors import ConfigError
from wha.models import (
    Answer,
    AnswerOption,
    BeliefState,
    CauseId,
    Detection,
    DetectionLevel,
    Disposition,
    EpisodeDetail,
    EpisodeOutcome,
    EpisodeState,
    EpisodeSummary,
    Forecast,
    ForecastStatus,
    InteractionView,
    MeasurementResult,
    NightlyFeatures,
    PendingInteraction,
    PipelineStage,
    Probe,
    Question,
    StageStatus,
)
from wha.policy.probes import load_probes

# What the Trace tab says each stage does. One entry per node in `wha.agent.graph`, and
# NOTHING ELSE, because a name here that the graph does not have is shown to a person as a
# stage of their own investigation that is permanently pending. "measure" was exactly that:
# `node_measure` was deleted, this list was not updated, and the Trace tab went on
# advertising "Request spot resting heart rate or overnight wear" for a limb that no longer
# existed, explaining its absence with "No spot reading was requested". Found by opening the
# tab, 5 September 2026.
#
# The names are no longer written out here. They are read from `wha.agent.steps`, which is
# where the agent declares them, so the drift above cannot recur: a node renamed in the
# graph and not described here fails a test instead of a reader.
_STAGE_DESCRIPTIONS: dict[str, str] = {
    "preload": "Fetch preloaded nightly features, baselines, and quality metrics",
    "investigate": "Query closed T1 tools for clinical context and evidence",
    "believe": "Enumerate exact 4096-state joint belief over 12 causes",
    "decide": "Select EVSI-optimal action and evaluate veto policy",
    "ask": "Prompt user for targeted symptom/exposure probe",
    "conclude": "Draft structured clinical outcome with bounded differential",
    "critique": "Verify deterministic claim grounding and strip ungrounded assertions",
    "review": "Human clinician or supervisor review checkpoint",
}


def _canonical_stages() -> list[tuple[str, str]]:
    """The stages the Trace tab renders, in the order the graph runs them.

    Refuses to load rather than rendering a blank row: a node with no description here
    would reach the reader as an unexplained stage of their own investigation.
    """
    undescribed = [node for node in AGENT_NODES if node not in _STAGE_DESCRIPTIONS]
    if undescribed:
        raise ConfigError(
            f"These agent nodes have no Trace tab description: {undescribed}. "
            "Add one to _STAGE_DESCRIPTIONS in service/episodes.py. A node declared in "
            "wha.agent.steps and not described here would be shown to a person as a blank "
            "stage of their own investigation."
        )
    return [(node, _STAGE_DESCRIPTIONS[node]) for node in AGENT_NODES]


CANONICAL_STAGES = _canonical_stages()


def get_pending_interaction(
    subject_id: str,
    conn: sqlite3.Connection | None = None,
) -> PendingInteraction | None:
    """Retrieve the single active pending user interaction for a subject.

    Precedence order: review -> measurement -> question.
    Returns at most one PendingInteraction or None. Handles empty DB cleanly.
    """
    close_conn = False
    if conn is None:
        conn = connect()
        apply_schema(conn)
        close_conn = True

    try:
        # Find active episodes
        ep_rows = conn.execute(
            """SELECT episode_id, state, disposition, baseline_nights, baseline_rung
               FROM episodes
               WHERE subject_id = ? AND state IN ('AWAITING_HUMAN_REVIEW', 'AWAITING_MEASUREMENT', 'AWAITING_USER')
               ORDER BY opened_on DESC""",
            (subject_id,),
        ).fetchall()

        if not ep_rows:
            return None

        # Check by precedence
        # 1. Review
        for ep in ep_rows:
            if ep["state"] == "AWAITING_HUMAN_REVIEW":
                ep_id = ep["episode_id"]
                out_row = conn.execute(
                    "SELECT payload_json FROM outcomes WHERE episode_id = ?",
                    (ep_id,),
                ).fetchone()
                draft = None
                if out_row and out_row["payload_json"]:
                    draft = EpisodeOutcome.model_validate_json(out_row["payload_json"])
                return PendingInteraction(
                    kind="review",
                    episode_id=ep_id,
                    draft_outcome=draft,
                )

        # 2. Measurement was here. The spot-reading limb was removed on 5 September
        #    2026, so nothing can create a PENDING measurement any more. The table is kept
        #    so databases written before this still open.

        # 3. Question
        for ep in ep_rows:
            if ep["state"] == "AWAITING_USER":
                ep_id = ep["episode_id"]
                q_row = conn.execute(
                    """SELECT id, probe_id, question_text, text_source, options_json, evsi, interruption_cost FROM interactions
                       WHERE episode_id = ? AND status = 'PENDING'
                       ORDER BY asked_at_utc DESC LIMIT 1""",
                    (ep_id,),
                ).fetchone()
                if q_row:
                    probes = {p.probe_id: p for p in load_probes()}
                    probe_def = probes.get(q_row["probe_id"])
                    raw_opts = json.loads(q_row["options_json"])
                    options = [AnswerOption(**o) for o in raw_opts]
                    if probe_def:
                        probe_obj = Probe(
                            probe_id=probe_def.probe_id,
                            target_cause=probe_def.target_cause,
                            answer_space=probe_def.answer_space,
                            evsi=float(q_row["evsi"]),
                            interruption_cost=float(q_row["interruption_cost"]),
                            fallback_text=probe_def.fallback_text,
                        )
                        q_obj = Question(
                            probe=probe_obj,
                            text=q_row["question_text"],
                            text_source=q_row["text_source"],
                            options=options,
                            allows_free_text=True,
                        )
                        return PendingInteraction(
                            kind="question",
                            episode_id=ep_id,
                            question=q_obj,
                        )

        return None
    finally:
        if close_conn:
            conn.close()


def submit_answer(
    interaction_id: str,
    answer: Answer,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Record an answer to a question interaction idempotently.

    First writer wins. Submitting on a CLOSED episode or already ANSWERED row is a no-op.

    Records the answer and releases the episode from AWAITING_USER. It does NOT drive the
    graph forward here: the docstring used to promise that and it never happened, and doing
    it inline would make a click in the dashboard wait on several model calls. The episode
    tick picks it up, which is the same path a Telegram reply takes.
    """
    close_conn = False
    if conn is None:
        conn = connect()
        apply_schema(conn)
        close_conn = True

    try:
        int_row = conn.execute(
            """SELECT id, episode_id, status FROM interactions
               WHERE id = ? OR (episode_id = ? AND status = 'PENDING')
               ORDER BY asked_at_utc DESC LIMIT 1""",
            (interaction_id, interaction_id),
        ).fetchone()

        if int_row is None:
            return

        if int_row["status"] in ("ANSWERED", "DECLINED", "TIMED_OUT"):
            # Idempotent no-op
            return

        ep_id = int_row["episode_id"]
        ep_row = conn.execute(
            "SELECT state FROM episodes WHERE episode_id = ?",
            (ep_id,),
        ).fetchone()

        if ep_row and ep_row["state"] == "CLOSED":
            # Answering on closed episode is no-op
            return

        now_str = now_utc().isoformat()
        actual_int_id = int_row["id"]
        # The ask node parks the episode AWAITING_USER; answering releases it so the next
        # tick advances the graph.
        conn.execute(
            "UPDATE episodes SET state = 'OPEN' WHERE episode_id = ? AND state = 'AWAITING_USER'",
            (ep_id,),
        )
        if answer.declined:
            conn.execute(
                """UPDATE interactions
                   SET status = 'DECLINED', answered_at_utc = ?
                   WHERE id = ?""",
                (now_str, actual_int_id),
            )
        else:
            conn.execute(
                """UPDATE interactions
                   SET status = 'ANSWERED', answer_option_id = ?, free_text = ?, answered_at_utc = ?
                   WHERE id = ?""",
                (answer.option_id, answer.free_text, now_str, actual_int_id),
            )
        conn.commit()
    finally:
        if close_conn:
            conn.close()


def submit_measurement_done(
    measurement_id: str,
    value: float | None = None,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Record measurement completion idempotently and advance episode."""
    close_conn = False
    if conn is None:
        conn = connect()
        apply_schema(conn)
        close_conn = True

    try:
        m_row = conn.execute(
            "SELECT id, episode_id, status FROM measurements WHERE id = ?",
            (measurement_id,),
        ).fetchone()

        if m_row is None or m_row["status"] != "PENDING":
            return

        now_str = now_utc().isoformat()
        res_json = json.dumps({"value": value, "satisfied": True, "ts_utc": now_str})
        conn.execute(
            """UPDATE measurements
               SET status = 'SATISFIED', satisfied_at_utc = ?, result_json = ?
               WHERE id = ?""",
            (now_str, res_json, measurement_id),
        )
        conn.commit()
    finally:
        if close_conn:
            conn.close()


def submit_human_decision(
    episode_id: str,
    decision: Literal["approve", "reject", "edit", "escalate"],
    edited_prose: str | None = None,
    rationale: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Apply a person's review decision by resuming the graph that is waiting for it.

    This used to close the episode with its own SQL while the graph stayed parked on the
    `interrupt()` in `node_review`, so the same four decisions were implemented twice, in
    two places, differently. The scheduler then reached the abandoned interrupt later and
    resumed it with a hardcoded "approve".

    Resuming is the only path now. `node_review` already knows what reject, edit, escalate
    and approve mean, it writes the decision into the audit record, and `review` runs
    straight to END, so nothing here makes a model call.
    """
    close_conn = False
    if conn is None:
        conn = connect()
        apply_schema(conn)
        close_conn = True

    try:
        ep_row = conn.execute(
            "SELECT state, disposition FROM episodes WHERE episode_id = ?",
            (episode_id,),
        ).fetchone()

        if ep_row is None or ep_row["state"] != "AWAITING_HUMAN_REVIEW":
            return

        # Changed wording is an edit whichever button was pressed. The dashboard puts the
        # draft in a text area beside "Looks right", so a person who reworded it and
        # approved it meant to keep their wording, and both the old SQL path and the first
        # version of this one dropped it on the floor: only decision == "edit" was read,
        # and no button in the interface sends that.
        resume: dict[str, Any] = {"decision": decision}
        if edited_prose and decision in ("approve", "edit"):
            resume["decision"] = "edit"
            resume["edited_observation"] = edited_prose
        if rationale:
            resume["rationale"] = rationale

        step_episode(episode_id, conn=conn, resume=resume)
        conn.commit()
    finally:
        if close_conn:
            conn.close()


def list_episodes(
    subject_id: str,
    db_path: Path | None = None,
    conn: sqlite3.Connection | None = None,
) -> list[EpisodeSummary]:
    """Retrieve summaries for all episodes for a subject, ordered newest first."""
    close_conn = False
    if conn is None:
        conn = connect(db_path) if db_path is not None else connect()
        apply_schema(conn)
        close_conn = True

    try:
        rows = conn.execute(
            """SELECT episode_id, opened_on, closed_on, state, disposition
               FROM episodes
               WHERE subject_id = ?
               ORDER BY opened_on DESC""",
            (subject_id,),
        ).fetchall()

        summaries: list[EpisodeSummary] = []
        for r in rows:
            ep_id = r["episode_id"]
            op_d = date.fromisoformat(r["opened_on"])
            cl_d = date.fromisoformat(r["closed_on"]) if r["closed_on"] else None
            state = EpisodeState(r["state"])
            disp = Disposition(r["disposition"]) if r["disposition"] else None

            # Get latest belief
            b_row = conn.execute(
                """SELECT marginals_json FROM beliefs
                   WHERE episode_id = ?
                   ORDER BY seq DESC LIMIT 1""",
                (ep_id,),
            ).fetchone()

            top_cause = None
            top_prob = None
            if b_row and b_row["marginals_json"]:
                margs = json.loads(b_row["marginals_json"])
                if margs:
                    sorted_m = sorted(margs.items(), key=lambda item: item[1], reverse=True)
                    top_cause = CauseId(sorted_m[0][0])
                    top_prob = float(sorted_m[0][1])

            summaries.append(
                EpisodeSummary(
                    episode_id=ep_id,
                    opened_on=op_d,
                    closed_on=cl_d,
                    state=state,
                    disposition=disp,
                    night_span=(op_d, cl_d or op_d),
                    top_cause=top_cause,
                    top_probability=top_prob,
                )
            )
        return summaries
    finally:
        if close_conn:
            conn.close()


def get_episode(
    episode_id: str,
    conn: sqlite3.Connection | None = None,
) -> EpisodeDetail:
    """Assemble complete episode detail including skipped stages and rejected probes."""
    close_conn = False
    if conn is None:
        conn = connect()
        apply_schema(conn)
        close_conn = True

    try:
        ep_row = conn.execute(
            """SELECT episode_id, subject_id, opened_on, closed_on, state, disposition
               FROM episodes
               WHERE episode_id = ?""",
            (episode_id,),
        ).fetchone()

        if ep_row is None:
            raise ValueError(f"Episode '{episode_id}' not found")

        op_d = date.fromisoformat(ep_row["opened_on"])
        cl_d = date.fromisoformat(ep_row["closed_on"]) if ep_row["closed_on"] else None

        # 1. Outcome
        out_row = conn.execute(
            "SELECT payload_json FROM outcomes WHERE episode_id = ?",
            (episode_id,),
        ).fetchone()
        outcome = None
        if out_row and out_row["payload_json"]:
            outcome = EpisodeOutcome.model_validate_json(out_row["payload_json"])

        # 2. Belief history
        b_rows = conn.execute(
            """SELECT seq, trigger, ts_utc, marginals_json, p_illness, state_logprob_json
               FROM beliefs WHERE episode_id = ? ORDER BY seq""",
            (episode_id,),
        ).fetchall()
        belief_history: list[tuple[int, str, BeliefState]] = []
        for br in b_rows:
            margs = json.loads(br["marginals_json"])
            # Without the joint log-posterior, EVSI silently falls back to a projection in
            # which every non-infection probe scores exactly zero, so a rehydrated belief
            # would stop the policy asking about alcohol, exercise, stress or sleep.
            raw_logprob = br["state_logprob_json"]
            b_state = BeliefState(
                marginals={CauseId(k): float(v) for k, v in margs.items()},
                p_illness=float(br["p_illness"]),
                state_logprob=json.loads(raw_logprob) if raw_logprob else [],
            )
            belief_history.append((int(br["seq"]), br["trigger"], b_state))

        # 3. Interactions
        int_rows = conn.execute(
            """SELECT id, probe_id, question_text, text_source, options_json,
                      evsi, interruption_cost, rejected_json, answer_option_id,
                      free_text, asked_at_utc, answered_at_utc, status
               FROM interactions
               WHERE episode_id = ? ORDER BY asked_at_utc""",
            (episode_id,),
        ).fetchall()
        interactions: list[InteractionView] = []
        for ir in int_rows:
            opts = [AnswerOption(**o) for o in json.loads(ir["options_json"])]
            rej_raw = json.loads(ir["rejected_json"]) if ir["rejected_json"] else []
            rej = [(r[0], float(r[1])) for r in rej_raw]
            interactions.append(
                InteractionView(
                    id=ir["id"],
                    probe_id=ir["probe_id"],
                    question_text=ir["question_text"],
                    text_source=ir["text_source"],
                    options=opts,
                    evsi=float(ir["evsi"]),
                    interruption_cost=float(ir["interruption_cost"]),
                    rejected=rej,
                    answer_option_id=ir["answer_option_id"],
                    free_text=ir["free_text"],
                    status=ir["status"],
                    asked_at_utc=datetime.fromisoformat(ir["asked_at_utc"]),
                    answered_at_utc=(
                        datetime.fromisoformat(ir["answered_at_utc"])
                        if ir["answered_at_utc"]
                        else None
                    ),
                )
            )

        # 4. Measurements
        m_rows = conn.execute(
            "SELECT id, kind, instruction, requested_at_utc, satisfied_at_utc, result_json, status FROM measurements WHERE episode_id = ?",
            (episode_id,),
        ).fetchall()
        measurements: list[MeasurementResult] = []
        for mr in m_rows:
            val = None
            if mr["result_json"]:
                r_dict = json.loads(mr["result_json"])
                val = r_dict.get("value")
            measurements.append(
                MeasurementResult(
                    measurement_id=mr["id"],
                    kind=mr["kind"],
                    value=val,
                    observed_at_utc=(
                        datetime.fromisoformat(mr["satisfied_at_utc"])
                        if mr["satisfied_at_utc"]
                        else None
                    ),
                    satisfied=mr["status"] == "SATISFIED",
                )
            )

        # 5. Citations, and the claims the grounding check removed.
        citations = outcome.citations if outcome else []
        trace = _episode_trace(conn, episode_id)
        stripped_claims: list[str] = list(trace.get("stripped_claims", []))

        # 6. What the agent actually did, from the record the graph wrote.
        stages = _pipeline_stages(trace)

        # Build summary
        top_cause = None
        top_prob = None
        if belief_history:
            latest_b = belief_history[-1][2]
            sorted_m = sorted(latest_b.marginals.items(), key=lambda item: item[1], reverse=True)
            if sorted_m:
                top_cause = sorted_m[0][0]
                top_prob = sorted_m[0][1]

        summary = EpisodeSummary(
            episode_id=episode_id,
            opened_on=op_d,
            closed_on=cl_d,
            state=EpisodeState(ep_row["state"]),
            disposition=Disposition(ep_row["disposition"]) if ep_row["disposition"] else None,
            night_span=(op_d, cl_d or op_d),
            top_cause=top_cause,
            top_probability=top_prob,
        )

        return EpisodeDetail(
            summary=summary,
            outcome=outcome,
            stages=stages,
            belief_history=belief_history,
            interactions=interactions,
            measurements=measurements,
            citations=citations,
            stripped_claims=stripped_claims,
        )
    finally:
        if close_conn:
            conn.close()


def _episode_trace(conn: sqlite3.Connection, episode_id: str) -> dict[str, Any]:
    """What `node_conclude` recorded about this episode, or an empty record."""
    row = conn.execute(
        "SELECT payload_json FROM episode_traces WHERE episode_id = ?", (episode_id,)
    ).fetchone()
    if row is None or not row["payload_json"]:
        return {}
    try:
        loaded = json.loads(row["payload_json"])
    except (TypeError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _pipeline_stages(trace: dict[str, Any]) -> list[PipelineStage]:
    """The nine stages, and which of them ran.

    This used to match stage names against the `operation` column of the audit log. That
    column holds ten fixed values and none of them is a stage name, so nothing could ever
    match and every stage on every episode was reported SKIPPED with a made-up reason,
    including "Ask probe not selected by EVSI optimizer" on episodes whose own summary
    said a question had been asked. The belief chart directly below showed the probability
    moving, so the page contradicted itself.

    An episode with no trace record predates this and is reported PENDING rather than
    SKIPPED, because "we did not write it down" is not the same claim as "it did not run".
    """
    ran = pipeline_steps_that_ran(trace.get("nodes_ran", []))
    tool_calls = list(trace.get("tool_calls", []))

    stages: list[PipelineStage] = []
    for name, description in CANONICAL_STAGES:
        if not trace:
            stages.append(
                PipelineStage(
                    name=name,
                    status=StageStatus.PENDING,
                    reason="This episode ran before the system recorded which stages ran.",
                    detail_json={},
                )
            )
            continue

        if name in ran:
            detail: dict[str, Any] = {}
            if name == "investigate" and tool_calls:
                # The expander in wha/ui/components/pipeline_trace.py is written and has
                # never had data to render.
                detail = {"tool_calls": tool_calls}
            elif name == "ask":
                detail = {"questions_asked": trace.get("questions_asked", 0)}
            elif name == "critique" and trace.get("stripped_claims"):
                detail = {"stripped_claims": trace["stripped_claims"]}
            stages.append(
                PipelineStage(
                    name=name,
                    status=StageStatus.RAN,
                    reason=description,
                    detail_json=detail,
                )
            )
        else:
            reason = f"{description}. Not needed for this episode."
            if name == "ask":
                reason = "No question was worth its interruption, so none was asked."
            elif name == "review":
                reason = "This episode has not reached the review checkpoint."
            stages.append(
                PipelineStage(
                    name=name,
                    status=StageStatus.SKIPPED,
                    reason=reason,
                    detail_json={},
                )
            )
    return stages


def _run_start(conn: sqlite3.Connection, subject_id: str, opened_on: str) -> str:
    """Walk back from the flagged night over consecutive elevated nights."""
    start = date.fromisoformat(opened_on)
    while True:
        previous = start - timedelta(days=1)
        row = conn.execute(
            "SELECT level FROM detections WHERE subject_id = ? AND night_date = ?",
            (subject_id, previous.isoformat()),
        ).fetchone()
        if row is None or row["level"] not in ("YELLOW", "RED"):
            return start.isoformat()
        start = previous


def _episode_nights(
    conn: sqlite3.Connection,
    subject_id: str,
    opened_on: str,
) -> list[Detection]:
    """Detections covering the alert run, as the agent's evidence.

    An episode opens on the night a persistent run reaches length, so starting at
    ``opened_on`` would hand the agent only the last night of the run and discard the
    elevation that triggered it. The belief model needs the whole run: its likelihoods
    are indexed by nights elapsed, and one night cannot distinguish a rising infection
    from a single bad night.
    """
    start = _run_start(conn, subject_id, opened_on)
    rows = conn.execute(
        """SELECT * FROM detections
           WHERE subject_id = ? AND night_date >= ?
           ORDER BY night_date ASC""",
        (subject_id, start),
    ).fetchall()
    return [
        Detection(
            subject_id=r["subject_id"],
            night_date=date.fromisoformat(r["night_date"]),
            deviation_bpm=r["deviation_bpm"],
            robust_z=r["robust_z"],
            explained_bpm=r["explained_bpm"],
            residual_bpm=r["residual_bpm"],
            level=DetectionLevel(r["level"]),
            flagged=bool(r["flagged"]),
            forecast=Forecast(
                status=ForecastStatus(r["forecast_status"]),
                predicted_bpm=r["forecast_bpm"],
                lo_bpm=r["forecast_lo_bpm"],
                hi_bpm=r["forecast_hi_bpm"],
                forecast_z=r["forecast_z"],
            ),
            reasons=json.loads(r["reasons_json"]) if r["reasons_json"] else [],
        )
        for r in rows
    ]


def _episode_features(
    conn: sqlite3.Connection,
    subject_id: str,
    opened_on: str,
) -> list[NightlyFeatures]:
    """Nightly features covering the episode, including the week before it opened."""
    start = (date.fromisoformat(opened_on) - timedelta(days=7)).isoformat()
    rows = conn.execute(
        """SELECT * FROM nightly_features
           WHERE subject_id = ? AND night_date >= ?
           ORDER BY night_date ASC""",
        (subject_id, start),
    ).fetchall()
    return [
        NightlyFeatures(
            subject_id=r["subject_id"],
            night_date=date.fromisoformat(r["night_date"]),
            rhr_bpm=r["rhr_bpm"],
            coverage_minutes=r["coverage_minutes"],
            implausible_dropped=r["implausible_dropped"],
            usable=bool(r["usable"]),
            steps_prev_day=r["steps_prev_day"],
            sleep_hours=r["sleep_hours"],
            exercise_end_offset_h=r["exercise_end_offset_h"],
        )
        for r in rows
    ]


def _close_if_concluded(
    conn: sqlite3.Connection,
    episode_id: str,
    result: dict[str, Any],
) -> str:
    """Write a reached disposition back to the episode row and close it.

    Returns the episode state after the write.
    """
    draft = result.get("draft")
    disposition = getattr(draft, "disposition", None)
    if disposition is None:
        action = result.get("action")
        disposition = getattr(action, "disposition", None)

    if disposition is None or result.get("status") not in ("closed", "unresolved"):
        row = conn.execute(
            "SELECT state FROM episodes WHERE episode_id = ?", (episode_id,)
        ).fetchone()
        state = str(row["state"]) if row else "OPEN"

        # A PARKED EPISODE STILL HAS A DRAFT, AND THE REVIEW SCREEN NEEDS IT.
        #
        # The outcome was written only on "closed" or "unresolved", and node_review is the
        # only node that returns either, and it returns them AFTER the interrupt. So an
        # episode waiting for a human had no row in `outcomes`, `get_pending_interaction`
        # returned draft_outcome=None, and the Today page's review branch is
        # `elif pending.kind == "review" and pending.draft_outcome:` - False. Because
        # `pending` was not None the "nothing needs you right now" branch was skipped too,
        # so the inbox rendered NOTHING AT ALL and the person could not approve, edit,
        # reject or escalate. Thirty-six hours later the scheduler released it as
        # closed_unreviewed. Item 3 removed the auto-approval and left the checkpoint
        # unreachable, which is the item's own title unmet.
        #
        # Nothing is closed here and no disposition is written to the episode row. This
        # stores the draft so it can be looked at, which is the whole point of a review.
        if state == "AWAITING_HUMAN_REVIEW" and draft is not None:
            _persist_outcome(conn, episode_id, draft)
        return state

    value = disposition.value if hasattr(disposition, "value") else str(disposition)
    conn.execute(
        """UPDATE episodes
           SET state = 'CLOSED', disposition = ?, closed_on = ?
           WHERE episode_id = ?""",
        (value, _closing_date(conn, episode_id).isoformat(), episode_id),
    )

    # Persist what the agent concluded, not only that it concluded something.
    #
    # Nothing anywhere wrote to the `outcomes` table. The conclude node drafts an
    # observation, a differential, its citations and the action it recommends, and all of
    # it was discarded: only the disposition survived on the episode row. So a person whose
    # episode closed ESCALATED was told to seek care by a message that was never stored,
    # and History could show them a verdict with no reasoning behind it.
    if draft is not None:
        _persist_outcome(conn, episode_id, draft)
        _notify_outcome(conn, episode_id, draft)

    return "CLOSED"


def _notify_outcome(conn: sqlite3.Connection, episode_id: str, draft: Any) -> None:
    """Tell the person what came of the question they answered.

    The system asked, they replied, and nothing ever came back. Three send calls existed in
    the whole application, for a question, a measurement and an escalation, and none for a
    conclusion, so seven episodes reached a disposition and the person heard about only the
    escalations. The transport was already built for this: MessageKind.OUTCOME is the one
    kind Telegram attaches a dashboard link and a "View detail" button to, and the outbound
    safety rules permit a URL only for it. Nothing ever sent one.

    Only episodes the person was actually interrupted for are reported. Telling somebody
    about an investigation they never knew had opened is noise, and the interruption budget
    exists precisely to keep this system quiet.
    """
    asked = conn.execute(
        """SELECT 1 FROM interactions
            WHERE episode_id = ? AND status IN ('ANSWERED', 'DECLINED', 'TIMED_OUT') LIMIT 1""",
        (episode_id,),
    ).fetchone()
    if asked is None:
        return

    row = conn.execute(
        "SELECT subject_id FROM episodes WHERE episode_id = ?", (episode_id,)
    ).fetchone()
    if row is None:
        return

    from wha.notify.factory import get_notifier
    from wha.notify.protocol import MessageKind
    from wha.service.phrasing import disposition_phrase

    # This used to import the words from the dashboard, which meant a service reached up
    # into a screen for what it sends to a phone. The words the system says about a
    # conclusion belong to the system, not to one of its clients.
    label, explanation = disposition_phrase(getattr(draft, "disposition", None))
    observation = getattr(draft, "observation", "") or ""
    text = f"{label}. {explanation}"
    if observation:
        text = text + "\n\n" + observation

    try:
        notifier = get_notifier()
        delivered = notifier.send(
            recipient_id=row["subject_id"],
            kind=MessageKind.OUTCOME,
            text=text,
            interaction_id=episode_id,
        )
        if delivered:
            from wha.agent.repository import EpisodeRepository

            EpisodeRepository(conn=conn).record_notification(
                interaction_id=episode_id,
                recipient=row["subject_id"],
                kind="OUTCOME",
                channel=getattr(notifier, "channel", "none"),
                episode_id=episode_id,
            )
    except Exception:  # noqa: BLE001, S110
        # A transport failure must never stop an episode closing.
        pass


def _closing_date(conn: sqlite3.Connection, episode_id: str) -> date:
    """The night an episode closed on, taken from the data rather than the wall clock.

    `local_today()` is the day the code happens to run, which is not the day the evidence
    describes. Because episodes are keyed by night date, that produced `closed_on` earlier
    than `opened_on`: History rendered investigations as "2026-10-04 to 2026-09-03", and
    the rule that excludes illness nights from a baseline, `night_date BETWEEN opened_on
    AND closed_on`, matched an inverted range and therefore excluded nothing. A subject's
    baseline drifted 59.0 to 63.0 bpm across repeated illness, desensitising detection.
    """
    row = conn.execute(
        """SELECT e.opened_on,
                  (SELECT MAX(d.night_date) FROM detections d
                    WHERE d.subject_id = e.subject_id AND d.night_date >= e.opened_on) AS last_night
             FROM episodes e WHERE e.episode_id = ?""",
        (episode_id,),
    ).fetchone()
    if row is None:
        return local_today()

    opened = date.fromisoformat(row["opened_on"])
    last_night = date.fromisoformat(row["last_night"]) if row["last_night"] else opened
    # Never before the night it opened on, whatever the clock says.
    return max(opened, last_night)


def _persist_outcome(conn: sqlite3.Connection, episode_id: str, draft: Any) -> None:
    """Store the concluded outcome so the person can read it later."""
    try:
        payload = draft.model_dump(mode="json")
    except AttributeError:
        return
    conn.execute(
        """INSERT OR REPLACE INTO outcomes (episode_id, schema_version, payload_json, created_at_utc)
           VALUES (?, ?, ?, ?)""",
        (
            episode_id,
            str(payload.get("schema_version", "1.0")),
            json.dumps(payload),
            to_iso(now_utc()),
        ),
    )


def step_episode(
    episode_id: str,
    db_path: Path | None = None,
    conn: sqlite3.Connection | None = None,
    resume: Any = None,
    restart: bool = False,
) -> dict[str, Any]:
    """Advance an episode by one step synchronously.

    If episode is already CLOSED, this is an idempotent no-op.
    """
    close_conn = False
    if conn is None:
        conn = connect(db_path) if db_path is not None else connect()
        apply_schema(conn)
        close_conn = True

    try:
        ep_row = conn.execute(
            """SELECT episode_id, subject_id, thread_id, opened_on, state, disposition, step_count
               FROM episodes WHERE episode_id = ?""",
            (episode_id,),
        ).fetchone()

        if ep_row is None:
            raise ValueError(f"Episode '{episode_id}' not found")

        if ep_row["state"] == "CLOSED":
            return {
                "episode_id": episode_id,
                "state": "CLOSED",
                "disposition": ep_row["disposition"],
                "step_count": ep_row["step_count"],
                "status": "closed",
            }

        from wha.agent.graph import get_agent_graph, run_episode_step

        # Cached and backed by SqliteSaver, so the checkpoint written by the previous
        # tick is visible to this one. Building a fresh graph here gave every tick an
        # empty in-memory saver, so no interrupt could ever be resumed.
        graph = get_agent_graph(db_path)
        # Seed the episode's evidence. Passing only the identifiers left the agent to
        # reason over an empty night sequence, so the belief never moved off its prior
        # and every episode concluded benign without asking anything.
        initial_state = {
            "episode_id": episode_id,
            "subject_id": ep_row["subject_id"],
            "step": ep_row["step_count"],
            "nights": _episode_nights(conn, ep_row["subject_id"], ep_row["opened_on"]),
            "features": _episode_features(conn, ep_row["subject_id"], ep_row["opened_on"]),
        }
        res = run_episode_step(
            graph,
            episode_id=episode_id,
            initial_state=initial_state,
            resume=resume,
            restart=restart,
        )

        new_step = int(ep_row["step_count"]) + 1
        # tool_call_count and depth_used were columns nothing ever wrote to. After an
        # episode that made three tool calls and asked one question, the row still read
        # zero and zero, so the two figures that evidence the agent doing any work at all
        # were absent from everything that reads the table rather than the graph state.
        conn.execute(
            """UPDATE episodes
                  SET step_count = ?, tool_call_count = ?, depth_used = ?
                WHERE episode_id = ?""",
            (
                new_step,
                int(res.get("tool_call_count") or 0),
                int(res.get("depth_used") or 0),
                episode_id,
            ),
        )

        # Persist the outcome. The graph reached a disposition in state and nothing wrote
        # it back, so an episode that had finished still read as OPEN with no disposition.
        final_state = _close_if_concluded(conn, episode_id, res)

        # Release a parked state the graph is no longer parked on.
        #
        # `node_ask` sets AWAITING_USER before it interrupts, so the interface can surface
        # the question. When the answer arrives and the policy then decides to OBSERVE,
        # the graph routes to END: it is waiting for another night, not for the person.
        # Nothing set the state back, so the screen said "waiting for your answer" with no
        # question to answer, and every later tick ran no nodes at all while still
        # counting as a step. Found by answering a real question from a real phone.
        if final_state and final_state.startswith("AWAITING"):
            from wha.agent.graph import get_pending_interrupt

            try:
                still_parked = get_pending_interrupt(graph, episode_id) is not None
            except (AttributeError, TypeError, ValueError):
                # A graph that cannot report its state cannot prove the episode is free.
                # Leaving it parked is the safe reading: releasing it on a guess could
                # hide a question the person still has to answer.
                still_parked = True
            waiting_on_person = conn.execute(
                """SELECT 1 FROM interactions
                    WHERE episode_id = ? AND status IN ('PENDING', 'ASKED') LIMIT 1""",
                (episode_id,),
            ).fetchone()
            if not still_parked and waiting_on_person is None:
                conn.execute(
                    "UPDATE episodes SET state = 'OPEN' WHERE episode_id = ?", (episode_id,)
                )
                final_state = "OPEN"

        conn.commit()

        return {
            "episode_id": episode_id,
            "state": final_state,
            "step_count": new_step,
            "result": res,
        }
    finally:
        if close_conn:
            conn.close()
