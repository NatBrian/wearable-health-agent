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


# Constants docs/CONTRACTS.md still lists that the code deliberately no longer has.
#
# The contract is read-only, so it cannot be amended here, and the disagreement is
# recorded in BLOCKERS.md instead of being hidden. Keeping these as dead names purely to
# satisfy a list would be the exact defect this project keeps producing: something
# defined, referenced, and never reached.
REMOVED_FROM_THE_CODE: dict[str, str] = {
    "FORECAST_MODEL": "Chronos removed 5 September 2026, see tools/cohort/chronos.py",
    "FORECAST_MIN_NIGHTS": "same",
    "FORECAST_Q_LO": "same",
    "FORECAST_Q_HI": "same",
    "FORECAST_HALF_WIDTH_FLOOR_BPM": "same",
}


def test_every_contract_constant_exists() -> None:
    """All contract constants exist in constants.py."""
    for name in CONTRACT_CONSTANTS:
        assert hasattr(constants, name), f"Constant {name} is missing from constants.py"


def test_the_only_missing_contract_constants_are_the_ones_deliberately_removed() -> None:
    """The disagreement with the contract is enumerated, not silent.

    Chronos was removed on a measurement: over 7,295 nights it separated illness worse
    than the residual the detector already computes, AUC 0.586 against 0.629. Its five
    constants went with it. docs/CONTRACTS.md still lists them and is read-only, so this
    names exactly which entries the code no longer honours, and BLOCKERS.md asks for the
    amendment.
    """
    for name in REMOVED_FROM_THE_CODE:
        assert not hasattr(constants, name), (
            f"{name} is back in constants.py. If Chronos returned, restore it to "
            "CONTRACT_CONSTANTS and delete it from this list."
        )


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


def test_every_cli_command_the_readme_shows_actually_exists() -> None:
    """The README's command reference drifted from the CLI in both directions.

    It advertised `wha data fetch stanford` and `wha data fetch chronos` for things that no
    longer fetch anything, and omitted `tell`, `corpus` and `llm` entirely. A reader
    following it hit commands that did nothing and never learned about the ones that work.

    This reads the top-level command names out of the Typer app and checks every
    `uv run wha <x>` in the README against them, so adding a command without documenting it
    is fine, but documenting one that does not exist is not.
    """
    import re
    from pathlib import Path

    from wha.cli import app

    registered = {
        info.name or (info.callback.__name__ if info.callback else "")
        for info in list(app.registered_commands)
    }
    for group in app.registered_groups:
        if group.name:
            registered.add(group.name)
    registered = {name for name in registered if name}
    assert len(registered) > 5, f"only found {registered}, this test would prove nothing"

    readme = (Path(__file__).resolve().parents[2] / "README.md").read_text(encoding="utf-8")

    unknown: list[str] = []
    for match in re.finditer(r"^uv run wha ([a-z-]+)", readme, re.MULTILINE):
        name = match.group(1)
        if name not in registered:
            unknown.append(name)

    assert not unknown, (
        f"README documents commands the CLI does not have: {sorted(set(unknown))}. "
        f"Registered: {sorted(registered)}"
    )
