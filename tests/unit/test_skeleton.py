"""Unit tests for project skeleton and configuration."""

import os
from pathlib import Path

from typer.testing import CliRunner

import wha
from wha.cli import app

CONTRACT_KEYS = [
    "WHA_DB_PATH",
    "WHA_SUBJECT",
    "WHA_TIMEZONE",
    "WHA_BRIDGE_HOST",
    "WHA_BRIDGE_PORT",
    "WHA_BRIDGE_TOKEN",
    "WHA_LLM_PROVIDER",
    "WHA_LLM_BASE_URL",
    "WHA_LLM_API_KEY",
    "WHA_LLM_MODEL",
    "WHA_CASSETTE_DIR",
    "WHA_TELEGRAM_TOKEN",
    "WHA_TELEGRAM_CHAT_ID",
    "WHA_NOTIFY_CHANNEL",
    "WHA_DATA_DIR",
]


def test_package_imports() -> None:
    """Importing wha package succeeds."""
    assert wha.__version__ == "0.1.0"


def test_env_example_covers_every_key() -> None:
    """Every key in the contract table appears in .env.example."""
    env_example = Path(__file__).parents[2] / ".env.example"
    assert env_example.exists(), ".env.example missing"
    content = env_example.read_text(encoding="utf-8")
    for key in CONTRACT_KEYS:
        assert key in content, f"Key {key} missing from .env.example"


def test_console_script_resolves() -> None:
    """WHA CLI returns 0 on --help."""
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Wearable Health Early Warning Agent" in result.output


def test_conftest_forces_cassette() -> None:
    """Autouse fixture overrides WHA_LLM_PROVIDER to cassette."""
    assert os.environ.get("WHA_LLM_PROVIDER") == "cassette"
