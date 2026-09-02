"""Wearable Health Early Warning Agent (WHA) Streamlit App Shell."""

import streamlit as st

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
    st.title("Wearable Health Agent Dashboard")
    st.info(
        "Select a page from the sidebar: Today, History, Audit, or Settings."
    )


if __name__ == "__main__":
    main()
