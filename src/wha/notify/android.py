"""The phone as a notification transport.

Python decides when and what to send, exactly as for Telegram. This class hands the message
to a sink the Kotlin side registers at start-up and reports whether delivery succeeded. It
never raises: a delivery failure inside an episode must degrade to "not delivered".
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from typing import Any

from wha.models import AnswerOption
from wha.notify.protocol import MessageKind, Notifier

logger = logging.getLogger(__name__)

Sink = Callable[[dict[str, Any]], bool]

_SINK: Sink | None = None


def set_sink(sink: Sink | None) -> None:
    """Register the phone's delivery function, or clear it."""
    global _SINK
    _SINK = sink


def get_sink() -> Sink | None:
    return _SINK


class AndroidNotifier(Notifier):
    """Delivers through a sink the host process supplied."""

    channel = "android"

    def __init__(self, sink: Sink) -> None:
        self._sink = sink

    def send(
        self,
        recipient_id: str,
        kind: MessageKind,
        text: str,
        interaction_id: str | None = None,
        probe_id: str | None = None,
        options: Sequence[AnswerOption] = (),
        url: str | None = None,
    ) -> bool:
        payload: dict[str, Any] = {
            "recipient_id": recipient_id,
            "kind": str(kind),
            "text": text,
            "interaction_id": interaction_id,
            "probe_id": probe_id,
            "options": [{"option_id": o.option_id, "label": o.label} for o in options],
            "url": url,
        }
        try:
            return bool(self._sink(payload))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Android notification not delivered: %s", exc)
            return False
