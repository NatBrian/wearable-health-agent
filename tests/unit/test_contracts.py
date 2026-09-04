"""Tests for contract constants, models, and errors."""

import pytest
from pydantic import ValidationError

from wha import constants, errors, models

CONTRACT_CONSTANTS = [
    "MIN_NOCTURNAL_MINUTES",
    "HR_PLAUSIBLE_MIN_BPM",
    "HR_PLAUSIBLE_MAX_BPM",
    "INGEST_STALE_WARN_HOURS",
    "INGEST_STALE_REFUSE_HOURS",
    "RUNG_COLD_MAX_NIGHTS",
    "RUNG_PRIOR_MAX_NIGHTS",
    "RUNG_SHRINKING_MAX_NIGHTS",
    "RUNG_PERSONAL_MAX_NIGHTS",
    "BASELINE_WINDOW_NIGHTS",
    "SHRINKAGE_PSEUDO_NIGHTS",
    "BASELINE_SCALE_FLOOR_BPM",
    "MAD_TO_SD_FACTOR",
    "POP_PRIOR_RHR_MEAN_BPM",
    "POP_PRIOR_RHR_SD_BPM",
    "DETECT_YELLOW_BPM",
    "DETECT_RED_BPM",
    "DETECT_PERSISTENCE_NIGHTS",
    "EXERCISE_EFFECT_BPM",
    "EXERCISE_LOOKBACK_HOURS",
    "SHORT_SLEEP_HOURS",
    "FORECAST_MODEL",
    "FORECAST_MIN_NIGHTS",
    "FORECAST_Q_LO",
    "FORECAST_Q_HI",
    "FORECAST_HALF_WIDTH_FLOOR_BPM",
    "N_CAUSES",
    "BELIEF_STATE_COUNT",
    "RESIDUAL_OBS_SD_BPM",
    "LEAK_EFFECT_SD_BPM",
    "UTILITY_MISS_ILLNESS",
    "UTILITY_FALSE_ALARM",
    "UTILITY_CORRECT",
    "POLICY_COST_PER_INTERRUPT",
    "INTERRUPTION_BUDGET_PER_WEEK",
    "DEPTH_BUDGET_PER_EPISODE",
    "ANSWER_TIMEOUT_HOURS",
    "MEASUREMENT_TIMEOUT_HOURS",
    "EPISODE_MAX_NIGHTS",
    "EPISODE_MAX_STEPS",
    "MAX_TOOL_CALLS_PER_EPISODE",
    "LLM_MAX_TOKENS_FLOOR",
    "LLM_TIMEOUT_SECONDS",
    "LLM_REPAIR_ATTEMPTS",
    "TEMP_DETERMINISTIC",
    "TEMP_NATURAL",
    "CHUNK_TARGET_TOKENS",
    "RRF_K",
    "RETRIEVE_TOP_K",
    "OUTBOUND_MAX_CHARS",
    "TELEGRAM_CALLBACK_MAX_BYTES",
]


def test_every_contract_constant_exists() -> None:
    """All contract constants exist in constants.py."""
    for name in CONTRACT_CONSTANTS:
        assert hasattr(constants, name), f"Constant {name} is missing from constants.py"


def test_causeid_has_twelve_members() -> None:
    """CauseId has exactly 12 members matching N_CAUSES."""
    assert len(models.CauseId) == 12
    assert len(models.CauseId) == constants.N_CAUSES


def test_models_forbid_extra_fields() -> None:
    """Pydantic models raise ValidationError when given extra unknown fields."""
    with pytest.raises(ValidationError):
        models.Baseline(
            centre_bpm=60.0,
            scale_bpm=3.0,
            usable_nights=14,
            rung=models.BaselineRung.PERSONAL,
            shrink_weight=0.8,
            extra_field="disallowed",
        )


def test_belief_marginals_need_not_sum_to_one() -> None:
    """Belief marginals represent independent probabilities and do not sum to 1."""
    marginals = {
        models.CauseId.INFECTION: 0.8,
        models.CauseId.ALCOHOL: 0.7,
        models.CauseId.EXERTION: 0.1,
        models.CauseId.SLEEP_RESTRICTION: 0.2,
        models.CauseId.STRESS: 0.5,
        models.CauseId.LUTEAL: 0.0,
        models.CauseId.VACCINATION: 0.0,
        models.CauseId.TRAVEL: 0.0,
        models.CauseId.MEDICATION: 0.0,
        models.CauseId.RECOVERY_TAIL: 0.0,
        models.CauseId.SENSOR_ARTIFACT: 0.0,
        models.CauseId.UNEXPLAINED: 0.1,
    }
    belief = models.BeliefState(marginals=marginals, p_illness=0.8)
    assert sum(belief.marginals.values()) > 1.0
    top3 = belief.top(3)
    assert len(top3) == 3
    assert top3[0][0] == models.CauseId.INFECTION


def test_every_error_subclasses_wha_error() -> None:
    """All domain errors subclass WHAError."""
    error_classes = [
        errors.ConfigError,
        errors.SourceUnavailable,
        errors.InsufficientData,
        errors.ValidationFailed,
        errors.LLMUnavailable,
        errors.BudgetExhausted,
        errors.SafetyIntercept,
        errors.PermissionDenied,
        errors.StaleData,
    ]
    for cls in error_classes:
        assert issubclass(cls, errors.WHAError)
        assert issubclass(cls, Exception)


def test_investigate_step_validates_mutual_exclusivity() -> None:
    """InvestigateStep requires exactly one of tool_call or done."""
    with pytest.raises(ValidationError):
        models.InvestigateStep()

    with pytest.raises(ValidationError):
        models.InvestigateStep(
            tool_call=models.ToolCall(
                tool_name="test", args={}, called_at_utc=models.datetime.now()
            ),
            done=models.Done(reason="all done"),
        )
