"""A night is compared against the person, not against the average adult.

The detection thresholds come from NightSignal, which measures deviations above a
per-individual streaming median with no population blending. The centre was shrunk toward
a 62.75 bpm population prior at a weight that capped at 0.8, because the trailing window
caps the night count, so a fifth of the prior never washed out. Every subject carried a
permanent residual offset proportional to their distance from the average, and the
detector is tuned to a 3 to 4 bpm change.
"""

from datetime import date, timedelta

import pytest

from wha.constants import (
    BASELINE_MIN_NIGHTS_PERSONAL,
    DETECT_RED_BPM,
    DETECT_YELLOW_BPM,
    POP_PRIOR_RHR_MEAN_BPM,
)
from wha.detect.baseline import compute_baseline
from wha.detect.detector import compute_detection_for_features
from wha.models import DetectionLevel, NightlyFeatures


def _history(rhr: float, nights: int) -> list[NightlyFeatures]:
    return [
        NightlyFeatures(
            subject_id="x",
            night_date=date(2026, 1, 1) + timedelta(days=i),
            rhr_bpm=rhr,
            coverage_minutes=400,
            usable=True,
        )
        for i in range(nights)
    ]


def _tonight(rhr: float) -> NightlyFeatures:
    return NightlyFeatures(
        subject_id="x",
        night_date=date(2026, 6, 1),
        rhr_bpm=rhr,
        coverage_minutes=400,
        usable=True,
    )


@pytest.mark.parametrize("rhr", [42.0, 45.0, 50.0, 62.75, 70.0, 75.0, 80.0])
def test_a_steady_person_sits_at_zero_whatever_their_resting_rate(rhr: float) -> None:
    """The regression: at 45 the residual was -3.5 forever, at 80 it was +3.5 forever.

    A subject at 80 was therefore YELLOW every night while perfectly healthy, and a subject
    at 45 needed a 6.5 bpm rise to reach YELLOW when infection produces 1.6 to 5.
    """
    baseline = compute_baseline(_history(rhr, 200))
    detection = compute_detection_for_features(_tonight(rhr), baseline)

    assert detection.residual_bpm == pytest.approx(0.0, abs=0.01)
    assert detection.level == DetectionLevel.GREEN


@pytest.mark.parametrize("rhr", [45.0, 62.75, 80.0])
def test_the_published_thresholds_mean_what_they_say(rhr: float) -> None:
    """3 bpm above the person's own median is YELLOW and 4 is RED, for everyone."""
    baseline = compute_baseline(_history(rhr, 30))

    just_under = compute_detection_for_features(_tonight(rhr + DETECT_YELLOW_BPM - 0.1), baseline)
    at_yellow = compute_detection_for_features(_tonight(rhr + DETECT_YELLOW_BPM), baseline)
    at_red = compute_detection_for_features(_tonight(rhr + DETECT_RED_BPM), baseline)

    assert just_under.level == DetectionLevel.GREEN
    assert at_yellow.level == DetectionLevel.YELLOW
    assert at_red.level == DetectionLevel.RED


def test_an_infection_sized_rise_is_detected_in_a_low_resting_subject() -> None:
    """The first real subject sits at 44 to 47. Infection raises RHR by 1.6 to 5 bpm.

    Against the old shrunk centre this subject needed 6.5 bpm and would never have been
    flagged for an infection at all.
    """
    baseline = compute_baseline(_history(45.0, 30))
    detection = compute_detection_for_features(_tonight(45.0 + 4.2), baseline)

    assert detection.level == DetectionLevel.RED


def test_the_centre_is_the_persons_own_median_once_established() -> None:
    baseline = compute_baseline(_history(45.0, BASELINE_MIN_NIGHTS_PERSONAL))
    assert baseline.centre_bpm == pytest.approx(45.0)


def test_the_centre_borrows_from_the_population_before_that() -> None:
    """A median over one or two nights is noise, so the prior still carries weight."""
    baseline = compute_baseline(_history(45.0, BASELINE_MIN_NIGHTS_PERSONAL - 1))
    assert 45.0 < baseline.centre_bpm < POP_PRIOR_RHR_MEAN_BPM


def test_nothing_is_flagged_before_the_baseline_is_the_persons_own() -> None:
    """A two-night baseline is 78 percent population guess and must not open an alert."""
    baseline = compute_baseline(_history(45.0, 2))
    detection = compute_detection_for_features(
        _tonight(90.0),
        baseline,
        preceding_consecutive_levels=[DetectionLevel.RED, DetectionLevel.RED],
    )

    assert detection.level == DetectionLevel.RED, "the level is still computed and charted"
    assert detection.flagged is False, "but it cannot raise an alert"


def test_flagging_resumes_once_there_are_enough_nights() -> None:
    baseline = compute_baseline(_history(45.0, BASELINE_MIN_NIGHTS_PERSONAL))
    detection = compute_detection_for_features(
        _tonight(45.0 + DETECT_RED_BPM),
        baseline,
        preceding_consecutive_levels=[DetectionLevel.RED],
    )

    assert detection.flagged is True


def test_the_scale_still_borrows_spread_from_the_population() -> None:
    """Scale sets band width and robust_z, never the level, so its shrinkage is kept."""
    few = compute_baseline(_history(45.0, 3))
    many = compute_baseline(_history(45.0, 28))
    assert few.scale_bpm > many.scale_bpm, "less data must give a wider band"
