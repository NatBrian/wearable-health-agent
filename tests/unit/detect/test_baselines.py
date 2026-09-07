"""Unit tests for mandatory comparator baselines: random and trivial detectors."""

import random

from wha.detect import detect_random, detect_trivial


def test_random_baseline_matches_alert_rate() -> None:
    """Random detector produces an empirical alert rate close to the target over large samples."""
    target_rate = 0.05
    n_days = 20_000
    rng = random.Random(42)

    alerts = detect_random(target_rate, n_days, rng)
    empirical_rate = sum(alerts) / n_days

    assert len(alerts) == n_days
    assert abs(empirical_rate - target_rate) < 0.005


def test_trivial_baseline_is_implemented() -> None:
    """Trivial detector alerts when RHR exceeds all-time median by at least DETECT_RED_BPM (4.0)."""
    all_time_median = 60.0
    rhrs = [58.0, 60.0, 63.9, 64.0, 65.0, None]
    alerts = detect_trivial(rhrs, all_time_median)

    # 58.0 (<64.0) -> False
    # 60.0 (<64.0) -> False
    # 63.9 (<64.0) -> False
    # 64.0 (>=64.0) -> True
    # 65.0 (>=64.0) -> True
    # None -> False
    assert alerts == [False, False, False, True, True, False]
