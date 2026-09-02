"""History: how your nights have looked, and what was looked into.

Column headings and badges name what a reading means to the person rather than what
the field is called in the database. The raw computation stays available underneath
for anyone who wants to check it.
"""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from wha.clock import local_today
from wha.models import EpisodeSummary, NightRow
from wha.service.episodes import get_episode, list_episodes
from wha.service.nights import get_night_detail, list_nights
from wha.service.status import get_system_status
from wha.ui.components.night_chart import render_night_chart
from wha.ui.components.status_strip import render_status_strip
from wha.ui.components.wording import (
    disposition_phrase,
    episode_state_phrase,
    level_phrase,
)

LEVEL_ICONS = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴", "NA": "⏸️"}


def render_episode_spans(episodes: list[EpisodeSummary]) -> str | None:
    """Render horizontal clickable episode spans beneath the chart."""
    st.subheader("Investigations")
    st.caption(
        "An investigation opens when a raised reading persists for more than one night. "
        "Most nights never open one."
    )
    if not episodes:
        # This claimed every night sat inside the band. The band is two-sided and the
        # system only investigates elevation, so a person whose nights run below it was
        # told something plainly contradicted by the chart directly above.
        st.caption("None so far. No night has been raised for long enough to look into.")
        return None

    selected_ep_id = None
    cols = st.columns(min(len(episodes), 4))
    for idx, ep in enumerate(episodes):
        col = cols[idx % len(cols)]
        with col:
            if ep.disposition is not None:
                phrase = disposition_phrase(ep.disposition)
                icon = (
                    "🚨"
                    if ep.disposition.value == "ESCALATED"
                    else "🩺"
                    if ep.disposition.value == "LIKELY_ILLNESS"
                    else "🧘"
                )
            else:
                phrase = episode_state_phrase(ep.state)
                icon = "🔍"
            ended = ep.closed_on.isoformat() if ep.closed_on else "ongoing"
            btn_label = f"{icon} {phrase.label}\n{ep.opened_on} to {ended}"
            if st.button(btn_label, key=f"span_{ep.episode_id}", use_container_width=True):
                selected_ep_id = ep.episode_id
                st.query_params["episode"] = ep.episode_id

    return selected_ep_id


def render_night_table(subject_id: str, nights: list[NightRow]) -> None:
    """Render night table with detailed computation expander."""
    st.subheader("Night by night")
    if not nights:
        st.info("No nights recorded yet.")
        return

    table_data = []
    for n in sorted(nights, key=lambda x: x.night_date, reverse=True):
        phrase = level_phrase(n.level)
        icon = LEVEL_ICONS.get(n.level.value, "")
        table_data.append(
            {
                "Night": n.night_date.isoformat(),
                "How it looked": f"{icon} {phrase.label}",
                "Resting heart rate": f"{n.rhr_bpm:.1f} bpm" if n.rhr_bpm is not None else "-",
                "vs your usual": (
                    f"{n.deviation_bpm:+.1f} bpm" if n.deviation_bpm is not None else "-"
                ),
                "Explained by activity": f"{n.explained_bpm:.1f} bpm",
                "Left unexplained": (
                    f"{n.residual_bpm:+.1f} bpm" if n.residual_bpm is not None else "-"
                ),
                "Measured over": f"{n.coverage_minutes} min",
                "Investigation": "yes" if n.episode_id else "-",
            }
        )

    df_table = pd.DataFrame(table_data)
    st.dataframe(df_table, use_container_width=True)
    st.caption(
        "'Left unexplained' is the column that matters. It is how far the night sat "
        "above your usual after subtracting what a recorded workout or a short night's "
        "sleep would be expected to add."
    )

    with st.expander("Look at one night in detail"):
        selected_date_str = st.selectbox(
            "Which night",
            # The column is "Night". This read said "Date", so opening the History page
            # raised KeyError for any subject with any nights. Nothing in the test suite
            # rendered this page, so a guaranteed crash sat here while every test passed.
            options=[d["Night"] for d in table_data],
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
                        "Resting heart rate",
                        f"{feat.rhr_bpm:.1f} bpm" if feat.rhr_bpm is not None else "n/a",
                    )
                    st.caption("Measured between midnight and 7am.")
                    st.metric(
                        "Your usual for this period",
                        f"{base.centre_bpm:.1f} bpm" if base.centre_bpm is not None else "n/a",
                    )
                    st.caption("The middle of your recent nights, not an average.")
                with col_b:
                    st.metric("Measured over", f"{feat.coverage_minutes} min")
                    if getattr(feat, "rhr_window_source", "clock") == "sleep":
                        st.caption("Minutes of recorded sleep this reading was taken from.")
                    else:
                        st.caption(
                            "Your watch recorded no sleep for this night, so midnight to "
                            "7am was used instead. This is a weaker basis than a night "
                            "where sleep was recorded."
                        )
                    st.metric(
                        "Time asleep",
                        f"{feat.sleep_hours:.1f} h" if feat.sleep_hours is not None else "n/a",
                    )
                with col_c:
                    st.metric("Explained by activity", f"{det.explained_bpm:.1f} bpm")
                    st.caption("What a recorded workout would be expected to add.")
                    st.metric(
                        "Left unexplained",
                        f"{det.residual_bpm:+.1f} bpm" if det.residual_bpm is not None else "n/a",
                    )
                    st.caption("This is the number the system judges.")

                with st.expander("Everything recorded for this night"):
                    st.json(detail.model_dump(mode="json"))
            else:
                st.write("Nothing was recorded for that night.")


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

            if st.button("Back to all nights"):
                del st.query_params["episode"]
                st.rerun()
            render_episode_panel(ep_detail)
            return
        st.warning("That investigation could not be found.")

    end_d = local_today()
    start_d = end_d - timedelta(days=60)
    nights = list_nights(subject_id, start=start_d, end=end_d)
    episodes = list_episodes(subject_id)

    # The chart says whether the band is still a population estimate, which needs the rung.
    status = get_system_status(subject_id)
    render_night_chart(nights, rung=status.rung)
    st.write("---")
    render_episode_spans(episodes)
    st.write("---")
    render_night_table(subject_id, nights)
