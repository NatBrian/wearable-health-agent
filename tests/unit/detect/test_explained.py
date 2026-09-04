"""Unit tests for explained-variance subtraction."""

from datetime import date

from wha.constants import EXERCISE_EFFECT_BPM
from wha.detect import explained_bpm
from wha.models import NightlyFeatures


def _make_features(
    exercise_offset_h: float | None = None,
    sleep_hours: float | None = None,
    steps_prev_day: int | None = None,
) -> NightlyFeatures:
    return NightlyFeatures(
        subject_id="subj_exp",
        night_date=date(2026, 9, 2),
        rhr_bpm=65.0,
        coverage_minutes=420,
        usable=True,
        exercise_end_offset_h=exercise_offset_h,
        sleep_hours=sleep_hours,
        steps_prev_day=steps_prev_day,
    )


def test_exercise_subtraction_by_bucket() -> None:
    """Each exercise offset bucket subtracts the exact cited BPM effect.

    Asserts against the constants rather than repeating the numbers, so this test checks
    the bucketing rather than restating a figure. The figures themselves are checked
    against Leota et al. 2025 in docs/CORPUS-VERIFICATION.md.
    """
    # 0-2h bucket (e.g. 1.0h)
    f_0_2 = _make_features(exercise_offset_h=1.0)
    sub_0_2, _ = explained_bpm(f_0_2)
    assert sub_0_2 == EXERCISE_EFFECT_BPM["0-2h"]

    # 2-4h bucket (e.g. 3.0h)
    f_2_4 = _make_features(exercise_offset_h=3.0)
    sub_2_4, _ = explained_bpm(f_2_4)
    assert sub_2_4 == EXERCISE_EFFECT_BPM["2-4h"]

    # 4-6h bucket (e.g. 5.0h)
    f_4_6 = _make_features(exercise_offset_h=5.0)
    sub_4_6, _ = explained_bpm(f_4_6)
    assert sub_4_6 == EXERCISE_EFFECT_BPM["4-6h"]


def test_exercise_beyond_lookback_subtracts_nothing() -> None:
    """Workouts ending >6 hours before window start subtract 0.0 bpm."""
    f_7 = _make_features(exercise_offset_h=7.0)
    sub, reasons = explained_bpm(f_7)
    assert sub == 0.0
    assert len(reasons) == 0


def test_short_sleep_is_never_subtracted() -> None:
    """Short sleep duration is never subtracted from heart rate deviation."""
    f_short = _make_features(exercise_offset_h=None, sleep_hours=3.5)
    sub, reasons = explained_bpm(f_short)
    assert sub == 0.0
    assert len(reasons) == 0


def test_reasons_recorded_for_every_subtraction() -> None:
    """Every positive subtraction appends a reason string citing Leota 2025."""
    f = _make_features(exercise_offset_h=1.5)
    sub, reasons = explained_bpm(f)
    # Against the constant, not a repeated literal. The number is verified against the
    # source in docs/CORPUS-VERIFICATION.md; what this test is for is that a subtraction
    # never happens silently.
    assert sub == EXERCISE_EFFECT_BPM["0-2h"]
    assert len(reasons) == 1
    assert "exercise ended 1.5h before the window" in reasons[0]
    assert "Leota 2025" in reasons[0]
