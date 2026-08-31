# Wearable Health Agent

> **Building this? Read [`HANDOFF.md`](HANDOFF.md), not this file.**
> The status section below predates the implementation plan and is out of date. The plan lives in
> [`plan/`](plan/) and is the only implementation contract.

---


**Agentic illness triage from smartwatch data.** It detects overnight physiological deviations, decides by expected value of sample information whether asking you one question is worth the interruption, can order a watch measurement, and returns a source-grounded differential.

> **Status: implementation plan complete and frozen. Build in progress.**
> Research, design and a full implementation plan are done. The plan is in [`plan/`](plan/): 17 component specifications, 67 test-gated tasks, cited knowledge tables, and 11 frozen end-to-end scenarios. See the [roadmap](#roadmap).

**Start here:** [the problem](#the-problem) → [the gap](#the-gap) → [the design](#the-approach) → [`plan/`](plan/) for the implementation contract.

**Building it?** Read [`HANDOFF.md`](HANDOFF.md). `PROPOSAL.md` is a narrative design document that predates the plan and is superseded in fourteen documented ways.

---

## The problem

Consumer wearables have become good at noticing that something in your body has changed, and remain unable to tell you why.

A raised overnight resting heart rate is produced by an incubating infection, by alcohol, by a hard training session, by poor sleep, by stress, by a recent vaccination, and by the luteal phase of the menstrual cycle. To a wrist sensor these look nearly identical, yet they demand opposite responses: rest and isolate, or carry on as normal.

The consequence is measured, not hypothetical. An independent prospective evaluation of a wearable illness-detection system issued **665 alerts across 470 participants at a positive predictive value of 4%**, roughly twenty-four false alarms for every true one. The authors attributed those false alerts by cause: stress 16.0%, poor sleep 13.7%, exercise 9.7%, alcohol 6.0%.

**About 45% of them had a cause that a single question could have resolved.** Nothing on the market asks it.

There is a second number that explains why this is hard rather than merely unsolved. Acute respiratory infection raises resting heart rate by roughly **1.1 to 2.1 bpm**. One alcoholic drink raises it by 2.4 to 2.8. A hard evening session raises it by about 5.94. **The confounders are larger than the signal.** Detection works at all only because it is multi-channel, within-person and multi-night.

---

## The gap

| What exists | What it does well | Where it stops |
|---|---|---|
| Passive detectors (Samsung Vitals, Oura Symptom Radar, WHOOP, Apple Vitals) | Detect deviations against a personal baseline | Notify, then leave you to guess. One vendor's own marketing says the feature helps you "determine whether you are fighting an illness or just need more rest". It does not determine that |
| Symptom checkers (Ada, NHS 111 online) | Structured clinical questioning producing a real differential | Completely blind to your physiology. They start from zero every time |
| Daily journals (WHOOP Journal, Oura tags) | Collect context | Ask **unconditionally**, every morning, whether anything happened or not, which is why people stop answering |

> Physiological monitors detect but never ask. Symptom checkers ask but never measure. Journals ask unconditionally, so people stop answering.
>
> **No shipped product connects a detected physiological deviation to a targeted question capable of resolving it, and then to a grounded explanation.**

Every component needed to close that gap has already shipped somewhere. Google's Loss of Pulse Detection asks the user and escalates autonomously on silence. Ultrahuman's Jade responds to anomalies by ordering a confirmatory measurement rather than giving advice. Adaptive testing is deployed across healthcare, asking 22 questions instead of 60 because each one is chosen from what is still unknown. **No shipped product assembles them.**

The closest prior art is a preprint, *Project Hermes* (arXiv:2602.18643), which connects a deviation to an LLM-generated question and a Bayesian update, reporting a false positive rate of 61.7% falling to 12.5% at 89% sensitivity on migraine. It is cited rather than sidestepped. It validates alerts that have already fired; it has no model of **whether a question is worth the interruption**, and it does not measure, escalate, or diagnose. That decision layer is what this project adds. See [`research/15-project-hermes-read.md`](research/15-project-hermes-read.md).

---

## The approach

The monitor is **not** the agent. Detecting a deviation is cheap, deterministic and continuous. It is a sensor.

**The agent is the investigation.** When a deviation is flagged, a bounded agent is instantiated with one goal: determine the most probable explanation, acquiring only the evidence worth acquiring, and reach a disposition. It reasons across several nights, holds state while it waits, and terminates at a typed outcome.

Its action space is five choices:

```
OBSERVE     stay silent, log, wait for another night
ASK         pose one targeted question
MEASURE     instruct a specific measurement on the watch
ESCALATE    surface a warning, or direct the user to clinical care
CONCLUDE    terminate with a disposition and a grounded explanation
```

### Three decisions that carry the project

**The ask-or-stay-silent decision is explicit arithmetic, not an LLM judgement.** The agent tracks which of twelve candidate causes are contributing and computes the expected value of sample information for each candidate probe against a quantified interruption cost. Information that cannot change what the system does is worth exactly zero, so the quiet band at both ends emerges from the arithmetic rather than being imposed by a threshold. Keeping this outside the language model is what makes the policy **measurable**: it can be compared directly against never-ask, always-ask and fixed-threshold baselines. An LLM told to "ask if unsure" can be demonstrated but never evaluated.

**The agent can order a test.** Not just ask how you feel. It can instruct a stress and HRV reading, a blood-oxygen reading, or a sit-to-stand orthostatic test, then re-reason on the result. This turns the action space from a chatbot's into a clinician's: observe, ask, order a test, escalate.

**Nothing is trained.** Every model is pretrained and zero-shot, or hand-specified from published effect sizes. This is the statistically correct choice rather than a convenience: the obtainable labelled data is far too thin to generalise, the open cohort carries different sensor channels than the target device, and fitted weights cannot be cited. Every number in the belief model comes from a peer-reviewed effect size with a source attached.

---

## Architecture

```
   Wearable --> Health Connect --> local bridge --> nightly batch
                                                        |
                              deterministic, local CPU, NO LLM
                                                        |
                                              deviation flagged?
                                    NO --> log and sleep, zero cost
                                                        | YES
                                                        v
                                    deterministic red-flag intercept
                                    (plain code, cannot be reasoned past)
                                                        |
                                                        v
   +--------------------------------------------------------------------+
   |  BOUNDED EPISODE AGENT                                             |
   |    belief state over 12 causes  <----------+                       |
   |            |                                |  new evidence        |
   |    information-gain policy                  |                      |
   |            |                                |                      |
   |    OBSERVE / ASK / MEASURE / CONCLUDE ------+                      |
   |            |                                                       |
   |    retrieval + claim-to-source enforcement                         |
   +--------------------------------------------------------------------+
                                    |
                    human checkpoint --> audit log --> visible trace
```

Two properties this makes visible: the LLM sits in exactly one box and is **never invoked on a quiet night**, and the red-flag intercept sits upstream of the agent, so it cannot be reasoned past.

Every episode terminates in one schema-validated object carrying the disposition, the observation, a ranked differential with probabilities, what was ruled out and by which evidence, citations, a count of any claims stripped for lacking a source, an action, and explicit escalation criteria. `INSUFFICIENT_DATA` is one of the dispositions, not an error.

### Stack

| Layer | Choice |
|---|---|
| Ingestion | Android Health Connect via an off-the-shelf bridge. No app to build, no manual export. **Samsung writes heart rate, steps, sleep stages and exercise to Health Connect, and nothing else**, so resting heart rate is derived rather than read |
| Detection | Python, pandas, NumPy. Personal baseline, multi-signal concordance, multi-night persistence |
| Forecasting | Chronos-Bolt, zero-shot, CPU |
| Belief state | Twelve independent binary causes with additive effects and published temporal profiles. Exact inference by enumeration over 4096 states, in numpy. Literature-elicited priors, every row cited |
| Decision policy | Expected value of sample information against a quantified interruption cost. The testing threshold is derived from the stated utilities, not asserted |
| Orchestration | LangGraph with SQLite checkpointing and human-in-the-loop interrupts |
| Retrieval | Hybrid BM25 and dense, reciprocal rank fusion, claim-to-source enforcement |
| LLM | Provider-agnostic: any OpenAI-compatible endpoint, or a local Ollama. Bring your own model. It investigates, extracts, writes its own questions and runs the interview, but never decides whether to interrupt you |
| Interface | Streamlit, with the reasoning trace and audit log visible |

---

## What it can and cannot do

Stating the limits precisely is part of the design, because they determine the model selection.

**Can:** tell you your physiology has deviated from your own normal, and when it started; tell you the deviation is fully explained by a recorded event; identify systemic strain consistent with immune activation; distinguish likely benign causes from possible illness **given one or two answers**; produce a grounded differential **given symptoms**; escalate deterministically on red flags.

**Cannot:** distinguish influenza from COVID from RSV from a common cold using sensors alone, because they produce the same host response and no model recovers information that was never measured; give a definitive diagnosis; predict illness before physiological change begins, since **this is early detection, not prediction**; see conditions with no autonomic signature; work without two to four weeks of personal history; separate a first-night hangover from a first-night infection **without asking**, which is the identifiability limit that motivates the entire project.

---

## Roadmap

| Stage | State |
|---|---|
| Research corpus | **Done.** Nine parallel investigations, ~126,000 words, ~2,100 citations |
| Design specification | **Done.** See [`PROPOSAL.md`](PROPOSAL.md) |
| Ingestion probe and synthetic generator | **Done.** See [`tools/`](tools/) |
| Self-hosted LLM endpoint on free tier | **Done.** Measured on hardware, see [`tools/kaggle_serve_qwen27b.ipynb`](tools/kaggle_serve_qwen27b.ipynb) |
| Implementation plan | **Done.** 17 components, 67 tasks, see [`plan/`](plan/) |
| Phase A: data, detection, belief, policy, evaluation | Planned, 28 tasks |

| Phase B: agent graph, tools, retrieval, safety, notifier | Planned, 27 tasks |

| Phase C: dashboard, scheduler, documentation | Planned, 12 tasks |


---

## Repository

| Path | Contents |
|---|---|
| [`plan/`](plan/) | **The implementation contract.** 17 component specifications, 67 test-gated tasks, the schema and model contract, and the decision record. Everything is built from here |
| [`data/knowledge/`](data/knowledge/) | The cited medical tables: twelve causes with effect sizes and temporal profiles, nine probes with their likelihoods, the red-flag rules, and the source allow-list. **Every number labelled `CITED`, `DERIVED` or `ASSUMED`** |
| [`tests/fixtures/`](tests/fixtures/) | Eleven frozen end-to-end scenarios and nineteen authored LLM responses, so the whole system runs offline with no data and no endpoint |
| [`tools/`](tools/) | The ingestion probe (structure only, prints no health values), the synthetic payload generator that documents the real device schema, and the LLM serving notebook |
| [`HANDOFF.md`](HANDOFF.md) | **The entry point for building this.** Written for someone, or something, with no prior knowledge of the project |
| [`AGENTS.md`](AGENTS.md) · [`GEMINI.md`](GEMINI.md) · [`.agents/rules/`](.agents/rules/) | Operating rules for a coding agent: prohibitions, environment, conventions, task workflow |
| [`PROPOSAL.md`](PROPOSAL.md) | The original narrative design document. **Superseded by `plan/` in fourteen documented ways** and kept for the reasoning, not as a specification |
| [`research/`](research/) | Working notes 00 to 15, and the evidence corpus. See [`research/README.md`](research/README.md) for what is still current |
| [`research/findings/`](research/findings/) | **The research corpus.** Nine parallel investigations |
| [`archive/`](archive/) | An earlier, weaker generation, retained deliberately and audited in [`research/00-prior-work-audit.md`](research/00-prior-work-audit.md) |
| [`DISCLAIMER.md`](DISCLAIMER.md) | Not a medical device |

### Research corpus

Nine independent investigations, each verifying claims against primary sources rather than summaries.

| Doc | Territory |
|---|---|
| F1 | Clinical cohort studies, claim verification, dataset availability |
| F2 | Commercial products, regulatory status, the measured 4% precision figure |
| F3 | Health LLM agents, time-series serialization evidence, repository inspection |
| F4 | Time-series and physiological foundation models, availability classification |
| F5 | Device APIs, measured latency tiers, Samsung and WHOOP deep dives |
| F6 | Detection methods, datasets, and the pathologies of anomaly-detection evaluation |
| F7 | Agentic patterns, prompt injection, audit logging, medical corpora, regulatory boundaries |
| F8 | Confounder physiology and the separability matrix; value-of-information machinery |
| F9 | Advanced techniques ranked by impressiveness-per-hour, with a "will not work here" list |

Every document carries explicit `UNVERIFIED` flags and a closing list of what could not be sourced. Those are deliberate: an unverified claim marked as such is useful, one presented as fact is not.

---

## Notes on method

Four things here are worth more than the design itself.

**The prior work was audited, not inherited.** An earlier generation of research is kept in `archive/` and systematically checked in [`research/00-prior-work-audit.md`](research/00-prior-work-audit.md). A long list of its performance figures turned out to be fabricated or badly distorted, and its ranking method selected the union of its own options. Finding that out was worth more than accepting it.

**The audit was itself audited.** The first pass concluded that the archive's citations were generated rather than retrieved and could not be trusted. A second pass checked every suspicious identifier against arXiv and found **they all resolve to real papers**. The conclusion was narrowed to what the evidence supported: *the identifiers are mostly reliable; the numbers are not.* A separate claim, that the archive's recommended architecture needed sensor channels the hardware does not expose, was **withdrawn** once the export path was examined properly. Both reversals are recorded in place rather than quietly edited out.

**Claims were verified at source.** Where the research reports a number, the paper, repository or API was fetched and checked. Where verification failed, the document says so instead of quietly rounding.

**The limits are stated in the design, not discovered later.** The specification contains an explicit list of what the system cannot determine, and why, at the level of mechanism. A system that names its own identifiability limits is easier to trust than one that does not.

**Prior art that undercut the claim was sought out, not avoided.** A preprint flagged early as a required read was left unread while the design was written. Reading it falsified a sentence in this project's own summary. The claim was corrected rather than defended, and the reasoning is in [`research/15-project-hermes-read.md`](research/15-project-hermes-read.md).

---

## Data, privacy and scope

No personal health data is in this repository, and `.gitignore` is configured to keep it that way. Wearable data used during development stays on the local machine.

This is a research prototype and a personal wellness tool. **It is not a medical device.** It makes no claim of clinical validity, and anything clinically consequential is routed to a professional by deterministic code the model cannot override. See [`DISCLAIMER.md`](DISCLAIMER.md).
