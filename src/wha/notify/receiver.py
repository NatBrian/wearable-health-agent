"""Telegram receive long-poll transport, callback query processing, and offset persistence."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class TelegramReceiver:
    """Long-polling Telegram update receiver with authorization guard and idempotent handling."""

    def __init__(
        self,
        token: str,
        authorized_chat_id: str | None = None,
        base_url: str = "https://api.telegram.org",
        client: httpx.Client | None = None,
        db: Any = None,
    ) -> None:
        self.token = token
        self.authorized_chat_id = authorized_chat_id
        self.base_url = f"{base_url.rstrip('/')}/bot{token}"
        self._client = client
        self.db = db
        self._memory_offset: int = 0

    def get_persisted_offset(self) -> int:
        """Retrieve last acknowledged update offset from database or memory."""
        if self.db is not None and hasattr(self.db, "get_telegram_offset"):
            return self.db.get_telegram_offset()
        return self._memory_offset

    def save_offset(self, update_id: int) -> None:
        """Persist next expected update offset."""
        self._memory_offset = update_id
        if self.db is not None and hasattr(self.db, "set_telegram_offset"):
            self.db.set_telegram_offset(update_id)

    def _answer_callback_query(self, callback_query_id: str, text: str) -> None:
        """Send answerCallbackQuery response to dismiss button loading spinner in Telegram."""
        endpoint = f"{self.base_url}/answerCallbackQuery"
        payload = {
            "callback_query_id": callback_query_id,
            "text": text,
        }
        try:
            if self._client is not None:
                self._client.post(endpoint, json=payload, timeout=5.0)
            else:
                with httpx.Client(timeout=5.0) as client:
                    client.post(endpoint, json=payload)
        except (httpx.HTTPError, OSError) as exc:
            logger.warning("Failed to answer callback query %s: %s", callback_query_id, exc)

    def _send_reply(self, chat_id: str | int, text: str) -> None:
        """Send simple text reply message."""
        endpoint = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
        }
        try:
            if self._client is not None:
                self._client.post(endpoint, json=payload, timeout=5.0)
            else:
                with httpx.Client(timeout=5.0) as client:
                    client.post(endpoint, json=payload)
        except (httpx.HTTPError, OSError) as exc:
            logger.warning("Failed to send reply message to %s: %s", chat_id, exc)

    def _converse(self, chat_id: str | int | None, text: str, up_id: int) -> dict[str, Any]:
        """Run one conversational turn and send the reply back to the phone.

        Never raises into the polling loop. A conversation failing must not stop the
        receiver, and it must not leave the person with silence, so a failure still sends
        something that says what happened rather than nothing.
        """
        from wha.service.conversation import converse_over_telegram

        if not text.strip():
            self.save_offset(up_id + 1)
            return {"status": "ignored_empty"}

        try:
            reply, message = converse_over_telegram(text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Conversation turn failed for update %d: %s", up_id, exc)
            if chat_id is not None:
                self._send_reply(
                    chat_id,
                    "Something went wrong answering that, so I have not answered it. "
                    "Nothing here is a judgement about how you are. If this is urgent, "
                    "contact a doctor or emergency services rather than waiting for me.",
                )
            self.save_offset(up_id + 1)
            return {"status": "conversation_failed"}

        if chat_id is not None:
            self._send_reply(chat_id, message)
        self.save_offset(up_id + 1)
        return {
            "status": "conversed",
            "urgency": reply.urgency,
            "asked_item_id": reply.asked_item_id,
        }

    def process_update(self, update: dict[str, Any]) -> dict[str, Any]:
        """Process a single Telegram update with identity checks and transaction idempotency."""
        up_id = update.get("update_id", 0)

        # 1. Sender identity verification
        chat_id: str | int | None = None
        if "message" in update and "chat" in update["message"]:
            chat_id = update["message"]["chat"].get("id")
        elif "callback_query" in update:
            cq = update["callback_query"]
            if "message" in cq and "chat" in cq["message"]:
                chat_id = cq["message"]["chat"].get("id")
            elif "from" in cq:
                chat_id = cq["from"].get("id")

        if (
            self.authorized_chat_id is not None
            and chat_id is not None
            and str(chat_id) != str(self.authorized_chat_id)
        ):
            # Dropped update: log event without message content
            logger.warning(
                "Dropped update %d from unauthorised sender chat_id=%s (safety_event='unauthorised_sender')",
                up_id,
                chat_id,
            )
            self.save_offset(up_id + 1)
            return {
                "status": "dropped",
                "reason": "unauthorised_sender",
                "safety_event": "unauthorised_sender",
            }

        # 2. Callback query handling (inline buttons)
        if "callback_query" in update:
            cq = update["callback_query"]
            cb_id = cq.get("id", "")
            raw_data = cq.get("data", "")
            # Format: a:<short_id>:<option_id>
            parts = raw_data.split(":")
            if len(parts) >= 3 and parts[0] == "a":
                short_id = parts[1]
                option_id = ":".join(parts[2:])
            else:
                short_id = "unknown"
                option_id = raw_data

            interaction = None
            if self.db is not None and hasattr(self.db, "find_interaction_by_prefix"):
                interaction = self.db.find_interaction_by_prefix(short_id)

            if interaction is None and self.db is not None:
                # If no interaction found or expired
                self._answer_callback_query(cb_id, "This question has expired.")
                self.save_offset(up_id + 1)
                return {"status": "expired"}

            if interaction is not None:
                status = (
                    interaction.get("status")
                    if isinstance(interaction, dict)
                    else getattr(interaction, "status", None)
                )
                if status in ("ANSWERED", "DECLINED"):
                    # Duplicate tap is a no-op
                    self._answer_callback_query(cb_id, "Response already recorded.")
                    self.save_offset(up_id + 1)
                    return {"status": "noop_duplicate"}

                if status == "TIMED_OUT":
                    self._answer_callback_query(cb_id, "This question has expired.")
                    self.save_offset(up_id + 1)
                    return {"status": "expired"}

                int_id = (
                    interaction.get("id")
                    if isinstance(interaction, dict)
                    else getattr(interaction, "id", short_id)
                )

                if option_id == "not_now":
                    # 'Not now' records declined but interruption budget is still consumed
                    if hasattr(self.db, "record_interaction_declined"):
                        self.db.record_interaction_declined(int_id)
                    self._answer_callback_query(cb_id, "Postponed.")
                    self.save_offset(up_id + 1)
                    return {"status": "declined", "budget_consumed": True}
                else:
                    if hasattr(self.db, "record_interaction_answer"):
                        self.db.record_interaction_answer(int_id, option_id=option_id)
                    self._answer_callback_query(cb_id, "Response recorded.")
                    self.save_offset(up_id + 1)
                    return {"status": "answered", "option_id": option_id}

            self._answer_callback_query(cb_id, "Response recorded.")
            self.save_offset(up_id + 1)
            return {"status": "acknowledged"}

        # 3. Message handling (free text)
        if "message" in update:
            msg = update["message"]
            text = msg.get("text", "")

            pending_int = None
            if self.db is not None and hasattr(self.db, "get_pending_interaction_for_chat"):
                pending_int = self.db.get_pending_interaction_for_chat(chat_id)

            if pending_int is not None:
                int_id = (
                    pending_int.get("id")
                    if isinstance(pending_int, dict)
                    else getattr(pending_int, "id", "")
                )
                if hasattr(self.db, "record_interaction_answer"):
                    self.db.record_interaction_answer(int_id, free_text=text)

                # Say that it arrived. Tapping a button answers with "Response recorded";
                # typing the same thing said nothing at all, so somebody who answered a
                # question about their own health got silence back and could not tell
                # whether the message had been received. It is an acknowledgement and not
                # a reply: nothing here is a judgement about what they said.
                if chat_id is not None:
                    self._send_reply(
                        chat_id,
                        "Thanks, I have recorded that as your answer. I am working through "
                        "it now and will only message again if there is something worth "
                        "telling you. If you feel unwell, contact a clinician rather than "
                        "waiting for me.",
                    )
                self.save_offset(up_id + 1)
                return {"status": "answered_free_text"}
            else:
                # Free text with no pending question is a conversation, not a stray input.
                # This used to reply "Please check your health dashboard for episode status
                # and history", which is a brush-off. The phone is where the person is, and
                # answering only in the dashboard means the multi-turn conversation does
                # not exist on the one channel they actually use.
                #
                # The same engine handles it as the dashboard, so there is one transcript,
                # one safety floor and one set of citations however they reach it.
                return self._converse(chat_id, text, up_id)

        self.save_offset(up_id + 1)
        return {"status": "processed"}

    def poll_once(self) -> list[dict[str, Any]]:
        """Perform a single long-polling getUpdates cycle."""
        offset = self.get_persisted_offset()
        endpoint = f"{self.base_url}/getUpdates"
        params = {"offset": offset, "timeout": 30}

        try:
            if self._client is not None:
                resp = self._client.get(endpoint, params=params, timeout=35.0)
            else:
                with httpx.Client(timeout=35.0) as client:
                    resp = client.get(endpoint, params=params)

            if resp.status_code != 200:
                logger.warning("getUpdates returned HTTP %d: %s", resp.status_code, resp.text)
                return []

            data = resp.json()
            updates = data.get("result", [])
            results = []
            for upd in updates:
                res = self.process_update(upd)
                results.append(res)
            return results
        except (httpx.HTTPError, OSError) as exc:
            logger.warning("Telegram getUpdates polling network error: %s", exc)
            return []
