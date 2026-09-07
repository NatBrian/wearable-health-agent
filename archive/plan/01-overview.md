# 01. Overview

**Status:** draft, under review. Once approved this folder is the implementation contract.
**Supersedes `history/PROPOSAL.md` wherever the two disagree.** `history/PROPOSAL.md` is the written narrative
artefact and is not the thing to code from. `04-decisions.md` records every point of divergence.

---

## 1. What the system is

Consumer wearables detect that something in your body changed. They cannot tell you why. A raised
overnight resting heart rate is produced by an incubating infection, by alcohol, by a hard training
session, by short sleep, by stress, by a recent vaccination, or by the luteal phase. To a wrist
sensor these look nearly identical and they demand opposite responses.

The system separates two jobs that are usually conflated.

**The monitor is deterministic and cheap.** Every morning it derives last night's resting heart rate
from the overnight window, compares it against the subject's own baseline, and decides whether
anything happened. No language model is involved. On a quiet night the cost is zero, and most nights
are quiet.

**The agent is the investigation.** When a deviation is flagged, a bounded agent opens an *episode*.
It investigates: it reads the history, looks for comparable past episodes, checks local disease
activity, retrieves clinical evidence, and decides for itself what to look at next. Underneath, a
deterministic model tracks which of twelve candidate causes are contributing. It runs an adaptive
interview, orders a measurement, escalates, or concludes. It reasons across several nights, holds state while it waits,
and terminates at a typed disposition.

**One decision is not the model's to make: whether to interrupt the human.** That is computed as
expected value of sample information on the action decision, net of a quantified interruption cost,
in arithmetic, outside the model. Every
other judgement in the investigation is the model's. Section 3.1 states the boundary precisely and
`04-decisions.md` D-102 gives the evidence for it.

---

## 2. The daily loop

```
  overnight     the watch records; Samsung Health syncs to Health Connect
      |
  morning       `wha nightly` runs (scheduler thread, or Windows Task Scheduler)
      |         ingest -> quality gate -> features -> baseline -> detector -> forecast
      |
      +-- quiet ----> one row in the night log. Nothing is sent. No LLM call.
      |               This is the overwhelmingly common case and the correct behaviour
      |
      +-- flagged --> deterministic red-flag intercept (plain code, always runs first)
                          |
                          +-- crossed ----> ESCALATE. Bypasses the agent entirely
                          |
                          +-- clear ------> episode opens, or an open episode resumes
                                  |
                                  (1) INVESTIGATE   the LLM drives, choosing its own
                                  |                 read-only tool calls until it has enough
                                  (2) BELIEF        exact update over 12 binary causes
                                  (3) POLICY        expected value of sample information
                                  |                 vs interruption cost. Not the LLM
                                  (4) ACT
                                        |
                                        +-- OBSERVE   stay silent, wait for another night
                                        +-- ASK       Telegram message, tappable options
                                        +-- MEASURE   Telegram message, requested reading
                                        +-- ESCALATE  Telegram message, care guidance
                                        +-- CONCLUDE  Telegram summary, link to dashboard
```

When the agent asks, the answer options arrive as inline buttons on the phone. Tapping one advances
the episode. Nothing has to be opened.

**The dashboard is for inspection, not operation.** On most days there is no reason to open it. The
system is silent by default and initiates only when it has something to say.

---

## 3. System shape

```
 Galaxy Watch 5
      | Samsung's own sync
      v
 Samsung Health --> Android Health Connect --> Health Connect Webhook app (local HTTP :8787)
      |
      | polled over the local network by DataSource:LiveBridge
      v
 +--------------------------------------------------------------------------+
 | INGEST         raw payload stored verbatim, then normalised               |
 |                DataSource is an interface with three implementations:     |
 |                LiveBridge | Synthetic | CohortReplay                      |
 +-----------------------------------+--------------------------------------+
                                     v
 +--------------------------------------------------------------------------+
 | NIGHTLY BATCH  deterministic, local CPU, NO LLM                           |
 |   quality gate -> nightly features -> baseline (shrinkage) -> detector    |
 |   -> explained-variance subtraction -> Chronos forecast (advisory)        |
 +-----------------------------------+--------------------------------------+
                                     | deviation flagged?
                    NO --> night log row, stop, cost = 0
                                     | YES
                                     v
 +--------------------------------------------------------------------------+
 | RED-FLAG INTERCEPT   plain code, runs first, always, cannot be bypassed   |
 +-----------------------------------+--------------------------------------+
                                     | clear
                                     v
 +--------------------------------------------------------------------------+
 | EPISODE AGENT   LangGraph, SQLite checkpointer, interrupt() across waits  |
 |                                                                          |
 |   (1) INVESTIGATE   the LLM drives. Free tool use over the T1 read-only   |
 |       +-------+     tools. It decides what to read, in what order, and    |
 |       |       |     when it has enough. The path depends on what it finds |
 |       v       |                                                          |
 |    tool call -+                                                          |
 |       |                                                                  |
 |       v   structured evidence, Pydantic validated                        |
 |                                                                          |
 |   (2) BELIEF        exact update over 12 binary causes. Deterministic     |
 |       |                                                                  |
 |   (3) POLICY        expected value of sample information, net of the      |
 |       |             interruption cost, in numpy.                            |
 |       |             Selects OBSERVE / ASK / MEASURE / ESCALATE / CONCLUDE |
 |       v                                                                  |
 |   (4) ACT           LLM writes the question, runs the interview,          |
 |                     synthesises, critiques. Code validates and sends      |
 +-----------------------------------+--------------------------------------+
                                     v
              notifier (Telegram)  ->  audit log  ->  dashboard
```

Two properties this makes visible. The LLM is never touched on a quiet night, which is what makes
the cost model work. The red-flag intercept sits upstream of the agent, so it cannot be reasoned
past.

### 3.1 Where agency lives

Actions are classified by control tier. **Tier is assigned per action, per data scope and per blast
radius**, not once for the whole product.

| Tier | Definition | In this system | Who decides |
|---|---|---|---|
| **T0** | Text generation only, no subject data, no tools | Not used | - |
| **T1** | Subject-scoped read with provenance. Cannot create or change a record | `get_nightly_features`, `get_personal_baseline`, `get_known_events`, `get_data_quality`, `find_similar_past_episodes`, `retrieve_clinical_evidence`, `get_local_disease_activity` | **The LLM, freely.** It loops, chooses what to read, and decides when it has enough. This is the agentic loop |
| **T2** | Draft or pend. A reversible artefact inside a fixed schema | The drafted question text, the drafted `EpisodeOutcome`, the drafted escalation wording | **The LLM drafts. Deterministic validators check.** Nothing here has reached the human |
| **T3** | Administrative commit, non-clinical | None. The system has no administrative surface | - |
| **T4** | User-facing commit. Reaches the person and cannot be undone | Sending a Telegram message of any kind | **Arithmetic and budget, in code.** The LLM has no tool that performs a T4 action |
| **X** | Open-ended authority: expanding its own scope, acting without bounded permission | **Denied.** No shell, no code execution, no open web, no self-expansion. Attempts are logged and counted | - |

Permission model in the same terms: **READ** is subject-scoped and provenance-carrying; **DRAFT**
and **PEND** are permitted inside fixed schemas; **COMMIT** outside the local database is denied
except through the single gated notifier; **SELF-EXPANSION** is denied outright.

#### What the LLM does

Drives the investigation loop and chooses its own tool calls. Extracts structured facts from messy
free text. **Writes the question text itself**, in context, informed by what it retrieved. Runs the
adaptive interview once the human has opted in by answering, including generating follow-ups that no
authored bank contains. Acts as an additive second-opinion red-flag detector. Synthesises retrieved
evidence into a grounded explanation. Critiques its own draft before anything is shown.

#### What the LLM never does

| Never | Why, with evidence |
|---|---|
| States a probability | Numbers come from the Bayesian network. Stated LLM confidence is systematically overconfident |
| Decides **whether** to interrupt | The project's contribution, and the measured-worse option to delegate. MediQ (arXiv:2406.00922) found prompting frontier models to ask questions *degrades* performance, and an abstention gate recovered **+22.3%** accuracy |
| Decides **what to find out** | The policy selects a `Probe` by expected value of sample information. The LLM then writes the question for that probe. See 3.2 |
| Removes a red flag | It may only add one. Deterministic rules are the floor |
| Sends anything outward | The notifier is not a tool and does not appear in the tool table |

**The asymmetry underneath all five:** the model can always make the system quieter or safer. It can
never make it louder or riskier.

#### Cheap context is pre-loaded, and that is an optimisation not a restriction

Five of the T1 reads are cheap and wanted on essentially every episode, so the graph pre-loads
nightly features, personal baseline, known events, data quality and the episode's own history into
the first investigation prompt. Making the model spend turns fetching them at roughly nine tokens
per second buys nothing and adds ordering nondeterminism to the cassette tests.

**Every T1 tool stays callable at any time**, including re-fetching a pre-loaded one with different
arguments. The judgement that matters is concentrated where it belongs: constructing the retrieval
query from the case, re-querying after learning something, choosing the pattern for
`find_similar_past_episodes`, and deciding when it has enough. See `04-decisions.md` D-121.

#### T1 is free, but free is not risk-free

In an agentic loop the output of one cycle becomes the input to the next, so a wrong read-only
summary propagates into every downstream decision. Every T1 return therefore carries a source
identifier, a timestamp and a freshness verdict, and a stale or conflicting read is surfaced rather
than silently consumed.

#### Containment, given that the control flow is dynamic

`history/PROPOSAL.md` 5.4 commits to **Plan-Then-Execute**, in which the plan is fixed before any untrusted
content is read. **This design does not satisfy that pattern and must not claim to**, because the
LLM chooses its next tool call after reading retrieved documents, so untrusted content does
influence control flow.

What it satisfies instead is the **Action-Selector** pattern, and the containment argument is
different:

1. The action space is a **closed enumerated set**. Injected text can change which read happens
   next; it cannot invent an action that does not exist.
2. There is **no outbound tool**. The lethal trifecta's third leg is structurally absent, so
   influencing control flow buys an attacker nothing they can exfiltrate.
3. Untrusted text is processed only by calls whose sole legal output is a typed Pydantic object.
   Instruction-like text has nowhere to go: it is not in the output schema.
4. Every T4 action is gated by arithmetic the model cannot reach, and by a budget.
5. Tool calls are capped per episode (`MAX_TOOL_CALLS_PER_EPISODE`) and the graph has a hard step
   limit.

`04-decisions.md` B-11 records this correction, and the write-up must describe the pattern
accurately rather than claiming the stronger one.

#### Latency

Not a constraint. The investigation loop runs inside the background nightly batch. The human is
asynchronous by design and is never waiting on a 9.2 token per second endpoint.

### 3.2 Probes and questions: what is fixed and what is free

This split is what lets the model write questions freely without destroying the benchmark.

| | Decided by | Fixed or free |
|---|---|---|
| **Which cause to resolve** (`Probe`) | Value-of-information arithmetic over the belief state | Fixed. Selected from `data/knowledge/probes.yaml` |
| **The answer space** | The probe definition | Fixed. The cited likelihood table `p(answer given cause)` is defined over exactly these slots |
| **The question wording** | The LLM, in context | Free. It may reference what it already knows and relabel options for clarity |
| **Follow-ups inside an open conversation** | The LLM | Free. It may generate questions no bank contains, within the depth budget |

The likelihood table is defined over *what is being asked about*, not over a string. Recall
reliability and physiology do not change because a sentence is phrased differently. That is why the
arithmetic survives free wording.

### 3.3 Model inventory

Four models. **None is trained. None is optional.** Row 0 is listed for completeness and is
deliberately not a model.

| # | Component | Job | Status | Location |
|---|---|---|---|---|
| **0** | Personal statistical baseline and detector | Rolling median and MAD, shrinkage, persistence. **Alone sets `level` and `flagged`** | Not a model. Ordinary statistics, and the thing every other component must beat | `detect/` |
| **1** | **Chronos-Bolt** (Apache-2.0) | Zero-shot forecast of tonight's expected resting heart rate with a prediction interval. Supplies a **second deviation score** as evidence | Pretrained, zero-shot, CPU | `detect/forecast.py` |
| **2** | **Bayesian cause model** (exact enumeration, numpy) | Which of twelve causes are contributing. The reasoning core | Hand-specified structure, literature-elicited priors and effect sizes. No PGM library | `belief/` |
| **3** | **Sentence embedding model** (`bge-small-en-v1.5`) | Dense retrieval over the clinical corpus | Pretrained | `retrieve/` |
| **4** | **LLM** (provider-agnostic) | Investigation, extraction, question writing, interview, synthesis, critique | Pretrained | `llm/` |

**The boundary that must not move:** the deterministic detector alone sets `level` and `flagged`.
Chronos is advisory. If it fails or is unavailable the detector is unaffected and `forecast_status`
records why.

**Why Chronos is expected to matter most in the cold-start regime.** A rolling median and MAD
baseline needs history, and at five nights MAD frequently collapses to zero on quantised data, so
the band has no width. A zero-shot foundation model carries a prior over short physiological series
and yields a calibrated interval from very few points. The hypothesis, which is unpublished and
which the evaluation tests directly on the baseline-age curve, is that Chronos extends usable
detection to earlier nights than statistics can.

### 3.4 Is this a good agent use case?

The standard list of poor fits names **open-ended diagnosis** first. This system is
diagnosis-adjacent, so the objection has to be answered rather than avoided.

| Criterion | This system |
|---|---|
| High volume and repetitive | Once per night, indefinitely |
| Machine-checkable output | `EpisodeOutcome` is schema-validated with a closed disposition set. Success is testable: schema pass, every clinical claim source-linked, `unsupported_claims` counted, disposition matches the frozen scenario's expectation |
| Reversible or transactional | Every artefact is advisory. Nothing is committed to any external system. The worst case of the single T4 action is one unnecessary question against a budget of two per week |
| Bounded scope | Twelve enumerated causes, five enumerated actions, six terminal dispositions, one subject's own data, nightly cadence, hard step and tool-call caps |
| Provenance available | Every T1 return carries source and timestamp. Every clinical claim carries a citation. The audit log is hash-chained |
| Least privilege feasible | Every tool is read-only. The one outbound path is not in the tool space |

**Where it still bites.** The criterion this system scores worst on is **ambiguity**: there is no
reliable ground truth at execution time for what actually caused tonight's deviation. That is why
the output is a ranked differential with explicit uncertainty and a first-class `INSUFFICIENT_DATA`
outcome rather than a verdict, and why the policy is benchmarked against real human self-reports
rather than values we invented.

The claim is not that agents are ready for diagnosis. It is that **bounded differential triage over
an enumerated cause set, with a typed disposition and a deterministic safety floor, is a different
task from open-ended diagnosis** and passes the criteria open-ended diagnosis fails.

### 3.5 Release stage

| Stage | Meaning | This project |
|---|---|---|
| 1. Offline test | Historical cases with known outcomes; measure task completion, unsupported claims, source accuracy, failure recovery | **In scope.** Frozen scenario suite and cohort evaluations |
| 2. Silent mode (shadow) | Read live data, take no action, compare proposals against reality | **In scope.** Every proposed action is logged whether or not it fires |
| 3. Controlled release | Draft or pend enabled in a narrow scope with fixed permissions and stop conditions | **Narrow.** One consenting subject, who is the operator |
| 4. Monitored scale | Expand only after thresholds are met | **Out of scope, stated as such** |

---

## 4. Runtime model

One SQLite database is the single source of truth. Everything else reads or writes it.

| Command | What it does |
|---|---|
| `uv run wha ingest` | Pull from the configured `DataSource`, store raw, normalise |
| `uv run wha nightly [--date D]` | Deterministic batch for one night. Idempotent |
| `uv run wha episode step <id>` | Advance one episode by one step. Used by the scheduler and by tests |
| `uv run wha demo run <scenario>` | Generate a synthetic scenario and run it end to end into its own subject |
| `uv run wha cohort replay --dataset stanford --participant P` | Replay a cohort participant into its own subject |
| `uv run wha eval <suite>` | Run an evaluation suite and write results |
| `uv run wha serve` | Start the dashboard plus a background scheduler thread |
| `uv run wha doctor` | Check every dependency: database, bridge, LLM endpoint, Telegram, datasets. Prints a pass or fail per item |

`wha serve` running is what makes notifications fire when the dashboard is closed. A documented
Windows Task Scheduler entry running `wha nightly` is the alternative.

**Every command is idempotent and takes `--subject`, defaulting to `me`.**

---

## 5. Subjects

Every table carries `subject_id`. The dashboard reads the database and does not know or care where
the data came from. Demo scenarios and cohort replays write to their own subjects
(`demo-illness-onset`, `cohort-P110465`). A subject selector appears in the sidebar **only when more
than one subject exists**, so a normal install shows nothing.

One code path, one interface, no mode branching, and a demo that is real because it runs the real
pipeline. Also required regardless, because cohort evaluation iterates over many participants.

---

## 6. The baseline maturity ladder

Deviation detection needs a personal baseline, and a new subject has none. Published methods require
7 to 28 nights and simply refuse until they have them. This system instead starts from a population
prior over nocturnal resting heart rate and shrinks toward the personal estimate as nights accrue.
Closed-form conjugate updating, nothing trained, every number citable.

What the agent may claim depends on how many usable nights exist:

| Usable nights | Rung | Permitted behaviour |
|---|---|---|
| 0 to 2 | `COLD` | `INSUFFICIENT_DATA` only. Reports coverage. Never opens an episode |
| 3 to 6 | `PRIOR_DOMINATED` | Wide bands. Extreme deviations only. Disposition capped at `INSUFFICIENT_DATA` or `LIKELY_BENIGN`. **May not ASK** |
| 7 to 13 | `SHRINKING` | May open episodes and ask. Confidence discounted. The outcome states its baseline age |
| 14 to 27 | `PERSONAL` | Full behaviour |
| 28 and above | `MATURE` | Full behaviour, matching the published literature standard |

`EpisodeOutcome` carries `baseline_nights` and `baseline_rung`, so the limitation is machine-readable
rather than prose. Thresholds are constants in `docs/CONTRACTS.md` and are swept in the evaluation.

**This produces a result nobody has published:** detection recall and false-alert rate as a function
of baseline age, obtained by truncating each cohort participant's history to N nights.

---

## 7. Phases

Each phase ends with something runnable. The task list is linear and resumable, so phases can run
back to back or stop at a boundary.

| Phase | Contents | Done when |
|---|---|---|
| **A. Offline core** | Storage, ingestion, features, quality gate, baseline ladder, detector, explained-variance subtraction, Chronos forecast, belief model, value-of-information policy, evaluation harness. **No LLM, no LangGraph, no interface** | `uv run wha eval detection` and `uv run wha eval policy` produce real numbers on real cohort data |
| **B. The agent** | LangGraph episode graph, T1 tool table, red-flag intercept, retrieval, LLM client, interview, self-critique, audit log, Telegram notifier | `uv run wha demo run illness-onset` completes an episode end to end against recorded LLM responses |
| **C. Surface** | Streamlit dashboard, five navigation surfaces plus the episode drill-down, live status strip, episode trace, scenario fixtures, README | `uv run wha serve` renders every scenario correctly and the UI test suite is green |
| **D. Optional polish** | FastAPI wrapper over the service layer, Next dashboard | Start only after C is signed off. Never start if C is not green |

---

## 8. Scope

### In

| Feature | `history/PROPOSAL.md` id |
|---|---|
| Automatic continuous ingestion via the Health Connect bridge | F1 |
| Baseline maturity ladder with population-prior shrinkage | **replaces F2** |
| Data-quality gate producing refusal, not a guess | F3 |
| Synthetic generator with injectable confounders and illness signatures | F3b |
| Personal baseline with shrinkage | F4 |
| Deviation detection, NightSignal-style, with persistence | F5 |
| Chronos-Bolt zero-shot forecast supplying a second deviation score | F6 |
| Explained-variance subtraction from recorded exercise | F7 |
| Belief state over twelve candidate causes | F8 |
| Value-of-information policy able to conclude that no question is needed | F9 |
| Adaptive interview, tap-first, delivered over Telegram | F10 |
| Measurement request, redefined as a spot resting heart rate reading | F11 |
| Hybrid retrieval with claim-to-source enforcement | F12 |
| Live local disease activity from NEA dengue clusters | F13 |
| Deterministic claim-to-source enforcement, plus an additive LLM critique | F14 |
| Deterministic red-flag interception, plus an additive LLM detector | F15 |
| Human checkpoint on any drafted conclusion: approve, edit, reject, escalate | F16 |
| Hash-chained audit log | F17 |
| Visible reasoning trace, including skipped stages and why | F18 |
| Detection metrics, policy benchmark, ablations, adversarial suite | 4.7 |
| **Detection versus baseline-age curve** | new |
| **Two-way Telegram notifier** | new |
| **Provider-agnostic LLM client, bring your own model** | new |
| **Grounded follow-up Q&A about a closed episode** | new |

### Out, and why

| Cut | Reason |
|---|---|
| Counterfactual projection (F19) | No evaluable ground truth. Decorative |
| Second device vendor (F20) | Nothing to test against. Portability is claimed from the Health Connect architecture instead |
| Orthostatic sit-to-stand test | Heart rate arrives in 1-minute buckets; an orthostatic response peaks in 15 to 30 seconds. The granularity does not support it |
| Samsung Health export backfill | Ruled out. Replaced by the baseline ladder |
| Any trained model | `04-decisions.md` D-002 |
| Cross-encoder reranker, MOMENT, TTM, GraphRAG, multi-agent | `history/PROPOSAL.md` 4.5.2.1. Unchanged |
| Open web search as an agent tool | Completes the lethal trifecta and produces claims that cannot be cited. Live data comes from named authoritative endpoints only |
| Intraday monitoring, any real-time claim | The decision cadence is nightly. `04-decisions.md` B-10 |

**Note on the LLM provider.** Not a cut. **Every test runs against cassettes**, forced by an autouse
fixture. Development and any human-run command use the OpenAI-compatible endpoint configured in
`.env`. Any OpenAI-compatible provider works, and `ollama_native` remains supported for a local
model. See D-112.

---

## 9. Repository layout

```
src/wha/
  __init__.py
  constants.py         every threshold and budget. Single source of truth
  models.py            every Pydantic domain and view model
  errors.py            the error taxonomy
  config.py            settings and env loading. No secrets in code
  db/                  schema.sql, migrations, connection handling, hash chain
  ingest/              DataSource protocol; live_bridge, synthetic, cohort
  features/            nightly feature derivation, quality gate
  detect/              baseline ladder, detector, explained variance, forecast
  belief/              cause priors, effect model, exact enumeration, evidence
  policy/              expected value of sample information, utilities, budgets
  agent/               LangGraph graph, nodes, state, tool registry
  safety/              red-flag rules, output checks, injection detection, outbound validation
  retrieve/            corpus loading, chunking, BM25, dense, fusion, grounding
  llm/                 provider clients, prompts, cassettes
  notify/              Notifier protocol, Telegram implementation
  audit/               audit event writing and querying
  service/             UI-agnostic entry points. All business logic
  ui/                  Streamlit pages and components. No business logic
  eval/                evaluation suites
  cli.py               the wha command

data/knowledge/        AUTHORED, READ ONLY: causes, probes, CPTs, red flags, corpus manifest
data/                  gitignored: wha.sqlite, datasets, corpus cache
tests/                 unit, integration, scenario, ui
tests/fixtures/        scenario definitions, LLM cassettes, sample payloads
plan/                  this folder
AGENTS.md              always-in-context rules for the coding agent
.agents/rules/         additional rules, each under 12,000 characters
```

---

## 10. Canonical component list

Component numbers are fixed. Tasks reference them by number and they are never renumbered.

| # | File | Covers |
|---|---|---|
| 01 | `components/01-data-ingestion.md` | `DataSource` protocol, live bridge, synthetic, cohort replay |
| 02 | `components/02-storage.md` | Schema application, migrations, connections, hash chain |
| 03 | `components/03-features-and-quality.md` | Nightly feature derivation, coverage, plausibility, refusal |
| 04 | `components/04-baseline-and-ladder.md` | Population prior, shrinkage, rungs, permitted-claim gating |
| 05 | `components/05-detection.md` | Levels, persistence, alert events, explained-variance subtraction |
| 06 | `components/06-forecast-chronos.md` | Zero-shot forecast band, second deviation score, cold-start comparison |
| 07 | `components/07-belief-model.md` | Cause priors, additive effect model, temporal profiles, exact enumeration |
| 08 | `components/08-policy.md` | Expected value of sample information, decision utilities, budgets, action selection |
| 09 | `components/09-agent-graph.md` | LangGraph nodes, edges, state, checkpointing, interrupts, timeouts |
| 10 | `components/10-tools.md` | T1 tool table, argument validation, provenance, freshness |
| 11 | `components/11-safety.md` | Red-flag rules, LLM second opinion, injection detection, outbound validation |
| 12 | `components/12-retrieval.md` | Corpus, chunking, BM25, dense, fusion, claim-to-source enforcement |
| 13 | `components/13-llm-client.md` | Provider clients, cassettes, structured output, repair, unavailability |
| 14 | `components/14-service-layer.md` | Every UI-agnostic entry point |
| 15 | `components/15-ui-and-interaction.md` | Telegram notifier and the Streamlit dashboard |
| 16 | `components/16-evaluation.md` | Detection metrics, baseline-age curve, policy benchmark, ablations, adversarial suite |
| 17 | `components/17-cli-and-runtime.md` | The `wha` command, scheduler, idempotency, Task Scheduler setup |

---

## 11. How to use this folder

1. Read `AGENTS.md` at the repository root. It is always in context and holds the hard rules.
   The detailed rules it points to live in `.agents/rules/`.
2. Read `docs/CONTRACTS.md` in full. Every task depends on it. Never contradict it.
3. Open `history/plan/PROGRESS.md`, find the first incomplete task, and open only that task file.
4. Read the component document that task names, and nothing else.
5. Do the task. Run its exit command. Update `PROGRESS.md`.
6. If blocked, write to `plan/BLOCKERS.md` and move to the next independent task.
   **Never weaken or delete a test to make it pass.**

`plan/03-conventions.md` does not exist. Conventions live in `.agents/rules/30-python-conventions.md`
so that there is one home for them and no drift between two documents.
