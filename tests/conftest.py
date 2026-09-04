"""Pytest configuration and global fixtures."""

from pathlib import Path

import pytest
from pytest import MonkeyPatch


@pytest.fixture(scope="session")
def monkeypatch_session():
    """Session-scoped monkeypatch."""
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture(autouse=True, scope="session")
def _force_cassette_provider(monkeypatch_session):
    """Force cassette provider in all tests, overriding .env."""
    monkeypatch_session.setenv("WHA_LLM_PROVIDER", "cassette")


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    """Provide a path to a temporary SQLite database."""
    return tmp_path / "test_wha.sqlite"


# --- screens read their thresholds from the application over HTTP --------------------
#
# A rendering test should not need a running server, and it should not need hand-written
# numbers either: a test asserting a screen says "7 nights" against a hardcoded 7 would
# keep passing after the constant changed. So the config endpoint is served from the real
# constants module, in process.
#
# Here rather than in tests/ui/ because screens are rendered from integration and service
# tests too, and those were failing on a refused connection to the API.


def _real_config() -> dict[str, object]:
    from wha import constants
    from wha.clock import local_today

    exported: dict[str, object] = {
        name: getattr(constants, name)
        for name in dir(constants)
        if name.isupper()
        and isinstance(
            getattr(constants, name), str | int | float | bool | list | dict | type(None)
        )
    }
    exported["today"] = local_today().isoformat()
    exported["configured_subject"] = "sub_test"
    return exported


@pytest.fixture(autouse=True)
def _api_without_a_server():
    """Point the shared client at the API running in this process.

    Screens talk to the application over HTTP now. Mocking each client method in each test
    would leave the boundary itself untested, which is the part most likely to break: a
    renamed field passes silently through JSON in a way it never did through a Python call.
    So the real FastAPI app is mounted in-process and the client is bound to it.

    Config is still substituted, because it is read on nearly every render and building it
    from the constants module directly keeps a screen test from asserting a hardcoded
    threshold that has since changed.
    """
    from unittest.mock import patch

    from fastapi.testclient import TestClient

    from wha.api import client as client_module
    from wha.api.app import app as api_app

    previous = client_module._client
    client_module._client = client_module.ApiClient(
        base_url="http://testserver", client=TestClient(api_app)
    )
    with patch("wha.api.client.ApiClient.config", return_value=_real_config()):
        from wha.ui.components import api as api_module

        api_module.config.clear()
        yield
        api_module.config.clear()
    client_module._client = previous
