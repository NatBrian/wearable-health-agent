"""The conversation, and the properties that must hold on every turn of it."""

from unittest.mock import MagicMock, patch

import pytest

from wha.agent.conversation import (
    ConversationReply,
    ConverseResponse,
    RuleAnswer,
    RuleExtraction,
    established_urgency,
    load_rule_answers,
    load_transcript,
    respond,
)
from wha.db.connection import connect
from wha.db.migrations import apply_schema
from wha.llm.client import LLMUsage
from wha.retrieve.models import GeneratedClaim


@pytest.fixture
def conn(tmp_path):
    """A database with the conversation tables, and no corpus build."""
    connection = connect(tmp_path / "conv.sqlite")
    apply_schema(connection)
    return connection


def _client(converse: ConverseResponse, extraction: RuleExtraction | None = None) -> MagicMock:
    """A stub for one turn.

    A turn makes two calls: the conversation, then a separate focused extraction pass at
    temperature zero. They are split because asked to converse and extract at once the
    model conversed and returned no answers, leaving the decision rule permanently
    incomplete.
    """
    client = MagicMock()
    client.complete.side_effect = [
        (converse, LLMUsage()),
        (extraction or RuleExtraction(), LLMUsage()),
    ]
    return client


def _reply(conn, client, message: str, **kwargs) -> ConversationReply:
    # The corpus index is a several-second build and is exercised in its own tests. These
    # tests are about the checks around the model, so retrieval is stubbed out.
    with patch("wha.agent.conversation._passages_for", return_value=[]):
        return respond(conn, "sub_test", message, llm_client=client, **kwargs)


def test_chest_pain_asks_before_it_escalates(conn) -> None:
    """The behaviour change this whole redesign exists for.

    A phrase match used to be a verdict: "chest pain" went straight to an ambulance with no
    confirming question. Downie et al. BMJ 2013;347:f7095 found single red flags mostly
    uninformative; the Marburg Heart Score asks five and is validated at sensitivity 87.1
    percent. So the first turn asks, and does not yet declare an urgency.
    """
    client = _client(
        ConverseResponse(
            reply="Thanks for telling me. A few short questions will tell us how urgent this is.",
            asked_item_id="mhs_worse_with_exercise",
            question="Does it get worse when you climb stairs?",
        )
    )

    reply = _reply(conn, client, "I have chest pain", age_years=40)

    assert "rf_chest_pain" in reply.triggered_flags
    assert reply.urgency is None, "escalated on a phrase match without asking anything"
    assert reply.asked_item_id == "mhs_worse_with_exercise"
    assert reply.triage is not None and reply.triage.complete is False


def test_a_confirmed_safety_gate_escalates_immediately_and_computes_no_score(conn) -> None:
    """Marburg's own contraindication is "do not use in an emergency setting"."""
    client = _client(
        ConverseResponse(reply="That needs attention now."),
        RuleExtraction(gates_confirmed=["gate_collapse"]),
    )

    reply = _reply(conn, client, "chest pain and I blacked out", age_years=40)

    assert reply.urgency == "urgent"
    assert reply.triage is not None
    assert reply.triage.gate_triggered == "gate_collapse"
    assert reply.triage.score is None


def test_a_completed_low_score_routes_to_same_day_not_an_ambulance(conn) -> None:
    """The rule decides, and it is allowed to conclude something less than urgent."""
    client = _client(
        ConverseResponse(reply="Thank you, that is everything I need."),
        RuleExtraction(
            rule_answers=[
                RuleAnswer(item_id="mhs_age_sex", answer=False, quote="I am 40"),
                RuleAnswer(item_id="mhs_known_vascular", answer=False, quote="no heart problems"),
                RuleAnswer(item_id="mhs_worse_with_exercise", answer=False, quote="no difference"),
                RuleAnswer(
                    item_id="mhs_reproducible_by_palpation",
                    answer=True,
                    quote="pressing on it hurts the same",
                ),
                RuleAnswer(
                    item_id="mhs_patient_assumes_cardiac", answer=False, quote="feels muscular"
                ),
            ],
        ),
    )

    reply = _reply(conn, client, "chest pain, pressing on it reproduces it exactly", age_years=40)

    assert reply.triage is not None
    assert reply.triage.complete
    assert reply.triage.score == 0
    assert reply.urgency == "same_day"
    assert load_rule_answers(conn, "sub_test", "chest_pain")["mhs_age_sex"] is False


def test_urgency_can_rise_and_can_never_fall(conn) -> None:
    """The property that keeps the floor unreasonable-past.

    Once anything has established urgent, a later turn that scores low cannot walk it back.
    """
    escalating = _client(
        ConverseResponse(reply="Understood."),
        RuleExtraction(gates_confirmed=["gate_cannot_speak"]),
    )
    _reply(conn, escalating, "chest pain and I can't get a full breath", age_years=40)
    assert established_urgency(conn, "sub_test") == "urgent"

    calming = _client(
        ConverseResponse(reply="Noted."),
        RuleExtraction(
            rule_answers=[
                RuleAnswer(item_id="mhs_age_sex", answer=False),
                RuleAnswer(item_id="mhs_known_vascular", answer=False),
                RuleAnswer(item_id="mhs_worse_with_exercise", answer=False),
                RuleAnswer(item_id="mhs_reproducible_by_palpation", answer=True),
                RuleAnswer(item_id="mhs_patient_assumes_cardiac", answer=False),
            ],
        ),
    )
    later = _reply(conn, calming, "actually pressing on it reproduces it", age_years=40)

    assert later.urgency == "urgent", "a later low score walked back an escalation"


def test_a_flag_with_no_validated_rule_still_escalates_on_the_spot(conn) -> None:
    """Narrowing chest pain to a rule must not quietly disarm the rest of the floor."""
    client = _client(ConverseResponse(reply="Understood."))

    reply = _reply(conn, client, "I fainted this morning", age_years=40)

    assert reply.urgency == "urgent"
    assert reply.triggered_flags


def test_an_ungrounded_claim_is_labelled_rather_than_presented_as_sourced(conn) -> None:
    """Draelos et al. 2025 measured 5 to 13 percent of unguarded answers as unsafe.

    A claim whose evidence span is not found verbatim in a retrieved passage does not get
    to appear as though it had a source. It moves to the uncited list, which the interface
    labels.
    """
    client = _client(
        ConverseResponse(
            reply="Here is what I can tell you.",
            grounded_claims=[
                GeneratedClaim(
                    text="A raised overnight heart rate is often an infection.",
                    evidence_span="this span appears in no retrieved passage",
                )
            ],
            uncited_notes=["Drinking fluids is generally sensible."],
        )
    )

    reply = _reply(conn, client, "what does a high heart rate mean", age_years=40)

    assert reply.citations == []
    assert "A raised overnight heart rate is often an infection." in reply.uncited
    assert "Drinking fluids is generally sensible." in reply.uncited


def test_forbidden_phrasings_are_stripped_from_what_the_model_wrote(conn) -> None:
    """red_flags.yaml states it plainly: this system never says "you are fine"."""
    client = _client(ConverseResponse(reply="Good news, you are fine and it's nothing."))

    reply = _reply(conn, client, "am I ok", age_years=40)

    assert "you are fine" not in reply.text.lower()
    assert "it's nothing" not in reply.text.lower()


def test_the_model_being_unavailable_never_reads_as_reassurance(conn) -> None:
    """An outage must not look like a clean bill of health."""
    from wha.errors import LLMUnavailable

    client = MagicMock()
    client.complete.side_effect = LLMUnavailable("provider down")

    reply = _reply(conn, client, "I fainted", age_years=40)

    assert reply.refused
    assert reply.urgency == "urgent", "an outage lost an escalation the rules had found"
    assert "fine" not in reply.text.lower()


def test_the_transcript_outlives_the_call(conn) -> None:
    """A conversation the person can scroll back through, and the agent can resume."""
    client = _client(ConverseResponse(reply="Noted."))
    _reply(conn, client, "hello", age_years=40)

    turns = load_transcript(conn, "sub_test")
    assert [t["role"] for t in turns] == ["user", "agent"]
    assert turns[0]["text"] == "hello"


def test_only_items_belonging_to_the_rule_are_stored(conn) -> None:
    """The model does not get to invent an item and have it scored."""
    client = _client(
        ConverseResponse(reply="Noted."),
        RuleExtraction(
            rule_answers=[
                RuleAnswer(item_id="mhs_age_sex", answer=True),
                RuleAnswer(item_id="not_a_real_item", answer=True),
            ]
        ),
    )

    _reply(conn, client, "I have chest pain", age_years=70)

    stored = load_rule_answers(conn, "sub_test", "chest_pain")
    assert "mhs_age_sex" in stored
    assert "not_a_real_item" not in stored


def test_nobody_is_left_in_limbo_when_the_rule_will_not_complete(conn) -> None:
    """Not knowing how urgent something is must not look like nothing being wrong.

    Measured need, not a hypothetical. In a live run the agent asked the Marburg questions
    correctly and recorded none of the answers, so the rule never completed and a person
    describing chest pain was left with no urgency at all. That is worse than the
    over-escalation this whole redesign replaced. After a bounded number of turns the
    presentation resolves the cautious way and says that is what it is doing.
    """
    from wha.constants import TRIAGE_MAX_TURNS_BEFORE_ESCALATE

    last = None
    for turn in range(TRIAGE_MAX_TURNS_BEFORE_ESCALATE):
        # Every turn: the model asks, and extracts nothing at all.
        client = _client(
            ConverseResponse(reply="Another question.", asked_item_id="mhs_age_sex"),
            RuleExtraction(),
        )
        # The first message opens the presentation; the later ones are vague, which is
        # what real answers look like and is exactly when the presentation used to be
        # forgotten between turns.
        message = "I have chest pain" if turn == 0 else f"it still hurts, message {turn}"
        last = _reply(conn, client, message, age_years=40)

    assert last is not None
    assert last.urgency == "urgent"
    assert "cautious direction" in (last.triage.meaning if last.triage else "")
    assert "not a finding" in (last.triage.meaning if last.triage else "")
