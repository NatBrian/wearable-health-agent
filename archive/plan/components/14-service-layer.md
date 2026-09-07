# Component 14. Service layer

**Phase:** B, alongside the agent. **Module:** `src/wha/service/`.
**Depends on:** everything below it.

The only place business logic lives, and the boundary that makes the frontend decision reversible.

---

## 1. The contract

Every function signature is fixed in `docs/CONTRACTS.md` section 7. This document says how they
behave, not what they are called.

**Rules, enforced by a lint rule rather than by intention:**

- `ui/` may import **only** `service/` and `models.py`.
- `cli.py` may import **only** `service/` and `config.py`.
- No `sqlite3` import outside `db/`.
- No page or command constructs a query, calls `detect/`, `belief/`, `policy/` or `agent/`, or
  touches the filesystem.

If a page needs a computation, it belongs here. That is what makes a later FastAPI wrapper a wrapper
rather than a rewrite.

---

## 2. Behaviour every function shares

**Never raises to a page.** A page must be able to render whatever comes back. Failures become a
field on the view model:

```python
class ComponentStatus(BaseModel):
    ok: bool
    detail: str
    severity: Literal["ok", "warn", "error"]
```

The exceptions are programmer errors, an unknown `episode_id` or a malformed argument, which raise
because a page should never produce one.

**Every function handles an empty database.** Zero subjects, zero nights, zero episodes. This is the
state a new user is in for their first two days, so it is a first-class path and every function has
a test for it.

**Read-only by default.** Only `submit_answer`, `submit_measurement_done`, `submit_human_decision`,
`update_settings` and `delete_all_subject_data` write, and each is idempotent on repeat.

**Never returns a domain internal.** No `sqlite3.Row`, no raw dict, no `BeliefState` where a
`NightRow` was asked for. The view models exist so the interface cannot accidentally couple to
storage.

---

## 3. Status

```python
def get_system_status(subject_id: str) -> SystemStatus
```

Assembles six `ComponentStatus` rows: database, bridge, scheduler, llm, telegram, datasets. Plus
`last_ingest_utc`, `last_nightly_utc`, `usable_nights`, `rung`, `errors_24h`, and
`quiet_nights_streak`.

**Cheap enough to poll every ten seconds**, because the status strip does. Reads `system_status` and
aggregates; it does not run a health check. The `test_*_connection` functions do that and are
button-driven.

`quiet_nights_streak` exists so the "nothing pending" state reads as reassuring rather than empty.
Consecutive nights since the last flagged one.

Severity: `bridge` is `warn` beyond `INGEST_STALE_WARN_HOURS` and `error` beyond
`INGEST_STALE_REFUSE_HOURS`. `llm` is `ok` when the provider is `cassette`, since that is a valid
configuration and not a degraded one.

---

## 4. Connection checks

```python
def test_bridge_connection() -> ConnectionCheck
def test_llm_connection() -> ConnectionCheck
def test_telegram_connection() -> ConnectionCheck
```

Actually attempt the connection, with a short timeout. Button-driven, never polled.

**Never return a secret in `detail`**, and never echo one back. On failure the detail names what
failed and where, not what was sent.

---

## 5. Episodes

```python
def get_pending_interaction(subject_id: str) -> PendingInteraction | None
```

The single most-called function. Returns at most one thing, because at most one
`AWAITING_USER` interaction exists per subject by construction. Order of precedence if several
states somehow coexist: review, then measurement, then question.

```python
def submit_answer(interaction_id: str, answer: Answer) -> None
```

**Idempotent, and the same code path as the Telegram callback.** First writer wins; a second submit
on an `ANSWERED` row is a no-op, not an error. That is what makes answering in either place safe.

Writes the answer, then **advances the episode by one step synchronously**, so the page can re-render
with the result rather than waiting for the next scheduler tick.

```python
def get_episode(episode_id: str) -> EpisodeDetail
```

Assembles the outcome, the stages, the belief history, the interactions with their `evsi` and
rejected alternatives, the measurements, the citations and the stripped claims. One call, because the
episode panel should not make eight.

Stages are derived from `audit_events` for that episode, in canonical order, with `SKIPPED` inferred
from absence plus the reason recorded when the skip happened. **Skipped stages must be present in the
returned list**, not omitted, since the interface exists to show them.

```python
def ask_about_episode(episode_id: str, question: str) -> GroundedAnswer
```

**Bounded.** It may retrieve only from that episode's own stored evidence and citations. No tool
access, no corpus-wide search, no state change. An answer that cannot be grounded returns
`refused=True` with a reason rather than a guess.

---

## 6. Nights

```python
def list_nights(subject_id: str, start: date, end: date) -> list[NightRow]
```

One row per **calendar** night in the range, including nights with no data, so the chart can draw a
gap. A missing night is a row with `rhr_bpm=None` and `usable=False`, **not an absent row**.

`band_lo` and `band_hi` are `centre ± scale`, or `None` when there is no baseline. The band visibly
narrows as the baseline matures, which is the ladder made visible.

---

## 7. Audit

```python
def query_audit(f: AuditFilter, limit: int, offset: int) -> list[AuditEventView]
def verify_hash_chain(subject_id: str) -> tuple[bool, str | None]
def export_audit(f: AuditFilter, path: Path) -> Path
```

`AuditEventView.hash_ok` is per row, so a tampered row is visible in the table and not only in the
summary. Verification walks the chain and returns the **first** bad `event_id`.

Export writes CSV and JSON. **Secrets are already absent from the table**, so export needs no
redaction pass, and that is a property worth asserting in a test rather than assuming.

---

## 8. Settings

```python
def get_settings() -> Settings                       # NO secret fields at all
def update_settings(patch: SettingsPatch) -> Settings
def delete_all_subject_data(subject_id: str) -> None
```

`Settings` carries no secrets. `SettingsPatch` uses `SecretStr` and is write-only. A saved secret is
never read back, so the field renders empty after saving, and that is correct rather than a bug.

**A policy change is logged as an audit event**, because changing a threshold changes behaviour.

`delete_all_subject_data` deletes every row for that subject across every table, inside one
transaction, and writes a final audit row recording the deletion before the audit rows for that
subject are removed. It is behind a typed confirmation in the interface. **It is not reversible and
the interface says so.**

---

## 9. Edge cases

| Case | Behaviour |
|---|---|
| Empty database | Every function returns an empty view model. **Nothing raises** |
| Unknown `episode_id` | Raises. A page should never produce one |
| `submit_answer` twice | Second is a no-op |
| Answer submitted for a closed episode | No-op, logged. Not an error to the user |
| Two subjects, none selected | Defaults to `WHA_SUBJECT`, then `me`, then the first alphabetically |
| Range spanning nights with no data | Rows present with `None` values. **Never omitted** |
| Hash chain broken | `verify_hash_chain` returns the first bad id; other functions still work |
| Evaluation result missing | `get_evaluation_results` returns an empty result with a caveat naming the command |
| `delete_all_subject_data` on the last subject | Allowed. The database returns to the first-run state |

---

## 10. Tests

`tests/unit/service/`

| Test | Asserts |
|---|---|
| `test_every_function_handles_empty_database` | Parametrised over all of them. **The single most valuable test here** |
| `test_no_function_raises_on_degraded_component` | Bridge down, LLM down, Telegram unconfigured |
| `test_status_is_cheap` | No health check performed; only reads |
| `test_connection_checks_never_return_secrets` | With every secret configured |
| `test_pending_interaction_returns_at_most_one` | |
| `test_submit_answer_is_idempotent` | |
| `test_submit_answer_same_path_as_telegram` | Both routes converge on one function |
| `test_answer_on_closed_episode_is_noop` | |
| `test_list_nights_includes_empty_nights` | A 30-day range with 12 nights of data returns 30 rows |
| `test_band_is_none_without_baseline` | |
| `test_episode_detail_includes_skipped_stages` | Present with reasons, not omitted |
| `test_episode_detail_includes_rejected_probes` | With scores |
| `test_ask_about_episode_cannot_reach_corpus` | Only that episode's citations |
| `test_ask_about_episode_refuses_ungrounded` | `refused=True`, not a guess |
| `test_ask_about_episode_changes_no_state` | Row counts identical before and after |
| `test_audit_export_contains_no_secrets` | |
| `test_settings_never_returns_secrets` | `Settings` has no such field |
| `test_policy_change_writes_audit_event` | |
| `test_delete_all_removes_every_table` | And leaves the database usable |
| `test_ui_imports_only_service` | Import-graph assertion |
| `test_no_sqlite_outside_db` | Import-graph assertion |

The last two are what keep the boundary from rotting, and they are cheap.

---

## 11. Exit condition

```bash
uv run pytest tests/unit/service -q
```

Green, with `test_every_function_handles_empty_database` and both import-graph assertions passing.
