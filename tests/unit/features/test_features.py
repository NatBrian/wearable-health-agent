"""Unit tests for nocturnal window and resting heart rate derivation."""

from datetime import UTC, date, datetime, timedelta

from wha.constants import MIN_NOCTURNAL_MINUTES
from wha.features import compute_nocturnal_rhr, nocturnal_rhr, nocturnal_window
from wha.models import HeartRateSample


def test_window_uses_subject_timezone() -> None:
    """Asia/Singapore (UTC+8) produces 16:00Z (prior day) to 23:00Z bounds for 00:00-07:00 local."""
    night = date(2026, 9, 2)
    start_utc, end_utc = nocturnal_window(night, "Asia/Singapore")

    assert start_utc == datetime(2026, 9, 1, 16, 0, 0, tzinfo=UTC)
    assert end_utc == datetime(2026, 9, 1, 23, 0, 0, tzinfo=UTC)


def test_window_handles_dst_transition() -> None:
    """Zone with DST transition produces exact local 00:00 to 07:00 bounds in UTC."""
    # America/New_York DST start in March 2026: 2026-03-08
    night = date(2026, 3, 8)
    start_utc, end_utc = nocturnal_window(night, "America/New_York")

    # Local 00:00 is EST (-5h -> 05:00 UTC), Local 07:00 is EDT (-4h -> 11:00 UTC)
    assert start_utc == datetime(2026, 3, 8, 5, 0, 0, tzinfo=UTC)
    assert end_utc == datetime(2026, 3, 8, 11, 0, 0, tzinfo=UTC)


def test_rhr_is_median_not_mean() -> None:
    """Median RHR is robust against high motion artifact spikes."""
    start = datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC)
    samples = [
        HeartRateSample(
            ts_utc=start + timedelta(minutes=i),
            avg_bpm=60.0,
        )
        for i in range(200)
    ]
    # Add a massive motion artifact spike
    samples.append(HeartRateSample(ts_utc=start + timedelta(minutes=201), avg_bpm=180.0))

    rhr = nocturnal_rhr(samples)
    assert rhr is not None
    assert abs(rhr - 60.0) < 0.5


def test_implausible_values_dropped_and_counted() -> None:
    """Values <25 bpm or >220 bpm are excluded from RHR and counted in implausible_dropped."""
    start = datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC)
    samples = [
        HeartRateSample(ts_utc=start, avg_bpm=60.0),
        HeartRateSample(ts_utc=start + timedelta(minutes=1), avg_bpm=10.0),  # implausible low
        HeartRateSample(ts_utc=start + timedelta(minutes=2), avg_bpm=300.0),  # implausible high
    ]

    rhr, coverage, dropped, _ = compute_nocturnal_rhr(samples)
    assert rhr == 60.0
    assert dropped == 2
    assert coverage == 1


def test_coverage_counts_distinct_minutes() -> None:
    """Multiple samples in the same minute count as 1 minute of coverage."""
    start = datetime(2026, 9, 1, 0, 0, 10, tzinfo=UTC)
    samples = [
        HeartRateSample(ts_utc=start, avg_bpm=60.0),
        HeartRateSample(ts_utc=start + timedelta(seconds=20), avg_bpm=62.0),
        HeartRateSample(ts_utc=start + timedelta(seconds=40), avg_bpm=61.0),
    ]
    _, coverage, _, _ = compute_nocturnal_rhr(samples)
    assert coverage == 1


def test_below_min_coverage_is_not_usable() -> None:
    """Coverage below MIN_NOCTURNAL_MINUTES marks usable = False."""
    start = datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC)
    samples = [
        HeartRateSample(ts_utc=start + timedelta(minutes=i), avg_bpm=60.0)
        for i in range(MIN_NOCTURNAL_MINUTES - 1)
    ]
    _, coverage, _, usable = compute_nocturnal_rhr(samples)
    assert coverage == MIN_NOCTURNAL_MINUTES - 1
    assert usable is False


def test_at_min_coverage_is_usable() -> None:
    """Coverage exactly at MIN_NOCTURNAL_MINUTES marks usable = True."""
    start = datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC)
    samples = [
        HeartRateSample(ts_utc=start + timedelta(minutes=i), avg_bpm=60.0)
        for i in range(MIN_NOCTURNAL_MINUTES)
    ]
    _, coverage, _, usable = compute_nocturnal_rhr(samples)
    assert coverage == MIN_NOCTURNAL_MINUTES
    assert usable is True


def test_no_samples_returns_none_not_zero() -> None:
    """Empty samples list produces rhr_bpm = None and usable = False, never 0.0."""
    rhr, coverage, dropped, usable = compute_nocturnal_rhr([])
    assert rhr is None
    assert coverage == 0
    assert dropped == 0
    assert usable is False


def test_gap_is_not_interpolated() -> None:
    """Gaps between observations are preserved and never imputed."""
    start = datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC)
    # Samples in first hour and last hour only
    samples = [
        HeartRateSample(ts_utc=start + timedelta(minutes=i), avg_bpm=60.0) for i in range(30)
    ] + [
        HeartRateSample(ts_utc=start + timedelta(minutes=300 + i), avg_bpm=60.0) for i in range(30)
    ]
    _, coverage, _, usable = compute_nocturnal_rhr(samples)
    assert coverage == 60
    assert usable is False  # 60 < 180 min
