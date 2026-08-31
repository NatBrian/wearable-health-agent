"""Unit tests for baseline age evaluation suite."""

from datetime import date, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

from wha.eval.baseline_age import run_baseline_age_eval
from wha.models import NightlyFeatures


class StubPipeline:
    """Stub pipeline returning deterministic quantiles."""

    def predict_quantiles(
        self,
        context: Any,
        prediction_length: int = 1,
        quantile_levels: list[float] | None = None,
    ) -> dict[float, float]:
        return {0.1: 58.0, 0.5: 60.0, 0.9: 62.0}


def _make_features(subject_id: str, n_nights: int) -> list[NightlyFeatures]:
    start_d = date(2026, 8, 1)
    feats: list[NightlyFeatures] = []
    for i in range(n_nights):
        d = start_d + timedelta(days=i)
        feats.append(
            NightlyFeatures(
                subject_id=subject_id,
                night_date=d,
                rhr_bpm=60.0 + (5.0 if i in {10, 11} else 0.0),
                coverage_minutes=420,
                usable=True,
            )
        )
    return feats


def test_baseline_age_uses_real_code_path(tmp_path: Path) -> None:
    """Baseline age evaluation executes real compute_baseline and detection pipeline."""
    labels = {
        "stanford": {
            "p01": {
                "covid_positive": True,
                "symptom_onset": "2026-08-12",
            }
        }
    }
    feats = {"p01": _make_features("p01", 30)}

    with patch("wha.detect.forecast.get_chronos_pipeline", return_value=StubPipeline()):
        res = run_baseline_age_eval(
            features_by_participant=feats,
            labels=labels,
            eval_dir=tmp_path,
        )

    assert res.suite == "baseline-age"
    assert "baseline_age_curve" in res.tables
    curve = res.tables["baseline_age_curve"]
    assert len(curve) == 7


def test_curve_has_both_estimators(tmp_path: Path) -> None:
    """Every truncation point records metrics for both the shrinkage baseline and Chronos."""
    labels = {
        "stanford": {
            "p01": {
                "covid_positive": True,
                "symptom_onset": "2026-08-12",
            }
        }
    }
    feats = {"p01": _make_features("p01", 30)}

    with patch("wha.detect.forecast.get_chronos_pipeline", return_value=StubPipeline()):
        res = run_baseline_age_eval(
            features_by_participant=feats,
            labels=labels,
            eval_dir=tmp_path,
        )

    curve = res.tables["baseline_age_curve"]
    for row in curve:
        assert "n_usable_nights" in row
        assert "shrinkage_recall" in row
        assert "shrinkage_far" in row
        assert "chronos_recall" in row
        assert "chronos_far" in row
