"""Tests for documentation integrity and CLI command validity in README."""

import re
import subprocess
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


def test_no_prose_this_project_maintains_has_an_em_dash() -> None:
    """The rule was enforced on README.md alone, so everything else drifted.

    On 7 September 2026 a sweep found 42 em-dashes across five documents that nobody had
    ever checked. The style rule in AGENTS.md applies to all prose in this repository, and
    a rule that lives only in a document is a rule that holds until the next person writes
    a heading.

    archive/ is excluded on purpose: it is a record of finished work and is not rewritten.

    IT ASKS GIT which files exist rather than walking the directory. The first version
    walked the tree and skipped a hand written list of directory names, so it failed once
    on a package README inside a directory the list did not name, and passed on the next
    run. A test that depends on what happens to be lying around the working directory is
    not testing this repository, and one that passes on a retry is worse than none,
    because it teaches you to retry.
    """
    root = Path(__file__).resolve().parents[2]
    listing = subprocess.run(
        ["git", "ls-files", "-z", "*.md"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    checked = [
        root / name for name in listing.split("\0") if name and not name.startswith("archive/")
    ]
    assert checked, "git listed no markdown, which means this is not asking git properly"

    dash = chr(0x2014)
    offenders = [
        f"{p.relative_to(root).as_posix()}:{n}"
        for p in checked
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
        if dash in line
    ]
    joined = ("\n  ").join(offenders)
    assert not offenders, f"em-dash ({dash}) in prose this project maintains:\n  {joined}"
