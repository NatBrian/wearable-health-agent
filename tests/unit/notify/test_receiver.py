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


def test_free_text_with_no_pending_question_is_answered_not_deflected() -> None:
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

    from unittest.mock import patch

    from wha.agent.conversation import ConversationReply

    # Free text with no pending question is now a conversation turn, not a brush-off.
    # It used to answer "Please check your health dashboard for episode status and
    # history", which meant the multi-turn conversation did not exist on the one channel
    # the person actually uses. Opening an episode from a stray message is still refused:
    # that is what this test has always been about.
    reply = ConversationReply(text="Thanks, noted. Did you sleep normally after those?")
    with patch(
        "wha.service.conversation.converse_over_telegram",
        return_value=(reply, "Thanks, noted. Did you sleep normally after those?"),
    ):
        res = receiver.process_update(update)

    assert res["status"] == "conversed"
    assert not mock_db.open_episode.called, "a stray message opened an investigation"
    assert mock_client.post.called
    call_payload = mock_client.post.call_args.kwargs.get("json", {})
    assert "did you sleep normally" in call_payload.get("text", "").lower()


def test_a_typed_answer_is_acknowledged_on_the_phone() -> None:
    """Somebody answered a question about their own health and got silence back.

    Tapping a button answers with "Response recorded". Typing the same thing recorded the
    answer and sent nothing, so the person could not tell whether it had arrived, and the
    dashboard did not show it either.
    """
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_db.get_pending_interaction_for_chat.return_value = {"id": "int_1"}

    receiver = TelegramReceiver(
        token="test_token",
        authorized_chat_id="111222",
        client=mock_client,
        db=mock_db,
    )

    res = receiver.process_update(
        {
            "update_id": 501,
            "message": {"chat": {"id": "111222"}, "text": "I feel a bit dizzy"},
        }
    )

    assert res["status"] == "answered_free_text"
    mock_db.record_interaction_answer.assert_called_once_with(
        "int_1", free_text="I feel a bit dizzy"
    )

    sent = [c for c in mock_client.post.call_args_list if "sendMessage" in str(c)]
    assert sent, "the answer was recorded and nothing was sent back to the phone"
    text = sent[0].kwargs["json"]["text"]
    assert "recorded that as your answer" in text
    # An acknowledgement, not a verdict on what they said.
    assert "dizzy" not in text.lower()


def test_the_acknowledgement_says_nothing_about_their_health() -> None:
    """It confirms receipt. Anything more would be the receiver making a clinical claim."""
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_db.get_pending_interaction_for_chat.return_value = {"id": "int_1"}

    receiver = TelegramReceiver(
        token="t", authorized_chat_id="111222", client=mock_client, db=mock_db
    )
    receiver.process_update(
        {"update_id": 502, "message": {"chat": {"id": "111222"}, "text": "chest pain"}}
    )

    text = mock_client.post.call_args_list[0].kwargs["json"]["text"].lower()
    for claim in ("you are fine", "nothing to worry", "you may be", "likely"):
        assert claim not in text
    assert "contact a clinician" in text
