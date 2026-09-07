"""The line across the top of every screen: is this working, and what if it is not.

The version this replaces showed six coloured pills naming a component and its state:
"Watch data: Arriving (07:12)", "AI model: Ready". A person who does not know what a
bridge or a provider is learns nothing from that, and worse, learns nothing from its
absence either.

Every line here says what the state means for the person. When something is degraded it
says what stops working, because "warn" on its own is a colour, not information.

The timestamp fix from the old strip is kept and is the reason `local_time` takes the
client: printing the UTC hour told a person in Singapore their data arrived at 17:41 when
it was 01:41 for them.
"""

from typing import Any

import streamlit as st

from wha.models import SystemStatus
from wha.ui import design, format
from wha.ui.components.api import api


def _component(status: SystemStatus, name: str) -> Any:
    return next((c for c in status.components if c.component == name), None)


def _watch_line(status: SystemStatus, client: Any) -> tuple[str, str, str]:
    bridge = _component(status, "bridge")
    if bridge is not None and bridge.severity == "error":
        return (
            "Watch data",
            "not arriving",
            "Nothing new is coming from your phone, so nights from now on will not be judged.",
        )
    if bridge is not None and bridge.severity == "warn":
        return ("Watch data", "delayed", bridge.detail)
    arrived = format.local_time(client, status.last_ingest_utc)
    return ("Watch data", f"arrived {arrived}", "Your phone is handing over readings.")


def _baseline_line(status: SystemStatus) -> tuple[str, str, str]:
    from wha.ui import explain

    return (
        "Your normal",
        f"{status.usable_nights} nights measured",
        explain.rung(str(status.rung)),
    )


def _nightly_line(status: SystemStatus, client: Any) -> tuple[str, str, str]:
    scheduler = _component(status, "scheduler")
    if scheduler is not None and not scheduler.ok:
        return (
            "Nightly check",
            "not running",
            "Nights are not being judged until this is running again.",
        )
    ran = format.local_time(client, status.last_nightly_utc)
    return ("Nightly check", f"last ran {ran}", "Runs on its own, several times a day.")


def _model_line(status: SystemStatus) -> tuple[str, str, str]:
    llm = _component(status, "llm")
    if llm is not None and not llm.ok:
        return (
            "AI model",
            "not reachable",
            (
                "Questions and written summaries are unavailable. Nights are still "
                "measured and judged, because that half uses no AI at all."
            ),
        )
    return ("AI model", "reachable", "Used only for questions, summaries and chat.")


def _contact_line(status: SystemStatus) -> tuple[str, str, str]:
    telegram = _component(status, "telegram")
    if telegram is None or not telegram.ok:
        return (
            "How you get asked",
            "this screen only",
            "No messaging is set up, so questions wait here until you open the dashboard.",
        )
    return ("How you get asked", "Telegram", "Questions reach you on your phone.")


@st.fragment(run_every=30)
def render(subject_id: str, status: SystemStatus | None = None) -> None:
    """Five plain statements, and one line saying whether anything needs attention."""
    client = api()
    if status is None:
        try:
            status = client.get_system_status(subject_id)
        except (RuntimeError, ValueError, OSError, KeyError, AttributeError) as exc:
            st.error(
                "**Cannot reach the application.** Nothing on this screen is a statement "
                f"about your health. ({exc})"
            )
            return

    lines = [
        _watch_line(status, client),
        _baseline_line(status),
        _nightly_line(status, client),
        _model_line(status),
        _contact_line(status),
    ]

    degraded = [
        name
        for name, value, _note in lines
        if value in {"not arriving", "not running", "not reachable", "delayed"}
    ]
    # Named separately rather than added to the list above. "Problems today" was not one
    # of the five lines, so the attention sentence pointed at something the reader could
    # not find on the screen.
    problems = status.errors_24h

    columns = st.columns(len(lines))
    for column, (name, value, note) in zip(columns, lines, strict=True):
        tone = "warn" if name in degraded else "ok"
        with column:
            st.markdown(design.tile(name, value, note, tone=tone), unsafe_allow_html=True)

    if degraded:
        st.warning(
            "Some parts of the system need attention: "
            + ", ".join(degraded)
            + ". The lines above say what each one stops."
        )
    if problems:
        st.warning(
            f"The system recorded {problems} problems in the last day. They are listed on "
            "the record screen, under everything the system did."
        )
