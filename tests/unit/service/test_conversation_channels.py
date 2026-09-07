"""The conversation has to exist on the phone, not only in the dashboard."""

from unittest.mock import MagicMock, patch

from wha.agent.conversation import ConversationReply
from wha.db.connection import connect
from wha.db.migrations import apply_schema
from wha.models import Citation
from wha.service.conversation import format_for_telegram, send_message


def test_the_uncited_marker_travels_with_the_message() -> None:
    """A phone has no amber panel to put the warning in.

    A sentence the model invented must not arrive looking the same as one with a study
    behind it. Draelos et al. 2025 measured 5 to 13 percent of unguarded frontier-model
    answers to patient questions as outright unsafe.
    """
    reply = ConversationReply(
        text="Your overnight heart rate was higher than usual on two nights.",
        uncited=["Elevated heart rate can follow a poor night's sleep."],
        citations=[
            Citation(
                source_id="confounder_alcohol#c0",
                title="Confounder evidence: Alcohol",
                passage="Per-drink RHR +2.8 bpm",
                retrieval_score=0.4,
            )
        ],
    )

    message = format_for_telegram(reply)

    assert "Not from a cited source" in message
    assert "Elevated heart rate can follow a poor night's sleep." in message
    assert "Confounder evidence: Alcohol" in message


def test_an_urgency_leads_the_message_and_says_the_ai_cannot_lower_it() -> None:
    """On a phone the first line is what gets read on the lock screen."""
    urgent = format_for_telegram(ConversationReply(text="Please read this.", urgency="urgent"))
    same_day = format_for_telegram(ConversationReply(text="Please read this.", urgency="same_day"))

    assert urgent.startswith("THIS NEEDS MEDICAL ATTENTION TODAY.")
    assert same_day.startswith("You should see a doctor today.")
    for message in (urgent, same_day):
        assert "The AI cannot lower it." in message


def test_a_long_reply_is_cut_to_one_message_rather_than_dropped() -> None:
    """Outbound messages are length-bounded, and silence is the worst failure."""
    message = format_for_telegram(ConversationReply(text="x" * 5000), max_chars=200)
    assert len(message) <= 200
    assert message.endswith("...")


def test_an_escalation_reached_in_the_dashboard_still_reaches_the_phone(tmp_path) -> None:
    """Someone who escalates on a laptop and then closes it must not lose the escalation."""
    conn = connect(tmp_path / "c.sqlite")
    apply_schema(conn)

    notifier = MagicMock()
    reply = ConversationReply(text="This needs attention.", urgency="urgent")

    with (
        patch("wha.service.conversation.respond", return_value=reply),
        patch("wha.notify.get_notifier", return_value=notifier),
    ):
        send_message(subject_id="me", text="I fainted", conn=conn)

    assert notifier.send.called
    assert "MEDICAL ATTENTION" in notifier.send.call_args.kwargs["text"]


def test_a_turn_that_changes_nothing_does_not_buzz_the_phone(tmp_path) -> None:
    """The phone is for changes. Every turn pushing a notification is the alarm fatigue
    this project exists to avoid."""
    conn = connect(tmp_path / "c.sqlite")
    apply_schema(conn)

    notifier = MagicMock()
    reply = ConversationReply(text="Thanks, noted.", urgency=None)

    with (
        patch("wha.service.conversation.respond", return_value=reply),
        patch("wha.notify.get_notifier", return_value=notifier),
    ):
        send_message(subject_id="me", text="I slept badly", conn=conn)

    assert not notifier.send.called


def test_a_notifier_failure_never_breaks_the_conversation(tmp_path) -> None:
    """The urgency is already recorded on the turn; the transport is best effort."""
    conn = connect(tmp_path / "c.sqlite")
    apply_schema(conn)

    notifier = MagicMock()
    notifier.send.side_effect = RuntimeError("telegram unreachable")
    reply = ConversationReply(text="This needs attention.", urgency="urgent")

    with (
        patch("wha.service.conversation.respond", return_value=reply),
        patch("wha.notify.get_notifier", return_value=notifier),
    ):
        result = send_message(subject_id="me", text="I fainted", conn=conn)

    assert result.urgency == "urgent"


def test_the_escalation_that_reaches_the_phone_is_written_down(tmp_path) -> None:
    """The most urgent message this system sends was the one it did not record.

    Found on 7 September 2026 while building the demo film. Questions and outcomes each
    write a `notifications` row when they go out. `_push_escalation` sent straight to the
    notifier, so "you should see a doctor today" arrived on somebody's phone leaving no
    trace that it had been delivered: nothing in `notifications`, nothing in the audit
    trail.

    The DECISION was recorded, on the conversation turn, with its urgency and the flags
    behind it. What was missing is the DELIVERY, which is the half a person or a clinician
    would actually want evidenced, because "nobody told me" and "you were told" are
    answered by different rows.

    The record screen says everything this system does is written down as it happens.
    """
    conn = connect(tmp_path / "c.sqlite")
    apply_schema(conn)

    notifier = MagicMock()
    notifier.channel = "telegram"
    reply = ConversationReply(text="You should see a doctor today.", urgency="same_day")

    with (
        patch("wha.service.conversation.respond", return_value=reply),
        patch("wha.notify.get_notifier", return_value=notifier),
    ):
        send_message(subject_id="me", text="I have a fever and I am vomiting", conn=conn)

    assert notifier.send.called, "the escalation never reached the phone"

    rows = conn.execute(
        "SELECT kind, channel, status FROM notifications WHERE subject_id = 'me'"
    ).fetchall()
    assert rows, (
        "an escalation was delivered to the person's phone and nothing recorded that it had been"
    )
    assert rows[0]["kind"] == "ESCALATION"
    assert rows[0]["status"] == "SENT"
