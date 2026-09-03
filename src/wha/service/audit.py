"""Service functions for audit trail querying, hash-chain verification, and data export."""

import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from wha.db import connect
from wha.db.audit_chain import _build_row_payload, compute_audit_hash, verify_chain
from wha.db.migrations import apply_schema
from wha.models import AuditEvent, AuditEventView, AuditFilter, ControlTier


def query_audit(
    f: AuditFilter,
    limit: int = 100,
    offset: int = 0,
    conn: sqlite3.Connection | None = None,
) -> list[AuditEventView]:
    """Query audit events matching the provided filter with row-level hash-chain verification.

    Handles empty database cleanly.
    """
    close_conn = False
    if conn is None:
        conn = connect()
        apply_schema(conn)
        close_conn = True

    try:
        query_parts = ["SELECT * FROM audit_events WHERE subject_id = ?"]
        params: list[str | int] = [f.subject_id]

        if f.episode_id is not None:
            query_parts.append("AND episode_id = ?")
            params.append(f.episode_id)

        if f.actor is not None:
            query_parts.append("AND actor = ?")
            params.append(f.actor)

        if f.operation is not None:
            query_parts.append("AND operation = ?")
            params.append(f.operation)

        if f.safety_event is not None:
            query_parts.append("AND safety_event = ?")
            params.append(f.safety_event)

        if f.since_utc is not None:
            query_parts.append("AND timestamp_utc >= ?")
            params.append(f.since_utc.isoformat())

        if f.until_utc is not None:
            query_parts.append("AND timestamp_utc <= ?")
            params.append(f.until_utc.isoformat())

        query_parts.append("ORDER BY timestamp_utc ASC LIMIT ? OFFSET ?")
        params.extend([limit, offset])

        sql = " ".join(query_parts)
        rows = conn.execute(sql, params).fetchall()

        events: list[AuditEventView] = []
        for r in rows:
            sources = json.loads(r["sources_json"]) if r["sources_json"] else []
            tier = ControlTier(r["control_tier"]) if r["control_tier"] else None

            # Verify row-level hash
            try:
                event_obj = AuditEvent(
                    event_id=r["event_id"],
                    subject_id=r["subject_id"],
                    episode_id=r["episode_id"],
                    step_index=r["step_index"],
                    checkpoint_id=r["checkpoint_id"],
                    timestamp_utc=datetime.fromisoformat(r["timestamp_utc"]),
                    actor=r["actor"],
                    operation=r["operation"],
                    control_tier=tier,
                    input=json.loads(r["input_json"]) if r["input_json"] else None,
                    tool_name=r["tool_name"],
                    tool_args=json.loads(r["tool_args_json"]) if r["tool_args_json"] else None,
                    tool_result=json.loads(r["tool_result_json"])
                    if r["tool_result_json"]
                    else None,
                    permission_decision=r["permission_decision"],
                    sources=sources,
                    output=json.loads(r["output_json"]) if r["output_json"] else None,
                    output_schema_version=r["output_schema_version"],
                    validation_status=r["validation_status"],
                    human_decision=r["human_decision"],
                    human_decision_rationale=r["human_decision_rationale"],
                    model_id=r["model_id"],
                    prompt_id=r["prompt_id"],
                    prompt_version=r["prompt_version"],
                    latency_ms=r["latency_ms"],
                    token_usage=json.loads(r["token_usage_json"])
                    if r["token_usage_json"]
                    else None,
                    safety_event=r["safety_event"],
                )
                payload = _build_row_payload(event_obj)
                expected_hash = compute_audit_hash(r["prev_hash"], payload)
                hash_ok = r["hash"] == expected_hash
            except (ValueError, TypeError, KeyError):
                hash_ok = False

            events.append(
                AuditEventView(
                    event_id=r["event_id"],
                    timestamp_utc=datetime.fromisoformat(r["timestamp_utc"]),
                    episode_id=r["episode_id"],
                    step_index=r["step_index"],
                    actor=r["actor"],
                    operation=r["operation"],
                    control_tier=tier,
                    tool_name=r["tool_name"],
                    permission_decision=r["permission_decision"],
                    sources=sources,
                    validation_status=r["validation_status"],
                    human_decision=r["human_decision"],
                    safety_event=r["safety_event"],
                    latency_ms=r["latency_ms"],
                    hash_ok=hash_ok,
                )
            )

        return events
    finally:
        if close_conn:
            conn.close()


def list_plain_records(
    subject_id: str,
    limit: int = 20,
    conn: sqlite3.Connection | None = None,
) -> list[dict]:
    """Recent deterministic entries, as the sentences a person can actually read.

    The raw event table is precise and unreadable. Every monitor entry carries a `plain`
    narrative written for someone with no medical or technical background, and this is what
    the page shows; the table underneath keeps the exact fields for anyone checking.
    """
    close_conn = False
    if conn is None:
        conn = connect()
        apply_schema(conn)
        close_conn = True
    try:
        rows = conn.execute(
            """SELECT event_id, timestamp_utc, actor, operation, output_json
                 FROM audit_events
                WHERE subject_id = ? AND actor IN ('monitor', 'system')
                ORDER BY timestamp_utc DESC, rowid DESC
                LIMIT ?""",
            (subject_id, limit),
        ).fetchall()
    finally:
        if close_conn:
            conn.close()

    out: list[dict] = []
    for r in rows:
        try:
            payload = json.loads(r["output_json"]) if r["output_json"] else {}
        except (TypeError, ValueError):
            payload = {}
        sentences = payload.get("plain")
        if not sentences:
            summary = payload.get("summary")
            sentences = [summary] if summary else []
        out.append(
            {
                "event_id": r["event_id"],
                "timestamp_utc": r["timestamp_utc"],
                "operation": r["operation"],
                "night": payload.get("night"),
                "sentences": sentences,
                "detail": payload,
            }
        )
    return out


def count_audit_events(subject_id: str, conn: sqlite3.Connection | None = None) -> int:
    """How many entries the record holds. An empty chain verifies, so callers must ask."""
    close_conn = False
    if conn is None:
        conn = connect()
        apply_schema(conn)
        close_conn = True
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM audit_events WHERE subject_id = ?", (subject_id,)
        ).fetchone()
        return int(row[0]) if row else 0
    finally:
        if close_conn:
            conn.close()


def verify_hash_chain(
    subject_id: str,
    conn: sqlite3.Connection | None = None,
) -> tuple[bool, str | None]:
    """Verify cryptographic SHA-256 hash chain across all audit events for a subject.

    Returns (True, None) if intact, or (False, first_bad_event_id) on discrepancy.
    """
    close_conn = False
    if conn is None:
        conn = connect()
        apply_schema(conn)
        close_conn = True

    try:
        return verify_chain(conn, subject_id)
    finally:
        if close_conn:
            conn.close()


def export_audit(
    f: AuditFilter,
    path: Path,
    conn: sqlite3.Connection | None = None,
) -> Path:
    """Export filtered audit trail to CSV or JSON.

    Secrets are guaranteed absent from the audit trail by design.
    """
    events = query_audit(f, limit=100000, offset=0, conn=conn)

    target_path = Path(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if str(target_path).lower().endswith(".json"):
        records = [e.model_dump(mode="json") for e in events]
        target_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    else:
        # Default CSV export
        with open(target_path, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "event_id",
                "timestamp_utc",
                "episode_id",
                "step_index",
                "actor",
                "operation",
                "control_tier",
                "tool_name",
                "permission_decision",
                "sources",
                "validation_status",
                "human_decision",
                "safety_event",
                "latency_ms",
                "hash_ok",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for e in events:
                row_dict = e.model_dump(mode="json")
                row_dict["sources"] = ";".join(row_dict.get("sources", []))
                writer.writerow(row_dict)

    return target_path


def get_permitted_tool_names() -> list[str]:
    """Names of every tool the agent is allowed to call, for display in the audit view.

    Exposed here because the UI layer may not import from wha.agent, and because a page
    that lists the tools by hand drifts from the registry that actually enforces them.
    """
    from wha.agent.tools.registry import CLOSED_TOOL_REGISTRY

    return sorted(CLOSED_TOOL_REGISTRY)
