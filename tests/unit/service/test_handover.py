"""The clinician handover: SBAR, a question prompt list, and nothing invented."""

from datetime import UTC, datetime

from wha.db.connection import connect
from wha.db.iso import to_iso
from wha.db.migrations import apply_schema
from wha.service.handover import build_handover


def _seed(tmp_path):
    conn = connect(tmp_path / "h.sqlite")
    apply_schema(conn)
    conn.execute(
        """INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
           VALUES ('me', 'me', 'live', 'Asia/Singapore', ?)""",
        (to_iso(datetime.now(UTC)),),
    )
    for item_id, answer, quote in [
        ("mhs_age_sex", 0, "I am 40"),
        ("mhs_known_vascular", 0, "no heart problems"),
        ("mhs_worse_with_exercise", 0, "stairs make no difference"),
        ("mhs_reproducible_by_palpation", 1, "pressing reproduces it exactly"),
        ("mhs_patient_assumes_cardiac", 0, "feels muscular"),
    ]:
        conn.execute(
            """INSERT INTO triage_answers
                 (subject_id, presentation, item_id, answer, source_text, recorded_at_utc)
               VALUES ('me', 'chest_pain', ?, ?, ?, ?)""",
            (item_id, answer, quote, to_iso(datetime.now(UTC))),
        )
    conn.commit()
    return conn


def test_the_handover_follows_sbar_and_ends_with_questions(tmp_path) -> None:
    """SBAR is the WHO, Joint Commission, AHRQ and IHI recognised handover structure.

    Question prompt lists are added because a 2025 meta-analysis of randomised trials found
    they increase the questions a patient asks without lengthening the consultation.
    """
    conn = _seed(tmp_path)
    text = build_handover("me", conn=conn).as_text()

    for heading in ("SITUATION", "BACKGROUND", "ASSESSMENT", "RECOMMENDATION"):
        assert heading in text
    assert text.index("SITUATION") < text.index("BACKGROUND") < text.index("ASSESSMENT")
    assert text.index("ASSESSMENT") < text.index("RECOMMENDATION")
    assert text.index("RECOMMENDATION") < text.index("QUESTIONS YOU MIGHT ASK")


def test_it_says_what_it_is_not_before_it_says_anything_else(tmp_path) -> None:
    """A clinician must not have to infer the provenance of what they are handed."""
    conn = _seed(tmp_path)
    text = build_handover("me", conn=conn).as_text()

    assert text.index("WHAT THIS IS NOT") < text.index("SITUATION")
    assert "not a medical device" in text
    assert "no ECG" in text


def test_an_inverted_rule_item_is_reported_as_the_question_and_the_answer(tmp_path) -> None:
    """Printing the scored label against the raw answer tells a clinician the opposite.

    The person said pressing DOES reproduce the pain. The line read "Pain not reproducible
    by pressing on the chest wall: yes", which asserts the reverse of what they said, on a
    document written for a clinician. It now prints the question asked, their answer, and
    what it scored.
    """
    conn = _seed(tmp_path)
    text = build_handover("me", conn=conn).as_text()

    assert "Does pressing firmly on the painful spot" in text
    assert "-> yes" in text
    assert "Pain not reproducible by pressing on the chest wall: yes" not in text
    assert "Total 0 of 5" in text
    assert "cut-off is 3" in text


def test_the_rule_carries_its_source_and_its_published_limitation(tmp_path) -> None:
    """A score without its provenance and its contraindication is an assertion."""
    conn = _seed(tmp_path)
    text = build_handover("me", conn=conn).as_text()

    assert "Marburg Heart Score" in text
    assert "CMAJ 2010" in text
    assert "Do not use in an emergency setting" in text


def test_it_names_what_it_cannot_assess(tmp_path) -> None:
    """The limits belong in the document, not in a footnote somewhere else."""
    conn = _seed(tmp_path)
    text = build_handover("me", conn=conn).as_text()

    assert "cannot assess" in text
    assert "escalates rather than assessing" in text
