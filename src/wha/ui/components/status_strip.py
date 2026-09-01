"""Status strip component refreshed in an isolated fragment every 10 seconds."""

from typing import Any

import streamlit as st

from wha.models import SystemStatus
from wha.service.status import get_system_status


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
            status = get_system_status(subject_id)
        except (RuntimeError, ValueError, OSError, KeyError, AttributeError) as exc:
            st.error(f"Status check failed: {exc}")
            return

    cols = st.columns(6)

    # 1. Watch Data (Bridge / Ingest)
    bridge_comp = next((c for c in status.components if c.component == "bridge"), None)
    with cols[0]:
        if bridge_comp and bridge_comp.severity == "error":
            st.error(f"Watch: {bridge_comp.detail}", icon="⚠️")
        elif bridge_comp and bridge_comp.severity == "warn":
            st.warning(f"Watch: {bridge_comp.detail}", icon="⏳")
        else:
            last_in = (
                status.last_ingest_utc.strftime("%H:%M") if status.last_ingest_utc else "Current"
            )
            html = _render_pill("⌚", "Watch Data", f"OK ({last_in})", severity="ok")
            st.markdown(html, unsafe_allow_html=True)

    # 2. Baseline
    with cols[1]:
        rung_label = status.rung.value
        html = _render_pill(
            "📈", "Baseline", f"{status.usable_nights}d ({rung_label})", severity="info"
        )
        st.markdown(html, unsafe_allow_html=True)

    # 3. Scheduler
    sched_comp = next((c for c in status.components if c.component == "scheduler"), None)
    with cols[2]:
        if sched_comp and not sched_comp.ok:
            html = _render_pill("⏰", "Scheduler", "Degraded", severity="error")
        else:
            html = _render_pill("⏰", "Scheduler", "Active", severity="ok")
        st.markdown(html, unsafe_allow_html=True)

    # 4. LLM
    llm_comp = next((c for c in status.components if c.component == "llm"), None)
    with cols[3]:
        detail = llm_comp.detail if llm_comp else "Active"
        html = _render_pill("🤖", "LLM Provider", detail, severity="info")
        st.markdown(html, unsafe_allow_html=True)

    # 5. Telegram / Notifications
    tg_comp = next((c for c in status.components if c.component == "telegram"), None)
    with cols[4]:
        detail = tg_comp.detail if tg_comp else "Disabled"
        html = _render_pill("💬", "Notifications", detail, severity="info")
        st.markdown(html, unsafe_allow_html=True)

    # 6. Errors 24h
    with cols[5]:
        if status.errors_24h > 0:
            html = _render_pill(
                "🚨", "Errors (24h)", f"{status.errors_24h} detected", severity="error"
            )
        else:
            html = _render_pill("✅", "System Errors", "0 in 24h", severity="ok")
        st.markdown(html, unsafe_allow_html=True)
