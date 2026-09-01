"""Today Streamlit Page."""

import streamlit as st

from wha.ui.components.subject_selector import render_subject_selector
from wha.ui.today import render_today_page


def main() -> None:
    """Page runner for Today."""
    st.set_page_config(page_title="Today | WHA", page_icon="🩺", layout="wide")
    active_subject = render_subject_selector() or st.session_state.get("active_subject")
    if not active_subject:
        st.warning("No subject selected.")
        return

    render_today_page(active_subject)


if __name__ == "__main__":
    main()
