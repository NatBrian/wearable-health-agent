"""Statistical evaluation metrics, Clopper-Pearson intervals, and cluster bootstrap."""

import random
from collections.abc import Callable, Sequence
from datetime import date, timedelta
from typing import Any

import numpy as np
import scipy.stats

from wha.models import Detection


def clopper_pearson_interval(k: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Exact Clopper-Pearson binomial confidence interval."""
    if n <= 0:
        return 0.0, 1.0
    if k <= 0:
        lower = 0.0
    else:
        lower = float(scipy.stats.beta.ppf((1.0 - confidence) / 2.0, k, n - k + 1))

    if k >= n:
        upper = 1.0
    else:
        upper = float(scipy.stats.beta.ppf(1.0 - (1.0 - confidence) / 2.0, k + 1, n - k))

    return round(lower, 4), round(upper, 4)


def extract_alert_events(
    detections: Sequence[Detection],
    min_run_length: int = 2,
) -> list[tuple[date, date]]:
    """Extract maximal runs of consecutive flagged days >= min_run_length.

    Returns list of (start_date, end_date) tuples for each event.
    """
    sorted_dets = sorted(detections, key=lambda d: d.night_date)
    events: list[tuple[date, date]] = []
    current_run: list[date] = []

    for det in sorted_dets:
        if det.flagged:
            if not current_run:
                current_run.append(det.night_date)
            else:
                prev = current_run[-1]
                if (det.night_date - prev).days == 1:
                    current_run.append(det.night_date)
                else:
                    if len(current_run) >= min_run_length:
                        events.append((current_run[0], current_run[-1]))
                    current_run = [det.night_date]
        else:
            if len(current_run) >= min_run_length:
                events.append((current_run[0], current_run[-1]))
            current_run = []

    if len(current_run) >= min_run_length:
        events.append((current_run[0], current_run[-1]))

    return events


def cluster_bootstrap_ci(
    participant_data: dict[str, Any],
    metric_fn: Callable[[dict[str, Any]], float],
    n_resamples: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
) -> tuple[float, float]:
    """Non-parametric cluster bootstrap resampling participants (never days)."""
    participants = list(participant_data.keys())
    if not participants:
        return 0.0, 0.0

    rng = random.Random(seed)
    n = len(participants)
    scores: list[float] = []

    for _ in range(n_resamples):
        resampled_keys = [rng.choice(participants) for _ in range(n)]
        # Map to synthetic resampled participant dictionary
        sample_dict = {f"sample_{i}_{p}": participant_data[p] for i, p in enumerate(resampled_keys)}
        val = metric_fn(sample_dict)
        scores.append(val)

    alpha = 1.0 - confidence
    lower = float(np.percentile(scores, alpha / 2.0 * 100))
    upper = float(np.percentile(scores, (1.0 - alpha / 2.0) * 100))
    return round(lower, 4), round(upper, 4)


def permutation_test_null(
    detections_by_participant: dict[str, Sequence[Detection]],
    labels_by_participant: dict[str, dict[str, Any]],
    n_permutations: int = 1000,
    seed: int = 42,
) -> float:
    """Permute symptom onset dates to establish null recall distribution."""
    rng = random.Random(seed)
    actual_recall = evaluate_episode_recall(detections_by_participant, labels_by_participant)

    null_recalls: list[float] = []
    for _ in range(n_permutations):
        permuted_labels: dict[str, dict[str, Any]] = {}
        for p, meta in labels_by_participant.items():
            dets = detections_by_participant.get(p, [])
            if not dets or not meta.get("symptom_onset"):
                permuted_labels[p] = meta
                continue
            all_dates = [d.night_date for d in dets]
            random_onset = rng.choice(all_dates)
            permuted_labels[p] = {**meta, "symptom_onset": random_onset.isoformat()}

        r = evaluate_episode_recall(detections_by_participant, permuted_labels)
        null_recalls.append(r)

    p_value = sum(1 for nr in null_recalls if nr >= actual_recall) / float(len(null_recalls))
    return round(p_value, 4)


def evaluate_episode_recall(
    detections_by_participant: dict[str, Sequence[Detection]],
    labels_by_participant: dict[str, dict[str, Any]],
    persistence_nights: int = 2,
    l_max: int = 7,
) -> float:
    """Compute fraction of illness episodes detected in [onset - L_max, onset + 1]."""
    total_episodes = 0
    detected_episodes = 0

    for p, meta in labels_by_participant.items():
        if not meta.get("covid_positive") and not meta.get("is_illness"):
            continue
        onset_str = meta.get("symptom_onset")
        if not onset_str:
            continue

        onset_d = date.fromisoformat(onset_str) if isinstance(onset_str, str) else onset_str
        total_episodes += 1

        window_start = onset_d - timedelta(days=l_max)
        window_end = onset_d + timedelta(days=1)

        dets = detections_by_participant.get(p, [])
        events = extract_alert_events(dets, min_run_length=persistence_nights)

        # Detected iff FIRST day of at least one alert event is in [onset - l_max, onset + 1]
        is_detected = any(window_start <= ev[0] <= window_end for ev in events)
        if is_detected:
            detected_episodes += 1

    if total_episodes == 0:
        return 0.0
    return detected_episodes / float(total_episodes)


def calculate_lead_times(
    detections_by_participant: dict[str, Sequence[Detection]],
    labels_by_participant: dict[str, dict[str, Any]],
    persistence_nights: int = 2,
    l_max: int = 7,
) -> list[int]:
    """Calculate lead time (onset - first_alert) in days for detected episodes."""
    lead_times: list[int] = []
    for p, meta in labels_by_participant.items():
        onset_str = meta.get("symptom_onset")
        if not onset_str:
            continue
        onset_d = date.fromisoformat(onset_str) if isinstance(onset_str, str) else onset_str
        window_start = onset_d - timedelta(days=l_max)
        window_end = onset_d + timedelta(days=1)

        dets = detections_by_participant.get(p, [])
        events = extract_alert_events(dets, min_run_length=persistence_nights)
        qualifying = [ev[0] for ev in events if window_start <= ev[0] <= window_end]
        if qualifying:
            first_alert = min(qualifying)
            lead_times.append((onset_d - first_alert).days)

    return lead_times
