"""Settings: where your data comes from, how you get asked, and how often.

Each control says what it changes from the person's point of view, and every
number that affects how often they are interrupted explains what moving it does.
"""

import os

import streamlit as st
from pydantic import SecretStr

from wha.models import SettingsPatch
from wha.ui.components.api import api
from wha.ui.components.status_strip import render_status_strip


def render_profile_section(subject_id: str) -> None:
    """Five standing facts, each one read by something named.

    The rule for being on this page is that something CONSUMES the field. That is why
    weight, height and BMI are not here: nothing has a covariate model, the baseline
    becomes personal after seven nights, and a field nobody reads tells you your data is
    being used when it is not.
    """
    st.subheader("About you")
    st.caption(
        "Five things, asked once. Each one changes how a rule decides, and each one says "
        "which. Nothing here is asked out of curiosity, and nothing you type in the last "
        "box is ever shown to the AI."
    )

    profile = api().get_subject_profile(subject_id)

    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input(
            "Your age",
            min_value=0,
            max_value=120,
            value=profile.age_years if profile.age_years is not None else 0,
            help=(
                "The chest pain rule this system uses was tested only on people aged 35 "
                "and over. Below that it is not applied to you at all, and you are routed "
                "the cautious way instead."
            ),
        )
    with col2:
        sex_options = ["Prefer not to say", "female", "male"]
        sex_index = sex_options.index(profile.sex) if profile.sex in sex_options else 0
        sex = st.selectbox(
            "Sex",
            sex_options,
            index=sex_index,
            help=(
                "One item of the chest pain rule is whether you are a woman 65 or over, "
                "or a man 55 or over. Answering here means you are not asked it during a "
                "conversation about chest pain."
            ),
        )

    vascular = st.checkbox(
        "I have been diagnosed with coronary artery disease, a stroke or TIA, "
        "or peripheral arterial disease",
        value=bool(profile.known_vascular_disease),
        help=(
            "Another item of the same rule. It is the one most easily misremembered when "
            "you are frightened, and it does not change from day to day."
        ),
    )

    menstruates = st.checkbox(
        "I menstruate",
        value=bool(profile.menstruates),
        help=(
            "The menstrual cycle is one of the twelve causes this system weighs, and it "
            "is the largest ordinary explanation for a raised night. Left unanswered it "
            "is switched off entirely rather than assumed, so answering here makes the "
            "reasoning about your nights more accurate."
        ),
    )

    medicine = st.checkbox(
        "I take a medicine that lowers my heart rate, such as a beta blocker",
        value=bool(profile.rate_lowering_medicine),
        help=(
            "Nothing calculates with this. It exists so the system can tell you it is "
            "less able to see an infection in you, rather than being quietly worse at "
            "its job."
        ),
    )

    notes = st.text_area(
        "Anything your doctor should know",
        value=profile.notes_for_doctor or "",
        help=(
            "For the summary you would hand a doctor. This is NEVER shown to the AI and "
            "never enters its reasoning, because text the model reads without a source "
            "behind it is exactly what this system is built to avoid."
        ),
    )

    if st.button("Save", key="profile_save"):
        api().update_subject_profile(
            subject_id,
            age_years=int(age) if age else None,
            sex=None if sex == "Prefer not to say" else sex,
            known_vascular_disease=vascular,
            menstruates=menstruates,
            rate_lowering_medicine=medicine,
            notes_for_doctor=notes or None,
        )
        st.success("Saved.")
        st.rerun()

    if medicine:
        st.warning(
            "**A limitation, while that box is ticked.** Medicines that slow the heart "
            "blunt the rise an infection causes, so an illness may not lift your "
            "overnight rate far enough for this system to notice. It is less able to see "
            "an infection in you than in somebody not taking one. That is a limitation of "
            "the method, not a reason to change your medication."
        )


def render_connection_section(subject_id: str) -> None:
    """Render Bridge Connection settings, test button, and setup instructions."""
    st.subheader("Where your readings come from")
    st.caption(
        "The companion app on your phone sends heart rate and step data to this "
        "address. Nothing is read from your phone unless it is running."
    )
    current_settings = api().get_service_settings()

    col1, col2 = st.columns(2)
    with col1:
        bridge_host = st.text_input(
            "Phone address",
            value=current_settings.bridge_host or "",
            placeholder="http://192.168.1.20:8787",
            help="The address shown in the companion app on your phone.",
            key="sett_bridge_host",
        )
    with col2:
        # Secrets are rendered as password fields and never echoed back
        st.text_input(
            "Phone access code",
            value="",
            type="password",
            placeholder="Only needed to change it",
            help="Shown in the companion app. Never displayed back to you.",
            key="sett_bridge_token",
        )

    if st.button("Check the connection", key="btn_test_bridge"):
        clean_host = bridge_host.strip()
        if (
            clean_host
            and not clean_host.startswith("http://")
            and not clean_host.startswith("https://")
        ):
            clean_host = f"http://{clean_host}"
        token_val = st.session_state.get("sett_bridge_token") or None
        st.info(f"Trying `{clean_host}`...")
        chk = api().test_bridge_connection(bridge_host=clean_host, bridge_token=token_val)
        if chk.ok:
            st.success(f"✅ {chk.detail} ({chk.latency_ms}ms)")
        else:
            st.error(f"❌ {chk.detail} ({chk.latency_ms}ms)")

    with st.expander("How to set the phone up"):
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
    st.subheader("The AI model")
    st.caption(
        "Used to word questions and write summaries. It never decides whether to "
        "interrupt you, and it cannot switch off the safety rules."
    )
    current_settings = api().get_service_settings()

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
        st.text_input(
            "Base URL (for OpenAI compatible / Ollama)",
            value=getattr(current_settings, "llm_base_url", None)
            or os.environ.get("WHA_LLM_BASE_URL", "https://api.gptplus5.com/v1"),
            key="sett_llm_base_url",
        )
    with col2:
        llm_model = st.text_input(
            "Model Name",
            value=current_settings.llm_model,
            key="sett_llm_model",
        )
        # Secrets are rendered as password fields and never echoed back
        st.text_input(
            "API Key",
            value="",
            type="password",
            placeholder="Enter API key to update (never echoed)",
            key="sett_llm_key",
        )

    if st.button("🧪 Test LLM Provider", key="btn_test_llm"):
        # Deliberately not written into os.environ. The dashboard process is shared by
        # every browser session, so promoting one visitor's key or endpoint to process
        # environment would leak it into all of them and outlive the request.
        st.info(f"Testing `{llm_provider}` with model `{llm_model}`...")
        chk = api().test_llm_connection(provider=llm_provider, model=llm_model)
        if chk.ok:
            st.success(f"✅ {chk.detail} ({chk.latency_ms}ms)")
        else:
            st.error(f"❌ {chk.detail} ({chk.latency_ms}ms)")


def render_notifications_section(subject_id: str) -> None:
    """Render Telegram notification settings and bot setup instructions."""
    st.subheader("How you get asked")
    current_settings = api().get_service_settings()

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
            token_val = st.session_state.get("sett_tg_token") or None
            chk = api().test_telegram_connection(token=token_val)
            if chk.ok:
                st.success(f"✅ {chk.detail} ({chk.latency_ms}ms)")
            else:
                st.error(f"❌ {chk.detail} ({chk.latency_ms}ms)")

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
    st.subheader("How often you get asked")
    st.caption(
        "The system only asks a question when the answer would genuinely change what "
        "it concludes. These limits cap it regardless."
    )
    current_settings = api().get_service_settings()

    col1, col2, col3 = st.columns(3)
    with col1:
        inter_budget = st.number_input(
            "Most questions per week",
            min_value=1,
            max_value=14,
            value=current_settings.interruption_budget_per_week,
            help="A hard cap. Once reached, nothing else will ask you until next week.",
            key="sett_inter_budget",
        )
    with col2:
        depth_budget = st.number_input(
            "Most questions per investigation",
            min_value=1,
            max_value=10,
            value=current_settings.depth_budget_per_episode,
            help="Stops one investigation asking you over and over.",
            key="sett_depth_budget",
        )
    with col3:
        cost_weight = st.number_input(
            "How much being interrupted bothers you",
            min_value=0.0,
            max_value=2.0,
            step=0.05,
            value=current_settings.policy_cost_weight,
            help=(
                "Higher means the system needs to be more certain a question is worth "
                "it before asking. Lower means it asks more often and is right more "
                "often. See EVALUATION.md for the measured trade-off."
            ),
            key="sett_cost_weight",
        )

    if st.button("Save", key="btn_save_settings"):
        patch = SettingsPatch(
            interruption_budget_per_week=int(inter_budget),
            depth_budget_per_episode=int(depth_budget),
            policy_cost_weight=float(cost_weight),
            notify_channel=st.session_state.get("sett_notify_channel"),
            llm_provider=st.session_state.get("sett_llm_provider"),
            llm_model=st.session_state.get("sett_llm_model"),
            llm_base_url=st.session_state.get("sett_llm_base_url"),
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
        api().update_settings(patch, subject_id=subject_id)
        st.success("Saved. The change is recorded in the audit record.")


def render_data_privacy_section(subject_id: str) -> None:
    """Render Data Management and Delete-All under typed confirmation."""
    st.subheader("Delete everything")
    st.warning(
        "This removes every heart rate reading, every night, every investigation, "
        "every question and answer, the audit record, and what the AI remembered "
        "between steps. It cannot be undone and there is no backup."
    )

    confirm_text = st.text_input(
        "Type DELETE to confirm",
        key="sett_delete_confirm",
    )

    if st.button("Delete all my data", type="primary", key="btn_delete_all"):
        if confirm_text.strip() == "DELETE":
            api().delete_all_subject_data(subject_id)
            st.error("Everything has been deleted.")
        else:
            st.warning("Nothing was deleted. Type DELETE exactly to confirm.")


def render_settings_page(subject_id: str) -> None:
    """Render complete Settings page."""
    render_status_strip(subject_id)
    st.write("---")

    render_profile_section(subject_id)
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
