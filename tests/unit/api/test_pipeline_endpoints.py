"""The night pipeline over HTTP, so a front end that is not Streamlit can draw it."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from wha.api.app import app
from wha.models import (
    CANONICAL_PIPELINE_STEPS,
    DetectionLevel,
    NightPipeline,
    PipelineHeadline,
    PipelineNightRef,
    PipelineStepView,
    StepStatus,
)

client = TestClient(app)


def _pipeline() -> NightPipeline:
    return NightPipeline(
        subject_id="sim",
        night_date=date(2026, 9, 4),
        episode_id="ep_1",
        headline=PipelineHeadline(level=DetectionLevel.RED, flagged=True),
        steps=[
            PipelineStepView(
                step_id=definition.step_id,
                ordinal=definition.ordinal,
                layer=definition.layer,
                status=StepStatus.RAN,
                reason=f"reason for {definition.step_id}",
            )
            for definition in CANONICAL_PIPELINE_STEPS
        ],
    )


@pytest.fixture
def stub_service(monkeypatch):
    """The endpoints are pass-throughs, so what is tested here is routing and shape.

    Reaching the real database would make this test depend on a machine having data in
    it, which a fresh checkout does not.
    """
    monkeypatch.setattr(
        "wha.api.app.service.get_night_pipeline",
        lambda subject_id, night_date: _pipeline(),
    )
    monkeypatch.setattr(
        "wha.api.app.service.list_pipeline_nights",
        lambda subject_id, days=60, end=None: [
            PipelineNightRef(
                night_date=date(2026, 9, 4),
                level=DetectionLevel.RED,
                has_episode=True,
                usable=True,
            )
        ],
    )


def test_the_pipeline_endpoint_returns_every_step(stub_service) -> None:
    response = client.get("/subjects/sim/nights/2026-09-04/pipeline")

    assert response.status_code == 200
    body = response.json()
    assert [s["ordinal"] for s in body["steps"]] == [d.ordinal for d in CANONICAL_PIPELINE_STEPS]
    assert body["headline"]["level"] == "RED"


def test_a_step_carries_everything_a_screen_needs_to_explain_it(stub_service) -> None:
    """Layer and status reach the client, because the screen colours and dims by them."""
    body = client.get("/subjects/sim/nights/2026-09-04/pipeline").json()
    step = body["steps"][0]

    assert set(step) >= {
        "step_id",
        "ordinal",
        "layer",
        "status",
        "reason",
        "headline_figure",
        "occurred_utc",
        "inputs",
        "outputs",
        "sources",
        "detail_json",
    }


def test_an_unknown_night_is_a_404_not_a_500(monkeypatch) -> None:
    """A client has to tell "no such thing" from "the application broke"."""

    def _raise(subject_id, night_date):
        raise ValueError("No such night")

    monkeypatch.setattr("wha.api.app.service.get_night_pipeline", _raise)

    assert client.get("/subjects/sim/nights/1999-01-01/pipeline").status_code == 404


def test_the_night_list_is_small_enough_to_load_sixty_at_once(stub_service) -> None:
    """The stepper loads every night in the window, so each entry stays minimal."""
    response = client.get("/subjects/sim/pipeline/nights?days=60")

    assert response.status_code == 200
    assert set(response.json()[0]) == {"night_date", "level", "has_episode", "usable"}


def test_both_routes_are_registered() -> None:
    """Route order matters in FastAPI, and this is cheaper than reasoning about it."""
    paths = {r.path for r in app.routes if hasattr(r, "methods")}

    assert "/subjects/{subject_id}/nights/{night_date}/pipeline" in paths
    assert "/subjects/{subject_id}/pipeline/nights" in paths


def test_a_window_ends_where_the_record_ends_not_at_the_calendar(monkeypatch) -> None:
    """A night dated after today is real, and every screen hid it.

    The mock watch advances the cursor past the wall clock, which the simulation runbook
    documents. Ending each window at local_today() meant Today showed a green night from
    yesterday while a red one sat unshown in the record.
    """
    from datetime import date as _date

    from wha.api import app as api_app

    monkeypatch.setattr(
        api_app.service, "latest_recorded_night", lambda subject_id: _date(2026, 9, 7)
    )
    monkeypatch.setattr(api_app, "local_today", lambda: _date(2026, 9, 6))

    assert api_app._record_end("sim") == _date(2026, 9, 7)


def test_a_record_behind_today_still_ends_today(monkeypatch) -> None:
    """The usual case: the newest reading is older than today, and the nights since then
    are shown as the gaps they are rather than being cut off the end of the window."""
    from datetime import date as _date

    from wha.api import app as api_app

    monkeypatch.setattr(
        api_app.service, "latest_recorded_night", lambda subject_id: _date(2026, 9, 1)
    )
    monkeypatch.setattr(api_app, "local_today", lambda: _date(2026, 9, 6))

    assert api_app._record_end("sim") == _date(2026, 9, 6)


def test_an_empty_record_ends_today(monkeypatch) -> None:
    from datetime import date as _date

    from wha.api import app as api_app

    monkeypatch.setattr(api_app.service, "latest_recorded_night", lambda subject_id: None)
    monkeypatch.setattr(api_app, "local_today", lambda: _date(2026, 9, 6))

    assert api_app._record_end("sim") == _date(2026, 9, 6)
