"""Evidence log-likelihood factors for residual, sensors, answers, and measurements."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from wha.belief.states import CAUSE_ORDER, PRESENT
from wha.constants import (
    MIN_NOCTURNAL_MINUTES,
    SHORT_SLEEP_HOURS,
)
from wha.models import (
    Answer,
    CauseId,
    NightlyFeatures,
)

_probes_cache: dict[str, Any] | None = None


def load_probes_raw(path: Path | str | None = None) -> dict[str, Any]:
    """Load raw probe definitions and likelihood tables."""
    global _probes_cache
    if _probes_cache is not None and path is None:
        return _probes_cache

    probe_file = Path(path) if path is not None else Path("data/knowledge/probes.yaml")
    if not probe_file.exists():
        return {}

    content = probe_file.read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    probes_list = data.get("probes", [])
    result = {p["probe_id"]: p for p in probes_list if isinstance(p, dict) and "probe_id" in p}
    if path is None:
        _probes_cache = result
    return result


def compute_exercise_logfactor(features: Sequence[NightlyFeatures]) -> np.ndarray | None:
    """Recorded workouts reduce prior probability of additional unrecorded exertion."""
    has_recorded_workout = any(f.exercise_end_offset_h is not None for f in features)
    if not has_recorded_workout:
        return None

    idx = CAUSE_ORDER.index(CauseId.EXERTION)
    # Penalize exertion states by log(0.15 / 0.85) roughly -1.7
    return PRESENT[:, idx] * (-1.7) + (~PRESENT[:, idx]) * 0.2


def compute_sleep_logfactor(features: Sequence[NightlyFeatures]) -> np.ndarray | None:
    """Short sleep (<6h) is evidence for sleep restriction; normal sleep is weak evidence against."""
    usable_sleep = [f.sleep_hours for f in features if f.sleep_hours is not None]
    if not usable_sleep:
        return None

    latest_sleep = usable_sleep[-1]
    idx = CAUSE_ORDER.index(CauseId.SLEEP_RESTRICTION)
    if latest_sleep < SHORT_SLEEP_HOURS:
        return PRESENT[:, idx] * 1.2 + (~PRESENT[:, idx]) * (-0.4)
    elif latest_sleep >= 7.0:
        return PRESENT[:, idx] * (-0.6) + (~PRESENT[:, idx]) * 0.1
    return None


def compute_coverage_logfactor(features: Sequence[NightlyFeatures]) -> np.ndarray | None:
    """Low coverage or many dropped implausible values is evidence for sensor artifact."""
    has_bad_coverage = any(
        f.implausible_dropped > 0 or f.coverage_minutes < MIN_NOCTURNAL_MINUTES for f in features
    )
    if not has_bad_coverage:
        return None

    idx = CAUSE_ORDER.index(CauseId.SENSOR_ARTIFACT)
    return PRESENT[:, idx] * 1.5 + (~PRESENT[:, idx]) * (-0.3)


def compute_answer_logfactor(
    answer: Answer | dict[str, Any],
    probes_map: dict[str, Any] | None = None,
) -> np.ndarray | None:
    """Compute likelihood update factor from a user's answer to a probe."""
    if isinstance(answer, dict):
        probe_id = str(answer.get("probe_id"))
        option_id = answer.get("option_id")
        declined = bool(answer.get("declined", False))
    else:
        probe_id = answer.probe_id
        option_id = answer.option_id
        declined = answer.declined

    if declined or option_id is None:
        return None

    p_map = probes_map if probes_map is not None else load_probes_raw()
    probe_def = p_map.get(probe_id)
    if not probe_def:
        return None

    target_cause_str = probe_def.get("target_cause")
    try:
        target_cause = CauseId(str(target_cause_str))
    except ValueError:
        return None

    if target_cause not in CAUSE_ORDER:
        return None

    idx = CAUSE_ORDER.index(target_cause)
    lik = probe_def.get("likelihood", {})
    p_pres_dict = lik.get("present", {})
    p_abs_dict = lik.get("absent", {})

    p_pres = float(p_pres_dict.get(str(option_id), 0.5))
    p_abs = float(p_abs_dict.get(str(option_id), 0.5))

    # Guard against 0 probability
    p_pres = max(p_pres, 1e-6)
    p_abs = max(p_abs, 1e-6)

    return PRESENT[:, idx] * np.log(p_pres) + (~PRESENT[:, idx]) * np.log(p_abs)
