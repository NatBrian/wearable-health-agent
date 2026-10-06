"""Configuration that the browser dashboard needs to explain the running system."""

from typing import Any

from pydantic import BaseModel

from wha.clock import local_today
from wha.config import get_settings
from wha.constants import (
    DASHBOARD_STEPS_AVERAGE_DAYS,
    HISTORY_WINDOW_DAYS,
    POLICY_COST_WEIGHT_UI_STEP,
)
from wha.models import SettingsPatch, SubjectProfilePatch


def get_dashboard_configuration() -> dict[str, Any]:
    """Return public operating values, date and editable-field bounds."""
    from wha import constants

    exported: dict[str, Any] = {}
    for name in dir(constants):
        if not name.isupper():
            continue
        value = getattr(constants, name)
        if isinstance(value, str | int | float | bool | list | dict | type(None)):
            exported[name] = value

    exported["today"] = local_today().isoformat()
    exported["configured_subject"] = get_settings().subject
    exported["dashboard"] = {
        "history_windows_days": HISTORY_WINDOW_DAYS,
        "steps_average_days": DASHBOARD_STEPS_AVERAGE_DAYS,
        "cause_combinations": 2**constants.N_CAUSES,
        "settings_bounds": {
            "age_years": _numeric_bounds(SubjectProfilePatch, "age_years"),
            "interruption_budget_per_week": _numeric_bounds(
                SettingsPatch, "interruption_budget_per_week"
            ),
            "depth_budget_per_episode": _numeric_bounds(SettingsPatch, "depth_budget_per_episode"),
            "policy_cost_weight": {
                **_numeric_bounds(SettingsPatch, "policy_cost_weight"),
                "step": POLICY_COST_WEIGHT_UI_STEP,
            },
        },
    }
    return exported


def _numeric_bounds(model: type[BaseModel], field_name: str) -> dict[str, int | float | None]:
    """Read optional numeric input bounds from the Pydantic contract."""
    field_schema = model.model_json_schema()["properties"][field_name]
    if "anyOf" in field_schema:
        field_schema = next(
            branch for branch in field_schema["anyOf"] if branch.get("type") != "null"
        )
    return {
        "minimum": field_schema.get("minimum"),
        "maximum": field_schema.get("maximum"),
    }
