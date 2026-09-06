"""The first screen: what this is, what it cannot do, and where to go next.

Not a README on a page. A person arriving here wants three things in this order: what to
do if they feel unwell right now, what this system is and is not, and which screen answers
their question. The repository carried a DISCLAIMER.md from the beginning and no screen
ever showed it, so a person using the dashboard was never told it is not a medical device.

Every figure on this page comes from the application over HTTP. The wording comes from
`wha.ui.explain`, which is checked against the same forbidden-phrase list the model's own
output is checked against.
"""

import streamlit as st

from wha.api.client import ApiUnavailable
from wha.ui import design, explain
from wha.ui.components.api import api, unavailable
from wha.ui.components.status_bar import render as render_status_bar


def _pick_subject() -> str | None:
    """Which person this dashboard is showing. Silent when there is only one."""
    client = api()
    subjects = client.list_subjects()
    if not subjects:
        return None
    if len(subjects) == 1:
        return subjects[0].subject_id

    labels = {s.subject_id: f"{s.label} ({s.subject_id})" for s in subjects}
    ids = list(labels)
    configured = client.config().get("configured_subject")
    remembered = st.session_state.get("active_subject") or configured
    index = ids.index(remembered) if remembered in ids else 0
    return st.sidebar.selectbox("Whose data", ids, index=index, format_func=lambda i: labels[i])


def _unevidenced_count() -> int | None:
    """How many clinical figures carry no published source, read live, never typed in."""
    try:
        provenance = api().get_knowledge_provenance()
    except (ApiUnavailable, RuntimeError, ValueError, OSError):
        return None
    values = provenance.values() if isinstance(provenance, dict) else []
    return sum(
        1
        for entry in values
        if str(entry.get("provenance", "") if isinstance(entry, dict) else entry).upper()
        == "ASSUMED"
    )


def main() -> None:
    st.set_page_config(
        page_title="Your night watch",
        page_icon="🌙",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    design.inject()
    st.sidebar.title("Your night watch")

    try:
        subject = _pick_subject()
    except ApiUnavailable as exc:
        unavailable(exc)
        return

    if not subject:
        st.warning(
            "There is nobody to show yet. Once your watch data has been pulled in for the "
            "first time, this screen will show it."
        )
        return

    st.session_state["active_subject"] = subject
    render_status_bar(subject)
    st.markdown(design.separator(), unsafe_allow_html=True)

    st.title("What this is")
    st.markdown(
        f'<p class="wha-lede">{explain.text("home.what_it_is")}</p>', unsafe_allow_html=True
    )

    st.error(f"**If you feel unwell now.** {explain.text('home.emergency')}")

    left, right = st.columns(2)
    with left:
        st.markdown(
            design.card("What it can do", f"<p>{explain.text('home.can')}</p>"),
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            design.card("What it cannot do", f"<p>{explain.text('home.cannot')}</p>"),
            unsafe_allow_html=True,
        )

    st.subheader("How a night gets judged")
    st.write(explain.text("home.judging"))
    st.caption("Every step of this is shown, night by night, on the Record screen.")

    st.subheader("Where to go")
    columns = st.columns(4)
    for column, (name, key) in zip(
        columns,
        [
            ("Today", "home.nav.today"),
            ("History", "home.nav.history"),
            ("Record", "home.nav.audit"),
            ("Settings", "home.nav.settings"),
        ],
        strict=True,
    ):
        with column:
            st.markdown(design.card(name, f"<p>{explain.text(key)}</p>"), unsafe_allow_html=True)

    st.subheader("Being straight with you about the evidence")
    unevidenced = _unevidenced_count()
    st.write(explain.text("home.provenance"))
    if unevidenced is not None:
        st.caption(
            f"{unevidenced} figures in this system's knowledge currently have no published "
            "source and are marked as such wherever they are used."
        )


if __name__ == "__main__":
    main()
