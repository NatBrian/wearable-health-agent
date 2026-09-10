"""The phone calls these and parses the JSON. They never raise across the boundary."""

import json

from wha_android import envelope, facade


def test_ok_wraps_a_model_as_json() -> None:
    from wha.models import Answer

    out = json.loads(envelope.ok(Answer(probe_id="p", option_id="yes")))
    assert out == {"probe_id": "p", "option_id": "yes", "free_text": None, "declined": False}


def test_guarded_turns_a_service_error_into_an_envelope() -> None:
    from wha.errors import SourceUnavailable

    @envelope.guarded
    def boom() -> str:
        raise SourceUnavailable("bridge is not reachable")

    out = json.loads(boom())
    assert out["error"]["kind"] == "unavailable"
    assert "bridge" in out["error"]["message"]


def test_guarded_marks_bad_input_as_invalid() -> None:
    @envelope.guarded
    def bad() -> str:
        raise ValueError("no such episode")

    assert json.loads(bad())["error"]["kind"] == "invalid"


def test_guarded_marks_everything_else_internal_and_keeps_the_type() -> None:
    @envelope.guarded
    def crash() -> str:
        raise RuntimeError("unexpected")

    out = json.loads(crash())
    assert out["error"]["kind"] == "internal"
    assert "RuntimeError" in out["error"]["message"]


def test_status_on_an_empty_database_is_a_payload_not_an_error(tmp_db_path, monkeypatch) -> None:
    monkeypatch.setenv("WHA_DB_PATH", str(tmp_db_path))
    from wha.config import get_settings

    get_settings(reload=True)
    out = json.loads(facade.status("me"))
    assert "error" not in out
    assert out["usable_nights"] == 0
    assert out["rung"] == "COLD"
    assert isinstance(out["components"], list)


def test_answer_returns_recorded_and_pending_reads_it_back(seeded_pending_episode) -> None:
    """Round trip through the same functions Telegram uses."""
    episode_id, probe_id = seeded_pending_episode
    out = json.loads(facade.answer(episode_id, probe_id, "yes", None, False))
    assert out == {"status": "recorded"}
