"""Tests for the defect SHAPE, not only for today's behaviour.

The bug these exist to prevent was not a logic error. `check_red_flags_deterministic`
accepted a `symptom_history` argument, the persistence rule that reads it was written and
unit tested, `red_flags.yaml` documented it, six symptoms carried a reviewed
`persist_nights` value, and no caller anywhere passed the argument. Every part worked and
the wire between them did not exist, so the persistence half of Tier B never fired once.

A test asserting "four nights of fever escalates" would have passed the whole time,
because the unit test supplied the history dict by hand. So these tests do two things
that one does not:

* drive the REAL path, building the history from stored observations the way production
  does, rather than passing a dict in
* assert on the WIRING, by reading the source, because "this function is called with this
  argument" is the property that was violated and no behavioural test at the unit level
  can see it
"""

import ast
from datetime import date, timedelta
from pathlib import Path

import pytest

from wha.clock import local_today
from wha.constants import EPISODE_RECURRENCE_LINK_DAYS
from wha.db import connect
from wha.db.migrations import apply_schema
from wha.models import BaselineRung, BeliefState, CauseId, Disposition
from wha.policy.select import select_action
from wha.safety.rules import check_red_flags_deterministic, load_red_flags
from wha.service.episode_lifecycle import (
    check_close_conditions,
    close_episode,
    open_or_append_episode,
)
from wha.service.symptoms import cooccurring_tier_b, record_symptoms, symptom_history

SRC = Path(__file__).resolve().parents[3] / "src" / "wha"


@pytest.fixture
def conn(tmp_path):
    connection = connect(tmp_path / "t.sqlite")
    apply_schema(connection)
    connection.execute(
        """INSERT INTO subjects (subject_id, label, timezone, source_kind, created_at_utc)
           VALUES ('s', 's', 'Asia/Singapore', 'synthetic', '2026-08-01T00:00:00Z')"""
    )
    connection.commit()
    return connection


def _floor(connection, night, text):
    """Run the floor exactly as production does: record first, then read the history."""
    record_symptoms(connection, "s", text, night)
    return check_red_flags_deterministic(
        user_text=text,
        symptom_history=symptom_history(connection, "s", night),
        recent_tier_b=cooccurring_tier_b(connection, "s", night),
    )


@pytest.mark.parametrize("rule", load_red_flags().tier_b, ids=lambda r: r.id)
def test_every_persist_nights_rule_can_actually_fire(conn, rule):
    """Each Tier B rule escalates once its own persist_nights is exceeded.

    Parameterised over the FILE rather than over a hand-written list, so a rule added to
    `red_flags.yaml` with a persistence window nobody wired up fails here instead of
    sitting dead for months, which is precisely what happened to all six of these.
    """
    phrase = rule.match[0]
    start = date(2026, 9, 1)

    # Up to and including persist_nights: not yet "beyond" the window, so quiet.
    for offset in range(rule.persist_nights):
        result = _floor(conn, start + timedelta(days=offset), f"I have {phrase}")
        assert not result.escalate, (
            f"{rule.id} escalated after {offset + 1} nights, before its window of "
            f"{rule.persist_nights} was exceeded"
        )

    # One night beyond it: escalates.
    result = _floor(conn, start + timedelta(days=rule.persist_nights), f"I have {phrase}")
    assert result.escalate, (
        f"{rule.id} did not escalate after {rule.persist_nights + 1} nights of "
        f"'{phrase}'. Its persist_nights value is unreachable, which is the exact defect "
        "this file exists to prevent."
    )
    assert result.level == "same_day"
    assert rule.id in result.triggered_flags


def test_a_symptom_the_person_retracts_stops_accumulating(conn):
    """Saying it has gone resets the run. Otherwise a settled symptom escalates later."""
    start = date(2026, 9, 1)
    _floor(conn, start, "I have a fever")
    _floor(conn, start + timedelta(days=1), "I have a fever")
    _floor(conn, start + timedelta(days=2), "no more fever, it has gone")
    for offset in range(3, 7):
        result = _floor(conn, start + timedelta(days=offset), "feeling ok")
        assert not result.escalate


def test_a_quiet_night_does_not_reset_a_run(conn):
    """Not picking up your phone on Tuesday is not recovering on Tuesday."""
    start = date(2026, 9, 1)
    _floor(conn, start, "I have a fever")
    # Nothing said on the 2nd or 3rd.
    result = _floor(conn, start + timedelta(days=3), "still have a fever")
    assert result.escalate, "a gap in reporting silently reset the run"


def test_tier_b_cooccurrence_spans_nights_not_sentences(conn):
    """Fever on Monday and vomiting on Tuesday co-occur in any ordinary reading.

    This was implemented as two or more in the SAME MESSAGE, so an illness whose symptoms
    evolve across nights produced nothing on any night.
    """
    start = date(2026, 9, 1)
    first = _floor(conn, start, "I have a fever")
    assert not first.escalate

    second = _floor(conn, start + timedelta(days=1), "I keep throwing up")
    assert second.escalate, "two Tier B symptoms on consecutive nights did not co-occur"
    assert second.level == "same_day"


def test_symptoms_further_apart_than_the_window_do_not_co_occur(conn):
    """The window has to bound something, or it is not a window."""
    start = date(2026, 9, 1)
    _floor(conn, start, "I have a fever")
    result = _floor(conn, start + timedelta(days=5), "I keep throwing up")
    assert not result.escalate


# --------------------------------------------------------------------------- wiring


def _calls_to(module_path: Path, function_names: set[str]) -> list[ast.Call]:
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
        if name in function_names:
            found.append(node)
    return found


# Call sites that legitimately run the floor without a symptom history, each with the
# reason it is allowed. Anything not listed here must pass the history.
_ALLOWED_HISTORYLESS = {
    # The data safety floor judges robust_z and blood oxygen. It passes no user text at
    # all, so there is no symptom to have a history of.
    "service/nightly.py",
    # The demo harness, which must run unattended and reproducibly against frozen
    # scenarios with no conversation behind them.
    "service/symptom_report.py",
    # The documented fallback inside node_ask, taken only when there is no database
    # connection, and logged when it is.
    "agent/nodes.py",
    # The layer being called, not a caller.
    "safety/tier_c.py",
}


def test_every_free_text_call_site_passes_the_symptom_history():
    """The wire that did not exist for the life of the project.

    A behavioural test cannot catch this: every unit test of the persistence rule passed
    while no production caller supplied the argument, because the tests supplied it
    themselves. The property being asserted is about the CALL, so it is checked on the
    call.
    """
    targets = {"check_red_flags_with_tier_c", "check_red_flags_deterministic"}
    offenders: list[str] = []

    for path in sorted(SRC.rglob("*.py")):
        relative = path.relative_to(SRC).as_posix()
        if relative in _ALLOWED_HISTORYLESS:
            continue
        for call in _calls_to(path, targets):
            keywords = {kw.arg for kw in call.keywords}
            if "user_text" not in keywords:
                continue  # judging data, not words
            if "symptom_history" not in keywords:
                offenders.append(f"{relative}:{call.lineno}")

    assert not offenders, (
        "These call the safety floor on something a person typed without their symptom "
        "history, so Tier B persistence cannot fire there: " + ", ".join(offenders)
    )


# --------------------------------------------------------------------------- silences


def test_green_nights_do_not_close_an_episode_over_an_outstanding_symptom(conn):
    """Green is evidence about the reading, not about the person.

    In dengue the critical phase begins at defervescence; Faget's sign puts relative
    bradycardia in several infections; and resting heart rate takes weeks to months to
    return to baseline after one. A settled reading cannot mean recovered.
    """
    today = local_today()
    opened = today - timedelta(days=3)
    episode_id = open_or_append_episode(conn, "s", opened)
    conn.execute("UPDATE episodes SET step_count = 5 WHERE episode_id = ?", (episode_id,))
    for offset in (1, 2):
        conn.execute(
            """INSERT INTO detections (subject_id, night_date, level, flagged, reasons_json)
               VALUES ('s', ?, 'GREEN', 0, '[]')""",
            ((opened + timedelta(days=offset)).isoformat(),),
        )
    conn.commit()

    record_symptoms(conn, "s", "I feel dizzy", today - timedelta(days=1))
    assert check_close_conditions(conn, episode_id) is None, (
        "closed an investigation as benign while the person had an outstanding symptom"
    )

    record_symptoms(conn, "s", "no more dizziness, it has gone", today)
    assert check_close_conditions(conn, episode_id) == Disposition.LIKELY_BENIGN.value


def test_an_outstanding_symptom_is_asked_about_even_when_asking_is_worth_nothing():
    """EVSI cannot see somebody getting worse, so a rule has to.

    With infection at 0.92 every probe scores zero: the cause is settled and no answer
    moves the belief. That is the arithmetic working as designed and it is the wrong
    arithmetic for "are you worse than yesterday".
    """
    belief = BeliefState(
        marginals={c: (0.92 if c == CauseId.INFECTION else 0.02) for c in CauseId},
        p_illness=0.92,
    )
    common = {
        "belief": belief,
        "rung": BaselineRung.MATURE,
        "already_asked_probe_ids": ["probe_symptoms"],
    }

    assert select_action(**common).kind.value != "ASK"

    asked = select_action(**common, outstanding_symptom="sx_dizziness")
    assert asked.kind.value == "ASK"
    assert asked.followup_for == "sx_dizziness"


def test_the_follow_up_is_bounded_on_every_side():
    """A rule that overrides the arithmetic must not become a nightly alarm."""
    belief = BeliefState(
        marginals={c: (0.92 if c == CauseId.INFECTION else 0.02) for c in CauseId},
        p_illness=0.92,
    )
    common = {
        "belief": belief,
        "rung": BaselineRung.MATURE,
        "already_asked_probe_ids": ["probe_symptoms"],
        "outstanding_symptom": "sx_dizziness",
    }

    assert select_action(**common, episode_followups_sent=3).kind.value != "ASK"
    assert select_action(**common, has_pending_interaction=True).kind.value != "ASK"

    # And NOT bounded by these, deliberately. A budget exists to stop the system pestering
    # a well person; letting it silence somebody who has said they feel unwell inverts it.
    survives = select_action(
        belief=belief,
        rung=BaselineRung.PRIOR_DOMINATED,
        already_asked_probe_ids=["probe_symptoms"],
        outstanding_symptom="sx_dizziness",
        weekly_interruptions_used=99,
    )
    assert survives.kind.value == "ASK"


@pytest.mark.parametrize(
    ("gap_days", "should_link"),
    [(1, True), (2, True), (6, True), (7, False), (14, False)],
)
def test_a_recurrence_inside_the_window_is_linked(conn, gap_days, should_link):
    """Seven symptom-free days separates two illnesses; less than that is one illness.

    The 1 and 2 day cases are the saddleback dengue gap, where the second fever peak is
    the dangerous one. Scoring that as an unrelated new event is the failure this guards.
    """
    first_night = date(2026, 9, 1)
    first = open_or_append_episode(conn, "s", first_night)
    closed_on = first_night + timedelta(days=2)
    close_episode(conn, first, Disposition.LIKELY_BENIGN, closed_on)

    second = open_or_append_episode(conn, "s", closed_on + timedelta(days=gap_days))
    row = conn.execute(
        "SELECT preceded_by_episode_id, days_since_previous FROM episodes WHERE episode_id = ?",
        (second,),
    ).fetchone()

    if should_link:
        assert row["preceded_by_episode_id"] == first
        assert row["days_since_previous"] == gap_days
        assert gap_days < EPISODE_RECURRENCE_LINK_DAYS
    else:
        assert row["preceded_by_episode_id"] is None
