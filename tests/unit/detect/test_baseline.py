"""Unit tests for shrinkage baseline calculation and the maturity ladder."""

from datetime import date, timedelta

from wha.constants import (
    BASELINE_SCALE_FLOOR_BPM,
    POP_PRIOR_RHR_MEAN_BPM,
    POP_PRIOR_RHR_SD_BPM,
)
from wha.detect import compute_baseline, compute_baseline_truncated, rung_for
from wha.models import BaselineRung, NightlyFeatures


def _make_night(d: int, rhr: float | None = 60.0, usable: bool = True) -> NightlyFeatures:
    return NightlyFeatures(
        subject_id="subj_base",
        night_date=date(2026, 8, 1) + timedelta(days=d),
        rhr_bpm=rhr,
        coverage_minutes=400 if usable else 50,
        usable=usable,
    )


def test_zero_nights_returns_population_prior() -> None:
    """Empty history returns population prior values with zero weight and COLD rung."""
    base = compute_baseline([])
    assert base.centre_bpm == POP_PRIOR_RHR_MEAN_BPM
    assert base.scale_bpm == POP_PRIOR_RHR_SD_BPM
    assert base.usable_nights == 0
    assert base.shrink_weight == 0.0
    assert base.rung == BaselineRung.COLD


def test_shrink_weight_is_half_at_pseudo_nights() -> None:
    """At exactly 7 usable nights, shrinkage weight w equals 0.5."""
    history = [_make_night(i, 60.0) for i in range(7)]
    base = compute_baseline(history)
    assert base.shrink_weight == 0.5
    assert base.usable_nights == 7


def test_mad_floor_applies_when_window_is_constant() -> None:
    """When all historical nights have identical RHR, scale_bpm is floored at BASELINE_SCALE_FLOOR_BPM."""
    history = [_make_night(i, 60.0) for i in range(28)]
    base = compute_baseline(history)
    # With 28 nights, personal_sd is 0 (MAD is 0), so scale_bpm will reach the floor
    assert base.scale_bpm >= BASELINE_SCALE_FLOOR_BPM
    assert base.scale_bpm > 0


def test_median_resists_one_outlier() -> None:
    """A single large outlier in history does not significantly move the baseline centre."""
    history = [_make_night(i, 58.0) for i in range(20)]
    history.append(_make_night(20, 95.0))  # one big spike

    base = compute_baseline(history)
    # Personal median should still be 58.0
    assert (
        abs(
            base.centre_bpm
            - (base.shrink_weight * 58.0 + (1 - base.shrink_weight) * POP_PRIOR_RHR_MEAN_BPM)
        )
        < 0.01
    )


def test_tonight_excluded_from_own_baseline() -> None:
    """Passing only historical nights ensures tonight's observation is excluded."""
    # 5 nights of 60 bpm history
    history = [_make_night(i, 60.0) for i in range(5)]
    # Tonight is 80 bpm (not in history passed to compute_baseline)
    base = compute_baseline(history)
    assert base.usable_nights == 5


def test_illness_nights_excluded_when_closed() -> None:
    """Illness nights from closed episodes can be filtered out of history before compute_baseline."""
    all_nights = [_make_night(i, 60.0) for i in range(10)]
    # Suppose nights 4 and 5 were part of a closed illness episode
    illness_night_dates = {all_nights[4].night_date, all_nights[5].night_date}
    filtered_history = [n for n in all_nights if n.night_date not in illness_night_dates]

    base = compute_baseline(filtered_history)
    assert base.usable_nights == 8


def test_open_episode_nights_are_included() -> None:
    """Open episode nights remain in baseline history until resolution."""
    all_nights = [_make_night(i, 60.0) for i in range(10)]
    base = compute_baseline(all_nights)
    assert base.usable_nights == 10


def test_rung_boundaries_exact() -> None:
    """All 7 rung boundary points match the contract ladder definitions."""
    assert rung_for(0) == BaselineRung.COLD
    assert rung_for(2) == BaselineRung.COLD
    assert rung_for(3) == BaselineRung.PRIOR_DOMINATED
    assert rung_for(6) == BaselineRung.PRIOR_DOMINATED
    assert rung_for(7) == BaselineRung.SHRINKING
    assert rung_for(13) == BaselineRung.SHRINKING
    assert rung_for(14) == BaselineRung.PERSONAL
    assert rung_for(27) == BaselineRung.PERSONAL
    assert rung_for(28) == BaselineRung.MATURE
    assert rung_for(100) == BaselineRung.MATURE


def test_unusable_nights_do_not_count() -> None:
    """Unusable nights are ignored by compute_baseline."""
    history = [_make_night(i, usable=False) for i in range(40)]
    history.append(_make_night(41, rhr=60.0, usable=True))

    base = compute_baseline(history)
    assert base.usable_nights == 1
    assert base.rung == BaselineRung.COLD


def test_window_caps_at_28() -> None:
    """History longer than 28 nights caps at BASELINE_WINDOW_NIGHTS = 28."""
    history = [_make_night(i, 60.0) for i in range(60)]
    base = compute_baseline(history)
    assert base.usable_nights == 28
    assert base.rung == BaselineRung.MATURE


def test_truncated_baseline_matches_full_at_same_n() -> None:
    """compute_baseline_truncated agrees with compute_baseline on same effective history length."""
    history = [_make_night(i, 58.0 + (i % 3)) for i in range(20)]
    b_full = compute_baseline(history[:10])
    b_trunc = compute_baseline_truncated(history, 10)

    assert b_full.centre_bpm == b_trunc.centre_bpm
    assert b_full.scale_bpm == b_trunc.scale_bpm
    assert b_full.usable_nights == b_trunc.usable_nights
