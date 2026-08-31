# 04. Structured Research Checklist

**Status:** Phase 1 output. This is the Phase 2 work plan.
**Date:** 2026-08-30

## How to use this

Total research budget: **2 to 3 days** out of the 2-week envelope. Anything longer eats the build.

Every item states the **decision it unblocks**. If an item does not unblock a decision, it is reading for its own sake and should be cut. Items marked **[SPIKE]** are hands-on: download something, run something, print something. Items marked **[LIT]** are reading. **[ASK]** items are questions for the author and cost nothing but a message.

Track 0 is a hard gate. Do not start Tracks B through F until Track 0 and Track A are done, because their answers change what is worth researching.

Findings go in `research/findings/` as one file per track, each ending with an explicit **"what this means for the design"** section. A finding without a design implication has not been finished.

---

## Track 0: Cheap answers first (target: same day)

| # | Item | Type | Unblocks |
|---|---|---|---|
| 0.1 | Confirm the deliverable, audience, deadline, and requirements or success criteria | [ASK] | U3, and the whole scope envelope |
| 0.2 | Confirm device ownership, exportable history depth, and channel availability | [ASK] | U4, decision gate G1 |
| 0.3 | Confirm LLM provider, API budget, and whether local inference is required | [ASK] | U15 |
| 0.4 | Confirm available compute (CPU only, or GPU and how much VRAM) | [ASK] | U16, and whether area I is viable at all |
| 0.5 | Confirm realistic working hours per day across the two weeks | [ASK] | Scope sizing |
| 0.6 | Confirm whether a live-device demonstration is valued or whether replay is acceptable | [ASK] | Decision gate G9, and area M budget |

---

## Track A: Data reality check (target: half a day, highest priority)

This track is where the project is most likely to be saved or killed. It is deliberately hands-on. **Do not substitute reading papers for downloading data.**

| # | Item | Type | Unblocks |
|---|---|---|---|
| A.1 | Enumerate candidate public datasets. For each, record: access mechanism (open / registration / DUA / institutional), licence, size, participant count, date range | [SPIKE] | U1 |
| A.2 | For every dataset that is actually obtainable: download it, load it, and print the real schema. Record exactly which channels exist (HR? HRV? skin temperature? respiratory rate? sleep stages? steps?) and at what cadence | [SPIKE] | U1, and area J (whether any DSP is needed) |
| A.3 | Quantify coverage and missingness per participant: participant-days available, fraction of nights with valid data, longest gaps, non-wear rate | [SPIKE] | U5, U13, and baseline window length in area D |
| A.4 | Count the labelled illness episodes usable for evaluation, and record how onset is defined and dated (PCR, antigen, self-report, clinician) and its granularity | [SPIKE] | U13, and the entire evaluation design |
| A.5 | Search every obtainable dataset for **any** confounder annotation: alcohol, exercise, stress, sleep, menstrual phase, vaccination, travel, medication | [SPIKE] | U2, the circularity problem |
| A.6 | If the user owns a device: export their own data and run A.2 through A.5 on it, including how far back the history goes | [SPIKE] | U4, decision gate G1 |
| A.7 | Verify the exact identity and access status of the specific cohorts the prior work named, since the archived citations are unreliable | [LIT] | U1, and doc 00 audit closure |

**Exit criterion for Track A.** A one-page table: dataset name, obtainable yes/no, channels present, cadence, participant-days, illness episodes, confounder labels present yes/no. Everything downstream is conditioned on that table.

---

## Track B: Evaluation methodology (target: half a day, second priority)

Deliberately placed before the modelling tracks. Designing the experiment before choosing the model is the difference between a result and a demo.

| # | Item | Type | Unblocks |
|---|---|---|---|
| B.1 | Establish the correct event-based scoring protocol for early-warning detectors. Explicitly determine the current recommended practice given published criticism of point-adjusted F1 and of standard anomaly-detection benchmarks | [LIT] | U12, the entire results section |
| B.2 | Fix the metric set and define each precisely: episode-level sensitivity, alerts per user-week, positive predictive value at realistic base rate, detection lead time distribution, calibration (Brier / reliability) | [LIT] | U12, and the claims in doc 01 section 1.3 |
| B.3 | Verify the headline numbers cited in the archived work at their primary sources: sensitivity, lead time, alert rate, AUC, for each named system. Record verified / corrected / unfindable | [LIT] | Doc 00 audit closure, and the comparison baseline |
| B.4 | Compute the realistic base rate and PPV explicitly for the population and target condition we pick, and record the assumptions | [SPIKE] | Doc 01 section 1.3, and the project's motivating argument |
| B.5 | Determine how the active-query claim can be evaluated **without circularity** given the expected absence of confounder labels. Identify the accepted practice for simulated-oracle evaluation and for reporting sensitivity to generative assumptions | [LIT] | U2, the sharpest anticipated objection |
| B.6 | Determine how to evaluate an interaction policy without human subjects: simulated user design, modelling non-response and recall error | [LIT] | U11, decision gate G7 |
| B.7 | Do a power / feasibility sanity check: with the episode count from A.4, what difference between two detectors is even detectable | [SPIKE] | U13, right-sizing every claim |

**Exit criterion for Track B.** A written evaluation protocol, fixed before any model is chosen, that a skeptical reviewer could not dismiss on methodology alone.

---

## Track C: Prior systems and the state of the art (target: half a day)

| # | Item | Type | Unblocks |
|---|---|---|---|
| C.1 | For each academic cohort study: device, channels, algorithm, operating point, cohort size, released code, released data | [LIT] | Area E, the baseline bar |
| C.2 | For each commercial product: what it claims, what channels it uses, what it demonstrably cannot do, and what users complain about | [LIT] | Area E, the product-novelty argument |
| C.3 | Locate and inspect any released reference implementation of a published detector. Assess whether it is directly runnable as our baseline arm | [SPIKE] | Area D, the control arm |
| C.4 | Identify published systems that combine wearable monitoring with LLM agents, and record specifically what each does and does not do | [LIT] | Area H, and the novelty argument |
| C.5 | Explicitly answer: what has nobody done? Write the gap statement in two sentences | [LIT] | The project's contribution claim |

---

## Track D: Confounder physiology (target: half a day)

| # | Item | Type | Unblocks |
|---|---|---|---|
| D.1 | For each confounder in the doc 01 list: which channels move, direction, magnitude, onset latency, duration, and recovery shape. Cite each | [LIT] | Area F, the hypothesis set |
| D.2 | Assess pairwise separability: given only the channels we will actually have (from A.2), which confounders are distinguishable from infection by sensors alone and which are genuinely not | [LIT] | P2 identifiability, and which questions are worth asking |
| D.3 | Derive the question bank: the minimal set of user-answerable questions that maximally separate the hypothesis set | [SPIKE] | Area C, the query policy |
| D.4 | Record base rates for each confounder (how often does an adult drink, train hard, sleep badly, travel) since these are the priors in the attribution model | [LIT] | Attribution likelihoods, and the simulator if one is needed |

**Exit criterion for Track D.** A confounder table with cited magnitudes and time courses, plus a separability matrix. This artifact is reusable as the knowledge base, the simulator specification, and the RAG corpus, so it is worth doing properly once.

---

## Track E: Modelling head-to-heads (target: half a day, only after A and B)

These are experiments, not surveys. Each is small.

| # | Item | Type | Unblocks |
|---|---|---|---|
| E.1 | Implement the strongest simple baseline: personalized rolling median plus MAD, with CUSUM or EWMA persistence, on real data from Track A | [SPIKE] | Area D, the control arm |
| E.2 | Determine the baseline window length empirically rather than by assumption, and record sensitivity to that choice | [SPIKE] | Area D |
| E.3 | Run at least one zero-shot time-series foundation model on the same data and compare against E.1 under the Track B protocol | [SPIKE] | U6, decision gate G3 |
| E.4 | Test whether an LLM, given identical features, attributes causes better than a simple rule set or logistic model | [SPIKE] | U7, decision gate G4 |
| E.5 | Record compute, latency, and dependency cost for each option | [SPIKE] | U16, feasibility |

**Exit criterion for Track E.** A comparison table with numbers on real data. Whichever way it comes out, it is a reportable finding, and it prevents including a component for decoration.

---

## Track F: Agent, policy, and grounding design (target: half a day)

| # | Item | Type | Unblocks |
|---|---|---|---|
| F.1 | Survey formalisms for the ask/don't-ask decision and pick one on cost-versus-rigour grounds. Specifically check whether exact expected information gain over a small discrete hypothesis set is cheap enough to implement directly | [LIT] | U8, decision gate G4, the contribution claim |
| F.2 | Find empirical evidence for the interaction cost term: how many prompts per week users tolerate, and attrition curves for micro-surveys | [LIT] | Area K, the c_q parameter |
| F.3 | Decide the agent-computer interface: typed deterministic tools versus generated code, argued from our fixed feature set rather than by analogy to prior systems | [LIT] + [SPIKE] | U14, decision gate G5 |
| F.4 | Count the distinct facts the system needs to ground. Then decide whether retrieval beats inlining, and design the test that would show it | [SPIKE] | U9, decision gate G6 |
| F.5 | If retrieval is warranted: identify openly licensed, bulk-retrievable medical corpora and check licence terms | [LIT] | U9 |
| F.6 | Fix the grounding evaluation: citation precision, faithfulness, hallucination rate, and whether an LLM judge is used and how its bias is controlled | [LIT] | U10 |
| F.7 | Draft the safety envelope: red-flag thresholds, the deterministic bypass path, output contract, and disclaimer language | [LIT] | Area L, U17 |

---

## Track G: Feasibility and scoping (target: end of research phase)

| # | Item | Type | Unblocks |
|---|---|---|---|
| G.1 | Convert Track A through F findings into resolved positions on each decision gate in doc 06 | [LIT] | Phase 3 |
| G.2 | Identify the top three ways this project fails, and the cheapest mitigation for each | [LIT] | Risk plan |
| G.3 | Size the build against the actual hours available (from 0.5), with an explicit cut list ordered by what gets dropped first | [LIT] | Phase 3 |
| G.4 | Write the two-sentence claim the finished project will make, and confirm the planned evidence actually supports it | [LIT] | Everything |

**Exit criterion for the whole research phase.** Doc 06's decision gates are all closed with a recorded position and the evidence behind it, and G.4's two sentences are written and defensible. Only then does architecture design begin.

---

## Explicitly out of scope for the research phase

- Deep reading on wearable vendor OAuth flows, unless 0.2 and 0.6 make live ingestion a real requirement.
- Foundation model architecture internals beyond what is needed to run them.
- Multi-agent orchestration frameworks. No evidence yet that more than one model invocation per event is needed.
- Raw waveform DSP, unless A.2 shows the data arrives as raw waveforms.
- Front-end framework comparison. Deferred to build planning and deliberately minimized.
