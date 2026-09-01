"""History Streamlit Page."""

import streamlit as st

from wha.ui.components.subject_selector import render_subject_selector
from wha.ui.history import render_history_page


def main() -> None:
    """Page runner for History."""
    st.set_page_config(page_title="History | WHA", page_icon="🩺", layout="wide")
    active_subject = render_subject_selector() or st.session_state.get("active_subject")
    if not active_subject:
        st.warning("No subject selected.")
        return

    render_history_page(active_subject)


if __name__ == "__main__":
    main()
