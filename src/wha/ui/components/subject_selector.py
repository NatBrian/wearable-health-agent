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
    ids = list(subject_options.keys())

    # Remember the choice across pages, and start on the configured subject.
    #
    # The selectbox took no index and no key, so every page load reset it to the first
    # subject alphabetically. Switching to another subject and then clicking History put
    # you back on the first one, and the configured WHA_SUBJECT was ignored entirely.
    remembered = st.session_state.get("active_subject")
    if remembered not in ids:
        from wha.config import get_settings

        configured = get_settings().subject
        remembered = configured if configured in ids else ids[0]

    selected_id = st.sidebar.selectbox(
        "Select Subject",
        options=ids,
        index=ids.index(remembered),
        format_func=lambda sid: subject_options[sid],
        key="subject_selector",
    )
    st.session_state["active_subject"] = selected_id
    return selected_id
