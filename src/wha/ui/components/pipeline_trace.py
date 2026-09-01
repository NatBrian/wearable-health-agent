"""Pipeline trace component rendering ordered execution stages, skipped reasons, and tool calls."""

import streamlit as st

from wha.models import EpisodeDetail, StageStatus
from wha.ui.components.belief_chart import render_belief_evolution

STAGE_ICONS = {
    StageStatus.RAN: "✅",
    StageStatus.SKIPPED: "⏭️",
    StageStatus.FAILED: "❌",
    StageStatus.PENDING: "⏳",
}


def render_pipeline_trace(detail: EpisodeDetail) -> None:
    """Render full execution trace of the episode, including skipped stages and tool calls."""
    st.subheader("🔍 Execution Trace")
    st.caption(
        "All stages in canonical execution order. Skipped stages are shown with full rationale."
    )

    for stage in detail.stages:
        icon = STAGE_ICONS.get(stage.status, "•")
        dur_str = f"({stage.duration_ms}ms)" if stage.duration_ms is not None else ""
        header = f"{icon} **{stage.name}** — `{stage.status.value}` {dur_str}"
        st.markdown(header)
        st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;*Reason:* {stage.reason}")

        # Details and Tool Calls expander
        if stage.detail_json:
            with st.expander(f"Details: {stage.name}"):
                if stage.name == "investigate" and "tool_calls" in stage.detail_json:
                    st.markdown("**🔧 Individual T1 Tool Calls Chosen at Runtime:**")
                    tool_calls = stage.detail_json["tool_calls"]
                    for idx, tc in enumerate(tool_calls):
                        st.markdown(
                            f"**{idx + 1}. `{tc.get('tool_name')}`** "
                            f"(Source: `{tc.get('source_ref')}`, Freshness: `{tc.get('freshness', 'current')}`)"
                        )
                        st.json(tc.get("arguments", {}))
                        if "result" in tc:
                            st.caption("Result:")
                            st.write(tc["result"])
                else:
                    st.json(stage.detail_json)

    st.write("---")
    render_belief_evolution(detail.belief_history)
