"""Episode panel component rendering Summary, Trace, Conversation, and Evidence tabs."""

import pandas as pd
import streamlit as st

from wha.models import EpisodeDetail
from wha.ui.components.pipeline_trace import render_pipeline_trace


def render_summary_tab(detail: EpisodeDetail) -> None:
    """Render Tab 1: Episode outcome summary card, differential, and honesty metrics."""
    outcome = detail.outcome
    if not outcome:
        st.info("This episode is currently in progress. Outcome will appear upon conclusion.")
        return

    st.subheader(f"📋 Outcome: `{outcome.disposition.value}`")

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Confidence", outcome.confidence.upper())
    with col2:
        st.metric("Recommended Action", outcome.action.replace("_", " ").title())
    with col3:
        st.metric(
            "Baseline Maturity", f"{outcome.baseline_nights}d ({outcome.baseline_rung.value})"
        )
    with col4:
        st.metric("Unsupported Claims", outcome.unsupported_claims)

    st.markdown("### 📝 Clinical Observation")
    st.info(outcome.observation)

    if outcome.escalation_criteria:
        st.markdown("### 🚨 Escalation Criteria")
        for crit in outcome.escalation_criteria:
            st.warning(f"• {crit}")

    if outcome.differential:
        st.markdown("### 📊 Cause Differential")
        diff_data = []
        for d in outcome.differential:
            diff_data.append(
                {
                    "Cause": d.cause.value,
                    "Probability": d.probability,
                    "Supporting Evidence": "; ".join(d.supporting) or "None",
                    "Contradicting Evidence": "; ".join(d.contradicting) or "None",
                }
            )
        df_diff = pd.DataFrame(diff_data).sort_values("Probability", ascending=False)
        st.bar_chart(df_diff.set_index("Cause")["Probability"])
        st.dataframe(df_diff, use_container_width=True)

    st.caption(
        f"Budget used: {outcome.interruptions_used_this_week} interruptions this week, "
        f"depth {outcome.depth_used_this_episode} questions for this episode."
    )


def render_episode_panel(detail: EpisodeDetail) -> None:
    """Render 4-tab drill-down panel for an episode."""
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Summary", "🔍 Trace", "💬 Conversation", "📚 Evidence"])

    with tab1:
        render_summary_tab(detail)

    with tab2:
        render_pipeline_trace(detail)

    with tab3:
        st.caption("Conversation transcript will render here.")

    with tab4:
        st.caption("Evidence passages and stripped claims will render here.")
