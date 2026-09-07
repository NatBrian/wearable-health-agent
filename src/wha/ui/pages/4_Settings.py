"""Settings: everything that can be changed, grouped, and each one saying what it changes.

Two rules this page is built on:

* **Every field the application accepts has a control here.** A test enumerates them from
  the model rather than from a list somebody maintains, so a setting added tomorrow fails
  that test until this page grows a control for it.
* **Every control says what it changes about the system's behaviour**, not what the field
  is called. "Interruption budget" is a field name; "how many times a week this may
  interrupt you" is what a person is deciding.

Secrets are write-only. They render as password fields, are never read back, and are
deliberately not promoted into the process environment: the dashboard process is shared by
every browser session, so one visitor's key would leak into all of them and outlive the
request.
"""

import streamlit as st

from wha.api.client import ApiUnavailable
from wha.ui import design
from wha.ui.components.api import api, unavailable
from wha.ui.components.status_bar import render as render_status_bar
from wha.ui.components.subject import resolve as resolve_subject


def render_profile(subject: str) -> None:
    """Five standing facts, each read by something named. Nothing is collected for show."""
    st.subheader("About you")
    st.caption(
        "Only what something in this system actually reads. Nothing here is collected "
        "because it might be useful later."
    )
    profile = api().get_subject_profile(subject)

    left, right = st.columns(2)
    with left:
        age = st.number_input(
            "Your age",
            min_value=0,
            max_value=120,
            value=int(profile.age_years or 0),
            help=(
                "The published checklist used for chest pain was tested only on people "
                "aged thirty-five and over. Without your age it cannot be applied to you "
                "safely, so it is not applied at all."
            ),
        )
        sex = st.selectbox(
            "Sex",
            ["not said", "female", "male"],
            index=["not said", "female", "male"].index(profile.sex or "not said"),
            help="Read by the same published checklist, which scores it as the study did.",
        )
    with right:
        vascular = st.checkbox(
            "I have a known heart or vascular condition",
            value=bool(profile.known_vascular_disease),
            help="Raises how cautiously the safety rules treat chest symptoms.",
        )
        menstruates = st.checkbox(
            "I menstruate",
            value=bool(profile.menstruates),
            help=(
                "Lets the cycle be considered as an ordinary explanation for a raised "
                "night, instead of it being treated as unexplained."
            ),
        )
        medicine = st.checkbox(
            "I take medicine that slows my heart rate",
            value=bool(profile.rate_lowering_medicine),
            help=(
                "Read by nothing, on purpose. It appears in your record as a disclosure "
                "so anyone reading it knows, rather than quietly changing a threshold."
            ),
        )

    notes = st.text_area(
        "Anything you want a doctor to see",
        value=profile.notes_for_doctor or "",
        help=(
            "Goes into the summary for your doctor and into no AI prompt. Information for "
            "a doctor is not information for the model."
        ),
    )

    if st.button("Save these", key="save_profile"):
        api().update_subject_profile(
            subject,
            age_years=int(age) or None,
            sex=None if sex == "not said" else sex,
            known_vascular_disease=vascular,
            menstruates=menstruates,
            rate_lowering_medicine=medicine,
            notes_for_doctor=notes or None,
        )
        st.success("Saved.")


def render_source(settings) -> dict:
    """Where readings come from."""
    st.subheader("Where your readings come from")
    bridge_host = st.text_input(
        "Your phone's address on this network",
        value=settings.bridge_host or "",
        help=(
            "The app on your phone serves your watch data at this address. If it is wrong "
            "or the phone is asleep, no new night can be measured."
        ),
    )
    bridge_token = st.text_input(
        "Phone access token",
        value="",
        type="password",
        help="Stored on this machine only, and never shown again after you save it.",
    )
    if st.button("Test the connection to my phone", key="test_bridge"):
        result = api().check_component("bridge", bridge_host=bridge_host or None)
        st.success(result.detail) if result.ok else st.error(result.detail)

    return {"bridge_host": bridge_host or None, "bridge_token": bridge_token or None}


def render_model(settings) -> dict:
    """The AI, which touches questions, summaries and chat, and nothing else."""
    st.subheader("The AI model")
    st.caption(
        "Used for wording questions, writing summaries and chat. Nothing that decides "
        "whether a night is unusual uses AI at all."
    )
    providers = ["cassette", "ollama_native", "openai_compatible"]
    provider = st.selectbox(
        "Which kind of model",
        providers,
        index=providers.index(settings.llm_provider),
        help=(
            "cassette replays recorded answers and never leaves this machine. "
            "ollama_native runs a model on this machine. openai_compatible sends your "
            "question to a remote service."
        ),
    )
    model = st.text_input(
        "Model name",
        value=settings.llm_model,
        help="Which model to ask. Changing it changes the wording you get, nothing else.",
    )
    base_url = st.text_input(
        "Where that model lives",
        value=settings.llm_base_url or "",
        help="Required for a remote or self-hosted model. Left empty for recorded answers.",
    )
    api_key = st.text_input(
        "Key for that service",
        value="",
        type="password",
        help="Stored on this machine only. Never shown again after you save it.",
    )
    if st.button("Test the model", key="test_llm"):
        result = api().check_component(
            "llm", llm_provider=provider, llm_model=model, llm_base_url=base_url or None
        )
        st.success(result.detail) if result.ok else st.error(result.detail)

    return {
        "llm_provider": provider,
        "llm_model": model,
        "llm_base_url": base_url or None,
        "llm_api_key": api_key or None,
    }


def render_contact(settings) -> dict:
    """How a question reaches the person."""
    st.subheader("How you get asked")
    channels = ["none", "telegram"]
    channel = st.selectbox(
        "Where questions should reach you",
        channels,
        index=channels.index(settings.notify_channel),
        help=(
            "With none, questions wait on this screen until you open it. With telegram "
            "they arrive on your phone and you can answer there."
        ),
    )
    token = st.text_input(
        "Telegram bot token",
        value="",
        type="password",
        help="Stored on this machine only. Never shown again after you save it.",
    )
    if st.button("Send myself a test message", key="test_telegram"):
        result = api().check_component("telegram")
        st.success(result.detail) if result.ok else st.error(result.detail)

    return {"notify_channel": channel, "telegram_token": token or None}


def render_budgets(settings) -> dict:
    """How often this may interrupt, and how hard it may work on one investigation."""
    st.subheader("How often you get asked")
    weekly = st.number_input(
        "Most questions in a week",
        min_value=0,
        max_value=20,
        value=settings.interruption_budget_per_week,
        help=(
            "A hard ceiling. Lower it and the system stays quieter, at the cost of "
            "sometimes concluding without asking the one question that would have helped."
        ),
    )
    depth = st.number_input(
        "Most questions in one investigation",
        min_value=0,
        max_value=10,
        value=settings.depth_budget_per_episode,
        help="Stops a single investigation asking you repeatedly over several nights.",
    )
    cost = st.number_input(
        "How much an interruption costs you",
        min_value=0.0,
        max_value=1.0,
        step=0.01,
        value=float(settings.policy_cost_weight),
        help=(
            "Raise it and only the most useful questions get asked. Lower it and you are "
            "asked more often. This is weighed against how much an answer would change "
            "the conclusion."
        ),
    )
    return {
        "interruption_budget_per_week": int(weekly),
        "depth_budget_per_episode": int(depth),
        "policy_cost_weight": float(cost),
    }


def render_delete(subject: str) -> None:
    """The highest-stakes control on the screen, and it once did nothing."""
    st.subheader("Delete everything")
    st.warning(
        "This erases everything held about you on this machine: every heart rate reading, "
        "every night, every investigation, every message and the record of all of it. It "
        "cannot be undone and nothing is kept elsewhere."
    )
    typed = st.text_input(
        f"Type the name of the person to delete, which is {subject}",
        key="delete_confirm",
    )
    if st.button("Delete everything about this person", type="primary", key="delete_all"):
        if typed != subject:
            st.error("The name did not match, so nothing was deleted.")
            return
        api().delete_all_subject_data(subject)
        st.success("Deleted. Nothing about this person is left on this machine.")


def main() -> None:
    st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")
    design.inject()

    try:
        # Resolved in one place. Reading `subjects[0]` here showed a different person on
        # this screen than on Home, with no indication that it had.
        subject = resolve_subject()
        if subject is None:
            st.warning("There is nobody to show yet.")
            return

        render_status_bar(subject)
        st.markdown(design.separator(), unsafe_allow_html=True)
        st.title("Settings")

        render_profile(subject)
        st.markdown(design.separator(), unsafe_allow_html=True)

        settings = api().get_service_settings()
        changes: dict = {}
        changes |= render_source(settings)
        st.markdown(design.separator(), unsafe_allow_html=True)
        changes |= render_model(settings)
        st.markdown(design.separator(), unsafe_allow_html=True)
        changes |= render_contact(settings)
        st.markdown(design.separator(), unsafe_allow_html=True)
        changes |= render_budgets(settings)

        if st.button("Save all of the above", type="primary", key="save_settings"):
            applied = api().update_settings(**{k: v for k, v in changes.items() if v is not None})
            st.success("Saved.")
            st.caption(f"Changed: {applied}")

        st.markdown(design.separator(), unsafe_allow_html=True)
        render_delete(subject)
    except ApiUnavailable as exc:
        unavailable(exc)


if __name__ == "__main__":
    main()
