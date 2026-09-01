"""Audit page runner for Streamlit."""

import streamlit as st

from wha.ui.audit import render_audit_page
from wha.ui.components.subject_selector import render_subject_selector


def main() -> None:
    """Entry point for Audit page."""
    st.set_page_config(page_title="WHA - Audit Trail & Pipeline Inspector", page_icon="📜", layout="wide")
    subject = render_subject_selector() or st.session_state.get("active_subject")
    if subject:
        render_audit_page(subject)
    else:
        st.warning("No subjects available.")


if __name__ == "__main__":
    main()
