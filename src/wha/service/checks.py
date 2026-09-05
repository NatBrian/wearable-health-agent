"""Facts the diagnostics report, established in exactly one place.

`wha doctor` and `wha doctor --live` each used to establish these for themselves, and
drifted: one read the schema version from the database while the other printed a hardcoded
"v1", and one asked whether a dataset directory had anything in it while the other asked
only whether the directory existed. Because `wha data fetch stanford` creates an empty
directory, the second question always answered yes, and the command that ends with
"PRODUCTION READY" told the operator they had benchmark data they did not have.

A diagnostic that reports something it has not checked is worse than one that reports
nothing, so every claim in this module is answerable from what it actually inspects.
"""

import sqlite3
from pathlib import Path


def read_schema_version(conn: sqlite3.Connection) -> str:
    """The migration version recorded in the database, or 'unknown' if absent."""
    try:
        row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    except sqlite3.Error:
        return "unknown"
    if row is None:
        return "unknown"
    return str(row[0])


def dataset_present(data_dir: Path, name: str) -> bool:
    """Whether a benchmark cohort is actually usable.

    An empty directory is not a dataset. `wha data fetch <name>` creates the directory and
    nothing else, so existence alone is never evidence that the data arrived.
    """
    target = data_dir / name
    return target.is_dir() and any(target.iterdir())
