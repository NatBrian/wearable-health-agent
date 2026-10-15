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
# recorded in docs/DISCLOSURES.md instead of being hidden. Keeping these as dead names purely to
# satisfy a list would be the exact defect this project keeps producing: something
# defined, referenced, and never reached.
REMOVED_FROM_THE_CODE: dict[str, str] = {
    "FORECAST_MODEL": "Chronos removed 5 September 2026, see experiments/detection/cohort/chronos.py",
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
    names exactly which entries the code no longer honours, and docs/DISCLOSURES.md asks for the
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


# --------------------------------------------------------------- the contract, checked


def _contract() -> str:
    from pathlib import Path

    return (Path(__file__).resolve().parents[2] / "docs" / "CONTRACTS.md").read_text(
        encoding="utf-8"
    )


def _declared_models() -> dict[str, set[str]]:
    """Every `class X(BaseModel):` block in the contract, and the field names in it."""
    import re

    out: dict[str, set[str]] = {}
    current: str | None = None
    fields: set[str] = set()
    for line in _contract().splitlines():
        header = re.match(r"class (\w+)\(BaseModel\):", line)
        if header:
            if current:
                out[current] = fields
            current, fields = header.group(1), set()
            continue
        if current is None:
            continue
        if line and not line.startswith((" ", "\t")):
            out[current] = fields
            current, fields = None, set()
            continue
        for part in line.split("#")[0].split(";"):
            field = re.match(r"([a-z_][a-z0-9_]*)\s*:", part.strip())
            if field:
                fields.add(field.group(1))
    if current:
        out[current] = fields
    return out


def test_the_contract_lists_the_fields_the_models_actually_have() -> None:
    """docs/CONTRACTS.md drifted seven models behind the code before anyone checked.

    It is the file the source cites by name for "every schema, model, field name, enum
    value and constant", and nothing compared it to the code. Two of the seven gaps were
    recorded as blockers; five were not, including NightRow carrying four forecast fields
    for a subsystem that had been deleted and Settings missing llm_base_url.

    A contract nobody checks is a description, not a contract.
    """
    from pydantic import BaseModel

    from wha import models as domain

    problems: list[str] = []
    for name, declared in _declared_models().items():
        model = getattr(domain, name, None)
        if not (isinstance(model, type) and issubclass(model, BaseModel)):
            continue
        actual = set(model.model_fields)
        if declared - actual:
            problems.append(
                f"{name}: contract lists fields the code lacks {sorted(declared - actual)}"
            )
        if actual - declared:
            problems.append(
                f"{name}: code has fields the contract lacks {sorted(actual - declared)}"
            )

    assert not problems, "docs/CONTRACTS.md and wha.models disagree:\n  " + "\n  ".join(problems)


def test_the_contract_lists_the_tables_and_columns_the_schema_actually_has() -> None:
    """Eleven schema disagreements, none of them recorded anywhere.

    Seven whole tables existed and were undescribed, including `subject_profile` and
    `conversation_turns`, which hold the most sensitive rows in the database. That is not
    a documentation problem on its own; it is how `delete_all_subject_data` came to miss
    them, because the hand-written list it used was checked against this file.
    """
    import re
    import sqlite3

    from wha.db.migrations import apply_schema

    conn = sqlite3.connect(":memory:")
    apply_schema(conn)
    real = {
        name: {r[1] for r in conn.execute(f"PRAGMA table_info({name})")}
        for (name,) in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }

    declared: dict[str, set[str]] = {}
    current: str | None = None
    columns: set[str] = set()
    for line in _contract().splitlines():
        header = re.search(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)", line)
        if header:
            if current:
                declared[current] = columns
            current, columns = header.group(1), set()
            continue
        if current is None:
            continue
        if line.strip().startswith(")"):
            declared[current] = columns
            current, columns = None, set()
            continue
        column = re.match(r"\s*([a-z_][a-z0-9_]*)\s+[A-Z]", line)
        if column:
            columns.add(column.group(1))
    if current:
        declared[current] = columns

    # Created by the LangGraph SQLite saver rather than by this project's schema.
    NOT_OURS = {"schema_version", "checkpoints", "writes"}

    problems: list[str] = []
    for table, cols in declared.items():
        if table not in real:
            problems.append(f"{table}: in the contract, not in the schema")
            continue
        if cols - real[table]:
            problems.append(f"{table}: contract-only columns {sorted(cols - real[table])}")
        if real[table] - cols:
            problems.append(f"{table}: schema-only columns {sorted(real[table] - cols)}")
    for table in real:
        if table not in declared and table not in NOT_OURS:
            problems.append(f"{table}: in the schema, not in the contract")

    assert not problems, "docs/CONTRACTS.md and schema.sql disagree:\n  " + "\n  ".join(problems)


def test_the_contract_quotes_the_constant_values_the_code_holds() -> None:
    """POLICY_COST_PER_INTERRUPT read 0.30 here and 0.15 in the code for days.

    It is the price of interrupting a person, it was moved on a measured frontier, and the
    document the source cites by name went on quoting the old figure.
    """
    import re

    from wha import constants

    block = _contract()
    block = block[block.index("## 4. Constants") : block.index("## 5. Storage schema")]

    problems: list[str] = []
    for match in re.finditer(r"^([A-Z][A-Z0-9_]+)\s*=\s*([^#\n]+)", block, re.MULTILINE):
        name, raw = match.group(1), match.group(2).strip().rstrip(",")
        if not hasattr(constants, name):
            problems.append(f"{name}: in the contract, not in constants.py")
            continue
        try:
            declared = eval(raw, {"__builtins__": {}}, {})
        except Exception:  # noqa: BLE001, S112
            # A non-literal declaration, such as a computed expression or a type name.
            # Only literal values can be compared, so the rest are skipped by design.
            continue
        actual = getattr(constants, name)
        if (
            isinstance(declared, (int, float))
            and isinstance(actual, (int, float))
            and abs(float(declared) - float(actual)) > 1e-9
        ):
            problems.append(f"{name}: contract={declared} code={actual}")
    assert not problems, "docs/CONTRACTS.md and constants.py disagree:\n  " + "\n  ".join(problems)


def test_contract_source_labels_match_the_values_the_ui_displays() -> None:
    """A new citation source must be credited consistently on both chat surfaces."""
    import ast
    import re

    from wha.constants import SOURCE_LABEL_PREFIXES

    block = _contract()
    block = block[block.index("## 4. Constants") : block.index("## 5. Storage schema")]
    match = re.search(r"^SOURCE_LABEL_PREFIXES\s*=\s*(\{.*\})$", block, re.MULTILINE)

    assert match is not None, "the constant's display labels are missing from the contract"
    assert ast.literal_eval(match.group(1)) == SOURCE_LABEL_PREFIXES


def test_the_contract_lists_the_dependencies_pyproject_actually_declares() -> None:
    """The contract claimed this project depends on torch and chronos-forecasting.

    Both went with the forecaster on 5 September 2026. The table survived because it was
    the one part of CONTRACTS.md nothing compared against the code, so it also still
    described five dependency groups that had never existed. A new agent reading it would
    have believed the repository ships a neural forecasting stack.

    Every other section of this document is checked. This one now is too.
    """
    import re
    import tomllib
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    declared = {
        "runtime": set(pyproject["project"]["dependencies"]),
        "dev": set(pyproject["dependency-groups"]["dev"]),
    }

    block = _contract()
    block = block[block.index("## 1. Environment") : block.index("## 2. Configuration and secrets")]

    documented: dict[str, set[str]] = {}
    for row in re.finditer(r"^\| (runtime|dev) \| (.+) \|$", block, re.MULTILINE):
        documented[row.group(1)] = set(re.findall(r"`([^`]+)`", row.group(2)))

    problems: list[str] = []
    for group, wanted in declared.items():
        if group not in documented:
            problems.append(f"{group}: no row in the contract table")
            continue
        for missing in sorted(wanted - documented[group]):
            problems.append(f"{group}: {missing} is in pyproject.toml and not in the contract")
        for extra in sorted(documented[group] - wanted):
            problems.append(f"{group}: {extra} is in the contract and not in pyproject.toml")

    assert not problems, "docs/CONTRACTS.md and pyproject.toml disagree:\n  " + "\n  ".join(
        problems
    )
