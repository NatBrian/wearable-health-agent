"""Explained-variance subtraction for automatically recorded physical events."""

from wha.constants import EXERCISE_EFFECT_BPM, EXERCISE_LOOKBACK_HOURS
from wha.models import NightlyFeatures


def explained_bpm(features: NightlyFeatures) -> tuple[float, list[str]]:
    """Calculate resting heart rate deviation accounted for by recorded events.

    Only automatically recorded exercise sessions within EXERCISE_LOOKBACK_HOURS are
    subtracted. Short sleep, alcohol, and stress are never subtracted here.

    Returns:
        (explained_bpm_total, reasons_list)
    """
    offset_h = features.exercise_end_offset_h
    if offset_h is None or offset_h < 0.0 or offset_h > EXERCISE_LOOKBACK_HOURS:
        return 0.0, []

    if 0.0 <= offset_h < 2.0:
        effect = EXERCISE_EFFECT_BPM["0-2h"]
    elif 2.0 <= offset_h < 4.0:
        effect = EXERCISE_EFFECT_BPM["2-4h"]
    elif 4.0 <= offset_h <= 6.0:
        effect = EXERCISE_EFFECT_BPM["4-6h"]
    else:
        return 0.0, []

    reason = f"exercise ended {offset_h}h before the window, -{effect} bpm (Leota 2025)"
    return float(effect), [reason]
