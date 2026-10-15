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


def test_conversation_requests_enough_output_tokens_for_structured_reply(conn) -> None:
    """The structured answer must have enough output space to finish its JSON object."""
    client = _client(ConverseResponse(reply="I can explain the recorded night."))

    _reply(
        conn,
        client,
        "What did my watch record for resting heart rate last night?",
    )

    assert client.complete.call_args_list[0].kwargs["max_tokens"] == 4096


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


def test_an_ungrounded_claim_is_retained_for_audit_not_presented_as_sourced(conn) -> None:
    """Draelos et al. 2025 measured 5 to 13 percent of unguarded answers as unsafe.

    A claim whose evidence span is not found verbatim in a retrieved passage does not get
    to appear as though it had a source. It moves to the uncited list for storage and audit.
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


def test_a_watch_reading_can_be_cited_to_the_personal_record(conn) -> None:
    """A recorded measurement has a source even though it is not clinical literature."""
    record = (
        "Latest recorded night: 2026-09-25.\n"
        "Resting heart rate: 52 bpm.\n"
        "Baseline centre: 47 bpm.\n"
        "Difference from baseline: +5 bpm.\n"
        "Detection level: RED."
    )
    client = _client(
        ConverseResponse(
            reply="Your heart rate was 52 bpm.",
            grounded_claims=[
                GeneratedClaim(
                    text="Your heart rate was 52 bpm.",
                    evidence_span="Resting heart rate: 52 bpm.",
                )
            ],
        )
    )

    with patch("wha.agent.conversation._passages_for", return_value=[]):
        reply = respond(
            conn,
            "sub_test",
            "What was my heart rate last night?",
            episode_summary=record,
            llm_client=client,
        )

    assert len(reply.citations) == 1
    assert reply.citations[0].source_id == "watch_record_2026-09-25"
    assert reply.citations[0].title == "Your wearable record"
    assert reply.citations[0].uri is None
    assert reply.citations[0].quoted_span == "Resting heart rate: 52 bpm."


def test_uncited_claim_repeated_in_reply_is_removed_but_remains_flagged(conn) -> None:
    """An unsupported sentence must not sit inline with claims that have sources."""
    record = (
        "Latest recorded night: 2026-09-25.\n"
        "Resting heart rate: 52 bpm.\n"
        "Baseline centre: 47 bpm.\n"
        "Difference from baseline: +5 bpm.\n"
        "Detection level: RED."
    )
    uncited = "You need to see a doctor today because your fever keeps coming back."
    client = _client(
        ConverseResponse(
            reply=(
                "Your watch recorded 52 bpm. "
                f"{uncited} Are you having trouble breathing right now?"
            ),
            grounded_claims=[
                GeneratedClaim(
                    text="Your watch recorded 52 bpm.",
                    evidence_span="Resting heart rate: 52 bpm.",
                )
            ],
            uncited_notes=[uncited],
        )
    )

    reply = _reply(
        conn,
        client,
        "What did my watch record for resting heart rate last night?",
        episode_summary=record,
    )

    assert uncited not in reply.text
    assert uncited in reply.uncited
    assert len(reply.citations) == 1


def test_reply_uses_only_grounded_claims_when_uncited_notes_exist(conn) -> None:
    """A paraphrased unsupported claim must not remain beside a valid citation."""
    record = (
        "Latest recorded night: 2026-09-25.\n"
        "Resting heart rate: 52 bpm.\n"
        "Baseline centre: 47 bpm.\n"
        "Difference from baseline: +5 bpm.\n"
        "Detection level: RED."
    )
    unsupported = "You need to see a doctor today because your fever keeps coming back."
    paraphrase = "The returning fever means you need medical care today."
    client = _client(
        ConverseResponse(
            reply=f"Your watch recorded 52 bpm. {paraphrase}",
            grounded_claims=[
                GeneratedClaim(
                    text="Your watch recorded 52 bpm.",
                    evidence_span="Resting heart rate: 52 bpm.",
                )
            ],
            uncited_notes=[unsupported],
        )
    )

    reply = _reply(
        conn,
        client,
        "What did my watch record for resting heart rate last night?",
        episode_summary=record,
    )

    assert reply.text == "Your watch recorded 52 bpm."
    assert paraphrase not in reply.text
    assert unsupported in reply.uncited
    assert len(reply.citations) == 1


def test_structured_follow_up_question_is_not_repeated_inside_reply(conn) -> None:
    client = _client(
        ConverseResponse(
            reply="Drink enough liquids. Does your neck feel stiff? Do you have a stiff neck?",
            question="Do you have a stiff neck along with the fever?",
            uncited_notes=["Drink enough liquids."],
        )
    )

    reply = _reply(conn, client, "I have a fever today. What should I do?")

    assert reply.text.count("?") == 1
    assert reply.text.endswith("Do you have a stiff neck along with the fever?")
    assert "Does your neck feel stiff?" not in reply.text
    assert "Do you have a stiff neck?" not in reply.text
    assert "Drink enough liquids." not in reply.text


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


def test_old_consultations_do_not_enter_the_current_prompt(conn) -> None:
    """Old symptom reports must not be mistaken for the person's current condition."""
    from datetime import timedelta

    from wha.agent.conversation import record_turn
    from wha.clock import now_utc
    from wha.constants import CONVERSATION_SESSION_GAP_HOURS
    from wha.db.iso import to_iso

    record_turn(conn, "sub_test", "user", "old consultation: fever returned")
    old_stamp = to_iso(now_utc() - timedelta(hours=CONVERSATION_SESSION_GAP_HOURS + 1))
    conn.execute(
        "UPDATE conversation_turns SET created_at_utc = ? WHERE subject_id = ?",
        (old_stamp, "sub_test"),
    )
    record_turn(conn, "sub_test", "user", "current consultation: how was my night?")
    client = _client(ConverseResponse(reply="I can check the recorded night."))

    with patch("wha.agent.conversation._passages_for", return_value=[]):
        respond(
            conn,
            "sub_test",
            "current question: what did my watch record?",
            llm_client=client,
        )

    prompt = str(client.complete.call_args_list[0].args[0])
    assert "old consultation: fever returned" not in prompt
    assert "current consultation: how was my night?" in prompt
    assert "current question: what did my watch record?" in prompt


def test_rule_extraction_uses_only_the_current_consultation(conn) -> None:
    """A symptom from an older consultation must not fill today's decision-rule answer."""
    from datetime import timedelta
    from types import SimpleNamespace

    from wha.agent.conversation import extract_rule_items, record_turn
    from wha.clock import now_utc
    from wha.constants import CONVERSATION_SESSION_GAP_HOURS
    from wha.db.iso import to_iso

    record_turn(conn, "sub_test", "user", "old consultation: I fainted")
    old_stamp = to_iso(now_utc() - timedelta(hours=CONVERSATION_SESSION_GAP_HOURS + 1))
    conn.execute(
        "UPDATE conversation_turns SET created_at_utc = ? WHERE subject_id = ?",
        (old_stamp, "sub_test"),
    )
    record_turn(conn, "sub_test", "user", "current consultation: I have chest pain")
    record_turn(conn, "sub_test", "user", "it gets worse when I climb stairs")
    client = MagicMock()
    client.complete.return_value = (RuleExtraction(), LLMUsage())

    extract_rule_items(
        conn,
        "sub_test",
        "it gets worse when I climb stairs",
        rule=object(),
        outstanding=[
            SimpleNamespace(id="mhs_worse_with_exercise", question_intent="worse with exertion")
        ],
        config=SimpleNamespace(unconditional=[]),
        llm_client=client,
    )

    prompt = str(client.complete.call_args.args[0])
    assert "old consultation: I fainted" not in prompt
    assert "current consultation: I have chest pain" in prompt
    assert prompt.count("it gets worse when I climb stairs") == 1


def test_retrieval_uses_focused_terms_and_reuses_current_symptom_for_followups(conn) -> None:
    """A generic follow-up should search the symptom already raised in this consultation."""
    from wha.agent.conversation import record_turn

    fever = _client(ConverseResponse(reply="I will look up the fever information."))
    with patch("wha.agent.conversation._passages_for", return_value=[]) as retrieve:
        respond(
            conn,
            "sub_test",
            "I feel a bit fever today, what should I do?",
            llm_client=fever,
        )
    assert retrieve.call_args.args[0] == "fever"

    record_turn(conn, "sub_test", "user", "I feel a bit fever today")
    follow_up = _client(ConverseResponse(reply="I can help with that."))
    with patch("wha.agent.conversation._passages_for", return_value=[]) as retrieve:
        respond(
            conn,
            "sub_test",
            "Can you recommend what I should do?",
            llm_client=follow_up,
        )
    assert retrieve.call_args.args[0] == "fever"


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


def test_every_turn_lands_in_the_tamper_evident_record(conn) -> None:
    """The Audit page says everything the system does is written down as it happens.

    After the conversation was added it recorded ingest, night scoring and the agent's tool
    calls and nothing else, so the exchange in which someone described chest pain and was
    routed to a doctor left no trace on the one page whose purpose is to be checkable.
    """
    client = _client(
        ConverseResponse(reply="I need to ask you something."),
        RuleExtraction(gates_confirmed=["gate_collapse"]),
    )

    _reply(conn, client, "chest pain and I blacked out", age_years=40)

    rows = conn.execute(
        "SELECT actor, operation, input_json, output_json, safety_event FROM audit_events"
    ).fetchall()
    chat_rows = [r for r in rows if r["operation"] == "chat"]

    assert chat_rows, "the conversation left no entry in the audit chain"
    entry = chat_rows[-1]
    assert entry["actor"] == "human"
    assert "blacked out" in entry["input_json"]
    assert "urgent" in entry["output_json"]
    assert entry["safety_event"] == "red_flag_conversation"


def test_the_audit_chain_stays_verifiable_after_a_conversation(conn) -> None:
    """A new entry type must not break the hash chain the Audit page verifies."""
    from wha.service.audit import verify_hash_chain

    client = _client(ConverseResponse(reply="Noted."))
    _reply(conn, client, "I slept badly", age_years=40)

    intact, bad_event = verify_hash_chain("sub_test", conn=conn)
    assert intact, f"chain broken at {bad_event}"


def test_refusing_to_converse_never_lowers_the_deterministic_floor(conn) -> None:
    """The turn limit must stop the conversing, and nothing else.

    Holding the floor's urgency back is a TRADE: no escalation now, in exchange for the
    validated rule's questions being asked instead. `at_limit` is exactly the case where
    the second half cannot be honoured, because the conversation stops there.

    Measured before the fix: "I have chest pain" on turn twenty-one returned urgency None
    and a message saying we had talked enough. The comment in that branch asserted the
    opposite, which is why nobody looked.
    """
    from wha.agent.conversation import record_turn
    from wha.constants import CONVERSATION_MAX_TURNS

    conn.execute(
        "INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc) "
        "VALUES (?, ?, ?, ?, ?)",
        ("s", "L", "synthetic", "Asia/Singapore", "2026-09-05T00:00:00Z"),
    )
    for i in range(CONVERSATION_MAX_TURNS * 2):
        record_turn(conn, "s", "user" if i % 2 == 0 else "agent", f"filler {i}")
    conn.commit()

    reply = respond(conn, subject_id="s", user_message="I have chest pain")

    assert reply.at_turn_limit is True, "the limit should have been reached"
    assert reply.urgency == "urgent", "the floor was silently lowered by refusing to talk"
    assert "rf_chest_pain" in reply.triggered_flags

    # And the escalation is a real investigation, not just a sentence.
    assert conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == 1


def test_every_path_that_can_escalate_opens_an_investigation(conn) -> None:
    """An escalation that exists only as a message is the defect item 27 exists to remove.

    The episode-opening block was written inline on the main path, below two early
    returns. Measured before the fix: with the model raising LLMUnavailable and the
    message "I am coughing up blood", `respond` returned urgency 'urgent' and the episodes
    table stayed empty. The offline branch is the one that runs when nothing else is
    working, so it is the worst place to lose an investigation.
    """
    from wha.errors import LLMUnavailable

    conn.execute(
        "INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc) "
        "VALUES (?, ?, ?, ?, ?)",
        ("s", "L", "synthetic", "Asia/Singapore", "2026-09-05T00:00:00Z"),
    )
    conn.commit()

    offline = MagicMock()
    offline.complete.side_effect = LLMUnavailable("no model")

    reply = respond(conn, subject_id="s", user_message="I am coughing up blood", llm_client=offline)
    assert reply.refused is True
    assert reply.urgency == "urgent"
    assert conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == 1

    # Saying it again appends to the open investigation rather than opening a second.
    respond(conn, subject_id="s", user_message="I am coughing up blood", llm_client=offline)
    assert conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == 1


def test_an_old_acknowledgement_does_not_clear_a_new_urgency(conn) -> None:
    """Item 32's own "what could go wrong" forbids exactly this silent drop.

    `urgency_state` took MIN(created_at_utc) as when the urgency was set, so an
    acknowledgement was compared against the FIRST time that level was ever reached.
    Raised on day 1, acknowledged on day 2, raised again on day 30: the day-2
    acknowledgement still compared as "after it", so a live red banner was suppressed by a
    fortnight-old click and the page said "You said you have seen somebody about this".
    """
    import time

    from wha.agent.conversation import record_turn, urgency_state
    from wha.audit.monitor import record_urgency_acknowledged

    conn.execute(
        "INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc) "
        "VALUES (?, ?, ?, ?, ?)",
        ("s", "U", "synthetic", "Asia/Singapore", "2026-09-01T00:00:00Z"),
    )
    conn.commit()

    record_turn(conn, "s", "agent", "first escalation", urgency="urgent")
    state = urgency_state(conn, "s")
    assert state["cleared"] is False

    record_urgency_acknowledged(conn, "s", "urgent", state["set_on"])
    assert urgency_state(conn, "s")["cleared"] is True, "acknowledging should clear it"

    # A second escalation, later. This must come back uncleared.
    time.sleep(1.1)
    record_turn(conn, "s", "agent", "a new escalation", urgency="urgent")
    after = urgency_state(conn, "s")

    assert after["urgency"] == "urgent"
    assert after["cleared"] is False, "an old acknowledgement silently cleared a new urgency"
    assert after["set_on"] > state["set_on"], "set_on must track the most recent, not the first"


def test_the_turn_limit_is_per_consultation_not_per_lifetime(conn) -> None:
    """A limit derived from Tu et al. and applied to a lifetime is not that paper's finding.

    The counter was `len(load_transcript(conn, subject_id, limit=1000))`, every row the
    subject had ever produced, with no episode, session or date filter, and nothing
    anywhere resets or deletes conversation_turns. So after twenty stored rows the agent
    stopped conversing permanently: every future message, forever, got "we have been going
    back and forth for 10 exchanges".

    Tu et al. measured ten turns within ONE consultation with one patient.
    """
    import uuid
    from datetime import UTC, datetime, timedelta

    from wha.agent.conversation import _turns_this_session
    from wha.constants import CONVERSATION_MAX_TURNS
    from wha.db.iso import to_iso

    conn.execute(
        "INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc) "
        "VALUES (?, ?, ?, ?, ?)",
        ("s", "S", "synthetic", "Asia/Singapore", "2026-09-01T00:00:00Z"),
    )

    def turn(seq: int, when: datetime) -> None:
        conn.execute(
            """INSERT INTO conversation_turns
                 (id, subject_id, seq, role, text, citations_json, uncited_json,
                  triggered_flags_json, created_at_utc)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (f"t{uuid.uuid4().hex[:8]}", "s", seq, "user", "x", "[]", "[]", "[]", to_iso(when)),
        )

    now = datetime.now(UTC)
    exhausted = CONVERSATION_MAX_TURNS * 2 + 2
    for i in range(exhausted):
        turn(i + 1, now - timedelta(days=1) - timedelta(minutes=exhausted - i))
    conn.commit()

    assert _turns_this_session(conn, "s") == exhausted, "yesterday's session is one session"

    # The next day, the person picks the phone up again. That is a new consultation.
    turn(1000, now - timedelta(minutes=2))
    conn.commit()
    assert _turns_this_session(conn, "s") == 1, (
        "the counter did not reset, so the agent is silenced for the life of the database"
    )

    # The history is NOT deleted, and an escalation from the earlier session still stands.
    assert len(load_transcript(conn, "s", limit=1000)) == exhausted + 1
