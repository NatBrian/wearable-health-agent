# Wearable Health Agent (WHA)

> **Agentic early-warning, physiological anomaly detection, and causal attribution for
> consumer wearable data.**

Your smartwatch can tell that something changed. It cannot tell you what changed it.

Consumer smartwatches detect that something in your body changed: a raised overnight resting
heart rate (RHR), reduced HRV, or fragmented sleep. **However, wrist sensors cannot tell you
why.** A resting heart rate 3.5 bpm above your own normal might mean an infection is
incubating. It might equally mean you drank wine with dinner, trained hard at 9pm, slept
badly, had a stressful day, were vaccinated on Tuesday, or are in the luteal phase of your
menstrual cycle. **To an optical sensor on the wrist these look nearly identical, and they
demand opposite responses.**

**WHA decouples continuous passive monitoring from episodic agentic investigation.** A cheap,
boring, always-on monitor watches your nights using ordinary statistics and no AI at all.
Only when it sees something worth explaining does a bounded AI agent wake up, gather
evidence, weigh the possible causes, and decide whether asking you a question is worth
interrupting you for.

---

## What this is not

**This has never been tested on a patient.** There is no clinical trial behind it, no peer
review and no validation against any medical outcome. Nobody has been warned by it, treated
because of it, or helped by it. It is a two week student project.

**How well it detects illness in real use is not known.** Where you see a number in this
repository it is either from a published source with its citation beside it, or an operating
parameter of the code. Anything this project measured about itself lives in
[`experiments/`](experiments/README.md) behind a disclaimer, and is not evidence that any of
this works.

It is not a medical device and it does not diagnose. See [DISCLAIMER.md](DISCLAIMER.md).

---

## Current state, as of 8 September 2026

**The build is finished, and the repository is now open to more than one person.** There is
still no task queue: nothing here is waiting to be picked up, and if you are asked to
"continue" with no further detail, **ask what is wanted**. `archive/` is full of documents
that look like plans and every one of them describes work that has ended.

- The whole suite passes, `ruff` is clean on `src` and `tests`, `wha doctor` reports no
  failures.
- The dashboard has five screens and was driven end to end through a seventeen day illness.
- A complete demo timeline is committed and can be opened in one command, below.
- A 28 minute walkthrough film of the whole system is in [`docs/demo/`](docs/demo/README.md).

**What changed on 8 September.** The boundaries several people would work across at the same
time were made real rather than assumed: the agent's eight nodes are one file each, the agent
declares its own step names in one place instead of having them copied into four, retrieval
sits behind a protocol, and the dependencies between packages are checked by a test. Nothing
the system does changed. See **Working on this at the same time as somebody else** below
before starting, and
`archive/session-logs-2026-09/superpowers/plans/2026-09-08-modularity-handover.md` for why
each one was done.

---

## Setting it up from a clean checkout

```bash
uv sync                                   # install. ALWAYS uv, never bare python
cp .env.example .env                      # then fill in the values it lists
uv run wha data fetch corpus              # REQUIRED. ~32 MB, see below
uv run wha doctor                         # should report no `fail` rows
```

**The corpus fetch is not optional.** `data/corpus/` holds the MedlinePlus passages the
agent is allowed to quote, plus their embeddings. It is about 32 MB, it is deliberately not
committed, and **retrieval cannot run without it**. Which release is in use, and its
SHA-256, are recorded in `data/knowledge/corpus-sources.json`.

Nothing else needs downloading to run the system. The cohort dataset under `data/cohort/` is
only needed to re-run the detection experiment, and `wha doctor` will report it as `miss`
without it, which is expected and harmless.

### Look at a working system immediately

```bash
uv run python tools/demo_film/serve_demo.py     # then http://localhost:8501
```

This opens a committed seventeen day timeline: quiet nights, an illness, a relapse, a
recovery, three linked investigations, every question asked and answered, an escalation, and
the audit trail behind all of it. It shifts the clock so the newest night reads as "last
night" however long from now you run it, serves a copy so browsing cannot alter the
committed timeline, and runs without the scheduler so nothing moves while you look.

**It is the fastest way to understand what this system does.** Use it before reading the
architecture.

---

## The repository, folder by folder

| Path | What it is | Status |
|---|---|---|
| `src/wha/` | **The system.** All of it | **Live** |
| `tests/` | The suite. You may add, never weaken | **Live** |
| `data/knowledge/` | The clinical tables: causes, probes, red flags, triage rules. Every number carries its own provenance | **Live, under change control.** See rule 4 in `AGENTS.md` |
| `docs/` | The design documents, contracts and disclosures | **Live** |
| `tools/` | The mock watch, the retrieval check, and `demo_film/` which built the demo and the film | **Live** |
| `experiments/` | **Our own experiments, and NOT evidence of anything.** Detection re-analysis, a self-scored policy simulation, a retrieval comparison, a deleted forecaster. Every folder carries a disclaimer | **Live, but read the disclaimer first** |
| `data/corpus/` | Fetched MedlinePlus text and embeddings. Not authored here, not committed | Fetch only |
| `archive/` | **Finished work. Describes nothing about the present.** Old plans, the build log, the September review, and this project's own session logs | **Read-only.** Never a queue |

### The documents, and which of them you must write to

Three documents are **obligations**, not reference reading. You do not need to read them
cover to cover, but if you do the matching thing you must add to them, and a test will fail
if you do not.

| Document | You must write to it when |
|---|---|
| `docs/KNOWLEDGE-CHANGELOG.md` | You change any clinical figure in `data/knowledge/` or `constants.py` |
| `docs/DISCLOSURES.md` | You add or discover a limitation. Every one names the screen that shows it |
| `docs/CONTRACTS.md` | You change a schema, model, constant or service signature. **Four tests compare it against the code on every run**: its models, its schema, its constant values and its dependency table |

The rest are reference:

| Document | What it answers |
|---|---|
| [AGENTS.md](AGENTS.md) | **The rules.** Read this before writing any code |
| [docs/CODE-CONVENTIONS.md](docs/CODE-CONVENTIONS.md) | Type hints, naming, module boundaries |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | The whole system in 19 parts. Routed by part below, do not read it cold |
| [docs/RESEARCH-AGENTIC-TRIAGE.md](docs/RESEARCH-AGENTIC-TRIAGE.md) | Every clinical citation, with what it studied and what it justifies |
| [USER-GUIDE.md](USER-GUIDE.md) | The product, for the person whose health it is |
| [docs/demo/README.md](docs/demo/README.md) | The demo timeline and the film |
| [experiments/README.md](experiments/README.md) | What we measured ourselves, and why it is not evidence |
| [docs/RUNBOOK-SIMULATION.md](docs/RUNBOOK-SIMULATION.md) | Running a simulated timeline with the mock watch |
| [docs/CORPUS-VERIFICATION.md](docs/CORPUS-VERIFICATION.md) | Every corpus figure checked against its paper |
| `docs/DESIGN-*.md` | Four decisions argued at length: the sleep window, the baseline centre, the symptom timeline, which data channels are used |

---

## I want to do X. What do I read?

| Goal | Read, in this order |
|---|---|
| **Understand what it does** | Run `serve_demo.py` above and click through it. Then this file's architecture section |
| **Fix a bug** | `AGENTS.md`, then the relevant `ARCHITECTURE.md` part below. **Reproduce it in the running dashboard first**, because a green suite proves very little here |
| **Add a feature** | `AGENTS.md`, `docs/CODE-CONVENTIONS.md`, `docs/CONTRACTS.md` for the boundary you are touching |
| **Change a clinical number** | `AGENTS.md` rule 4, then `docs/KNOWLEDGE-CHANGELOG.md` for the format. You need a quotable source or a committed measurement |
| **Change what the screen says** | `src/wha/ui/explain.py` holds the copy. UI copy may contain no digits, and the dashboard may not import from `wha.service`. Tests enforce both |
| **Add or change a safety rule** | `data/knowledge/red_flags.yaml`, `src/wha/safety/`, and `ARCHITECTURE.md` Part 12. The floor may only ever raise urgency |
| **Work on the agent's reasoning** | `ARCHITECTURE.md` Parts 8 to 11, and `src/wha/agent/` |
| **Work on retrieval or grounding** | `ARCHITECTURE.md` Parts 13 and 14, and `src/wha/retrieve/` |
| **Re-cut or re-record the film** | `docs/demo/README.md` |
| **Understand why a past decision was made** | `archive/session-logs-2026-09/superpowers/` holds the specs and plans, each explaining the reasoning at the time |

### Where in ARCHITECTURE.md

It is 19 parts and about 85 KB. Read the part you need, not the file.

| Part | Subject |
|---|---|
| 1 to 2 | Getting data off the watch, and storage |
| 3 to 4 | The sleep window, and turning a night into one number |
| 5 to 6 | The personal baseline, and deciding a night is worth looking at |
| 7 | The forecaster that was removed, and why |
| 8 | The Bayesian belief over twelve causes |
| 9 | The EVSI policy: deciding whether to interrupt somebody |
| 10 to 11 | The agent graph, and its tools |
| 12 | **The deterministic safety floor** |
| 13 to 14 | Retrieval, the corpus, and grounding |
| 15 | The conversation |
| 16 to 17 | The HTTP boundary, the dashboard, and Telegram |
| 18 to 19 | The audit trail, and what is actually known about accuracy |

---

## Local files a clone will not have

Two large files live only on the machine this was built on, and **neither is needed to run
the system**.

| Path | Size | What it is | Safe to delete? |
|---|---|---|---|
| `data/wha.sqlite` | 213 MB | **The owner's real watch data.** Subject `me` | **NO. Never delete or overwrite this** |
| `data/corpus/` | 32 MB | Fetched MedlinePlus text and its embeddings | Yes, but retrieval stops working until you re-run the fetch above |

About 3.6 GB of build leftovers were removed on 7 September 2026: database backups, a
scratch directory, the cohort dataset, the demo snapshots and two superseded databases.
None was tracked by git, so a clone was never going to have them. The cohort comes back with
`uv run python experiments/detection/cohort/fetch.py` if you want to re-run the detection
experiment.

| `data/demo_film.sqlite` | 22 MB | The finished demo timeline | **No,** and it is committed. Not reproducible: rebuilding costs model calls and produces different wording |

---

## The shape of the system

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ DAILY PASSIVE MONITOR (Tier 0)                                                  │
│ Local CPU • Plain Python • Closed-Form Statistics • Zero LLM Calls • $0 Cost    │
│ Recorded-Sleep Extraction ──> Coverage Gate ──> Shrinkage Baseline ──> Test    │
└──────────────────────────────────────┬──────────────────────────────────────────┘
                                       │
                      ┌────────────────┴────────────────┐
                      ▼ Quiet Night                     ▼ Anomaly Flagged
               Write Log Row ($0)             ┌───────────────────────────────────┐
                                              │ DETERMINISTIC RED-FLAG FLOOR      │
                                              │ Hard-coded emergency triage rules │
                                              └───────────────┬───────────────────┘
                                                              │
                                            ┌─────────────────┴─────────────────┐
                                            ▼ Emergency Crossed                 ▼ Clear
                                      ESCALATE to Care             ┌─────────────────────────┐
                                                                   │ BOUNDED AGENT (Tier 1)  │
                                                                   │ Exact 4,096-State Bayes │
                                                                   │ EVSI Interruption Math  │
                                                                   │ LLM Clinical Dialogue   │
                                                                   └────────────┬────────────┘
                                                                                │
                                                                                ▼
                                                                   ┌─────────────────────────┐
                                                                   │ DELIVERY (Tier 2)       │
                                                                   │ Telegram Inline Buttons │
                                                                   │ Streamlit Web Dashboard │
                                                                   │ SHA-256 Audit Trail     │
                                                                   └─────────────────────────┘
```

> **Project status:** see the current state near the top of this file for what works, and
> what still needs a human decision.

---

## The short version of the architecture

The full account is **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**. This is the same
system in one page.

Every night runs through **21 numbered steps**, and the dashboard's "The record" screen draws
all 21 for every night, coloured by which part of the system ran them. They fall into five
groups.

### 1. Get the data, and turn the night into one number (steps 1 to 4)

Your watch writes to Samsung Health, which writes to Android Health Connect. A small bridge
app on your phone serves that over local HTTP. WHA pulls it, stores the raw payload
untouched, then:

- **Finds the sleep the watch actually recorded**, rather than assuming midnight to 7am.
  Waking spells inside the night are cut out. If the watch recorded no sleep, it falls back
  to a clock window and the night says so.
- **Checks there is enough data.** At least 180 minutes of contact, or the night is marked
  unusable rather than guessed at. Implausible readings are dropped as sensor error.
- **Takes the median heart rate** over that window. The median, not the mean, so one bad
  stretch cannot drag it.

### 2. Compare it against your own normal (steps 5 to 7)

Your baseline is the median of your recent nights, with the band around it scaled by how much
*you* vary from night to night. Until it knows you, it leans on a population figure and says
so on screen. Anything a recorded workout explains is subtracted first.

Then the night is judged: **GREEN**, **YELLOW** at +3 bpm, **RED** at +4 bpm. An
investigation opens only on **two consecutive RED nights**. Yellow-then-red does not open
one, and a run of yellow nights never does. That is the published NightSignal rule; the
looser version was measured and rejected (see [design decisions](#the-design-decisions-and-why)).

### 3. The safety floor (step 8, and steps 20 to 21)

Plain rules, no AI, that can only ever *raise* urgency and never lower it. They run on two
different things: **what you typed**, matched against fixed phrase lists in
`data/knowledge/red_flags.yaml` and read **over time** rather than one message at a time; and
**what your readings show**, an extreme heart rate against your own range plus overnight
blood oxygen where the device records it.

| Tier | Rule | Example |
|---|---|---|
| **A** | One is enough. Urgent, now. | Chest pain, fainting, coughing blood |
| **B** | Two together, **or one that persists** past its own number of nights | Fever, vomiting, cannot keep fluids down |
| **Tracked** | Recorded and asked about; escalates on nothing | Dizziness |
| **C** | A language model reads the same text and may **add** a flag | Catches wording the phrase lists miss |

### 4. The agent (steps 9 to 19)

Only runs once a night is flagged. It is a LangGraph loop with hard limits on steps and tool
calls, and it does five things in order:

1. **Preload.** A fixed set of readings, so every investigation starts from the same facts.
2. **Investigate.** The model picks tools from a closed list and calls them. It cannot reach
   anything not on that list, and every call is recorded.
3. **Believe.** An exact Bayesian update over 12 possible causes and all 2¹² = 4,096
   combinations of them being present or absent, in log-space. Ordinary arithmetic; the same
   evidence always gives the same answer.
4. **Decide.** Whether to ask you, keep watching, or conclude. **This is arithmetic, not the
   model.**
5. **Conclude.** Draft an outcome, strip any sentence that cannot quote a real source, and
   record it.

### 5. Delivery

Telegram with one-tap buttons, the Streamlit dashboard, and a SHA-256 hash-chained audit log
that makes tampering detectable.

---

## The design decisions, and why

These are the choices a new maintainer is most likely to want to change, with the reasons they
are the way they are. Several were settled by **measurement**; re-arguing those from theory
wastes time.

### Why the monitor uses no AI at all

An ordinary night must cost nothing and must work when the internet does not. The detector is
closed-form statistics on local CPU. If every model provider went down tonight, your raised
heart rate would still be flagged and you would still be told.

### Why questions are decided by arithmetic, not by the model

The model does not get to decide to interrupt you. A policy computes the **Expected Value of
Sample Information**, how much an answer would change what the system concludes, and
compares it against a fixed cost of interrupting you. It asks only when the first is larger.
This is what stops an eager assistant messaging you every morning.

**One deliberate exception.** EVSI measures how much an answer moves the belief across the
twelve *causes*. Once a cause is settled, asking again is worth nothing by construction,
meaning **the more confident the system became that you were ill, the less reason it had to
speak to you.** That is the arithmetic working correctly and being the wrong tool for the job.
So a separate **rule** forces a follow-up when you have reported a symptom and never said it
settled. A rule rather than a number, because putting "worse than yesterday" into the belief
table would mean inventing likelihoods no study supplies. Full reasoning:
**[docs/DESIGN-SYMPTOM-TIMELINE.md](docs/DESIGN-SYMPTOM-TIMELINE.md)**.

### Why a normal heart rate does not close an investigation

If you have told the system about a symptom and not said it has gone, a run of green nights
will **not** close your investigation as "probably nothing". Three findings say that inference
does not hold:

- **In dengue the dangerous phase begins as the fever breaks.** WHO and CDC both teach that
  patients may appear to improve at exactly the wrong moment.
- **Faget's sign:** heart rate can be normal or slow *during* an active infection, in typhoid,
  dengue, Legionella and Q fever.
- **Real recovery is slow.** Resting heart rate takes an average of **79 days** to return to
  baseline after COVID, against 24 days for sleep.

A green run is good evidence about the **reading** and close to none about the **person**.

### Why symptoms are read over time

Because for the life of this project they were not, and it was a real hole. `red_flags.yaml`
documented Tier B as "two or more together, **or one that persists**", and the persistence
half had never once fired: the function accepted a symptom history that no caller ever passed.
Five nights of a worsening fever produced five refusals to escalate. "Two or more together"
separately meant "in the same sentence", so a fever on Monday and vomiting on Tuesday counted
as two unrelated singletons. **No threshold changed; they simply began to be read.**

### Why dizziness is "tracked" rather than a red flag

It had no good home. Putting it in a tier asserts a routing threshold no source supports.
Leaving it out means somebody can report it, have it worsen for three nights, and be met with
silence. **Tracking asserts nothing clinical**, it says only "you told us, so we will
remember and ask", which is exactly why it is defensible where an invented number is not.

### Why the system knows nothing about specific illnesses

Decided deliberately, on 7 September 2026, after a live test. The agent can say that a group of
symptoms is worth seeing somebody about; it cannot say which illness they point to, or warn you
how that illness usually behaves. The corpus carries general health information only. **The
accepted cost is written down:** for a WHO dengue warning-sign presentation, the same-day
routing may be under-triaged. Disclosed on the Today screen.

### Why symptom phrases are matched exactly

Also a deliberate decision. The phrase lists stay literal and the Tier C model is the backstop.
Measured before deciding: Tier C caught "I cannot keep any water down", which the lists miss,
and escalated it correctly. A Tier C finding is now also written to the symptom timeline, so it
persists instead of counting once and being forgotten.

### Engineering questions that were tried and settled

**These were settled by our own experiments, not by evidence about anybody's health.** The
runs, and what each is and is not worth, are in [`experiments/`](experiments/README.md).
The answers are recorded here so they are not re-argued from theory; the numbers behind
them are not, because they are not the kind of number that belongs in a summary.

| Question | What was decided |
|---|---|
| Should a long run of **yellow** nights open an investigation? | **No.** Adding that rule found nothing extra on the archive we tried it on, and would have interrupted people more often. |
| Should flagging need one RED night or two? | **Two.** One night is common and has many ordinary causes. The looser rule found slightly more of the illnesses in that archive at the cost of considerably more investigations into people who were never ill. |
| Personal thresholds (`robust_z`) or absolute bpm? | **Absolute.** Personal thresholds were no better at any matched alert rate. |
| Would a neural forecaster help? | **No.** It separated illness less well than plain arithmetic, so it was deleted. |
| Would a reranker improve retrieval? | **No.** Several configurations were tried; none beat plain hybrid retrieval on this corpus. |
| Within-person or between-person spread for the band? | **Within-person.** Using the spread between different people to judge one person's night is a category error, whatever the numbers say. |

---

## What data it uses, and why not more

Health Connect defines around sixty kinds of health data. This system uses the seven a
Galaxy Watch 5 actually provides, and four of those can change a conclusion. Nothing is
filtered out, and the full raw payload is retained regardless.

Supporting the rest is not planned. Most of it has no bearing on illness, and the three
channels that would help (heart rate variability, respiratory rate, skin temperature) are
not recorded by this device, cannot be computed from one-minute heart rate averages, and
would not solve the problem the system exists for: they move in the same direction for
infection, stress, poor sleep and the luteal phase alike.

The reasoning, the measurements behind it and the sources are in
**[docs/DESIGN-DATA-CHANNELS.md](docs/DESIGN-DATA-CHANNELS.md)**. Run
`uv run wha data capability` to see what your own device provides.

---

## Key Clinical & Architectural Invariants

These are the properties that must survive any change. Break one and you have changed what the
system *is*.

1. **Zero-LLM Passive Monitoring**: Nights are scored on a repeating interval rather than at a fixed hour, over **the sleep the watch actually recorded**, falling back to 00:00-07:00 only when it recorded none. A cron at 09:00 assumed the person was awake and synced by then; the first real subject wakes around 11:00, so their night was scored before it had finished being recorded. Robust statistics throughout: MAD scaling, empirical Bayes shrinkage toward a population centre of 62.75 bpm (Bloomfield et al. 2024) with a **within-person** night-to-night scale, and explained-variance subtraction. The between-person SD of 8.64 from the same source is deliberately NOT used for the band, because the spread between different people is the wrong yardstick for one person's night; see `docs/DESIGN-BASELINE-CENTRE.md`. On normal nights, **execution cost is zero and no language model is invoked**.
2. **Deterministic Emergency Safety Floor**: Phrase matching against `data/knowledge/red_flags.yaml` runs on the person's own words **before any model sees them**, and an LLM may only ever ADD a flag, never remove one. Two honest qualifications, because an earlier version of this line overstated both halves. **It does not always escalate immediately:** chest pain maps to a validated decision rule (Marburg Heart Score), so it opens that rule's questions instead of escalating on a phrase, which is the argument of Downie et al. 2013 about single red flags. Presentations with no validated history-only rule, and the unconditional gates such as collapse or crushing pain, do escalate on the spot. **And it does not bypass generative models:** tier C is an additive LLM check that runs on every free-text message. What no model can do is lower the urgency the fixed rules set.
3. **Symptoms Are Read Over Time**: A symptom is a thing with a duration, not a keyword in one message. `symptom_observations` holds one row per symptom per night, and a run ends when the person says it has gone or after seven days of silence. It does **not** end because they went quiet for one night, and it does **not** end because their heart rate settled. Both halves of Tier B, persistence and co-occurrence, are evaluated against it.
4. **Exact 12-Cause Bayesian Belief Engine**: Evaluates joint probabilities over all $2^{12} = 4,096$ discrete causal combinations in log-space, using peer-reviewed effect sizes and temporal onset/decay curves.
5. **Arithmetic Value-of-Information Policy**: Decides whether to stay silent (`OBSERVE`), ask a targeted symptom question (`ASK`), or draft a differential (`CONCLUDE`) strictly via **Expected Value of Sample Information (EVSI) minus Interruption Cost**. The LLM cannot decide to interrupt or spam the patient on its own. **One deliberate override exists:** an outstanding symptom forces a follow-up regardless of EVSI, because EVSI cannot see somebody deteriorating. It may not bypass a pending question or its per-episode cap; it may bypass the weekly interruption budget, because a budget exists to stop the system pestering a *well* person and must not be able to gag somebody who has said they feel unwell. The spot-check limb (`MEASURE`) was deleted on 5 September 2026: it rested on three numbers with no source and asked the noisier instrument to adjudicate the less noisy one.
6. **Fail-Closed Data Quality Gates**: Requires $\ge 180\text{ minutes}$ (3 hours) of nocturnal sensor coverage and refuses biometrics older than 72 hours. The system never fabricates heart rates or invents missing data.
7. **Strict Outbound Safety & Grounding**: Outbound messages pass 6 deterministic checks (length, control characters, URL whitelisting, slot matching, callback sizes). All clinical assertions are strictly grounded against cited medical literature in `data/knowledge/`.
8. **Tamper-Evident Audit Chain**: Every tool call, Bayesian update, human interaction, and LLM reasoning step is logged with **SHA-256 cryptographic hash chaining** into SQLite for tamper-evident clinical auditability.

---

## Failure-Mode Philosophy & Fault Tolerance

**An auxiliary model outage must never block a health alert.** That is the principle the
degradation paths below are built on. It is not a compliance claim: this project has not been
assessed against IEC 62304, ISO 14971 or any other standard, and is not a medical device. See
[DISCLAIMER.md](DISCLAIMER.md).

```
┌────────────────────────────────────────────────────────────────────────┐
│ SUBSYSTEM FAILURE SCENARIOS & RECOVERY PATHS                           │
├──────────────────────────┬──────────────────────┬──────────────────────┤
│ Component Failure        │ System Behavior      │ User & UI Visibility │
├──────────────────────────┼──────────────────────┼──────────────────────┤
│ Retrieval index         │ Grounding strips the │ Reply shows the      │
│ (embedding model absent) │ ungrounded sentence; │ amber uncited block; │
│                          │ BM25 alone continues.│ Evidence tab is thin.│
├──────────────────────────┼──────────────────────┼──────────────────────┤
│ Live LLM API             │ Safety filter trips; │ Conversation badge   │
│ (Malformed/Bad Syntax)   │ substitutes clinical │ shows 'Source:       │
│                          │ fallback template.   │ FALLBACK'.           │
├──────────────────────────┼──────────────────────┼──────────────────────┤
│ Total LLM API Outage     │ Checkpoints state;   │ Status strip turns   │
│ (503 / Network Cut)      │ parks episode in DB; │ red; trace tab logs  │
│                          │ never guesses claims │ 'status = parked'.   │
├──────────────────────────┼──────────────────────┼──────────────────────┤
│ Phone Bridge             │ Rejects stale data;  │ Status strip warns   │
│ (Phone Unreachable)      │ refuses to synthesize│ 'Watch: Connection   │
│                          │ fake heart rates.    │ Error (:8787)'.      │
└──────────────────────────┴──────────────────────┴──────────────────────┘
```

* **Why we do NOT halt the pipeline indefinitely**: If a patient develops an acute infection, an auxiliary LLM or PyTorch failure must never prevent their resting heart rate anomaly from being flagged. The deterministic statistical detector and clinical fallback questions deliver immediate alerts regardless of cloud uptime.
* **Full Transparency**: Every fallback, skipped stage, stripped claim, and tool call is recorded in the **Episode Trace tab** and the cryptographic **audit journal**, both on the **The record** screen. There is no separate Audit page; it was folded into The record during the 6 September dashboard overhaul.

---

## Production Hardware & Subsystem Integrations

WHA connects live wearable sensors, language models, and mobile notifications:

```mermaid
flowchart LR
    subgraph Hardware["Wearable & Phone Bridge"]
        Watch["Samsung Galaxy Watch"] --> SH["Samsung Health"]
        SH --> HC["Health Connect"]
        HC --> Bridge["Health Connect Webhook App (:8787)"]
    end

    subgraph Core["WHA Core Engine"]
        Bridge --> Ingest["Ingestion & Raw Store"]
        Ingest --> Stats["Baseline & Variance Engine"]
        Stats --> Bayes["4,096-State Bayesian Engine"]
        Stats --> Safety["Deterministic Safety Floor"]
        Bayes --> LLM["Live LLM Reasoning Engine"]
    end

    subgraph Delivery["User Interaction Channels"]
        LLM --> TG["Telegram Bot (Inline Buttons)"]
        LLM --> UI["Streamlit Dashboard (Port 8501)"]
        Stats --> DB[("SQLite DB + Audit Chain")]
    end
```

* **⌚ Phone Bridge (Health Connect Webhook)**: Ingests raw heart rate samples, step counts, and sleep stages directly from Android Health Connect over local HTTP (`:8787`) with Bearer token authentication.
* **🤖 Live LLM Inference API**: Compatible with OpenAI, DeepSeek (`deepseek-chat`, `gpt-4o`, `gpt-4.1-mini`), Ollama, OpenRouter, or offline recorded cassettes with automatic Pydantic v2 JSON repair.
* **💬 Telegram Companion Bot**: Pushes instant anomaly alerts and interactive symptom questionnaires with 1-tap clickable inline keyboard buttons directly to your mobile phone.
* **📐 Hybrid Retrieval (BM25 + `BAAI/bge-small-en-v1.5` + Reciprocal Rank Fusion)**: Every clinical sentence the agent produces must **quote a span that is verbatim in a retrieved passage**, or it is stripped or labelled on screen. That check is decidable by code and deliberately narrow: it proves the quoted span exists, not that the sentence around it says what the source says. A neural forecaster was tried here and removed, because it separated illness less well than the plain baseline residual on our own data. See [`experiments/forecasting/`](experiments/forecasting/README.md).

---

## Configuring and running it

**The setup steps are [above](#setting-it-up-from-a-clean-checkout), and that is the only
place they live.** This section is the reference for what goes in `.env`, what `wha doctor`
prints, and what the server does once it is up. It used to repeat the setup and left out the
corpus fetch, so somebody following it got a system whose retrieval could not run.

### The environment file (`.env`)

Create or edit `.env` in the repository root:

```dotenv
# --- Storage ---
WHA_DB_PATH=data/wha.sqlite
WHA_SUBJECT=me
WHA_TIMEZONE=Asia/Singapore

# --- Live LLM Inference Provider ---
WHA_LLM_PROVIDER=openai_compatible
WHA_LLM_BASE_URL=https://openrouter.ai/api/v1     # or https://api.openai.com/v1
WHA_LLM_MODEL=deepseek-chat                      # or gpt-4o, gpt-4.1-mini
WHA_LLM_API_KEY=sk-your-api-key-here

# --- Health Connect Phone Bridge ---
WHA_BRIDGE_URL=http://192.168.1.42:8787          # your phone's address on your own network
WHA_BRIDGE_TOKEN=your-phone-bridge-bearer-token

# --- Telegram Mobile Notifications ---
WHA_NOTIFY_CHANNEL=telegram
WHA_TELEGRAM_BOT_TOKEN=123456789:ABCDefghIJKlmnoPQRstuvw
WHA_TELEGRAM_CHAT_ID=your-telegram-chat-id
```

### Diagnostics (`wha doctor`)

WHA provides two diagnostic modes:

```bash
# Fast offline configuration & file audit
uv run wha doctor

# Real-time active hardware, LLM, and Telegram network probe
uv run wha doctor --live
```

**What it prints**, copied from a real run on 7 September 2026:
```text
clock           ok     today is 2026-09-07
database        ok     data\wha.sqlite, schema v9, 72 nights, 2 subjects
knowledge       ok     causes.yaml 12 rows, probes.yaml 8 rows
bridge          ok     configured at http://127.0.0.1:8788 (auth token configured: True)
llm             ok     provider=openai_compatible, model=deepseek-chat (key configured: True)
telegram        ok     chat id and token configured
cohort          miss   not fetched. This is only needed to re-run the detection experiment,
                       whose results and their limits are in experiments/detection/.
baseline        info   subject 'sim': 38 usable nights, rung MATURE
```

`cohort miss` is the expected state; nothing in the running system uses that dataset. The
`clock` row is the one to read before you trust any date on screen: it says `today is` and
then a date, and if that date is not today, `WHA_CLOCK_OFFSET_DAYS` is set and you are
looking at the demo timeline rather than at now.

Any row can read `fail`, and `wha doctor` exits non-zero if one does. `--live` additionally
opens the bridge, the model provider and the Telegram bot, and reports the round trip in ms.

### The dashboard and the background scheduler

```bash
uv run wha serve --port 8501
```

Access the dashboard at `http://localhost:8501`. The server runs the 24/7 background scheduler:
* **Every 30 mins**: Ingests new wearable samples from the phone bridge.
* **On a repeating interval, not a fixed hour**: Derives overnight baseline features, executes anomaly detection, and opens an episode if a night is flagged. A night settles as soon as its sleep syncs, whatever time that is.
* **Every 15 mins**: Ticks interaction timeouts and advances open episodes.

> `wha serve` holds the virtual environment open and will block `uv sync`. Stop it first.

---

## Three Symmetrical Configuration Interfaces

You can configure, test, and manage the system through whichever interface you prefer:

| Interface | How to Use | What It Supports |
|---|---|---|
| **Web Dashboard** | Open `http://localhost:8501/Settings` | Live test buttons for Bridge, LLM, and Telegram; secret inputs; one-click persistent saves; permanent data purge. |
| **Environment File** | Edit `.env` | File-based persistent configuration for headless and production deployments. |
| **CLI Overrides** | `uv run wha ... --live` | Inline shell flags, temporary runtime overrides, and diagnostic probing. |

---

## Command-Line Interface (CLI) Reference

```bash
# Diagnostics & Health
uv run wha doctor                # Fast offline configuration check
uv run wha doctor --live         # Live network, hardware, and LLM probe check

# Data & Ingestion
uv run wha ingest --days 3       # Fetch & normalize live biometrics from phone bridge
uv run wha nightly               # Run daily baseline calculation & anomaly detector
uv run wha data fetch corpus     # Build the retrieval corpus, including MedlinePlus
uv run wha data capability       # What your watch sends, and how far each channel gets
uv run python experiments/detection/cohort/fetch.py   # The Mishra 2020 cohort, a 378 MB public download
uv run python experiments/detection/cohort/labels.py  # Its symptom-onset labels, from the same paper

# Demonstrations & Scenarios
uv run wha demo list             # List available offline clinical replay scenarios
uv run wha demo run illness-onset --live  # Run illness scenario against live LLM

# Investigation & Bayesian Belief
uv run wha episode list          # View active and resolved clinical episodes
uv run wha episode step <id>     # Manually advance an episode cycle
uv run wha belief explain        # Output exact mathematical marginals over 12 causes

# Evaluation
uv run wha eval-report           # Run the offline suites, writes into experiments/detection/
uv run wha eval policy           # Real policies through the real belief model
uv run wha eval adversarial      # Prompt-injection containment over 15 cases
uv run wha eval baseline-age     # How the baseline behaves as nights accumulate

# Two suites REFUSE rather than report, and say why when you run them:
#   eval detection  scores detections a caller replays, and nothing in the app replays
#                   them, so it used to print zeros as a benchmark. Detection accuracy
#                   comes from experiments/detection/cohort/ and is published in experiments/detection/detection-results.json
#   eval ablation   was entirely synthetic: 32 invented participants, scores from
#                   random.Random(42) and a hardcoded table of "effect sizes"

# Cohort measurements that settled design questions
uv run python experiments/detection/cohort/sweep.py              # Threshold and persistence sweep
uv run python experiments/detection/cohort/yellow_persistence.py # Does a long yellow run deserve an alert?
uv run python experiments/detection/cohort/band_width.py         # The within-person scale, and alert rates

# Conversation, corpus, and the model provider
uv run wha tell "I have a sore throat"   # Say how you feel without waiting to be asked
uv run wha corpus search fever           # What the agent would retrieve for a query
uv run wha corpus build                  # Rebuild the retrievable corpus from the tables
uv run wha llm record illness-onset      # Re-record the offline cassettes for a scenario
```

---

## Web Dashboard Overview (`wha serve`)

**For a full walkthrough written for a non-technical reader, see
[USER-GUIDE.md](USER-GUIDE.md).**

![Today](docs/screenshots/guide-today.png)

*Today: the status strip, last night as a colour and a plain sentence, then three numbers,
each saying what it is. The one that matters is the third, the gap between your reading and
your own normal.*

![History](docs/screenshots/guide-history.png)

*History: your nights against your own usual range, which narrows as the system learns you.
Gaps are left as gaps. The axis is deliberately not anchored at zero.*

![The record](docs/screenshots/guide-record.png)

*The record: all 21 steps for every night, coloured by which part of the system ran them.
Green is arithmetic, blue is the AI inside its fenced loop, purple is the person, red is the
safety floor. Every step opens.*

![A step, opened](docs/screenshots/guide-step-detail.png)

*Any step opens to what it did, why it exists, the arithmetic in words, and the raw record
underneath. This is step 8, showing every symptom the person has reported, how many nights
each has run, and how many nights it would take to raise it.*

*Rewritten on 6 and 7 September 2026 for a reader with no engineering and no medical
background. Every number on screen says what it is, where it came from, and what to do about
it; the wording lives in one module and carries no figures, because a number typed into a
screen drifts away from the code that uses it.*

* **📅 Today (`/Today`)**: Anything needing you first, then last night as a level, a plain
  sentence, three numbers each with its explanation, and what happens next. Chat with
  citations that open to the whole passage with the quoted span marked. One control copies a
  summary for a clinician.
* **📊 History (`/History`)**: One chart with a caption naming every element on it, and six
  columns rather than eleven. Everything else is behind one toggle.
* **🔍 The record (`/The_record`)**: The night drawn as **21** numbered clickable steps,
  coloured by which machine ran them, for **every** night rather than only investigated ones.
  Each step opens to what it did, why it exists, the arithmetic in words, and its sources:
  all twelve causes with their probabilities, every question the policy weighed and what each
  was worth, the symptoms you have reported and for how long, and the tamper-evident log
  beside it. A step with no recorded time shows none.
* **⚙️ Settings (`/Settings`)**: Every field the application accepts, each saying what it
  changes about the system's behaviour, connection tests, and deletion.

Benchmark results are not a dashboard page. They live in [experiments/detection/](experiments/detection/README.md),
regenerated by `uv run wha eval-report`, because they are evidence for someone assessing
the system rather than something a person checking their own health acts on.

---

## Working on this codebase

### Where things live

```
src/wha/
  ingest/     Pulling from the phone bridge, normalising, storing raw payloads
  features/   Sleep window resolution, turning a night into one number
  detect/     Baseline, shrinkage, the GREEN / YELLOW / RED decision
  safety/     The deterministic floor: phrase rules, tier C, triage, outbound checks
  belief/     The exact 12-cause Bayesian update
  policy/     EVSI, probe scoring, gates, the action decision
  agent/      The LangGraph loop, its nodes, its tools, and the conversation
  retrieve/   BM25 + embeddings + fusion, and the grounding check
  service/    Application logic: nightly, episodes, symptoms, pipeline, scheduler
  api/        The HTTP boundary. Everything the dashboard reads goes through here
  ui/         Streamlit screens. Holds NO data logic and NO clinical content
  llm/        Provider clients, prompts, cassettes
  notify/     Telegram and other outbound channels
  audit/      The SHA-256 hash-chained log
data/knowledge/   The clinical tables. Under change control, see below
experiments/detection/cohort/     The measurement scripts behind every published number
tests/            unit, integration, scenario, and ui (Streamlit AppTest)
```

### Rules enforced by tests, not by convention

You will hit these if you break them, so they are worth knowing up front.

- **`docs/CONTRACTS.md` is compared against the models, schema and constants on every run.**
  Add a table or a model field and the suite fails until the contract is updated.
- **The dashboard may not import from `wha.service`.** It is an API client. A test walks the
  UI source and fails on any reach past the API.
- **UI copy may contain no digits.** A number typed into a screen drifts away from the code
  that computes it, so every figure is fetched from `/config` at render time.
- **Every pipeline step must have plain-English copy and a name,** and the "How this works"
  tab must cover exactly the steps that exist. Adding a step without explaining it fails.
- **Every number in `red_flags.yaml`, `causes.yaml` and `probes.yaml` must declare its
  provenance** (`CITED`, `DERIVED` or `ASSUMED`) or the file refuses to load.
- **Every free-text call into the safety floor must pass the symptom history.** An AST check
  enforces it, because that exact wire was missing for the life of the project and no
  behavioural test could see it.
- **A new dependency between two packages fails the build until it is declared.** Every one
  that exists is listed in `tests/unit/test_layering.py`. Two import cycles are named there
  with their reasons; an eighth upward import fails.
- **The agent's node names and the graph must agree.** `src/wha/agent/steps.py` declares
  them and `tests/unit/agent/test_steps.py` compares that against the compiled graph, so a
  node added or renamed cannot go missing from the audit view.

### Working on this at the same time as somebody else

Four things are shared by everything, so they are where parallel work collides. Changing one
is not wrong, but say so in the pull request, because somebody else is probably in the same
file:

| Shared surface | Why it collides |
|---|---|
| `src/wha/models.py` | Imported by 71 files. Every workstream eventually adds a field |
| `src/wha/constants.py` | Imported by 54. Also under change control: a clinical figure here needs `docs/KNOWLEDGE-CHANGELOG.md` |
| `data/schema.sql` | Four tests compare it to `docs/CONTRACTS.md`, so a column is never a local change |
| `docs/CONTRACTS.md` | The obligation the three above all lead back to |

The seams that let the big workstreams proceed without touching each other:

| If you are... | Start at | What holds it together |
|---|---|---|
| Replacing the dashboard | `src/wha/api/client.py` and the 34 endpoints behind it | `tests/ui/test_ui_boundary.py`. No screen may reach past the API |
| Restructuring the agent | `src/wha/agent/steps.py`, then `src/wha/agent/nodes/` | `tests/unit/agent/test_steps.py`. Map new nodes onto existing public steps and no screen moves |
| Replacing retrieval | The `Retriever` protocol in `src/wha/retrieve/index.py` | `tests/unit/retrieve/test_retriever_protocol.py`. Keep the `RetrievalResult` shape or you disable the grounding check |
| Changing when an investigation opens | `src/wha/service/episode_lifecycle.py` | It is already independent of the agent. The detector does not know episodes exist |

### How to make common changes

| You want to... | Do this |
|---|---|
| **Change the retrieval, or replace it** | Implement the `Retriever` protocol in `src/wha/retrieve/index.py`: one method, `query`. Nothing outside the package names `HybridIndex`. **Keep returning `RetrievalResult` with its fields.** `enforce_grounding` reads `chunk_id`, `title`, `text` and `source_url` off those results to strip clinical sentences no passage supports, so a different shape does not swap the search, it disables the claim-to-source check, and it does so without erroring. |
| **Change the AI model or provider** | Set `WHA_LLM_PROVIDER`, `WHA_LLM_BASE_URL`, `WHA_LLM_MODEL` and `WHA_LLM_API_KEY` in `.env`, or use the Settings screen. Anything OpenAI-compatible works. Prompts live in `src/wha/llm/prompts`. |
| **Add or change a cause** | Edit `data/knowledge/causes.yaml`. Every number needs a provenance label and a derivation. Record it in `docs/KNOWLEDGE-CHANGELOG.md` with the source sentence quoted. |
| **Add a question the agent can ask** | Add a probe to `data/knowledge/probes.yaml` with its answer slots and likelihood rows. The policy scores it automatically. |
| **Add or change a red flag** | Edit `data/knowledge/red_flags.yaml`. A symptom with no evidence for a routing threshold belongs in `tracked:`, not in a tier. |
| **Add a tool the agent can call** | Register it in `src/wha/agent/tools/`. The registry is a closed allow-list; anything not on it is refused, and the refusal is recorded. |
| **Add a pipeline step** | A step a person can see. Add it to `CANONICAL_PIPELINE_STEPS` in `models.py`, implement it in `service/pipeline.py`, give it copy in `ui/explain.py`, a name in `ui/components/pipeline_graph.py`, and a topic in `ui/components/how_it_works.py`. The tests will tell you which you missed. |
| **Rename, split or add an agent node** | Not the same job as the row above, and much smaller. `src/wha/agent/steps.py` is the only file that has to change: name the node in `AGENT_NODES` and map it onto the public step it reports as in `NODE_TO_PIPELINE_STEP`. Several nodes may map to one step, which is how the agent is restructured without any screen moving. Describe it in `_STAGE_DESCRIPTIONS` in `service/episodes.py` for the Trace tab. `tests/unit/agent/test_steps.py` fails if the graph and that file disagree |
| **Change a detection threshold** | Measure it first with `experiments/detection/cohort/`. Several such changes have been proposed and rejected on measurement; the table above lists them. |

### Testing

```bash
uv run pytest -n auto                     # Whole suite in parallel, about 5 minutes
uv run pytest tests/unit/safety -n auto   # Just what you changed, while you work
uv run ruff check src tests               # Lint
```

**A green suite proves less here than you would expect.** Every serious defect in this project
was found by opening the dashboard and using it, not by reading code. Full suites have passed
while a page crashed on load, while the safety floor was unreachable, and while four subsystems
had never once executed. **Finish by driving the real interface.**

The recurring defect shape is **code that exists, is referenced, and is never reached.** Assume
that before assuming a logic error.

---

## Identifiability Boundaries & Clinical Reality

* **Autonomic Response vs. Etiology**: Wearable optical sensors observe host autonomic nervous system changes (tachycardia, reduced vagal tone), not circulating pathogens. WHA cannot differentiate Influenza A from COVID-19 without self-reported symptoms or rapid antigen test results.
* **Confounder Magnitudes**: The everyday causes move the overnight resting rate about as
  far as an infection does, and often further, which is the whole reason the system asks
  rather than assumes. **Alcohol**: +2.8 bpm in females and +2.4 in males across a two-drink
  span, within-person (Grosicki et al., PLOS Digit Health 2026;5(3):e0001284, n=20,968).
  **Late exercise**: +1.58 bpm for a session ending 6 hours before sleep, rising to +5.59 at
  sleep onset (Leota et al., Nat Commun 2025;16:3297, n=14,689). **Infection**: average peak
  increases over baseline of 1.8 percent in females and 3.4 percent in males (Natarajan, Su
  and Heneghan, Front Physiol 2022;13:898251, n=7,200). The figures the detector uses, how
  each was derived from these papers and which parts are not from them, are in
  `data/knowledge/causes.yaml`, with the working shown on every row.
* **Maturity Ladder**:
  * `0-2 Nights` (`COLD`): Population prior only ($\mu=62.75$ bpm, and a **within-person**
    night-to-night scale, which is the value the detector actually uses. The
    between-person SD of $8.64$ from Bloomfield et al. 2024 is deliberately NOT used
    here, because the spread between different people is the wrong yardstick for one
    person's own night: see `docs/DESIGN-BASELINE-CENTRE.md`).
  * `3-6 Nights` (`PRIOR_DOMINATED`): Shrinkage heavily weighted to population prior.
  * `7-13 Nights` (`SHRINKING`): Empirical Bayes shrinkage transitioning to personal data.
  * `14-27 Nights` (`PERSONAL`): Personal median & MAD dominate.
  * `28+ Nights` (`MATURE`): Trailing 28 night window, the person's own median as the centre.

---

## Corpus & Knowledge Sources

In this repository. Every number carries its own `provenance`, one of three labels:
`CITED` (the number is in the paper), `DERIVED` (worked out from published numbers, with
the working shown) or `ASSUMED` (no published value exists, and the assumption is stated).

**There are no `CITED` rows left in `causes.yaml`, and that is a labelling correction
rather than a loss of evidence.** An audit on 5 September 2026 checked all three against
their sources and none survived: alcohol's own citation text said "it is not what the paper
measured", luteal's effect size is Goodale's but its spread and base rate are not, and
Radin supports recovery_tail's 79 day window and none of its three numbers. A row carries
one label for four numbers, so the label has to describe the weakest of them.

* **`data/knowledge/causes.yaml`**: 12 clinical causes with effect sizes, base rates and
  temporal dynamics. Each row's `derivation` names which of its figures comes from the
  paper, which is worked out from it, and which is `NO EVIDENCE FOUND`.
* **`data/knowledge/probes.yaml`**: 8 structured clinical questions over discrete answer slots. **Every likelihood row is `ASSUMED`.** No published study measures how accurately a person reports drinking, stress or early symptoms to an app the next morning, so the numbers are set flat, which understates how informative a question is and makes the system interrupt less rather than more.
* **`data/knowledge/red_flags.yaml`**: The deterministic safety floor: the urgent list (6 rules), the same-day list (6 rules), the tracked list (recorded, escalates on nothing), the two extreme heart-rate bounds and the care-pathway sentences every outcome carries. **Eight of its ten numbers are `ASSUMED` and say so on the dashboard**, because no study was found measuring how many nights a symptom should persist before it is worth an appointment. Loading fails if any of them loses its label.
* **`data/knowledge/sources.yaml`**: The allow-list of external sources, and complete bibliographic citations for all clinical numbers.

Fetched from outside, and not redistributed here:

* **MedlinePlus health topics** (National Library of Medicine, attribution-only). About 1,000 English topics, fetched with `uv run wha data fetch corpus`. This is the only material the agent can cite that describes a condition in general rather than describing this person. Which release is in use, with its SHA-256, is recorded in **`data/knowledge/corpus-sources.json`**. Fetched text is untrusted and is scanned for prompt injection before the model sees it, exactly like any other retrieved passage.

Two layers `sources.yaml` names are still narrower than the design says: StatPearls has never been fetched, and the Singapore care-pathway material exists only as the wording already in `red_flags.yaml`. **The second is now a settled decision rather than a gap:** the corpus deliberately carries no illness-specific guidance, and the cost of that is disclosed on screen. See `docs/DISCLOSURES.md`.

The agent may cite these and nothing else. There is no open web search, and it cannot write clinical text of its own: an assertion whose quoted span is not verbatim in a cited passage is either stripped or labelled on screen as coming from the model's own knowledge. That check proves the span exists; it does not prove the sentence around it describes the source correctly, and `docs/ARCHITECTURE.md` Part 14 shows a real case where it did not. Every figure in the authored corpus was checked against the paper it cites; what held up and what did not is in **`docs/CORPUS-VERIFICATION.md`**, and every clinical figure that was changed, with the source sentence quoted for it, is in **`docs/KNOWLEDGE-CHANGELOG.md`**.

---

## Disclaimer

This software is a research prototype and personal health intelligence system. It is **not an FDA/CE-certified medical device**, does not provide formal medical diagnoses, and must not be used as a substitute for professional medical care or emergency services. If you experience severe chest pain, shortness of breath, or emergency symptoms, seek immediate professional medical attention.
