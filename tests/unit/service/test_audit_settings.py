"""Unit tests for audit trail, settings management, subject data deletion, and evaluation services."""

import re
from pathlib import Path

from pydantic import SecretStr

from wha.db import connect
from wha.db.migrations import apply_schema
from wha.models import (
    AuditFilter,
    EvaluationResult,
    Settings,
    SettingsPatch,
)
from wha.service import (
    delete_all_subject_data,
    export_audit,
    get_evaluation_results,
    get_service_settings,
    query_audit,
    update_settings,
)


def test_audit_export_contains_no_secrets(tmp_path: Path) -> None:
    """Exported audit log in JSON and CSV contains no secret keys or token values."""
    conn = connect(":memory:")
    apply_schema(conn)
    subject_id = "sub_audit_test"

    # Insert a settings update with SecretStr
    patch = SettingsPatch(
        interruption_budget_per_week=5,
        telegram_token=SecretStr("123456:SECRET_BOT_TOKEN_XYZ"),
        bridge_token=SecretStr("BRIDGE_SECRET_BEARER_999"),
    )
    update_settings(patch, subject_id=subject_id, conn=conn)

    export_json = tmp_path / "audit_export.json"
    export_csv = tmp_path / "audit_export.csv"

    af = AuditFilter(subject_id=subject_id)
    export_audit(af, export_json, conn=conn)
    export_audit(af, export_csv, conn=conn)

    json_text = export_json.read_text(encoding="utf-8")
    csv_text = export_csv.read_text(encoding="utf-8")

    assert "SECRET_BOT_TOKEN_XYZ" not in json_text
    assert "BRIDGE_SECRET_BEARER_999" not in json_text
    assert "SECRET_BOT_TOKEN_XYZ" not in csv_text
    assert "BRIDGE_SECRET_BEARER_999" not in csv_text


def test_settings_never_returns_secrets() -> None:
    """get_service_settings model has no secret attributes and never exposes credentials."""
    settings = get_service_settings()
    assert isinstance(settings, Settings)
    assert not hasattr(settings, "telegram_token")
    assert not hasattr(settings, "bridge_token")
    assert not hasattr(settings, "llm_api_key")


def test_policy_change_writes_audit_event() -> None:
    """Updating a policy threshold or budget writes a signed audit event."""
    conn = connect(":memory:")
    apply_schema(conn)
    subject_id = "sub_policy_audit"

    patch = SettingsPatch(interruption_budget_per_week=4, policy_cost_weight=0.35)
    update_settings(patch, subject_id=subject_id, conn=conn)

    events = query_audit(AuditFilter(subject_id=subject_id, operation="settings"), conn=conn)
    assert len(events) == 1
    assert events[0].operation == "settings"
    assert events[0].actor == "human"
    assert events[0].hash_ok is True


def test_delete_all_removes_every_table() -> None:
    """delete_all_subject_data clears subject rows from all tables while keeping database usable."""
    conn = connect(":memory:")
    apply_schema(conn)
    subject_id = "sub_purge"

    conn.execute(
        "INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc) VALUES (?, ?, ?, ?, ?)",
        (subject_id, "Purge User", "synthetic", "Asia/Singapore", "2026-08-01T00:00:00Z"),
    )
    conn.execute(
        """INSERT INTO episodes (episode_id, subject_id, thread_id, opened_on, state, baseline_nights, baseline_rung)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("ep_purge_01", subject_id, "th_01", "2026-08-10", "CLOSED", 10, "COLD"),
    )
    conn.execute(
        """INSERT INTO nightly_features (subject_id, night_date, rhr_bpm, coverage_minutes, usable, computed_at_utc)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (subject_id, "2026-08-10", 60.0, 480, 1, "2026-08-10T08:00:00Z"),
    )
    conn.commit()

    # Delete all data
    delete_all_subject_data(subject_id, conn=conn)

    # Verify all tables cleared for subject_id
    sub_count = conn.execute(
        "SELECT COUNT(*) FROM subjects WHERE subject_id = ?", (subject_id,)
    ).fetchone()[0]
    ep_count = conn.execute(
        "SELECT COUNT(*) FROM episodes WHERE subject_id = ?", (subject_id,)
    ).fetchone()[0]
    feat_count = conn.execute(
        "SELECT COUNT(*) FROM nightly_features WHERE subject_id = ?", (subject_id,)
    ).fetchone()[0]

    assert sub_count == 0
    assert ep_count == 0
    assert feat_count == 0

    # Verify database remains completely usable
    conn.execute(
        "INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc) VALUES (?, ?, ?, ?, ?)",
        ("sub_new", "New User", "live", "Asia/Singapore", "2026-08-11T00:00:00Z"),
    )
    conn.commit()
    new_count = conn.execute(
        "SELECT COUNT(*) FROM subjects WHERE subject_id = ?", ("sub_new",)
    ).fetchone()[0]
    assert new_count == 1


def test_evaluation_missing_returns_caveat_with_command(tmp_path: Path) -> None:
    """When an evaluation suite result file is missing, get_evaluation_results returns a caveat naming the CLI command."""
    result = get_evaluation_results("adversarial", eval_dir=tmp_path)
    assert isinstance(result, EvaluationResult)
    assert result.suite == "adversarial"
    assert result.sample_size == 0
    assert len(result.caveats) >= 1
    assert "uv run wha eval run adversarial" in result.caveats[0]


def test_delete_all_leaves_nothing_in_any_table_that_can_hold_a_person() -> None:
    """The named-three version of this test hid a delete that deleted nothing.

    `test_delete_all_removes_every_table` seeds 3 of the schema's 27 tables and checks those
    same 3. It therefore passed while `delete_all_subject_data` was missing four tables, two
    of which carry foreign keys back to `subjects` and `episodes`. With one row in
    `subject_profile` present, the final DELETEs raised FOREIGN KEY constraint failed and
    `with conn:` rolled the whole transaction back. Measured on a copy of the real database:
    58,730 heart rate samples before, 58,730 after.

    The two tables missed for longest were `conversation_turns` and `triage_answers`: the
    person's entire chat transcript and their answers to the triage rules.

    This test seeds EVERY table that has a subject_id or an episode_id, discovering them from
    the schema rather than naming them, so a table added tomorrow is covered the day it is
    added and this cannot silently narrow again.
    """
    conn = connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    apply_schema(conn)
    subject_id = "sub_total_purge"
    episode_id = "ep_total_purge"

    def columns(table: str) -> dict[str, tuple[str, int]]:
        return {r[1]: (r[2], r[3]) for r in conn.execute(f"PRAGMA table_info({table})")}

    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    ]
    scoped = [t for t in tables if {"subject_id", "episode_id"} & set(columns(t))]
    assert len(scoped) >= 20, f"only {len(scoped)} scoped tables found, schema may have moved"

    def allowed_values(table: str) -> dict[str, str]:
        """First value of each `col IN ('a','b')` CHECK, so a generic insert is accepted."""
        ddl = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()[0]
        return {
            m.group(1): m.group(2)
            for m in re.finditer(r"CHECK\s*\(\s*(\w+)\s+IN\s*\(\s*'([^']+)'", ddl)
        }

    def value_for(name: str, decl: str, checks: dict[str, str]) -> object:
        if name == "subject_id":
            return subject_id
        if name == "episode_id":
            return episode_id
        if name in checks:
            return checks[name]
        decl = (decl or "TEXT").upper()
        if "INT" in decl:
            return 1
        if "REAL" in decl or "FLOA" in decl or "DOUB" in decl:
            return 1.0
        return "x"

    # Parents first so the foreign keys resolve.
    conn.execute(
        "INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc) "
        "VALUES (?, ?, ?, ?, ?)",
        (subject_id, "Purge", "synthetic", "Asia/Singapore", "2026-08-01T00:00:00Z"),
    )
    conn.execute(
        """INSERT INTO episodes (episode_id, subject_id, thread_id, opened_on, state,
                                 baseline_nights, baseline_rung, step_count, tool_call_count,
                                 depth_used)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (episode_id, subject_id, "th_purge", "2026-08-10", "CLOSED", 10, "COLD", 0, 0, 0),
    )

    seeded = []
    for table in scoped:
        if table in ("subjects", "episodes"):
            continue
        cols = columns(table)
        # Fill every NOT NULL column plus the scoping ones, so the insert is accepted
        # without needing to know the table.
        names = [
            n for n, (_d, notnull) in cols.items() if notnull or n in ("subject_id", "episode_id")
        ]
        if not names:
            names = list(cols)[:1]
        checks = allowed_values(table)
        values = [value_for(n, cols[n][0], checks) for n in names]
        placeholders = ",".join("?" for _ in names)
        conn.execute(
            f"INSERT OR REPLACE INTO {table} ({','.join(names)}) VALUES ({placeholders})", values
        )
        seeded.append(table)
    conn.commit()

    assert len(seeded) >= 18, f"only seeded {len(seeded)} tables: {seeded}"
    for table in ("conversation_turns", "triage_answers", "subject_profile", "episode_traces"):
        assert table in seeded, f"{table} was not seeded, so this test would not catch it"

    delete_all_subject_data(subject_id, conn=conn)

    survivors = {}
    for table in seeded + ["subjects", "episodes"]:
        cols = set(columns(table))
        if "subject_id" in cols:
            n = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE subject_id = ?", (subject_id,)
            ).fetchone()[0]
        else:
            n = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE episode_id = ?", (episode_id,)
            ).fetchone()[0]
        if n:
            survivors[table] = n

    assert not survivors, f"rows survived 'Delete everything': {survivors}"

    # And the database is still usable afterwards, which is the other half of the promise.
    conn.execute(
        "INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc) "
        "VALUES (?, ?, ?, ?, ?)",
        ("sub_after", "After", "synthetic", "Asia/Singapore", "2026-09-05T00:00:00Z"),
    )
    conn.commit()
