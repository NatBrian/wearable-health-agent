"""Belief chart component for episode belief evolution and marginals."""

from typing import Any

import pandas as pd
import streamlit as st

from wha.models import BeliefState
from wha.ui.components.api import config


def decision_threshold_p_illness() -> float:
    """The testing threshold, derived from the utilities the application holds.

    A function rather than a module constant, because it now comes over HTTP. Computing it
    at import time meant merely importing a screen required a running backend, which broke
    every test that touched the module and would break any tooling that inspected it.
    """
    false_alarm = abs(config()["UTILITY_FALSE_ALARM"])
    miss = abs(config()["UTILITY_MISS_ILLNESS"])
    return false_alarm / (false_alarm + miss)


def build_belief_evolution_data(
    belief_history: list[tuple[int, str, BeliefState]],
) -> pd.DataFrame:
    """Build DataFrame tracking per-cause marginal probabilities and p_illness across update steps.

    NOTE: The marginal probabilities are independent and DO NOT sum to 1.0.
    """
    rows = []
    for seq, trigger, state in belief_history:
        row: dict[str, Any] = {
            "seq": seq,
            "step": f"Step {seq}: {trigger}",
            "trigger": trigger,
            "p_illness": state.p_illness,
            "decision_threshold": decision_threshold_p_illness(),
        }
        for cause, prob in state.marginals.items():
            row[f"P({cause.value})"] = prob
        rows.append(row)

    return pd.DataFrame(rows)


def render_belief_evolution(belief_history: list[tuple[int, str, BeliefState]]) -> None:
    """Render belief state evolution chart with explicit marginals labeling."""
    st.subheader("🧠 Belief Evolution & Decision Trajectory")
    st.caption(
        "Axis shows independent marginal probabilities P(cause ∈ active) — does not sum to 1.0."
    )

    if not belief_history:
        st.info("No belief update steps recorded for this episode.")
        return

    df = build_belief_evolution_data(belief_history)
    st.line_chart(df.set_index("step")[["p_illness", "decision_threshold"]])

    with st.expander("View Full Marginal History"):
        st.dataframe(df, use_container_width=True)
