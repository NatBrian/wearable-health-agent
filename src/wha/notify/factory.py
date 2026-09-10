"""Notifier selection.

Nothing in the system constructed a notifier, so even a correct ``send`` call had no
transport behind it. This picks one from configuration and falls back to the no-op
transport whenever the configured channel is not fully available, because a missing
token or an unregistered phone sink must degrade to "not delivered" rather than raise
inside an episode.
"""

import logging
import os
from typing import Any

from wha.config import get_settings
from wha.notify.android import AndroidNotifier, Sink, get_sink
from wha.notify.null import NullNotifier
from wha.notify.protocol import Notifier
from wha.notify.telegram import TelegramNotifier

logger = logging.getLogger(__name__)


def select_notifier(
    channel: str,
    sink: Sink | None,
    telegram_token: Any,
    telegram_chat_id: str | None,
) -> Notifier:
    """Pure selection, so it can be tested without the session-wide factory patch."""
    if channel == "android":
        if sink is None:
            logger.warning("WHA_NOTIFY_CHANNEL is android but the phone registered no sink")
            return NullNotifier()
        return AndroidNotifier(sink)

    if telegram_token is None or not telegram_chat_id:
        return NullNotifier()
    secret = (
        telegram_token.get_secret_value()
        if hasattr(telegram_token, "get_secret_value")
        else str(telegram_token)
    )
    if not secret:
        return NullNotifier()
    return TelegramNotifier(token=secret, chat_id=telegram_chat_id)


def get_notifier() -> Notifier:
    """Return the configured outbound transport, or NullNotifier when unavailable."""
    settings = get_settings()
    channel = os.environ.get("WHA_NOTIFY_CHANNEL", "none")
    return select_notifier(
        channel, get_sink(), settings.telegram_bot_token, settings.telegram_chat_id
    )
