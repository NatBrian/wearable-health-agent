# Component 02. Storage

**Phase:** A. **Module:** `src/wha/db/`. **Depends on:** nothing.
**Everything else depends on this**, so it lands first.

`src/wha/db/` is the **only** module in the project that imports `sqlite3`.

---

## 1. Responsibilities

1. Create the schema idempotently at startup.
2. Hand out connections with the right pragmas.
3. Provide a transaction helper that actually rolls back.
4. Write and verify the audit hash chain.
5. Nothing else. No queries about domain objects live here; those live in `service/` and in the
   module that owns the table.

---

## 2. Files

```
src/wha/db/
  __init__.py       exports: connect, transaction, apply_schema, DB_VERSION
  schema.sql        the full DDL from docs/CONTRACTS.md section 5, verbatim
  connection.py     connect(), pragmas, path resolution
  migrations.py     apply_schema(), version tracking
  audit_chain.py    append_audit(), verify_chain()
```

---

## 3. Connections

```python
def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Open the database with the pragmas this project needs.

    WAL because the scheduler thread writes while the UI thread reads.
    foreign_keys because the schema declares them and SQLite ignores them by default.
    """
```

Pragmas, all of them required:

| Pragma | Value | Why |
|---|---|---|
| `journal_mode` | `WAL` | The scheduler writes while Streamlit reads. Without this they block each other |
| `foreign_keys` | `ON` | **SQLite ignores foreign keys unless you turn them on.** The schema declares them and they would silently do nothing |
| `busy_timeout` | `5000` | Two threads, one file. Without it a concurrent write raises immediately |
| `synchronous` | `NORMAL` | Safe under WAL, and much faster than `FULL` for a local file |

`row_factory` is `sqlite3.Row` so rows are addressable by name. Never index a row by position.

The path comes from `settings.db_path`, and its parent directory is created with
`mkdir(parents=True, exist_ok=True)` before opening.

**Connections are per-thread.** Never share one across threads. The scheduler thread and the UI
thread each open their own.

---

## 4. Transactions

```python
@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Commit on success, roll back on any exception, always."""
```

Every multi-statement write goes through this. The specific failure it prevents is in the contract:
a bridge fetch that times out mid-way must leave **no partial night** behind, not a half-written one.

Nested use is not supported and must raise, rather than silently producing a savepoint nobody
reasoned about.

---

## 5. Schema application

`schema.sql` is the DDL from `docs/CONTRACTS.md` section 5, **copied verbatim**. If the two ever
differ, the contract is right and that is a blocker.

```python
def apply_schema(conn: sqlite3.Connection) -> None:
    """Idempotent. Safe to call on every startup."""
```

Every statement uses `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`. A
`schema_version` table holds a single integer row. `DB_VERSION` is a module constant.

**Migrations.** For this build there are none: the schema is created once and the contract forbids
changing it. If a future version needs one, `migrations.py` holds numbered functions applied in
order inside a transaction, and the version row is bumped in the same transaction. Do not build
migration machinery speculatively; a single `apply_schema` is the whole requirement today.

---

## 6. The audit hash chain

```python
def append_audit(conn, event: AuditEvent) -> str:
    """Append one row, chained to the previous. Returns the new hash."""

def verify_chain(conn, subject_id: str) -> tuple[bool, str | None]:
    """Walk the chain. Returns (ok, first_bad_event_id)."""
```

The rule, exactly:

```
hash = sha256( prev_hash + canonical_json(row_without_hash_fields) ).hexdigest()
```

`canonical_json` is `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.
**Key order and whitespace must be deterministic**, or a chain written on one run will fail
verification on the next for no reason.

The first row of a subject's chain has `prev_hash = None` and hashes against the empty string.

`audit_events` is **append-only**. There is no update path and no delete path. If a task seems to
need one, that is a blocker.

`append_audit` and the write it describes go in **the same transaction**, otherwise a crash between
them produces an action with no audit row, which is the one thing the log exists to prevent.

---

## 7. Timestamps and dates

Stored as ISO 8601 strings, because SQLite has no date type and integers lose readability when a
human inspects the file.

| Kind | Format | Column suffix |
|---|---|---|
| Instant | `2026-09-01T22:14:07Z`, always UTC, always `Z` | `_utc` |
| Local date | `2026-09-01` | `night_date`, `opened_on`, `week_start` |

Two helpers in `db/__init__.py`, and **nothing else formats a timestamp**:

```python
def to_iso(dt: datetime) -> str: ...     # asserts tzinfo is UTC, raises if naive
def from_iso(s: str) -> datetime: ...    # always returns tz-aware UTC
```

A naive datetime reaching storage is a bug. `to_iso` raises rather than guessing.

---

## 8. Edge cases

| Case | Behaviour |
|---|---|
| Database file does not exist | Create parent directory, create file, apply schema. Not an error |
| Database exists at an older `DB_VERSION` | Raise `ConfigError` naming both versions. Do not auto-migrate silently |
| Two threads write at once | `busy_timeout` handles it. If it still raises, let it propagate; do not retry in a loop |
| Insert of an existing primary key | `INSERT OR REPLACE` for derived tables (`nightly_features`, `baselines`, `detections`) because the batch is idempotent. **Plain `INSERT` for append-only tables** (`audit_events`, `beliefs`, `raw_payloads`), where a duplicate is a real bug |
| `raw_payloads` duplicate sha256 | `INSERT OR IGNORE`. The same payload fetched twice is not an error and must not create a second row |
| Disk full | Let it propagate. Do not catch |

---

## 9. Tests

`tests/unit/db/`

| Test | Asserts |
|---|---|
| `test_apply_schema_is_idempotent` | Calling it three times leaves one set of tables and does not raise |
| `test_foreign_keys_are_enforced` | Inserting a row referencing a missing subject raises `IntegrityError`. **This fails if the pragma is missing, which is the point** |
| `test_transaction_rolls_back_on_error` | An exception mid-transaction leaves zero rows written |
| `test_transaction_commits_on_success` | Rows are visible from a second connection afterwards |
| `test_hash_chain_verifies_clean` | Ten appended events verify as ok |
| `test_hash_chain_detects_tamper` | Mutating one row's `output_json` makes `verify_chain` return that row's id |
| `test_hash_chain_is_stable_across_runs` | The same events appended twice in two processes produce the same hashes |
| `test_first_row_has_null_prev_hash` | And still verifies |
| `test_to_iso_rejects_naive_datetime` | Raises rather than assuming UTC |
| `test_from_iso_returns_aware_utc` | Round-trips exactly |
| `test_raw_payload_duplicate_is_ignored` | Same sha256 twice leaves one row, no exception |
| `test_derived_tables_are_upsert` | Re-running the batch for one night replaces rather than duplicating |

---

## 10. Exit condition

```bash
uv run pytest tests/unit/db -q
```

Green, and `uv run ruff check src/wha/db` clean.
