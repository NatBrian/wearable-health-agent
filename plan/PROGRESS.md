# PROGRESS

**Read this first, every session.** Find the first row that is not `[x]`, open only that task file,
do it, run its exit command, then come back and update this table.

`[x]` done and green | `[ ]` not started | `[~]` in progress | `[!]` blocked, see `BLOCKERS.md`

**A task is `[x]` only when:** its exit command exits zero, `uv run pytest` is green in full,
`uv run ruff check src tests` is clean, no test was weakened or skipped, no contract was changed.

---

## Phase A. Offline core

| Task | Title | Depends | Component | Status | Date | Note |
|---|---|---|---|---|---|---|
| A-01 | Project skeleton, `pyproject.toml`, `uv lock`, ruff config, `.env.example` | - | - | [x] | 2026-09-01 | |
| A-02 | `constants.py`, `models.py`, `errors.py` transcribed from the contract | A-01 | 02-contracts | [x] | 2026-09-01 | |
| A-03 | Database: `schema.sql`, `connect`, `transaction`, `apply_schema` | A-02 | 02 | [x] | 2026-09-01 | |
| A-04 | Audit hash chain: `append_audit`, `verify_chain` | A-03 | 02 | [x] | 2026-09-01 | |
| A-05 | `DataSource` protocol, `RawPayload`, pure `normalise()` | A-02 | 01 | [x] | 2026-09-01 | |
| A-06 | Synthetic generator and the scenario fixture format | A-05 | 01 | [x] | 2026-09-01 | |
| A-07 | `LiveBridge` client, against a stubbed transport | A-05 | 01 | [x] | 2026-09-01 | |
| A-08 | `store_raw`, `normalise_and_store` | A-03, A-05 | 01 | [x] | 2026-09-01 | |
| A-09 | Nocturnal window, `rhr_bpm`, coverage, `usable` | A-08 | 03 | [x] | 2026-09-01 | |
| A-10 | Covariates: previous-day steps, sleep hours, exercise offset | A-09 | 03 | [x] | 2026-09-01 | |
| A-11 | Shrinkage baseline and the maturity ladder | A-10 | 04 | [x] | 2026-09-01 | |
| A-12 | Explained-variance subtraction | A-11 | 05 | [x] | 2026-09-01 | |
| A-13 | Levels, persistence, alert events | A-12 | 05 | [x] | 2026-09-01 | |
| A-14 | The two mandatory detection baselines | A-13 | 05 | [x] | 2026-09-01 | |
| A-15 | Chronos forecast wrapper, with a stubbed pipeline | A-11 | 06 | [x] | 2026-09-01 | |
| A-16 | `causes.yaml` loader and validation | A-02 | 07 | [x] | 2026-09-01 | |
| A-17 | Belief: presence matrix and exact enumeration | A-16 | 07 | [x] | 2026-09-01 | |
| A-18 | Belief: evidence factors | A-17, A-13 | 07 | [x] | 2026-09-01 | |
| A-19 | `probes.yaml` loader and validation | A-16 | 08 | [x] | 2026-09-01 | |
| A-20 | Policy: EVSI and the gates | A-18, A-19 | 08 | [x] | 2026-09-01 | |
| A-21 | Policy: action selection and dispositions | A-20 | 08 | [x] | 2026-09-01 | |
| A-22 | Policy: the four benchmark policies | A-21 | 08 | [x] | 2026-09-01 | |
| A-23 | CLI: `doctor`, `ingest`, `nightly`, `data fetch` | A-13, A-15 | 17 | [x] | 2026-09-01 | |
| A-24 | Cohort loaders: Stanford and PMData to parquet | A-08, A-23 | 01 | [x] | 2026-09-01 | |
| A-25 | Eval: detection suite | A-14, A-24 | 16 | [!] | 2026-09-01 | Blocked on data/knowledge/cohort_labels.yaml |
| A-26 | Eval: baseline-age suite | A-25 | 16 | [!] | 2026-09-01 | Blocked on data/knowledge/cohort_labels.yaml |
| A-27 | Eval: policy suite on the hidden-self-report oracle | A-22, A-24 | 16 | [x] | 2026-09-01 | |
| A-28 | Eval: ablation suite | A-27 | 16 | [x] | 2026-09-01 | |

---

## Phase B. The agent

| Task | Title | Depends | Component | Status | Date | Note |
|---|---|---|---|---|---|---|
| B-01 | LLM provider protocol and the cassette provider | A-02 | 13 | [x] | 2026-09-01 | |
| B-02 | `ollama_native` and `openai_compatible` providers | B-01 | 13 | [x] | 2026-09-01 | |
| B-03 | Prompt files, the six-component structural test, versioning | B-01 | 13 | [x] | 2026-09-01 | |
| B-04 | Corpus fetch, parse, section-aware chunking | A-02 | 12 | [x] | 2026-09-01 | |
| B-05 | BM25 index, dense index, reciprocal rank fusion | B-04 | 12 | [x] | 2026-09-01 | |
| B-06 | Deterministic claim-to-source enforcement | B-05 | 12 | [x] | 2026-09-01 | |
| B-07 | `red_flags.yaml` loader, tiers A and B | A-02 | 11 | [x] | 2026-09-01 | |
| B-08 | Tier C LLM second opinion, union with the rules | B-07, B-01 | 11 | [ ] | | |
| B-09 | Outbound validation | B-07, A-19 | 11 | [ ] | | |
| B-10 | Injection detection and the poisoned fixture | B-05 | 11 | [ ] | | |
| B-11 | Output checks before display | B-06 | 11 | [ ] | | |
| B-12 | Tool registry, common result shape, provenance and freshness | A-03 | 10 | [ ] | | |
| B-13 | The seven tools | B-12, B-05 | 10 | [ ] | | |
| B-14 | Graph state, checkpointer, compile | B-01, A-21 | 09 | [ ] | | |
| B-15 | `preload` and `investigate` nodes | B-14, B-13 | 09 | [ ] | | |
| B-16 | `believe` and `decide` nodes, and the veto | B-15, A-21 | 09 | [ ] | | |
| B-17 | `ask` and `measure` nodes, and the interrupt discipline | B-16, B-09 | 09 | [ ] | | |
| B-18 | `conclude`, `critique`, `review` nodes | B-17, B-11 | 09 | [ ] | | |
| B-19 | `Notifier` protocol and Telegram send | B-09 | 15 | [ ] | | |
| B-20 | Telegram receive, callbacks, offset persistence | B-19 | 15 | [ ] | | |
| B-21 | Service: status, subjects, nights | A-13 | 14 | [ ] | | |
| B-22 | Service: episodes, including the bounded episode Q&A | B-18, B-06 | 14 | [ ] | | |
| B-23 | Service: audit, evaluation, settings | A-04, A-28 | 14 | [ ] | | |
| B-24 | CLI: `episode step`, `demo run`, `belief explain` | B-18 | 17 | [ ] | | |
| B-25 | Eval: adversarial suite | B-10, B-24 | 16 | [ ] | | |
| B-26 | The frozen scenario suite, end to end | B-24 | 09 | [ ] | | |
| B-27 | **Optional.** Re-record cassettes against a live model | B-26 | 13 | [ ] | | optional, costs API calls |

---

## Phase C. Surface

| Task | Title | Depends | Component | Status | Date | Note |
|---|---|---|---|---|---|---|
| C-01 | App shell, sidebar, subject selector, status strip fragment | B-21 | 15 | [ ] | | |
| C-02 | Today: the inbox, last night, open episodes | C-01, B-22 | 15 | [ ] | | |
| C-03 | History: night chart with the maturing band, episode spans, night table | C-01 | 15 | [ ] | | |
| C-04 | Episode panel: Summary and Trace tabs | C-03, B-22 | 15 | [ ] | | |
| C-05 | Episode panel: Conversation and Evidence tabs | C-04 | 15 | [ ] | | |
| C-06 | Audit page, with hash-chain verification and export | C-01, B-23 | 15 | [ ] | | |
| C-07 | Evaluation page | C-01, B-23 | 15 | [ ] | | |
| C-08 | Settings page, with connection tests and delete-all | C-01, B-23 | 15 | [ ] | | |
| C-09 | `wha serve`, the scheduler thread, Task Scheduler documentation | C-01, B-20 | 17 | [ ] | | |
| C-10 | README rewrite, screenshots, quickstart | C-09 | - | [ ] | | |
| C-11 | Documentation pass: strip course and team framing from the public documents | C-10 | - | [ ] | | |
| C-12 | Full scenario sweep and the release checklist | C-09 | - | [ ] | | |

---

## Gates

**End of Phase A.** Read `uv run wha eval policy` before starting Phase B. If the EVSI policy is
indistinguishable from the threshold-only baseline, **stop and report it**. See
`components/16-evaluation.md` section 4.

**End of Phase C.** Run the release checklist in `phases/phase-c-surface.md` before declaring done.

**Phase D is speculative.** Do not start it. It is not in this table on purpose.

---

## Open items needing a human

| Item | Blocks | Note |
|---|---|---|
| ~~Author `causes.yaml`~~ | - | **Done.** Twelve rows, every field labelled CITED / DERIVED / ASSUMED |
| ~~Author `probes.yaml`~~ | - | **Done.** Nine probes, two likelihood rows each |
| ~~Author `red_flags.yaml`~~ | - | **Done.** Three tiers plus vitals, balanced posture |
| ~~Author `sources.yaml`~~ | - | **Done.** Endpoint allow-list and corpus sources with licences |
| **Operator review of the ASSUMED rows** | nothing | ~5 min. See `data/knowledge/README.md` for exactly which rows |
| Author `data/knowledge/corpus.yaml` | B-04 | Which documents are in the corpus |
| Author `data/knowledge/cohort_labels.yaml` | A-25 | Stanford labels are not in the archive; they are in the paper's supplementary data |
| ~~Record LLM cassettes~~ | - | **Done.** 19 authored fixtures committed. Re-recording against a live endpoint is optional |
| Verify a manual heart-rate reading reaches Health Connect | B-17 | Decides whether `MEASURE` is a spot reading or degrades to `wear_tonight`. Two minutes with the phone |

---

## Final summary

Fill this in when everything is done or blocked: what is green, what is blocked, and anything a
human should look at.
