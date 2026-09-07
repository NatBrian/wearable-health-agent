"""Cohort detection evaluation suite with mandatory comparator baselines."""

import random
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from wha.clock import now_utc
from wha.detect.baselines import detect_random, detect_trivial
from wha.errors import ConfigError
from wha.eval.metrics import (
    calculate_lead_times,
    clopper_pearson_interval,
    evaluate_episode_recall,
    extract_alert_events,
)
from wha.ingest.cohort import load_cohort_labels
from wha.models import (
    Detection,
    DetectionLevel,
    EvaluationResult,
    Forecast,
    ForecastStatus,
    NightlyFeatures,
)

# Fixed so a comparator is reproducible between runs, and large enough that the mean
# recall is stable. Neither is a clinical figure.
RANDOM_BASELINE_TRIALS = 100
RANDOM_BASELINE_SEED = 20260901


def _all_time_median(nights: Sequence[NightlyFeatures]) -> float | None:
    """Median resting heart rate over every usable night, or None if there are none."""
    values = [n.rhr_bpm for n in nights if n.usable and n.rhr_bpm is not None]
    return float(np.median(values)) if values else None


def _alerts_to_detections(
    subject_id: str,
    nights: Sequence[NightlyFeatures],
    alerts: Sequence[bool],
) -> list[Detection]:
    """Attach a comparator's boolean alert series to the nights it was computed over.

    The comparators return plain booleans while the recall metric reads Detections by
    night_date, so the two cannot be connected without this.
    """
    detections: list[Detection] = []
    for night, alerted in zip(nights, alerts, strict=False):
        detections.append(
            Detection(
                subject_id=subject_id,
                night_date=night.night_date,
                level=DetectionLevel.RED if alerted else DetectionLevel.GREEN,
                flagged=bool(alerted),
                residual_bpm=None,
                forecast=Forecast(status=ForecastStatus.NOT_RUN),
            )
        )
    return detections


def run_detection_eval(
    detections_by_participant: dict[str, Sequence[Detection]] | None = None,
    features_by_participant: dict[str, Sequence[NightlyFeatures]] | None = None,
    labels: dict[str, Any] | None = None,
    eval_dir: Path | None = None,
) -> EvaluationResult:
    """Execute the detection benchmark over cohort detections supplied by the caller.

    REFUSES RATHER THAN REPORTING ZEROS. `run_evaluation_suite("detection")` calls this
    with no detections and no features, and always has, so every field it computed was over
    two empty dicts: recall 0.0, lead time 0.0, alerts per user-week 0.0, and
    number_needed_to_evaluate 10000. It printed those as a benchmark result. A command that
    reports measured-looking zeros is worse than one that fails, because failure is
    obviously not a result and 0.0 is not obviously not one.

    The real measurement exists and is reproducible: `experiments/detection/cohort/` replays this system's
    own detector over 8,508 nights of the Mishra 2020 cohort, and the figures it produces
    are published in experiments/detection/. This function stays
    because it is a genuine benchmark harness for a caller that has the data; it just
    refuses to pretend when it does not.
    """
    if not detections_by_participant:
        raise ConfigError(
            "run_detection_eval was given no detections, so there is nothing to score. "
            "This suite scores detections a caller replays; it does not replay them "
            "itself, and nothing in the application does. The measured detection "
            "accuracy comes from tools/cohort:\n"
            "    uv run python experiments/detection/cohort/fetch.py\n"
            "    uv run python experiments/detection/cohort/labels.py\n"
            "    uv run python experiments/detection/cohort/evaluate.py\n"
            "    uv run python experiments/detection/cohort/report.py\n"
            "The published figures are in experiments/detection/."
        )

    cohort_labels = labels if labels is not None else load_cohort_labels()
    stanford_labels = cohort_labels.get("stanford", {})

    target_eval_dir = eval_dir if eval_dir is not None else Path("data/eval")
    target_eval_dir.mkdir(parents=True, exist_ok=True)

    dets = detections_by_participant if detections_by_participant is not None else {}
    feats = features_by_participant if features_by_participant is not None else {}

    # Total episodes and detected episodes
    n_episodes = sum(1 for meta in stanford_labels.values() if meta.get("symptom_onset"))
    recall = evaluate_episode_recall(dets, stanford_labels)
    k_detected = round(recall * n_episodes)
    ci_lower, ci_upper = clopper_pearson_interval(k_detected, n_episodes)

    # Lead times
    leads = calculate_lead_times(dets, stanford_labels)
    median_lead = float(np.median(leads)) if leads else 0.0
    iqr_lead = float(np.percentile(leads, 75) - np.percentile(leads, 25)) if len(leads) > 1 else 0.0

    # False alert rates
    total_non_episode_days = 0
    total_person_days_alerting = 0
    total_false_events = 0
    for p, p_dets in dets.items():
        total_person_days_alerting += sum(1 for d in p_dets if d.flagged)
        total_non_episode_days += len(p_dets)
        events = extract_alert_events(p_dets)
        total_false_events += len(events)

    user_weeks = max(1.0, total_non_episode_days / 7.0)
    events_per_user_week = total_false_events / user_weeks
    fraction_days_alerting = total_person_days_alerting / float(max(1, total_non_episode_days))

    # NNE and prevalence
    prevalence = (
        n_episodes / float(max(1, total_non_episode_days)) if total_non_episode_days > 0 else 0.05
    )
    auprc = max(prevalence, recall * (1.0 - fraction_days_alerting))
    nne = 1.0 / max(1e-4, recall / max(1.0, float(total_false_events + k_detected)))

    # Mandatory baseline 1: trivial detector.
    #
    # Both comparators were previously called with signatures that do not exist:
    # detect_trivial omitted its required all_time_median, and detect_random received the
    # feature list in its positional alert_rate slot with n_days missing. Both also return
    # a boolean series, not Detections, so evaluate_episode_recall could not have read
    # them. The only test omitted features_by_participant, leaving feats empty and the
    # whole branch unexecuted, so the suite reported 0.0 as a measured comparator.
    trivial_dets: dict[str, list[Detection]] = {}
    for p, p_feats in feats.items():
        median = _all_time_median(p_feats)
        if median is None:
            continue
        trivial_dets[p] = _alerts_to_detections(p, p_feats, detect_trivial(p_feats, median))
    trivial_recall = evaluate_episode_recall(trivial_dets, stanford_labels) if trivial_dets else 0.0

    # Mandatory baseline 2: random detector matched on the real detector's alert rate.
    random_recalls: list[float] = []
    if feats:
        rng = random.Random(RANDOM_BASELINE_SEED)
        for _ in range(RANDOM_BASELINE_TRIALS):
            rand_dets = {
                p: _alerts_to_detections(
                    p,
                    p_feats,
                    detect_random(fraction_days_alerting, len(p_feats), rng=rng),
                )
                for p, p_feats in feats.items()
            }
            random_recalls.append(evaluate_episode_recall(rand_dets, stanford_labels))
        matched_random_recall = float(np.mean(random_recalls))
    else:
        matched_random_recall = fraction_days_alerting

    metrics = {
        "episode_recall": round(recall, 4),
        "recall_ci_lower": round(ci_lower, 4),
        "recall_ci_upper": round(ci_upper, 4),
        "lead_time_median_days": round(median_lead, 2),
        "lead_time_iqr_days": round(iqr_lead, 2),
        "events_per_user_week": round(events_per_user_week, 4),
        "fraction_days_alerting": round(fraction_days_alerting, 4),
        "number_needed_to_evaluate": round(nne, 2),
        "auprc": round(auprc, 4),
        "prevalence": round(prevalence, 4),
        "baseline_trivial_recall": round(trivial_recall, 4),
        "baseline_random_recall": round(matched_random_recall, 4),
    }

    caveats = []
    if n_episodes < 50:
        caveats.append(
            f"With N={n_episodes} positive episodes the 95% confidence interval spans "
            f"{(ci_upper - ci_lower) * 100:.1f} percentage points. "
            "Study is powered to establish signal presence, not rank detector variants."
        )

    result = EvaluationResult(
        suite="detection",
        generated_at_utc=now_utc(),
        metrics=metrics,
        tables={
            "contingency": [
                {"total_episodes": n_episodes, "detected": k_detected, "lead_times": leads}
            ]
        },
        figures=[],
        sample_size=n_episodes,
        caveats=caveats,
    )

    out_file = target_eval_dir / "detection.json"
    out_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result
