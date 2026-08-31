"""Chronos foundation model forecast wrapper for resting heart rate."""

import math
import threading
from collections.abc import Sequence
from datetime import timedelta
from typing import Any

from wha.constants import (
    FORECAST_HALF_WIDTH_FLOOR_BPM,
    FORECAST_MIN_NIGHTS,
    FORECAST_Q_HI,
    FORECAST_Q_LO,
)
from wha.models import Forecast, ForecastStatus, NightlyFeatures

_pipeline_lock = threading.Lock()
_cached_pipeline: Any | None = None


def get_chronos_pipeline(model_id: str = "amazon/chronos-bolt-small") -> Any:
    """Load Chronos pipeline once per process behind a thread lock.

    Raises ImportError if the ml dependency group (torch / chronos) is missing.
    """
    global _cached_pipeline
    with _pipeline_lock:
        if _cached_pipeline is not None:
            return _cached_pipeline

        from chronos import ChronosBoltPipeline  # type: ignore

        _cached_pipeline = ChronosBoltPipeline.from_pretrained(
            model_id,
            device_map="cpu",
        )
        return _cached_pipeline


def forecast_night(
    history: Sequence[NightlyFeatures],
    actual_rhr: float | None,
    pipeline: Any | None = None,
) -> Forecast:
    """Produce a one-step-ahead forecast of nocturnal RHR and uncertainty interval.

    Advisory only: never raises into the caller and never sets level or flagged.
    Gaps enter context as NaN without imputation or dropping.
    """
    # 1. Check usable night count
    usable_count = sum(1 for n in history if n.usable and n.rhr_bpm is not None)
    if usable_count < FORECAST_MIN_NIGHTS or actual_rhr is None:
        return Forecast(status=ForecastStatus.TOO_FEW_NIGHTS)

    # 2. Build full calendar series context with NaNs for gaps
    sorted_history = sorted(history, key=lambda n: n.night_date)
    start_date = sorted_history[0].night_date
    end_date = sorted_history[-1].night_date

    date_to_feature = {n.night_date: n for n in sorted_history}
    context: list[float] = []
    curr = start_date
    while curr <= end_date:
        feat = date_to_feature.get(curr)
        if feat is not None and feat.usable and feat.rhr_bpm is not None:
            context.append(float(feat.rhr_bpm))
        else:
            context.append(float("nan"))
        curr += timedelta(days=1)

    # 3. Resolve pipeline
    pipe = pipeline
    if pipe is None:
        try:
            pipe = get_chronos_pipeline()
        except ImportError:
            return Forecast(status=ForecastStatus.NOT_RUN)
        except Exception:  # noqa: BLE001
            return Forecast(status=ForecastStatus.FAILED)

    if pipe is None:
        return Forecast(status=ForecastStatus.NOT_RUN)

    # 4. Predict quantiles
    try:
        if hasattr(pipe, "predict_quantiles"):
            try:
                import torch  # type: ignore

                tensor_ctx = torch.tensor(context, dtype=torch.float32).unsqueeze(0)
                pred_out = pipe.predict_quantiles(
                    context=tensor_ctx,
                    prediction_length=1,
                    quantile_levels=[FORECAST_Q_LO, 0.5, FORECAST_Q_HI],
                )
            except (ImportError, TypeError, AttributeError):
                pred_out = pipe.predict_quantiles(
                    context=context,
                    prediction_length=1,
                    quantile_levels=[FORECAST_Q_LO, 0.5, FORECAST_Q_HI],
                )
        else:
            pred_out = pipe(context)

        # Parse quantile outputs
        if isinstance(pred_out, dict):
            pred_bpm = float(pred_out[0.5])
            lo_bpm = float(pred_out[FORECAST_Q_LO])
            hi_bpm = float(pred_out[FORECAST_Q_HI])
        elif isinstance(pred_out, (list, tuple)) and len(pred_out) >= 3:
            lo_bpm = float(pred_out[0])
            pred_bpm = float(pred_out[1])
            hi_bpm = float(pred_out[2])
        elif hasattr(pred_out, "quantile"):
            pred_bpm = float(pred_out.quantile(0.5)[0, 0])
            lo_bpm = float(pred_out.quantile(FORECAST_Q_LO)[0, 0])
            hi_bpm = float(pred_out.quantile(FORECAST_Q_HI)[0, 0])
        elif hasattr(pred_out, "shape"):
            # Tensor shape (batch, pred_len, num_quantiles)
            lo_bpm = float(pred_out[0, 0, 0])
            pred_bpm = float(pred_out[0, 0, 1])
            hi_bpm = float(pred_out[0, 0, 2])
        else:
            return Forecast(status=ForecastStatus.FAILED)

        # Verify finite values
        if any(math.isnan(v) or math.isinf(v) for v in (pred_bpm, lo_bpm, hi_bpm)):
            return Forecast(status=ForecastStatus.FAILED)

        half_width = max((hi_bpm - lo_bpm) / 2.0, FORECAST_HALF_WIDTH_FLOOR_BPM)
        forecast_z = (actual_rhr - pred_bpm) / half_width

        if math.isnan(forecast_z) or math.isinf(forecast_z):
            return Forecast(status=ForecastStatus.FAILED)

        return Forecast(
            predicted_bpm=round(pred_bpm, 3),
            lo_bpm=round(lo_bpm, 3),
            hi_bpm=round(hi_bpm, 3),
            forecast_z=round(forecast_z, 3),
            status=ForecastStatus.OK,
        )
    except Exception:  # noqa: BLE001
        return Forecast(status=ForecastStatus.FAILED)
