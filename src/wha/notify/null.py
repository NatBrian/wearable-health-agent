"""NullNotifier implementation for testing and headless environments."""

from collections.abc import Sequence

from wha.models import AnswerOption
from wha.notify.protocol import MessageKind, Notifier


class NullNotifier(Notifier):
    """No-op notifier transport that silently accepts all messages."""

    channel = "none"

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
        """Accept message without external delivery."""
        return True
