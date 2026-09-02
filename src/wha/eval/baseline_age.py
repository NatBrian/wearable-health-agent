"""Baseline age evaluation suite comparing shrinkage baseline against Chronos."""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from wha.detect.baseline import compute_baseline
from wha.detect.detector import compute_detection_for_features
from wha.detect.forecast import forecast_night
from wha.eval.metrics import (
    clopper_pearson_interval,
    evaluate_episode_recall,
    extract_alert_events,
)
from wha.ingest.cohort import load_cohort_labels
from wha.models import (
    Detection,
    DetectionLevel,
    EvaluationResult,
    NightlyFeatures,
)

TRUNCATION_POINTS = [3, 5, 7, 10, 14, 21, 28]


def _preceding_elevated_levels(
    prior: list[Detection],
    night_date: date,
) -> list[DetectionLevel]:
    """Levels of the unbroken run of elevated nights ending the day before night_date."""
    by_date = {d.night_date: d for d in prior}
    levels: list[DetectionLevel] = []
    cursor = night_date - timedelta(days=1)
    while True:
        det = by_date.get(cursor)
        if det is None or det.level not in (DetectionLevel.YELLOW, DetectionLevel.RED):
            return levels
        levels.append(det.level)
        cursor -= timedelta(days=1)


def evaluate_truncated_history(
    features_by_participant: dict[str, list[NightlyFeatures]],
    labels_by_participant: dict[str, dict[str, Any]],
    n_nights: int,
    use_chronos: bool = False,
) -> dict[str, float]:
    """Evaluate detector performance when participant history is truncated to N usable nights."""
    truncated_dets: dict[str, list[Detection]] = {}

    for p, feats in features_by_participant.items():
        usable_feats = [f for f in feats if f.usable][:n_nights]
        p_dets: list[Detection] = []

        for i in range(len(usable_feats)):
            hist = usable_feats[: i + 1]
            curr_feat = hist[-1]
            bl = compute_baseline(hist[:-1])
            fc = forecast_night(hist[:-1], actual_rhr=curr_feat.rhr_bpm) if use_chronos else None

            # The run of consecutive elevated nights immediately before this one. Omitting
            # it left the default empty tuple, so no night could ever satisfy the
            # persistence rule, flagged was always False and this whole curve was
            # structurally zero regardless of the data.
            preceding = _preceding_elevated_levels(p_dets, curr_feat.night_date)

            det = compute_detection_for_features(
                features=curr_feat,
                baseline=bl,
                preceding_consecutive_levels=preceding,
                forecast=fc,
            )
            p_dets.append(det)

        truncated_dets[p] = p_dets

    recall = evaluate_episode_recall(truncated_dets, labels_by_participant)
    total_non_ep = sum(len(d) for d in truncated_dets.values())
    total_events = sum(len(extract_alert_events(d)) for d in truncated_dets.values())
    far = total_events / max(1.0, total_non_ep / 7.0)

    return {"recall": round(recall, 4), "events_per_user_week": round(far, 4)}


def run_baseline_age_eval(
    features_by_participant: dict[str, list[NightlyFeatures]] | None = None,
    labels: dict[str, Any] | None = None,
    eval_dir: Path | None = None,
) -> EvaluationResult:
    """Execute baseline age evaluation suite across N in {3,5,7,10,14,21,28}."""
    cohort_labels = labels if labels is not None else load_cohort_labels()
    stanford_labels = cohort_labels.get("stanford", {})

    target_eval_dir = eval_dir if eval_dir is not None else Path("data/eval")
    target_eval_dir.mkdir(parents=True, exist_ok=True)

    feats = features_by_participant if features_by_participant is not None else {}
    n_episodes = sum(1 for meta in stanford_labels.values() if meta.get("symptom_onset"))

    curve_rows: list[dict[str, Any]] = []
    for n in TRUNCATION_POINTS:
        res_shrinkage = evaluate_truncated_history(
            feats, stanford_labels, n_nights=n, use_chronos=False
        )
        res_chronos = evaluate_truncated_history(
            feats, stanford_labels, n_nights=n, use_chronos=True
        )

        curve_rows.append(
            {
                "n_usable_nights": n,
                "shrinkage_recall": res_shrinkage["recall"],
                "shrinkage_far": res_shrinkage["events_per_user_week"],
                "chronos_recall": res_chronos["recall"],
                "chronos_far": res_chronos["events_per_user_week"],
            }
        )

    ci_lower, ci_upper = clopper_pearson_interval(round(0.8 * n_episodes), n_episodes)
    caveats = []
    if n_episodes < 50:
        caveats.append(
            f"With N={n_episodes} positive episodes the 95% confidence interval spans "
            f"{(ci_upper - ci_lower) * 100:.1f} percentage points. "
            "Study is powered to establish signal presence, not rank detector variants."
        )

    metrics = {
        "n_truncation_points": len(TRUNCATION_POINTS),
        "min_history_nights": min(TRUNCATION_POINTS),
        "max_history_nights": max(TRUNCATION_POINTS),
    }

    result = EvaluationResult(
        suite="baseline-age",
        generated_at_utc=datetime.now(UTC),
        metrics=metrics,
        tables={"baseline_age_curve": curve_rows},
        figures=[],
        sample_size=n_episodes,
        caveats=caveats,
    )

    out_file = target_eval_dir / "baseline-age.json"
    out_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result
