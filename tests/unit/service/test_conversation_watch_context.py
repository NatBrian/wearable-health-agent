"""Chat receives only the watch facts that the database actually recorded."""

from wha.agent.conversation import ConversationReply
from wha.db import connect
from wha.db.migrations import apply_schema
from wha.service.conversation import send_message


def test_chat_fills_missing_watch_context_from_the_selected_episode(monkeypatch) -> None:
    """A dashboard message with an episode ID can answer from that episode's night."""
    conn = connect(":memory:")
    apply_schema(conn)
    conn.execute(
        "INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc) "
        "VALUES ('sim', 'Simulated', 'synthetic', 'Asia/Singapore', '2026-09-01T00:00:00Z')"
    )
    conn.execute(
        """INSERT INTO episodes
           (episode_id, subject_id, thread_id, opened_on, state, baseline_nights, baseline_rung)
           VALUES ('ep_1', 'sim', 'thread_1', '2026-09-25', 'OPEN', 20, 'PERSONAL')"""
    )
    conn.execute(
        """INSERT INTO nightly_features
           (subject_id, night_date, rhr_bpm, coverage_minutes, usable, steps_prev_day,
            sleep_hours, rhr_window_source, computed_at_utc)
           VALUES ('sim', '2026-09-25', 52, 420, 1, NULL, NULL, 'clock',
                   '2026-09-26T00:00:00Z')"""
    )
    conn.execute(
        """INSERT INTO nightly_features
           (subject_id, night_date, rhr_bpm, coverage_minutes, usable, steps_prev_day,
            sleep_hours, rhr_window_source, computed_at_utc)
           VALUES ('sim', '2026-09-24', 51, 420, 1, NULL, NULL, 'clock',
                   '2026-09-25T00:00:00Z')"""
    )
    conn.execute(
        """INSERT INTO baselines
           (subject_id, night_date, centre_bpm, scale_bpm, usable_nights, rung, shrink_weight)
           VALUES ('sim', '2026-09-25', 47, 3, 20, 'PERSONAL', 1)"""
    )
    conn.execute(
        """INSERT INTO baselines
           (subject_id, night_date, centre_bpm, scale_bpm, usable_nights, rung, shrink_weight)
           VALUES ('sim', '2026-09-24', 47, 3, 20, 'PERSONAL', 1)"""
    )
    conn.execute(
        """INSERT INTO detections
           (subject_id, night_date, deviation_bpm, explained_bpm, residual_bpm,
            level, flagged, reasons_json)
           VALUES ('sim', '2026-09-25', 5, 0, 5, 'RED', 1, '[]')"""
    )
    conn.execute(
        """INSERT INTO detections
           (subject_id, night_date, deviation_bpm, explained_bpm, residual_bpm,
            level, flagged, reasons_json)
           VALUES ('sim', '2026-09-24', 4, 0, 4, 'RED', 1, '[]')"""
    )
    conn.commit()

    captured: dict[str, object] = {}

    def fake_respond(_conn, **kwargs):
        captured.update(kwargs)
        return ConversationReply(text="Recorded.")

    monkeypatch.setattr("wha.service.conversation.respond", fake_respond)
    send_message(
        "sim",
        "What was my heart rate last night?",
        episode_id="ep_1",
        episode_summary="Latest recorded night: 2026-09-25. Resting heart rate: 999 bpm.",
        conn=conn,
        notify_on_escalation=False,
    )

    summary = str(captured["episode_summary"])
    assert "2026-09-25" in summary
    assert "52 bpm" in summary
    assert "999 bpm" not in summary
    assert "47 bpm" in summary
    assert "5 bpm" in summary
    assert "RED" in summary
    assert "420 minutes" in summary
    assert "clock" in summary
    assert "Sleep: not recorded." in summary
    assert "Previous-day steps: not recorded." in summary
    assert "Immediately preceding night: 2026-09-24." in summary
    assert "Difference from baseline: +4 bpm." in summary
    assert captured["episode_id"] == "ep_1"


def test_chat_uses_latest_recorded_night_when_no_episode_is_selected(monkeypatch) -> None:
    """The chat can still identify the latest stored night when no investigation is open."""
    conn = connect(":memory:")
    apply_schema(conn)
    conn.execute(
        "INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc) "
        "VALUES ('sim', 'Simulated', 'synthetic', 'Asia/Singapore', '2026-09-01T00:00:00Z')"
    )
    conn.execute(
        """INSERT INTO nightly_features
           (subject_id, night_date, rhr_bpm, coverage_minutes, usable, computed_at_utc)
           VALUES ('sim', '2026-09-25', 51, 300, 1, '2026-09-26T00:00:00Z')"""
    )
    conn.commit()

    captured: dict[str, object] = {}

    def fake_respond(_conn, **kwargs):
        captured.update(kwargs)
        return ConversationReply(text="Recorded.")

    monkeypatch.setattr("wha.service.conversation.respond", fake_respond)
    send_message(
        "sim",
        "What was my heart rate?",
        conn=conn,
        notify_on_escalation=False,
    )

    summary = str(captured["episode_summary"])
    assert "2026-09-25" in summary
    assert "51 bpm" in summary
    assert "300 minutes" in summary
