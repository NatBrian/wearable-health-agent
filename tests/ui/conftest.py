"""Every interface test runs the real script against a fake application.

`AppTest` runs the Streamlit script exactly as the browser does, so a page that raises on
import fails here rather than in front of a person. That matters in this repository more
than most: a full suite once passed while an import error made the Today page impossible
to open, because no test rendered a page.

Patching `get_client` means no server, no database and no network, while the screens still
go through the same HTTP client they use in production. Return values are real
`wha.models` instances rather than dicts, so a renamed field fails the test instead of
passing silently through JSON.
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# AppTest resolves a relative path against the test file, so screens are addressed
# through the installed package instead. That also means these tests exercise the same
# files `wha serve` runs, not a copy.
import wha.ui
from wha.models import BaselineRung, ComponentStatus, Subject, SystemStatus

UI_ROOT = Path(wha.ui.__file__).parent


def page(name: str) -> str:
    """The path of a screen, as AppTest wants it."""
    return str(UI_ROOT / name)


# Thresholds come from the real constants rather than being typed here. A fixture that
# hardcodes them passes while the screen and the code disagree, which is the exact class
# of drift the /config endpoint exists to prevent.
def _thresholds() -> dict:
    from wha import constants

    return {
        name: getattr(constants, name)
        for name in dir(constants)
        if name.isupper()
        and isinstance(
            getattr(constants, name), str | int | float | bool | list | dict | type(None)
        )
    }


CONFIG = {
    "today": "2026-09-05",
    "configured_subject": "sim",
    "DETECT_YELLOW_BPM": 3.0,
    "DETECT_RED_BPM": 4.0,
    "DETECT_PERSISTENCE_NIGHTS": 2,
    "BASELINE_MIN_NIGHTS_PERSONAL": 7,
    "RECENT_NIGHTS_WINDOW": 7,
    "SOURCE_LABEL_PREFIXES": {"medlineplus": "MedlinePlus"},
    "SOURCE_LABEL_FALLBACK": "this repository's own knowledge",
    "EXTERNAL_SOURCE_PREFIX": "medlineplus",
    **_thresholds(),
}


def working_status() -> SystemStatus:
    now = datetime(2026, 9, 5, 7, 12, tzinfo=UTC)
    return SystemStatus(
        components=[
            ComponentStatus(
                component=name,
                ok=True,
                detail="working",
                severity="ok",
                checked_at_utc=now,
            )
            for name in ("bridge", "scheduler", "llm", "telegram", "database", "datasets")
        ],
        last_ingest_utc=now,
        last_nightly_utc=now,
        usable_nights=28,
        rung=BaselineRung.MATURE,
        errors_24h=0,
        quiet_nights_streak=14,
    )


@pytest.fixture
def fake_api(monkeypatch):
    """A client that answers every call, so a screen fails on its own logic or not at all."""
    client = MagicMock()
    client.config.return_value = CONFIG
    client.list_subjects.return_value = [
        Subject(
            subject_id="sim",
            label="Simulated",
            source_kind="synthetic",
            timezone="Asia/Singapore",
            usable_nights=28,
            rung=BaselineRung.MATURE,
        )
    ]
    client.get_system_status.return_value = working_status()
    client.localise.side_effect = lambda moment: moment
    client.get_knowledge_provenance.return_value = {
        "fever_likelihood": {"provenance": "CITED"},
        "guess_one": {"provenance": "ASSUMED"},
        "guess_two": {"provenance": "ASSUMED"},
    }

    monkeypatch.setattr("wha.api.client.get_client", lambda *a, **k: client)
    monkeypatch.setattr("wha.ui.components.api.get_client", lambda *a, **k: client)
    return client
