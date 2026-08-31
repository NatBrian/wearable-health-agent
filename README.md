# Wearable Health Agent

**An agentic differential-triage system that answers the one question wearables cannot: *am I getting sick, or do I just need rest?***

> **Status: design complete, implementation not started.** This repository currently holds the research and the design specification. Code will follow.

---

## The problem

Consumer wearables have become good at noticing that something in your body has changed, and remain unable to tell you why.

A raised overnight resting heart rate is produced by an incubating infection, by alcohol, by a hard training session, by poor sleep, by stress, by a recent vaccination, and by the luteal phase of the menstrual cycle. To a wrist sensor these look nearly identical, yet they demand opposite responses: rest and isolate, or carry on as normal.

The consequence is measured, not hypothetical. An independent prospective evaluation of a wearable illness-detection system issued **665 alerts across 470 participants at a positive predictive value of 4%**, roughly twenty-four false alarms for every true one. The authors attributed the false alerts by cause: stress 16.0%, poor sleep 13.7%, exercise 9.7%, alcohol 6.0%.

**About 45% of those false alerts had a cause that a single question could have resolved.** Nothing on the market asks it.

---

## The gap

| What exists | What it does well | Where it stops |
|---|---|---|
| Passive detectors (Samsung Vitals, Oura Symptom Radar, WHOOP, Apple Vitals) | Detect deviations against a personal baseline | Notify, then leave you to guess. One vendor's own marketing says the feature helps you "determine whether you are fighting an illness or just need more rest". It does not determine that |
| Symptom checkers (Ada, NHS 111 online) | Structured clinical questioning producing a real differential | Completely blind to your physiology. They start from zero every time |
| Daily journals (WHOOP Journal, Oura tags) | Collect context | Ask **unconditionally**, every morning, whether anything happened or not, which is why people stop answering |

> Physiological monitors detect but never ask. Symptom checkers ask but never measure. Journals ask unconditionally, so people stop answering.
>
> **Nothing connects a detected physiological deviation to a targeted question capable of resolving it, and then to a grounded explanation.**

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

### Three design decisions that carry the project

**The ask-or-stay-silent decision is explicit arithmetic, not an LLM judgement.** The agent holds a probability distribution over twelve candidate causes and computes the expected information gain of each candidate question against the cost of interrupting, in the form given by Horvitz, Jacobs and Hovel's *Attention-Sensitive Alerting* (UAI 1999). Keeping this out of the language model is what makes the policy **measurable**: it can be compared directly against never-ask, always-ask and fixed-threshold baselines. An LLM told to "ask if unsure" can be demonstrated but never evaluated.

**The agent can order a test.** Not just ask how you feel. It can instruct a stress and HRV reading, a blood-oxygen reading, or a sit-to-stand orthostatic test, then re-reason on the result. Two shipped products prove the pattern: Google's Loss of Pulse Detection asks the user and escalates autonomously on silence, and Ultrahuman's Jade responds to anomalies by triggering a confirmatory measurement rather than giving advice. Neither has been applied to illness triage.

**Nothing is trained.** Every model is pretrained and zero-shot, or hand-specified from published effect sizes. This is the statistically correct choice rather than a convenience: the obtainable labelled data is far too thin to generalise, the open cohort carries different channels than the target device, and fitted weights cannot be cited. Every number in the belief model comes from a peer-reviewed effect size with a source attached.

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

Two properties this makes visible: the LLM sits in exactly one box and is **never invoked on a quiet night**, and the red-flag path sits upstream of the agent so it cannot be reasoned past.

### Stack

| Layer | Choice |
|---|---|
| Ingestion | Android Health Connect via an off-the-shelf bridge, plus a one-time export for history |
| Detection | Python, pandas, NumPy. Personal baseline, multi-signal concordance, multi-night persistence |
| Forecasting | Chronos-Bolt, zero-shot, CPU |
| Belief state | pgmpy discrete Bayesian network, literature-elicited priors |
| Decision policy | Custom expected-information-gain arithmetic |
| Orchestration | LangGraph with SQLite checkpointing and human-in-the-loop interrupts |
| Retrieval | Hybrid BM25 and dense, reciprocal rank fusion, claim-to-source enforcement |
| LLM | Open-weight model, self-hosted, used for language only |
| Interface | Streamlit, with the reasoning trace and audit log visible |

---

## What it can and cannot do

Being precise about this is part of the design, because the limits determine the model selection.

**Can:** tell you your physiology has deviated from your own normal, and when it started; tell you the deviation is fully explained by a recorded event; identify systemic strain consistent with immune activation; distinguish likely benign causes from possible illness **given one or two answers**; produce a grounded differential **given symptoms**; escalate deterministically on red flags.

**Cannot:** distinguish influenza from COVID from RSV from a common cold using sensors alone, because they produce the same host response and no model recovers information that was never measured; give a definitive diagnosis; predict illness before physiological change begins, since **this is early detection, not prediction**; see conditions with no autonomic signature; work without two to four weeks of personal history; separate a first-night hangover from a first-night infection **without asking**, which is the identifiability limit that motivates the entire project.

---

## Repository

| Path | Contents |
|---|---|
| [`PROPOSAL.md`](PROPOSAL.md) | **The design specification.** Problem, agentic approach, prototype, safety and limitations |
| [`research/`](research/) | Working notes: problem formulation, unknowns, decision gates, evidence synthesis, candidate formulations |
| [`research/findings/`](research/findings/) | **The research corpus.** Nine parallel investigations, roughly 126,000 words and 2,100 citations |
| [`archive/`](archive/) | An earlier, weaker generation of the research, retained deliberately and audited in `research/00-prior-work-audit.md` |

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

Every document carries explicit `UNVERIFIED` flags and a closing list of what could not be sourced. Those are deliberate: an unverified claim marked as such is useful, and one presented as fact is not.

---

## Notes on method

Three things here are worth more than the design itself.

**The prior work was audited rather than inherited.** An earlier generation of research is kept in `archive/` and systematically checked in `research/00-prior-work-audit.md`. Several of its headline figures turned out to be fabricated, its ranking method selected the union of its own options, and its recommended architecture depended on sensor channels the target hardware does not expose. Finding that out was worth more than accepting it.

**Claims were verified at source.** Where the research reports a number, the paper, repository or API was fetched and checked. Where verification failed, the document says so.

**The limits are stated in the design, not discovered later.** The specification contains an explicit list of what the system cannot determine, and why, at the level of mechanism. A system that names its own identifiability limits is easier to trust than one that does not.

---

## Data and privacy

No personal health data is included in this repository, and `.gitignore` is configured to keep it that way. Wearable data used during development stays on the local machine.

This is a research prototype and a personal wellness tool. **It is not a medical device**, it makes no claim of clinical validity, and anything clinically consequential is routed to a professional by deterministic code that the model cannot override.
