"""Unit tests for Telegram receiver, long polling, callback queries, and offset persistence."""

import logging
from unittest.mock import MagicMock

from wha.notify import TelegramReceiver


def test_unauthorised_chat_id_dropped(caplog) -> None:
    """Updates from unauthorized chat IDs are dropped and logged without message content."""
    mock_client = MagicMock()
    mock_db = MagicMock()

    receiver = TelegramReceiver(
        token="test_token",
        authorized_chat_id="111222",
        client=mock_client,
        db=mock_db,
    )

    unauthorized_update = {
        "update_id": 101,
        "message": {
            "chat": {"id": 999999},  # Unauthorized
            "text": "Sensitive medical secrets",
        },
    }

    with caplog.at_level(logging.WARNING):
        res = receiver.process_update(unauthorized_update)

    assert res["status"] == "dropped"
    assert res["safety_event"] == "unauthorised_sender"
    # Content of the message was NOT logged
    assert "Sensitive medical secrets" not in caplog.text
    # Offset was advanced so it won't be reprocessed
    assert mock_db.set_telegram_offset.called
    assert mock_db.set_telegram_offset.call_args[0][0] == 102


def test_duplicate_tap_is_noop() -> None:
    """When a button is tapped for an already answered interaction, callback query is acknowledged and no state changes."""
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_db.find_interaction_by_prefix.return_value = {
        "id": "int_12345678",
        "status": "ANSWERED",
    }

    receiver = TelegramReceiver(
        token="test_token",
        authorized_chat_id="111222",
        client=mock_client,
        db=mock_db,
    )

    update = {
        "update_id": 105,
        "callback_query": {
            "id": "cq_01",
            "data": "a:int_1234:opt_none",
            "message": {"chat": {"id": 111222}},
        },
    }

    res = receiver.process_update(update)
    assert res["status"] == "noop_duplicate"
    assert not mock_db.record_interaction_answer.called


def test_not_now_consumes_budget() -> None:
    """When user taps 'Not now', status is set to DECLINED and budget is consumed."""
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_db.find_interaction_by_prefix.return_value = {
        "id": "int_12345678",
        "status": "PENDING",
    }

    receiver = TelegramReceiver(
        token="test_token",
        authorized_chat_id="111222",
        client=mock_client,
        db=mock_db,
    )

    update = {
        "update_id": 106,
        "callback_query": {
            "id": "cq_02",
            "data": "a:int_1234:not_now",
            "message": {"chat": {"id": 111222}},
        },
    }

    res = receiver.process_update(update)
    assert res["status"] == "declined"
    assert res["budget_consumed"] is True
    assert mock_db.record_interaction_declined.called
    assert mock_db.record_interaction_declined.call_args[0][0] == "int_12345678"


def test_offset_persisted() -> None:
    """Offset is stored in database and used upon restart so updates are not reprocessed."""
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_db.get_telegram_offset.return_value = 500

    receiver = TelegramReceiver(
        token="test_token",
        authorized_chat_id="111222",
        client=mock_client,
        db=mock_db,
    )

    assert receiver.get_persisted_offset() == 500

    update = {
        "update_id": 500,
        "message": {
            "chat": {"id": 111222},
            "text": "Hello",
        },
    }
    receiver.process_update(update)
    assert mock_db.set_telegram_offset.called
    assert mock_db.set_telegram_offset.call_args[0][0] == 501


def test_expired_question_tap_changes_nothing() -> None:
    """Tapping a button for an expired interaction acknowledges expiry without altering interaction state."""
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_db.find_interaction_by_prefix.return_value = {
        "id": "int_9999",
        "status": "TIMED_OUT",
    }

    receiver = TelegramReceiver(
        token="test_token",
        authorized_chat_id="111222",
        client=mock_client,
        db=mock_db,
    )

    update = {
        "update_id": 200,
        "callback_query": {
            "id": "cq_expired",
            "data": "a:int_9999:opt1",
            "message": {"chat": {"id": 111222}},
        },
    }

    res = receiver.process_update(update)
    assert res["status"] == "expired"
    assert not mock_db.record_interaction_answer.called


def test_free_text_with_no_pending_question_does_not_open_episode() -> None:
    """Free text received when no question is pending points to the dashboard and does NOT open an episode."""
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_db.get_pending_interaction_for_chat.return_value = None

    receiver = TelegramReceiver(
        token="test_token",
        authorized_chat_id="111222",
        client=mock_client,
        db=mock_db,
    )

    update = {
        "update_id": 300,
        "message": {
            "chat": {"id": 111222},
            "text": "I drank three beers yesterday.",
        },
    }

    res = receiver.process_update(update)
    assert res["status"] == "replied_dashboard_pointer"
    assert res["opened_episode"] is False
    # Verified reply sent with dashboard pointer
    assert mock_client.post.called
    call_payload = mock_client.post.call_args.kwargs.get("json", {})
    assert "dashboard" in call_payload.get("text", "").lower()
