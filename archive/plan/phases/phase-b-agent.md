# Phase B. The agent

The LLM, the graph, retrieval, safety and the notifier. **Everything still runs offline**, against
recorded responses, because the endpoint is expected to be down most of the time.

**Done when** `uv run wha demo run illness-onset` completes an episode end to end against cassettes,
with no network, producing a validated `EpisodeOutcome` that matches the fixture's `expect` block.

**Do not start until Phase A's gate has been read.**

---

## Tasks

| ID | Title | Depends on | Component |
|---|---|---|---|
| B-01 | LLM provider protocol and the cassette provider | A-02 | 13 |
| B-02 | `ollama_native` and `openai_compatible` providers | B-01 | 13 |
| B-03 | Prompt files, the six-component structural test, versioning | B-01 | 13 |
| B-04 | Corpus fetch, parse, section-aware chunking | A-02 | 12 |
| B-05 | BM25 index, dense index, reciprocal rank fusion | B-04 | 12 |
| B-06 | Deterministic claim-to-source enforcement | B-05 | 12 |
| B-07 | `red_flags.yaml` loader, tiers A and B | A-02 | 11 |
| B-08 | Tier C LLM second opinion, union with the rules | B-07, B-01 | 11 |
| B-09 | Outbound validation | B-07, A-19 | 11 |
| B-10 | Injection detection and the poisoned fixture | B-05 | 11 |
| B-11 | Output checks before display | B-06 | 11 |
| B-12 | Tool registry, common result shape, provenance and freshness | A-03 | 10 |
| B-13 | The seven tools | B-12, B-05 | 10 |
| B-14 | Graph state, checkpointer, compile | B-01, A-21 | 09 |
| B-15 | `preload` and `investigate` nodes | B-14, B-13 | 09 |
| B-16 | `believe` and `decide` nodes, and the veto | B-15, A-21 | 09 |
| B-17 | `ask` and `measure` nodes, and the interrupt discipline | B-16, B-09 | 09 |
| B-18 | `conclude`, `critique`, `review` nodes | B-17, B-11 | 09 |
| B-19 | `Notifier` protocol and Telegram send | B-09 | 15 |
| B-20 | Telegram receive, callbacks, offset persistence | B-19 | 15 |
| B-21 | Service: status, subjects, nights | A-13 | 14 |
| B-22 | Service: episodes, including the bounded episode Q&A | B-18, B-06 | 14 |
| B-23 | Service: audit, evaluation, settings | A-04, A-28 | 14 |
| B-24 | CLI: `episode step`, `demo run`, `belief explain` | B-18 | 17 |
| B-25 | Eval: adversarial suite | B-10, B-24 | 16 |
| B-26 | The frozen scenario suite, end to end | B-24 | 09 |
| B-27 | **Optional.** Re-record cassettes against a live model | B-26 | 13 |

---

## Critical path

```
B-01 -> B-12 -> B-14 -> B-15 -> B-16 -> B-17 -> B-18 -> B-24 -> B-26
```

Retrieval (B-04 to B-06) and safety (B-07 to B-11) are parallel tracks that join at B-15 and B-17.

---

## Order notes

**B-01 first, and cassettes before providers.** Every later test runs against recorded responses. A
live provider written first invites tests that quietly hit the network, which is the failure this
whole arrangement prevents.

**B-03 is a structural test as much as a set of files.** Every prompt must carry all six components,
and **refusal conditions separately asserted**, because that is the one usually omitted and it is
what makes `INSUFFICIENT_DATA` reachable in practice.

**B-07 before B-08, always.** The deterministic rules are the floor. Building the model tier first
invites a design where the model is load-bearing for safety, which is exactly what this project
argues against.

**B-09 before B-17.** No send exists until outbound validation exists. There must never be a commit
in the repository where a message can leave the system unvalidated.

**B-12 before B-13.** The registry, the provenance shape and the denial path come before any tool,
so `test_registry_is_closed` is true from the first tool onward.

**B-17 is where the interrupt discipline is proved.** Resuming re-runs the whole node from the top.
Every write before an `interrupt()` must be idempotent and every send must check `notifications`
first. `test_interrupt_resume_does_not_double_send` is the test that matters.

**B-10 needs the poisoned fixture and its clean twin.** Both are committed. The demonstration is the
side-by-side, and the negative controls are what make it a test rather than a demo.

---

## Cassettes

**Already authored and committed.** Nineteen files under `tests/fixtures/llm_cassettes/`, keyed on
`(prompt_id, scenario)` with a `default.json` fallback per prompt id. **No recording step is
required and the endpoint is not needed at any point in this phase.**

Every one carries `origin: AUTHORED_FIXTURE` and `model_id: authored-fixture`, so the audit trail
and the demo trace never pretend a model was consulted when it was not.

**A miss is a hard failure** naming the prompt id, the scenario and the path, never a fall-through to
a live call.

Re-recording against the live endpoint with `uv run wha llm record` is **optional** and is not a
prerequisite for anything. The system is fully demonstrable without it.

---

## Exit condition

```bash
uv run pytest -q
uv run ruff check src tests
uv run wha demo run illness-onset
uv run wha demo run alcohol-night
uv run wha demo run workout-explained
uv run wha demo run red-flag
uv run wha demo run injection-poisoned && uv run wha demo run injection-clean
uv run wha eval adversarial
```

Every scenario reaches the disposition its fixture expects. The two injection runs produce the same
disposition, and only the poisoned one emits `safety_event='injection_contained'`.
