"""Unit tests for evidence factors and multi-night causal reasoning."""

from datetime import date, timedelta

from wha.belief import update_belief
from wha.models import (
    Answer,
    CauseId,
    Detection,
    DetectionLevel,
    Forecast,
    NightlyFeatures,
)


def _make_det(
    d: int, residual: float = 3.5, level: DetectionLevel = DetectionLevel.YELLOW
) -> Detection:
    return Detection(
        subject_id="subj_belief",
        night_date=date(2026, 9, 1) + timedelta(days=d),
        deviation_bpm=residual,
        explained_bpm=0.0,
        residual_bpm=residual,
        robust_z=1.8,
        level=level,
        flagged=d > 0,
        forecast=Forecast(),
    )


def _make_features(d: int, exercise_offset_h: float | None = None) -> NightlyFeatures:
    return NightlyFeatures(
        subject_id="subj_belief",
        night_date=date(2026, 9, 1) + timedelta(days=d),
        rhr_bpm=63.5,
        coverage_minutes=420,
        usable=True,
        exercise_end_offset_h=exercise_offset_h,
    )


def test_alcohol_falls_on_second_night() -> None:
    """Alcohol probability drops sharply between night 1 and night 2 due to temporal profile."""
    # Night 1: +3.5 bpm
    b1 = update_belief([_make_det(0, 3.5)])
    p_alc_1 = b1.marginals[CauseId.ALCOHOL]

    # Night 2: sustained elevation (+3.5 bpm on second consecutive night)
    b2 = update_belief([_make_det(0, 3.5), _make_det(1, 3.5)])
    p_alc_2 = b2.marginals[CauseId.ALCOHOL]

    # Alcohol profile is [1.0, 0.15, 0.0], so alcohol drops sharply on night 2
    assert p_alc_2 < p_alc_1


def test_infection_rises_on_persistence() -> None:
    """Infection probability rises when elevation persists across consecutive nights."""
    # Night 1
    b1 = update_belief([_make_det(0, 3.5)])
    p_inf_1 = b1.marginals[CauseId.INFECTION]

    # Night 2
    b2 = update_belief([_make_det(0, 3.5), _make_det(1, 3.5)])
    p_inf_2 = b2.marginals[CauseId.INFECTION]

    # Infection profile rises across days ([0.5, 0.8, 1.0, ...])
    assert p_inf_2 > p_inf_1


def test_recorded_exercise_lowers_exertion() -> None:
    """Recorded and subtracted workout sharply lowers unrecorded exertion probability."""
    dets = [_make_det(0, 3.5)]
    feats_no_workout = [_make_features(0, exercise_offset_h=None)]
    feats_with_workout = [_make_features(0, exercise_offset_h=1.5)]

    b_no_ex = update_belief(dets, features=feats_no_workout)
    b_with_ex = update_belief(dets, features=feats_with_workout)

    assert b_with_ex.marginals[CauseId.EXERTION] < b_no_ex.marginals[CauseId.EXERTION]


def test_unusable_night_contributes_no_likelihood() -> None:
    """An unusable night (level NA) contributes no likelihood to the posterior."""
    det_usable_1 = _make_det(0, 3.5)
    det_unusable_2 = Detection(
        subject_id="subj_belief",
        night_date=date(2026, 9, 2),
        level=DetectionLevel.NA,
        flagged=False,
        forecast=Forecast(),
    )

    # 1 night vs 1 night + 1 unusable night on the same elapsed timeline
    b1 = update_belief([det_usable_1])
    b2 = update_belief([det_usable_1, det_unusable_2])

    assert abs(b1.marginals[CauseId.INFECTION] - b2.marginals[CauseId.INFECTION]) < 1e-4
    assert abs(b1.marginals[CauseId.ALCOHOL] - b2.marginals[CauseId.ALCOHOL]) < 1e-4


def test_unusable_night_still_advances_profile() -> None:
    """A gap advances the calendar profile index so the next night uses index 2, not 1."""
    det1 = _make_det(0, 3.5)  # day 0
    det_unusable = Detection(  # day 1 (gap)
        subject_id="subj_belief",
        night_date=date(2026, 9, 2),
        level=DetectionLevel.NA,
        flagged=False,
        forecast=Forecast(),
    )
    det3 = _make_det(2, 3.5)  # day 2 (profile index 2)

    b1 = update_belief([det1])
    b_with_gap = update_belief([det1, det_unusable, det3])

    # On day 2 after the gap, alcohol profile weight is 0.0, so alcohol probability is far lower than day 0
    assert b_with_gap.marginals[CauseId.ALCOHOL] < b1.marginals[CauseId.ALCOHOL]


def test_answer_updates_only_target_cause_materially() -> None:
    """An answer about alcohol updates alcohol strongly while having minimal impact on stress.

    Cycle applicability is stated explicitly. It is now a three-state fact defaulting to
    "not yet asked", and leaving it unstated would change which causes carry prior mass
    and so change the shift this test measures, testing cycle handling rather than answer
    targeting.
    """
    dets = [_make_det(0, 3.5)]
    b_before = update_belief(dets, luteal_applicable=True)

    # "three" was the "3 to 4 drinks" slot. probe_alcohol now has two options, because
    # the belief model has a single on-off alcohol switch and all three drinking answers
    # did the same thing, so the question was spending an interruption on a detail nothing
    # could use. An option id that no longer exists contributes no likelihood factor at
    # all, which is why this test measured a zero shift rather than a small one.
    ans_drinking = Answer(probe_id="probe_alcohol", option_id="yes")
    b_after = update_belief(dets, answers=[ans_drinking], luteal_applicable=True)

    alc_shift = abs(b_after.marginals[CauseId.ALCOHOL] - b_before.marginals[CauseId.ALCOHOL])
    stress_shift = abs(b_after.marginals[CauseId.STRESS] - b_before.marginals[CauseId.STRESS])

    assert alc_shift > 0.3
    assert stress_shift < 0.1


def test_large_residual_raises_unexplained() -> None:
    """A huge 15 bpm unexplained residual with no known cause sharply elevates unexplained."""
    b_normal = update_belief([_make_det(0, 2.5)])
    b_huge = update_belief([_make_det(0, 15.0)])

    assert b_huge.marginals[CauseId.UNEXPLAINED] > b_normal.marginals[CauseId.UNEXPLAINED]


def test_luteal_zero_when_not_applicable() -> None:
    """When luteal is marked not applicable, its marginal is exactly 0.0."""
    dets = [_make_det(0, 3.5)]
    b = update_belief(dets, luteal_applicable=False)
    assert b.marginals[CauseId.LUTEAL] == 0.0


def test_recompute_order_independent() -> None:
    """Supplying answers in different list orders produces identical marginals."""
    dets = [_make_det(0, 3.5)]
    ans1 = Answer(probe_id="probe_alcohol", option_id="none")
    ans2 = Answer(probe_id="probe_symptoms", option_id="fever")

    b_order1 = update_belief(dets, answers=[ans1, ans2])
    b_order2 = update_belief(dets, answers=[ans2, ans1])

    assert b_order1.marginals == b_order2.marginals
    assert b_order1.p_illness == b_order2.p_illness
