"""Unit tests for level determination, alert persistence, and detection storage."""

from datetime import date, timedelta
from pathlib import Path

from wha.db import apply_schema, connect
from wha.detect import (
    compute_detection_for_features,
    detect_night,
)
from wha.models import (
    Baseline,
    BaselineRung,
    DetectionLevel,
    NightlyFeatures,
)


def _make_baseline(
    centre: float = 60.0, scale: float = 2.0, rung: BaselineRung = BaselineRung.MATURE
) -> Baseline:
    return Baseline(
        centre_bpm=centre,
        scale_bpm=scale,
        usable_nights=28,
        rung=rung,
        shrink_weight=0.8,
    )


def _make_features(
    d: int,
    rhr: float = 60.0,
    usable: bool = True,
    exercise_offset_h: float | None = None,
) -> NightlyFeatures:
    return NightlyFeatures(
        subject_id="subj_det_test",
        night_date=date(2026, 9, 1) + timedelta(days=d),
        rhr_bpm=rhr if usable else None,
        coverage_minutes=420 if usable else 0,
        usable=usable,
        exercise_end_offset_h=exercise_offset_h,
    )


def test_level_thresholds_exact() -> None:
    """Residual boundaries are exact: <3.0 GREEN, [3.0, 4.0) YELLOW, >=4.0 RED."""
    base = _make_baseline(centre=60.0)

    # Residual = 2.99 -> GREEN
    d_299 = compute_detection_for_features(_make_features(0, rhr=62.99), base)
    assert d_299.level == DetectionLevel.GREEN

    # Residual = 3.00 -> YELLOW
    d_300 = compute_detection_for_features(_make_features(0, rhr=63.00), base)
    assert d_300.level == DetectionLevel.YELLOW

    # Residual = 3.99 -> YELLOW
    d_399 = compute_detection_for_features(_make_features(0, rhr=63.99), base)
    assert d_399.level == DetectionLevel.YELLOW

    # Residual = 4.00 -> RED
    d_400 = compute_detection_for_features(_make_features(0, rhr=64.00), base)
    assert d_400.level == DetectionLevel.RED


def test_level_uses_residual_not_deviation() -> None:
    """A 5 bpm deviation with 2.91 bpm explained by workout results in 2.09 bpm residual (GREEN)."""
    base = _make_baseline(centre=60.0)
    # RHR is 65.0 (+5.0 deviation), workout ended 1.0h before sleep (-2.91 bpm) -> residual 2.09.
    #
    # The subtraction was 4.14 until 4 September 2026. That figure appears nowhere in
    # Leota et al. 2025; two of the three band values traced exactly to the paper's table
    # and this one did not. Corrected to the paper's high-strain value at the far edge of
    # the band, which subtracts less. The assertion this test exists for is unchanged: the
    # level follows the residual, not the raw deviation, and this night is still GREEN.
    features = _make_features(0, rhr=65.0, exercise_offset_h=1.0)
    det = compute_detection_for_features(features, base)

    assert det.deviation_bpm == 5.0
    assert det.explained_bpm == 2.91
    assert det.residual_bpm == 2.09
    assert det.level == DetectionLevel.GREEN
    assert not det.flagged


def test_single_red_night_does_not_flag() -> None:
    """A single RED night does not meet the 2-night persistence threshold."""
    base = _make_baseline(centre=60.0)
    # Night with +5.0 bpm residual (RED) but no preceding elevated nights
    features = _make_features(0, rhr=65.0)
    det = compute_detection_for_features(features, base, preceding_consecutive_levels=[])

    assert det.level == DetectionLevel.RED
    assert not det.flagged


def test_only_two_consecutive_reds_flag() -> None:
    """Both nights must be RED. A RED beside a YELLOW is not an investigation.

    CORRECTED 5 September 2026, and the two cases that changed are named below rather than
    deleted. This test asserted the looser rule: two consecutive elevated nights with at
    least ONE red. That is not what the cited paper does. NightSignal raises a red alert
    when the overnight reading is at or above baseline + 4 on two consecutive nights, and
    this project quotes NightSignal's sensitivity as support for its own thresholds while
    running something looser.

    Measured before changing it, on 30 labelled COVID-19 cases and 76 healthy people over
    738 person-weeks (uv run python experiments/detection/cohort/sweep.py):

        at least one RED : 60.0 percent sensitivity, 0.272 investigations per person-week
        both RED         : 53.3 percent sensitivity, 0.198 investigations per person-week

    Two cases in thirty, for 37 percent more investigations on people who were not ill.
    """
    base = _make_baseline(centre=60.0)

    # Yesterday YELLOW, tonight RED. Used to flag. Does not now.
    det1 = compute_detection_for_features(
        _make_features(1, rhr=65.0), base, preceding_consecutive_levels=[DetectionLevel.YELLOW]
    )
    assert det1.level == DetectionLevel.RED
    assert det1.flagged is False

    # Yesterday RED, tonight YELLOW. Used to flag. Does not now.
    det2 = compute_detection_for_features(
        _make_features(1, rhr=63.5), base, preceding_consecutive_levels=[DetectionLevel.RED]
    )
    assert det2.level == DetectionLevel.YELLOW
    assert det2.flagged is False

    # Yesterday RED, tonight RED. The published rule, and the only one that flags.
    det3 = compute_detection_for_features(
        _make_features(1, rhr=65.0), base, preceding_consecutive_levels=[DetectionLevel.RED]
    )
    assert det3.level == DetectionLevel.RED
    assert det3.flagged is True

    # Three RED nights still flags on the third, which is the run continuing.
    det4 = compute_detection_for_features(
        _make_features(1, rhr=65.0),
        base,
        preceding_consecutive_levels=[DetectionLevel.RED, DetectionLevel.RED],
    )
    assert det4.flagged is True


def test_two_yellows_without_red_does_not_flag() -> None:
    """Two consecutive YELLOW nights without a RED do not flag."""
    base = _make_baseline(centre=60.0)
    det = compute_detection_for_features(
        _make_features(1, rhr=63.5), base, preceding_consecutive_levels=[DetectionLevel.YELLOW]
    )
    assert det.level == DetectionLevel.YELLOW
    assert not det.flagged


def test_unusable_night_breaks_the_run(tmp_db_path: Path) -> None:
    """An unusable night between two RED nights breaks the consecutive run and prevents flagging."""
    conn = connect(tmp_db_path)
    apply_schema(conn)

    # Insert subject
    conn.execute(
        """
        INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
        VALUES ('subj_break', 'Subject Break', 'synthetic', 'Asia/Singapore', '2026-09-01T00:00:00Z');
        """
    )
    # Day 1: RED
    conn.execute(
        """
        INSERT INTO nightly_features (subject_id, night_date, rhr_bpm, coverage_minutes, usable, computed_at_utc)
        VALUES ('subj_break', '2026-09-01', 70.0, 420, 1, '2026-09-01T00:00:00Z');
        """
    )
    # Day 2: UNUSABLE (gap)
    conn.execute(
        """
        INSERT INTO nightly_features (subject_id, night_date, rhr_bpm, coverage_minutes, usable, computed_at_utc)
        VALUES ('subj_break', '2026-09-02', NULL, 0, 0, '2026-09-02T00:00:00Z');
        """
    )
    # Day 3: RED
    conn.execute(
        """
        INSERT INTO nightly_features (subject_id, night_date, rhr_bpm, coverage_minutes, usable, computed_at_utc)
        VALUES ('subj_break', '2026-09-03', 70.0, 420, 1, '2026-09-03T00:00:00Z');
        """
    )
    conn.commit()

    det1 = detect_night(conn, "subj_break", date(2026, 9, 1))
    assert det1.level == DetectionLevel.RED
    assert not det1.flagged

    det2 = detect_night(conn, "subj_break", date(2026, 9, 2))
    assert det2.level == DetectionLevel.NA
    assert not det2.flagged

    det3 = detect_night(conn, "subj_break", date(2026, 9, 3))
    assert det3.level == DetectionLevel.RED
    assert not det3.flagged  # Broken run!

    conn.close()


def test_flag_fires_on_the_night_the_run_completes(tmp_db_path: Path) -> None:
    """Flagging occurs exactly on the 2nd elevated night when persistence requirement is met."""
    conn = connect(tmp_db_path)
    apply_schema(conn)

    conn.execute(
        """
        INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
        VALUES ('subj_flag', 'Subject Flag', 'synthetic', 'Asia/Singapore', '2026-09-01T00:00:00Z');
        """
    )
    # 10 baseline nights at 60 bpm
    for i in range(1, 11):
        conn.execute(
            f"""
            INSERT INTO nightly_features (subject_id, night_date, rhr_bpm, coverage_minutes, usable, computed_at_utc)
            VALUES ('subj_flag', '2026-08-{i:02d}', 60.0, 420, 1, '2026-08-{i:02d}T00:00:00Z');
            """
        )
    # Night 1: RED (70.0 bpm)
    conn.execute(
        """
        INSERT INTO nightly_features (subject_id, night_date, rhr_bpm, coverage_minutes, usable, computed_at_utc)
        VALUES ('subj_flag', '2026-08-11', 70.0, 420, 1, '2026-08-11T00:00:00Z');
        """
    )
    # Night 2: RED, 65.0 bpm against a personal median of 60.0 for a +5.0 residual.
    #
    # Restated twice, both times because the rule under test changed and not the intent.
    # It began at 64.5, chosen when the centre was shrunk toward the 62.75 population
    # prior. When the centre became the person's own median that became +4.5 and RED, so
    # it was restated to 63.5 for a +3.5 YELLOW. The persistence rule is now two
    # consecutive REDs, matching the cited paper, so a YELLOW second night no longer
    # completes a run. This test is about WHEN the flag fires on a completed run, so the
    # input is restated again against the rule the detector now uses.
    conn.execute(
        """
        INSERT INTO nightly_features (subject_id, night_date, rhr_bpm, coverage_minutes, usable, computed_at_utc)
        VALUES ('subj_flag', '2026-08-12', 65.0, 420, 1, '2026-08-12T00:00:00Z');
        """
    )
    conn.commit()

    d1 = detect_night(conn, "subj_flag", date(2026, 8, 11))
    assert d1.level == DetectionLevel.RED
    assert not d1.flagged

    d2 = detect_night(conn, "subj_flag", date(2026, 8, 12))
    assert d2.level == DetectionLevel.RED
    assert d2.flagged is True

    conn.close()


def test_detector_never_reads_future_nights(tmp_db_path: Path) -> None:
    """Detection on day N is unaffected by whether day N+1 data is in the database."""
    conn = connect(tmp_db_path)
    apply_schema(conn)

    conn.execute(
        """
        INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
        VALUES ('subj_future', 'Subject Future', 'synthetic', 'Asia/Singapore', '2026-09-01T00:00:00Z');
        """
    )
    # 5 baseline nights
    for i in range(1, 6):
        conn.execute(
            f"""
            INSERT INTO nightly_features (subject_id, night_date, rhr_bpm, coverage_minutes, usable, computed_at_utc)
            VALUES ('subj_future', '2026-08-{i:02d}', 60.0, 420, 1, '2026-08-{i:02d}T00:00:00Z');
            """
        )
    conn.commit()

    d_before = detect_night(conn, "subj_future", date(2026, 8, 5))

    # Add future night with anomalous value
    conn.execute(
        """
        INSERT INTO nightly_features (subject_id, night_date, rhr_bpm, coverage_minutes, usable, computed_at_utc)
        VALUES ('subj_future', '2026-08-06', 99.0, 420, 1, '2026-08-06T00:00:00Z');
        """
    )
    conn.commit()

    d_after = detect_night(conn, "subj_future", date(2026, 8, 5))

    assert d_before.residual_bpm == d_after.residual_bpm
    assert d_before.level == d_after.level
    assert d_before.flagged == d_after.flagged

    conn.close()


def test_negative_residual_is_green_not_clamped() -> None:
    """Negative residual (e.g. -2.5 bpm) is preserved and mapped to GREEN, never clamped to zero."""
    base = _make_baseline(centre=60.0)
    features = _make_features(0, rhr=57.5)
    det = compute_detection_for_features(features, base)

    assert det.residual_bpm == -2.5
    assert det.level == DetectionLevel.GREEN
    assert det.robust_z is not None and det.robust_z < 0


def test_cold_rung_still_computes_detection() -> None:
    """When baseline is on COLD rung, detection row is still fully computed."""
    base = _make_baseline(centre=62.75, rung=BaselineRung.COLD)
    features = _make_features(0, rhr=68.0)
    det = compute_detection_for_features(features, base)

    assert det.level == DetectionLevel.RED
    assert det.residual_bpm is not None and det.residual_bpm > 0
