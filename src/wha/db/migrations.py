"""Schema application and version verification."""

import sqlite3
from pathlib import Path

from wha.errors import ConfigError

DB_VERSION = 1


def apply_schema(conn: sqlite3.Connection) -> None:
    """Idempotently apply database schema and verify schema version."""
    schema_path = Path(__file__).parent / "schema.sql"
    sql_script = schema_path.read_text(encoding="utf-8")

    conn.executescript(sql_script)

    # Verify or initialize schema version
    cursor = conn.execute("SELECT version FROM schema_version LIMIT 1;")
    row = cursor.fetchone()
    if row is None:
        conn.execute("INSERT INTO schema_version (version) VALUES (?);", (DB_VERSION,))
        conn.commit()
    else:
        current_version = row["version"] if isinstance(row, sqlite3.Row) else row[0]
        if current_version != DB_VERSION:
            raise ConfigError(
                f"Database schema version mismatch: expected {DB_VERSION}, found {current_version}"
            )
