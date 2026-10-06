"""Whose data a screen is showing, decided the same way on every screen.

Found by opening the pages directly rather than clicking through from Home. Home read the
application's configured subject; the other four fell back to `subjects[0]`, whichever row
the database happened to return first. So Home showed `sim` while Today, History, the
record and Settings showed `me`, which holds four nights of a real person's data, and the
only clue was that the two screens quoted different night counts.

A dashboard for one person that can silently show a different one is the worst kind of
wrong on a health screen, because everything on it stays plausible.
"""

import streamlit as st

from wha.ui.components.api import api, config


def resolve() -> str | None:
    """The subject every screen should be showing, in one place.

    Order: what the reader picked this session, then the subject this installation is
    configured for, then the only subject there is. Never "the first row", which is not a
    decision anybody made.
    """
    chosen = st.session_state.get("active_subject")
    subjects = api().list_subjects()
    if not subjects:
        return None

    known = {s.subject_id for s in subjects}
    if chosen in known:
        return str(chosen)

    configured = config().get("configured_subject")
    if configured in known:
        st.session_state["active_subject"] = configured
        return str(configured)

    if len(subjects) == 1:
        st.session_state["active_subject"] = subjects[0].subject_id
        return str(subjects[0].subject_id)

    # More than one person and none of them configured. Say so rather than guessing: on a
    # single-user system this means the configuration and the database disagree.
    st.warning(
        "This installation is configured for a person who has no data here, and there is "
        "more than one person on file. Pick one on the Home screen."
    )
    return None
