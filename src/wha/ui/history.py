"""History view rendering night chart with maturing band, episode spans, and night table."""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from wha.models import EpisodeSummary, NightRow
from wha.service.episodes import get_episode, list_episodes
from wha.service.nights import get_night_detail, list_nights
from wha.ui.components.night_chart import render_night_chart
from wha.ui.components.status_strip import render_status_strip

LEVEL_BADGES = {
    "GREEN": "🟢 Normal Baseline",
    "YELLOW": "🟡 Elevated (Investigating)",
    "RED": "🔴 Acute Red-Flag Alert",
    "NA": "⏸️ Non-Wear / Insufficient Data",
}


def render_episode_spans(episodes: list[EpisodeSummary]) -> str | None:
    """Render horizontal clickable episode spans beneath the chart."""
    st.subheader("🏷️ Clinical Investigation Episodes")
    if not episodes:
        st.caption(
            "No episodes recorded for this subject (all nights within normal physiological thresholds)."
        )
        return None

    selected_ep_id = None
    cols = st.columns(min(len(episodes), 4))
    for idx, ep in enumerate(episodes):
        col = cols[idx % len(cols)]
        with col:
            disp = ep.disposition.value if ep.disposition else ep.state.value
            disp_badge = (
                "🩺"
                if "ILLNESS" in disp
                else "🚨"
                if "ESCALATE" in disp
                else "🧘"
                if "BENIGN" in disp
                else "🔍"
            )
            btn_label = f"{disp_badge} Ep {ep.episode_id[:8]} ({disp})\n{ep.opened_on} -> {ep.closed_on or 'now'}"
            if st.button(btn_label, key=f"span_{ep.episode_id}", use_container_width=True):
                selected_ep_id = ep.episode_id
                st.query_params["episode"] = ep.episode_id

    return selected_ep_id


def render_night_table(subject_id: str, nights: list[NightRow]) -> None:
    """Render night table with detailed computation expander."""
    st.subheader("📊 Night-by-Night Physiological Detail")
    if not nights:
        st.info("No nights recorded.")
        return

    table_data = []
    for n in sorted(nights, key=lambda x: x.night_date, reverse=True):
        status_label = LEVEL_BADGES.get(n.level.value, n.level.value)
        table_data.append(
            {
                "Date": n.night_date.isoformat(),
                "Resting HR": f"{n.rhr_bpm:.1f} bpm" if n.rhr_bpm is not None else "-",
                "Deviation": f"{n.deviation_bpm:+.1f} bpm" if n.deviation_bpm is not None else "-",
                "Explained Offset": f"{n.explained_bpm:.1f} bpm",
                "Residual": f"{n.residual_bpm:+.1f} bpm" if n.residual_bpm is not None else "-",
                "Coverage": f"{n.coverage_minutes} min",
                "Clinical Status": status_label,
                "Episode": n.episode_id or "-",
            }
        )

    df_table = pd.DataFrame(table_data)
    st.dataframe(df_table, use_container_width=True)

    with st.expander("🔍 Inspect Full Night Computation & Physiological Breakdown"):
        selected_date_str = st.selectbox(
            "Select a specific night to inspect sensor breakdown:",
            options=[d["Date"] for d in table_data],
            key="history_night_inspect_select",
        )
        if selected_date_str:
            sel_date = date.fromisoformat(selected_date_str)
            detail = get_night_detail(subject_id, sel_date)
            if detail:
                col_a, col_b, col_c = st.columns(3)
                feat = detail.features
                base = detail.baseline
                det = detail.detection
                with col_a:
                    st.metric(
                        "Overnight Resting HR",
                        f"{feat.rhr_bpm:.1f} bpm" if feat.rhr_bpm is not None else "N/A",
                    )
                    st.metric(
                        "Personal Baseline (Median)",
                        f"{base.centre_bpm:.1f} bpm" if base.centre_bpm is not None else "N/A",
                    )
                with col_b:
                    st.metric("Valid Nocturnal Minutes", f"{feat.coverage_minutes} min")
                    st.metric(
                        "Sleep Duration",
                        f"{feat.sleep_duration_seconds // 3600}h {(feat.sleep_duration_seconds % 3600) // 60}m"
                        if feat.sleep_duration_seconds is not None
                        else "N/A",
                    )
                with col_c:
                    st.metric("Post-Exercise Tachycardia Offset", f"{det.explained_bpm:.1f} bpm")
                    st.metric(
                        "Final Residual Deviation",
                        f"{det.residual_bpm:+.1f} bpm" if det.residual_bpm is not None else "N/A",
                    )

                st.markdown("#### Full Raw Computation Output:")
                st.json(detail.model_dump(mode="json"))
            else:
                st.write("Detail not found for selected night.")


def render_history_page(subject_id: str) -> None:
    """Render full History surface."""
    render_status_strip(subject_id)
    st.write("---")

    # Check query param for drill-down episode
    ep_param = st.query_params.get("episode")
    if ep_param:
        ep_detail = get_episode(ep_param)
        if ep_detail:
            from wha.ui.components.episode_panel import render_episode_panel

            if st.button("⬅️ Back to Full History"):
                del st.query_params["episode"]
                st.rerun()
            render_episode_panel(ep_detail)
            return
        st.warning(f"Episode `{ep_param}` not found.")

    from datetime import UTC, datetime

    end_d = datetime.now(UTC).date()
    start_d = end_d - timedelta(days=60)
    nights = list_nights(subject_id, start=start_d, end=end_d)
    episodes = list_episodes(subject_id)

    render_night_chart(nights)
    st.write("---")
    render_episode_spans(episodes)
    st.write("---")
    render_night_table(subject_id, nights)
