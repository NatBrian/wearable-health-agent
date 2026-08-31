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
