"""How detection performance depends on how many of the person's own nights exist.

CORRECTED 5 September 2026. This patched `wha.detect.forecast.get_chronos_pipeline` and
asserted that every row of the curve carried both a `shrinkage_` and a `chronos_` figure.

Two things were wrong with that, and only the second is about the deletion.

The `chronos_` column was never a second estimator. Both arms called the same detector,
and the forecast never set `level` or `flagged`, so the two arms computed identical alerts
and the second column was the first under another name. A test asserting "both estimators
are present" passed on a table that had one estimator in it twice.

The forecast is now gone entirely, measured rather than argued: over 7,295 nights of the
Mishra 2020 cohort it separated illness nights from ordinary ones WORSE than the plain
residual (AUC 0.586 against 0.629) and caught at most one of thirty infections the
detector missed. See `experiments/detection/cohort/chronos.py`.
"""

from datetime import date, timedelta
from pathlib import Path

from wha.eval.baseline_age import run_baseline_age_eval
from wha.models import NightlyFeatures

TRUNCATION_POINTS = 7


def _make_features(subject_id: str, n_nights: int) -> list[NightlyFeatures]:
    start_d = date(2026, 8, 1)
    feats: list[NightlyFeatures] = []
    for i in range(n_nights):
        d = start_d + timedelta(days=i)
        feats.append(
            NightlyFeatures(
                subject_id=subject_id,
                night_date=d,
                # Two consecutive raised nights, which is what the persistence rule needs.
                rhr_bpm=60.0 + (5.0 if i in {10, 11} else 0.0),
                coverage_minutes=420,
                usable=True,
            )
        )
    return feats


def _labels() -> dict:
    return {"stanford": {"p01": {"covid_positive": True, "symptom_onset": "2026-08-12"}}}


def test_baseline_age_uses_real_code_path(tmp_path: Path) -> None:
    """It runs the real compute_baseline and the real detector, with nothing patched.

    Nothing needs patching now. The stub pipeline this used to install existed only to
    stand in for Chronos.
    """
    res = run_baseline_age_eval(
        features_by_participant={"p01": _make_features("p01", 30)},
        labels=_labels(),
        eval_dir=tmp_path,
    )

    assert res.suite == "baseline-age"
    curve = res.tables["baseline_age_curve"]
    assert len(curve) == TRUNCATION_POINTS


def test_the_curve_reports_one_estimator_because_there_is_one(tmp_path: Path) -> None:
    """No `chronos_` column, because there was never a second estimator behind it."""
    res = run_baseline_age_eval(
        features_by_participant={"p01": _make_features("p01", 30)},
        labels=_labels(),
        eval_dir=tmp_path,
    )

    for row in res.tables["baseline_age_curve"]:
        assert set(row) == {"n_usable_nights", "shrinkage_recall", "shrinkage_far"}


def test_recall_is_zero_below_the_alerting_floor(tmp_path: Path) -> None:
    """Nothing is flagged before the baseline is the person's own, so nothing is recalled.

    Worth asserting because a curve that started above zero would mean the truncation was
    not being applied, and this evaluation exists to show exactly that floor.
    """
    res = run_baseline_age_eval(
        features_by_participant={"p01": _make_features("p01", 30)},
        labels=_labels(),
        eval_dir=tmp_path,
    )

    curve = {row["n_usable_nights"]: row for row in res.tables["baseline_age_curve"]}
    assert curve[3]["shrinkage_recall"] == 0.0
    assert curve[5]["shrinkage_recall"] == 0.0
