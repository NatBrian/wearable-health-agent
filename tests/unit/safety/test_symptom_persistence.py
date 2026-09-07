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
from wha.constants import EPISODE_RECURRENCE_LINK_DAYS, SYMPTOM_FOLLOWUP_MAX_PER_EPISODE
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
    #
    # Names the single module holding the call, not the package: an exemption that names a
    # directory would widen as files are added to it.
    "agent/nodes/ask.py",
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


def test_a_symptom_only_tier_c_spotted_still_reaches_the_timeline(conn):
    """The model's findings must persist, or they count for tonight and nothing after.

    Found by running the live dengue scenario, not by reading code. "I cannot keep any
    water down" is not an exact match for "can't keep fluids down", so the phrase lists
    missed it and Tier C caught it. The escalation was correct and the symptom was then
    forgotten, because only the deterministic matcher wrote to the timeline. That is the
    same silence-over-time defect this module exists to remove, reintroduced one layer up.

    Safe in the one direction that matters: Tier C is additive only and may never clear a
    rule, so recording what it found can raise urgency later and never lower it.
    """
    from unittest.mock import patch

    from wha.safety.models import SafetyCheckResult
    from wha.service.symptoms import observe_and_check, symptom_runs

    # `model_flags` is what the model found in THIS text; `triggered_flags` is everything
    # in play, which includes flags carried from earlier nights. The stub carries a flag
    # in triggered_flags that is NOT in model_flags precisely to pin the difference: only
    # what the model read here may be written onto tonight.
    spotted = SafetyCheckResult(
        escalate=True,
        level="same_day",
        triggered_flags=["rf_fever", "rf_poor_intake"],
        model_flags=["rf_poor_intake"],
        guidance=[],
    )
    start = date(2026, 9, 1)
    with patch("wha.safety.tier_c.check_red_flags_with_tier_c", return_value=spotted):
        result = observe_and_check(conn, "s", "I cannot keep any water down", start)
        assert result.model_flags == ["rf_poor_intake"]

        runs = symptom_runs(conn, "s", start)
        assert [r.flag_id for r in runs] == ["rf_poor_intake"], (
            "Tier C escalated on a symptom the phrase lists missed, and it never reached "
            "the timeline, so it would count for nothing tomorrow"
        )
        assert "rf_fever" not in {r.flag_id for r in runs}, (
            "rf_fever was in play for the escalation but the person never mentioned it "
            "here, so it must not be written onto tonight as a fresh report"
        )

        # And it accumulates, which is the whole point of recording it.
        observe_and_check(conn, "s", "still cannot keep any water down", start + timedelta(days=1))
        observe_and_check(conn, "s", "still cannot keep any water down", start + timedelta(days=2))

    assert symptom_runs(conn, "s", start + timedelta(days=2))[0].nights == 3


# ---------------------------------------------------------------------------
# The follow-up rule could fire without limit inside one night. Found on
# 7 September 2026 by building the demo film timeline, not by any test.
#
# The rule fired ten times in three minutes on the day the person answered
# promptly, consumed the whole conversation depth budget, and closed the
# investigation as UNRESOLVED on its second day. On a real phone that is ten
# notifications, which is precisely the alarm fatigue this project exists to
# reduce, produced by the change that was meant to stop it going silent.
#
# Two things were wrong, both introduced on 7 September:
#
#   1. SYMPTOM_FOLLOWUP_MIN_NIGHTS_APART was declared in constants.py,
#      documented as "at most one follow-up per night, whatever else happens",
#      and read by NOTHING.
#   2. The per-episode cap counts rows in `interactions` with
#      initiation='followup'. Follow-up rows are keyed
#      int_{episode}_{probe}_{night}, so every follow-up on one night upserts
#      into ONE row. The count is pinned at 1 for the whole day and the cap of
#      3 can never be reached from inside a single night.
#
# The unit test above passes `episode_followups_sent=3` directly and is green,
# which is why it never caught this. The gate was right. Its input could not
# reach the value that trips it.
# ---------------------------------------------------------------------------


def test_a_follow_up_does_not_repeat_within_one_night():
    """The guard that constants.py has always described and never had."""
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

    assert select_action(**common).kind.value == "ASK"
    assert select_action(**common, followup_sent_tonight=True).kind.value != "ASK"


def test_the_per_episode_cap_cannot_see_repeats_inside_one_night(tmp_path):
    """Why the per-night guard has to exist, demonstrated against the real table.

    Writing the same night's follow-up twice leaves one row, so the number the
    per-episode cap reads does not move. A cap of three is unreachable by
    repeating within a night, however many times the rule fires.
    """
    from wha.agent.repository import EpisodeRepository
    from wha.db import apply_schema, connect

    conn = connect(tmp_path / "t.sqlite")
    apply_schema(conn)
    conn.execute(
        "INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc) "
        "VALUES ('s', 's', 'synthetic', 'Asia/Singapore', '2026-09-13T00:00:00Z')"
    )
    conn.execute(
        "INSERT INTO episodes (episode_id, subject_id, thread_id, opened_on, state, "
        "baseline_nights, baseline_rung) VALUES ('ep', 's', 'th', '2026-09-13', 'OPEN', 30, "
        "'MATURE')"
    )
    repo = EpisodeRepository(conn)

    night_id = "int_ep_probe_symptoms_2026-09-13"
    for _ in range(10):
        repo.upsert_interaction(
            interaction_id=night_id,
            episode_id="ep",
            subject_id="s",
            probe_id="probe_symptoms",
            question_text="How are you feeling now?",
            initiation="followup",
        )

    counted = conn.execute(
        "SELECT COUNT(*) FROM interactions WHERE episode_id = 'ep' AND probe_id = "
        "'probe_symptoms' AND initiation = 'followup'"
    ).fetchone()[0]
    assert counted == 1, (
        "ten follow-ups in one night are counted as one, so the per-episode cap of "
        f"{SYMPTOM_FOLLOWUP_MAX_PER_EPISODE} cannot bound them"
    )
    conn.close()


def test_the_decide_node_tells_the_policy_whether_it_already_asked_tonight():
    """The same wiring failure, guarded on the call rather than on the behaviour.

    `select_action` grew `followup_sent_tonight` and would happily default it to False
    forever if the one production caller never passed it, which is exactly how
    `symptom_history` went unread for the life of the project and how
    `SYMPTOM_FOLLOWUP_MIN_NIGHTS_APART` sat in constants.py being read by nothing.
    """
    offenders: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        for call in _calls_to(path, {"select_action"}):
            keywords = {kw.arg for kw in call.keywords}
            if "outstanding_symptom" not in keywords:
                continue  # not the caller that can trigger a follow-up
            if "followup_sent_tonight" not in keywords:
                offenders.append(f"{path.relative_to(SRC).as_posix()}:{call.lineno}")

    assert not offenders, (
        "These ask the policy for a decision that can force a symptom follow-up without "
        "saying whether one already went out tonight, so the one-per-night guard cannot "
        "fire: " + ", ".join(offenders)
    )


# ---------------------------------------------------------------------------
# Saying you feel better made the system record MORE symptoms. Found on
# 7 September 2026 by building the demo film, not by any test.
#
# On 15 September the person said "I feel a lot better today, the fever has
# gone". Three rows were written for that night: fever PRESENT, vomiting
# PRESENT and poor intake PRESENT. The message mentions one symptom, to say it
# has stopped, and names neither of the other two.
#
# `observe_and_check` recorded every id in `result.triggered_flags`, and that
# field does not mean "found in this message". `rules.py` deliberately adds the
# co-occurring flags from earlier NIGHTS to it, because they are the flags in
# play for the escalation being explained. So every message re-asserted every
# symptom still inside the window, as of tonight.
#
# Three consequences, in order of how much they matter:
#   1. A symptom could never expire, because speaking at all renewed it.
#   2. Retracting one symptom silently re-asserted the others.
#   3. Run lengths grew without the person reporting anything, and run length
#      is what Tier B persistence escalates on.
#
# The fix is to record what the MODEL found in this text, which is what the
# comment at that call site always said it was doing.
# ---------------------------------------------------------------------------


def test_a_message_only_records_symptoms_that_are_in_it(conn):
    """A report of feeling better must not write three symptoms onto the night."""
    from wha.service.symptoms import observe_and_check, symptom_history

    monday = local_today() - timedelta(days=2)
    tuesday = local_today() - timedelta(days=1)

    record_symptoms(conn, "s", "I have a fever and chills", monday)
    record_symptoms(conn, "s", "I have been vomiting all morning", tuesday)

    before = symptom_history(conn, "s", tuesday)
    observe_and_check(conn, "s", "I feel a lot better today, the fever has gone", local_today())

    rows = conn.execute(
        "SELECT flag_id, present FROM symptom_observations WHERE subject_id = 's' "
        "AND night_date = ? ORDER BY flag_id",
        (local_today().isoformat(),),
    ).fetchall()
    written = {r["flag_id"]: r["present"] for r in rows}

    assert "rf_persistent_vomiting" not in written, (
        "vomiting is not mentioned in that sentence and must not be written onto tonight "
        f"from the history. Tonight was recorded as {written}"
    )
    assert written.get("rf_fever") != 1, (
        f"the sentence says the fever has GONE, so recording it as present is backwards: {written}"
    )
    assert before, "the fixture should have written some history to read back"


# ---------------------------------------------------------------------------
# "The fever has gone" read as a report of fever. Found on 7 September 2026 by
# building the demo film.
#
# `negation_guards` already lists "gone" and "resolved", and the guard only
# looks BACKWARDS from the matched phrase, so it catches "no fever" and misses
# "the fever has gone". Both are ordinary ways to say the same thing.
#
# This failed in the SAFE direction: an undetected retraction leaves the
# symptom on the record and keeps the investigation open. That is why it is
# fixed carefully rather than quickly. The dangerous direction is a FALSE
# retraction, which can close an investigation as benign, and a naive forward
# window creates one immediately:
#
#     "I still have a fever, the vomiting has gone"
#
# Four words forward from "fever" reaches "gone" and would retract the fever
# the person just said they still have. So a resolution word only counts if
# nothing but an auxiliary verb stands between it and the symptom.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("I have a fever", True),
        ("no fever today", False),
        ("the fever has gone", False),
        ("my fever is gone", False),
        ("the fever resolved yesterday", False),
        # The dangerous one. A resolution word belonging to a DIFFERENT symptom
        # must not retract this one.
        ("I still have a fever, the vomiting has gone", True),
        ("fever gone but I am still vomiting", False),
    ],
)
def test_a_resolution_after_the_symptom_is_read_as_a_retraction(text, expected):
    from wha.service.symptoms import detect_symptoms

    found = detect_symptoms(text)
    assert found.get("rf_fever") == expected, (
        f"{text!r} should record fever as {expected}, got {found.get('rf_fever')!r}. "
        f"All flags: {found}"
    )


def test_a_quiet_run_does_not_close_an_episode_waiting_on_a_person(conn):
    """The human checkpoint must not be closed out from under the person.

    Found on 7 September 2026 by building the demo film. The agent drafted its conclusion,
    parked in AWAITING_HUMAN_REVIEW and asked the person to check it. Two green nights
    later the time-based close fired, closed the investigation as LIKELY_BENIGN, and the
    review simply vanished: no decision in the audit trail, and no `closed_unreviewed`
    either, so the record showed a review requested and never resolved.

    `check_close_conditions` guarded only on state == 'CLOSED'. A pending QUESTION was
    already handled, because that is a row in `interactions`; a pending REVIEW is a parked
    graph interrupt and had nothing looking for it.

    This is the second time a background job has walked through this checkpoint. The first
    time it resumed the interrupt with a hardcoded "approve" and the record said a human
    had done it. Nothing is stuck by this: `REVIEW_TIMEOUT_HOURS` still releases the draft,
    and that path records that nobody approved it.
    """
    today = local_today()
    episode_id = open_or_append_episode(conn, "s", today - timedelta(days=4))
    conn.execute(
        "UPDATE episodes SET step_count = 6, state = 'AWAITING_HUMAN_REVIEW' WHERE episode_id = ?",
        (episode_id,),
    )
    for offset in (1, 0):
        conn.execute(
            "INSERT OR REPLACE INTO detections (subject_id, night_date, level, flagged, "
            "residual_bpm, reasons_json) VALUES ('s', ?, 'GREEN', 0, 0.0, '[]')",
            ((today - timedelta(days=offset)).isoformat(),),
        )
    conn.commit()

    assert check_close_conditions(conn, episode_id) is None, (
        "a quiet run closed an investigation that was waiting for a person to review its "
        "conclusion, so the checkpoint was skipped and nothing recorded that it had been"
    )
    state = conn.execute(
        "SELECT state FROM episodes WHERE episode_id = ?", (episode_id,)
    ).fetchone()["state"]
    assert state == "AWAITING_HUMAN_REVIEW"
