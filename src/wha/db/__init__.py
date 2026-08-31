"""Database access, transaction handling, schema management, and timestamp conversions."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from wha.db.connection import connect
from wha.db.migrations import DB_VERSION, apply_schema

_active_transactions: set[int] = set()


def to_iso(dt: datetime) -> str:
    """Convert timezone-aware datetime to ISO 8601 UTC string ending in 'Z'.

    Raises ValueError if a naive datetime is passed.
    """
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError(f"Naive datetime not allowed in storage: {dt!r}")
    dt_utc = dt.astimezone(UTC)
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def from_iso(s: str) -> datetime:
    """Parse ISO 8601 string to timezone-aware UTC datetime."""
    clean_s = s.replace("Z", "+00:00")
    dt = datetime.fromisoformat(clean_s)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Context manager for database transactions.

    Commits on clean exit, rolls back on any exception.
    Raises RuntimeError on attempted nested transactions.
    """
    conn_id = id(conn)
    if conn_id in _active_transactions:
        raise RuntimeError("Nested transactions not supported")

    _active_transactions.add(conn_id)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _active_transactions.discard(conn_id)


__all__ = [
    "DB_VERSION",
    "apply_schema",
    "connect",
    "from_iso",
    "to_iso",
    "transaction",
]
