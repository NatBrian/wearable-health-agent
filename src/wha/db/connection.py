"""Database connection handling with required pragmas."""

import sqlite3
from pathlib import Path

from wha.config import get_db_path


def connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Open the SQLite database with the pragmas this project needs.

    WAL because the scheduler thread writes while the UI thread reads.
    foreign_keys because the schema declares them and SQLite ignores them by default.
    """
    if db_path is None:
        target_path = get_db_path()
    else:
        target_path = Path(db_path) if isinstance(db_path, str) else db_path

    # Only create parent dirs if target is a filesystem file (not :memory:)
    is_memory = str(target_path) == ":memory:"
    if not is_memory:
        target_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(target_path), timeout=5.0)
    conn.row_factory = sqlite3.Row

    # Execute required pragmas
    if not is_memory:
        conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA synchronous=NORMAL;")

    return conn
