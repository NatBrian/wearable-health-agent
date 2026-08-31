# Component 17. CLI and runtime

**Phase:** A for the batch commands, C for `serve`. **Module:** `src/wha/cli.py`,
`src/wha/runtime/`. **Depends on:** 14 service layer.

The `wha` command is the only entry point. `cli.py` imports from `service/` and `config.py` and
**nothing else**, enforced by a lint rule.

---

## 1. Commands

```bash
uv run wha doctor                                  # check everything, print pass/fail per item
uv run wha ingest [--days N]                       # pull from the configured source
uv run wha nightly [--date D | --range A:B]        # deterministic batch
uv run wha episode step <id>                       # advance one episode by one step
uv run wha episode list                            # open episodes
uv run wha belief explain --episode <id|latest>    # marginals night by night
uv run wha demo run <scenario> [--dry-run] [--live]  # synthetic scenario end to end
uv run wha cohort replay --dataset D --participant P
uv run wha data fetch <stanford|pmdata|chronos|corpus>
uv run wha eval <suite>
uv run wha serve [--port 8501] [--no-scheduler]
```

Global options on every command: `--subject` defaulting to `WHA_SUBJECT` then `me`, `--db` for the
database path, `-v` for verbose, `--json` for machine-readable output.

**`wha demo run` forces `WHA_LLM_PROVIDER=cassette` unless `--live` is passed.** The demo is how a
human reviews this project, so it must be deterministic and must work with no network. `--live` runs
the same scenario against the configured provider and is the impressive version; it is never used in
an exit condition.

Typer for the parser. Every command returns a **meaningful exit code**: `0` success, `1` an expected
failure such as `SourceUnavailable`, `2` a usage error, `3` a configuration error. An unattended run
and a Task Scheduler entry both depend on this.

---

## 2. `wha doctor`

The first thing a person runs and the first thing to run after any change. Every check is
independent and a failure never stops the others.

```
database        ok      data/wha.sqlite, schema v1, 31 nights, 1 subject
knowledge       ok      causes.yaml 12 rows, probes.yaml 9 rows, red_flags.yaml 18 rules
bridge          warn    last successful ingest 41h ago (warn at 36h, refuse at 72h)
llm             ok      provider=cassette, 24 cassettes present
telegram        off     WHA_NOTIFY_CHANNEL=none
datasets        miss    stanford absent. run: uv run wha data fetch stanford
chronos         ok      amazon/chronos-bolt-small cached
baseline        info    subject 'me': 2 usable nights, rung COLD
```

**Never prints a secret**, only whether one is configured. Exit code `0` if nothing is `fail`, `1`
otherwise; `warn`, `off`, `miss` and `info` do not fail the command.

---

## 3. `wha nightly`

The deterministic batch, and the only thing that must run every day.

```
for each night in the requested range, oldest first:
    ingest if the source has newer data      (skipped with --no-ingest)
    compute features            component 03
    compute baseline            component 04
    detect                      component 05
    forecast                    component 06, advisory
    if flagged:
        red-flag intercept      component 11
        open or extend the episode
        run one agent step      component 09        (Phase B; a no-op in Phase A)
```

**Idempotent.** Running it twice for the same night produces identical rows. Running it for a range
that includes already-computed nights recomputes them, which is required because data arrives late.

**Refuses rather than guessing.** If the last successful ingest is older than
`INGEST_STALE_REFUSE_HOURS`, the night is marked not usable with a recorded reason. It does not
interpolate and it does not use the previous night's value.

Default range with no arguments: the last 7 nights, so a missed day self-heals without anyone
noticing.

---

## 4. The scheduler

`wha serve` starts a background `APScheduler` thread alongside Streamlit.

| Job | Interval | Does |
|---|---|---|
| `ingest` | 30 min | Pull, store, normalise. Writes a `system_status` heartbeat |
| `nightly` | daily at 09:00 local | The batch for last night |
| `episode_tick` | 15 min | Advance every open episode by one step. **This is what drives timeouts**, since LangGraph has none |
| `telegram_poll` | continuous | `getUpdates` long-poll in its own thread |

**`episode_tick` is load-bearing.** Answer and measurement timeouts, retrying a parked episode after
`LLMUnavailable`, and closing an episode that has run past `EPISODE_MAX_NIGHTS` all happen here.
Without it an episode waiting on a human waits forever.

Jobs are **serialised on a single lock**. Two overlapping `nightly` runs would race on the same rows.
`max_instances=1` and `coalesce=True` on every job.

A job that raises writes a `system_status` row and **never kills the thread**. A dead scheduler with
a live dashboard is the worst failure mode here, because the interface would look healthy while
nothing ran.

### Without leaving the dashboard open

Documented in the README, and `wha doctor` prints whether it is registered:

```powershell
schtasks /Create /SC DAILY /ST 09:00 /TN "WearableHealthAgent" ^
  /TR "cmd /c cd /d C:\...\agentic-wearable-early-warning && uv run wha nightly"
```

Notifications need `wha serve` running, because `telegram_poll` lives there. That trade is stated in
the README rather than hidden.

---

## 5. First run

No database, no subject, no data. This must work and produce something sensible.

```
wha doctor      creates the database, applies the schema, reports what is missing
wha ingest      creates subject 'me' from WHA_TIMEZONE on first successful fetch
wha nightly     one night, rung COLD, INSUFFICIENT_DATA, no episode
wha serve       Today shows "2 usable nights, learning your normal", nothing pending
```

**Nothing crashes on an empty database.** Every service function handles zero rows and returns an
empty view model rather than raising. This is the state a new user is in for their first two days,
so it is a first-class path, not an edge case.

---

## 6. Configuration

`config.py` loads `.env` once into a frozen `Settings` object. Secrets are `SecretStr` and
`Settings.__repr__` redacts them.

**Config is read at startup, not per call.** A changed `.env` needs a restart, which is stated in the
Settings page. The exception is the Settings page itself, which writes and reloads deliberately.

Missing required config raises `ConfigError` naming **the key, never the value**, and it happens at
startup rather than on first use.

---

## 7. Logging

`structlog`-style key-value to stderr, plus a rotating file under `data/logs/`.

Levels: `INFO` for what ran and what it decided, `DEBUG` for values, `WARNING` for a degraded
component, `ERROR` for a caught failure.

**Never log a secret. Never log raw health values above `DEBUG`. Never log message content from an
unauthorised Telegram sender**, only that one was dropped.

The application log is **not** the audit log. Audit rows go through `audit/`, are append-only and
hash-chained. Nothing writes to `audit_events` directly.

---

## 8. Edge cases

| Case | Behaviour |
|---|---|
| `wha nightly` twice concurrently | The second blocks on the scheduler lock, or exits `1` with "already running" if invoked by hand |
| Database locked by the dashboard | WAL plus `busy_timeout` handles it. Do not retry in a loop |
| Bridge unreachable during a scheduled run | `SourceUnavailable`, one status row, exit `1`. Task Scheduler records it, the next run recovers |
| Machine asleep at 09:00 | Task Scheduler runs it late. The batch is date-driven, not clock-driven, so this is fine |
| Range spanning a timezone change | Each night resolves its own window from the subject's zone |
| `serve` with the port taken | Exit `2` with the port named |
| Scheduler job raises | Status row, thread survives, next interval retries |
| Ctrl-C during a batch | Transaction rolls back. No partial night |

---

## 9. Tests

`tests/unit/cli/` and `tests/integration/`

| Test | Asserts |
|---|---|
| `test_doctor_on_empty_database` | Creates it, reports missing items, exits 0 |
| `test_doctor_never_prints_secrets` | With every secret configured, no value appears in the output |
| `test_nightly_is_idempotent` | Twice gives identical rows and no duplicates |
| `test_nightly_recomputes_late_data` | New samples for an old night change its row |
| `test_nightly_refuses_when_stale` | Beyond `INGEST_STALE_REFUSE_HOURS`, not usable, reason recorded, **no interpolation** |
| `test_nightly_default_range_is_seven_nights` | |
| `test_exit_codes` | 0, 1, 2, 3 on the four classes of outcome |
| `test_first_run_produces_insufficient_data` | Empty database to a rendered Today page without an exception |
| `test_empty_database_service_calls_do_not_raise` | Every `service/` function on zero rows |
| `test_scheduler_job_failure_does_not_kill_thread` | A raising job leaves the scheduler alive and writes a status row |
| `test_scheduler_jobs_do_not_overlap` | `max_instances=1` honoured under a slow job |
| `test_episode_tick_expires_timed_out_interaction` | Past `ANSWER_TIMEOUT_HOURS`, status becomes `TIMED_OUT` and the episode advances |
| `test_config_error_names_key_not_value` | |
| `test_cli_imports_only_service` | An import-graph assertion, so the boundary cannot rot |

---

## 10. Exit condition

```bash
uv run pytest tests/unit/cli tests/integration -q
uv run wha doctor
uv run wha demo run illness-onset
uv run wha nightly --range 2026-08-03:2026-09-01
```

All four succeed on a fresh database, and running the last one twice changes nothing.
