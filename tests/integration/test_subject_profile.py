"""Five standing facts, each one reaching the thing that reads it.

Two wires were dead and one rule was running outside its evidence.

**The chest pain rule ran on everybody.** The Marburg Heart Score was built on "1,199
unselected and consecutive patients aged >= 35 years". `triage()` has always taken an
`age_years` to enforce that, and nothing ever filled it in. In a real run somebody typed
"I am 24 and male", the system extracted and stored that, then applied the rule anyway,
scored 3 of 5 on three things common in a young adult with a pulled muscle, said urgent,
and cited a study of people twice their age.

**The cycle answer went nowhere.** `update_belief` takes a `luteal_applicable` and no
caller passed one, so the largest ordinary explanation for a raised night sat at exactly
0.0 through every episode.

**The recovery boost went nowhere either.** `update_belief` reads
`context.has_recent_illness` by name, and that field was not on `EpisodeContext`, so even
a correctly built context failed the `hasattr` check.

Each test here goes from the profile to the decision, because every one of these defects
was invisible to a test of the function in the middle.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from wha.agent.conversation import profile_rule_answers
from wha.agent.repository import EpisodeRepository
from wha.constants import RECOVERY_TAIL_DAYS
from wha.db import connect
from wha.db.iso import to_iso
from wha.db.migrations import apply_schema
from wha.models import SubjectProfilePatch
from wha.safety.triage import load_triage_rules, triage
from wha.service.settings import get_subject_profile, update_subject_profile

SUBJECT = "me"
MARBURG_ITEMS = {
    "mhs_age_sex",
    "mhs_known_vascular",
    "mhs_worse_with_exercise",
    "mhs_reproducible_by_palpation",
    "mhs_patient_assumes_cardiac",
}


def _db(tmp_path: Path) -> Path:
    db_file = tmp_path / "profile.db"
    conn = connect(db_file)
    apply_schema(conn)
    conn.execute(
        """INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
           VALUES (?, 'me', 'synthetic', 'Asia/Singapore', ?)""",
        (SUBJECT, to_iso(datetime(2026, 7, 1, tzinfo=UTC))),
    )
    conn.commit()
    conn.close()
    return db_file


# -- the age gate -------------------------------------------------------------------


def test_the_rule_is_not_applied_to_someone_it_was_never_tested_on() -> None:
    """A 24 year old is routed conservatively rather than scored."""
    config = load_triage_rules()
    # All five items answered the way that scores 3 of 5, which is the run that produced
    # the wrong urgent verdict.
    answers = {
        "mhs_age_sex": False,
        "mhs_known_vascular": False,
        "mhs_worse_with_exercise": True,
        "mhs_reproducible_by_palpation": False,
        "mhs_patient_assumes_cardiac": True,
    }

    young = triage("chest_pain", answers=answers, age_years=24, config=config)
    assert young.score is None, "a 24 year old was scored on a rule built for 35 and over"
    assert young.urgency == "urgent", "withholding the rule must route the cautious way"
    assert "35 and over" in (young.meaning or ""), (
        "the person is told which rule was withheld and why, not left to infer it"
    )

    older = triage("chest_pain", answers=answers, age_years=52, config=config)
    assert older.score == 3, "the rule must still run on somebody it was built on"


def test_an_unknown_age_does_not_silently_apply_the_rule() -> None:
    """Not knowing must never look like the rule being safe to use.

    This is the state every user was in, because nothing filled the field.
    """
    config = load_triage_rules()
    outcome = triage("chest_pain", answers={}, age_years=None, config=config)
    assert outcome.urgency != "low"


# -- the profile answers the two items that never change -----------------------------


def test_the_two_standing_marburg_items_come_from_the_profile() -> None:
    """So nobody is asked them during a conversation about their chest."""
    from wha.models import SubjectProfile

    profile = SubjectProfile(
        subject_id=SUBJECT, age_years=70, sex="female", known_vascular_disease=True
    )
    answers = {a.item_id: a.answer for a in profile_rule_answers(profile, MARBURG_ITEMS)}

    # A woman of 70 is over the 65 threshold the published item names.
    assert answers["mhs_age_sex"] is True
    assert answers["mhs_known_vascular"] is True


def test_the_age_and_sex_item_uses_the_published_thresholds() -> None:
    """Woman 65 or over, or man 55 or over. Not one threshold for everyone."""
    from wha.models import SubjectProfile

    def item(age: int, sex: str) -> bool:
        profile = SubjectProfile(subject_id=SUBJECT, age_years=age, sex=sex)
        return next(
            a.answer
            for a in profile_rule_answers(profile, MARBURG_ITEMS)
            if a.item_id == "mhs_age_sex"
        )

    assert item(60, "female") is False
    assert item(65, "female") is True
    assert item(60, "male") is True
    assert item(54, "male") is False


def test_a_missing_field_produces_no_answer_rather_than_a_false() -> None:
    """A False would be an assertion about somebody's health that nobody made.

    The rule then stays incomplete and resolves the cautious way, which is the design.
    """
    from wha.models import SubjectProfile

    partial = SubjectProfile(subject_id=SUBJECT, age_years=40)  # no sex recorded
    ids = {a.item_id for a in profile_rule_answers(partial, MARBURG_ITEMS)}
    assert "mhs_age_sex" not in ids

    empty = SubjectProfile(subject_id=SUBJECT)
    assert profile_rule_answers(empty, MARBURG_ITEMS) == []


# -- the belief model reads it -------------------------------------------------------


def test_the_cycle_answer_reaches_the_belief_model(tmp_path: Path) -> None:
    """It sat at exactly 0.0 through every episode because nothing passed the flag."""
    db_file = _db(tmp_path)
    conn = connect(db_file)
    repo = EpisodeRepository(conn=conn)

    assert repo.get_profile_menstruates(SUBJECT) is None, "unset must read as unknown"

    update_subject_profile(SubjectProfilePatch(menstruates=True), SUBJECT, conn=conn)
    assert repo.get_profile_menstruates(SUBJECT) is True

    update_subject_profile(SubjectProfilePatch(menstruates=False), SUBJECT, conn=conn)
    assert repo.get_profile_menstruates(SUBJECT) is False, "False must not read as unset"
    conn.close()


def test_a_recent_illness_is_found_inside_the_published_window(tmp_path: Path) -> None:
    """Radin 2021: resting heart rate did not return to baseline for roughly 79 days."""
    db_file = _db(tmp_path)
    conn = connect(db_file)
    repo = EpisodeRepository(conn=conn)
    today = date(2026, 9, 5)

    assert repo.has_recent_illness_episode(SUBJECT, today) is False

    def add(episode_id: str, closed: date, disposition: str) -> None:
        conn.execute(
            """INSERT INTO episodes
                 (episode_id, subject_id, thread_id, opened_on, closed_on, state,
                  disposition, baseline_nights, baseline_rung, step_count,
                  tool_call_count, depth_used)
               VALUES (?, ?, ?, ?, ?, 'CLOSED', ?, 28, 'MATURE', 1, 0, 0)""",
            (episode_id, SUBJECT, episode_id, closed.isoformat(), closed.isoformat(), disposition),
        )
        conn.commit()

    add("ep_old", today - timedelta(days=RECOVERY_TAIL_DAYS + 5), "LIKELY_ILLNESS")
    assert repo.has_recent_illness_episode(SUBJECT, today) is False, "outside the window"

    add("ep_recent", today - timedelta(days=10), "LIKELY_ILLNESS")
    assert repo.has_recent_illness_episode(SUBJECT, today) is True
    conn.close()


def test_a_benign_episode_is_not_a_recent_illness(tmp_path: Path) -> None:
    """The boost is for recovering from an illness, not for having been investigated."""
    db_file = _db(tmp_path)
    conn = connect(db_file)
    conn.execute(
        """INSERT INTO episodes
             (episode_id, subject_id, thread_id, opened_on, closed_on, state, disposition,
              baseline_nights, baseline_rung, step_count, tool_call_count, depth_used)
           VALUES ('ep_b', ?, 'ep_b', '2026-09-01', '2026-09-02', 'CLOSED',
                   'LIKELY_BENIGN', 28, 'MATURE', 1, 0, 0)""",
        (SUBJECT,),
    )
    conn.commit()
    assert (
        EpisodeRepository(conn=conn).has_recent_illness_episode(SUBJECT, date(2026, 9, 5)) is False
    )
    conn.close()


# -- what the profile deliberately does not collect ----------------------------------


def test_the_profile_holds_only_fields_something_reads() -> None:
    """A field nobody reads tells a person their data is being used when it is not.

    Weight, height and BMI are absent on purpose: there is no covariate model, and the
    baseline becomes personal after seven nights so it does not need them.
    """
    from wha.models import SubjectProfile

    fields = set(SubjectProfile.model_fields)
    for absent in ("weight_kg", "height_cm", "bmi", "smoker", "conditions"):
        assert absent not in fields

    assert fields == {
        "subject_id",
        "age_years",
        "sex",
        "known_vascular_disease",
        "menstruates",
        "rate_lowering_medicine",
        "notes_for_doctor",
        "updated_at_utc",
    }


def test_a_partial_update_leaves_the_rest_alone(tmp_path: Path) -> None:
    """Somebody setting their age must not clear what they said about their heart."""
    db_file = _db(tmp_path)
    conn = connect(db_file)

    update_subject_profile(
        SubjectProfilePatch(age_years=41, sex="male", known_vascular_disease=True),
        SUBJECT,
        conn=conn,
    )
    update_subject_profile(SubjectProfilePatch(menstruates=False), SUBJECT, conn=conn)

    profile = get_subject_profile(SUBJECT, conn=conn)
    assert profile.age_years == 41
    assert profile.sex == "male"
    assert profile.known_vascular_disease is True
    assert profile.menstruates is False
    conn.close()


def test_changing_the_profile_is_recorded(tmp_path: Path) -> None:
    """It changes how a rule decides, so it belongs in the record, without the values."""
    db_file = _db(tmp_path)
    conn = connect(db_file)
    update_subject_profile(SubjectProfilePatch(age_years=41), SUBJECT, conn=conn)

    row = conn.execute(
        "SELECT output_json FROM audit_events WHERE operation = 'settings' ORDER BY rowid DESC LIMIT 1"
    ).fetchone()
    assert row is not None, "a change to how the rules decide was not written down"
    assert "age_years" in row["output_json"]
    assert "41" not in row["output_json"], "the value itself does not belong in an exported log"
    conn.close()
