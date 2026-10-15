"""MedlinePlus has to be credited on the phone too, and the amber block has to survive.

Confirmed by sending a real message during the review. The dashboard labels a quoted
passage "MedlinePlus, National Library of Medicine". The same passage arrived on Telegram
as `Sources: Fever`. A topic title credits nobody, and the licence is attribution-only.

The labels lived in `wha/ui/components/citations.py`, and the Telegram path correctly
refuses to import anything under `ui/`, so it had no way to reach them. They now live in
`wha.retrieve.attribution`, which both surfaces can import.

Separately: messages were cut at 900 characters wherever that fell, and in one real message
the cut landed inside the "not from a cited source" block, so the label survived and the
warning it carried did not. That is the one trim this must never make.
"""

from __future__ import annotations

from wha.agent.conversation import ConversationReply
from wha.models import Citation
from wha.retrieve.attribution import MEDLINEPLUS_LABEL, source_label
from wha.service.conversation import format_for_telegram

LIMIT = 900


def _citation(source_id: str, title: str) -> Citation:
    return Citation(source_id=source_id, title=title, passage="x", retrieval_score=0.9)


def _reply(**overrides: object) -> ConversationReply:
    base: dict = {
        "text": "A fever is a temperature above normal.",
        "citations": [],
        "uncited": [],
        "urgency": None,
        "urgency_reason": "",
        "triggered_flags": [],
        "guidance": [],
        "turn_index": 1,
    }
    base.update(overrides)
    return ConversationReply(**base)


def test_medlineplus_is_named_not_just_its_topic_title() -> None:
    """The defect, exactly as it arrived on a real phone."""
    message = format_for_telegram(_reply(citations=[_citation("medlineplus_4744#c0", "Fever")]))

    assert MEDLINEPLUS_LABEL in message
    assert "National Library of Medicine" in message
    assert message.count("Sources: Fever\n") == 0, "the bare topic title is not a credit"


def test_the_attribution_note_travels_with_external_text() -> None:
    """Attribution-only means the credit goes wherever the text goes."""
    external = format_for_telegram(_reply(citations=[_citation("medlineplus_4744#c0", "Fever")]))
    assert "used with attribution" in external

    ours = format_for_telegram(
        _reply(citations=[_citation("escalation_rf_chest_pain#c0", "Chest pain")])
    )
    assert "used with attribution" not in ours, "our own rules are not MedlinePlus"
    assert "this system's safety rules" in ours


def test_a_personal_reading_is_named_as_the_wearable_record() -> None:
    """A stored measurement is attributed to the person's record, not a clinical source."""
    assert source_label("watch_record_2026-09-25") == "your wearable record"


def test_a_long_message_never_cuts_inside_the_uncited_block() -> None:
    """The amber block arrives whole or not at all. It arrived halved once."""
    message = format_for_telegram(
        _reply(
            text="A fever is a temperature above normal. " * 40,
            citations=[_citation("medlineplus_4744#c0", "Fever")],
            uncited=["That is reassuring, and the AI is the one saying so."],
            urgency="same_day",
        )
    )

    assert len(message) <= LIMIT
    assert "Not from a cited source" in message
    assert "That is reassuring, and the AI is the one saying so." in message, (
        "the label survived and the warning it carries did not, which is worse than dropping both"
    )


def test_a_long_message_keeps_the_urgency_and_the_reply() -> None:
    """Trimming must not leave somebody with a banner and no message."""
    message = format_for_telegram(
        _reply(text="A fever is a temperature above normal. " * 40, urgency="urgent")
    )

    assert len(message) <= LIMIT
    assert message.startswith("THIS NEEDS MEDICAL ATTENTION TODAY.")
    assert "A fever is a temperature above normal." in message


def test_the_cut_lands_at_a_sentence_end_not_mid_word() -> None:
    """A message that stops mid-word reads as a delivery failure, not as a limit."""
    message = format_for_telegram(_reply(text="This sentence is complete. " * 60))

    assert len(message) <= LIMIT
    assert message.endswith("."), f"cut mid-sentence: {message[-40:]!r}"
