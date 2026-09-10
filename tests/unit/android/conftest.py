"""Fixtures for the phone facade tests: an empty database and one episode awaiting an answer."""

import json

import pytest

from wha.db import connect
from wha.db.migrations import apply_schema


@pytest.fixture
def seeded_pending_episode(tmp_db_path, monkeypatch):
    """An episode in AWAITING_USER with one PENDING question, on a throwaway database.

    Seeded with raw SQL like tests/unit/service/test_episodes.py, so the test reaches
    the facade through the same rows the agent writes.
    """
    monkeypatch.setenv("WHA_DB_PATH", str(tmp_db_path))
    from wha.config import get_settings

    get_settings(reload=True)
    conn = connect(tmp_db_path)
    apply_schema(conn)
    sub_id, ep_id, int_id = "sub_facade", "ep_facade_01", "int_facade_q1"
    conn.execute(
        "INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc) VALUES (?, ?, ?, ?, ?)",
        (sub_id, "Facade Test", "synthetic", "Asia/Singapore", "2026-08-01T00:00:00Z"),
    )
    conn.execute(
        """INSERT INTO episodes (episode_id, subject_id, thread_id, opened_on, state, disposition, baseline_nights, baseline_rung)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (ep_id, sub_id, "thread_facade", "2026-08-15", "AWAITING_USER", None, 14, "PERSONAL"),
    )
    conn.execute(
        """INSERT INTO interactions (id, episode_id, probe_id, question_text, text_source, options_json, evsi, interruption_cost, rejected_json, channel, asked_at_utc, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            int_id,
            ep_id,
            "probe_alcohol",
            "Did you consume alcohol yesterday?",
            "llm",
            json.dumps([{"option_id": "yes", "label": "Yes"}, {"option_id": "no", "label": "No"}]),
            0.45,
            0.10,
            json.dumps([]),
            "android",
            "2026-08-15T08:00:00Z",
            "PENDING",
        ),
    )
    conn.commit()
    conn.close()
    return ep_id, "probe_alcohol"
