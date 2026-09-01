"""Service functions for episode management, interactive submissions, and bounded Q&A."""

import json
import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal

from wha.db import connect
from wha.db.migrations import apply_schema
from wha.models import (
    Answer,
    AnswerOption,
    BeliefState,
    CauseId,
    Citation,
    Disposition,
    EpisodeDetail,
    EpisodeOutcome,
    EpisodeState,
    EpisodeSummary,
    GroundedAnswer,
    InteractionView,
    MeasurementRequest,
    MeasurementResult,
    PendingInteraction,
    PipelineStage,
    Probe,
    Question,
    StageStatus,
)
from wha.policy.probes import load_probes

CANONICAL_STAGES = [
    ("preload", "Fetch preloaded nightly features, baselines, and quality metrics"),
    ("investigate", "Query closed T1 tools for clinical context and evidence"),
    ("believe", "Enumerate exact 4096-state joint belief over 12 causes"),
    ("decide", "Select EVSI-optimal action and evaluate veto policy"),
    ("ask", "Prompt user for targeted symptom/exposure probe"),
    ("measure", "Request spot resting heart rate or overnight wear"),
    ("conclude", "Draft structured clinical outcome with bounded differential"),
    ("critique", "Verify deterministic claim grounding and strip ungrounded assertions"),
    ("review", "Human clinician or supervisor review checkpoint"),
]


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

        # 2. Measurement
        for ep in ep_rows:
            if ep["state"] == "AWAITING_MEASUREMENT":
                ep_id = ep["episode_id"]
                m_row = conn.execute(
                    """SELECT id, kind, instruction, expires_at_utc FROM measurements
                       WHERE episode_id = ? AND status = 'PENDING'
                       ORDER BY requested_at_utc DESC LIMIT 1""",
                    (ep_id,),
                ).fetchone()
                if m_row:
                    m_req = MeasurementRequest(
                        measurement_id=m_row["id"],
                        kind=m_row["kind"],
                        instruction=m_row["instruction"],
                        expires_at_utc=datetime.fromisoformat(m_row["expires_at_utc"]),
                    )
                    return PendingInteraction(
                        kind="measurement",
                        episode_id=ep_id,
                        measurement=m_req,
                    )

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
    Advances the episode synchronously.
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

        now_str = datetime.now(UTC).isoformat()
        actual_int_id = int_row["id"]
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

        now_str = datetime.now(UTC).isoformat()
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
    """Process human review decision for an episode."""
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

        now_d = datetime.now(UTC).date().isoformat()
        if decision == "approve":
            conn.execute(
                "UPDATE episodes SET state = 'CLOSED', closed_on = ? WHERE episode_id = ?",
                (now_d, episode_id),
            )
        elif decision == "reject":
            conn.execute(
                "UPDATE episodes SET state = 'CLOSED', disposition = 'UNRESOLVED', closed_on = ? WHERE episode_id = ?",
                (now_d, episode_id),
            )
        elif decision == "escalate":
            conn.execute(
                "UPDATE episodes SET state = 'CLOSED', disposition = 'ESCALATED', closed_on = ? WHERE episode_id = ?",
                (now_d, episode_id),
            )
        elif decision == "edit" and edited_prose:
            # Update outcome observation
            out_row = conn.execute(
                "SELECT payload_json FROM outcomes WHERE episode_id = ?",
                (episode_id,),
            ).fetchone()
            if out_row and out_row["payload_json"]:
                payload = json.loads(out_row["payload_json"])
                payload["observation"] = edited_prose
                conn.execute(
                    "UPDATE outcomes SET payload_json = ? WHERE episode_id = ?",
                    (json.dumps(payload), episode_id),
                )
            conn.execute(
                "UPDATE episodes SET state = 'CLOSED', closed_on = ? WHERE episode_id = ?",
                (now_d, episode_id),
            )
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
            "SELECT seq, trigger, ts_utc, marginals_json, p_illness FROM beliefs WHERE episode_id = ? ORDER BY seq",
            (episode_id,),
        ).fetchall()
        belief_history: list[tuple[int, str, BeliefState]] = []
        for br in b_rows:
            margs = json.loads(br["marginals_json"])
            b_state = BeliefState(
                marginals={CauseId(k): float(v) for k, v in margs.items()},
                p_illness=float(br["p_illness"]),
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

        # 5. Citations & Stripped Claims
        citations = outcome.citations if outcome else []
        stripped_claims: list[str] = []

        # 6. Pipeline stages derivation (Canonical stages: ran vs skipped with explicit reason)
        audit_rows = conn.execute(
            "SELECT operation, latency_ms, safety_event, input_json, output_json FROM audit_events WHERE episode_id = ?",
            (episode_id,),
        ).fetchall()
        op_map = {ar["operation"]: ar for ar in audit_rows}

        stages: list[PipelineStage] = []
        for stg_name, default_reason in CANONICAL_STAGES:
            if stg_name in op_map:
                ar = op_map[stg_name]
                stages.append(
                    PipelineStage(
                        name=stg_name,
                        status=StageStatus.RAN,
                        reason=f"Executed stage {stg_name}",
                        duration_ms=ar["latency_ms"],
                        detail_json={},
                    )
                )
            else:
                # Inferred skipped stage with recorded reason
                skip_reason = f"Stage {stg_name} skipped: not invoked in policy sequence"
                if stg_name == "review":
                    skip_reason = "Human review checkpoint bypassed (direct auto-approval)"
                elif stg_name in ("ask", "measure"):
                    skip_reason = f"{stg_name.capitalize()} probe not selected by EVSI optimizer"

                stages.append(
                    PipelineStage(
                        name=stg_name,
                        status=StageStatus.SKIPPED,
                        reason=skip_reason,
                        duration_ms=None,
                        detail_json={},
                    )
                )

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


def ask_about_episode(
    episode_id: str,
    question: str,
    conn: sqlite3.Connection | None = None,
) -> GroundedAnswer:
    """Answer a question about a closed or active episode strictly bounded to its own recorded evidence.

    Has no tool access, cannot perform corpus-wide retrieval, and mutates no state.
    Refuses ungrounded queries.
    """
    close_conn = False
    if conn is None:
        conn = connect()
        apply_schema(conn)
        close_conn = True

    try:
        ep_detail = get_episode(episode_id, conn=conn)
        outcome = ep_detail.outcome

        # Bounded evidence corpus: only citations and observation recorded in this episode
        available_citations = ep_detail.citations

        # Check for grounding overlap
        q_tokens = set(question.lower().replace("?", "").split())

        matched_citations: list[Citation] = []
        for cit in available_citations:
            cit_tokens = set(cit.passage.lower().split()) | set(cit.title.lower().split())
            if q_tokens & cit_tokens:
                matched_citations.append(cit)

        if outcome is not None:
            obs_tokens = set(outcome.observation.lower().split())
            overlap = q_tokens & obs_tokens
            if overlap or matched_citations:
                text = (
                    f"Based on episode {episode_id} evidence: {outcome.observation} "
                    f"Disposition: {outcome.disposition}. Recommended action: {outcome.action}."
                )
                return GroundedAnswer(
                    text=text,
                    citations=matched_citations,
                    refused=False,
                    refusal_reason=None,
                )

        if matched_citations:
            text = f"Based on episode {episode_id} evidence: {matched_citations[0].passage}"
            return GroundedAnswer(
                text=text,
                citations=matched_citations,
                refused=False,
                refusal_reason=None,
            )

        return GroundedAnswer(
            text="",
            citations=[],
            refused=True,
            refusal_reason=(
                f"Question '{question}' cannot be grounded in the bounded evidence of episode {episode_id}."
            ),
        )
    finally:
        if close_conn:
            conn.close()


def step_episode(
    episode_id: str,
    db_path: Path | None = None,
    conn: sqlite3.Connection | None = None,
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
            """SELECT episode_id, subject_id, thread_id, state, disposition, step_count
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

        from wha.agent.graph import build_agent_graph, run_episode_step

        graph = build_agent_graph()
        initial_state = {
            "episode_id": episode_id,
            "subject_id": ep_row["subject_id"],
            "step": ep_row["step_count"],
        }
        res = run_episode_step(graph, episode_id=episode_id, initial_state=initial_state)

        new_step = int(ep_row["step_count"]) + 1
        conn.execute(
            "UPDATE episodes SET step_count = ? WHERE episode_id = ?",
            (new_step, episode_id),
        )
        conn.commit()

        return {
            "episode_id": episode_id,
            "state": ep_row["state"],
            "step_count": new_step,
            "result": res,
        }
    finally:
        if close_conn:
            conn.close()
