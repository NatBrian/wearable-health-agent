"""Audit view rendering filterable audit trail, cryptographic hash-chain verification, and exports."""

from pathlib import Path

import pandas as pd
import streamlit as st

from wha.models import AuditFilter
from wha.service.audit import export_audit, query_audit, verify_hash_chain
from wha.ui.components.status_strip import render_status_strip


def render_hash_chain_panel(subject_id: str) -> bool:
    """Render tamper-evidence hash-chain verification card."""
    st.subheader("🔒 Cryptographic Hash-Chain Verification")
    intact, bad_id = verify_hash_chain(subject_id)
    if intact:
        st.success(
            "✅ **Hash-Chain Intact**: All audit event hashes match their SHA-256 chain links."
        )
        return True
    else:
        st.error(f"🚨 **TAMPER DETECTED**: Cryptographic mismatch at event `{bad_id}`.")
        return False


def render_audit_table(subject_id: str, f: AuditFilter, limit: int = 50, offset: int = 0) -> None:
    """Render filterable, paginated audit trail table."""
    st.subheader("📜 Audit Trail")
    events = query_audit(f, limit=limit, offset=offset)

    if not events:
        st.info("No audit events match the selected criteria.")
        return

    data = []
    for e in events:
        data.append(
            {
                "Event ID": e.event_id,
                "Timestamp (UTC)": e.timestamp_utc.strftime("%Y-%m-%d %H:%M:%S"),
                "Episode": e.episode_id or "-",
                "Actor": e.actor,
                "Operation": e.operation,
                "Tier": e.control_tier.value,
                "Tool": e.tool_name or "-",
                "Permission": e.permission_decision or "-",
                "Safety Event": e.safety_event or "-",
                "Hash Status": "VALID" if e.hash_ok else "INVALID",
            }
        )

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)


def render_audit_page(subject_id: str) -> None:
    """Render complete Audit page."""
    render_status_strip(subject_id)
    st.write("---")

    render_hash_chain_panel(subject_id)
    st.write("---")

    # Filter sidebar or form
    st.markdown("### 🔍 Filters")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        ep_filter = st.text_input("Filter by Episode ID", key="audit_ep_filter")
    with col2:
        actor_filter = st.text_input("Filter by Actor", key="audit_actor_filter")
    with col3:
        op_filter = st.text_input("Filter by Operation", key="audit_op_filter")
    with col4:
        safety_filter = st.text_input("Filter by Safety Event", key="audit_safety_filter")

    audit_f = AuditFilter(
        subject_id=subject_id,
        episode_id=ep_filter or None,
        actor=actor_filter or None,
        operation=op_filter or None,
        safety_event=safety_filter or None,
    )

    render_audit_table(subject_id, audit_f)

    st.write("---")
    st.markdown("### 📥 Export Audit Trail")
    col_csv, col_json = st.columns(2)
    with col_csv:
        if st.button("Export to CSV", key="btn_export_csv"):
            export_path = Path("scratch") / f"audit_{subject_id}.csv"
            export_audit(audit_f, export_path)
            st.success(f"Exported to `{export_path}`")
    with col_json:
        if st.button("Export to JSON", key="btn_export_json"):
            export_path = Path("scratch") / f"audit_{subject_id}.json"
            export_audit(audit_f, export_path)
            st.success(f"Exported to `{export_path}`")
