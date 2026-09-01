"""Tests for documentation integrity and CLI command validity in README."""

import re
from pathlib import Path

from typer.testing import CliRunner

from wha.cli import app

runner = CliRunner()


def test_readme_quickstart_commands_exist() -> None:
    """Every 'wha <cmd>' command mentioned in README quickstart or usage is a valid registered CLI command."""
    readme_path = Path("README.md")
    assert readme_path.exists(), "README.md must exist"

    content = readme_path.read_text(encoding="utf-8")

    # Extract commands matching `wha <subcommand>` or `uv run wha <subcommand>` inside backticks / code blocks
    pattern = re.compile(r"`(?:uv run )?wha\s+([a-z0-9_\-]+)", re.IGNORECASE)

    # Valid base commands in Typer app
    # Collect registered command and subgroup names
    registered_commands = set(app.registered_commands)
    # Collect sub-typers
    registered_groups = {g.name for g in app.registered_groups if g.name}

    for match in pattern.finditer(content):
        primary = match.group(1).lower()
        # Ensure the primary command is either a top-level command or a group
        valid_cmd_or_group = (
            primary in [c.name for c in registered_commands if c.name]
            or primary in registered_groups
        )
        assert valid_cmd_or_group, (
            f"Command '{primary}' in README.md is not a registered CLI command."
        )


def test_readme_has_no_em_dashes() -> None:
    """README contains no em-dashes, conforming to repository stylistic rules."""
    readme_path = Path("README.md")
    content = readme_path.read_text(encoding="utf-8")
    assert "\u2014" not in content, "README.md contains an em-dash (\u2014)"
