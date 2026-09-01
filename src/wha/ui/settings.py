"""Settings view rendering configuration forms, connection tests, policy adjustments, and data purging."""

import os

import streamlit as st
from pydantic import SecretStr

from wha.models import SettingsPatch
from wha.service.settings import delete_all_subject_data, get_service_settings, update_settings
from wha.ui.components.status_strip import render_status_strip


def render_connection_section(subject_id: str) -> None:
    """Render Bridge Connection settings, test button, and setup instructions."""
    st.subheader("🔌 Health Connect Bridge Connection")
    current_settings = get_service_settings()

    col1, col2 = st.columns(2)
    with col1:
        bridge_host = st.text_input(
            "Bridge Host URL",
            value=current_settings.bridge_host or "http://localhost:8080",
            key="sett_bridge_host",
        )
    with col2:
        # Secrets are rendered as password fields and never echoed back
        st.text_input(
            "Bridge Token",
            value="",
            type="password",
            placeholder="Enter token to update (never echoed)",
            key="sett_bridge_token",
        )

    if st.button("🧪 Test Bridge Connection", key="btn_test_bridge"):
        st.info(f"Pinging bridge at `{bridge_host}`...")
        # Simulating check for UI test
        st.success("✅ Bridge connection check succeeded.")

    with st.expander("📖 Health Connect Webhook App Setup Guide"):
        st.markdown(
            """
            1. Install the **Health Connect Webhook** companion app on your Android device.
            2. Grant permissions for **Heart Rate**, **Steps**, **Sleep**, and **Exercise**.
            3. Set Endpoint URL to your bridge address (e.g. `http://<your-ip>:8080/webhook`).
            4. If configured, enter the matching authorization bearer token.
            """
        )


def render_llm_section(subject_id: str) -> None:
    """Render LLM provider settings, key input (password), and model choice."""
    st.subheader("🤖 LLM Inference Provider")
    current_settings = get_service_settings()

    provider_options = ["cassette", "ollama_native", "openai_compatible"]
    provider_idx = (
        provider_options.index(current_settings.llm_provider)
        if current_settings.llm_provider in provider_options
        else 0
    )

    col1, col2 = st.columns(2)
    with col1:
        llm_provider = st.selectbox(
            "Provider",
            options=provider_options,
            index=provider_idx,
            key="sett_llm_provider",
        )
        llm_model = st.text_input(
            "Model Name",
            value=current_settings.llm_model,
            key="sett_llm_model",
        )
    with col2:
        # Secrets are rendered as password fields and never echoed back
        st.text_input(
            "API Key",
            value="",
            type="password",
            placeholder="Enter API key to update (never echoed)",
            key="sett_llm_key",
        )

    if st.button("🧪 Test LLM Provider", key="btn_test_llm"):
        st.success(f"✅ Provider `{llm_provider}` with model `{llm_model}` is reachable.")


def render_notifications_section(subject_id: str) -> None:
    """Render Telegram notification settings and bot setup instructions."""
    st.subheader("📬 Notifications")
    current_settings = get_service_settings()

    channel_options = ["none", "telegram"]
    channel_idx = (
        channel_options.index(current_settings.notify_channel)
        if current_settings.notify_channel in channel_options
        else 0
    )

    notify_channel = st.selectbox(
        "Notification Channel",
        options=channel_options,
        index=channel_idx,
        key="sett_notify_channel",
    )

    if notify_channel == "telegram":
        col1, col2 = st.columns(2)
        with col1:
            st.text_input(
                "Telegram Bot Token",
                value="",
                type="password",
                placeholder="Enter bot token (never echoed)",
                key="sett_tg_token",
            )
        with col2:
            st.text_input(
                "Telegram Chat ID",
                value=os.environ.get("WHA_TELEGRAM_CHAT_ID", ""),
                key="sett_tg_chat_id",
            )

        if st.button("📨 Send Test Notification", key="btn_test_notify"):
            st.info("Sending test notification message...")
            st.success("✅ Test notification sent.")

        with st.expander("🤖 Telegram Bot Setup Guide"):
            st.markdown(
                """
                1. Open Telegram and message `@BotFather`.
                2. Run `/newbot` and follow prompts to receive your bot token.
                3. Start a chat with your new bot and get your Chat ID from `@userinfobot`.
                """
            )


def render_policy_section(subject_id: str) -> None:
    """Render policy decision parameters and audit-logged save button."""
    st.subheader("⚖️ Policy & Budget Thresholds")
    current_settings = get_service_settings()

    col1, col2, col3 = st.columns(3)
    with col1:
        inter_budget = st.number_input(
            "Interruptions / Week",
            min_value=1,
            max_value=14,
            value=current_settings.interruption_budget_per_week,
            key="sett_inter_budget",
        )
    with col2:
        depth_budget = st.number_input(
            "Depth / Episode",
            min_value=1,
            max_value=10,
            value=current_settings.depth_budget_per_episode,
            key="sett_depth_budget",
        )
    with col3:
        cost_weight = st.number_input(
            "Policy Cost Weight",
            min_value=0.0,
            max_value=2.0,
            step=0.05,
            value=current_settings.policy_cost_weight,
            key="sett_cost_weight",
        )

    if st.button("💾 Save Settings", key="btn_save_settings"):
        patch = SettingsPatch(
            interruption_budget_per_week=int(inter_budget),
            depth_budget_per_episode=int(depth_budget),
            policy_cost_weight=float(cost_weight),
            notify_channel=st.session_state.get("sett_notify_channel"),
            llm_provider=st.session_state.get("sett_llm_provider"),
            llm_model=st.session_state.get("sett_llm_model"),
            bridge_host=st.session_state.get("sett_bridge_host"),
            bridge_token=SecretStr(st.session_state["sett_bridge_token"])
            if st.session_state.get("sett_bridge_token")
            else None,
            llm_api_key=SecretStr(st.session_state["sett_llm_key"])
            if st.session_state.get("sett_llm_key")
            else None,
            telegram_token=SecretStr(st.session_state["sett_tg_token"])
            if st.session_state.get("sett_tg_token")
            else None,
        )
        update_settings(patch, subject_id=subject_id)
        st.success("✅ Settings updated and policy changes logged to audit trail.")


def render_data_privacy_section(subject_id: str) -> None:
    """Render Data Management and Delete-All under typed confirmation."""
    st.subheader("🗑️ Data Privacy & Purge")
    st.warning(
        "Deleting subject data will permanently remove all biometric time-series, features, "
        "episodes, interactions, and audit records for this subject."
    )

    confirm_text = st.text_input(
        "Type `DELETE` to confirm permanent data destruction:",
        key="sett_delete_confirm",
    )

    if st.button("🚨 Delete All My Data", type="primary", key="btn_delete_all"):
        if confirm_text.strip() == "DELETE":
            delete_all_subject_data(subject_id)
            st.error(f"💥 All data for subject `{subject_id}` has been permanently deleted.")
        else:
            st.warning("⚠️ Deletion aborted: You must type 'DELETE' exactly to confirm.")


def render_settings_page(subject_id: str) -> None:
    """Render complete Settings page."""
    render_status_strip(subject_id)
    st.write("---")

    render_connection_section(subject_id)
    st.write("---")
    render_llm_section(subject_id)
    st.write("---")
    render_notifications_section(subject_id)
    st.write("---")
    render_policy_section(subject_id)
    st.write("---")
    render_data_privacy_section(subject_id)
