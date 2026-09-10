"""Python decides to notify; the phone delivers. The notifier hands the phone a dict and
never raises, because a delivery failure inside an episode must degrade to "not
delivered", exactly as Telegram does."""

import logging

from wha.models import AnswerOption
from wha.notify import android
from wha.notify.protocol import MessageKind


def test_send_hands_a_flat_dict_to_the_sink() -> None:
    received: list[dict] = []
    notifier = android.AndroidNotifier(sink=lambda payload: received.append(payload) or True)
    ok = notifier.send(
        recipient_id="me",
        kind=MessageKind.QUESTION,
        text="Did you drink alcohol last night?",
        interaction_id="int-1",
        probe_id="alcohol",
        options=[AnswerOption(option_id="yes", label="Yes"), AnswerOption(option_id="no", label="No")],
    )
    assert ok is True
    assert received == [
        {
            "recipient_id": "me",
            "kind": "QUESTION",
            "text": "Did you drink alcohol last night?",
            "interaction_id": "int-1",
            "probe_id": "alcohol",
            "options": [{"option_id": "yes", "label": "Yes"}, {"option_id": "no", "label": "No"}],
            "url": None,
        }
    ]


def test_a_sink_that_raises_is_reported_as_not_delivered(caplog) -> None:
    def broken(payload: dict) -> bool:
        raise RuntimeError("no notification permission")

    notifier = android.AndroidNotifier(sink=broken)
    with caplog.at_level(logging.WARNING):
        ok = notifier.send("me", MessageKind.ESCALATION, "See a clinician today.")
    assert ok is False
    assert "no notification permission" in caplog.text


def test_factory_picks_android_when_configured_and_a_sink_exists() -> None:
    from wha.notify import factory

    android.set_sink(lambda payload: True)
    try:
        assert factory.select_notifier("android", sink=android.get_sink(), telegram_token=None, telegram_chat_id=None).channel == "android"
    finally:
        android.set_sink(None)


def test_factory_falls_back_to_null_when_android_has_no_sink() -> None:
    from wha.notify import factory

    android.set_sink(None)
    assert factory.select_notifier("android", sink=None, telegram_token=None, telegram_chat_id=None).channel == "none"
