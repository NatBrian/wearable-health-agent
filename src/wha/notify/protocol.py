"""Notifier protocol and message kind definitions."""

from collections.abc import Sequence
from enum import StrEnum
from typing import Protocol, runtime_checkable

from wha.models import AnswerOption


class MessageKind(StrEnum):
    """Closed enumeration of outbound notification message types."""

    QUESTION = "QUESTION"
    MEASUREMENT = "MEASUREMENT"
    ESCALATION = "ESCALATION"
    OUTCOME = "OUTCOME"
    SYSTEM = "SYSTEM"


@runtime_checkable
class Notifier(Protocol):
    """Outbound user notification protocol."""

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
        """Send a structured notification message.

        Returns True on success, False on failure. Never raises.
        """
        ...
