"""Subject selector component rendered in sidebar, hidden when only one subject exists."""

import streamlit as st

from wha.service.subjects import list_subjects


def render_subject_selector() -> str | None:
    """Render subject selector dropdown in the sidebar only if multiple subjects exist.

    If exactly one subject exists, returns its ID silently without rendering a widget.
    If no subjects exist, returns None.
    """
    subjects = list_subjects()
    if not subjects:
        return None

    if len(subjects) == 1:
        # Hidden entirely when only one subject exists
        return subjects[0].subject_id

    subject_options = {s.subject_id: f"{s.label} ({s.subject_id})" for s in subjects}
    selected_id = st.sidebar.selectbox(
        "Select Subject",
        options=list(subject_options.keys()),
        format_func=lambda sid: subject_options[sid],
    )
    return selected_id
