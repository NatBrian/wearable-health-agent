# 11. Supervisor Challenge and Candidate Project Formulations

**Status:** Phase 4. No decision made. Input to a brainstorming discussion.
**Date:** 2026-08-30
**Basis:** `10-evidence-synthesis.md` and `findings/F0-F9`.

---

## Part 1: The original idea, challenged

> "Multi-Agent / Agentic Real-Time Wearable Sickness Prediction and Early-Warning System: build an adaptive, personalized early-warning system that detects physiological deviations and dynamically determines whether additional evidence is required before estimating illness risk."

Four of the words in that title do not survive Phase 2. Taking them in order of how much damage they do.

### "Real-time" is not achievable, and is not wanted

F5 measured it. Vendor cloud APIs sit **6 to 14 hours behind** a nocturnal event, and WHOOP recovery data **does not exist until the sleep cycle closes**. There is no in-sleep query on any cloud API. The only genuinely real-time paths are a Wear OS app on the Galaxy Watch (2 to 5 days of build, which is most of the 45-hour budget) or WHOOP's BLE broadcast (1 to 3 hours, but **BPM and RR intervals only**, and untested overnight).

Worse, the illness signal lives in the nocturnal window and is evaluated per night. There is nothing for a real-time system to decide between 02:00 and 07:00. **"Real-time" here buys latency on a decision that is made once a day.** Presenting it as real-time invites a reviewer to ask what the sub-second path is for, and there is no good answer.

### "Multi-agent" is ruled out three independent times

The lecture's own comparison says single agent is the best fit for bounded, single-domain tasks and that multi-agent gives "multiple agents and logs, harder end-to-end reconstruction" when auditability is assessed. VitalAgent's own ablation shows its extra validate and replan stages contribute nothing, and removing validation is *better* on one tier. And the free-tier rate limit makes N agents times M turns arithmetically impossible to evaluate. Keeping "multi-agent" in the title is a liability with no upside.

### "Sickness prediction" is the wrong output

Wearables measure host response, not pathogens. Influenza, COVID, RSV, a cold and a bacterial infection produce broadly the same systemic signature. The lecture names **"open-ended diagnosis" as a poor fit** for agents outright. The FDA's revised wellness boundary (6 Jan 2026) permits alerts only if they do not name a disease, do not characterise output as pathological, do not state clinical thresholds, and do not provide ongoing disease monitoring. An Oura class action was filed on 20 August 2026 over accuracy claims. The output must be a **disposition about a deviation**, not a prediction about a disease.

### "Detects physiological deviations" is the commoditised half

NightSignal is Apache-2.0, under 100 lines, and achieves 80% sensitivity with a 3-day median lead in a 3,318-participant prospective deployment. Building a detector and attaching an LLM to it is precisely the "smartwatch plus LLM demo" failure mode. **The detection layer is infrastructure we should borrow, not contribute.**

### Answering the specific challenge questions

**Is the problem already solved by Oura and WHOOP?** The *detection* half, yes, and better than we will do. The *precision* half, emphatically not. Independent evaluation (Northwell/Fitbit, JMIR 2024) measured **PPV of 4%**: 665 alerts across 470 people, roughly twenty-four false alerts per true one. The only randomised controlled trial in the field (COVID-RED, n=17,825) found 93.8 to 99.2% sensitivity at **0.8 to 4.2% specificity**. Commercially this category is shipped; scientifically it is unsolved.

**Is there meaningful technical novelty left?** Yes, in one specific place. Across every system reviewed in F3, **nobody models the cost of interrupting the user.** Three proactive health agents' triggering policies were read in source: one uses a hardcoded plus-or-minus 30% against a moving average, one uses agent-authored thresholds with a cooldown, one uses three fixed clinical rules. None weighs information gain against interruption cost. The formal machinery exists (Horvitz's NEVA, 1999; Pauker-Kassirer thresholds; PROMIS adaptive testing) and has never been applied to physiological monitoring.

**Is there a better adjacent problem?** Yes, and it is not obvious. See candidate C3: the deep difficulty in this whole area traces to **not knowing when the event happened**. Inverting to events whose time is known changes the problem from detection to characterisation, gives ground truth by construction, and is self-demonstrable in two weeks.

**Can agentic AI materially improve it?** Only through the asking decision and state across multi-night waits. Three numbers make that case: confounder nights outnumber prodrome nights **20 to 40 : 1**; five confounders are **not separable** on consumer channels; and roughly **45% of measured false alerts had askable causes**. Without those numbers the agent would be decoration.

**What makes it more than a demo?** An explicit, measurable decision policy that can be compared against never-ask and always-ask; a belief state outside the LLM so the arithmetic is auditable; and an evaluation whose oracle answers are real human self-reports rather than values we invented.

**What can be experimentally evaluated in two weeks?** The asking policy, via the dataset-pairing design in doc 10 section 11. Not clinical validity, and not detection on ourselves.

---

## Part 2: Should the named capabilities be separate projects, or one system?

Asked directly, so answered directly.

| Capability | Verdict |
|---|---|
| Physiological anomaly triage | **One system.** It is the trigger for everything else |
| Competing-cause / hypothesis analysis | **One system.** It *is* the belief state |
| False-alert reduction | **One system.** It is the outcome metric, not a component |
| Active questioning | **One system.** It is the policy acting on the belief state |
| Uncertainty-aware inference | **One system.** It is the belief state's representation |
| Contextual evidence acquisition | **One system.** It is what a question *is* |
| Longitudinal personalization | **One system**, as a property of the baseline layer and the per-user priors |
| **Multimodal sensor conflict resolution** | **Genuinely separable.** It answers a different question ("can this system say anything today?") and can stand alone. See C5 |

Six of the eight are not components of a system, they are **the same decision loop described from different angles**. Splitting them would be artificial in exactly the way the prompt warns against: you cannot have active questioning without a belief state, and a belief state with no policy is inert.

**But there is a trap here, and the archived prior work fell into it.** Its ranking exercise selected the candidate that was explicitly the union of all the others, which is not selecting. The correct position is: **one system, one claim.** The capabilities cohere; the *claim* must stay single and falsifiable, and every component must earn its place through an ablation that could show it does not.

---

## Part 3: Ten candidate formulations

Each on the 19 requested dimensions. "Resource feasibility" assumes roughly 45 build hours, free Colab/Kaggle GPU, OpenRouter free tier with a low daily cap, and local CPU development.

---

### C1. The original: real-time multi-agent wearable sickness prediction

1. **Problem.** Continuously ingest wearable telemetry, detect deviation, decide whether more evidence is needed, and estimate illness risk in real time using multiple cooperating agents.
2. **Why it matters.** Pre-symptomatic warning could enable isolation and rest before transmission peaks.
3. **Closest systems.** NightSignal, Oura Symptom Radar, WHOOP Health Monitor, Scripps DETECT.
4. **Already solved.** Nocturnal deviation detection, at 80% sensitivity with a 3-day lead, in open-source code.
5. **What remains interesting.** Very little as stated. The interesting part is buried inside "decide whether additional evidence is required" and the title does not foreground it.
6. **Wearable data.** Primary input.
7. **Pretrained ML.** Chronos as a forecast band, marginal value (2.4% over EWMA).
8. **LLM.** Narration of statistical deltas.
9. **Agent.** Weak. "Multi-agent" contradicts three independent lines of evidence.
10. **RAG.** Prodromal timelines.
11. **Interaction.** Morning risk card.
12. **Main challenge.** "Real-time" is unachievable; illness ground truth for our own deployment will not exist.
13. **Evaluation.** Sensitivity and lead time on the Stanford cohort; nothing evaluates the agentic part.
14. **Resource feasibility.** Detector yes; real-time no; multi-agent not evaluable under the rate limit.
15. **Product novelty.** Low. Ships in three commercial products.
16. **Engineering novelty.** Low-medium.
17. **Research novelty.** Low.
18. **Risk.** High risk of reading as a reimplementation with an LLM attached.
19. **Skeptical professor.** *"Stanford published this in 2020 and open-sourced it. What is real-time about a once-a-night decision, why do you need multiple agents, and how did you validate 'sickness' on two healthy people in a fortnight?"*

---

### C2. Confounder-resolving deviation triage with an explicit ask-or-stay-silent policy

1. **Problem.** Given a detected multi-night physiological deviation, maintain an explicit posterior over candidate causes (infection-like immune activation, alcohol, exertion, sleep debt, stress, luteal phase, vaccination, travel, medication, artifact, unexplained), and decide by expected information gain against interruption cost whether to ask the user one targeted question, stay silent, or escalate. Terminate at a typed disposition.
2. **Why it matters.** Measured PPV is 4%. About 45% of false alerts had askable causes. Alarm fatigue is the documented reason people abandon these systems.
3. **Closest systems.** Scripps DETECT (static daily surveys), WHOOP Journal (unconditional daily prompts), Oura tags (manual, passive), Project Hermes (single-author preprint, no code).
4. **Already solved.** Detection; unconditional questioning; passive tagging.
5. **What remains interesting.** Nobody conditions a question on a detected deviation, and **nobody anywhere models interruption cost.** Apple's Vitals notification lists the candidate causes in its own text and then asks nothing.
6. **Wearable data.** Trigger and evidence; nightly cadence; replayed cohort plus own devices.
7. **Pretrained ML.** Chronos as a measured comparison arm, not a component.
8. **LLM.** Free-text to typed slots; question phrasing; explanation with source links; hypothesis proposal. Never scoring, never arithmetic.
9. **Agent.** Central and load-bearing: a bounded episode investigation with state across multi-night waits and a human checkpoint.
10. **RAG.** Necessary for source-linked guidance; measured against inlining for confounder facts.
11. **Interaction.** Silent by default. At most about two questions per week, single-tap, event-contingent. Must be able to conclude "no question needed".
12. **Main challenge.** Building a defensible likelihood table p(answer | cause, question) that encodes recall noise, and proving the policy beats never-ask and always-ask.
13. **Evaluation.** The dataset-pairing design: Stanford for detection, PMData for confounder attribution, with PMData's **real self-reports revealed only when the agent asks**. Injected +4 bpm 4-day bumps with an amplitude-duration sweep.
14. **Resource feasibility.** Good. Everything but the LLM is local CPU; 320 multiply-adds for the policy; caching makes the ablation affordable.
15. **Product novelty.** High. Attacks the documented failure of every shipped product.
16. **Engineering novelty.** High. Explicit belief state outside the LLM, principled policy, real ablation.
17. **Research novelty.** Medium-high. The transplant of information-value machinery into physiological monitoring is unpublished; Project Hermes is adjacent and must be read first.
18. **Risk.** Medium. Hermes may pre-empt part of the claim. The likelihood table is judgement-heavy and must be documented as such.
19. **Skeptical professor.** *"Apple reduced false alarms with a two-of-five concordance rule and asked nobody. Show me your policy beats that silent baseline, not just a naive threshold."* (This is a fair challenge and must be a required evaluation arm.)

---

### C3. Known-event response modelling, with unexplained residual as the alarm

1. **Problem.** Maintain a ledger of events whose timing the user knows (vaccination, medication change, alcohol, hard training, travel, poor sleep). For each, model the expected physiological response envelope for **this** person. Flag only the **residual deviation that no known event explains**, and ask only to fill gaps in the ledger.
2. **Why it matters.** Every hard part of this problem traces to not knowing when the event happened. Inverting to known-onset events gives **ground truth by construction**, and "is this reaction normal?" is a question people genuinely ask after a jab or a hard block of training.
3. **Closest systems.** CDC V-safe (survey only, no physiology), Oura tags, WHOOP Journal, Stanford's vaccine wearable work.
4. **Already solved.** That vaccines and alcohol produce measurable 24 to 72 hour responses, with published magnitudes (vaccination: HR +9.85% within 48 h, resolving day 3; alcohol: +2.4 to 2.8 bpm and -3.3 to -3.8 ms rMSSD per drink, saturating).
5. **What remains interesting.** Personalised expected-response envelopes; atypical-response detection; and the elegant inversion that **an unexplained residual is exactly what an early-warning system should alert on**. This reframes illness detection as "deviation minus explained variance" rather than "deviation".
6. **Wearable data.** Primary, and the same nightly features.
7. **Pretrained ML.** Forecasting the expected post-event trajectory; a genuine use for a forecast band with covariates.
8. **LLM.** Event extraction from free text; explanation; reassurance framing.
9. **Agent.** Time-gated follow-up across the response window (check at 24 h, 48 h, 72 h), state across waits, escalation if the response is atypical.
10. **RAG.** Strong fit: published reactogenicity tables and expected-response literature are exactly the citable content.
11. **Interaction.** User logs an event, or the agent asks when it sees an unexplained bump. Then scheduled low-friction check-ins during the response window.
12. **Main challenge.** Building per-person envelopes from few prior events; distinguishing atypical response from a coincident infection.
13. **Evaluation.** **Self-demonstrable in two weeks**: the team can deliberately induce events on a schedule (a drink, a hard session, a late night, a flu shot if timing allows) and validate the envelope prospectively. Plus PMData, which annotates exactly these events daily.
14. **Resource feasibility.** **Highest of any candidate.** Ground truth is free, events are inducible, no illness needs to occur.
15. **Product novelty.** High. Nothing does personalised expected-response envelopes.
16. **Engineering novelty.** Medium-high.
17. **Research novelty.** Medium-high. The explained-variance framing is a genuine reformulation.
18. **Risk.** Low-medium. Risk is that it reads as narrower than illness detection unless the residual-alarm inversion is foregrounded.
19. **Skeptical professor.** *"If the user has to log the event, what does your system add over a diary? And how many vaccination events will you actually observe?"*

---

### C4. When should a monitoring agent interrupt a human? (policy as the contribution)

1. **Problem.** Formalise and evaluate the interruption decision for a continuous monitoring agent: given a belief state and a query cost, when is asking worth it? Demonstrate on wearable health, and validate the generality on a second monitoring domain.
2. **Why it matters.** Users already receive about **63.5 notifications a day**. HeartSteps' effect decayed from +66% to +24% over six weeks. The binding constraint is habituation, and no monitoring agent reasons about it.
3. **Closest systems.** Horvitz's PRIORITIES (1999, email, deployed); ContextAgent (NeurIPS 2025, not health); ProAgentBench; "Ask Less, Learn More" (IMWUT 2024, shortens an already-triggered survey).
4. **Already solved.** The decision theory (Howard 1966, Horvitz 1999). Which question to ask, in adaptive testing.
5. **What remains interesting.** **Whether to ask at all**, in a physiological monitoring context, with a cost term that is honestly swept rather than invented.
6. **Wearable data.** The testbed, not the point.
7. **Pretrained ML.** Minimal.
8. **LLM.** Question generation and answer parsing; explicitly *not* the decision maker.
9. **Agent.** The entire contribution.
10. **RAG.** Optional; weak fit.
11. **Interaction.** Central and measured.
12. **Main challenge.** Making a generality claim credible with one real domain and 45 hours.
13. **Evaluation.** Simulated users with non-response, recall error and inconsistency; policy compared against never-ask, always-ask, threshold-ask and random-ask, with paired bootstrap intervals.
14. **Resource feasibility.** Good for one domain; **the second domain is probably unaffordable**.
15. **Product novelty.** Low as a product; it is not one.
16. **Engineering novelty.** Medium.
17. **Research novelty.** **Highest of any candidate.**
18. **Risk.** Medium-high for course project: the brief wants a healthcare workflow prototype, and this framing subordinates the health application to a methods claim.
19. **Skeptical professor.** *"This is a decision-theory paper wearing a wearable. Where is the healthcare workflow, and how do you claim generality from one testbed?"*

---

### C5. Refusal-first monitoring: knowing when the system may not speak

1. **Problem.** Before any inference, decide whether the available data supports **any** statement at all. Detect sensor conflict, non-wear, informative missingness, baseline drift after a device or firmware change, and channel disagreement, and make "I cannot tell you anything about last night, and here is why" a first-class output.
2. **Why it matters.** The lecture names "missing or conflicting source data" as a poor fit for agents. Turning that stated weakness into the product is contrarian and defensible. Stanford's step files are zero-filled, so non-wear can only be inferred from HR; coverage in a sample ran 88.2 to 98.6%. Commercial products silently guess.
3. **Closest systems.** Signal-quality-index literature; Apple's motion filtering; nothing user-facing.
4. **Already solved.** Basic outlier clipping and accelerometer thresholding.
5. **What remains interesting.** Cross-channel corroboration to separate artifact from physiology; a calibrated abstention policy; making epistemic honesty visible.
6. **Wearable data.** Primary, and the quality channel is the subject rather than a filter.
7. **Pretrained ML.** Reconstruction error for artifact isolation.
8. **LLM.** Explaining data-quality faults in lay terms.
9. **Agent.** Moderate: orchestrates checks, asks "did you wear it normally?", escalates to abstention.
10. **RAG.** Weak fit.
11. **Interaction.** Mostly diagnostic, with occasional device-placement prompts.
12. **Main challenge.** Ground truth for artifact versus physiology.
13. **Evaluation.** Block-gap injection into gap-free real data (published precedent); measure abstention precision and the accuracy gain from abstaining.
14. **Resource feasibility.** Good.
15. **Product novelty.** Medium. Reads as a developer utility unless the abstention framing is strong.
16. **Engineering novelty.** High.
17. **Research novelty.** Medium-high. Calibrated abstention in consumer health is underexplored.
18. **Risk.** Emotional flatness. "The system says nothing" is a hard demo.
19. **Skeptical professor.** *"You have built a data-quality filter and called it epistemics. Where is the health decision?"*

---

### C6. Return-to-baseline: recovery tracking after a known illness

1. **Problem.** After a confirmed illness, track recovery against the individual's own pre-illness baseline, decide when it is reasonable to resume normal activity, and flag non-recovery.
2. **Why it matters.** Resting HR does not return to baseline until roughly **79 days** after COVID onset, and 13.7% remain more than 5 bpm elevated past 133 days; sleep recovers around day 24 and steps around day 32. People resume training far too early, and there is a distinctive transient bradycardia phase at days 9 to 15.
3. **Closest systems.** WHOOP recovery score, Oura Rest Mode, Visible (Long COVID pacing).
4. **Already solved.** That recovery is slow, with published trajectories.
5. **What remains interesting.** Per-person return-to-baseline forecasting and the resume-activity decision, which is genuinely actionable.
6. **Wearable data.** Primary.
7. **Pretrained ML.** Good fit for trajectory forecasting toward a known target.
8. **LLM.** Pacing guidance and explanation.
9. **Agent.** Longitudinal check-ins over weeks; escalation on non-recovery.
10. **RAG.** Return-to-play and post-viral guidance is real, citable, and safety-relevant.
11. **Interaction.** Weekly rather than nightly; low burden.
12. **Main challenge.** Timescale. Recovery runs for months and the project runs for two weeks.
13. **Evaluation.** The Snyder Long COVID dataset is **openly downloadable under ODC-By and ships symptom surveys**.
14. **Resource feasibility.** Medium. Onset is known, which helps, but nobody on the team will conveniently be recovering.
15. **Product novelty.** Medium-high.
16. **Engineering novelty.** Medium.
17. **Research novelty.** Medium.
18. **Risk.** The demo requires a subject who is recovering.
19. **Skeptical professor.** *"You cannot observe a 79-day process in a fortnight. What did you actually measure?"*

---

### C7. Chronic-condition pacing: energy envelope for Long COVID, ME/CFS or POTS

1. **Problem.** Track autonomic instability and exertion to predict and prevent post-exertional symptom crashes, managing a daily energy envelope.
2. **Why it matters.** Millions live with unpredictable crashes triggered by minor exertion, and pacing is the only evidence-supported management strategy.
3. **Closest systems.** Visible (Polar armband), Bateman Horne pacing protocols.
4. **Already solved.** Real-time heart-rate pacing alerts.
5. **What remains interesting.** Predictive crash forecasting; the ethics and design of a system whose advice is "do less".
6. **Wearable data.** Orthostatic HR response, HRV volatility, activity.
7. **Pretrained ML.** Multi-day stability forecasting.
8. **LLM.** Compassionate interaction; this population is poorly served and highly sensitive to tone.
9. **Agent.** Daily budget management with proactive warnings.
10. **RAG.** Specialist consensus guidance; strong fit and safety-critical.
11. **Interaction.** Daily, high stakes, high trust requirement.
12. **Main challenge.** No crash-labelled continuous wearable dataset. Also a vulnerable population, which raises real ethical questions for a course project prototype.
13. **Evaluation.** Snyder Long COVID data helps; crash labels do not exist.
14. **Resource feasibility.** Low-medium.
15. **Product novelty.** **Very high.**
16. **Engineering novelty.** Medium-high.
17. **Research novelty.** High.
18. **Risk.** **Highest of any candidate.** Data scarcity plus a vulnerable population plus advice with real consequences.
19. **Skeptical professor.** *"Where did you get validated crash telemetry, and what is your ethical justification for prototyping advice for this group?"*

---

### C8. Cycle-aware personalised baselines

1. **Problem.** Model menstrual cycle phase from wearable signals and correct the personal baseline for it, so luteal-phase physiology stops generating spurious illness alerts.
2. **Why it matters.** This is the **worst confounder in the entire problem**: Goodale 2019 (n=193, 708 cycles) measured wrist temperature +0.44 C, HR +3.91 bpm, respiratory rate +0.60 br/min and HRV -0.32 ms. **All four channels move in the infection direction**, on roughly 45% of days, with magnitude larger than the mean vaccine response. Roughly half of all users are affected and no illness-detection system corrects for it.
3. **Closest systems.** Natural Cycles (contraception, FDA-cleared), Oura cycle insights.
4. **Already solved.** Temperature-based ovulation estimation.
5. **What remains interesting.** Using phase as a **covariate in an anomaly detector** rather than as a standalone feature, and quantifying the false-alert reduction it buys.
6. **Wearable data.** Primary.
7. **Pretrained ML.** Periodicity modelling.
8. **LLM.** Minor.
9. **Agent.** Weak. This is a modelling correction, not a decision loop.
10. **RAG.** Weak.
11. **Interaction.** One question at enrolment, then modelled.
12. **Main challenge.** Needs multiple cycles of history; new users are unresolvable, which is precisely why F8 grades it "NO from raw physiology".
13. **Evaluation.** Measurable false-alert reduction on a menstruating cohort, if one is obtainable.
14. **Resource feasibility.** Medium; depends entirely on data.
15. **Product novelty.** High, and socially valuable.
16. **Engineering novelty.** Medium.
17. **Research novelty.** Medium.
18. **Risk.** **This is a component, not a project.** Poor fit for an agentic AI brief since the agentic content is near zero.
19. **Skeptical professor.** *"This is a good feature. Where is the agent?"*

---

### C9. A benchmark and evaluation harness for agentic health monitoring

1. **Problem.** Build the missing evaluation infrastructure: a simulated-oracle environment over confounder-annotated real data, an adversarial suite, precise metric definitions, and reference baselines, so that agentic health monitors can be compared at all.
2. **Why it matters.** F7 found **no published test suite for consumer agentic health monitoring**. F6 found the standard metrics are broken (random scores reach 0.969 point-adjusted F1). The Epic Sepsis Model's AUC fell from 0.76-0.83 to 0.63 once the detection window was defined correctly.
3. **Closest systems.** AgentDojo, AgentClinic, VitalBench, TSB-AD, HealthBench.
4. **Already solved.** Benchmarks for clinical QA and for agent security, separately.
5. **What remains interesting.** The simulated oracle over **real self-reports**, and metric definitions that survive the point-adjustment critique.
6. **Wearable data.** The substrate.
7. **Pretrained ML.** As reference baselines.
8. **LLM.** The system under test.
9. **Agent.** The object of study.
10. **RAG.** As a tested component.
11. **Interaction.** Simulated.
12. **Main challenge.** The brief requires a working prototype; a benchmark alone may not satisfy it.
13. **Evaluation.** Self-referential, which is a genuine weakness.
14. **Resource feasibility.** Good. Most of it is needed for any other candidate anyway.
15. **Product novelty.** Low.
16. **Engineering novelty.** High.
17. **Research novelty.** High, and it is the most reusable output.
18. **Risk.** Rubric mismatch. "Prototype" is a graded deliverable.
19. **Skeptical professor.** *"A benchmark with only your own system on it is not a benchmark."*

---

### C10. Care-team-facing escalation triage for home monitoring

1. **Problem.** Reframe to the clinical seam: collect home vitals, triage which deviations warrant care-team attention, draft a structured handover, and escalate. The human in the loop is a clinician, not the patient.
2. **Why it matters.** The lecture places most agent value "between visits" and lists **NUHS@Home vitals chatbot, collects vitals at home, escalates to the care team** as a Singapore example. Capacity, not knowledge, is the stated constraint.
3. **Closest systems.** NUHS@Home, Current Health, Huma, Biobeat.
4. **Already solved.** Threshold-based RPM alerting, widely deployed.
5. **What remains interesting.** Triage and prioritisation under a fixed clinician time budget, which is a queueing problem with real utility.
6. **Wearable data.** Primary.
7. **Pretrained ML.** Deterioration scoring.
8. **LLM.** Structured handover drafting, which is a well-evidenced agent use.
9. **Agent.** Strong: draft, pend, escalate, with the clinician signing. Maps perfectly onto "agents draft, validators check, people sign".
10. **RAG.** Local protocols and escalation criteria.
11. **Interaction.** Clinician-facing dashboard with approve/edit/reject.
12. **Main challenge.** **We have no clinician and no patients.** Everything would be simulated.
13. **Evaluation.** Simulated queue; triage ordering versus a gold standard we would have to invent.
14. **Resource feasibility.** Good technically, weak evidentially.
15. **Product novelty.** Low-medium; this is a crowded commercial space.
16. **Engineering novelty.** Medium.
17. **Research novelty.** Low.
18. **Risk.** Entirely simulated stakeholders. Also loses the personal-tool goal completely.
19. **Skeptical professor.** *"You have modelled a clinical workflow you have never observed. What is your evidence for the triage criteria?"*

---

## Part 4: Ranking

Not by averaging subjective scores. Doc 00 section 4.3 criticised the archived work for exactly that, and averaging self-assigned numbers manufactures precision rather than a decision. Instead: rank against the four constraints that actually bind, and state where each candidate fails.

**The binding constraints:** (a) it must be evaluable with data we can obtain in two weeks; (b) it must satisfy the the course prototype and governance requirements; (c) it must survive the "smartwatch plus LLM" criticism; (d) it must fit roughly 45 build hours under a low LLM rate limit.

| Rank | Candidate | Evaluable? | Rubric fit | Survives (c)? | Fits budget? | Fails on |
|---|---|---|---|---|---|---|
| **1** | **C2** Confounder-resolving triage with an ask policy | Yes, via dataset pairing | Excellent | Yes | Yes | Project Hermes overlap; likelihood table is judgement-heavy |
| **2** | **C3** Known-event response, unexplained residual as alarm | **Yes, ground truth by construction** | Excellent | Yes | Yes | Reads narrower unless the inversion is foregrounded |
| **3** | **C5** Refusal-first monitoring | Yes, injection precedent | Good | Yes | Yes | Hard to demo; emotionally flat |
| 4 | **C4** Interruption policy as the contribution | Partly | **Weak** (subordinates the health workflow) | Yes | One domain only | Rubric mismatch |
| 5 | **C6** Return-to-baseline recovery | Partly | Good | Yes | Yes | Cannot observe a 79-day process in 14 days |
| 6 | **C9** Benchmark and harness | Self-referential | **Weak** (prototype is assessed) | Yes | Yes | No system under test but our own |
| 7 | **C10** Care-team escalation triage | Simulated only | Excellent | Marginal | Yes | No real stakeholders; loses personal-tool goal |
| 8 | **C1** The original | Detection only | Good | **No** | Real-time no, multi-agent no | The agentic claim is unevaluable |
| 9 | **C8** Cycle-aware baselines | Data-dependent | **Poor** (no agent) | N/A | Yes | Component, not project |
| 10 | **C7** Chronic-condition pacing | **No** | Good | Yes | No | No labels; vulnerable population; ethics |

---

## Part 5: Top three and the trade-offs

### First: C2, confounder-resolving deviation triage

**Why.** It is the only candidate where every required rubric capability is load-bearing rather than bolted on, and where the evidence supplies both the motivation (4% PPV, 45% askable, 20-40:1 base rates) and the gap (nobody models interruption cost). The evaluation design exists and is non-circular. The agentic content is genuine because the next action really does depend on the ambiguity of the intermediate result.

**Trade-off.** Project Hermes reports approximately this result already, which is why reading it is a blocking task. The likelihood table is the weakest joint: it encodes judgement, and it must be presented as an elicited prior with a sensitivity analysis, not as fact. And it must beat Apple's silent concordance baseline, not just a naive threshold.

### Second: C3, known-event response with unexplained residual as the alarm

**Why.** It is the strongest *feasibility* play and the most intellectually interesting reformulation. Every hard problem here traces to unknown event timing, and this inverts that. Ground truth comes free, events are deliberately inducible within two weeks, and the residual framing turns illness detection into "deviation minus explained variance", which is both more honest and more novel than "deviation".

**Trade-off.** Weaker headline. "We predict your response to a known event" sounds smaller than "we detect illness early", even though it is better founded. Mitigated entirely by foregrounding the residual inversion, at which point it *is* an early-warning system with a better epistemology.

### Third: C5, refusal-first monitoring

**Why.** Genuinely contrarian, directly answers a stated poor-fit condition from the lecture, and produces something no commercial product does: a system that knows when to say nothing. Engineering novelty is high and the evaluation has published precedent.

**Trade-off.** Weakest demo. Three minutes of presentation in which the system declines to speak is a hard sell, and it risks reading as a data-quality filter with ambitions.

### The combination worth considering

C2 and C3 are not really competitors. **C3 is the mechanism that makes C2's belief state work.** A ledger of known events with modelled response envelopes is precisely how you compute "how much of tonight's deviation is already explained", and the residual is what the asking policy then reasons about. C5's abstention logic is the same machinery answering "is there enough data to have a belief at all".

The honest unified formulation is therefore something like: **a bounded agent that explains physiological deviations by subtracting what known events already account for, asks at most one targeted question when and only when the expected information gain exceeds the cost of interrupting, abstains when the data cannot support a statement, and never names a disease.**

That keeps one claim (the asking policy earns its interruptions), while C3 supplies the explanatory model and C5 supplies the abstention path. It is not the archived work's "union of everything wins" error, because the components are one decision loop rather than a feature list, and each still has to survive its own ablation.

---

## Part 6: Decisions taken in discussion (2026-08-30)

### D1. Diagnosis-shaped output is IN SCOPE. My earlier "non-negotiable" was overstated.

**the author's position:** produce a diagnosis where possible, provided the response is grounded in the user's own data and in retrieved documents, with red flags and anything clinically important routed to a doctor or hospital.

**Correction to my earlier claim.** I said no-diagnosis was non-negotiable. That conflated three separate things, only one of which is a real limit.

| What I bundled together | What it actually is |
|---|---|
| FDA wellness boundary (6 Jan 2026) | A constraint on what a **marketed product** may claim without becoming a regulated device. This is a course project prototype and a personal tool. It constrains our *marketing language*, not our reasoning |
| Lecture calling "open-ended diagnosis" a poor agent fit | An **engineering** argument about machine-checkability, reversibility and provenance. It is advice about use-case selection, not a prohibition |
| **Identifiability** | **The only genuine hard limit**, and it is physics, not policy |

**The real limit, stated precisely.** Wearable *sensors* measure host response, not pathogens. Influenza, COVID, RSV, a common cold and a bacterial infection produce broadly the same autonomic and thermal signature. **No amount of RAG fixes this, because retrieval cannot add information that is absent from the sensor stream.**

**But that limit dissolves the moment symptoms enter.** Symptoms carry pathogen-discriminating information that physiology does not: anosmia points to COVID; abrupt onset with high fever and myalgia points to influenza; sore throat with fever and no cough raises streptococcal pharyngitis (the Centor criteria are a real, citable, grounded decision rule). This produces an important reframing:

> **The asking policy is not merely confounder rejection. It is the evidence acquisition that makes grounded differential reasoning possible at all.**

That strengthens the project rather than weakening it. The agent's questions now serve two purposes with one mechanism: ruling out benign causes, and acquiring the symptom evidence that licenses a differential.

**What is in scope as a result:**
- A **ranked differential over candidate causes**, with calibrated probabilities, each claim linked to a retrieved source.
- Named conditions **when symptom evidence supports them**, presented as a differential with explicit uncertainty rather than a single verdict.
- Deterministic red-flag interception routing to a doctor or emergency care, outside and above the model.

**What stays out, and this is a narrow list:**
- A confident single named diagnosis from **physiology alone with no symptom evidence**. That is the genuinely unsupportable case.
- Any claim of clinical validation we have not performed.
- Treatment or prescription advice.

**Why this is better, not merely permitted.** A single label from wearable data is the thing a reviewer would attack. A ranked differential with calibrated probability, evidence links and an explicit "what would distinguish these" is what the lecture's own six evaluation metrics reward, since calibration, unsupported-claim rate and citation accuracy are three of them. It is also what a clinician actually produces.

**Consequence for the candidates.** This *strengthens* C2 (the asking policy now unlocks diagnosis, not just confounder rejection), makes RAG unambiguously **NECESSARY** rather than arguable, and slightly weakens C5, whose refusal-first posture pulls against it. C3 is unaffected and still complementary. Gate G10 is updated accordingly.

### D2. Hardware is confirmed as Samsung Galaxy Watch, automatic channels only

**the author's position:** full automatic Galaxy Watch data (heart rate, sleep, exercise). **No manual input data at all** (no food, no nutrition, no tags).

**What this means for available channels.** Per F5, the ungated Samsung paths have real gaps: the Samsung Health Data SDK has **no HRV type and no respiratory-rate type**, and Samsung Health is reported not to write HRV, breathing rate or resting HR into Health Connect. Skin temperature exists as a type but is not in Samsung's published sync list and is model-dependent (Galaxy Watch 5 and later).

So the realistic automatic channel set is **nocturnal heart rate, sleep stages and duration, and activity/steps**. That is:

- **The same channel set as the open Stanford cohort** (heart rate, steps, sleep), which is a convenient alignment: methods developed on the public data transfer directly to personal data with no channel mismatch.
- **Exactly NightSignal's channel set**, which is the best-evidenced detector in the field. So the channel limitation costs us nothing on the detection side.
- **Not** the "biophysical triad". Skin temperature and respiratory rate are out unless the on-watch Sensor SDK route is taken, which F5 estimates at 16 to 40 hours and is above the cut line.

**The absence of manual logging is a feature, not a problem.** Commercial systems depend on manual tags: Oura tags, WHOOP's daily journal. the developer does not fill these in, which is exactly the behaviour the EMA attrition literature predicts and exactly why unconditional logging fails. **A system that asks rarely, and only when the answer would change a decision, is the direct answer to the user's own observed behaviour.** This is a strong and honest personal-use motivation, and it belongs in the report's introduction.

**Open hardware questions:** the specific Galaxy Watch model (determines skin-temperature availability), and what the "Download personal data" export actually contains for this device. The export is ungated and takes minutes; running it is the highest-value next hardware action.

---

## Part 7: What I need from you before we choose

1. **Does the "no diagnosis" constraint bother you?** It is non-negotiable for safety and regulatory reasons, but it changes the pitch from "detects illness" to "explains deviations". I want to know if that feels like a downgrade to you, because if so we should talk about how to frame it rather than discover the tension in week two.

2. **How do you feel about deliberately inducing events on yourselves** (a hard training session, a late night, alcohol, and a vaccination if the timing happens to work)? C3's feasibility advantage depends on it. It is safe and ordinary behaviour, but it is a real commitment and it needs to start early to be useful.

3. **Is the second teammate's WHOOP actually available for the whole two weeks**, and are both of you willing to retrospectively annotate a few months of history? That is what turns N=2 from a weakness into the only confounder-labelled real data anyone in this space has.

4. **Portfolio versus grade, when they conflict.** C4 has the highest research novelty and the worst requirements fit. If they diverge, which wins?

5. **Do you want me to read Project Hermes now?** It reports roughly C2's target result. If it is strong, C2's claim needs narrowing and C3 becomes more attractive. This is the single highest-value thing I can do before we decide.
