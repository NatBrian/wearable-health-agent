"""Schema application and version verification."""

import sqlite3
from pathlib import Path

from wha.errors import ConfigError

DB_VERSION = 9

# Columns added after version 1. CREATE TABLE IF NOT EXISTS does not alter a table that
# already exists, so a database created before a column was introduced would silently
# lack it and fail at the first write. Each entry is applied only when absent.
_ADDED_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("beliefs", "state_logprob_json", "TEXT"),
    # v4. Which window the night's reading came from, "sleep" or "clock".
    ("nightly_features", "rhr_window_source", "TEXT"),
    # v5. The most recent night the agent has actually reasoned over, so an episode that
    # decided to observe can be re-entered when a further night arrives.
    ("episodes", "last_evidence_night", "TEXT"),
    # v6. Whether a question was pushed at a person who was not asking, or asked inside a
    # conversation they were already having. Only the first kind spends the weekly budget.
    ("interactions", "initiation", "TEXT"),
    # v6. Which discriminator conversation a turn belongs to.
    ("conversation_turns", "presentation", "TEXT"),
    # v9. The investigation this one continues, and how many days separated them.
    # A recurrence inside the episode-separation window is the same illness, and an
    # episode that starts from scratch asks as though it had never met the person.
    ("episodes", "preceded_by_episode_id", "TEXT"),
    ("episodes", "days_since_previous", "INTEGER"),
)


# Tables whose shape changed after they were first created. CREATE TABLE IF NOT EXISTS
# leaves an existing table alone, so a database carrying an earlier shape keeps it and
# fails at the first write with a confusing "no such column".
_RESHAPED_TABLES: tuple[tuple[str, frozenset[str]], ...] = (
    (
        "oxygen_saturation_samples",
        frozenset({"subject_id", "ts_utc", "percentage", "origin"}),
    ),
)


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, decl: str) -> bool:
    """Add a column if the table lacks it. Returns True when something changed."""
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table});").fetchall()}
    if not existing or column in existing:
        return False
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl};")
    return True


def _ensure_table_shape(conn: sqlite3.Connection, table: str, expected: frozenset[str]) -> bool:
    """Recreate a table whose columns no longer match the schema, if it holds no rows.

    Dropping is only ever done on an empty table. A mismatched table with data in it is
    reported rather than destroyed, because silently discarding a person's readings to
    resolve a schema disagreement is never the right trade.
    """
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table});").fetchall()}
    if not existing or existing == expected:
        return False

    row_count = conn.execute(f"SELECT COUNT(*) FROM {table};").fetchone()[0]
    if row_count:
        raise ConfigError(
            f"Table '{table}' has columns {sorted(existing)} where {sorted(expected)} is "
            f"expected, and holds {row_count} rows. Refusing to drop data. Export the "
            "table, remove it, and re-open the database."
        )

    conn.execute(f"DROP TABLE {table};")
    return True


def apply_schema(conn: sqlite3.Connection) -> None:
    """Idempotently apply database schema, migrate older databases, and verify version."""
    schema_path = Path(__file__).parent / "schema.sql"
    sql_script = schema_path.read_text(encoding="utf-8")

    conn.executescript(sql_script)

    # Drop any table left in an earlier shape, then re-run the script so it is recreated
    # from the current definition.
    if any(_ensure_table_shape(conn, table, cols) for table, cols in _RESHAPED_TABLES):
        conn.executescript(sql_script)

    for table, column, decl in _ADDED_COLUMNS:
        _ensure_column(conn, table, column, decl)
    conn.commit()

    # Verify or initialize schema version
    cursor = conn.execute("SELECT version FROM schema_version LIMIT 1;")
    row = cursor.fetchone()
    if row is None:
        conn.execute("INSERT INTO schema_version (version) VALUES (?);", (DB_VERSION,))
        conn.commit()
        return

    current_version = row["version"] if isinstance(row, sqlite3.Row) else row[0]
    if current_version == DB_VERSION:
        return
    if current_version > DB_VERSION:
        raise ConfigError(
            f"Database schema version {current_version} is newer than this build "
            f"expects ({DB_VERSION}). Upgrade the application rather than the database."
        )

    # Older database: the additive migrations above have already run, so record the
    # new version rather than refusing to open a database we just brought up to date.
    conn.execute("UPDATE schema_version SET version = ?;", (DB_VERSION,))
    conn.commit()
