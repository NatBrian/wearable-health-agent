"""Telegram notification transport over HTTPX, callback_data packing, and error containment."""

import hashlib
import logging
from collections.abc import Sequence
from typing import Any

import httpx

from wha.constants import TELEGRAM_CALLBACK_MAX_BYTES
from wha.models import AnswerOption
from wha.notify.protocol import MessageKind, Notifier
from wha.safety.outbound import OutboundMessage, validate_outbound

logger = logging.getLogger(__name__)


def format_callback_token(interaction_id: str) -> str:
    """Stable short token identifying an interaction inside a 64-byte callback payload."""
    return hashlib.sha256(interaction_id.encode("utf-8")).hexdigest()[:12]


def format_callback_data(interaction_id: str, option_id: str) -> str:
    """Format compact callback_data conforming to 64-byte limit: a:<interaction_id[:8]>:<option_id>."""
    # A stable hash of the whole id, not its first eight characters. Interaction ids are
    # built as f"int_{episode_id}_{probe_id}", so for any episode id beginning "ep_2" the
    # first eight characters are the constant "int_ep_2" for every interaction, and the
    # receiver's prefix lookup would attribute an answer to an arbitrary question.
    short_id = format_callback_token(interaction_id)
    data = f"a:{short_id}:{option_id}"
    data_bytes = len(data.encode("utf-8"))
    if data_bytes > TELEGRAM_CALLBACK_MAX_BYTES:
        raise ValueError(
            f"callback_data '{data}' exceeds {TELEGRAM_CALLBACK_MAX_BYTES} bytes limit ({data_bytes} bytes)"
        )
    return data


class TelegramNotifier(Notifier):
    """Telegram bot notification transport using raw httpx."""

    channel = "telegram"

    def __init__(
        self,
        token: str,
        chat_id: str | None = None,
        base_url: str = "https://api.telegram.org",
        client: httpx.Client | None = None,
    ) -> None:
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"{base_url.rstrip('/')}/bot{token}"
        self._client = client

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
        """Validate outbound payload and send via Telegram Bot API sendMessage."""
        chat_target = self.chat_id or recipient_id
        effective_int_id = interaction_id or "generic"

        # Build callback data for validation
        cb_list: list[str] = []
        for opt in options:
            cb_list.append(format_callback_data(effective_int_id, opt.option_id))

        if kind == MessageKind.QUESTION:
            # Also append "Not now" button
            cb_list.append(format_callback_data(effective_int_id, "not_now"))

        option_labels = [opt.label for opt in options] if options else None

        out_msg = OutboundMessage(
            kind=kind.value,
            text=text,
            probe_id=probe_id,
            option_labels=option_labels,
            callback_data_list=cb_list if cb_list else None,
            dashboard_url=url if kind == MessageKind.OUTCOME else None,
        )

        validation = validate_outbound(out_msg)
        if not validation.valid:
            logger.warning("Outbound message validation rejected: %s", validation.violation_reason)
            return False

        final_text = validation.text_to_send

        # Build inline keyboard buttons
        reply_markup: dict[str, Any] | None = None
        keyboard_rows: list[list[dict[str, str]]] = []

        if kind == MessageKind.QUESTION:
            for opt in options:
                keyboard_rows.append(
                    [
                        {
                            "text": opt.label,
                            "callback_data": format_callback_data(effective_int_id, opt.option_id),
                        }
                    ]
                )
            keyboard_rows.append(
                [
                    {
                        "text": "Not now",
                        "callback_data": format_callback_data(effective_int_id, "not_now"),
                    }
                ]
            )
        elif kind == MessageKind.MEASUREMENT:
            keyboard_rows.append(
                [
                    {
                        "text": "Done",
                        "callback_data": format_callback_data(effective_int_id, "done"),
                    },
                    {
                        "text": "Can't right now",
                        "callback_data": format_callback_data(effective_int_id, "cant_now"),
                    },
                ]
            )
        elif kind == MessageKind.OUTCOME and url:
            keyboard_rows.append(
                [
                    {
                        "text": "View detail",
                        "url": url,
                    }
                ]
            )

        if keyboard_rows:
            reply_markup = {"inline_keyboard": keyboard_rows}

        payload: dict[str, Any] = {
            "chat_id": chat_target,
            "text": final_text,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup

        endpoint = f"{self.base_url}/sendMessage"
        try:
            if self._client is not None:
                resp = self._client.post(endpoint, json=payload, timeout=10.0)
            else:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(endpoint, json=payload)

            if resp.status_code >= 400:
                logger.error(
                    "Telegram send failed with status %d: %s",
                    resp.status_code,
                    resp.text,
                )
                return False
            return True
        except (httpx.HTTPError, OSError) as exc:
            # Failure NEVER raises into episode execution
            logger.error("Telegram send network exception: %s", exc)
            return False
