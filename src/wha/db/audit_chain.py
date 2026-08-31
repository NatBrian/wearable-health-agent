"""Audit hash chain implementation for append-only tamper-evident event logging."""

import hashlib
import json
import sqlite3
from collections.abc import Mapping
from typing import Any

from wha.db.iso import to_iso
from wha.models import AuditEvent


def canonical_json(obj: Any) -> str:
    """Deterministic JSON serialization with sorted keys and no unnecessary whitespace."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_audit_hash(prev_hash: str | None, payload: Mapping[str, Any]) -> str:
    """Compute sha256( (prev_hash or '') + canonical_json(row_without_hash_fields) )."""
    prev_str = prev_hash if prev_hash is not None else ""
    serialized = canonical_json(payload)
    content = prev_str + serialized
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _build_row_payload(event: AuditEvent) -> dict[str, Any]:
    """Convert AuditEvent model to canonical dict for hash computation and storage."""
    input_json = canonical_json(event.input) if event.input is not None else None
    tool_args_json = canonical_json(event.tool_args) if event.tool_args is not None else None
    tool_result_json = canonical_json(event.tool_result) if event.tool_result is not None else None
    sources_json = canonical_json(event.sources)
    output_json = canonical_json(event.output) if event.output is not None else None
    token_usage_json = canonical_json(event.token_usage) if event.token_usage is not None else None
    ts_str = to_iso(event.timestamp_utc)

    return {
        "actor": event.actor,
        "checkpoint_id": event.checkpoint_id,
        "control_tier": event.control_tier.value if event.control_tier else None,
        "episode_id": event.episode_id,
        "event_id": event.event_id,
        "human_decision": event.human_decision,
        "human_decision_rationale": event.human_decision_rationale,
        "input_json": input_json,
        "latency_ms": event.latency_ms,
        "model_id": event.model_id,
        "operation": event.operation,
        "output_json": output_json,
        "output_schema_version": event.output_schema_version,
        "permission_decision": (
            event.permission_decision.value
            if hasattr(event.permission_decision, "value")
            else event.permission_decision
        ),
        "prompt_id": event.prompt_id,
        "prompt_version": event.prompt_version,
        "safety_event": event.safety_event,
        "sources_json": sources_json,
        "step_index": event.step_index,
        "subject_id": event.subject_id,
        "timestamp_utc": ts_str,
        "token_usage_json": token_usage_json,
        "tool_args_json": tool_args_json,
        "tool_name": event.tool_name,
        "tool_result_json": tool_result_json,
        "validation_status": (
            event.validation_status.value
            if hasattr(event.validation_status, "value")
            else event.validation_status
        ),
    }


def append_audit(conn: sqlite3.Connection, event: AuditEvent) -> str:
    """Append one audit event chained to the subject's previous event. Returns the new hash."""
    cursor = conn.execute(
        "SELECT hash FROM audit_events WHERE subject_id = ? ORDER BY rowid DESC LIMIT 1;",
        (event.subject_id,),
    )
    row = cursor.fetchone()
    prev_hash: str | None = row["hash"] if row is not None else None

    payload = _build_row_payload(event)
    event_hash = compute_audit_hash(prev_hash, payload)

    conn.execute(
        """
        INSERT INTO audit_events (
            event_id, subject_id, episode_id, step_index, checkpoint_id,
            timestamp_utc, actor, operation, control_tier, input_json,
            tool_name, tool_args_json, tool_result_json, permission_decision,
            sources_json, output_json, output_schema_version, validation_status,
            human_decision, human_decision_rationale, model_id, prompt_id,
            prompt_version, latency_ms, token_usage_json, safety_event,
            prev_hash, hash
        ) VALUES (
            :event_id, :subject_id, :episode_id, :step_index, :checkpoint_id,
            :timestamp_utc, :actor, :operation, :control_tier, :input_json,
            :tool_name, :tool_args_json, :tool_result_json, :permission_decision,
            :sources_json, :output_json, :output_schema_version, :validation_status,
            :human_decision, :human_decision_rationale, :model_id, :prompt_id,
            :prompt_version, :latency_ms, :token_usage_json, :safety_event,
            :prev_hash, :hash
        );
        """,
        {**payload, "prev_hash": prev_hash, "hash": event_hash},
    )

    return event_hash


def verify_chain(conn: sqlite3.Connection, subject_id: str) -> tuple[bool, str | None]:
    """Walk the audit chain for a subject.

    Returns (True, None) if the chain is valid and intact.
    Returns (False, first_bad_event_id) if tampering or broken linkage is detected.
    """
    cursor = conn.execute(
        """
        SELECT
            event_id, subject_id, episode_id, step_index, checkpoint_id,
            timestamp_utc, actor, operation, control_tier, input_json,
            tool_name, tool_args_json, tool_result_json, permission_decision,
            sources_json, output_json, output_schema_version, validation_status,
            human_decision, human_decision_rationale, model_id, prompt_id,
            prompt_version, latency_ms, token_usage_json, safety_event,
            prev_hash, hash
        FROM audit_events
        WHERE subject_id = ?
        ORDER BY rowid ASC;
        """,
        (subject_id,),
    )
    rows = cursor.fetchall()
    if not rows:
        return True, None

    expected_prev_hash: str | None = None
    for row in rows:
        event_id = row["event_id"]
        actual_prev_hash = row["prev_hash"]
        actual_hash = row["hash"]

        # Verify prev_hash linkage
        if actual_prev_hash != expected_prev_hash:
            return False, event_id

        # Recompute hash for row
        row_payload = {
            "actor": row["actor"],
            "checkpoint_id": row["checkpoint_id"],
            "control_tier": row["control_tier"],
            "episode_id": row["episode_id"],
            "event_id": row["event_id"],
            "human_decision": row["human_decision"],
            "human_decision_rationale": row["human_decision_rationale"],
            "input_json": row["input_json"],
            "latency_ms": row["latency_ms"],
            "model_id": row["model_id"],
            "operation": row["operation"],
            "output_json": row["output_json"],
            "output_schema_version": row["output_schema_version"],
            "permission_decision": row["permission_decision"],
            "prompt_id": row["prompt_id"],
            "prompt_version": row["prompt_version"],
            "safety_event": row["safety_event"],
            "sources_json": row["sources_json"],
            "step_index": row["step_index"],
            "subject_id": row["subject_id"],
            "timestamp_utc": row["timestamp_utc"],
            "token_usage_json": row["token_usage_json"],
            "tool_args_json": row["tool_args_json"],
            "tool_name": row["tool_name"],
            "tool_result_json": row["tool_result_json"],
            "validation_status": row["validation_status"],
        }

        recomputed_hash = compute_audit_hash(actual_prev_hash, row_payload)
        if recomputed_hash != actual_hash:
            return False, event_id

        expected_prev_hash = actual_hash

    return True, None
