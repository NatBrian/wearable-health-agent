"""Settings: everything configurable, present and explained."""

from streamlit.testing.v1 import AppTest

from tests.ui.conftest import page
from wha.models import ConnectionCheck, Settings, SubjectProfile

PAGE = page("pages/4_Settings.py")

# Fields the application holds that are not a person's decision from a screen. Each needs
# a reason, and the reason is read by a person rather than checked by the test.
NOT_USER_EDITABLE: set[str] = set()

# What each settings field is called on screen. A field with no entry fails the
# completeness test, which is how a setting added later cannot stay invisible.
CONTROL_FOR_FIELD = {
    "interruption_budget_per_week": "Most questions in a week",
    "depth_budget_per_episode": "Most questions in one investigation",
    "policy_cost_weight": "How much an interruption costs you",
    "notify_channel": "Where questions should reach you",
    "llm_provider": "Which kind of model",
    "llm_model": "Model name",
    "llm_base_url": "Where that model lives",
    "bridge_host": "Your phone's address on this network",
}


def _ready(fake_api) -> None:
    fake_api.get_service_settings.return_value = Settings(
        interruption_budget_per_week=2,
        depth_budget_per_episode=3,
        policy_cost_weight=0.15,
        notify_channel="telegram",
        llm_provider="openai_compatible",
        llm_model="deepseek-chat",
        llm_base_url="https://example.invalid/v1",
        bridge_host="127.0.0.1",
    )
    fake_api.get_subject_profile.return_value = SubjectProfile(subject_id="sim")
    fake_api.check_component.return_value = ConnectionCheck(ok=True, detail="reachable")


def _controls(app: AppTest) -> list:
    return (
        list(app.text_input)
        + list(app.number_input)
        + list(app.selectbox)
        + list(app.text_area)
        + list(app.checkbox)
    )


def test_the_page_renders_without_an_exception(fake_api) -> None:
    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert not app.exception


def test_every_settings_field_the_application_accepts_has_a_control(fake_api) -> None:
    """A setting with no control is a setting nobody can change.

    Enumerated from the model rather than from a list somebody maintains, so a field added
    to the application fails this until the screen grows a control for it.
    """
    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()
    labels = [c.label for c in _controls(app)]

    missing = []
    for field in Settings.model_fields:
        if field in NOT_USER_EDITABLE:
            continue
        expected = CONTROL_FOR_FIELD.get(field)
        if expected is None or expected not in labels:
            missing.append(field)

    assert not missing, f"settings with no control on the screen: {missing}"


def test_every_profile_field_the_application_accepts_has_a_control(fake_api) -> None:
    """The same rule for the standing facts, which change how the safety rules behave."""
    from wha.models import SubjectProfilePatch

    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()
    labels = " ".join(c.label.lower() for c in _controls(app))

    for field, phrase in {
        "age_years": "age",
        "sex": "sex",
        "known_vascular_disease": "vascular",
        "menstruates": "menstruate",
        "rate_lowering_medicine": "slows my heart rate",
        "notes_for_doctor": "doctor",
    }.items():
        assert field in SubjectProfilePatch.model_fields
        assert phrase in labels, field


def test_every_control_says_what_it_changes(fake_api) -> None:
    """A field with no consequence stated is a field nobody can decide about."""
    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    without_help = [c.label for c in _controls(app) if not getattr(c, "help", None)]
    # The delete confirmation is the exception: its whole surrounding block is the warning.
    without_help = [label for label in without_help if "Type the name" not in label]

    assert not without_help, f"controls that do not say what they change: {without_help}"


def test_a_secret_is_never_read_back_into_the_screen(fake_api) -> None:
    """A password field pre-filled from storage is a secret on display."""
    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    # AppTest exposes the underlying proto, which is where the input's type lives.
    secrets = [c for c in app.text_input if c.proto.type == c.proto.PASSWORD]
    assert secrets, "no secret fields rendered at all"
    assert all(c.value == "" for c in secrets)


def test_delete_everything_names_what_it_deletes_and_refuses_without_confirmation(
    fake_api,
) -> None:
    """This function once reported success and deleted nothing.

    It is the highest-stakes control here, so the page states what goes and the call only
    happens when the typed name matches.
    """
    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    warning = " ".join(w.value.lower() for w in app.warning)
    assert "every heart rate reading" in warning

    delete = next(b for b in app.button if b.label.startswith("Delete everything about"))
    delete.click().run()

    assert fake_api.delete_all_subject_data.call_count == 0
    assert any("did not match" in e.value for e in app.error)


def test_confirming_the_name_does_delete(fake_api) -> None:
    """The refusal above must be a confirmation step, not a broken button."""
    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    confirm = next(c for c in app.text_input if "Type the name" in c.label)
    confirm.set_value("sim").run()
    next(b for b in app.button if b.label.startswith("Delete everything about")).click().run()

    fake_api.delete_all_subject_data.assert_called_once_with("sim")
