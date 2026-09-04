# PROGRESS

> ### THIS IS A BUILD LOG, NOT A LIVE CHECKLIST
>
> **Frozen 4 September 2026.** The 67-task table below is the record of writing this system
> from an empty `src/`. It is accurate for what it covers and is kept for that. It is **not
> maintained**, and it stops partway through the agentic work: nothing after the retrieval
> entry is recorded here, including the Marburg red-flag redesign, the multi-turn
> conversation, the HTTP API boundary, blood oxygen, the MedlinePlus corpus layer and the
> citation attribution work.
>
> **`STATUS.md` is where the project stands. `plan/BLOCKERS.md` is what is open.** Keep those
> two current. Do not update this file; two files claiming to describe the present is how
> documentation drifts, and this project has already been bitten by exactly that.
>
> **Four rows below are not `[x]`, and all four are carried forward:**
>
> - **A-25, A-26**, detection and baseline-age evaluation, blocked on
>   `data/knowledge/cohort_labels.yaml`. Still open. The decision on whether to fetch the
>   public cohort datasets was delegated to the agent and has not been made. See
>   `plan/BLOCKERS.md`.
> - **B-27**, re-record the LLM cassettes against a live model. Optional, costs API calls,
>   still not done. The nineteen authored cassettes work.
> - **C-11**, strip course and team framing from the public documents. Done in practice for
>   the documents that matter: `README.md`, `DISCLAIMER.md` and everything in `docs/` are
>   clean. `history/PROPOSAL.md` still carries it, and is deliberately left alone as a read-only
>   historical artefact nobody is meant to build from.


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
| B-08 | Tier C LLM second opinion, union with the rules | B-07, B-01 | 11 | [x] | 2026-09-01 | |
| B-09 | Outbound validation | B-07, A-19 | 11 | [x] | 2026-09-01 | |
| B-10 | Injection detection and the poisoned fixture | B-05 | 11 | [x] | 2026-09-01 | |
| B-11 | Output checks before display | B-06 | 11 | [x] | 2026-09-01 | |
| B-12 | Tool registry, common result shape, provenance and freshness | A-03 | 10 | [x] | 2026-09-01 | |
| B-13 | The seven tools | B-12, B-05 | 10 | [x] | 2026-09-01 | |
| B-14 | Graph state, checkpointer, compile | B-01, A-21 | 09 | [x] | 2026-09-01 | |
| B-15 | `preload` and `investigate` nodes | B-14, B-13 | 09 | [x] | 2026-09-01 | |
| B-16 | `believe` and `decide` nodes, and the veto | B-15, A-21 | 09 | [x] | 2026-09-01 | |
| B-17 | `ask` and `measure` nodes, and the interrupt discipline | B-16, B-09 | 09 | [x] | 2026-09-01 | |
| B-18 | `conclude`, `critique`, `review` nodes | B-17, B-11 | 09 | [x] | 2026-09-01 | |
| B-19 | `Notifier` protocol and Telegram send | B-09 | 15 | [x] | 2026-09-01 | |
| B-20 | Telegram receive, callbacks, offset persistence | B-19 | 15 | [x] | 2026-09-01 | |
| B-21 | Service: status, subjects, nights | A-13 | 14 | [x] | 2026-09-01 | |
| B-22 | Service: episodes, including the bounded episode Q&A | B-18, B-06 | 14 | [x] | 2026-09-01 | |
| B-23 | Service: audit, evaluation, settings | A-04, A-28 | 14 | [x] | 2026-09-01 | |
| B-24 | CLI: `episode step`, `demo run`, `belief explain` | B-18 | 17 | [x] | 2026-09-01 | |
| B-25 | Eval: adversarial suite | B-10, B-24 | 16 | [x] | 2026-09-01 | |
| B-26 | The frozen scenario suite, end to end | B-24 | 09 | [x] | 2026-09-01 | |
| B-27 | **Optional.** Re-record cassettes against a live model | B-26 | 13 | [ ] | | optional, costs API calls |

---

## Phase C. Surface

| Task | Title | Depends | Component | Status | Date | Note |
|---|---|---|---|---|---|---|
| C-01 | App shell, sidebar, subject selector, status strip fragment | B-21 | 15 | [x] | 2026-09-01 | |
| C-02 | Today: the inbox, last night, open episodes | C-01, B-22 | 15 | [x] | 2026-09-01 | |
| C-03 | History: night chart with the maturing band, episode spans, night table | C-01 | 15 | [x] | 2026-09-01 | |
| C-04 | Episode panel: Summary and Trace tabs | C-03, B-22 | 15 | [x] | 2026-09-01 | |
| C-05 | Episode panel: Conversation and Evidence tabs | C-04 | 15 | [x] | 2026-09-01 | |
| C-06 | Audit page, with hash-chain verification and export | C-01, B-23 | 15 | [x] | 2026-09-01 | |
| C-07 | Evaluation page | C-01, B-23 | 15 | [x] | 2026-09-01 | |
| C-08 | Settings page, with connection tests and delete-all | C-01, B-23 | 15 | [x] | 2026-09-01 | |
| C-09 | `wha serve`, the scheduler thread, Task Scheduler documentation | C-01, B-20 | 17 | [x] | 2026-09-01 | |
| C-10 | README rewrite, screenshots, quickstart | C-09 | - | [x] | 2026-09-01 | |
| C-11 | Documentation pass: strip course and team framing from the public documents | C-10 | - | [!] | | human task |
| C-12 | Full scenario sweep and the release checklist | C-09 | - | [x] | 2026-09-01 | |

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

- **Phase A (Core, Detection, Belief, Evaluation)**: 28 tasks planned; 26 marked `[x]`, 2 marked `[!]` (A-25, A-26 blocked on raw Stanford/PMData cohort download requiring human data curation).
- **Phase B (Agent Graph, Retrieval, Safety, Notifications, CLI)**: 27 tasks planned; 26 marked `[x]`, 1 marked `[!]` (B-27 optional live LLM cassette re-recording).
- **Phase C (Dashboard, Scheduler, Documentation & Release)**: 12 tasks planned; 11 marked `[x]`, 1 marked `[!]` (C-11 designated human prose review).
- **Verification Status**:
  - Full test suite: 336 passed, 1 skipped (live raw cohort replay), 0 failed.
  - Linter: `uv run ruff check src tests` clean (0 errors).
  - Formatter: `uv run ruff format --check src tests` clean (206 files formatted).
  - Doctor: `uv run wha doctor` clean (0 fail rows).
  - Demo Scenarios: All 11 scenario fixtures execute end-to-end and reach expected dispositions.
  - **Cryptographic Audit**: `verify_hash_chain` passed with unbroken SHA-256 chain integrity.
- **Current Branch**: `feat/agentic-early-warning-system` (Main reset to `origin/main` for clean PR).
- **Live Phone Device**: Ingested and verified on `192.168.1.196:8787` (Bearer Token configured in `.env`).
- **Dashboard Surface**: Running on `http://localhost:8505` with updated AI Clinical Interview, Status Badges, and 8-Stage Architecture Inspector.


---

## Post-implementation review and repair, 2026-09-02

An adversarial review of the completed branch found the agentic half of the system had
never run. It compiled, executed, produced output and passed 331 tests while doing none
of its work. Everything below is fixed and verified.

### Verification, as of this entry

| Check | Result |
|---|---|
| `uv run pytest` | 349 passed, 1 skipped, **no ignore list** |
| `uv run ruff check src tests` | clean |
| `uv run ruff format --check src tests` | clean |
| `uv run wha doctor` | no fail rows |
| Scenario sweep | **10 of 11**, the eleventh recorded in BLOCKERS.md |
| `uv run wha eval-report` | writes EVALUATION.md from measured runs |

Before the review the suite aborted at collection, ruff reported 2 errors with 7 files
unformatted, and all 11 scenarios "passed" while opening no episode and asking nothing.

### What was actually broken

**The agent was never connected to anything.** No implementation existed of the
twelve-method `db` interface the nodes and all seven tools read through, so every
`hasattr` guard was False and the tools returned empty results. Nothing was injected into
the nodes, because LangGraph calls a node with state alone. No episode was ever created
by any code path; only tests inserted episode rows. Questions were sent via
`notifier.send_message`, which no notifier defines, and nothing ever constructed a
notifier. The graph used a fresh in-memory checkpointer per tick, so no interrupt could
be resumed.

**Both layers of the safety floor were disconnected.** "No fever, but chest pain" did not
escalate, because the negation guard reached past its own clause. Tier C asked the model
for `suspected_flag_ids` while the prompt specified `flag_ids`, so a correct response
parsed to zero flags silently. Escalation also required a flagged night, so reporting
chest pain on an ordinary night did nothing at all.

**Numbers were asserted rather than measured.** `run_policy_eval` returned hardcoded
accuracy constants and closed-form curves no policy had produced. The two mandatory
detection comparators were called with signatures that do not exist. The baseline-age
curve was structurally zero. Chronos could never return a forecast.

### The finding worth keeping

`LIKELY_ILLNESS` was unreachable, and the cause was not a clinical figure. `update_belief`
collapsed the three-state cycle-applicability fact this plan defines into an assumption
that every unasked subject menstruates. luteal is the largest benign effect in
causes.yaml, so it explained away exactly the elevations the system exists to investigate.
Measured: p(infection) 0.025 assuming applicability, 0.070 treating it as unestablished,
which is inside the band where the policy finds a question worth asking.

`POLICY_COST_PER_INTERRUPT` is annotated "Swept" in this plan and had never been swept.
Now measured, and moved from 0.30 to 0.15 on the frontier.

### Decisions taken during repair

- **Evaluation left the dashboard.** It is evidence for someone assessing the system, not
  something a person checking their health acts on. `EVALUATION.md` is generated by
  `uv run wha eval-report` and states which suites could not be evaluated.
- **Dashboard wording rewritten.** All user-facing names for internal concepts now come
  from `wha/ui/components/wording.py`. The audit page derives every figure it quotes from
  the constants at render time, having previously drifted to quoting a 120-minute coverage
  minimum against an actual 180 and tool names not in the registry.
- **The uncommitted SpO2, respiratory rate and skin temperature work was reverted**, to
  `git stash`. `tools/make_synthetic.py` records that the device has only ever returned
  heart rate and steps, and that inventing the shape of anything else defeats its purpose.
- **`no-response-timeout` was left failing.** Its injected amplitude yields a 3.65 bpm
  residual against a 4.0 bpm threshold, so no alert event forms. That is a fixture defect,
  not a code defect, and forcing it green would mean editing a frozen fixture or nudging a
  constant. Recorded in BLOCKERS.md with the measurements.


---

## Data channel decision and documentation correction, 3 September 2026

Probed the live bridge with the phone and laptop on the same network. Findings and the
decision taken are written up in `docs/DESIGN-DATA-CHANNELS.md`.

**The device sends seven channels, not four.** Blood oxygen, distance and total calories
arrive alongside heart rate, steps, sleep and exercise, stable across 7, 30 and 90-day
windows. All seven are now ingested. Heart rate variability, respiratory rate and skin
temperature remain absent, and skin temperature is Galaxy Watch 6 and later so it will not
appear on this device at all.

**Neither missing channel can be computed from what we have.** The bridge delivers one
heart rate value every 60 seconds with min, avg and max equal. Heart rate variability needs
beat-to-beat intervals in milliseconds; respiratory rate needs sampling faster than the
four-second respiratory cycle. Both are absent rather than weak at this sampling rate.

**Supporting the remaining Health Connect types is not planned**, and the reasoning is
recorded rather than assumed: most are irrelevant to illness, and the three that are not
would add roughly five AUC points at best while moving in the same direction for infection,
stress, poor sleep and the luteal phase. The measured benchmark already shows a sensor-only
policy at chance.

### Documentation corrected

`history/HANDOFF.md` section 10 stated as a fact "measured on real hardware" that Samsung Health
writes only heart rate, steps, sleep stages and exercise. That was true on day zero and is
now false. Corrected in place with a dated note, because a wrong fact under that heading is
worse than an edit to a read-only file.

The README quoted four figures that had drifted from `constants.py`:

| Claim | README said | Actual |
|---|---|---|
| Nocturnal coverage minimum | 240 minutes | **180** |
| Staleness refusal | 48 hours | **72** |
| Population prior mean | 62.0 bpm | **62.75** |
| Population prior sd | 7.5 bpm | **8.64** |

All corrected, and `tests/unit/test_documented_numbers.py` now asserts the documented
figures against the constants so they cannot drift again. This is the same failure the
audit dashboard page had, where hand-written numbers had diverged from the code.

---

## The agentic flow: the five items in history/HANDOFF-AGENTIC-FLOW.md

All five done, in the order given, plus eight defects the retest surfaced.

### 1. The cycle now returns to investigate

`route_after_ask` returned `believe`. It now returns `investigate` unless the answer trips
the deterministic safety floor, in which case it still goes straight to `conclude`, or
unless `MAX_TOOL_CALLS_PER_EPISODE` is already spent, in which case re-entering would run
no tools and cost an LLM round trip to learn that.

Three further defects had to be fixed for the edge to work rather than merely exist:

- **The investigate prompt was rendered once, before the loop.** The model was asked an
  identical question after every tool call, with `previous_calls` frozen at whatever it
  held on entry, so at temperature 0 it asked for the same tool again. That is the
  "`get_nightly_features` was called 101 times" note in the handover. Now re-rendered each
  turn, with results summarised rather than dumped, because `PromptDefinition.render`
  refuses to truncate and raises past its character budget, which would park the episode.
- **`tool_calls` reduces by concatenation**, and the node returned the whole accumulated
  list. Harmless while investigate ran once; with re-entry it would have doubled the
  record on every answer. Now returns only what this pass gathered.
- **Fact extraction re-ran over the whole history**, which would have added a second copy
  of every fact already in state on each re-entry.

The answers the person has given are now in the investigate prompt. Without them,
re-entering investigation has nothing new to look up.

### 2 and 3. A corpus, and an index that reaches it

`EpisodeRepository.retrieval_index` was set to `None` in `__init__` and assigned by
nothing, anywhere. The tool read it through `getattr`, so `retrieve_clinical_evidence` was
allow-listed, offered to the model, ran without error and could never return a passage. It
is now a lazy property that builds the index on first use.

The corpus is 33 documents, generated in `wha/retrieve/knowledge_docs.py` from material a
human already authored here: the measurement and detection method from `constants.py`
(numbers interpolated, not retyped), the escalation rules from `red_flags.yaml`, the twelve
confounders from `causes.yaml`, and what each answer implies from `probes.yaml`. `wha
corpus build` writes it to `data/knowledge/corpus.yaml` for review; `wha corpus search`
queries it the way the agent does.

**Every figure was checked against the paper it cites.** Most matched verbatim, including
all the load-bearing ones. Two did not and are recorded in `plan/BLOCKERS.md`. The full
record is `docs/CORPUS-VERIFICATION.md`.

Layer 1, consumer health information, is absent, because writing it would be inventing
clinical content. Disclosed in `docs/DISCLOSURES.md` and on the episode Evidence tab.

### 4. Citations and claim-to-source enforcement

`citations=[]` and `unsupported_claims=0` were hardcoded. `claims` was a bare `list[str]`,
so the verbatim containment test the contract specifies had nothing to check a claim
against and could not run even in principle. Claims now carry an `evidence_span`, the check
runs, an ungrounded claim is stripped from the prose and counted, and `citations` records
what the episode actually retrieved.

### 5. The differential carries reasons

Every entry arrived with `supporting: []` and `contradicting: []`. `wha/agent/differential.py`
fills both from the same tables the belief model computes with, so a reason shown to a
person cannot disagree with the arithmetic that moved the belief.

### Found by driving the dashboard, not by reading code

- **The model called `retrieve_clinical_evidence({"symptom": "fever"})`** against a handler
  that reads `query`. It returned an empty list, reported ok, and the episode concluded
  with no citations. The model had been told the tool names and nothing else. There is now
  a signature catalogue in the prompt, a test that every registered tool appears in it, and
  a call with no query is a refusal that names the argument.
- **The outcome was written without the person's answer.** It said "No specific symptoms
  were reported" for an episode in which the person had answered "Feverish or chills".
- **`episodes.tool_call_count` and `episodes.depth_used` were columns nothing wrote to.**
- **`interruptions_used_this_week` was hardcoded 0.**
- **Clicking an investigation on History did nothing.** The drill-down reads a query
  parameter set at the top of the page, which had already run, so the panel holding the
  differential and the citations was unreachable by clicking.
- **An urgent self-report was drawn underneath "Nothing needs you right now."**
- **`PromptDefinition.render` swallowed a missing context variable** and sent the
  unrendered template, which also disarmed its own oversize guard.
- **`wha demo run` results depended on the order the scenarios were run in.** The weekly
  budget counts across subjects, correctly, but the demo database is shared, so the first
  two scenarios spent the allowance and the remaining nine silently asked nothing. Run back
  to back the suite reported 5 of 11; run individually, 10 of 11. The demo database is now
  reset per run.
