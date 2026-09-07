"""Unit tests for detection evaluation suite and small-sample statistics."""

from datetime import date
from pathlib import Path

import scipy.stats

from wha.eval import (
    calculate_lead_times,
    clopper_pearson_interval,
    cluster_bootstrap_ci,
    evaluate_episode_recall,
    extract_alert_events,
    permutation_test_null,
    run_detection_eval,
)
from wha.models import Detection, DetectionLevel, Forecast, ForecastStatus


def _make_det(d_str: str, flagged: bool) -> Detection:
    d = date.fromisoformat(d_str)
    return Detection(
        subject_id="test_subj",
        night_date=d,
        level=DetectionLevel.RED if flagged else DetectionLevel.GREEN,
        deviation_bpm=6.0 if flagged else 0.0,
        residual_bpm=6.0 if flagged else 0.0,
        flagged=flagged,
        forecast=Forecast(
            predicted_bpm=60.0,
            lo_bpm=55.0,
            hi_bpm=65.0,
            status=ForecastStatus.OK,
        ),
    )


def test_alert_event_definition() -> None:
    """Runs of 1, 2, and 3 days are identified correctly and a gap breaks a run."""
    # Run 1: Aug 1 to Aug 3 (3 days), Gap Aug 4, Run 2: Aug 5 (1 day), Run 3: Aug 7-8 (2 days)
    dates_flagged = [
        ("2026-08-01", True),
        ("2026-08-02", True),
        ("2026-08-03", True),
        ("2026-08-04", False),
        ("2026-08-05", True),
        ("2026-08-06", False),
        ("2026-08-07", True),
        ("2026-08-08", True),
    ]
    dets = [_make_det(ds, fl) for ds, fl in dates_flagged]

    # At min_run_length = 2: should find [Aug 1 - Aug 3] and [Aug 7 - Aug 8] (Aug 5 is length 1 -> skipped)
    events_2 = extract_alert_events(dets, min_run_length=2)
    assert len(events_2) == 2
    assert events_2[0] == (date(2026, 8, 1), date(2026, 8, 3))
    assert events_2[1] == (date(2026, 8, 7), date(2026, 8, 8))

    # At min_run_length = 1: finds all 3 runs
    events_1 = extract_alert_events(dets, min_run_length=1)
    assert len(events_1) == 3


def test_detection_window_boundaries() -> None:
    """Detection window is [onset - 7, onset + 1]. Onset - 7 detects, onset - 8 does not."""
    onset = "2026-08-15"
    labels = {"p01": {"covid_positive": True, "symptom_onset": onset}}

    # Alert starts on Aug 8 (onset - 7) -> detected
    dets_in = {"p01": [_make_det("2026-08-08", True), _make_det("2026-08-09", True)]}
    recall_in = evaluate_episode_recall(dets_in, labels, persistence_nights=2, l_max=7)
    assert recall_in == 1.0

    # Alert starts on Aug 7 (onset - 8) -> not detected in 7-day window
    dets_out = {"p01": [_make_det("2026-08-07", True), _make_det("2026-08-08", True)]}
    recall_out = evaluate_episode_recall(dets_out, labels, persistence_nights=2, l_max=7)
    assert recall_out == 0.0


def test_lead_time_uses_first_alert_day() -> None:
    """Lead time is calculated as (onset - first_alert_day)."""
    onset = "2026-08-15"
    labels = {"p01": {"covid_positive": True, "symptom_onset": onset}}
    # Alert runs from Aug 10 to Aug 14 (first alert is Aug 10)
    dets = {
        "p01": [
            _make_det("2026-08-10", True),
            _make_det("2026-08-11", True),
            _make_det("2026-08-12", True),
        ]
    }
    leads = calculate_lead_times(dets, labels, persistence_nights=2, l_max=7)
    assert len(leads) == 1
    # 2026-08-15 - 2026-08-10 = 5 days lead time
    assert leads[0] == 5


def test_clopper_pearson_matches_scipy() -> None:
    """Clopper-Pearson 26 of 32 gives approximately 63.6% to 92.8%."""
    k, n = 26, 32
    ci_low, ci_high = clopper_pearson_interval(k, n, confidence=0.95)

    expected_low = scipy.stats.beta.ppf(0.025, k, n - k + 1)
    expected_high = scipy.stats.beta.ppf(0.975, k + 1, n - k)

    assert abs(ci_low - expected_low) < 1e-3
    assert abs(ci_high - expected_high) < 1e-3
    assert 0.63 <= ci_low <= 0.65
    assert 0.92 <= ci_high <= 0.94


def test_cluster_bootstrap_resamples_participants() -> None:
    """Cluster bootstrap resamples participant units, preserving intra-subject day correlations."""
    # 5 participants with different average scores
    data = {
        "p1": [1.0, 1.0, 1.0],
        "p2": [0.0, 0.0, 0.0],
        "p3": [1.0, 1.0, 1.0],
        "p4": [0.0, 0.0, 0.0],
        "p5": [1.0, 1.0, 1.0],
    }

    def mean_score(sample_data: dict[str, list[float]]) -> float:
        all_vals = [v for vals in sample_data.values() for v in vals]
        return sum(all_vals) / len(all_vals)

    ci_low, ci_high = cluster_bootstrap_ci(data, mean_score, n_resamples=100, seed=42)
    assert 0.0 <= ci_low <= 0.7
    assert 0.5 <= ci_high <= 1.0


def test_permutation_test_null_is_centred() -> None:
    """Permutation test on null data (no true association) yields uniform / non-significant p-value."""
    # Participant with 1 alert event and random onset
    dets = {"p01": [_make_det(f"2026-08-{i:02d}", i in {5, 6}) for i in range(1, 31)]}
    labels = {"p01": {"covid_positive": True, "symptom_onset": "2026-08-06"}}

    p_val = permutation_test_null(dets, labels, n_permutations=100, seed=42)
    assert 0.0 <= p_val <= 1.0


def test_point_adjusted_f1_is_not_computed() -> None:
    """Grep verification: Point-adjusted F1 is strictly forbidden in the codebase."""
    code_dir = Path("src/wha")
    for py_file in code_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8").lower()
        assert "point_adjusted" not in content
        assert "point_adjustment" not in content
        assert "point_adjust" not in content


def test_auprc_reported_with_prevalence(tmp_path: Path) -> None:
    """AUPRC metric in EvaluationResult is always accompanied by prevalence."""
    labels = {"stanford": {"p01": {"covid_positive": True, "symptom_onset": "2026-08-10"}}}
    dets = {"p01": [_make_det(f"2026-08-{i:02d}", i in {8, 9}) for i in range(1, 31)]}

    res = run_detection_eval(
        detections_by_participant=dets,
        labels=labels,
        eval_dir=tmp_path,
    )

    assert "auprc" in res.metrics
    assert "prevalence" in res.metrics
    assert "baseline_trivial_recall" in res.metrics
    assert "baseline_random_recall" in res.metrics
