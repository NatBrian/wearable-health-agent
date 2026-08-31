"""Database access, transaction handling, schema management, and timestamp conversions."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from wha.db.audit_chain import append_audit, verify_chain
from wha.db.connection import connect
from wha.db.iso import from_iso, to_iso
from wha.db.migrations import DB_VERSION, apply_schema

_active_transactions: set[int] = set()


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
    "append_audit",
    "apply_schema",
    "connect",
    "from_iso",
    "to_iso",
    "transaction",
    "verify_chain",
]
