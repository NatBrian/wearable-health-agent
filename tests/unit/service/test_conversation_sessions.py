"""Which conversation belongs on a screen showing one night."""

from datetime import UTC, date, datetime, timedelta

import pytest

from wha.db import connect
from wha.db.migrations import apply_schema


@pytest.fixture
def db():
    conn = connect(":memory:")
    apply_schema(conn)
    conn.execute(
        "INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc) "
        "VALUES ('sim', 'Simulated', 'synthetic', 'Asia/Singapore', '2026-07-01T00:00:00+00:00')"
    )
    conn.commit()
    return conn


def _turn(conn, seq: int, when: datetime, text: str = "hello") -> None:
    conn.execute(
        """INSERT INTO conversation_turns
           (id, subject_id, seq, role, text, created_at_utc)
           VALUES (?, 'sim', ?, 'user', ?, ?)""",
        (f"t{seq}", seq, text, when.isoformat().replace("+00:00", "Z")),
    )
    conn.commit()


def test_a_reply_written_moments_ago_is_never_filed_as_history(db) -> None:
    """The user typed a question, it was answered, and nothing appeared on the screen.

    The night on screen begins after the conversation about it whenever the watch runs
    ahead of the clock, and also in ordinary use late in the evening. Scoping on the night
    boundary alone hid a reply the moment it was written.
    """
    from wha.service.conversation import get_conversation_sessions

    _turn(db, 1, datetime.now(UTC) - timedelta(minutes=2), "why my level is RED?")

    sessions = get_conversation_sessions("sim", since_night=date(2126, 1, 1), conn=db)

    assert sessions, "a conversation from two minutes ago was filed as history"
    assert sessions[0]["turns"][0]["text"] == "why my level is RED?"


def test_a_conversation_from_before_the_night_still_moves_to_the_record(db) -> None:
    """The counterpart: keeping live sessions must not bring back last week's chat."""
    from wha.service.conversation import get_conversation_sessions

    _turn(db, 1, datetime.now(UTC) - timedelta(days=3), "an old question")

    today = datetime.now(UTC).date()
    sessions = get_conversation_sessions("sim", since_night=today, conn=db)

    assert sessions == []


def test_without_a_night_every_conversation_is_returned(db) -> None:
    """The record screen asks for all of them and must get all of them."""
    from wha.service.conversation import get_conversation_sessions

    _turn(db, 1, datetime.now(UTC) - timedelta(days=3), "an old question")
    _turn(db, 2, datetime.now(UTC) - timedelta(minutes=1), "a new question")

    sessions = get_conversation_sessions("sim", conn=db)

    assert len(sessions) == 2


def test_a_conversation_dated_ahead_of_the_clock_is_not_treated_as_live(db) -> None:
    """Under a simulated watch the record runs into the future.

    Without an upper bound on "still in progress", every conversation in a forward
    simulation counted as live and none ever moved to the record.
    """
    from wha.service.conversation import get_conversation_sessions

    ahead = datetime.now(UTC) + timedelta(days=2)
    _turn(db, 1, ahead, "a conversation dated in the future")

    sessions = get_conversation_sessions(
        "sim", since_night=(ahead + timedelta(days=5)).date(), conn=db
    )

    assert sessions == []


def test_only_the_newest_conversation_gets_the_live_exception(db) -> None:
    """An older conversation that happens to fall inside the window is not "in progress".

    With the record dated ahead of the clock, a chat from days earlier in simulated terms
    was the only one recent by the wall clock, so it surfaced under a night it had nothing
    to do with while the newer one was hidden.
    """
    from wha.service.conversation import get_conversation_sessions

    _turn(db, 1, datetime.now(UTC) - timedelta(minutes=5), "recent by the wall clock")
    _turn(db, 2, datetime.now(UTC) + timedelta(days=2), "newer in the record")

    sessions = get_conversation_sessions(
        "sim", since_night=(datetime.now(UTC) + timedelta(days=5)).date(), conn=db
    )

    assert sessions == []
