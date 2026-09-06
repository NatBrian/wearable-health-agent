"""History: your nights over time, in six columns and one chart.

The old table showed eleven columns of the database's own vocabulary. Six is what a person
needs to answer the question they came with, which is "has this been happening, and did
anything come of it". Everything else is behind one toggle.

One defect worth keeping fixed: the drill-down set a query parameter and did not rerun, so
clicking an investigation redrew the same page and the detail behind it was unreachable
except by pasting the URL. Anything that changes what is shown now reruns.
"""

import streamlit as st

from wha.api.client import ApiUnavailable
from wha.models import DetectionLevel
from wha.ui import design, format
from wha.ui.components import night_chart
from wha.ui.components.api import api, unavailable
from wha.ui.components.status_bar import render as render_status_bar
from wha.ui.components.subject import resolve as resolve_subject

WINDOWS = {"Last 30 nights": 30, "Last 60 nights": 60, "Last 90 nights": 90, "Last year": 365}


def _open_pipeline(night) -> None:
    st.session_state["pipeline_night"] = night.isoformat()
    st.switch_page("pages/3_The_record.py")


def _outcome_words(episode_state: str | None, disposition: str | None) -> str:
    if episode_state is None:
        return ""
    if disposition:
        return disposition.replace("_", " ").lower()
    return {
        "OPEN": "being looked into",
        "AWAITING_USER": "waiting for your answer",
        "AWAITING_MEASUREMENT": "waiting for a measurement",
        "AWAITING_HUMAN_REVIEW": "waiting for review",
        "CLOSED": "closed with no conclusion recorded",
    }.get(episode_state, episode_state.lower())


def main() -> None:
    st.set_page_config(page_title="History", page_icon="📈", layout="wide")
    design.inject()

    try:
        # Resolved in one place. Reading `subjects[0]` here showed a different person on
        # this screen than on Home, with no indication that it had.
        subject = resolve_subject()
        if subject is None:
            st.warning("There is nobody to show yet.")
            return

        render_status_bar(subject)
        st.markdown(design.separator(), unsafe_allow_html=True)

        st.title("Your nights")
        choice = st.selectbox("How far back", list(WINDOWS), index=1)
        # No end date, for the same reason as Today: the record can run past the calendar.
        nights = api().list_nights(subject, days=WINDOWS[choice])
        episodes = {e.episode_id: e for e in api().list_episodes(subject)}

        night_chart.render(nights)

        st.subheader("Night by night")
        levels = st.multiselect(
            "Show which nights",
            [level.value for level in DetectionLevel],
            default=[],
            help="Leave empty to show every night.",
        )
        investigated_only = st.toggle("Only nights that were looked into", value=False)
        show_everything = st.toggle(
            "Show every recorded field",
            value=False,
            help="The six columns above are what the system judges. This adds the rest.",
        )

        rows = []
        for night in sorted(nights, key=lambda n: n.night_date, reverse=True):
            if levels and str(night.level) not in levels:
                continue
            if investigated_only and night.episode_id is None:
                continue
            episode = episodes.get(night.episode_id or "")
            row = {
                "Night": night.night_date.isoformat(),
                "Conclusion": str(night.level),
                "Your reading": format.bpm(night.rhr_bpm),
                "Against your normal": format.gap(night.deviation_bpm),
                "Sleep measured": format.minutes(night.coverage_minutes),
                "Investigated": _outcome_words(
                    str(episode.state) if episode else None,
                    str(episode.disposition) if episode and episode.disposition else None,
                ),
            }
            if show_everything:
                row |= {
                    "Explained by exercise": format.bpm(night.explained_bpm),
                    "Left after that": format.bpm(night.residual_bpm),
                    "Your normal": format.bpm(night.centre_bpm),
                    "Usual range": format.band(night.band_lo, night.band_hi),
                    "Measured over": night.rhr_window_source,
                    "Investigation": night.episode_id or "",
                }
            rows.append(row)

        if not rows:
            st.info("No nights match that filter. Nothing here is a statement about your health.")
        else:
            st.dataframe(rows, use_container_width=True, hide_index=True)
            # Each level gets its own line. Concatenated, the three sentences read as one
            # paragraph claiming the same night was in range, somewhat above and clearly
            # above at once, because every one of them opens "Your sleeping heart rate
            # was".
            st.caption("Conclusion is the system's own word for that night:")
            st.caption(
                "**GREEN** in your usual range. "
                "**YELLOW** somewhat above it, which on its own opens nothing. "
                "**RED** clearly above it, and enough of these in a row opens an "
                "investigation. "
                "**NA** too little of the night measured to judge."
            )

        st.subheader("Look at one night in full")
        measured = [n for n in nights if n.usable]
        if measured:
            selected = st.selectbox(
                "Which night",
                [n.night_date for n in sorted(measured, key=lambda n: n.night_date, reverse=True)],
                format_func=format.night,
            )
            if st.button("Show me every step of that night", key="history_trace"):
                _open_pipeline(selected)
        else:
            st.caption("No night in this window was measured well enough to open.")
    except ApiUnavailable as exc:
        unavailable(exc)


if __name__ == "__main__":
    main()
