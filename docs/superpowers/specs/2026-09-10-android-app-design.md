# The Android app: design

**Written 10 September 2026.** A standalone Android app that runs the whole Wearable Health
Agent on the phone. Not a port of the Streamlit dashboard: the passive monitor, the safety
floor, the agent, retrieval, grounding and the audit chain all execute on the phone, and the
PC is not needed after installation.

The PC remains the main codebase. Every project update happens there. The app exists so a
person who is not a power user can run the system on the phone they already carry, and it is
a second client of the same service layer the HTTP API already exposes.

---

## 1. Decisions already made, with the reasons

These were settled with the owner on 10 September 2026 and are not open.

| Decision | Choice | Why |
|---|---|---|
| How the Python runs on the phone | The existing Python core, embedded with Chaquopy | Easiest and most robust of the three options considered. Chaquopy is MIT licensed, maintained, and supports Python 3.12 and 3.13 with numpy, scipy, pandas, lxml, pyyaml and tokenizers prebuilt. A Kotlin rewrite of the clinical logic was rejected because it would create a second copy of reviewed clinical code that could silently diverge |
| Data source | The Health Connect Webhook app already installed on the phone, called over HTTP on localhost | The ingest code and its protocol are unchanged. Host and port are settings because the webhook app's port may change |
| Future of the PC | Stays the main system. CLI, tests, tooling, experiments and the Streamlit dashboard keep working | The app is for convenience, not a replacement |
| First launch data | Fresh from Health Connect only. No demo timeline, no import of PC history | The owner's choice. Health Connect grants read access to the thirty days before permission was given, which is enough to grow a baseline |
| Navigation | Bottom bar: Today, History, Record, Settings | Standard Android, one tap to anything |
| Chat | Inside Today, as one thread with the pending question | Mirrors Telegram: one transcript, one safety floor |
| Explanation depth | Layered: summary, then why, then full detail, collapsed | Progressive disclosure, see section 6 |
| Look | Calm clinical: light, muted, one accent colour | Reads as a health record, not a fitness app |
| Language | English only, structured so a second language can be added | The owner's choice for v1 |
| Notifications | Exactly the rules the system already has. No new rules | The owner's instruction: the only change is that the phone shows them natively instead of via Telegram |
| Record tab | A live, traceable pipeline view, not a static expander | The owner's stated objective, see section 7 |

---

## 2. What this is not

- It is not a medical device and does not diagnose. `DISCLAIMER.md` applies unchanged and
  is shown before first use.
- It does not add, remove or retune any clinical rule, threshold, notification rule or
  policy. Every number on a screen comes from the `/config` enumeration of
  `src/wha/constants.py` or from stored data, exactly as the dashboard does today.
- It does not measure its own accuracy or present any figure this project measured about
  itself. Rule 3 of `AGENTS.md` applies to every string in the app.
- It does not run a language model on the phone. The agent calls the configured
  OpenAI-compatible provider over HTTPS, as the PC does. The passive monitor and the safety
  floor never need the network, as today.

---

## 3. Shape

```
android/                      Kotlin app, Gradle project, in this repository
  app/src/main/python/        Chaquopy entry: a thin wha_android package that imports wha
  app/src/main/assets/        data/knowledge, the corpus manifest, the ONNX embedding model
  app/src/main/java/.../      Compose UI, WorkManager jobs, notifications, key storage
  wheels/                     Android wheels built in WSL, consumed by Gradle with find-links
src/wha/                      The system, unchanged except for the seams in section 4
```

Three layers on the phone:

1. **Python core** (`wha`). Everything clinical. Runs inside the app process under
   Chaquopy. Called through a small facade module, `wha_android.facade`, whose functions
   take and return JSON strings built from the same Pydantic models the HTTP API returns.
   That keeps `docs/CONTRACTS.md` as the app's contract too.
2. **Kotlin shell**. Owns what the phone must own: the schedule (WorkManager), the
   foreground service while an investigation runs, notifications, secure storage for the
   provider key and the webhook token, the corpus download, and the screens.
3. **The screens**. Jetpack Compose, Material 3, single activity, one view model per
   screen. No screen reads the database or the constants directly. Every screen reads a
   view model, every view model reads the facade. A test asserts it, as the dashboard test
   asserts today that no page imports the service layer.

Nothing leaves the phone except the provider call and the one-time corpus fetch from the
release recorded in `data/knowledge/corpus-sources.json`.

---

## 4. The minimum change to the core

The rule for this section: the owner asked for the least rewriting that is robust. Every
change here is a seam, not a redesign, and each one is enforced by a test.

### 4.1 Dependency split

`pyproject.toml` gains a `pc` extra. Core dependencies are those the phone needs: pydantic,
pandas, numpy, scipy, httpx, typer, python-dotenv, langgraph and its checkpointer,
rank-bm25, lxml, pyyaml. The `pc` extra holds streamlit, altair, fastapi, uvicorn,
sentence-transformers, apscheduler. `uv sync` on the PC installs both, so nothing changes
for the PC.

A new test imports every module under `wha` except `wha.ui`, `wha.api`, `wha.cli` and the
scheduler with the `pc` packages blocked in `sys.modules`, and fails if any import reaches
them. That is the guarantee the phone relies on.

### 4.2 Native wheels, decided by a spike before any app code

Chaquopy's documented path for Python 3.13 and later is: build the wheel with cibuildwheel
on Linux, then point Gradle at the folder that holds it. The owner's WSL Ubuntu can do
that. The packages in the runtime tree with native code that Chaquopy does not already
provide are:

| Package | Needed by | Language |
|---|---|---|
| pydantic-core | pydantic, 48 files in `src/wha` | Rust |
| orjson | langgraph-sdk, langsmith | Rust |
| ormsgpack | langgraph-checkpoint | Rust |
| xxhash | langgraph, langsmith | C |
| sqlite-vec | langgraph-checkpoint-sqlite | C |

Verified on 10 September 2026: pydantic-core 2.49.0 on PyPI has no Android wheel; the
Chaquopy issue asking for pydantic v2 has been open since November 2023; a recipe PR from
October 2025 is unmerged; the Chaquopy maintainer now directs everybody to cibuildwheel.
The Termux community wheels are tagged `linux_aarch64` and linked against Termux's Python,
so they are not usable here.

**The spike.** In WSL: install a JDK, the Android command-line tools and NDK, Rust with the
`aarch64-linux-android` target, and cibuildwheel. Build pydantic-core for
`arm64_v8a` at the API level the app targets. If it builds and imports on the phone, build
the other four the same way.

**The outcomes, decided in advance:**

- All five build: nothing in the Python changes. langgraph stays.
- pydantic-core builds, one or more of the langgraph four do not: `agent/graph.py` is
  replaced by a plain bounded loop over the same eight node functions in `AGENT_NODES`,
  with the same recursion limit, the same pause on `ask`, and the same resume on answer.
  The checkpointer becomes a small table in the existing database. `agent/steps.py`
  already declares the node names and their pipeline mapping, so no screen changes. The
  existing agent tests must pass unchanged against the loop.
- pydantic-core does not build: stop and bring it back to the owner. The fallback is a
  migration of the models to a pydantic v1 style or to dataclasses, which is the rewrite
  the owner does not want and must be their decision.

The spike is throwaway except for the wheel files it produces, which are committed under
`android/wheels/` with a `BUILD.md` recording the exact commands, versions and hashes.

### 4.3 The embedding seam

`wha.retrieve.index.Embedder` is already a protocol with an `embed_texts` method. The
phone supplies an implementation backed by the same `BAAI/bge-small-en-v1.5` model
exported to ONNX, run by ONNX Runtime for Android from Kotlin, with tokenisation by the
`tokenizers` package that Chaquopy provides. The corpus embeddings are the ones the PC
computed, fetched with the corpus, so phone and PC retrieve the same chunks for the same
query. `knowledge_docs.py` gains an injection point for the embedder instead of
constructing `DefaultSentenceTransformerEmbedder` inline. Until the corpus has arrived the
existing `_BM25OnlyEmbedder` path runs and the Today screen says retrieval is not yet
available, as a disclosure.

A test embeds a fixed set of sentences with the sentence-transformers model and the ONNX
model and asserts the vectors agree to a tolerance recorded in the test. That is the
evidence phone retrieval matches PC retrieval.

### 4.4 Paths

Knowledge tables are opened by paths relative to the working directory (`data/knowledge/
causes.yaml` and friends). The app extracts `data/knowledge` from its assets to its private
files directory on first launch and sets that directory as the Python working directory
before importing `wha`. `WHA_DB_PATH` and `WHA_CASSETTE_DIR` are set the same way. No path
in the core changes.

### 4.5 The schedule

`service/scheduler.py` already separates the job functions from APScheduler. WorkManager
runs the same functions through the facade:

| PC job | Phone |
|---|---|
| ingest, every thirty minutes | Periodic work, same interval, no network constraint because the webhook is on the phone |
| nightly scoring | Periodic work after the configured wake time, same function |
| episode tick | Chained after ingest and nightly, same function |
| startup catch-up | Run once when the app process starts |
| Telegram poll | Not on the phone |

An investigation runs inside a foreground service with a visible "Investigating last night"
notification, so the person can see the system working (section 6, guideline G11).

### 4.6 The notification channel

A new `Notifier` implementation with `channel = "android"` sits beside `telegram` and
`none`. Python decides when to send, exactly as today; the implementation hands the
message, its options and the interaction id to Kotlin, which posts the notification with
one action per option plus "Not now". A tapped action writes the answer back through the
same function the Telegram receiver uses, so "Not now" consumes the interruption budget on
the phone exactly as it does on Telegram. Free text typed in the app goes through the same
conversation engine and the same safety floor. Escalations are posted on a separate
high-importance channel. Which channel is used for what is stated on the Settings screen.

### 4.7 The provider key

The person types the provider key into Settings. Kotlin stores it in encrypted shared
preferences backed by the Android keystore and passes it to Python as an environment
variable at process start. It is never written to a file the person can read and never
logged. The key currently in the PC's `.env`, flagged as compromised in its own header, is
rotated before any phone build is made.

---

## 5. What the facade exposes

One Python module, `wha_android/facade.py`, and nothing else is called from Kotlin. Every
function takes primitives, returns a JSON string built by `model_dump_json` of an existing
model, and never raises across the boundary: errors are returned as a JSON envelope with a
kind and a message, and the kinds are enumerated in `docs/CONTRACTS.md`.

| Function | Backed by |
|---|---|
| `status(subject)` | `service.status` |
| `nights(subject, range)` and `night_pipeline(subject, date)` | `service.nights`, `service.pipeline.get_night_pipeline` |
| `pipeline_nights(subject)` | `service.pipeline.list_pipeline_nights` |
| `episodes(subject)` and `episode(id)` | `service.episodes` |
| `pending(subject)`, `answer(episode, option)`, `review(episode, decision)` | `service.episodes` |
| `conversation(subject)` and `say(subject, text)` | `service.conversation` |
| `urgency(subject)` and `acknowledge_urgency(subject)` | `service.status` |
| `audit(subject, page)`, `audit_export(subject)`, `audit_verify(subject)` | `service.audit` |
| `settings()` and `update_settings(patch)` | `service.settings` |
| `config()` and `localise()` | `api.app` equivalents, moved into the service layer so both clients share them |
| `knowledge_provenance()` and `safety_provenance()` | `retrieve.knowledge_docs` |
| `run_ingest()`, `run_nightly()`, `run_episode_tick()`, `run_startup_catchup()` | `service.scheduler` job functions |
| `fetch_corpus(progress_id)` | `cli` data fetch, with progress written to a table Kotlin polls |
| `doctor()` | `cli` doctor, returned as rows |

The list is the API's endpoint list with the diagnostics endpoint. A test asserts that the
set of facade functions and the set of API routes name the same service functions, so the
two clients cannot drift.

---

## 6. The screens, and the sources behind each rule

The rules below are the product of reading, not preference. Sources marked **(full)** were
read in full; **(located)** were found and their abstracts and result summaries read, with
the full text behind a bot wall. Every rule names the source it comes from.

### 6.1 The sources

1. Amershi S, Weld D, Vorvoreanu M, et al. *Guidelines for Human-AI Interaction.* CHI
   2019. doi:10.1145/3290605.3300233. Eighteen guidelines in four phases, validated with
   forty-nine practitioners across twenty products. **(full)**
2. Meng Y, Liu B, Liu Z, Chen R. *Wearing Trust: How Older Adults Calibrate Reliance on
   Health Wearables Through Bodily Experience and Everyday Use.* arXiv:2608.08856, 2026.
   Thirty-one interviews. Names the "observability gap": people judge a wearable by price,
   interface density and bodily agreement because the system hides signal quality,
   uncertainty and failure conditions. **(full)**
3. He X, Zheng X, Ding H. *Existing Barriers Faced by and Future Design Recommendations for
   Direct-to-Consumer Health Care Artificial Intelligence Apps: Scoping Review.* J Med
   Internet Res 2023;25:e50342. Thirty-two studies; eight barriers, six recommendations.
   **(full, results and recommendations sections)**
4. Islam F, Islam A, Amin MA, Zaber M. *A Proposed Participatory Framework for Explainable AI in mHealth: Mixed Methods Study Integrating User and Stakeholder Requirements.* J Med Internet Res
   2026;28:e87158. Survey of 137 users plus twenty stakeholders; a five-pillar framework.
   Its central finding: users did not distinguish between apps by their algorithm, they
   wanted stepwise cause-and-effect narratives and human validation. **(full, results,
   framework and discussion sections)**
5. Rojo D, Lamqaddam H, Gosak L, Verbert K. *Petal-X: Human-Centered Visual Explanations to
   Improve Cardiovascular Risk Communication.* arXiv:2406.18690, 2024. Lay audiences
   preferred a flower-shaped contribution plot over score charts for seeing which factor
   contributed how much. **(full, sections 1 to 4)**

None of these studied this system. They justify interface rules, never clinical ones.

### 6.2 The rules the whole app follows

| Rule | Source |
|---|---|
| Before first use, say what the system can do and how well, in plain words, including that it has never been tested on a patient | Amershi G1, G2; He 2023 recommendation on "performance" explanations |
| Every statement is labelled by which machine produced it: arithmetic, a rule, a language model, or a quoted source, with the source named | Meng 2026 "alert provenance"; JMIR 2026 pillar 2 |
| Every decision, including a decision to stay quiet, shows its reason on the screen where the person would look for it | Amershi G11; this project's own rule that silence needs justification |
| Show signal quality: minutes of contact, whether sleep was recorded, how many nights the baseline rests on and which rung it is on | Meng 2026 "signal quality and sensing gaps"; the `PipelineHeadline` already carries `rung` and `coverage_minutes` for this reason |
| Explanations are layered: a sentence, then the why, then the full trace on request | He 2023 "progressive disclosure"; JMIR 2026 "layered, adaptive explanations" |
| Explain as a narrative of cause and effect, not as probability tables first | JMIR 2026: users wanted "you reported these symptoms; therefore" narratives over confidence scores |
| Every answer can be dismissed with one tap and corrected afterwards | Amershi G8, G9 |
| One place controls everything the system does, with every constant and its provenance | Amershi G17 |
| End every conclusion with what to do next, and where to seek help | He 2023 "content actionability" |
| A human decides at the review checkpoint; the screen makes clear the system did not act alone | JMIR 2026 pillar 1, human oversight as the foundation |
| Colour is never the only carrier of meaning; every status has a word and an icon | Accessibility baseline; also Meng 2026 on dense interfaces being mistaken for capability |
| UI copy contains no digits. Numbers come from config or data | Existing project rule, kept |

### 6.3 Onboarding

Four screens, once. What it is (G1). What it cannot do, including the untested-on-patients
statement and that it does not diagnose (G2). The disclaimer as a consent step. Then the
webhook host and port with a "test connection" that shows the round trip and which record
types arrived, the provider key, and notification permission. Then the corpus fetch with a
progress bar, and the app is usable while it runs, with retrieval disclosed as pending.

### 6.4 Today

Top: last night as a sentence and a status word, with the signal-quality line under it
(contact minutes, sleep recorded or clock fallback, baseline rung and the nights behind
it). Then whichever applies: the pending question with its options and "Not now"; an open
escalation that stays until acknowledged, with the acknowledgement recorded; or the reason
the system is quiet, in words, taken from the decision output. Then the conversation thread.
Free text goes through the same safety floor and engine as everything else.

### 6.5 Investigation

Opened from Today or History. Three layers, top to bottom:

1. **What it concluded and what to do**, one paragraph, with the disposition word and the
   human review state.
2. **Why**: the narrative of what evidence moved the belief, in sentences, then the ranked
   list of the twelve causes as horizontal bars with the top one named. The Petal-X finding
   supports a contribution-style visual; the bar list is the simpler form and stays
   readable at phone width.
3. **The full trace**, collapsed: every tool call with its result, the EVSI decision with
   the numbers it compared, each question and answer, the critique's removals, and every
   quoted passage with "MedlinePlus, National Library of Medicine" named as today's
   constants require.

### 6.6 History

A nights chart with the baseline band and the status of each night, drawn with the dataviz
rules (light theme, colour pinned to meaning, a legend in words). Below it the episode list.
Tapping a night opens the Record tab on that night; tapping an episode opens Investigation.

### 6.7 Settings

Data source (host, port, token, test connection, last successful pull). Contact (which
notification channel carries which message kind, as the system defines them). Provider
(base URL, model, key). Every constant with its provenance, read from `/config`, grouped
as the dashboard groups them. Disclosures, the same list `docs/DISCLOSURES.md` requires
each screen to show. Diagnostics: the doctor rows. About: version, licence, the
MedlinePlus attribution.

---

## 7. The Record tab: the pipeline, live

The owner's objective, in their words: show a normal person how the system's pipeline works
live, each night, so they can trace where a result came from, why, how and what, in a clean
step-by-step graph, and inspect any step in detail. Four capabilities were chosen: live
progress while a run is happening, replay of any past night, data lineage on tap, and the
architecture map as the frame.

### 7.1 The frame

The graph is the twenty-one canonical steps in `CANONICAL_PIPELINE_STEPS`, drawn as a
vertical flow in five groups that match `ARCHITECTURE.md`:

| Group | Steps | Machine |
|---|---|---|
| Reading the watch | collect, store, sleep window, features | arithmetic |
| Comparing with your normal | baseline, subtract explained, detect | arithmetic |
| What you have told us | safety floor | rules |
| The investigation | episode open, preload, investigate, believe, decide, ask, answer, conclude, critique, review, deliver | language model inside a fenced loop, and the person at answer and review |
| The safety rules on your words | safety phrase rules, safety triage | rules |

Each node carries its layer as a colour and an icon and a word (arithmetic, rule, model,
you), because which machine produced a result is the first thing a person should know
about it (section 6.2). The layout is fixed, so the person learns the shape once. Steps that
did not run on a night are drawn dimmed with their reason, never removed, because
`StepStatus` distinguishes skipped, not applicable and unrecorded, and the difference is
the point.

### 7.2 Live progress

When a job is running, the Record tab shows the current night's graph animating: the
running step pulses, finished steps show a tick and their headline figure, and each result
appears as it lands. The data comes from `get_night_pipeline`, which already reads what
each step wrote. Kotlin polls it once a second while a job runs and stops when the job
ends. The deterministic half completes in well under a second, so it appears almost at once;
the agent half streams because every tool call is written to the audit log as it happens.

If polling proves too coarse for the agent half, the core gains one optional observer hook
in the node binding of `agent/graph.py` (or the loop that replaces it) that records
"step started" with a timestamp to the same table the pipeline view reads. That is the only
core change this section may require, and it is a no-op on the PC.

### 7.3 Replay

A night picker across the top, built from `list_pipeline_nights`. Choosing a night loads
its pipeline and the graph steps through it: play, pause, step forward, step back, with
the current step's sentence shown beneath the graph. Timing between steps is a fixed
cadence for readability, not a claim about how long a step took, and the screen says so.
Where a step recorded `occurred_utc` the real time is shown on the step.

### 7.4 Inspect

Tapping a step opens a sheet: what it did (the `reason` sentence), its headline figure, its
inputs and outputs as labelled rows, its sources with the provenance label, and the layer
statement ("This was arithmetic. Given the same nights it gives the same answer every
time." or "A language model produced this, inside a loop that limits what it may do.").
The wording comes from `ui/explain.py`, moved to a module both the dashboard and the facade
can import so the two surfaces say the same thing.

### 7.5 Lineage

Tapping any output row in a step's sheet highlights on the graph the steps whose outputs it
consumed and the steps that consumed it. The lineage edges are declared once, in the core,
as a static table beside `CANONICAL_PIPELINE_STEPS` mapping each step's named outputs to the
steps that read them. A test asserts every declared input of a step is produced by an
earlier step and that every step is reachable. This table is new, small, and documented in
`docs/CONTRACTS.md`.

### 7.6 How it works, by topic

A second tab within Record keeps the dashboard's "by topic" explainer, with every figure read
from config at render time as it is today, so the two views cannot drift.

---

## 8. State, storage and offline behaviour

- One SQLite database in the app's private files directory, the same schema and migrations
  as the PC. `data/wha.sqlite` on the PC is never touched by the app.
- The corpus lives beside it after the fetch, verified against the SHA-256 in
  `corpus-sources.json` before use.
- Everything except the provider call and the corpus fetch works with no network. If the
  provider is unreachable an investigation waits and the Today screen says so, with the
  time of the last attempt. The monitor and the safety floor are unaffected.
- The webhook being unreachable shows on Today as "no readings since", with the time, and
  on Settings with the last error. Nothing is guessed.
- Uninstalling the app deletes everything. Settings offers "export the record" using the
  existing audit export, so the person can keep it.

---

## 9. Error handling at the boundary

Python exceptions never cross into Kotlin. The facade catches everything, writes the
traceback to the app's log, and returns an envelope naming the kind: `unavailable` (webhook,
provider, corpus), `invalid` (bad input), `internal` (anything else). Screens show each kind
in words with the action available: retry, open Settings, or nothing. An internal error on
a screen shows the error and keeps the rest of the screen usable; the screen never blanks.

---

## 10. Testing and verification

**Python.** The existing suite runs unchanged on the PC with `-n auto`, plus: the import
isolation test (4.1), the embedder agreement test (4.3), the facade-to-API parity test (5),
the lineage table test (7.5), and if the loop replaces langgraph, the existing agent tests
against it.

**Kotlin.** Unit tests for every view model against a fake facade. Compose UI tests for the
Record graph: the twenty-one nodes render, dimmed steps show reasons, tapping a step opens
its sheet, lineage highlights the declared steps.

**On the phone.** Two scripted runs, expected outcomes written before each run and checked
against the screen afterwards:

1. Fresh install against the real webhook: onboarding, corpus fetch, first ingest, the
   status line on Today, thirty days of nights on History with the baseline rung shown
   honestly.
2. A scripted illness from the mock watch on the PC, with the app's data source pointed at
   the PC's address: two red nights open an investigation, the question arrives as a
   notification, "Not now" and an answer both behave as the Telegram path does, the
   escalation stays until acknowledged, the Record tab animates while it runs and replays
   afterwards.

Then, per `AGENTS.md`, drive the app as an ordinary person would and read what every screen
says. A green suite here proves very little.

---

## 11. Toolchain: build on the remote machine, install from the PC

**Decided 10 September 2026 after inspecting both machines.** The owner's laptop cannot
carry an Android toolchain: an i7-10610U, sixteen gigabytes of memory with under two free,
seventeen gigabytes of disk. Nothing Android-related is installed on it or in its WSL.

The owner has SSH access to a shared Linux machine (alias `huawei_blue_1_ppt`, Ubuntu
22.04 in a container, 192 cores, two terabytes of memory, over two terabytes free, glibc
2.35, outbound access to Google's Android repository, PyPI and GitHub confirmed). Every
build happens there. The rules for using it:

- **Only `/home/liangsheng/brian/android` is ours.** Nothing is written outside it. Every
  tool is installed under it in user space: there is no sudo, and none is needed. JDK from
  a Temurin tarball, Android command-line tools with one platform, one build-tools and the
  NDK, Gradle through the wrapper, rustup with the `aarch64-linux-android` target, and a
  uv-managed Python 3.13 for cibuildwheel. `JAVA_HOME`, `ANDROID_HOME`, `GRADLE_USER_HOME`,
  `CARGO_HOME`, `RUSTUP_HOME` and `UV_CACHE_DIR` all point inside that directory, set by a
  single `env.sh` there, never in the shell profile.
- **Other people use this machine.** The load average sits around twenty on 192 cores.
  Builds are run with `nice` and Gradle's worker count capped, never `kill` anything that
  is not ours, never touch the shell configuration, never reboot or restart services, and
  never open listening ports. A Gradle daemon is ours and is stopped after each session.
- **No emulator.** There is no `/dev/kvm` on the remote and no emulator fits the laptop.
  The phone is the only test device, as before.
- **Source travels from the PC, never through the remote's GitHub key.** The remote's SSH
  key authenticates to GitHub as a different account. The repository is private under
  NatBrian, so the remote never clones it. The worktree is synced to the remote with
  rsync over SSH, excluding the database, the corpus and the demo film, and the built APK
  and the wheel files are copied back the same way. The remote holds a working copy, not a
  clone, and nothing is committed from it.
- **Installing on the phone.** The APK is copied from the PC to the phone and sideloaded,
  or installed with adb over USB if the owner enables USB debugging. adb, if used, runs on
  the PC and is the one Android tool installed there; it is small.
- **Secrets.** No provider key, webhook token or database ever goes to the remote. The
  rsync exclude list is committed as `android/rsync-exclude.txt` and a test asserts it
  names `.env`, `data/wha.sqlite`, `data/corpus` and `data/demo_film.sqlite`.

## 12. Documentation obligations this creates

- `docs/CONTRACTS.md`: the facade functions, the error envelope, the lineage table, the
  `android` notifier.
- `docs/DISCLOSURES.md`: every limitation named above, each with the screen that shows it:
  retrieval pending until the corpus arrives; the provider unreachable; the webhook
  unreachable; the replay cadence not being real timing; the webhook app serving without
  authentication on the phone's network interfaces, which is that app's design.
- `README.md`: an Android section pointing at `android/README.md`, which holds the build
  and install steps.
- `USER-GUIDE.md`: a phone section.
- `docs/RESEARCH-AGENTIC-TRIAGE.md` or a new `docs/RESEARCH-HCI.md`: the five sources in
  section 6.1 with what each studied and which rule it justifies.

---

## 13. Risks, stated plainly

| Risk | What is done about it |
|---|---|
| pydantic-core does not build for Android | Section 4.2: stop and return to the owner |
| Chaquopy start-up time with numpy, scipy and pandas makes the first screen slow | Measure on the phone in the spike; if slow, start Python in the background at launch and show Today from cached JSON first |
| Battery cost of a half-hourly job | WorkManager batches; the ingest is one localhost request. Measured on the phone, disclosed in Settings if material |
| The app looks like it does more than it does | Section 6.2 rules, and the disclaimer at first use. Meng 2026 shows dense interfaces read as capability; the calm look is a deliberate counter |
| Two copies of screen wording drift | `explain.py` shared between dashboard and facade, one test comparing them |
