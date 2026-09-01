"""Status strip component refreshed in an isolated fragment every 10 seconds."""

from typing import Any

import streamlit as st

from wha.models import SystemStatus
from wha.service.status import get_system_status


def format_status_indicator(comp_name: str, status: Any) -> tuple[str, str, str]:
    """Helper returning (label, status_icon, tooltip)."""
    return comp_name, "ok", ""


@st.fragment(run_every=10)
def render_status_strip(subject_id: str, status: SystemStatus | None = None) -> None:
    """Render top compact system status strip using an st.fragment with 10s auto-refresh."""
    if status is None:
        try:
            status = get_system_status(subject_id)
        except (RuntimeError, ValueError, OSError, KeyError, AttributeError) as exc:
            st.error(f"Status check failed: {exc}")
            return

    # 6 Indicator pills in a container
    cols = st.columns(6)

    # 1. Watch Data (Bridge / Ingest)
    bridge_comp = next((c for c in status.components if c.component == "bridge"), None)
    with cols[0]:
        if bridge_comp and bridge_comp.severity == "error":
            st.error(f"Watch: {bridge_comp.detail}", icon="⚠️")
        elif bridge_comp and bridge_comp.severity == "warn":
            st.warning(f"Watch: {bridge_comp.detail}", icon="⏳")
        else:
            last_in = status.last_ingest_utc.strftime("%H:%M") if status.last_ingest_utc else "N/A"
            st.success(f"Watch: OK ({last_in})", icon="⌚")

    # 2. Baseline
    with cols[1]:
        rung_label = status.rung.value
        st.info(f"Baseline: {status.usable_nights}d ({rung_label})", icon="📈")

    # 3. Scheduler
    sched_comp = next((c for c in status.components if c.component == "scheduler"), None)
    with cols[2]:
        if sched_comp and not sched_comp.ok:
            st.error("Scheduler: Error", icon="⏰")
        else:
            st.success("Scheduler: Active", icon="⏰")

    # 4. LLM
    llm_comp = next((c for c in status.components if c.component == "llm"), None)
    with cols[3]:
        detail = llm_comp.detail if llm_comp else "LLM Active"
        st.info(f"LLM: {detail}", icon="🤖")

    # 5. Telegram / Notifications
    tg_comp = next((c for c in status.components if c.component == "telegram"), None)
    with cols[4]:
        detail = tg_comp.detail if tg_comp else "Notify None"
        st.info(f"Notify: {detail}", icon="💬")

    # 6. Errors 24h
    with cols[5]:
        if status.errors_24h > 0:
            st.error(f"Errors (24h): {status.errors_24h}", icon="🚨")
        else:
            st.success("Errors (24h): 0", icon="✅")
