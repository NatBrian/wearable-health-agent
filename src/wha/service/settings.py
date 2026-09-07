"""Service functions for system settings management, configuration updates, and subject data purging."""

import os
import sqlite3
import uuid
from pathlib import Path

from wha.clock import now_utc
from wha.db import connect
from wha.db.audit_chain import append_audit
from wha.db.iso import from_iso, to_iso
from wha.db.migrations import apply_schema
from wha.models import (
    AuditEvent,
    Settings,
    SettingsPatch,
    SubjectProfile,
    SubjectProfilePatch,
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
        llm_base_url=os.environ.get("WHA_LLM_BASE_URL", "https://openrouter.ai/api/v1"),
        # WHA_BRIDGE_URL is the canonical name, and the one config.py reads. This used to
        # read URL first but update_settings wrote HOST, so .env permanently shadowed every
        # change made in the Settings page: the displayed value never moved and ingestion
        # kept using the old address. The default is empty rather than a hardcoded address,
        # which was a specific person's phone on a specific network.
        bridge_host=os.environ.get("WHA_BRIDGE_URL", ""),
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
        os.environ["WHA_BRIDGE_URL"] = patch.bridge_host
        # Kept in step for anything still reading the older name.
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
            timestamp_utc=now_utc(),
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
            # THE TABLE LIST IS READ OUT OF THE SCHEMA, NOT WRITTEN DOWN HERE.
            #
            # It used to be a hand-maintained list of fifteen names, and it silently fell
            # behind the schema four times. On 5 September 2026 the schema had 27 tables and
            # this function covered 19 of them. The four it missed were `subject_profile`
            # and `episode_traces` (added in v7 and v8), and, for far longer,
            # `conversation_turns` and `triage_answers`: the person's entire chat transcript
            # and their answers to the triage rules, which are the most sensitive rows in
            # the database.
            #
            # Worse than incomplete, it was inert. `subject_profile` and `episode_traces`
            # carry foreign keys to `subjects` and `episodes`, so leaving them behind made
            # the final two DELETEs raise FOREIGN KEY constraint failed, and `with conn:`
            # rolled the whole transaction back. Measured on a copy of the real database
            # with one saved Settings profile present: 58,730 heart rate samples before,
            # 58,730 after. "Delete everything" deleted nothing.
            #
            # Introspection is what makes that unrepeatable: a table added tomorrow with a
            # subject_id or episode_id column is covered the day it is added.
            all_tables = [
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' "
                    "AND name NOT LIKE 'sqlite_%'"
                ).fetchall()
            ]

            def columns_of(table: str) -> set[str]:
                return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}

            # `subjects` and `episodes` are the parents and go last, after their children.
            by_subject = sorted(
                t
                for t in all_tables
                if "subject_id" in columns_of(t) and t not in ("subjects", "episodes")
            )
            by_episode = sorted(
                t for t in all_tables if "episode_id" in columns_of(t) and t != "episodes"
            )

            ep_rows = conn.execute(
                "SELECT episode_id FROM episodes WHERE subject_id = ?", (subject_id,)
            ).fetchall()
            ep_ids = [ep["episode_id"] for ep in ep_rows]

            # Episode-scoped children first: some carry no subject_id of their own, so this
            # is the only pass that reaches them.
            if ep_ids:
                placeholders = ",".join("?" for _ in ep_ids)
                for t in by_episode:
                    conn.execute(f"DELETE FROM {t} WHERE episode_id IN ({placeholders})", ep_ids)

            for t in by_subject:
                conn.execute(f"DELETE FROM {t} WHERE subject_id = ?", (subject_id,))

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


def get_subject_profile(
    subject_id: str = "me",
    conn: sqlite3.Connection | None = None,
    db_path: "Path | None" = None,
) -> SubjectProfile:
    """The five standing facts, or an empty profile if none has been set.

    An empty profile is not an error. Everything that reads it treats a missing value as
    "unknown" and behaves conservatively, which is the whole reason the Marburg age gate
    exists: it must refuse to score rather than guess.
    """
    close_conn = False
    if conn is None:
        conn = connect(db_path) if db_path is not None else connect()
        apply_schema(conn)
        close_conn = True
    try:
        row = conn.execute(
            "SELECT * FROM subject_profile WHERE subject_id = ?", (subject_id,)
        ).fetchone()
        if row is None:
            return SubjectProfile(subject_id=subject_id)
        return SubjectProfile(
            subject_id=row["subject_id"],
            age_years=row["age_years"],
            sex=row["sex"],
            known_vascular_disease=_as_bool(row["known_vascular_disease"]),
            menstruates=_as_bool(row["menstruates"]),
            rate_lowering_medicine=_as_bool(row["rate_lowering_medicine"]),
            notes_for_doctor=row["notes_for_doctor"],
            updated_at_utc=from_iso(row["updated_at_utc"]) if row["updated_at_utc"] else None,
        )
    finally:
        if close_conn:
            conn.close()


def _as_bool(value: object) -> bool | None:
    """SQLite has no boolean, and None must stay None rather than becoming False."""
    return None if value is None else bool(value)


def update_subject_profile(
    patch: SubjectProfilePatch,
    subject_id: str = "me",
    conn: sqlite3.Connection | None = None,
    db_path: "Path | None" = None,
) -> SubjectProfile:
    """Apply a partial update, and record it, because it changes how rules decide.

    Setting an age changes whether the Marburg Heart Score is applied at all, and setting
    whether the person menstruates switches a cause in the belief model on or off. Both are
    decisions about how this system will reason about someone's health, so they belong in
    the record The record screen shows, under the `settings` operation the contract reserves.
    """
    close_conn = False
    if conn is None:
        conn = connect(db_path) if db_path is not None else connect()
        apply_schema(conn)
        close_conn = True
    try:
        current = get_subject_profile(subject_id, conn=conn)
        merged = current.model_copy(
            update={
                field: value
                for field, value in patch.model_dump(exclude_unset=True).items()
                if value is not None
            }
        )
        now = to_iso(now_utc())
        conn.execute(
            """INSERT INTO subject_profile
                 (subject_id, age_years, sex, known_vascular_disease, menstruates,
                  rate_lowering_medicine, notes_for_doctor, updated_at_utc)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(subject_id) DO UPDATE SET
                 age_years = excluded.age_years,
                 sex = excluded.sex,
                 known_vascular_disease = excluded.known_vascular_disease,
                 menstruates = excluded.menstruates,
                 rate_lowering_medicine = excluded.rate_lowering_medicine,
                 notes_for_doctor = excluded.notes_for_doctor,
                 updated_at_utc = excluded.updated_at_utc""",
            (
                subject_id,
                merged.age_years,
                merged.sex,
                None
                if merged.known_vascular_disease is None
                else int(merged.known_vascular_disease),
                None if merged.menstruates is None else int(merged.menstruates),
                None
                if merged.rate_lowering_medicine is None
                else int(merged.rate_lowering_medicine),
                merged.notes_for_doctor,
                now,
            ),
        )
        changed = sorted(patch.model_dump(exclude_unset=True))
        append_audit(
            conn,
            AuditEvent(
                event_id=f"evt_{uuid.uuid4().hex[:12]}",
                subject_id=subject_id,
                timestamp_utc=now_utc(),
                actor="human",
                operation="settings",
                output={
                    "fields_changed": changed,
                    # The values themselves are not recorded. They are health facts about
                    # the person, they are readable in the profile, and the audit log is
                    # exported. What matters here is that a rule's inputs changed and when.
                    "summary": (
                        "You changed your profile. That changes how the rules decide: "
                        "your age decides whether the chest pain rule can be applied to "
                        "you at all, and whether you menstruate switches a cause in the "
                        "model on or off."
                    ),
                },
            ),
        )
        conn.commit()
        return get_subject_profile(subject_id, conn=conn)
    finally:
        if close_conn:
            conn.close()
