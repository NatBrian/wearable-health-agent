# Wearable Health Agent

> ### NOT THE IMPLEMENTATION SPECIFICATION
>
> **If you are a coding agent, stop and read `history/HANDOFF.md` instead.**
>
> This is a narrative design document, written *before* the implementation plan. It is out of date
> in fourteen specific, documented ways: it names a probabilistic-graphical-model library that was
> dropped, a measurement type that has no data path, a backfill mechanism that was ruled out, and a
> policy formulation that was replaced. Every one is catalogued in `history/plan/04-decisions.md` Part B.
>
> **The implementation contract is `history/plan/`.** Where this document and `history/plan/` disagree, `history/plan/`
> wins, always. Building from this file will produce the wrong system.

---


### An agentic differential-triage system that answers the one question wearables cannot: *am I getting sick, or do I just need rest?*

**Document type:** design specification and project proposal
**Status:** design frozen, implementation not started

---

## 1. Summary

Consumer wearables detect that something in your body has changed. None of them can tell you why. A raised overnight heart rate is produced by an incubating infection, by alcohol, by a hard training session, by poor sleep, by stress, by a vaccination, or by the luteal phase. They look nearly identical to a wrist sensor and they demand opposite responses.

The measured consequence is a positive predictive value around **4%**, roughly twenty-four false alarms for every true one, of which about **45% had a cause a single question could have resolved**.

**Wearable Health Agent** is a bounded agent that investigates each flagged deviation. It maintains an explicit probability distribution over twelve candidate causes, decides by expected information gain whether interrupting the user is worth it, conducts a short adaptive interview when it is, **can instruct the user to take a specific measurement on their watch**, grounds every clinical claim in a retrieved source, and terminates at a typed disposition. Red flags bypass the model entirely via deterministic code.

| | |
|---|---|
| **Detection** | Personal baseline, multi-signal concordance, multi-night persistence. No AI in the numeric path |
| **Reasoning** | Hand-specified Bayesian network with literature-cited priors. **Nothing is trained** |
| **Decision** | Expected information gain versus interruption cost, explicit arithmetic outside the LLM so it can be measured against never-ask and always-ask baselines |
| **Language** | LLM for extraction, question phrasing and explanation only. It never computes a number or decides an action |
| **Grounding** | Hybrid retrieval over a small curated clinical corpus, with claim-to-source enforcement |

**What is novel:** every component has shipped somewhere. Google's Loss of Pulse asks the user and escalates on silence. Ultrahuman's Jade orders a confirmatory measurement. Adaptive testing is deployed across healthcare. **No shipped product assembles them.**

One preprint does connect a deviation to an LLM-generated question with a Bayesian update: *Project Hermes* (arXiv:2602.18643, Feb 2026), reporting a false positive rate falling from 61.7% to 12.5% at 89% sensitivity on migraine prediction. It is prior art for the mechanism and is cited as such. What it does not do is **decide whether asking is worth the interruption at all.** Hermes validates an alert that has already fired. This system computes the expected information gain of each candidate question against a quantified interruption cost and an explicit budget, and can choose to stay silent. It also orders measurements, escalates, and returns a source-grounded differential, where Hermes explicitly performs validation rather than diagnosis. **The novelty is the decision layer and the action space, not the act of asking.**

---

## 2. The healthcare problem

### 2.1 The problem in one paragraph

Consumer wearables have become good at noticing that something in your body has changed, and remain unable to tell you why. A raised overnight heart rate is produced by an incubating infection, by three drinks, by a hard training session, by a bad night's sleep, by exam stress, by a vaccination, and by the luteal phase of the menstrual cycle. These look nearly identical to a wrist sensor, yet they demand opposite responses: rest and isolate, or carry on as normal. The result is a stream of alerts that are usually wrong, which users learn to ignore, at which point the genuinely important alert is ignored too.

### 2.2 Who is affected

**Directly:** anyone wearing a smartwatch or ring with health monitoring. Within that group the problem bites hardest for:

- **Students and shift workers**, whose sleep and stress patterns generate constant deviations. In one 525-student cohort, 64% of weekly responses reported moderate-to-high stress, and stress raises resting heart rate and respiratory rate while lowering heart rate variability, which is the same direction as infection.
- **Athletes and regular trainers**, for whom hard training and illness are the two candidate explanations for poor recovery, requiring opposite responses. Evening training raises resting heart rate by roughly 5.94 bpm, while acute respiratory infection raises it by only 1.1 to 2.1 bpm. **The confounder is larger than the signal.**
- **People who live or work with vulnerable others**, for whom a 24 to 48 hour warning genuinely changes behaviour.
- **Menstruating users**, who face the worst case of all: in the luteal phase, wrist temperature, heart rate, respiratory rate and heart rate variability all move in the infection direction, on roughly 45% of days.

**Intended users of our system:** individual adults who already own a compatible wearable and want an explanation rather than an alarm. This is a consumer wellness and self-triage tool, not a clinical device.

### 2.3 Why it matters

**The precision problem is measured, not hypothetical.** An independent prospective evaluation of a wearable illness-detection system (Northwell Health with Fitbit, JMIR 2024) issued **665 alerts across 470 participants and achieved a positive predictive value of 4%**, roughly twenty-four false alarms for every true one. The authors attributed the false alerts by cause: **stress 16.0%, poor sleep 13.7%, exercise 9.7%, alcohol 6.0%.** Approximately **45% of false alerts had a cause that a single question could have resolved.**

Independently, a deployed 3,318-participant smartwatch alerting study recorded **1.15 non-illness alert-days per person per 21 days**, roughly twenty spurious alert-days per person-year, and its authors explicitly listed the triggers as stress, alcohol, intense exercise, travel, poor sleep, vaccination and altitude.

**Alarm fatigue is a documented patient-safety problem, not an inconvenience.** In hospital monitoring, one study logged 2,558,760 alarms over 31 days across 77 beds, roughly 187 audible alarms per bed per day, with **88.8% of annotated arrhythmia alarms false**. The Joint Commission's Sentinel Event Alert 50 records 98 alarm-related events including 80 deaths, and states that between 85 and 99 percent of alarm signals do not require clinical intervention. The mechanism that makes clinicians tune out monitors is the same mechanism that makes consumers uninstall health apps.

**The upside of solving it.** Better self-triage decisions (rest, hydrate, isolate, or seek care), fewer avoidable primary-care visits for self-limiting illness, earlier care-seeking when it genuinely matters, and a monitoring tool people keep using rather than abandon. In Singapore, where one in four residents will be aged 65 or over by 2030 and the binding healthcare constraint is workforce capacity rather than knowledge, tools that help people triage themselves correctly reduce demand on a system that cannot easily add supply.

### 2.4 What already exists, and why it is not enough

Existing products are the evidence that this problem is real and that our approach is sound. Each has solved part of it, and each stops at the same wall.

| Existing solution | What it does well | Where it stops |
|---|---|---|
| **Samsung Health "Vitals"** (June 2026) | Analyses five overnight bio-signals (heart rate, HRV, respiratory rate, skin temperature, blood oxygen) against the user's own resting baseline, uses ML to detect statistically significant deviations, and notifies only on meaningful change | Its own marketing states it helps the user *"better determine whether you are fighting an illness or just need more rest."* **It does not determine that.** It notifies and leaves the user to guess, because it never acquires the information that would separate the two |
| **Oura Symptom Radar** | Three-tier illness signal (no signs / minor signs / major signs), on-device inference, personalised baseline over 7 nights in 14 | Gives a tier with no reasoning, no evidence, and no way to tell it "that was just a hangover" |
| **WHOOP Health Monitor and Journal** | Gradient-boosted classifier on a 21-day baseline; a daily journal that asks about behaviours | The journal is **unconditional**: it asks the same questions every morning whether anything happened or not. Burden without relevance, which is why people stop answering |
| **Apple Watch Vitals** | Elegant multi-signal rule: alert only when at least two of five metrics are outliers together. Silent, zero user burden | Its own notification text lists the likely causes, naming *"medications, elevation, alcohol intake, or even illness"*, **and then asks the user nothing** |
| **Symptom checkers** (Ada, NHS 111 online, Babylon) | Structured clinical questioning that produces a real differential | **Completely blind to your physiology.** They start from zero every time and cannot know your heart rate has been elevated for three nights |
| **Google Loss of Pulse Detection** (FDA-cleared) | The one shipped feature that responds to an anomaly by **asking the user**, and escalating autonomously if there is no answer | Scoped to cardiac arrest only |
| **Ultrahuman "Jade"** | Responds to anomalies by **triggering a confirmatory measurement** rather than giving advice | Scoped to specific cardiac checks |
| **Project Hermes** (arXiv:2602.18643, preprint) | The closest prior art. LLM-generated contextual queries plus Bayesian updating, as a validation layer downstream of any predictor. Reports 61.7% to 12.5% false positive rate at 89% sensitivity on migraine | **Asks whenever an alert fires**, with no model of whether the question is worth the interruption. Validation only, explicitly not diagnosis, and no measurement or escalation actions. Single author, no released code, one condition |

**The gap, stated precisely:**

> Physiological monitors detect but never ask. Symptom checkers ask but never measure. Journals ask unconditionally, so people stop answering. **No shipped product connects a detected physiological deviation to a targeted question capable of resolving it, and then to a grounded explanation.**

Every component needed to close that gap has been proven in a shipped product. **No shipped product assembles them.**

One preprint assembles part of it. *Project Hermes* connects deviation to LLM-generated question to Bayesian update, and reports that it works. It stops before the two things that make this a decision problem rather than a validation problem: **it does not weigh the question against the cost of asking**, and it does not act on the answer beyond adjusting a confidence. See `research/15-project-hermes-read.md`.

### 2.5 Scope of claims: what the system can and cannot determine

This section defines the project's limits precisely, because those limits determine the model selection in 4.5 and the agent's action space in Question 3. Getting it wrong in either direction produces either an unsafe system or a pointless one.

#### 2.5.1 The most important correction: this is detection, not prediction

The system does **not** predict future illness. It detects a physiological change that has **already begun** but that the user has not yet noticed. Published "lead time" in this field is the gap between physiological onset and **symptom awareness**, not between now and a future infection.

We therefore claim early **detection**, never prediction. Saying otherwise would be both wrong and unverifiable.

#### 2.5.2 What it can determine, by strength of evidence

| # | Claim | Evidence strength | Requires |
|---|---|---|---|
| 1 | *"Your physiology has deviated from your own normal, starting roughly N nights ago"* | **Strong.** This is what every shipped product does | Sensors only |
| 2 | *"This deviation is fully explained by a recorded event"* (a hard workout, very short sleep) | **Strong.** The watch already records the cause | Sensors only |
| 3 | *"There is systemic strain consistent with immune activation"* | **Strong but non-specific.** Deployed systems reach roughly 80% sensitivity with a 3-day median lead. It detects the body's general response, not a pathogen | Sensors only |
| 4 | *"This is more likely alcohol / training / stress / poor sleep than illness"* | **Moderate.** This is the project's contribution and is exactly what requires asking | Sensors **plus one or two answers** |
| 5 | *"Given your symptoms, the likely category is an upper respiratory infection / a febrile illness needing same-day review / something else"* | **Moderate.** Symptoms carry the discriminating information sensors lack | Sensors **plus a short interview** |
| 6 | *"You are in an active dengue cluster, which raises that possibility for this symptom pattern"* | **Moderate.** Live local disease activity legitimately shifts the prior | Sensors, symptoms, **location** |
| 7 | *"This requires clinical attention now"* | **Strong, by design.** Deterministic red-flag rules, deliberately over-sensitive | Either |

#### 2.5.3 What it cannot determine, stated plainly

| # | Cannot | Why, at the level of mechanism |
|---|---|---|
| 1 | Distinguish influenza from COVID-19 from RSV from a common cold **using sensors** | All produce the same autonomic and inflammatory host response. The information is not in the signal, and no model recovers information that was never measured |
| 2 | Distinguish bacterial from viral **using sensors** | Same reason. Symptom-based rules such as Centor help, and only partially |
| 3 | Give a definitive diagnosis | Wearables have no assay. Output is a ranked differential with explicit uncertainty |
| 4 | Predict illness before physiological change begins | See 2.5.1. There is nothing to observe yet |
| 5 | Detect illness with no systemic autonomic signature | Most cancers, musculoskeletal injury, most mental-health conditions, and localised infections without fever are invisible to these sensors |
| 6 | Work reliably on daytime data | Motion, posture, meals and stress dominate. The usable signal is the nocturnal window |
| 7 | Work without roughly 2 to 4 weeks of personal history | The entire method is deviation from *your* baseline. A new user gets nothing until a baseline exists |
| 8 | Work when the watch is not worn | Missing nights are refusals, not guesses |
| 9 | Separate a first-night hangover from a first-night infection **without asking** | The channels move identically and by comparable magnitudes. This is the identifiability limit that motivates the whole project |
| 10 | Make population-level or clinical-validity claims | Two participants over two weeks, with detection metrics from public cohorts |

#### 2.5.4 The conditions actually in scope

The published evidence base for wearable early detection is almost entirely **acute systemic illness with an inflammatory or autonomic signature**. In scope:

- **Acute viral respiratory infection** (the well-evidenced case)
- **Acute febrile illness generally**, including **dengue**, which is endemic in Singapore and shares the systemic signature
- **Vaccination reactogenicity**, which is the same immune pathway and is a useful positive control because its timing is known

Explicitly out of scope: chronic disease management, cancer, cardiac arrhythmia (a regulated, separately cleared function), mental-health conditions, and injury.

---

---

## 3. The agentic AI approach

### 3.1 What the agent is for

**The monitor is not the agent.** Detecting a deviation is cheap, deterministic and continuous, and it is not an agentic problem. It is a sensor.

**The agent is the investigation.** When a deviation is flagged, an agent is instantiated with a bounded goal: *determine the most probable explanation for this deviation, acquiring only the evidence that is worth acquiring, and reach a disposition.* It then reasons over multiple days, decides its own next actions, and terminates when it reaches a conclusion or hits a guardrail.

This is the distinction the course draws between a workflow and an agent: **the next action genuinely depends on the ambiguity of the intermediate result**, and is not knowable in advance.

### 3.2 Goal and guardrails, set by the human

**Goal (set by the user at setup):**
- Bounded objective: explain each flagged physiological deviation and reach a disposition.
- Success criterion the agent can test: a disposition is assigned from a closed set, with every claim source-linked.
- **Two interaction budgets**, both user-configurable, because they control different things:
 - **Interruption budget (default 2 per week):** how often the agent may open an unprompted conversation. This is the strict one, and it is what the information-gain policy spends.
 - **Depth budget (default 5 per conversation):** how many follow-up questions a single conversation may run to, once the user has answered the first one. Answering is treated as opting in.

 The evidence supports this split: compliance studies find prompt *frequency* is a weak predictor of drop-off, while habituation to repeated unprompted alerts is the documented failure. Users tolerate depth; they do not tolerate frequency.

**Guardrails:**

| Guardrail | Specification |
|---|---|
| **Scope** | One user's own data only. Read-only. No access to any other person's records |
| **Authority** | The agent **drafts**. It may never commit an action that reaches anyone but the user. It cannot book appointments, message clinicians, or alter records |
| **Thresholds** | Red-flag vitals and red-flag symptoms trigger deterministic escalation that bypasses the model entirely |
| **Traceability** | Every action logged with input, action, source, timestamp, output and human decision |
| **Self-expansion** | Denied. The agent cannot request or grant itself broader data access. Attempts are logged and counted |

### 3.3 The Perceive, Reason, Act loop

**PERCEIVE.** Ingest last night's signals. Compute derived features (nocturnal resting heart rate, HRV, respiratory rate, sleep architecture, activity load). Assess data quality and coverage; insufficient coverage produces an explicit refusal rather than a guess.

**REASON.** Three sub-steps, following the course's decomposition.
- *Interpret:* compare against the user's personal baseline and against a forecast of what tonight should have looked like. Subtract deviation already explained by events the watch recorded automatically (a workout, an unusually short night). Nothing is manually logged by the user, which is why alcohol and stress cannot be subtracted this way and must be asked about instead.
- *Decide:* select the next action. This is the core of the system and is described in 3.4.
- *Judge and check:* test the candidate conclusion against guardrails, red-flag thresholds, and whether every claim has a source.

**ACT.** Execute one of five actions:

| Action | Description |
|---|---|
| `OBSERVE` | Stay silent, log, and wait for another night of evidence |
| `ASK(question)` | Pose one targeted question to the user |
| `MEASURE(test)` | **Instruct the user to take a specific measurement on their watch** |
| `ESCALATE(level)` | Surface a warning, or direct the user to seek clinical care |
| `CONCLUDE(disposition)` | Terminate the episode with a disposition and a grounded explanation |

### 3.4 The decision the agent actually makes, and why it is not a threshold

The central autonomous decision is **whether interrupting the user is worth it.** The agent maintains an explicit probability distribution over **twelve** candidate causes:

```
infection-like immune activation alcohol acute exertion / DOMS
acute sleep restriction psychological stress luteal phase
recent vaccination travel / altitude medication change
illness recovery tail sensor artifact unexplained
```

For each candidate question, it computes the **expected information gain**: how much the answer would be expected to sharpen that distribution. It asks only when the expected gain exceeds the cost of interrupting, in the form given by Horvitz, Jacobs and Hovel's *Attention-Sensitive Alerting* (UAI 1999), which alerts only when net expected value is positive and was deployed as the PRIORITIES system.

Two properties matter.

**First, the agent must be able to conclude that no question is needed.** If the watch already recorded a hard workout that fully explains the deviation, asking is pure burden. A policy that can stay silent as readily as it can ask is the thing with value.

**Second, this decision is deliberately not made by the LLM.** It is explicit arithmetic over a small discrete space (12 causes by roughly 8 questions by roughly 4 answers, a few hundred multiply-adds, microseconds). This makes the policy **auditable and measurable**: we can compare it directly against never-ask, always-ask, and fixed-threshold baselines. An LLM told to "ask if unsure" can be demonstrated but not evaluated.

### 3.5 Why this is agentic and not a chatbot

| Property | How this system exhibits it |
|---|---|
| **Initiates** | The user never opens an app to start it. It wakes itself when a deviation is detected |
| **Plans** | Fixes its investigation plan before retrieving any external content, then executes |
| **Holds state across waits** | An episode spans several nights, pausing for the user to answer or take a measurement. State persists across days |
| **Uses tools** | Typed, enumerated, least-privilege tools over feature stores, personal history, and the knowledge base |
| **Acts in the world** | Can instruct a physical measurement to be taken, changing what evidence exists rather than only reasoning about existing evidence |
| **Coordinates multiple actions** | Retrieve history, compute, retrieve evidence, ask, wait, re-measure, re-reason, conclude |
| **Terminates** | A typed disposition, not an open-ended conversation |

A chatbot answers when spoken to. **This system decides whether to speak at all, and can order a test before it answers.**

### 3.6 Tools, data sources and knowledge repositories

**Agent tools (typed, validated, read-only unless stated).**

> **These are provisional and will change.** They are derived from the decision loop, not from the ingested data schema, which we have not yet inspected. Three things will revise them: what the Galaxy Watch export actually contains, which data types Samsung Health actually populates in Health Connect, and what the belief model turns out to need. We specify them now anyway, because **tool scope is itself a governance deliverable**: the set of things the agent may do, and the tier of each, is what bounds its authority, and that argument does not depend on the final field names. Expect the list to grow by roughly a third once the data structure is known, most likely with data-quality, episode-state and interaction-budget accessors.

| Tool | Returns | Control tier |
|---|---|---|
| `get_nightly_features(date_range)` | Derived nightly metrics | T1 |
| `get_personal_baseline(metric)` | Rolling median and dispersion | T1 |
| `get_known_events(window)` | Recorded workouts, sleep, prior answers | T1 |
| `find_similar_past_episodes(pattern)` | The user's own comparable past episodes and their outcomes | T1 |
| `retrieve_clinical_evidence(query)` | Passages with source identifiers | T1 |
| `request_measurement(type)` | Issues an instruction to the user | T2 (draft/pend, user must consent) |
| `ask_user(question)` | Poses one question | T2 |
| `check_red_flags(state)` | Deterministic safety verdict | T1, always runs |
| `get_local_disease_activity(location)` | Live NEA dengue cluster status and air quality for the user's area | T1 |

`COMMIT`-tier actions are denied entirely. There is no tool that writes to any external system.

**Data sources.** Three sources with three distinct jobs. Keeping them separate is deliberate: it is what lets us develop fast, evaluate credibly, and demonstrate honestly, without any one of the three having to do a job it is bad at.

| Role | Source | Why this one |
|---|---|---|
| **Build and test** | **Synthetic / mock data**, generated by us | Fast, repeatable, fully controlled. We inject a known deviation on a known night and assert that the detector fires, the belief updates, the interview branches and the safety layer intercepts. This runs in CI on every change and needs no wearable, no illness and no waiting |
| **Prove it works** | **Public cohorts:** Stanford for detection, PMData for the asking policy | Real people, real illness episodes, real self-reported alcohol, training and stress. This is where credible numbers come from. **Ground truth we did not invent** |
| **Demonstrate** | **A team member's own Galaxy Watch 5 data** | The system running on a real person's real physiology. Qualitatively different from running on numbers we generated |

**Note on what synthetic data may and may not be used for.** It is a development and regression-testing tool only. **No performance claim in this project rests on synthetic data**, because a result obtained on data we generated from our own assumptions only demonstrates that we can recover our own assumptions. Reported detection and policy results come from the public cohorts.

**Specifics:**
- **Wearable, live:** Samsung Galaxy Watch 5, reaching us automatically via Samsung Health, then Android Health Connect, then the **Health Connect Webhook** app (AGPL-3.0, installed from the Play Store, no app to build). It exposes 31 data types including HRV, respiratory rate, skin temperature, resting heart rate, blood oxygen and sleep stages, either by pushing to a webhook or through a local HTTP server on port 8787 that our code polls over Wi-Fi. Sync modes are interval (15 minutes minimum), scheduled, or manual. **Because Health Connect is the aggregation point for Samsung Health, Fitbit and Google Fit, device portability comes for free rather than being engineered.**
- **Wearable, history:** a one-time Samsung Health export at onboarding. **Required rather than optional**, because the live bridge only exposes a rolling 48-hour window while a personal baseline needs 2 to 4 weeks. Export bootstraps history; the bridge keeps it current.
- **Public cohort data for evaluation:** the Stanford COVID-19 Wearables dataset (open download, 2,123 participants) for detection performance, and **PMData** for confounder attribution. **Verified at source 2026-08-31**, not taken from secondary reporting: 16 participants over 5 months, **CC BY 4.0** (attribution only, no non-commercial restriction), 1.4 GB, hosted by SimulaMet with an OSF mirror. The files the evaluation depends on are:

| File | Contents relevant to us |
|---|---|
| `reporting.csv` | Daily meals, weight, **glasses drunk and an alcohol-consumption indicator** |
| `wellness.csv` | Daily **fatigue, mood, readiness, sleep duration, sleep quality, soreness and stress**, each on a 1 to 5 scale |
| `srpe.csv` | **Training sessions with rating of perceived exertion and duration** |
| `resting_heart_rate.json` | Resting heart rate **per day**, which is the exact quantity our detector operates on |
| `heart_rate.json`, `sleep.json`, `sleep_score.csv`, `steps.json` | Per-minute heart rate, sleep stage breakdown, a 0-100 sleep score, per-minute steps |

This matters because it confirms the simulated oracle can answer with **real human self-reports** rather than values we invented. Alcohol, training load, stress and sleep quality, the four causes that accounted for roughly 45% of false alerts in the field, are all present and all daily.

**Knowledge repositories for retrieval:**
- **MedlinePlus** (US National Library of Medicine): bulk XML, approximately 29 MB, updated daily, attribution-only licence.
- **StatPearls via NCBI Bookshelf**: peer-reviewed clinical reference articles.
- **CDC and WHO** guidance on illness timelines and when to seek care.
- **Published clinical decision rules**, notably the **Centor / McIsaac criteria** for pharyngitis, which turn a guess into a citable rule.
- **A quantitative confounder table** we compile from peer-reviewed sources, giving the direction, magnitude, onset and duration of each candidate cause. This is the evidence base for the probability model, and every entry carries a citation.

---

## 4. The prototype

### 4.1 What we will demonstrate

A working system that ingests real wearable data, detects deviations, runs the bounded agent loop with its reasoning visible, conducts an adaptive interview, instructs a watch measurement, retrieves and cites clinical evidence, produces a grounded differential with calibrated uncertainty, escalates red flags deterministically, and writes a complete audit log.

Developed against synthetic data for speed and repeatability, evaluated on public cohorts of people who genuinely fell ill, and demonstrated on a team member's own Galaxy Watch 5 data. The three roles are kept separate and no claim rests on the synthetic data.

### 4.2 Main features

Grouped by layer, with build priority. **MUST** items are the system; **SHOULD** items make it credible; **COULD** items are the cut list, in the order they get dropped.

| # | Feature | Layer | Priority |
|---|---|---|---|
| F1 | **Automatic continuous ingestion** from the Galaxy Watch 5 via Health Connect, polled over the local network. Device-agnostic by construction, since Health Connect aggregates Samsung Health, Fitbit and Google Fit | Data | MUST |
| F2 | **One-time historical backfill** from the Samsung Health export. Required, not optional: the live bridge exposes only a 48-hour window, while a personal baseline needs 2 to 4 weeks. Includes a defined **cold-start state**: with fewer than 14 usable nights the system reports `INSUFFICIENT_DATA` and explains that it is still learning the user's normal | Data | MUST |
| F3 | Data-quality gate: coverage, non-wear and implausible values produce a **refusal**, not a guess | Data | MUST |
| F3b | **Synthetic data generator** producing realistic nightly series with injectable deviations, confounder events and missingness, used for development and regression testing only | Data | MUST |
| F4 | Personalised baseline per signal (rolling median and dispersion, sick nights excluded) | Detect | MUST |
| F5 | Deviation detection by multi-signal concordance plus multi-night persistence | Detect | MUST |
| F6 | Expected-range forecast from Chronos, compared against actual | Detect | SHOULD |
| F7 | Explained-variance subtraction: remove deviation already accounted for by an **automatically recorded** event (workout, short sleep). Alcohol and stress are **not** recorded by any device, which is precisely the gap the questions exist to fill | Detect | MUST |
| F8 | Explicit belief state over twelve candidate causes, updated as evidence arrives | Reason | MUST |
| F9 | Information-gain policy deciding whether to ask, able to conclude "no question needed" | Reason | MUST |
| F10 | Adaptive interview: single-tap answer options with an optional free-text box, each answer selecting the next question | Reason | MUST |
| F11 | Watch measurement request, then re-reason on the result | Act | MUST (the distinguishing feature) |
| F12 | Retrieval over the layered corpus, with claim-to-source linking | Ground | MUST |
| F13 | Live local disease activity (NEA dengue clusters) as a prior-shifting tool | Ground | COULD |
| F14 | Self-critique pass before anything is shown to the user | Ground | SHOULD |
| F15 | Deterministic red-flag interception, outside and above the model | Safety | MUST |
| F16 | Human checkpoint: approve, edit, reject, escalate | Safety | MUST |
| F17 | Audit log with input, action, source, timestamp, output, human decision | Govern | MUST |
| F18 | Visible reasoning trace: planning, state transitions, tool calls | Govern | MUST |
| F19 | Counterfactual projection ("if you rest today versus train today") | Extra | COULD |
| F20 | Second device vendor, demonstrating portability. **Now near-free**: Health Connect already aggregates Fitbit and Google Fit, so adding a second device is granting permissions in the same bridge app rather than writing an adapter. Contingent only on a teammate having a compatible device | Extra | SHOULD if a device is available |

#### 4.2.1 System shape

```
 Galaxy Watch 5
 | automatic sync
 v
 Samsung Health --> Health Connect --> HC Webhook app (local HTTP :8787)
 | |
 | one-time export (history, 2-4 wks) | polled / pushed
 +------------------+-----------------------+
 |
 v
 +----------------------------------------------------------+
 | NIGHTLY BATCH (deterministic, local CPU, no LLM) |
 | F3 quality gate -> F4 baseline -> F5 concordance |
 | F6 forecast gap -> F7 subtract explained variance |
 +----------------------------+-----------------------------+
 |
 deviation flagged?
 NO --> log, sleep, no LLM call, cost = 0
 | YES
 v
 +----------------------------------------------------------+
 | F15 RED-FLAG INTERCEPT (plain code, runs first, always) |
 | crossed --> escalate, bypass the model entirely |
 +----------------------------+-----------------------------+
 | not crossed
 v
 +----------------------------------------------------------+
 | EPISODE AGENT (bounded, LangGraph, the only agentic bit)|
 | |
 | F8 belief state <--------------------+ |
 | | | |
 | v | new evidence |
 | F9 information-gain policy | |
 | | | |
 | +----+--------+-----------+---------+ | |
 | | | | | | |
 | OBSERVE F10 ASK F11 MEASURE CONCLUDE |
 | | | | | | |
 | +------------+-----------+----------+--+ |
 | | |
 | F12 retrieve + F14 self-critique |
 +----------------------------+-----------------------------+
 v
 F16 human checkpoint -> F17 audit log -> F18 trace
```

**Two things this makes visible.** The LLM sits inside one box only, and is never touched on a quiet night. And the red-flag path sits upstream of the agent, so it cannot be reasoned past.

#### 4.2.2 What the system emits

Every episode terminates in one structured, schema-validated object. This is the contract the whole system exists to produce.

```
EpisodeOutcome:
 episode_id, opened_on, closed_on
 disposition one of: EXPLAINED_BY_EVENT | LIKELY_ILLNESS |
 LIKELY_BENIGN | ESCALATED |
 UNRESOLVED | INSUFFICIENT_DATA
 observation which signals moved, by how much, against whose
 baseline, over how many nights
 differential ranked causes, each with a probability plus
 supporting and contradicting evidence
 evidence_used sensor findings, user answers, measurement results
 ruled_out what was eliminated, and by which piece of evidence
 citations every clinical claim -> source id + passage
 unsupported_claims count of statements stripped for having no source
 action rest | monitor | seek same-day care | seek urgent care
 escalation_criteria explicit "come back or see someone if X"
 confidence calibrated, with an explicit "cannot determine" option
 questions_asked interruptions used this week, and depth used
 in this conversation, against both budgets
```

`INSUFFICIENT_DATA` is a first-class outcome, not an error. A system that knows when it cannot speak is part of the design.

#### 4.2.3 Episode lifecycle, and what triggers what

An **episode** is the unit of work: one investigation of one deviation, spanning one or more nights.

| State | Meaning | Leaves when |
|---|---|---|
| `OPEN` | Deviation flagged, investigation running | The agent acts |
| `AWAITING_USER` | A question has been asked | An answer arrives, or timeout |
| `AWAITING_MEASUREMENT` | A watch reading has been requested | The reading syncs, or timeout |
| `AWAITING_HUMAN_REVIEW` | Conclusion drafted, sitting at the checkpoint | User approves, edits or rejects |
| `CLOSED` | Disposition assigned | Terminal |

**Triggers, which is what an implementation plan actually needs:**

| Trigger | Fires | Runs |
|---|---|---|
| Nightly batch | Once per day after sync | Quality gate, baseline, detection. **No LLM** |
| Deviation flagged | From the batch | Red-flag check, then open or resume an episode |
| User answers | Whenever they reply | Resume episode, update belief, re-decide |
| Measurement arrives | On sync | Resume episode, update belief, re-decide |
| Timeout | No reply within N hours | Resume and proceed without the answer, or close as `UNRESOLVED` |
| Human decision | At the checkpoint | Record and close |

**Three stop conditions, composed:** a disposition is reached (semantic, and the real one); an iteration cap is hit (safety net); or a wait deadline expires, closing as `UNRESOLVED` or `INSUFFICIENT_DATA`.

**Non-response is a designed path, not a failure.** The agent must reach a sensible disposition without an answer, because much of the time it will not get one.

#### 4.2.4 What the user actually sees

Five surfaces, and only two are ever pushed to the user.

| Surface | Pushed? | Contains |
|---|---|---|
| **Silent log** | No | Every night's assessment, including the many where nothing happened |
| **A question** | **Yes** | One question as single-tap options, plus an optional free-text box, plus a "not now" option |
| **A measurement request** | **Yes** | What to measure, why, and what it would rule in or out |
| **Episode outcome** | On open | The differential, the evidence, the sources, the action, the escalation criteria |
| **Trace and audit view** | No | Reasoning trace and full audit log. Primarily for the demonstration and the report |

**Design stance: the system is silent by default.** On most nights the correct behaviour is to log and say nothing.

#### 4.2.5 Demonstration strategy

**The demonstration is a time-warped replay of a real recorded episode, scripted and rehearsed.** This is a deliberate decision, not a fallback.

Three reasons. The presentation slot is ten minutes **including setup and Q&A**, so a realistic budget for the demo itself is three to four minutes. A real episode spans several nights, which cannot be shown at natural speed at any point. And the watch-measurement step requires the reading to sync through Samsung Health before our code can see it, which introduces a wait of minutes that we do not control and cannot risk on stage.

We will state plainly during the demonstration that it is replay of **real data from a real person**, not simulation. Live ingestion will be shown as a separate, brief artefact (data arriving from the watch) rather than as a dependency of the narrative.

**What the demonstration actually shows.** Two things side by side, both real. A replayed illness episode from a public cohort, where a real person genuinely fell ill, to show the full loop end to end including detection, questioning, measurement and a grounded conclusion. And the system running on a team member's own live watch data, showing correct behaviour on a real person in real time.

This pairing removes a dependency we cannot control. **Nobody on the team needs to fall ill on schedule for the demonstration to work**, because the illness episode comes from the cohort while the personal data proves the system runs on a real wrist. If the fortnight happens to be uneventful, the personal half correctly shows a system staying silent, which is the right behaviour rather than a failed demo.

**Note that the measurement loop does work live.** The bridge app has a manual sync control, so the round trip of "take a reading now" to the result reaching our code is about a minute rather than hours. We keep replay as the rehearsed path because a ten-minute slot has no room for anything that can fail, not because the live loop is infeasible.

### 4.3 Expected workflow

**Tuesday.** Resting heart rate 58 against a personal baseline of 52. The watch recorded a hard workout at 20:00, which fully explains a rise of that size. The agent logs it and **stays silent.** No LLM is invoked.

**Wednesday.** Still elevated, no workout recorded. Concordance rule satisfied: heart rate and respiratory rate both outside their personal bands, two nights running. The agent wakes.

It retrieves the user's own history and finds a comparable past episode. It computes the belief state: alcohol, stress, sleep debt, and early infection are all plausible. It computes expected information gain and determines that one question would meaningfully change the conclusion, and that the interruption budget allows it.

**It asks one question**, presented as single-tap options (had a drink / trained hard / slept badly / feeling unwell / none of these) with an optional text box. The user taps *feeling unwell* and adds: *"a bit rough, throat hurts."*

The LLM extracts structured facts. The belief state updates sharply toward infection. The agent now conducts a **short adaptive interview**: cough, fever, onset timing, each question chosen by the same information-gain rule.

**It requests a measurement:** a one-minute stress and HRV reading on the watch. The result arrives and the belief updates again.

**It retrieves evidence** for the resulting symptom pattern, including the Centor criteria for sore throat.

**It critiques its own conclusion**, checking for contradicting evidence and unsupported claims. Unsourced statements are stripped and counted.

**It concludes** with a disposition, a ranked differential with probabilities, the specific observations that drove it, the sources, and an action, together with explicit criteria for when to see a doctor.

**Red-flag path.** Had the user reported chest pain or breathlessness, or had vitals crossed hard thresholds, deterministic code would have escalated immediately without invoking the model at all.

### 4.4 Technology stack

| Layer | Technology | Rationale |
|---|---|---|
| **Data ingestion** | **Health Connect Webhook** (AGPL-3.0, on the Play Store) bridging Samsung Health via Android Health Connect, plus a one-time Samsung Health export for history | Automatic and continuous with no app to build. Health Connect is the aggregation point for Samsung Health, Fitbit and Google Fit, so multi-device support is free rather than engineered |
| **Storage** | SQLite, local file only | Local-first. No server, no external database. Health data does not leave the machine |
| **Feature extraction and detection** | Python, pandas, NumPy | Deterministic, microsecond, auditable. No AI in the safety-critical numeric path |
| **Models** | See the model inventory in 4.5 | **Four models, none trained.** One pretrained forecaster, one hand-specified belief network, one pretrained embedding model, one pretrained LLM |
| **Belief state** | **pgmpy** discrete Bayesian network | Auditable arithmetic. The LLM never computes a probability |
| **Decision policy** | Custom, expected information gain versus interruption cost | A few hundred operations over 12 causes. Comparable against never-ask, always-ask and threshold baselines |
| **Agent orchestration** | **LangGraph** with SQLite checkpointer, plus LangChain's `HumanInTheLoopMiddleware` | Checkpointer gives state across multi-day waits; `interrupt()` gives the human gate; its `allowed_decisions` are literally approve, edit, reject, respond. The graph renders as a diagram for the report |
| **LLM hosting** | See 4.5.3 | **Ollama on Kaggle 2x T4**, exposed to the local machine as an OpenAI-compatible endpoint over a Cloudflare tunnel behind a bearer-token proxy. Verified working, see 4.5.3 |
| **Retrieval** | See the RAG design in 4.6 | Hybrid BM25 plus dense, fused by reciprocal rank fusion. Reranking excluded, see 4.5.2.1 |
| **Structured output** | **Pydantic** schema validation on every agent step | "Machine-checkable outputs". Validation failure is a handled event |
| **Interface** | **Streamlit** | Maximises time on the agent rather than on front-end plumbing, while making planning, state transitions, tool calls and the audit log visible |
| **Observability** | **Langfuse** (self-hostable, free) or OpenTelemetry GenAI conventions | Per-run cost and latency instrumentation, and a visible trace |
| **Testing** | pytest, plus a **frozen scenario suite with cached and replayed LLM responses** | Makes every number re-derivable offline and keeps the evaluation inside free-tier rate limits |

### 4.5 Model inventory

**Four models, none of them trained**, plus ordinary statistics for the detector. Each has exactly one job. Every one must justify itself through the ablation in 4.7; any that does not is reported as not earning its place.

#### 4.5.1 A hard constraint: we train nothing

**No component of this system is trained.** Every model is used pretrained and zero-shot, or is hand-specified from published effect sizes. This is a deliberate constraint, and it is the statistically correct choice rather than merely a convenient one.

**Why training would be wrong here even if we wanted to:**

- The obtainable labelled data is thin. Public cohorts yield a limited number of illness episodes, which is far too few to train anything that generalises. Reported figures in this field are routinely inflated by favourable subgroups precisely because of this.
- The open cohort with illness labels carries **heart rate and steps only**. Its episode count is the binding problem: too few labelled illnesses to train anything that generalises, which is the point above. (The channel-mismatch worry that once sat here has been **resolved and removed**: Samsung writes only heart rate, steps, sleep stages and exercise to Health Connect, so our own channels are heart rate, steps and sleep. Our data and the cohort's now line up, and the domain-shift objection no longer applies. See `research/13-galaxy-watch5-data-reality.md`.)
- A trained model's reasoning cannot be audited or cited. **Every number in our belief model comes from a peer-reviewed effect size with a citation attached**, which is both more defensible in a report and more compatible with the grounding requirement.

**Where the knowledge comes from instead:** a compiled table of published effect sizes for each candidate cause, giving direction, magnitude, onset and duration, each row citing its source. For example, one drink raises nocturnal heart rate by roughly 2.4 to 2.8 bpm and lowers rMSSD by 3.3 to 3.8 ms; maximal training within two hours of sleep raises it by about 5.94 bpm; acute respiratory infection raises it by only 1.1 to 2.1 bpm. These become the likelihoods in the belief model. **Elicited priors with citations, not fitted weights.**

#### 4.5.2 The four models, and nothing else

Row 0 is listed for completeness but is **not a model**: it is ordinary statistics, and deliberately so. Rows 1 to 4 are the four models.

| # | Component | Job | Pretrained / hand-specified | Why this one |
|---|---|---|---|---|
| **0** | **Personal statistical baseline and detector** | Detect deviation from *your* normal: rolling median and MAD, multi-signal concordance, multi-night persistence | Neither. Pure statistics over the user's own history | Not a model at all, and deliberately so. The best-evidenced approach in this field, in under 100 lines, running in microseconds. Also the baseline every other component must beat |
| **1** | **Chronos-Bolt** (Amazon, Apache-2.0) | Zero-shot forecast: what should tonight have looked like for this person, with an expected range | **Pretrained, zero-shot** | The only time-series foundation model that is simultaneously zero-shot, permissively licensed, CPU-runnable, tolerant of missing values, and **proven at short context lengths of 32 to 64**. At nightly cadence, models requiring 512 steps would need 1.4 years of history. This is the project's pretrained-ML component |
| **2** | **Discrete Bayesian network** (pgmpy) | Hold and update the belief over twelve candidate causes as evidence arrives | **Hand-specified structure, literature-elicited priors** | The reasoning core. Auditable arithmetic where every prior carries a citation. Structure is hand-drawn because structure learning needs thousands of samples to beat a hand-drawn graph |
| **3** | **Sentence embedding model** (e.g. `bge-small-en-v1.5`) | Dense retrieval over the clinical corpus | **Pretrained** | Required by retrieval, not a discretionary choice. Small and CPU-runnable |
| **4** | **LLM** (Qwen family, see 4.5.3) | Language only: extract structured facts from free text, phrase questions, write explanations | **Pretrained** | Never computes a number, never decides an action, never scores a probability |

**That is it: four models (rows 1 to 4), none trained, plus statistics (row 0).** One pretrained forecaster, one hand-specified probabilistic model, one pretrained embedding model, one pretrained LLM.

#### 4.5.2.1 What we deliberately left out, and why

Focus is a design decision, so the exclusions are stated as deliberately as the inclusions.

| Excluded | Reason |
|---|---|
| **A trained illness classifier** | See 4.5.1. Too few labelled episodes, wrong channels, unauditable |
| **A cross-encoder reranker** | Would improve retrieval precision, but the corpus is only tens of documents, where hybrid retrieval plus fusion is already close to ceiling. Added complexity for a marginal gain |
| **MOMENT** | Excluded on a mechanism. Its authors state it *"struggles to differentiate between vertically shifted time series as it normalizes signals prior to modeling."* A sustained multi-night resting-heart-rate elevation **is** a vertical shift. It would normalise away the exact signal we detect |
| **IBM Tiny Time Mixers** | Hard 512-timestep minimum context. At one value per night that is 1.4 years of history |
| **Apple WBM, Google LSM-2, Google SensorFM** | Wearable-native foundation models with **no released weights and no API**. The models shaped like our data do not exist publicly |
| **TimesFM 3.0, Moirai** | Non-commercial licences |
| **GraphRAG** | Graph construction needs many LLM calls the free tier cannot absorb, and it targets corpora orders of magnitude larger than ours |
| **Multi-agent architectures** | The course's own guidance favours a single agent for bounded single-domain tasks, one action log is easier to audit, and published ablations show extra validate and replan stages contributing nothing |

#### 4.5.3 LLM selection and hosting, with the hardware checked

Requested target: Qwen3.8-27B on free Google Colab. **We checked, and it does not fit.**

- Free Colab provides a single **NVIDIA T4, 16 GB nominal but roughly 15 GB usable** after ECC overhead.
- Qwen3.8-27B at 4-bit is approximately **14 to 17 GB of weights alone**, before the KV cache (typically 1 to 3 GB at ordinary context lengths) and runtime overhead.
- The result is memory pressure and spillover into system RAM, with reported throughput around 12 tokens per second on a comparable 16 GB card. Practical guidance for this model is 24 GB minimum and 32 to 48 GB for comfort.
- The T4 is also Turing generation, so it lacks native bfloat16 and cannot use the faster quantisation kernels that require Ampere or newer.

**Therefore: Kaggle, not Colab.** Kaggle's 2x T4 gives 32 GB combined, 30 GPU-hours per week and 12-hour sessions.

**The serving engine is Ollama.** This was measured on real hardware on 31 August 2026, and two earlier choices were discarded on evidence.

| Engine | Verdict |
|---|---|
| **vLLM** | **Rejected.** Requires torch 2.13 and the CUDA 13 stack, so on Kaggle it uninstalls and replaces roughly thirty packages including torch, torchvision and triton. Turing (compute 7.5) is a neglected path with open reports of a 27B Qwen hanging indefinitely on a T4 |
| **llama-cpp-python** | **Rejected.** The prebuilt CUDA wheel index stops at 0.3.19 (March 2026). Qwen3.8-27B shipped in August 2026 with a new `qwen35` architecture that older builds refuse outright. Building current from source means a ~30 minute compile per rebuild |
| **Ollama** | **Chosen.** Qwen3.8 support landed in v0.32.12; we pin v0.33.2. Bundles its own CUDA runtime, so Kaggle's CUDA version is irrelevant. Turing is supported (floor is compute 5.0) |

**Measured, 2x Tesla T4:**

| Property | Value |
|---|---|
| Model | `qwen3.8:27b` from Ollama's registry, 18 GB |
| Placement | **100% GPU**, both cards, at 8192 context |
| Sustained generation | **9.2 tok/s** |
| Time to first token, streaming | 4.34 s |
| Cold start from cached weights | 2 min, against ~20 min without |
| Structured output | JSON mode returns schema-valid objects |

**Two implementation constraints this imposes:**

1. **Qwen3.8 is a thinking model.** Reasoning tokens are billed against `max_tokens` but stripped from `content`, so a small budget returns `finish_reason="length"` with an **empty string**. A two-word answer cost 37 completion tokens. **Never budget below 200.** Thinking can be disabled with `"think": false`, but only on Ollama's **native** `/api/chat`, not on `/v1/chat/completions`.
2. **The endpoint is ephemeral.** The Cloudflare hostname and bearer key are regenerated every session, so the client must read them from configuration at run time and never hard-code them.

Speed is bandwidth-bound: one token requires reading all 18 GB, a T4 gives ~320 GB/s, and Ollama splits layers **sequentially** rather than in parallel, giving a ~17.8 tok/s ceiling. The second T4 buys capacity, not speed. An untested `qwen3.8:27b-mtp-q4_K_M` variant at the same 18 GB offers multi-token prediction, reported at +33 to 39% with mathematically identical output.

**Fallback if the 27B proves impractical:** Qwen3.5 9B, or any small instruct model. The LLM does language only, never a number and never a decision, so the design absorbs a smaller model far better than a typical LLM application would.

The serving notebook is `tools/kaggle_serve_qwen27b.ipynb`.
| **Demonstration** | **OpenRouter free tier** | A stronger hosted model for the small number of live demo calls, where the daily cap is not binding |
| **Evaluation** | Cached and replayed responses from whichever model produced them | Makes every number re-derivable offline and independent of session limits |

**This turns a constraint into a result.** Running the same evaluation suite under the 8B and the 27B configurations answers a real question: does model capability actually matter for this task? Published work in this domain found contextual framing matters more than parameter count, so a negative result is plausible and would be worth reporting.

### 4.6 Retrieval design

#### 4.6.1 Corpus and why it is small

Tens to low hundreds of documents, deliberately. A small curated corpus with verifiable citations outperforms a large uncurated one on every metric we are assessed on, and it is far easier to demonstrate working.

**Layer 1, international clinical reference**
- **MedlinePlus** (US National Library of Medicine), bulk XML, roughly 29 MB, updated daily, attribution-only licence
- **StatPearls** via NCBI Bookshelf, peer-reviewed clinical reference articles
- **Published decision rules**, notably the **Centor / McIsaac criteria** for pharyngitis

**Layer 2, Singapore localisation** (see 4.6.4 for why this is not cosmetic)
- **HealthHub** (MOH Singapore), the national patient-facing health information service
- **MOH Singapore clinical guidance**, including the **National Dengue Clinical Guideline published 31 March 2026**
- Singapore care-pathway guidance: when to use a GP, a polyclinic, an A&E department, or call 995

**Layer 3, live local signals, retrieved as tools rather than documents**
- **NEA dengue cluster data** via `data.gov.sg`, GeoJSON with cluster polygons and case counts. **We tested this endpoint and it returns data without authentication.**
- **NEA air quality (PSI)**, since haze materially affects respiratory symptoms in this region

**Layer 4, our own compiled evidence table**
- A quantitative confounder table (direction, magnitude, onset, duration for each candidate cause), compiled from peer-reviewed sources with a citation on every row. This is the evidence base behind the Bayesian network's priors.

#### 4.6.2 Pipeline

| Stage | Approach | Rationale |
|---|---|---|
| **Chunking** | Section-aware splitting on document structure, target 300 to 500 tokens, with **parent-document retrieval**: match on the small chunk, return the enclosing section | Clinical documents are already structured by heading. Retrieving a fragment and losing its context is the classic failure |
| **Indexing** | **Hybrid**: BM25 sparse index plus dense vectors from the embedding model | Clinical text is full of exact terms (drug names, condition names, "Centor") where BM25 wins, and paraphrases where dense wins. Neither alone is sufficient |
| **Fusion** | **Reciprocal Rank Fusion** over the two result lists | Simple, parameter-light, no score normalisation needed between incompatible scoring schemes |
| **Filtering** | Metadata filters on document type, source authority, condition and geography | Lets the agent restrict to Singapore sources when the question is about local care pathways |
| **Grounding enforcement** | Every generated claim is matched back to a retrieved passage. Unsupported claims are **stripped and counted** | The count becomes a reported metric: unsupported-claim rate |

#### 4.6.3 Is it "agentic RAG"? Yes, in a specific and defensible sense

Not a fixed retrieve-then-generate pipeline. The agent decides:

- **whether** to retrieve at all (a deviation fully explained by a recorded workout needs no clinical evidence),
- **what** to query, derived from the current belief state rather than from the user's raw words,
- **when to re-query**, after a user answer or a measurement result changes the belief,
- **which layer** to query, for example the Singapore care-pathway layer when forming a recommendation versus the clinical reference layer when forming a differential.

Retrieval is a tool the agent chooses to use, on a query it constructs, at a moment it selects. That is the agentic part.

**We deliberately do not use GraphRAG.** Building an entity graph requires many LLM calls over the corpus, which our free-tier rate limit cannot absorb, and it is designed for corpora orders of magnitude larger than ours. Using it here would be cost without benefit, and we will say so rather than omit it silently.

#### 4.6.4 Why Singapore sources materially change the output

This is not localisation for the sake of it. It changes the differential and the recommendation.

**It changes the differential.** Fever with headache and body aches in Singapore raises **dengue**, which is endemic here and effectively absent from the US and UK sources that dominate international corpora. A system reasoning from MedlinePlus alone would systematically under-weight the single most locally relevant febrile illness. Dengue also has physiological features a wearable can plausibly see, and, critically, it has **different red flags and a different escalation urgency** from influenza.

**It changes the prior, dynamically.** The NEA publishes live dengue cluster polygons with case counts as open data. That makes `get_local_disease_activity(location)` a legitimate agent tool: if the user is inside an active cluster, the prior on dengue rises materially. **A wearable that adjusts its differential based on live local disease activity is something no shipped product does**, and it is a genuinely novel, genuinely Singaporean contribution.

**It changes the recommendation.** "See a doctor" is not actionable advice. "A polyclinic is appropriate for this; go to an A&E if you develop these specific warning signs; call 995 if this happens" is. Care pathways are national, and using the wrong country's pathway makes the advice useless.

### 4.7 Evaluation plan

#### 4.7.0 What success means

Weighted toward a convincing end-to-end demonstration, with measurement second.

| Level | Criterion |
|---|---|
| **Primary** | The system runs end to end on a real person's real watch data, detects a deviation, decides to ask, conducts the interview, requests a measurement, retrieves and cites evidence, and produces a grounded differential with an action and an audit trail |
| **Secondary** | The question policy is shown to beat never-ask, always-ask, and a silent multi-signal concordance rule on a benchmark whose oracle answers are real human self-reports |
| **Tertiary** | Every component survives an ablation, or is reported as not having earned its place |

If the primary is achieved and the secondary is only partially achieved, the project has succeeded. If the secondary is achieved and the primary is not, it has not.

#### 4.7.1 A stated limitation of the evaluation

**The detector we evaluate is not exactly the detector we run.** The open cohort with illness labels carries heart rate and steps only, while the deployed system is expected to use HRV, respiratory rate and blood oxygen as well, subject to the day-zero channel check. Detection metrics are therefore reported for the **common-channel configuration**, and the additional channels are justified from published effect sizes rather than from our own measured performance. We state this rather than blur it.

Evaluated on the six metrics the course specifies: task completion rate, unsupported-claim rate, source and citation accuracy, retrieval precision and recall, latency, and calibration.

**Detection performance** on the Stanford cohort, reporting episode-level recall with exact confidence intervals, lead-time distribution, false alerts per user-week, and number needed to evaluate. We will **not** report point-adjusted F1, on which random scores reach 0.969. We will show two mandatory baselines: a random detector matched on alert rate, and a trivial fixed-threshold rule.

**The asking policy** on PMData, which carries real daily self-reports of alcohol, training, stress and sleep. We inject a physiologically-calibrated illness signature (+4 bpm sustained over 4 days, taken from a published detector's own thresholds) and sweep amplitude and duration. **The oracle's answers are real human self-reports, revealed only when the agent asks for them**, rather than values we invented. Compared against never-ask, always-ask, fixed-threshold, and a silent multi-signal concordance rule.

**Test cases** in the course's Input / Expected / Logged format, covering both positive and negative inputs, including a systematic prompt-injection suite.

**An ablation** removing each component in turn, with paired bootstrap confidence intervals, so that any component which does not earn its place is reported as such.

---

## 5. Safety, ethics, privacy, security, and limitations

### 5.1 Safety

| Risk | Mitigation |
|---|---|
| **Missing a serious condition** | A deterministic red-flag layer runs **before** the model on every episode, covering both vitals thresholds and reported symptoms (chest pain, breathlessness, confusion, severe or persistent fever). It escalates directly to "seek clinical care" and the model cannot override or reason past it, because it is plain code |
| **False reassurance** | The system never outputs "you are fine". Its disposition set includes `UNRESOLVED` and `INSUFFICIENT_DATA`, and the output always carries explicit criteria for when to seek care regardless of the assessment |
| **Overconfident output** | Probabilities are produced by the explicit probability model, never verbalised by the LLM, whose stated confidence is known to be systematically overconfident. Calibration is measured and reported |
| **Health anxiety** | Silent by default. The interruption budget defaults to two unprompted conversations per week and is user-configurable. The system is designed to say nothing far more often than it says something |
| **Acting on a diagnosis** | Output is advisory. It has no tool that can commit any external action. It drafts, the user decides |

**Regulatory positioning.** This is a **student prototype and personal wellness tool, not a medical device**, and it will state so in the interface. We design against the FDA's revised general-wellness boundary (January 2026) as a set of deterministic output checks: the system does not present itself as a diagnostic device, does not state clinical thresholds as decision criteria, and routes anything clinically consequential to a professional. Where it names a possible condition, it does so as a **ranked differential with explicit uncertainty and cited sources**, in the manner of a triage aid, never as a single confident verdict.

### 5.2 Ethical concerns

- **Scope of competence.** Wearable sensors measure the body's general response, not specific pathogens. Influenza, COVID-19, RSV and a common cold are not separable on these signals. The system may only name conditions once **symptom evidence** has been acquired, and must say what it cannot know.
- **Equity.** The luteal phase moves every relevant signal in the infection direction on roughly 45% of days, so a system that ignores menstrual cycle context is systematically less accurate for around half the population. We treat cycle phase as an explicit candidate cause rather than pretending it does not exist. We will also state plainly that our own evaluation cohort is small and unrepresentative.
- **Consent and burden.** The user sets both budgets and can decline any question at any point without penalty. Non-response is treated as a valid state, not an error, and the agent must proceed sensibly without an answer.
- **Self-experimentation.** Team members generating their own data will do so only through ordinary safe behaviour (training, sleep, normal daily life). No health-relevant behaviour will be induced for the purpose of the project.

### 5.3 Privacy

- **Local-first by design.** Wearable data is stored on the user's own machine. The ingestion layer is self-hosted; there is no third-party health data cloud.
- **Minimum necessary.** The agent receives derived nightly features and explicitly requested history windows, not a full raw data dump. Unnecessary context increases exposure, latency and failure surface.
- **What leaves the machine.** Only the text sent to the LLM. That text contains derived numbers and the user's own answers. This is a **genuine limitation of using a hosted model** and we will state it, along with the mitigation: a self-hosted open-weight model removes it entirely, which is one reason we are running that configuration for evaluation.
- **Retention** is defined separately for raw data, derived features, conversation content and the audit log.
- **Team data.** Only team members' own data is used, by their own consent, and it is excluded from the repository via `.gitignore`.

### 5.4 Security

**Threat model.** The system has two untrusted inputs: the user's free-text answers, and retrieved document content. Both could contain instruction-like text.

| Threat | Mitigation |
|---|---|
| **Prompt injection**, direct or via retrieved documents | Architectural rather than prompt-based. We use a **Plan-Then-Execute** structure: the investigation plan is fixed *before* any external content is retrieved, so retrieved content can influence the **data** but never the **control flow**. Retrieved content is passed as delimited data, never as instructions. This matters because eight published prompt-level defences have been broken by adaptive attacks with over 50% success, so detection-based defences are not sufficient |
| **Data exfiltration** | **The system has no exfiltration vector.** It has private data and untrusted content but no tool that sends anything outward. We will document the tool table that keeps this true, which is a stronger guarantee than any prompt hardening |
| **Over-permissioning / excessive agency** | Every tool is typed, argument-validated, read-only where possible, and assigned an explicit control tier. No shell, no arbitrary code execution, no network access from tools. Self-expansion is denied and attempted expansions are logged and counted |
| **Goal hijack via memory** | Persisted episode state is schema-validated on read, so poisoned state cannot alter the agent's objective |
| **Model unavailability** | Free-tier quota limits and Kaggle session expiry are expected, and the endpoint URL and key change every session. Cached and replayed responses make evaluation independent of live availability, and the demonstration is a scripted replay by design (4.2.5), so it does not depend on a live model at all |
| **Unauthenticated local health data endpoint** | The Health Connect bridge exposes health data over the local network **without authentication**, by its own design, and is intended for trusted networks only. We state this as a real limitation rather than glossing it. Mitigations for the prototype: run it only on a private network, prefer webhook push to a loopback-bound listener over open polling, and treat the endpoint as untrusted input that is schema-validated on read. A production version would require authentication, which is noted as future work |

We will build a **systematic adversarial test suite** (a taxonomy of attack goals crossed with injection vectors, approximately 40 to 80 cases) with a measured attack success rate, rather than a single demonstration case.

### 5.5 Implementation concerns and known limitations

**Stated honestly, because they will be asked about.**

1. **We cannot demonstrate detection of real illness in ourselves.** A handful of people over two weeks are very unlikely to fall ill on schedule. Illness detection performance is therefore measured on public cohort data, while personal data demonstrates the system running live on a real person. In the course's own release-stage terms, this is a **silent-mode shadow deployment**: reading live data, proposing actions, taking none without human approval.
2. **No clinical validation.** We make no claim of clinical accuracy or safety, and the interface will say so.
3. **Which channels actually arrive is unverified until day zero.** Health Connect defines HRV, respiratory rate and skin temperature as data types, and the bridge app supports all of them, but whether **Samsung Health populates them for a Galaxy Watch 5** is not settled by the documentation we could find. Samsung's developer materials indicate skin temperature is exposed from Galaxy Watch 6 onward. If some channels are absent we operate on heart rate, resting heart rate and sleep, which is the channel set of the best-evidenced published detector and remains sufficient. This is resolved by a twenty-minute test, not by further research.
4. **The confounder probability table encodes judgement.** It is compiled from published effect sizes, but several entries are weakly evidenced. We present it as an **elicited prior with citations and an explicit sensitivity analysis**, not as fact.
5. **The interruption cost cannot be empirically fixed.** No published study gives a dose-response curve for alert burden. We therefore **sweep** that parameter and report the accuracy-versus-friction trade-off across a range, stating that the literature does not fix a point on it.
6. **Small sample sizes.** Public cohorts yield limited labelled episodes, so results are reported descriptively with exact confidence intervals, and we will state where the study is underpowered rather than implying a ranking.
7. **A single-author preprint reports an adjacent result.** We will read and cite it, and narrow our claim if it overlaps.
8. **Free-tier constraints shape the engineering.** Rate limits are why response caching is core infrastructure rather than an optimisation, and why the system is deliberately single-agent.

---

## Appendix A: Scope

**In scope:** nightly deviation detection; explained-variance subtraction; belief state over causes; information-gain question policy; adaptive interview; watch measurement requests; retrieval-grounded differential; deterministic red-flag escalation; human checkpoint; audit log; visible reasoning trace; evaluation on public and personal data; adversarial test suite.

**Out of scope:** real-time sub-minute monitoring; treatment or prescription advice; clinician-facing workflows; multi-user or population analytics; any claim of clinical validation; pathogen identification from sensors alone.

**Stretch goals if time allows:** counterfactual projection ("if you rest today versus train today"); **conjugate updating of per-user priors** from the user's own answers over time, which is closed-form Bayesian updating rather than model training and so does not breach the no-training constraint. A second device vendor is no longer a stretch goal, since Health Connect aggregates Fitbit and Google Fit and adding one is a permissions change.

## Appendix B: Indicative two-week plan

| Days | Focus |
|---|---|
| 0 | **Pre-work, before the build starts.** (a) ~~Samsung Health export~~ **not used**, at the participant's request. (b) Health Connect bridge installed and reachable; **confirmed working, currently returning heart rate and steps**, with sleep stages and exercise pending a Samsung-side sharing change. **HRV, respiratory rate and resting heart rate are not obtainable through Health Connect at all** and are therefore out of scope, see research/13. (c) **PMData verified at source**, see section 3.6. (d) **Done.** Kaggle notebook serving Qwen3.8-27B via Ollama, measured end to end |
| 1-2 | Data ingestion (Health Connect bridge poller plus Samsung export parser behind one `DataSource` interface), historical backfill, public dataset loading and inspection |
| 3-4 | Feature extraction, personal baselines, deviation detection with concordance and persistence, mandatory baselines |
| 5-7 | Agent skeleton in LangGraph: bounded loop, typed tools, state across waits, human interrupt, audit log |
| 8-9 | **Compile the prior table** (12 causes against the available channels, every effect size cited). This replaces training and is the single most important artefact in the project. Then belief state, information-gain policy, interview logic, measurement requests |
| 10 | Retrieval corpus, citation enforcement, unsupported-claim stripping, safety layer |
| 11-12 | Evaluation: detection metrics, policy benchmark on PMData, ablation, adversarial suite |
| 13 | Interface polish, visible trace, demonstration script and rehearsal |
| 14 | Report and buffer |

**Ordered cut list, decided in advance:** counterfactual projection first, then the self-critique pass, then the Singapore live-disease-activity tool, then reducing the adversarial suite from roughly 15 cases to a handful.

**The evaluation is the most likely overrun**, so it is scoped tightly from the start: the PMData policy benchmark and the Stanford detection metrics are kept in full, the adversarial suite is capped at roughly 15 cases rather than 40 to 80, and the ablation is three targeted comparisons (no asking, always asking, no retrieval) rather than a full matrix.

**Two things are explicitly not on the cut list.** *Chronos*, because with no trained component it is the project's only pretrained ML model and is therefore core. *Live ingestion (F1)*, because the primary success criterion is that the system runs on a real person's real watch data. Note that live ingestion and a replayed demonstration are not in tension: ingestion runs for real throughout the two weeks, and the presentation replays an episode it captured.

## Appendix C: Key references

Full bibliography (approximately 2,100 sources reviewed) is held in the project repository under `research/findings/`. Principal anchors:

- Alavi et al., *Real-time alerting system for COVID-19 and other stress events using wearable data*, Nature Medicine 28:175-184, 2022. DOI 10.1038/s41591-021-01593-2
- Mishra et al., *Pre-symptomatic detection of COVID-19 from smartwatch data*, Nature Biomedical Engineering 4:1208-1220, 2020. DOI 10.1038/s41551-020-00640-6
- Northwell Health / Fitbit prospective evaluation, JMIR 2024 (positive predictive value 4%, false-alert attribution)
- Zwiers et al., COVID-RED randomised controlled trial, PLoS ONE 2025 (n=17,825)
- Drew et al., alarm fatigue in hospital monitoring, 2014; Joint Commission Sentinel Event Alert 50
- Horvitz, Jacobs and Hovel, *Attention-Sensitive Alerting*, UAI 1999
- Chakraborty, *Project Hermes: A Model-Agnostic Validation Layer for Wearable Health Prediction Systems*, arXiv:2602.18643, 2026 (closest prior art; 61.7% to 12.5% false positive rate at 89% sensitivity, migraine)
- Anthropic, *Building Effective Agents*, 2024
- Beurer-Kellner et al., *Design Patterns for Securing LLM Agents against Prompt Injection*, arXiv:2506.08837
- OWASP Top 10 for LLM Applications, and for Agentic Applications, 2026
