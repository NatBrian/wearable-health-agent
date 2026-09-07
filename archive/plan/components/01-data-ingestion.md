# Component 01. Data ingestion

**Phase:** A. **Module:** `src/wha/ingest/`. **Depends on:** 02 storage.

Three sources, one normalised shape, so **nothing downstream ever branches on where data came
from**. That property is what makes the demo real (D-115) and the cohort evaluation possible.

---

## 1. The protocol

```python
class DataSource(Protocol):
    source_kind: Literal["live", "synthetic", "cohort"]
    def fetch(self, subject_id: str, days: int) -> RawPayload: ...
```

```
src/wha/ingest/
  __init__.py       get_source(kind) factory
  base.py           DataSource protocol, RawPayload, normalise()
  live_bridge.py    HTTP to the Health Connect Webhook app
  synthetic.py      scenario generator
  cohort.py         Stanford and PMData replay
  store.py          store_raw(), normalise_and_store()
```

---

## 2. The normalised payload

**Authoritative reference:** `tools/make_synthetic.py`, which documents the real device schema
observed on 2026-08-31 from app v1.9.17. Read it before writing the parser. Do not invent field
names.

```json
{
  "app_version": "1.9.17",
  "timestamp": "2026-08-31T08:57:07Z",
  "steps": [
    {"count": 2594, "start_time": "2026-08-29T16:00:00Z", "end_time": "2026-08-30T16:00:00Z"}
  ],
  "heart_rate": [
    {"time": "2026-08-30T16:33:00Z", "avg": 90, "min": 90, "max": 90,
     "metadata": {"data_origin": "com.sec.android.app.shealth"}}
  ],
  "sleep": [],
  "exercise": []
}
```

Facts about the real payload that the parser must handle and must not "fix":

- **Steps are daily buckets**, aligned to local midnight. On UTC+8 they run 16:00Z to 16:00Z. There
  is no per-minute step data and there never will be. This is why the detector uses the nocturnal
  window rather than the published activity-masking method.
- **Heart rate arrives in 1-minute buckets** with `avg`, `min` and `max`. Only `avg` is used for
  `rhr_bpm`.
- **The live payload repeats the `app_version` key twice.** JSON parsers keep the last one. Do not
  treat a duplicate key as corruption.
- **`sleep` and `exercise` may be absent or empty**, indefinitely. Code must not assume they arrive.
  Missing is normal, not an error.

---

## 3. Ingestion flow

```
fetch()  ->  RawPayload
             |
        store_raw()          verbatim, with sha256. INSERT OR IGNORE on duplicate
             |
        normalise()          -> typed rows
             |
        upsert into heart_rate_samples, step_buckets, sleep_stages, exercise_sessions
```

**Raw is stored before normalisation, always.** If the parser has a bug, the original bytes are
still there and the night can be recomputed. This has already saved projects and costs one table.

`normalise()` is a **pure function** from payload dict to typed rows. No IO, no database. That makes
it directly testable against a fixture file, which is where most of the parser tests live.

Normalisation rules:

- Timestamps parsed to tz-aware UTC. A timestamp without a zone is a parse error, not a guess.
- Heart-rate samples outside `[HR_PLAUSIBLE_MIN_BPM, HR_PLAUSIBLE_MAX_BPM]` are **kept in
  `heart_rate_samples`** and dropped later, in component 03, where the count is recorded. Storage is
  faithful; filtering is a feature-layer decision.
- Duplicate `(subject_id, ts_utc)` is `INSERT OR REPLACE`. Sync windows overlap by design.
- Sleep stage strings map through a fixed dict to `{AWAKE, LIGHT, DEEP, REM}`. An unrecognised stage
  is stored verbatim and logged once, never dropped.

---

## 4. `LiveBridge`

```python
class LiveBridge:
    source_kind = "live"
    def fetch(self, subject_id: str, days: int) -> RawPayload: ...
```

- `GET http://{host}:{port}/?days={days}`, `Authorization: Bearer {token}`, timeout 30 s.
- Fallback path order, matching `tools/probe_healthconnect.py`: `/?days=N`, then `/`, then `/latest`.
- Any non-200, timeout or connection error raises `SourceUnavailable` with host, port and status,
  **never the token**.
- The response is untrusted input. Schema-validate on read. A malformed body is
  `SourceUnavailable`, not a crash.

> **The bridge has no authentication of its own and serves health data over the local network.**
> This is a real limitation, stated rather than glossed. Run it only on a trusted network. Treat the
> response as untrusted regardless.

**Known behaviour:** the bridge returns HTTP 500 on unrecognised data types. Keep the requested type
set narrow. Do not add types speculatively.

---

## 5. `Synthetic`

Promoted from a tool to core infrastructure. Generates payloads in **exactly** the shape above, so
code written against it works unchanged against the phone.

```python
class Synthetic:
    source_kind = "synthetic"
    def __init__(self, scenario: Scenario, seed: int): ...
```

A `Scenario` is a fixture in `tests/fixtures/scenarios/*.json`:

```json
{
  "name": "illness-onset",
  "days": 30,
  "base_bpm": 58.0,
  "seed": 11,
  "injections": [
    {"kind": "illness",  "start_day": 26, "amplitude_bpm": 4.5, "profile": "infection"},
    {"kind": "exercise", "day": 22, "end_offset_h": 1.5},
    {"kind": "alcohol",  "day": 18, "amplitude_bpm": 2.6},
    {"kind": "nonwear",  "day": 24, "minutes": 300}
  ],
  "expect": {"disposition": "LIKELY_ILLNESS", "asks_at_least": 1, "escalates": false}
}
```

Generation rules:

- A plain circadian shape, lowest around 04:00, plus Gaussian noise.
- Injections **add** to the baseline shape, using the same effect sizes and temporal profiles as
  `data/knowledge/causes.yaml`, so the generator and the belief model agree about physics.
- `nonwear` removes samples rather than zeroing them, because a gap and a zero are different things.
- **Deterministic given the seed.** Two runs produce byte-identical payloads. This is asserted.

> **No performance claim ever rests on synthetic data.** It exists for development, regression and
> demonstration. Recovering our own assumptions proves nothing, and the write-up says so.

---

## 6. `CohortReplay`

```python
class CohortReplay:
    source_kind = "cohort"
    def __init__(self, dataset: Literal["stanford", "pmdata"], participant: str): ...
```

Converts a cohort participant into the same normalised shape and writes to subject
`cohort-<participant>`.

**Stanford COVID-19-Wearables.** One unauthenticated download, 378 MB zipped, 3.64 GB extracted.
`hr.csv`, `steps.csv`, `sleep.csv` per participant.

> **The archive contains no labels.** COVID status and symptom-onset dates live in the paper's
> supplementary information, not the zip. A pipeline that assumes labels are in the download will
> silently evaluate against nothing. Labels live in `data/knowledge/cohort_labels.yaml`, authored
> separately, and their absence is a hard error, not a warning.

**PMData.** 1.4 GB, CC BY 4.0, 16 participants over 5 months. Used for the policy benchmark, where
`reporting.csv` (alcohol), `wellness.csv` (stress, sleep quality, fatigue) and `srpe.csv` (training
load) are the **oracle answers, revealed only when the agent asks**.

Both are converted to parquet on first load and cached. **Never re-parse a 3.6 GB CSV per run.**
Extract selectively and delete intermediates; there is about 33 GB of disk and no second drive.

Datasets are fetched by `uv run wha data fetch <name>`, which is idempotent, resumable, and verifies
a checksum. **Unit tests never require a dataset.** Tests that do are marked
`skipif(not dataset_present)` with the fetch command in the skip message.

---

## 7. Edge cases

| Case | Behaviour |
|---|---|
| Bridge unreachable | `SourceUnavailable`, one `system_status` row, batch skips this night. **Not a crash** |
| Empty payload, no records | Store raw, normalise to zero rows. The night becomes not usable. Not an error |
| Overlapping fetch windows | `INSERT OR REPLACE` on samples. Expected, not a warning |
| Clock skew, sample timestamped in the future | Store it. Component 03 excludes it from the window |
| `sleep` and `exercise` never appear | Normal. Every downstream consumer treats them as optional |
| Payload larger than expected | No size cap. Store it. A cap would silently truncate history |
| Same payload fetched twice | `INSERT OR IGNORE` on sha256. One row |

---

## 8. Tests

`tests/unit/ingest/`

| Test | Asserts |
|---|---|
| `test_normalise_matches_real_schema` | Parsing the captured fixture yields the expected typed rows |
| `test_normalise_handles_duplicate_app_version_key` | Last value wins, no exception |
| `test_normalise_rejects_naive_timestamp` | Raises rather than assuming a zone |
| `test_steps_are_daily_buckets` | A 24-hour bucket is one row, not 1440 |
| `test_missing_sleep_and_exercise_is_normal` | Zero rows, no error, no warning |
| `test_implausible_hr_is_stored_not_dropped` | Filtering belongs to component 03 |
| `test_synthetic_is_deterministic` | Same seed, byte-identical payload, twice |
| `test_synthetic_injection_matches_causes_yaml` | Injected effect sizes equal the knowledge table |
| `test_nonwear_creates_gap_not_zero` | No sample rows in the window, rather than zero-valued ones |
| `test_live_bridge_timeout_raises_source_unavailable` | Against a stubbed transport, no network |
| `test_live_bridge_never_logs_token` | The token appears in no log record or exception message |
| `test_live_bridge_falls_back_through_paths` | `/?days=N`, then `/`, then `/latest` |
| `test_raw_stored_before_normalise` | A normalisation failure still leaves the raw row |
| `test_cohort_missing_labels_is_hard_error` | Stanford replay without `cohort_labels.yaml` raises |

---

## 9. Exit condition

```bash
uv run pytest tests/unit/ingest -q
uv run wha demo run illness-onset --dry-run
```

The second prints the normalised row counts for a 30-night synthetic scenario without touching the
network, the LLM or the phone.
