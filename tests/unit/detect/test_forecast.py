"""Unit tests for Chronos forecast wrapper and stub pipeline integration."""

import math
from datetime import date, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

from wha.constants import FORECAST_HALF_WIDTH_FLOOR_BPM
from wha.detect import (
    compute_baseline,
    compute_detection_for_features,
    forecast_night,
)
from wha.models import (
    DetectionLevel,
    Forecast,
    ForecastStatus,
    NightlyFeatures,
)


def _make_night(d: int, rhr: float | None = 60.0, usable: bool = True) -> NightlyFeatures:
    return NightlyFeatures(
        subject_id="subj_fc",
        night_date=date(2026, 9, 1) + timedelta(days=d),
        rhr_bpm=rhr,
        coverage_minutes=420 if usable else 0,
        usable=usable,
    )


class StubPipeline:
    """Stub pipeline returning deterministic quantiles."""

    def __init__(
        self,
        q_lo: float = 58.0,
        q_mid: float = 60.0,
        q_hi: float = 62.0,
        raises: bool = False,
        return_nan: bool = False,
    ) -> None:
        self.q_lo = q_lo
        self.q_mid = q_mid
        self.q_hi = q_hi
        self.raises = raises
        self.return_nan = return_nan
        self.received_contexts: list[list[float]] = []

    def predict_quantiles(
        self,
        context: Any,
        prediction_length: int = 1,
        quantile_levels: list[float] | None = None,
    ) -> dict[float, float]:
        if self.raises:
            raise RuntimeError("Stub pipeline simulated runtime failure")

        if hasattr(context, "tolist"):
            ctx_list = context.squeeze().tolist()
        elif isinstance(context, list):
            ctx_list = context
        else:
            ctx_list = list(context)
        self.received_contexts.append(ctx_list)

        if self.return_nan:
            return {0.1: float("nan"), 0.5: float("nan"), 0.9: float("nan")}

        return {0.1: self.q_lo, 0.5: self.q_mid, 0.9: self.q_hi}


def test_too_few_nights_returns_status_not_error() -> None:
    """Fewer than 5 usable nights returns TOO_FEW_NIGHTS without raising."""
    history = [_make_night(i, 60.0) for i in range(4)]
    fc = forecast_night(history, actual_rhr=65.0, pipeline=StubPipeline())
    assert fc.status == ForecastStatus.TOO_FEW_NIGHTS
    assert fc.predicted_bpm is None


def test_forecast_z_computed_from_half_width() -> None:
    """forecast_z is accurately computed as (actual - predicted) / half_width."""
    # lo=58, mid=60, hi=64 -> half_width = (64 - 58) / 2 = 3.0
    # actual = 66.0 -> (66 - 60) / 3.0 = 2.0
    stub = StubPipeline(q_lo=58.0, q_mid=60.0, q_hi=64.0)
    history = [_make_night(i, 60.0) for i in range(10)]
    fc = forecast_night(history, actual_rhr=66.0, pipeline=stub)

    assert fc.status == ForecastStatus.OK
    assert fc.predicted_bpm == 60.0
    assert fc.lo_bpm == 58.0
    assert fc.hi_bpm == 64.0
    assert fc.forecast_z == 2.0


def test_half_width_floor_prevents_infinite_z() -> None:
    """A zero-width interval is floored at FORECAST_HALF_WIDTH_FLOOR_BPM = 1.0."""
    # lo=60, mid=60, hi=60 -> raw half_width = 0.0 -> floored to 1.0
    # actual = 63.0 -> (63 - 60) / 1.0 = 3.0
    stub = StubPipeline(q_lo=60.0, q_mid=60.0, q_hi=60.0)
    history = [_make_night(i, 60.0) for i in range(10)]
    fc = forecast_night(history, actual_rhr=63.0, pipeline=stub)

    assert fc.status == ForecastStatus.OK
    assert fc.forecast_z == 3.0 / FORECAST_HALF_WIDTH_FLOOR_BPM
    assert not math.isinf(fc.forecast_z)


def test_gaps_passed_as_nan_not_dropped() -> None:
    """Calendar gaps enter the context as NaN so total sequence length matches calendar span."""
    # Day 0, Day 1, Day 2, gap on Day 3 & 4, Day 5, Day 6 (5 usable nights over 7 calendar days)
    history = [
        _make_night(0, 60.0, usable=True),
        _make_night(1, 60.0, usable=True),
        _make_night(2, 60.0, usable=True),
        _make_night(3, None, usable=False),
        _make_night(4, None, usable=False),
        _make_night(5, 60.0, usable=True),
        _make_night(6, 60.0, usable=True),
    ]
    stub = StubPipeline()
    fc = forecast_night(history, actual_rhr=60.0, pipeline=stub)

    assert fc.status == ForecastStatus.OK
    assert len(stub.received_contexts) == 1
    ctx = stub.received_contexts[0]
    assert len(ctx) == 7
    assert math.isnan(ctx[3])
    assert math.isnan(ctx[4])
    assert ctx[0] == 60.0


def test_model_failure_returns_failed_status() -> None:
    """Exceptions raised by the model pipeline return FAILED status, never crashing caller."""
    stub = StubPipeline(raises=True)
    history = [_make_night(i, 60.0) for i in range(10)]
    fc = forecast_night(history, actual_rhr=60.0, pipeline=stub)

    assert fc.status == ForecastStatus.FAILED
    assert fc.predicted_bpm is None


def test_non_finite_prediction_returns_failed() -> None:
    """Non-finite predictions (e.g. NaN) result in FAILED status."""
    stub = StubPipeline(return_nan=True)
    history = [_make_night(i, 60.0) for i in range(10)]
    fc = forecast_night(history, actual_rhr=60.0, pipeline=stub)

    assert fc.status == ForecastStatus.FAILED


def test_forecast_never_sets_level_or_flagged() -> None:
    """Advisory forecast never alters deterministic level or flagged assignment."""
    history = [_make_night(i, 60.0) for i in range(28)]
    base = compute_baseline(history)
    tonight_features = _make_night(28, rhr=61.0)  # +1.0 bpm residual -> GREEN

    # Provide an alarming forecast that would indicate extreme anomaly (z = 10.0)
    alarming_fc = Forecast(
        predicted_bpm=50.0,
        lo_bpm=48.0,
        hi_bpm=52.0,
        forecast_z=10.0,
        status=ForecastStatus.OK,
    )

    det = compute_detection_for_features(tonight_features, base, forecast=alarming_fc)
    # Must remain GREEN and unflagged according to the deterministic rule!
    assert det.level == DetectionLevel.GREEN
    assert not det.flagged
    assert det.forecast.forecast_z == 10.0


def test_missing_ml_group_returns_not_run() -> None:
    """Simulated missing ML libraries return NOT_RUN status gracefully."""
    history = [_make_night(i, 60.0) for i in range(10)]
    with patch(
        "wha.detect.forecast.get_chronos_pipeline",
        side_effect=ImportError("No module named 'chronos'"),
    ):
        fc = forecast_night(history, actual_rhr=60.0, pipeline=None)
        assert fc.status == ForecastStatus.NOT_RUN


def test_model_loaded_once() -> None:
    """Chronos pipeline loader caches the loaded instance across invocations."""
    mock_chronos = MagicMock()
    mock_pipeline = StubPipeline()
    mock_chronos.ChronosBoltPipeline.from_pretrained.return_value = mock_pipeline

    with (
        patch("wha.detect.forecast._cached_pipeline", None),
        patch.dict("sys.modules", {"chronos": mock_chronos}),
    ):
        from wha.detect.forecast import get_chronos_pipeline

        p1 = get_chronos_pipeline()
        p2 = get_chronos_pipeline()

        assert p1 is p2
        assert mock_chronos.ChronosBoltPipeline.from_pretrained.call_count == 1
