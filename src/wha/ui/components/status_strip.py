"""The strip across the top of every page: is the system actually working right now.

Six pills, each naming a thing that can silently stop working. The labels say what the
thing does for the person rather than what it is called in the code, so "LLM Provider"
is "AI model" and the baseline rung is described rather than spelled.
"""

from typing import Any

import streamlit as st

from wha.models import SystemStatus
from wha.ui.components.api import api
from wha.ui.components.wording import rung_phrase


def format_status_indicator(comp_name: str, status: Any) -> tuple[str, str, str]:
    """Helper returning (label, status_icon, tooltip)."""
    return comp_name, "ok", ""


def _render_pill(icon: str, label: str, value: str, severity: str = "ok") -> str:
    colors = {
        "ok": ("#0f5132", "#d1e7dd", "#badbcc"),
        "warn": ("#664d03", "#fff3cd", "#ffecb5"),
        "error": ("#842029", "#f8d7da", "#f5c2c7"),
        "info": ("#055160", "#cff4fc", "#b6effb"),
    }
    fg, bg, border = colors.get(severity, colors["ok"])
    return f"""<div style="background-color: {bg}; color: {fg}; border: 1px solid {border}; padding: 8px 12px; border-radius: 8px; font-size: 0.82rem; line-height: 1.2; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.04);">
        <div style="font-weight: 600; margin-bottom: 2px;">{icon} {label}</div>
        <div style="font-size: 0.78rem; opacity: 0.95; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{value}">{value}</div>
    </div>"""


@st.fragment(run_every=10)
def render_status_strip(subject_id: str, status: SystemStatus | None = None) -> None:
    """Render top compact system status strip using an st.fragment with 10s auto-refresh."""
    if status is None:
        try:
            status = api().get_system_status(subject_id)
        except (RuntimeError, ValueError, OSError, KeyError, AttributeError) as exc:
            st.error(f"Status check failed: {exc}")
            return

    cols = st.columns(6)

    # 1. Is data arriving from the watch at all
    bridge_comp = next((c for c in status.components if c.component == "bridge"), None)
    with cols[0]:
        if bridge_comp and bridge_comp.severity == "error":
            st.error(f"Watch data: {bridge_comp.detail}", icon="⚠️")
        elif bridge_comp and bridge_comp.severity == "warn":
            st.warning(f"Watch data: {bridge_comp.detail}", icon="⏳")
        else:
            # Shown to a person looking at their own clock, so it is their clock this
            # uses. Printing the UTC hour told a subject in Singapore that data arrived at
            # 17:41 when it was 01:41 for them.
            last_in = (
                api().localise(status.last_ingest_utc).strftime("%H:%M")
                if status.last_ingest_utc
                else "just now"
            )
            html = _render_pill("⌚", "Watch data", f"Arriving ({last_in})", severity="ok")
            st.markdown(html, unsafe_allow_html=True)

    # 2. How well the system knows this person's normal
    with cols[1]:
        phrase = rung_phrase(status.rung)
        nights = status.usable_nights
        html = _render_pill(
            "📈",
            "Your baseline",
            phrase.label,
            severity="ok" if nights >= 14 else "info",
        )
        st.markdown(html, unsafe_allow_html=True)

    # 3. Is the nightly check running
    sched_comp = next((c for c in status.components if c.component == "scheduler"), None)
    with cols[2]:
        if sched_comp and not sched_comp.ok:
            html = _render_pill("⏰", "Nightly check", "Not running", severity="error")
        else:
            html = _render_pill("⏰", "Nightly check", "Running", severity="ok")
        st.markdown(html, unsafe_allow_html=True)

    # 4. The model that writes questions and summaries
    llm_comp = next((c for c in status.components if c.component == "llm"), None)
    with cols[3]:
        detail = llm_comp.detail if llm_comp else "Ready"
        severity = "warn" if llm_comp and not llm_comp.ok else "info"
        html = _render_pill("🤖", "AI model", detail, severity=severity)
        st.markdown(html, unsafe_allow_html=True)

    # 5. How the person gets asked
    tg_comp = next((c for c in status.components if c.component == "telegram"), None)
    with cols[4]:
        detail = tg_comp.detail if tg_comp else "Off"
        html = _render_pill("💬", "How you're asked", detail, severity="info")
        st.markdown(html, unsafe_allow_html=True)

    # 6. Anything that went wrong recently
    with cols[5]:
        if status.errors_24h > 0:
            html = _render_pill(
                "🚨", "Problems today", f"{status.errors_24h} to look at", severity="error"
            )
        else:
            html = _render_pill("✅", "Problems today", "None", severity="ok")
        st.markdown(html, unsafe_allow_html=True)
