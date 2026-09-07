# Component 10. Tools

**Phase:** B. **Module:** `src/wha/agent/tools/`. **Depends on:** 02 storage, 12 retrieval.

Seven tools. All **T1**: subject-scoped reads that carry provenance and cannot create or change a
record. There is no T2, T3 or T4 tool, and there is no tool that reaches the network except through
the allow-list.

---

## 1. The registry

**A tool not in this table does not exist.** A call for anything else raises `PermissionDenied`,
writes `permission_decision='denied'`, and changes nothing.

| Tool | Returns | Reads | Network |
|---|---|---|---|
| `get_nightly_features(start, end)` | Derived nightly metrics | `nightly_features` | no |
| `get_personal_baseline(night_date)` | Centre, scale, usable nights, rung | `baselines` | no |
| `get_known_events(start, end)` | Recorded exercise, sleep, steps | `exercise_sessions`, `sleep_stages`, `step_buckets` | no |
| `get_data_quality(start, end)` | Coverage, dropped counts, gaps | `nightly_features` | no |
| `find_similar_past_episodes(pattern)` | This subject's own comparable closed episodes and their outcomes | `episodes`, `outcomes` | no |
| `retrieve_clinical_evidence(query, layer?)` | Passages with source ids | local index | no |
| `get_local_disease_activity(area?)` | NEA dengue clusters, air quality | **allow-listed endpoint only** | yes |

**Every tool is read-only. There is no write tool, no send tool, no shell, no code execution, no URL
fetch, and no open web search.** The notifier is not in this table and the model cannot reach it.

That is the strongest sentence available about this system's blast radius, and it is only true if
this table stays closed. Adding a tool is a contract change and therefore a blocker.

---

## 2. Common shape

```python
class ToolResult(BaseModel):
    tool_name: str
    args: dict
    ok: bool
    value: Any                      # a typed model, never a raw row or a raw dict
    source_ids: list[str]           # what this came from
    as_of_utc: datetime             # when the underlying data was recorded
    freshness: Literal["fresh", "stale", "missing"]
    note: str | None                # why it is stale or missing, in plain language
```

**Provenance and freshness are not optional.** In an agentic loop the output of one cycle is the
input to the next, so a wrong or stale read propagates into every downstream decision. Every return
carries where it came from, when, and whether that is good enough.

`freshness` is `stale` beyond `INGEST_STALE_WARN_HOURS`, `missing` when there is nothing at all. A
stale read is **returned with the flag**, never silently substituted and never hidden.

Arguments are validated by a Pydantic model per tool. Date ranges are clamped to the subject's own
data, are capped at 90 days, and **cannot reference another subject**: `subject_id` is injected by
the runtime from the episode and is not a model-supplied argument. That single choice removes
cross-subject access as a possibility rather than as a rule.

---

## 3. Caching and determinism

Identical `(tool_name, args)` within one episode returns the cached result and does **not** re-query.

Three reasons: it bounds a model that loops on the same call, it makes cassette replay exact, and it
makes the trace readable. The cache is per episode and is discarded on close.

Repeated identical calls still increment `tool_call_count`, so a looping model still hits
`MAX_TOOL_CALLS_PER_EPISODE`. Caching must not become an infinite-loop loophole.

---

## 4. `find_similar_past_episodes`

The most interesting tool, and the one the model calls with a pattern it chooses.

```python
def find_similar_past_episodes(pattern: EpisodePattern) -> list[PastEpisodeSummary]
```

Matches on the shape of this episode: peak residual, number of elevated nights, whether exercise was
recorded, month of year. Returns closed episodes only, with their disposition and what resolved
them.

**This is the subject's own history, never anyone else's.** No cross-subject retrieval exists, not
even for cohort subjects, because that would be a different person's health data.

It is what lets the agent notice "you had a near-identical episode in March that turned out to be a
hangover", which is exactly the reasoning a person would do and which no fixed pipeline produces.

---

## 5. `get_local_disease_activity`

The only tool that touches the network.

- Endpoints come from `data/knowledge/sources.yaml`, which is read-only and human-authored.
  **Anything not in that file is refused.** No arbitrary URL, ever.
- Currently: NEA dengue cluster GeoJSON and air quality, both open, both unauthenticated, both from
  a named authority.
- The response is **untrusted input**: schema-validated on read, and only typed fields propagate.
- Cached for 6 hours on disk. Cluster data does not change hourly.
- Unreachable returns `ok=False`, `freshness="missing"`, and a note. **Never raises into the graph.**

> **Open web search is deliberately absent.** This system holds private health data and has an
> outbound channel to a phone. Adding arbitrary untrusted web content completes the lethal trifecta,
> and a claim from a random page cannot be cited as clinical evidence while the entire grounding
> story is claim-to-source enforcement over a curated corpus. Reach is extended by adding a named
> source to the allow-list, not by opening the door.

---

## 6. Failure handling

**No tool raises into the graph.** Every failure returns `ok=False` with a note, and the model
decides what to do about it. A missing read is information, not a crash.

| Failure | Return |
|---|---|
| No rows in range | `ok=True`, empty value, `freshness="missing"`, note explaining |
| Data older than the warn threshold | `ok=True`, `freshness="stale"`, note with the age |
| Network endpoint unreachable | `ok=False`, `freshness="missing"`, note. One `system_status` row |
| Malformed external response | `ok=False`, note. `safety_event` recorded |
| Argument validation failure | `PermissionDenied`. **This one does surface**, because a malformed call is a control problem, not a data problem |

---

## 7. Audit

Every call writes one `audit_events` row before the result is returned: `tool_name`, `tool_args_json`,
`tool_result_json`, `source_ids` into `sources_json`, `control_tier='T1'`, `permission_decision`,
`latency_ms`.

`tool_result_json` is **truncated at a size cap** with a marker, because a 90-day feature dump would
bloat the log. The cap is a constant and the truncation is visible, never silent.

---

## 8. Edge cases

| Case | Behaviour |
|---|---|
| Range wider than 90 days | Clamped, note records the clamp. Not an error |
| Range in the future | Clamped to today |
| Model supplies `subject_id` | Ignored. Injected from the episode. Recorded as an attempted expansion |
| Model calls a tool 20 times identically | Cached after the first, counter still increments, cap eventually stops it |
| `sources.yaml` names an endpoint that now 404s | `ok=False`, note, status row. Not a crash |
| A retrieval query is empty | `ok=True`, empty result, note. Do not fabricate a query |

The `subject_id` row is worth stating plainly: **self-expansion is denied, and attempts are logged
and counted.** That count appears in the governance section of the write-up.

---

## 9. Tests

`tests/unit/agent/test_tools.py`

| Test | Asserts |
|---|---|
| `test_registry_is_closed` | Exactly seven tools; an eighth name raises `PermissionDenied` |
| `test_no_tool_can_write` | Every tool run against a read-only connection succeeds |
| `test_subject_id_is_injected_not_supplied` | A model-supplied `subject_id` for another subject returns this subject's data and logs an attempt |
| `test_cross_subject_access_impossible` | No argument combination reaches another subject's rows |
| `test_every_result_carries_provenance` | `source_ids`, `as_of_utc` and `freshness` populated on all seven |
| `test_stale_data_is_flagged_not_hidden` | Beyond the warn threshold, `freshness="stale"` and the note gives the age |
| `test_missing_data_returns_ok_false_not_raise` | |
| `test_identical_call_is_cached` | Second call issues no query |
| `test_cached_call_still_increments_counter` | Caching is not a loop loophole |
| `test_range_clamped_to_90_days` | With a note |
| `test_disease_activity_refuses_unlisted_url` | Any URL not in `sources.yaml` is refused |
| `test_disease_activity_unreachable_does_not_raise` | |
| `test_malformed_external_response_logs_safety_event` | |
| `test_tool_call_writes_audit_row` | With `control_tier='T1'` |
| `test_large_result_is_truncated_visibly` | Marker present, not silent |
| `test_no_network_in_six_of_seven_tools` | Asserted against a blocked transport |

---

## 10. Exit condition

```bash
uv run pytest tests/unit/agent/test_tools.py -q
```

Green, with `test_registry_is_closed` and `test_cross_subject_access_impossible` passing. Those two
are what the governance claim rests on.
