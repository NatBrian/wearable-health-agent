"""What the graph is told when a person answers."""

from wha.db import connect
from wha.db.migrations import apply_schema
from wha.service.scheduler import _resume_value

PENDING = {"kind": "question", "probe_id": "probe_symptoms"}


def _db_with_answer(**row):
    conn = connect(":memory:")
    apply_schema(conn)
    conn.execute(
        """INSERT INTO interactions
           (id, episode_id, probe_id, question_text, text_source, options_json, evsi,
            interruption_cost, rejected_json, channel, asked_at_utc, status,
            answer_option_id, free_text)
           VALUES ('int_1', 'ep_1', 'probe_symptoms', 'Any symptoms?', 'llm', '[]', 0.4,
                   0.015, '[]', 'telegram', '2026-09-06T13:42:58Z', ?, ?, ?)""",
        (row["status"], row.get("option_id"), row.get("free_text")),
    )
    conn.commit()
    return conn


def test_typing_an_answer_is_answering_not_declining() -> None:
    """A reply typed on the phone was delivered to the graph as a refusal to answer.

    The belief did not move, the probe stayed unanswered, and the episode parked again on
    a question that no longer existed. Tapping a button worked; typing did not.
    """
    conn = _db_with_answer(status="ANSWERED", free_text="I feel a bit dizzy")

    value = _resume_value(conn, "ep_1", PENDING)

    assert value == {"probe_id": "probe_symptoms", "free_text": "I feel a bit dizzy"}
    assert "declined" not in value


def test_a_tapped_option_still_carries_the_option() -> None:
    conn = _db_with_answer(status="ANSWERED", option_id="yes")

    value = _resume_value(conn, "ep_1", PENDING)

    assert value["option_id"] == "yes"
    assert "declined" not in value


def test_an_answer_with_neither_words_nor_option_is_a_decline() -> None:
    """The only honest reading of an empty answer."""
    conn = _db_with_answer(status="ANSWERED")

    value = _resume_value(conn, "ep_1", PENDING)

    assert value["declined"] is True


def test_an_explicit_decline_is_still_a_decline() -> None:
    conn = _db_with_answer(status="DECLINED", free_text="not now")

    value = _resume_value(conn, "ep_1", PENDING)

    assert value["declined"] is True


def test_an_unanswered_question_leaves_the_episode_parked() -> None:
    conn = _db_with_answer(status="PENDING")

    assert _resume_value(conn, "ep_1", PENDING) is None
