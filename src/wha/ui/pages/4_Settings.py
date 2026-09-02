"""Settings page runner for Streamlit."""

import streamlit as st

from wha.ui.components.subject_selector import render_subject_selector
from wha.ui.settings import render_settings_page


def main() -> None:
    """Entry point for Settings page."""
    st.set_page_config(page_title="Settings | WHA", page_icon="⚙️", layout="wide")
    st.title("Settings")

    subject = render_subject_selector() or st.session_state.get("active_subject")
    if subject:
        render_settings_page(subject)
    else:
        st.warning("No subjects available.")


if __name__ == "__main__":
    main()
