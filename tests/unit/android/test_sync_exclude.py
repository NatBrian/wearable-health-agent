"""Nothing private may travel to the shared build machine.

The exclude list is the only thing standing between the owner's health record and a
machine other people use. A test, because a list nobody checks drifts.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXCLUDE = ROOT / "android" / "sync-exclude.txt"

# Every one of these is either a secret, personal health data, or a large artefact the
# remote has no use for. Add to this set when a new private path appears in the repo.
MUST_EXCLUDE = {
    ".env",
    ".env.*",
    "data/wha.sqlite",
    "data/corpus",
    "data/demo_film.sqlite",
    "data/demo_film_live.sqlite",
    "data/demo-snapshots",
    "data/datasets",
    "data/cohort",
    "docs/demo/wha-demo.mp4",
    ".git",
    ".venv",
    "android/app/build",
    "android/.gradle",
}


def _lines() -> set[str]:
    return {
        line.strip()
        for line in EXCLUDE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


def test_exclude_list_names_every_private_path() -> None:
    missing = MUST_EXCLUDE - _lines()
    assert not missing, f"android/sync-exclude.txt does not exclude: {sorted(missing)}"


def test_exclude_list_covers_every_gitignored_data_pattern() -> None:
    """If .gitignore keeps it out of git, the sync must keep it off the remote."""
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    data_patterns = {
        line.strip()
        for line in ignore
        if line.strip().startswith("data/") and not line.strip().startswith("!")
    }
    exclude = EXCLUDE.read_text(encoding="utf-8")
    uncovered = [p for p in data_patterns if p.rstrip("/").split("/")[0] not in exclude]
    assert not uncovered, f"gitignored data patterns the sync does not exclude: {uncovered}"
