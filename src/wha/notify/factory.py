"""Notifier selection.

Nothing in the system constructed a notifier, so even a correct ``send`` call had no
transport behind it. This picks one from configuration and falls back to the no-op
transport whenever Telegram is not fully configured, because a missing token must
degrade to "not delivered" rather than raise inside an episode.
"""

from wha.config import get_settings
from wha.notify.null import NullNotifier
from wha.notify.protocol import Notifier
from wha.notify.telegram import TelegramNotifier


def get_notifier() -> Notifier:
    """Return the configured outbound transport, or NullNotifier when unavailable."""
    settings = get_settings()

    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id
    if token is None or not chat_id:
        return NullNotifier()

    secret = token.get_secret_value() if hasattr(token, "get_secret_value") else str(token)
    if not secret:
        return NullNotifier()

    return TelegramNotifier(token=secret, chat_id=chat_id)
