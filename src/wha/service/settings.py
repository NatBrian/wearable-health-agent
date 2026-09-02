"""Service functions for system settings management, configuration updates, and subject data purging."""

import os
import sqlite3
import uuid
from datetime import UTC, datetime

from wha.db import connect
from wha.db.audit_chain import append_audit
from wha.db.migrations import apply_schema
from wha.models import (
    AuditEvent,
    Settings,
    SettingsPatch,
)


def get_service_settings() -> Settings:
    """Retrieve current application settings. Secrets are NEVER returned on this model."""
    channel = os.environ.get("WHA_NOTIFY_CHANNEL", "none")
    if channel not in ("none", "telegram"):
        channel = "none"

    provider = os.environ.get("WHA_LLM_PROVIDER", "cassette")
    if provider not in ("cassette", "ollama_native", "openai_compatible"):
        provider = "cassette"

    return Settings(
        interruption_budget_per_week=int(os.environ.get("WHA_INTERRUPTION_BUDGET_PER_WEEK", "3")),
        depth_budget_per_episode=int(os.environ.get("WHA_DEPTH_BUDGET_PER_EPISODE", "3")),
        policy_cost_weight=float(os.environ.get("WHA_POLICY_COST_WEIGHT", "0.2")),
        notify_channel=channel,  # type: ignore[arg-type]
        llm_provider=provider,  # type: ignore[arg-type]
        llm_model=os.environ.get("WHA_LLM_MODEL", "deepseek-chat"),
        llm_base_url=os.environ.get("WHA_LLM_BASE_URL", "https://api.gptplus5.com/v1"),
        bridge_host=os.environ.get("WHA_BRIDGE_URL", os.environ.get("WHA_BRIDGE_HOST", "http://192.168.198.181:8787")),
    )


def update_settings(
    patch: SettingsPatch,
    subject_id: str = "me",
    conn: sqlite3.Connection | None = None,
) -> Settings:
    """Apply partial settings update, update environment, and record an audit event for policy changes."""
    if patch.interruption_budget_per_week is not None:
        os.environ["WHA_INTERRUPTION_BUDGET_PER_WEEK"] = str(patch.interruption_budget_per_week)
    if patch.depth_budget_per_episode is not None:
        os.environ["WHA_DEPTH_BUDGET_PER_EPISODE"] = str(patch.depth_budget_per_episode)
    if patch.policy_cost_weight is not None:
        os.environ["WHA_POLICY_COST_WEIGHT"] = str(patch.policy_cost_weight)
    if patch.notify_channel is not None:
        os.environ["WHA_NOTIFY_CHANNEL"] = patch.notify_channel
    if patch.llm_provider is not None:
        os.environ["WHA_LLM_PROVIDER"] = patch.llm_provider
    if patch.llm_model is not None:
        os.environ["WHA_LLM_MODEL"] = patch.llm_model
    if patch.llm_base_url is not None:
        os.environ["WHA_LLM_BASE_URL"] = patch.llm_base_url
    if patch.bridge_host is not None:
        os.environ["WHA_BRIDGE_HOST"] = patch.bridge_host
    if patch.bridge_token is not None:
        os.environ["WHA_BRIDGE_TOKEN"] = patch.bridge_token.get_secret_value()
    if patch.llm_api_key is not None:
        os.environ["WHA_LLM_API_KEY"] = patch.llm_api_key.get_secret_value()
    if patch.telegram_token is not None:
        os.environ["WHA_TELEGRAM_TOKEN"] = patch.telegram_token.get_secret_value()

    close_conn = False
    if conn is None:
        conn = connect()
        apply_schema(conn)
        close_conn = True

    try:
        # Redact secrets for audit payload
        patch_dict = patch.model_dump(
            mode="json", exclude={"bridge_token", "llm_api_key", "telegram_token"}
        )
        audit_ev = AuditEvent(
            event_id=f"audit_set_{uuid.uuid4().hex[:12]}",
            subject_id=subject_id,
            timestamp_utc=datetime.now(UTC),
            actor="human",
            operation="settings",
            input={"patch": patch_dict},
        )
        append_audit(conn, audit_ev)
        conn.commit()
    finally:
        if close_conn:
            conn.close()

    return get_service_settings()


def delete_all_subject_data(
    subject_id: str,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Permanently delete all records for a subject across all database tables in one transaction.

    Leaves database schema intact and usable.
    """
    close_conn = False
    if conn is None:
        conn = connect()
        apply_schema(conn)
        close_conn = True

    try:
        with conn:
            # Delete in foreign key dependency order
            tables_with_subject = [
                "raw_payloads",
                "heart_rate_samples",
                "step_buckets",
                "sleep_stages",
                "exercise_sessions",
                "nightly_features",
                "baselines",
                "detections",
                "budgets",
                "system_status",
                "notifications",
                "audit_events",
            ]
            for t in tables_with_subject:
                conn.execute(f"DELETE FROM {t} WHERE subject_id = ?", (subject_id,))

            # Find episodes for subject to delete interactions, measurements, outcomes, beliefs
            ep_rows = conn.execute(
                "SELECT episode_id FROM episodes WHERE subject_id = ?", (subject_id,)
            ).fetchall()
            for ep in ep_rows:
                ep_id = ep["episode_id"]
                conn.execute("DELETE FROM interactions WHERE episode_id = ?", (ep_id,))
                conn.execute("DELETE FROM measurements WHERE episode_id = ?", (ep_id,))
                conn.execute("DELETE FROM outcomes WHERE episode_id = ?", (ep_id,))
                conn.execute("DELETE FROM beliefs WHERE episode_id = ?", (ep_id,))

            # The agent's checkpointed state is keyed by thread_id, which is the episode
            # id. It holds the person's answers and beliefs verbatim, so a delete that
            # left it behind would not be a delete. These tables are created by the
            # LangGraph SQLite saver and may not exist before the first episode runs.
            for ep in ep_rows:
                ep_id = ep["episode_id"]
                for table in ("checkpoints", "writes"):
                    try:
                        conn.execute(f"DELETE FROM {table} WHERE thread_id = ?", (ep_id,))
                    except sqlite3.OperationalError:
                        pass

            conn.execute("DELETE FROM episodes WHERE subject_id = ?", (subject_id,))
            conn.execute("DELETE FROM subjects WHERE subject_id = ?", (subject_id,))
    finally:
        if close_conn:
            conn.close()
