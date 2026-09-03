"""Wearable Health Early Warning Agent (WHA) Streamlit App Shell."""

import streamlit as st

from wha.ui.components.disclaimer import render_disclaimer
from wha.ui.components.status_strip import render_status_strip
from wha.ui.components.subject_selector import render_subject_selector


def main() -> None:
    """Main application shell rendering layout, sidebar, and status strip."""
    st.set_page_config(
        page_title="Wearable Health Early Warning Agent",
        page_icon="🩺",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.sidebar.title("🩺 WHA Monitor")

    # Subject selection
    active_subject = render_subject_selector()

    if not active_subject:
        st.warning(
            "No active subjects found in the database. Ingest wearable data or run a demo scenario."
        )
        return

    st.session_state["active_subject"] = active_subject

    # Render top isolated status strip fragment
    render_status_strip(active_subject)

    st.write("---")
    st.title("Wearable Health Agent")
    render_disclaimer()
    st.write(
        "This watches your overnight heart rate and, when something looks off, works out "
        "why before deciding whether it is worth asking you about."
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            "**Today** - how last night looked, and anything that needs you.\n\n"
            "**History** - your nights over time, and what was investigated."
        )
    with col2:
        st.markdown(
            "**The record** - everything the system did, and proof it has not "
            "been changed.\n\n"
            "**Settings** - where readings come from, and how often you get asked."
        )


if __name__ == "__main__":
    main()
