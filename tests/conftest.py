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


@pytest.fixture(autouse=True, scope="session")
def _no_outbound_messages(monkeypatch_session):
    """No test may send a real message to a real phone.

    `get_notifier()` returns a live TelegramNotifier whenever a token and a chat id are
    present, and it reads them from `.env`, which on the development machine has both. So
    every test that reached an escalation was posting to a real person's Telegram, over
    the network, in a suite AGENTS.md describes as running offline. Slow, noisy, and
    capable of hanging the run on a network stall.

    Clearing the credentials makes `get_notifier()` fall back to NullNotifier, which is
    the transport a test should be exercising. A test that wants to assert what was sent
    should inject its own notifier rather than rely on the machine's configuration.
    """
    from wha.notify.null import NullNotifier

    # Patched at the factory rather than through the environment, because
    # pydantic-settings reads `.env` from disk and clearing the variable does not reach
    # it. Every caller imports get_notifier inside the function that uses it, from one of
    # these two names.
    monkeypatch_session.setattr("wha.notify.factory.get_notifier", lambda: NullNotifier())
    monkeypatch_session.setattr("wha.notify.get_notifier", lambda: NullNotifier())


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
        yield
    client_module._client = previous
