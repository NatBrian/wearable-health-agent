# Handoff: from design to implementation planning

**Written 31 August 2026.** Research, proposal and day-zero setup are complete. The next session's
job is **implementation planning only**: architecture, components, logic, features, testing. Not code
yet, unless asked.

---

## 0. How to use this document

Read this file first, then section 4's reading list. This file is the compressed context. It exists
so the next session does not redo settled work, does not relitigate settled decisions, and does not
repeat mistakes that already cost time.

Where this file states a **verified** fact, it was checked against a primary source or measured on
hardware. Where it states an **unverified** one, it says so. Preserve that distinction.

---

## 1. What this project is, in sixty seconds

Consumer wearables detect that something in your body changed but cannot tell you **why**. A raised
overnight resting heart rate is produced by an incubating infection, alcohol, hard training, poor
sleep, stress, a recent vaccination, or the luteal phase. To a wrist sensor these look nearly
identical, yet they demand opposite responses.

This is measured, not hypothetical: an independent prospective evaluation issued **665 alerts at a
positive predictive value of 4%**, and about **45% of the false alerts had a cause a single question
could have resolved**. Worse, the confounders are **larger than the signal**: infection raises resting
HR by 1.1 to 2.1 bpm, one drink by 2.4 to 2.8, a hard evening session by about 5.94.

**The monitor is not the agent.** Detection is cheap, deterministic, continuous statistics. When it
flags a deviation, a **bounded agent** is instantiated with one goal: determine the most probable
explanation, acquiring only the evidence worth acquiring, and reach a typed disposition. It reasons
across several nights, holds state while it waits, and terminates.

The project is simultaneously a **personal tool** and a **portfolio piece**. It is coursework for a
two-week AI-in-healthcare module, nominally a team of four, but **plan for one person**.

---

## 2. Status

| Area | State |
|---|---|
| Research corpus, 9 investigations, ~126k words, ~2,100 citations | Done, `research/findings/` |
| Working notes 00 to 15 | Done, `research/` |
| Design specification | Done, `PROPOSAL.md`, ~700 lines |
| Repository de-identified, published private, MIT licensed | Done, `github.com/NatBrian/wearable-health-agent` |
| Project Hermes blocking read | Done, `research/15-project-hermes-read.md` |
| Health Connect bridge reachable, schema captured | Done, `tools/probe_healthconnect.py` |
| Synthetic data generator matching the real payload shape | Done, `tools/make_synthetic.py` |
| LLM served on free Kaggle, measured end to end | Done, `tools/kaggle_serve_qwen27b.ipynb` |
| **Implementation planning** | **Not started. This is the next task** |
| Health Connect retest for sleep, RHR, HRV, respiratory rate, SpO2 | **Blocked on the user's phone and more days of data** |
| Rotate the bearer token used during probing | **Open, user action** |

Nothing is implemented. There is no application code, no tests, no data pipeline.

---

## 3. Standing constraints from the user

These are non-negotiable. Several were stated more than once.

| Constraint | The user's own words where it matters |
|---|---|
| **No personal health data shared** | *"I dont really want to give you my samsung health data, because it is private to me."* and *"I still will not provide my full samsung export."* Development uses synthetic data and public datasets |
| **Mask any health data that does appear** | *"remember my health data is sensitive so mask it"* |
| **Train nothing** | *"I also do not want to train any AI"* |
| **Do not overengineer** | *"we do not want our project to be overengineered and use many/various AI model. We must have a clear focus"* |
| **Must not be boring** | *"if the project if fucking boring, too generic and normal, no novelty than I will get poor grade and no recruiter care"* and *"My project should not be constraint by the lecture"* |
| **No manual export** | *"I want my project to be able to work without needing manual export"* |
| **Repo is portfolio-facing** | No course name, no real name, no private data. Will be made public on completion |
| **Free tiers only** | *"the healtconnect webhook app need to pay. I dont want to pay"* |
| **Quota-efficient notebooks** | *"I am using free so it should be safing my GPU usage time"* |
| **No secrets pasted into chat** | Standing rule from the user's memory |
| **No em-dashes; no Claude co-author trailer in commits** | Standing rule. Commits are authored as `NatBrian` |

**Working style:** deliver end to end, decide technical questions yourself, front-load questions into
planning rather than interrupting mid-build. Explanations in plain language.

---

## 4. Read these, in this order

1. **`PROPOSAL.md`** in full. This is the specification. Do not plan against a summary of it.
   Section 4.2 lists features F1 to F20 with MUST/SHOULD/COULD; 4.2.2 gives the `EpisodeOutcome`
   contract; 4.2.3 the episode lifecycle and triggers; 4.5 the model inventory; 4.6 retrieval;
   4.7 evaluation; 5 safety, ethics, privacy, security, limitations; Appendix B a two-week plan.
2. **`research/15-project-hermes-read.md`**. The closest prior art and what it means for the novelty
   claim. Short.
3. **`research/13-galaxy-watch5-data-reality.md`** and **`14-automatic-data-access-and-samsung-vitals.md`**.
   What the hardware actually exposes, and what Samsung already ships.
4. **`research/findings/F8`** (confounder physiology, separability matrix, value-of-information),
   **`F6`** (detection methods, datasets, and the pathologies of anomaly-detection evaluation),
   **`F7`** (agentic patterns, prompt injection, audit logging, medical corpora).
5. **`tools/`**, all three files. They define the real data shape and the real serving stack.
6. Everything else in `research/` as needed. `archive/` is an earlier, weaker generation retained
   deliberately and audited in `research/00-prior-work-audit.md`. **Do not treat `archive/` as fact.**

---

## 5. Locked decisions

Each of these was argued out. Reopening one needs new evidence, not a new opinion.

**Architecture**

- **The detector is not the agent.** Deterministic statistics flag deviations; the agent investigates
  an episode. The LLM is **never invoked on a quiet night**, which is what makes the cost model work.
- **Single agent, not multi-agent.** Free-tier rate limits make multi-agent infeasible, one action log
  is easier to audit, and published ablations show extra validate/replan stages contributing nothing.
- **Action space:** `OBSERVE`, `ASK(question)`, `MEASURE(test)`, `ESCALATE(level)`, `CONCLUDE(disposition)`.
- **Dispositions:** `EXPLAINED_BY_EVENT | LIKELY_ILLNESS | LIKELY_BENIGN | ESCALATED | UNRESOLVED |
  INSUFFICIENT_DATA`. The last is a first-class outcome, not an error.
- **Two budgets:** interruption budget, default 2 per week; depth budget, default 5 per conversation.
- **The red-flag intercept is deterministic code upstream of the agent**, so it cannot be reasoned past.
- **The ask-or-stay-silent decision is explicit arithmetic outside the LLM**, expected information gain
  against interruption cost, in the form of Horvitz, Jacobs and Hovel, *Attention-Sensitive Alerting*,
  UAI 1999. This is what makes the policy measurable against never-ask, always-ask and fixed-threshold
  baselines. An LLM told to "ask if unsure" can be demonstrated but never evaluated.

**Models: four, none trained**

| # | Component | Job |
|---|---|---|
| 0 | Personal statistical baseline | Rolling median and MAD, multi-signal concordance, multi-night persistence. **Not a model.** Also the baseline everything else must beat |
| 1 | **Chronos-Bolt**, Apache-2.0, zero-shot, CPU | What should tonight have looked like, with an expected range |
| 2 | **pgmpy** discrete Bayesian network | Belief over twelve candidate causes. Hand-specified structure, literature-elicited priors, every number cited |
| 3 | **Sentence embedding model** (e.g. `bge-small-en-v1.5`) | Dense retrieval |
| 4 | **LLM** (Qwen) | Language only: extract structured facts, phrase questions, write explanations. Never computes a number, never decides an action |

Explicitly excluded, with reasons in `PROPOSAL.md` 4.5.2.1: trained classifiers, cross-encoder
rerankers, MOMENT (normalises away vertical shifts, which is exactly our signal), IBM TTM (512-step
minimum equals 1.4 years at nightly cadence), Apple WBM / Google LSM-2 / SensorFM (no released
weights), TimesFM 3.0 and Moirai (non-commercial licences), GraphRAG, multi-agent.

**Stack**

LangGraph with SQLite checkpointer and `interrupt()` for the human gate; Pydantic validation on every
agent step; hybrid BM25 plus dense retrieval fused by reciprocal rank fusion with claim-to-source
enforcement; Streamlit with the reasoning trace and audit log visible; pytest plus a frozen scenario
suite with cached and replayed LLM responses.

**Data**

- Ingestion via the **Health Connect Webhook** app (AGPL-3.0, Play Store), not a custom Android app,
  and not a manual export.
- **Stanford COVID-19-Wearables** for detection (open, HR and steps only, no labels in the archive).
- **PMData** for confounder attribution (verified CC BY 4.0, 16 participants, 5 months;
  `reporting.csv` has alcohol, `wellness.csv` has stress/mood/sleep quality, `srpe.csv` training load,
  `resting_heart_rate.json` per day). **This is what dissolves the circularity objection**: PMData's
  real self-reports are revealed only when the agent asks for them.
- **COVID-RED** is the only RCT and the only dataset with confounder annotations, but it is gated.

---

## 6. Verified facts

**LLM serving, measured on Kaggle 2x Tesla T4, 31 August 2026**

| Property | Value |
|---|---|
| Engine | **Ollama v0.33.2** (pinned). Not vLLM, not llama-cpp-python |
| Model | `qwen3.8:27b` from Ollama's registry, 18 GB |
| Placement | **100% GPU**, both cards, 8192 context |
| Sustained generation | **9.2 tok/s** |
| Time to first token, streaming | 4.34 s |
| Cold start from cached weights | 2 min, versus ~20 min without |
| JSON mode | Returns schema-valid objects |
| Auth | Bearer-token proxy in front of the tunnel. Verified 401 on missing and wrong keys |

**Three constraints this imposes on implementation:**

1. **`max_tokens` must be at least 200.** Qwen3.8 is a thinking model; reasoning tokens are billed
   against the budget but stripped from `content`. A small budget returns `finish_reason="length"`
   with an **empty string**, which looks like a broken model. A two-word answer cost 37 tokens.
2. **Thinking can only be disabled on the native `/api/chat`** with `"think": false`, not on
   `/v1/chat/completions`. The proxy forwards all paths, so `/api/chat` is available unchanged.
   Untested but worth ~40 to 50% latency.
3. **The endpoint is ephemeral.** URL and key regenerate every Kaggle session. **The client must read
   them from a `.env` at run time.** Never hard-code, never commit. `.gitignore` already excludes `.env`.

**Speed is bandwidth-bound and near its ceiling.** One token reads all 18 GB, a T4 gives ~320 GB/s,
and Ollama splits layers **sequentially**, so the ceiling is ~17.8 tok/s. The second T4 buys capacity,
not speed. Tensor parallelism would help but Ollama does not do it and vLLM is broken on Turing. There
is no MoE variant of Qwen3.8. An **unmeasured** `qwen3.8:27b-mtp-q4_K_M` at the same 18 GB offers
multi-token prediction, reported at +33 to 39% with identical output. Measure it at the next cache
rebuild.

**Real device payload shape**, observed 31 August 2026, app v1.9.17. Fully documented in
`tools/make_synthetic.py`. Only `heart_rate` and `steps` have been seen so far; sleep, resting HR,
HRV, respiratory rate and SpO2 are pending a Samsung-side sharing change. Step buckets align to local
midnight (16:00Z on UTC+8), heart rate arrives in 1-minute buckets with avg/min/max.

**Important:** the Samsung Health **export** does contain `com.samsung.health.hrv`,
`respiratory_rate` and `skin_temperature`. The earlier claim that the watch lacks these was wrong; it
is true of the Data SDK, not the export. But **the user will not provide the export**, so plan for
whatever Health Connect delivers.

---

## 7. Traps that already cost time

| Trap | Avoid it by |
|---|---|
| **Bash heredocs mangle content.** Backticks became command substitution; apostrophes broke quoting; one incident silently emptied a table in `PROPOSAL.md` | Write scripts to a file, then execute. Do not pipe complex content through a heredoc |
| **Stale cross-references after rewrites.** Caught four times, twice by the user: "eight components" when there were four, "roughly ten causes" while listing twelve, a serving section still specifying vLLM after we had abandoned it | After any structural edit, **read the whole document**, not a targeted grep |
| **Jupyter "Run All" ignores `SystemExit`** | Use `RuntimeError` to halt a notebook run |
| **Kaggle output is capped at 20 GB** | The model store is 18 GB. Nothing else large goes in `/kaggle/working` |
| **A Quick Save from a serving session destroys the cache** | Only ever save from a `BUILD_CACHE=True` run |
| **Kaggle's DNS cannot resolve a fresh `trycloudflare.com` hostname** | Never let an in-container self-test decide whether the endpoint works. The laptop is the client that matters |
| **Ollama cannot import Unsloth "UD" GGUFs** | Use registry tags, not GGUF files |
| **The Health Connect app 500s on unrecognised record types** | Keep the selected data types narrow |
| **Overstating findings.** Twice I asserted something ("citations are fabricated", "the watch lacks HRV") that fuller checking disproved | State the evidence and its strength. Do not round a suspicion up to a fact |

---

## 8. Open questions the plan must resolve

These are genuinely unsettled. They are the right things to spend planning time on.

1. **What triggers a nightly run?** There is no server. Windows Task Scheduler, a manual button, or a
   Streamlit-launched job? This determines the whole execution model.
2. **How does the agent survive the LLM endpoint being down?** Kaggle sessions expire, quota is 30
   h/week, and the URL changes. What happens to an in-flight episode?
3. **The twelve causes: what exactly are they**, and what is the concrete elicitation procedure from
   published effect sizes to conditional probability tables? This is the reasoning core and the most
   under-specified part of the design.
4. **What is actually in the retrieval corpus?** Which Singapore sources (MOH, HealthHub, NEA dengue
   clusters) and which international ones, how many documents, chunked how?
5. **How is the information-gain policy evaluated without labels?** F6 documents the pathologies here:
   point-adjusted F1 lets random scores reach 0.969.
6. **How is the interview surfaced?** The proposal says tap-first rather than free text. What does
   that mean concretely for the UI and for the LLM's role?
7. **What is the demo?** 4.2.5 says scripted replay. What exactly is replayed, and what is live?
8. **Local versus Kaggle split.** What runs where, and what is the interface between them?
9. **Which features are genuinely MUST for two weeks?** F1 to F20 is more than one person builds. The
   plan should cut, explicitly, and say what is cut.

---

## 9. What the implementation plan must cover

The user asked for this to be **very detailed**:

- High-level architecture, with the boundaries between deterministic code, the belief model, and the LLM drawn explicitly
- Component-by-component breakdown, with responsibilities and interfaces
- Detailed logic for the detector, the belief update, the information-gain policy, and the agent loop
- Feature list mapped to F1 to F20, with a cut line for two weeks
- Data layer: ingestion, storage schema, backfill, synthetic generation, the public datasets
- Retrieval: corpus, chunking, indexing, fusion, claim-to-source enforcement
- Safety: red-flag intercept, escalation, prompt-injection posture, audit log
- Testing: unit, the frozen scenario suite, replayed LLM responses, the evaluation harness
- Evaluation: detection metrics, policy benchmark against never-ask/always-ask/threshold, ablation per model, adversarial suite
- Sequencing across two weeks, with dependencies and a critical path

---

## 10. What I would challenge in the next session

Offered as honest concerns, not blockers.

- **F1 to F20 is too much for two weeks and one person.** The plan should force a cut early rather
  than discover it in week two.
- **The twelve-cause Bayesian network is the highest-risk component.** Eliciting twelve priors and
  their conditional tables from literature, each with a citation, is slow and fiddly work. Consider
  whether six well-evidenced causes would demonstrate the same idea and actually get finished.
- **The evaluation is where marks are won and where projects run out of time.** Appendix B puts it
  last. Consider building the harness early against synthetic data so it is not sacrificed.
- **The novelty now rests on the decision layer**, since Hermes has the ask-and-update mechanism. That
  makes the information-gain policy and its baseline comparison the single most important thing to
  finish. If only one thing works properly, it should be that.
- **9.2 tok/s shapes the UX.** Design for short LLM outputs and stream them. A 45-second wait per
  interview turn will feel broken.

---

## 11. Repository map

```
PROPOSAL.md        the specification. Read in full
README.md          portfolio-facing overview
DISCLAIMER.md      not a medical device
LICENSE            MIT
HANDOFF.md         this file
research/          00-15 working notes; findings/ holds the 9 investigations
archive/           earlier weaker generation, audited in research/00. NOT a source of truth
tools/             probe_healthconnect.py, make_synthetic.py, kaggle_serve_qwen27b.ipynb
```

`main` is a protected ref; pushes bypass as owner. Twelve historical commits carry the author name
"Nathanael Brian"; the email is the GitHub noreply address throughout and repo-local `user.name` is
now `NatBrian`. Rewriting those twelve is an open, unmade decision.
