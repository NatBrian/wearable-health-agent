"""Unit tests for the UI application shell, subject selector, and status strip fragment."""

import ast
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from wha.models import BaselineRung, ComponentStatus, Subject, SystemStatus
from wha.ui.components.status_strip import render_status_strip
from wha.ui.components.subject_selector import render_subject_selector


def test_subject_selector_hidden_when_single() -> None:
    """Subject selector is hidden (no selectbox rendered) when only one subject exists."""
    single_subject = [
        Subject(
            subject_id="sub_single",
            label="Single Subject",
            source_kind="synthetic",
            timezone="Asia/Singapore",
            usable_nights=10,
            rung=BaselineRung.SHRINKING,
        )
    ]

    with (
        patch("wha.ui.components.subject_selector.list_subjects", return_value=single_subject),
        patch("streamlit.sidebar.selectbox") as mock_selectbox,
    ):
        chosen = render_subject_selector()
        assert chosen == "sub_single"
        mock_selectbox.assert_not_called()


def test_today_status_strip_degraded() -> None:
    """Stale ingest creates degraded error status naming the staleness duration."""
    stale_dt = datetime.now(UTC) - timedelta(hours=80)
    degraded_status = SystemStatus(
        components=[
            ComponentStatus(
                component="bridge",
                ok=False,
                detail="Ingest stale (80h > 72h refuse limit)",
                checked_at_utc=datetime.now(UTC),
                severity="error",
            )
        ],
        last_ingest_utc=stale_dt,
        last_nightly_utc=None,
        usable_nights=5,
        rung=BaselineRung.PRIOR_DOMINATED,
        errors_24h=1,
        quiet_nights_streak=0,
    )

    func = getattr(render_status_strip, "__wrapped__", render_status_strip)
    with (
        patch("streamlit.error") as mock_error,
        patch("streamlit.columns", return_value=[MagicMock() for _ in range(6)]),
    ):
        func(subject_id="sub_test", status=degraded_status)
        assert mock_error.called
        # Check that error message mentions staleness
        error_msgs = [call[0][0] for call in mock_error.call_args_list]
        assert any("stale" in m.lower() or "80h" in m for m in error_msgs)


def test_status_strip_is_a_fragment() -> None:
    """Status strip is decorated with Streamlit fragment decorator."""
    # Check that render_status_strip has fragment attribute or wrapper from Streamlit
    assert hasattr(render_status_strip, "__wrapped__") or callable(render_status_strip)
    # Check ast of status_strip.py
    tree = ast.parse(Path("src/wha/ui/components/status_strip.py").read_text(encoding="utf-8"))
    decorators = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "render_status_strip":
            for dec in node.decorator_list:
                if (
                    isinstance(dec, ast.Call)
                    and getattr(dec.func, "attr", None) == "fragment"
                    or getattr(dec, "attr", None) == "fragment"
                ):
                    decorators.append("fragment")
    assert "fragment" in decorators


def test_ui_imports_only_service() -> None:
    """UI modules must import only from wha.service, wha.config, wha.models, or wha.ui."""
    ui_dir = Path("src/wha/ui")
    forbidden_prefixes = (
        "wha.db",
        "wha.detect",
        "wha.belief",
        "wha.policy",
        "wha.agent",
        "wha.ingest",
        "wha.retrieve",
        "wha.safety",
        "wha.eval",
    )

    for py_file in ui_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_prefixes:
                        assert not alias.name.startswith(forbidden), (
                            f"{py_file} directly imports {alias.name}, violating boundary rule."
                        )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for forbidden in forbidden_prefixes:
                    assert not module.startswith(forbidden), (
                        f"{py_file} directly imports from {module}, violating boundary rule."
                    )
