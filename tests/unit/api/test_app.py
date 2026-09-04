"""The HTTP boundary, which is what makes the dashboard replaceable."""

from fastapi.testclient import TestClient

from wha.api.app import app

client = TestClient(app)


def test_config_gives_a_client_the_numbers_it_must_not_hardcode() -> None:
    """The dashboard imported these from wha.constants, which a browser cannot do.

    It also meant a threshold could drift between a screen and the code that uses it.
    """
    from wha.constants import BASELINE_MIN_NIGHTS_PERSONAL, DETECT_RED_BPM

    body = client.get("/config").json()

    # Names match the source exactly, so a reader can find the constant and the reasoning
    # written above it without a mapping table.
    assert body["BASELINE_MIN_NIGHTS_PERSONAL"] == BASELINE_MIN_NIGHTS_PERSONAL
    assert body["DETECT_RED_BPM"] == DETECT_RED_BPM
    assert body["today"], "a client has no way to know the subject's local date"
    assert body["configured_subject"], "a client cannot read the environment"


def test_config_is_enumerated_so_it_cannot_drift_from_the_code() -> None:
    """Listing the constants by hand would let this endpoint fall behind the module.

    Every public constant is exported, so a threshold added tomorrow reaches an interface
    without anyone remembering to add it here.
    """
    from wha import constants

    body = client.get("/config").json()
    public = {n for n in dir(constants) if n.isupper()}
    serialisable = {
        n
        for n in public
        if isinstance(getattr(constants, n), str | int | float | bool | list | dict | type(None))
    }

    assert serialisable <= set(body), f"missing from /config: {sorted(serialisable - set(body))}"


def test_every_endpoint_a_screen_needs_is_present() -> None:
    """A missing endpoint means a screen that cannot be rebuilt in another framework."""
    paths = {r.path for r in app.routes if hasattr(r, "methods")}

    for required in (
        "/config",
        "/subjects",
        "/subjects/{subject_id}/status",
        "/subjects/{subject_id}/nights",
        "/subjects/{subject_id}/episodes",
        "/subjects/{subject_id}/pending",
        "/subjects/{subject_id}/conversation",
        "/subjects/{subject_id}/urgency",
        "/subjects/{subject_id}/handover",
        "/subjects/{subject_id}/audit",
        "/episodes/{episode_id}",
        "/episodes/{episode_id}/answer",
        "/settings",
    ):
        assert required in paths, required


def test_an_unknown_episode_is_a_404_not_an_empty_success() -> None:
    """A screen must be able to tell "no such thing" from "nothing to show"."""
    assert client.get("/episodes/does-not-exist").status_code == 404


def test_an_unknown_diagnostic_component_is_refused() -> None:
    """The component list is closed, like the tool registry."""
    assert client.post("/diagnostics/anything", json={}).status_code == 404


def test_the_openapi_schema_is_generated() -> None:
    """A React author needs the contract without reading Python."""
    schema = client.get("/openapi.json").json()
    assert schema["info"]["title"]
    assert "/config" in schema["paths"]


def test_localise_returns_a_datetime_callers_can_format() -> None:
    """It replaced wha.clock.to_local, whose callers call .strftime on the result.

    Returning a string turned every one of those into an AttributeError at render time,
    and no test caught it because none rendered the status strip with a timestamp actually
    present. Driving the dashboard did.
    """
    from datetime import UTC, datetime

    from wha.api.client import ApiClient

    api = ApiClient(base_url="http://testserver", client=client)
    result = api.localise(datetime(2026, 9, 4, 5, 0, tzinfo=UTC))

    assert isinstance(result, datetime)
    assert result.strftime("%H:%M")
