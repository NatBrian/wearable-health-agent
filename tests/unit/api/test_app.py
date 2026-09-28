"""The HTTP boundary, which is what makes the dashboard replaceable."""

import pytest
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


def test_cors_allows_only_the_loopback_vite_origin_and_required_headers() -> None:
    response = client.options(
        "/subjects/me/nights",
        headers={
            "Origin": "http://127.0.0.1:8443",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:8443"
    assert "*" not in response.headers.get("access-control-allow-methods", "")
    assert "*" not in response.headers.get("access-control-allow-headers", "")


def test_cors_rejects_an_unlisted_origin() -> None:
    response = client.options(
        "/subjects/me/nights",
        headers={
            "Origin": "https://unlisted.invalid",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-origin" not in response.headers


def test_cors_origin_list_comes_from_backend_configuration(monkeypatch) -> None:
    from pydantic import ValidationError

    from wha.config import Settings

    monkeypatch.setenv(
        "WHA_CORS_ALLOWED_ORIGINS",
        "http://127.0.0.1:8443, http://localhost:8443",
    )

    assert Settings().dashboard_origins == [
        "http://127.0.0.1:8443",
        "http://localhost:8443",
    ]

    monkeypatch.setenv("WHA_CORS_ALLOWED_ORIGINS", "*")
    try:
        Settings()
    except ValidationError:
        pass
    else:
        raise AssertionError("the backend configuration accepted a wildcard CORS origin")


def test_dashboard_config_exposes_history_windows_and_schema_control_bounds() -> None:
    from wha.constants import N_CAUSES

    dashboard = client.get("/config").json()["dashboard"]

    assert dashboard["history_windows_days"] == [30, 60, 90, 365]
    assert dashboard["steps_average_days"] == 7
    assert dashboard["cause_combinations"] == 2**N_CAUSES
    assert dashboard["settings_bounds"] == {
        "age_years": {"minimum": 0, "maximum": 120},
        "interruption_budget_per_week": {"minimum": 0, "maximum": 20},
        "depth_budget_per_episode": {"minimum": 0, "maximum": 10},
        "policy_cost_weight": {"minimum": 0, "maximum": 1, "step": 0.01},
    }


def test_night_endpoint_applies_history_filters_server_side(monkeypatch) -> None:
    from datetime import date

    from wha.models import DetectionLevel, NightRow

    rows = [
        NightRow(
            night_date=date(2026, 9, 1),
            coverage_minutes=400,
            usable=True,
            level=DetectionLevel.RED,
            episode_id="ep_red",
            rhr_bpm=80,
        ),
        NightRow(
            night_date=date(2026, 9, 2),
            coverage_minutes=400,
            usable=True,
            level=DetectionLevel.RED,
            episode_id=None,
            rhr_bpm=80,
        ),
        NightRow(
            night_date=date(2026, 9, 3),
            coverage_minutes=400,
            usable=True,
            level=DetectionLevel.GREEN,
            episode_id="ep_green",
            rhr_bpm=60,
        ),
    ]
    monkeypatch.setattr("wha.api.app.service.list_nights", lambda *args, **kwargs: rows)

    response = client.get("/subjects/sim/nights?days=3&level=RED&investigated_only=true")

    assert response.status_code == 200
    assert [row["night_date"] for row in response.json()] == ["2026-09-01"]


def test_dashboard_summary_endpoint_uses_the_configured_calendar_window(monkeypatch) -> None:
    from datetime import date

    from wha.models import DashboardSummary

    received = []

    def summary(subject_id, end, steps_window_days):
        received.append((subject_id, end, steps_window_days))
        return DashboardSummary(
            latest_sleep_hours=None,
            latest_sleep_night=None,
            latest_steps=None,
            latest_steps_night=None,
            steps_average=None,
            steps_window_start=date(2026, 9, 1),
            steps_window_end=end,
        )

    monkeypatch.setattr("wha.api.app.service.get_dashboard_summary", summary)
    response = client.get("/subjects/sim/dashboard-summary?end=2026-09-07")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "latest_sleep_hours",
        "latest_sleep_night",
        "latest_steps",
        "latest_steps_night",
        "steps_average",
        "steps_window_start",
        "steps_window_end",
    }
    assert body["steps_window_start"] == "2026-09-01"
    assert body["steps_window_end"] == "2026-09-07"
    assert received == [("sim", date(2026, 9, 7), 7)]


def test_settings_and_profile_models_keep_the_legacy_control_ranges() -> None:
    from pydantic import ValidationError

    from wha.models import SettingsPatch, SubjectProfilePatch

    assert SettingsPatch(
        interruption_budget_per_week=20,
        depth_budget_per_episode=10,
        policy_cost_weight=1.0,
    )
    assert SubjectProfilePatch(age_years=120)
    for invalid in (
        lambda: SettingsPatch(interruption_budget_per_week=21),
        lambda: SettingsPatch(depth_budget_per_episode=11),
        lambda: SettingsPatch(policy_cost_weight=1.01),
        lambda: SubjectProfilePatch(age_years=121),
    ):
        try:
            invalid()
        except ValidationError:
            continue
        raise AssertionError("the API model accepted a value outside the legacy control range")


def test_settings_route_passes_a_validated_patch_to_the_service(monkeypatch) -> None:
    received = []
    monkeypatch.setattr(
        "wha.api.app.service.update_settings", lambda patch: received.append(patch) or patch
    )

    response = client.post("/settings", json={"llm_model": "local-model"})

    assert response.status_code == 200
    assert received[0].llm_model == "local-model"

    invalid = client.post("/settings", json={"interruption_budget_per_week": 21})
    assert invalid.status_code == 422


def test_profile_route_enforces_the_legacy_age_range(monkeypatch) -> None:
    monkeypatch.setattr("wha.api.app.service.update_subject_profile", lambda *args, **kwargs: None)

    response = client.post("/subjects/sim/profile", json={"age_years": 121})

    assert response.status_code == 422


def test_audit_export_receives_the_same_date_filters_as_the_query(monkeypatch) -> None:
    captured = []

    def export(filters, path):
        captured.append(filters)
        path.write_text("event", encoding="utf-8")

    monkeypatch.setattr("wha.api.app.service.export_audit", export)

    response = client.get(
        "/subjects/sim/audit/export?actor=human&since_utc=2026-09-01T00:00:00Z"
        "&until_utc=2026-09-08T00:00:00Z"
    )

    assert response.status_code == 200
    assert response.json() == {"content": "event"}
    assert captured[0].actor == "human"
    assert captured[0].since_utc.isoformat() == "2026-09-01T00:00:00+00:00"
    assert captured[0].until_utc.isoformat() == "2026-09-08T00:00:00+00:00"


def test_provenance_summary_counts_entries_not_figures(monkeypatch) -> None:
    monkeypatch.setattr(
        "wha.service.belief.get_knowledge_provenance",
        lambda: {
            "assumed": {"provenance": "ASSUMED", "has_unevidenced_number": "no"},
            "derived-with-gap": {"provenance": "DERIVED", "has_unevidenced_number": "yes"},
            "derived": {"provenance": "DERIVED", "has_unevidenced_number": "no"},
            "cited": {"provenance": "CITED", "has_unevidenced_number": "no"},
        },
    )

    response = client.get("/knowledge/provenance/summary")

    assert response.status_code == 200
    assert response.json() == {"unevidenced_entries": 2, "total_entries": 4}


def test_llm_diagnostic_uses_unsaved_values_without_echoing_the_secret(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def diagnostic(**values: object) -> dict[str, object]:
        captured.update(values)
        return {"ok": True, "detail": "Connected to the selected provider", "latency_ms": 4}

    monkeypatch.setattr("wha.api.app.service.test_llm_connection", diagnostic)
    secret = "private-diagnostic-key"
    response = client.post(
        "/diagnostics/llm",
        json={
            "provider": "openai_compatible",
            "model": "model-a",
            "base_url": "http://127.0.0.1:9000/v1",
            "api_key": secret,
        },
    )

    assert response.status_code == 200
    assert captured == {
        "provider": "openai_compatible",
        "model": "model-a",
        "base_url": "http://127.0.0.1:9000/v1",
        "api_key": secret,
    }
    assert secret not in response.text


def test_subject_delete_route_protects_the_real_subject(monkeypatch) -> None:
    deleted: list[str] = []
    monkeypatch.setattr("wha.api.app.service.delete_all_subject_data", deleted.append)

    response = client.delete("/subjects/me")

    assert response.status_code == 403
    assert deleted == []


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


def test_the_documented_endpoint_count_matches_the_app() -> None:
    """Four live documents published "28 endpoints" while the app served 31.

    A number repeated across four files with no single source drifts the moment anyone adds
    a route, and nothing notices. This reads the count from the app and from the documents,
    so adding an endpoint fails here rather than quietly making the docs wrong.
    """
    import re
    from pathlib import Path

    actual = len({(r.path, tuple(sorted(r.methods))) for r in app.routes if hasattr(r, "methods")})
    assert actual > 20, "route table looks wrong, this test would prove nothing"

    repo = Path(__file__).resolve().parents[3]
    # LIVE documents only. archive/ is finished work and is deliberately not checked:
    # a record written in September 2026 was accurate then, and rewriting it so a test
    # passes would turn the history into fiction.
    documents = [
        repo / "README.md",
        repo / "docs" / "ARCHITECTURE.md",
    ]

    wrong: list[str] = []
    for path in documents:
        if not path.exists():
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in re.finditer(r"(\d+) endpoints", line):
                if int(match.group(1)) != actual:
                    wrong.append(
                        f"{path.relative_to(repo)}:{i}: says {match.group(1)}, app has {actual}"
                    )

    assert not wrong, "the documented endpoint count is stale:\n  " + "\n  ".join(wrong)


def test_no_document_quotes_a_policy_accuracy_the_eval_did_not_produce() -> None:
    """Three live documents published an "Always ask" accuracy of 0.925. It is 0.825.

    `run_policy_eval` was fixed in an earlier session to run the real policies through the
    real belief model, and it wrote 0.825 to data/eval/policy.json. The documents kept the
    old constant, which is the figure from when the suite returned hardcoded numbers no
    policy had produced.
    """
    import json
    from pathlib import Path

    repo = Path(__file__).resolve().parents[3]
    results = repo / "data" / "eval" / "policy.json"
    if not results.exists():
        pytest.skip("policy.json not generated on this machine")

    metrics = json.loads(results.read_text(encoding="utf-8")).get("metrics", {})
    always_ask = metrics.get("always_ask_mean_accuracy")
    assert always_ask is not None, "policy.json has no always-ask accuracy"

    superseded = "0.925"

    # Records that quote the wrong number ON PURPOSE are excluded by name.
    # archive/review-2026-09/AUDIT-2026-09-05.md is the independent audit that FOUND this mismatch; it
    # quotes 0.925 as the finding, and rewriting it to say 0.825 would erase the thing it
    # exists to record. Its own header says it is kept unedited. The changelog and the
    # blocker file are the same shape: a correction has to be able to name what it
    # corrected.
    PRESERVED_RECORDS = {"AUDIT-2026-09-05.md", "KNOWLEDGE-CHANGELOG.md"}

    # The retracted figure must not appear at all, on any line, rather than only on lines
    # labelled "Always ask". The first version of this test required both on one line and
    # therefore missed docs/DESIGN-DATA-CHANNELS.md, which phrases it as "asks one
    # well-chosen question scores 0.925" with no label. Caught by reintroducing the number
    # and watching the test pass anyway.
    searched = list(repo.glob("docs/*.md")) + [
        repo / "README.md",
        repo / "README.md",
        repo / "AGENTS.md",
        repo / "EVALUATION.md",
    ]
    wrong: list[str] = []
    for path in searched:
        if path.name in PRESERVED_RECORDS or not path.exists():
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if superseded in line:
                wrong.append(f"{path.relative_to(repo)}:{i}: {line.strip()[:80]}")

    assert not wrong, (
        f"the measured always-ask accuracy is {always_ask}, and these still say {superseded}:\n  "
        + "\n  ".join(wrong)
    )
