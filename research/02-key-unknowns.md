# 02. Key Unknowns That Must Be Resolved Before Any Architecture Decision

**Status:** Phase 1 output.
**Date:** 2026-08-30

Unknowns are tiered by how much damage a wrong guess does. Tier 0 items can invalidate the whole project; they are resolved first and in order. Nothing in Tier 1 should be researched in depth until Tier 0 is settled, because Tier 0 answers change which Tier 1 questions even matter.

Each unknown states: the question, why it bites, what evidence resolves it, and what changes depending on the answer.

---

> ## UPDATE 2026-08-30: U1 and U2 largely answered
>
> Evidence in `findings/F1-clinical-infection-studies.md`. Summary of what is now known:
>
> **The Stanford cohort is openly downloadable with no registration**, and its size was verified byte-for-byte. Phase 2 is 5.54 GB compressed, 2,123 participant folders, roughly 36 GB uncompressed. Phase 1 is 378 MB, 117 participants plus 32 sleep files. **But both open archives contain heart rate and steps only, and neither carries illness labels or confounder annotations.** Alavi's team collected alcohol, exercise, travel, stress and vaccination surveys and did not release them.
>
> So the answer to U1 is the bad-but-survivable middle case anticipated in the original entry: plenty of realistic longitudinal telemetry, but only two channels, and no labels in the open archive. The "biophysical triad" fusion the archived prior work built its architecture on is **not implementable on the openly available data**. That prediction is now confirmed rather than suspected.
>
> **Labelled alternatives, ranked by obtainability:**
>
> | Dataset | Access | Contents | Verdict |
> |---|---|---|---|
> | Snyder Long COVID (Stanford Digital Repository) | **Open, ODC-By** | Ships symptom surveys | Best gettable labelled option. Investigate first |
> | CovIdentify (PhysioNet) | Credentialed + CITI training + DUA | Daily-aggregate RHR and steps, 132 positive / 1,157 negative | Obtainable but the credentialing takes time. Start now if wanted |
> | COVID-RED | Gated, UMC Utrecht request form + DSA | **The only dataset with explicit confounder annotations** (daily diary of alcohol, drugs, medication) | The one that would answer U2 properly. Request immediately; assume it will not arrive in time |
> | TemPredict | Effectively closed (Oura data policy; classifier code blocked by the US Department of Defense) | - | Rule out |
> | DETECT | Gated, register-and-pledge plus author email | - | Unlikely within timeframe |
> | Warrior Watch | No data statement at all | - | Rule out |
> | Li 2017 Lyme | URL dead (HTTP 404) | - | Rule out |
>
> **U2 verdict:** confounder ground truth exists in exactly one dataset, and it is gated. The circularity problem stands. The planned mitigations (real-data anchor plus a clearly-labelled semi-synthetic policy benchmark with sensitivity analysis, plus the team's own retrospectively annotated history) remain necessary, not optional.
>
> **The single most important number found in Phase 2**, and the anchor for all scepticism: COVID-RED (PLoS ONE 2025) is the only randomised controlled trial in this territory, n = 17,825. Its wearable algorithm achieved 93.8 to 99.2% sensitivity at **0.8 to 4.2% specificity**. Under trial conditions it alerted very nearly everyone. Every impressive figure elsewhere in this literature should be read against that result.
>
> **A clean novelty statement also falls out:** across every clinical system reviewed, the A-to-V schema fields for LLM use, agent use, agent tools and retrieval are "No" everywhere. No published system in wearable illness detection uses an agent at all.

---

## Tier 0: project-existential. Resolve first.

### U1. Does a usable public dataset actually exist, and what is physically inside it?

**Question.** Is there a public, downloadable dataset with (a) longitudinal per-individual wearable telemetry, (b) enough sensor channels to support multi-signal reasoning, and (c) timestamped illness ground truth?

**Why it bites.** The archived prior work assumed this and built an entire recommended architecture on top of the assumption. The specific risk is not "no dataset exists"; it is that the datasets that exist are **thinner than the architecture needs**. A widely cited wearable-infection cohort may contain only minute-level heart rate and step count, with no HRV, no skin temperature, and no respiratory rate. If so, the "biophysical triad" fusion that the prior work called the central insight is **not implementable on the only data we have**, and the design collapses.

**Evidence that resolves it.** Not a literature search. Download the candidate datasets, load them, and print the schema, the per-participant date coverage, the missingness rate, and the number of labelled illness episodes. This is a hands-on spike, not a reading task.

**Candidates to check** (status unknown, all to be verified):
- Stanford / Snyder Lab COVID-19 wearables cohort (Mishra et al.) and the NightSignal follow-up (Alavi et al.)
- TemPredict / Oura cohort (suspected to be access-gated, not open)
- Scripps DETECT (suspected access-gated)
- LifeSnaps (Fitbit, multi-month, with self-report instruments)
- WESAD, PPG-DaLiA, MMASH (stress/activity, not illness; useful for confounders)
- AI-READI, All of Us Fitbit tables, UK Biobank accelerometry (likely gated or wrong modality)
- PhysioNet wearable collections generally

**What changes by answer.**
- Rich multi-sensor + illness labels available: the "triad fusion" framing survives; real-data evaluation is possible.
- HR and steps only: skin temperature and HRV must be dropped or synthesized, which weakens every claim built on them; the project pivots toward what is actually measurable.
- Nothing usable at all: the project must be built on the user's own device data (see U4), or on an explicitly labelled simulation, and the honest claim shrinks from "detects illness" to "demonstrates an architecture."

---

### U2. Does confounder ground truth exist anywhere, and if not, how is the central claim evaluated without circularity?

**Question.** Is there any dataset in which alcohol intake, hard exercise, poor sleep, stress, or menstrual phase are timestamped **alongside** wearable telemetry and illness labels?

**Why it bites.** This is the sharpest methodological problem in the project and the prior work walked straight past it. The proposed contribution is "the agent asks questions to disambiguate confounders, which reduces false alarms." If the confounders are injected by us into a simulator that we also wrote, then the agent is being evaluated on its ability to recover a signal we planted. That is circular, and a competent reviewer will say so in one sentence.

**Evidence that resolves it.** Dataset inspection (as U1). Also a targeted literature check for how the active-learning and human-in-the-loop-ML communities handle exactly this (simulated oracles, semi-synthetic injection with held-out generative parameters, sensitivity analysis over injection assumptions).

**What changes by answer.**
- Real confounder labels exist somewhere: this becomes the headline empirical result and the project has a strong evaluation spine.
- They do not exist (expected): the evaluation must be restructured into (i) descriptive real-data results on detection, plus (ii) a clearly-labelled semi-synthetic policy benchmark whose generative assumptions are stated, varied, and reported as a sensitivity analysis rather than a point estimate. The framing shifts from "our system reduces false alarms in the world" to "under stated assumptions about confounder prevalence and answerability, the active policy dominates the passive baseline across the assumed range." That is a defensible claim. The unqualified version is not.

---

### U3. What is the deliverable, and what is it graded or judged on?

**Question.** Is this course project (a healthcare AI course is in the same workspace), a portfolio piece, a capstone, or a prototype intended for personal use? What artifacts are required, and what is the requirements or audience?

**Why it bites.** It changes the optimum completely. A rubric that rewards clinical reasoning and evaluation rigour points at a small, deeply evaluated system. A rubric that rewards system engineering points at a broader working stack. A portfolio piece points at a polished demo. These are different projects with the same title.

**Evidence that resolves it.** Direct answer from the developer. Listed in doc 07.

---

### U4. What device and personal data does the user actually have?

**Question.** Does the author own a wearable? Which one? How much historical data can be exported, and at what granularity? Is a live device demonstration valued by the audience?

**Why it bites.** Owning a device with 6+ months of exportable history unlocks a genuinely stronger project: a real N-of-1 longitudinal study on data nobody else has, with the user able to supply real confounder annotations retrospectively (they know when they drank, trained, travelled, or were ill). That partially solves U2, which is otherwise the hardest problem here. It also changes the demo from "replayed cohort data" to "my own physiology."

Conversely, if there is no device, then the two-week window is far too short to collect a personal baseline, and the whole live-ingestion branch must be cut.

**Evidence that resolves it.** Direct answer from the developer. Listed in doc 07.

**What changes by answer.** This is the single largest fork in the project's data strategy and it gates decision gate G1 in doc 06.

---

## Tier 1: architecture-shaping. Resolve after Tier 0.

### U5. What is the honest decision cadence?

Is the meaningful unit of decision the night (one epoch per day) or the hour (intraday streaming)? The prior work asserted nocturnal rollup is superior but also proposed a real-time streaming demo, which is internally inconsistent. Resolve by checking (a) the sampling cadence actually present in the chosen dataset, (b) published evidence on nocturnal versus intraday signal-to-noise, and (c) whether "real-time" is a requirement of the deliverable or a self-imposed constraint.

Consequence: if the answer is nightly, then "real-time" is a presentation choice (time-warped replay), not an architectural one, and a large amount of streaming infrastructure becomes optional.

### U6. Do time-series foundation models beat a simple statistical baseline on this data?

Zero-shot forecasting or reconstruction models (Chronos, MOMENT, TimesFM, and wearable-specific encoders) are proposed as the modern approach. Nobody has shown, in the material we have, that they beat a rolling median plus MAD plus CUSUM on gappy nightly wearable features. They may well not: these series are short, low-dimensional, heavily gapped, and dominated by a single seasonal component, which is the regime where classical methods are strongest.

Resolve by running both on the same data and comparing. This is a small experiment and it is worth more than any amount of reading.

Consequence: if the foundation model does not win, including it anyway is decoration. If it does win, that becomes a legitimate empirical finding worth reporting.

### U7. Can an LLM's cause-attribution beat a simple baseline given identical inputs?

If the LLM receives the same features a logistic regression or a small rule set receives, does it attribute causes better? This is directly testable and currently unknown. It determines whether the LLM's job is *reasoning* or merely *narration*.

Consequence: if the LLM does not add attribution accuracy, its defensible role narrows to question selection, natural-language interaction, and explanation. That is still a real role, but the claim must be stated accordingly.

### U8. What is the cheapest defensible formalism for the ask/don't-ask policy?

Candidate framings to evaluate for implementation cost versus rigour: expected value of information over a small discrete hypothesis set; Bayesian experimental design / expected information gain; active-learning acquisition functions; a bandit formulation with a query budget; a small POMDP solved by lookahead; or an LLM asked to choose with a hand-written cost prompt.

Resolve by reading enough to pick one, then estimating implementation cost. The key insight to check: if the hypothesis set is small (roughly 8 to 12 causes) and questions are few (roughly 6 to 10), then exact expected-information-gain computation is trivial and gives a *provably* principled policy for near-zero effort. If that is true, it is a strong result and it changes what the LLM is for.

### U9. Is RAG justified, and over what corpus?

Two sub-questions. First, what medical corpus is openly licensed and bulk-retrievable (NCBI Bookshelf / StatPearls, PubMed Central open-access subset, MedlinePlus, CDC and WHO guidance, NICE)? Second, and more important: **how many distinct facts does the system actually need?** If the answer is on the order of twenty prodromal-timeline and confounder facts, then a curated prompt beats a vector store on every axis, and RAG is the artificial attachment the brief warns against.

Resolve by drafting the actual knowledge the system must ground, then counting it.

Consequence: RAG is justified if and only if the corpus is large enough that retrieval beats inlining, or the deliverable requires verifiable citations to source documents. Both are checkable.

### U10. How is grounding and factual accuracy measured?

Retrieval quality, citation precision, answer faithfulness, and hallucination rate. Look at established evaluation frameworks and at LLM-as-judge protocols with their known biases. This is needed regardless of whether RAG is included, because the output makes factual health claims either way.

### U11. How is the interaction loop evaluated without recruiting human subjects?

A simulated user (an LLM or a scripted oracle with a known hidden ground-truth state) that answers the agent's questions with realistic noise, refusal, and recall error. Investigate how the dialogue-systems and clinical-decision-support literature does this, including how to model non-response, which is the dominant real-world failure mode.

### U12. How should anomaly detection be scored, given that the standard metrics are known to be broken?

There is a body of work showing that the "point-adjusted F1" convention in time-series anomaly detection is badly misleading, to the point where random scores can outperform published methods, and that several standard benchmarks are flawed. Any evaluation using naive point-wise or point-adjusted F1 is attackable. Determine the current recommended protocol (range-based or event-based precision and recall, or an explicit lead-time-and-false-alarm-rate reporting scheme) before writing any evaluation code.

This is a high-value, low-cost item. It protects the entire results section.

### U13. What are the sample sizes, and what can they support statistically?

If the usable cohort has, for example, on the order of tens of labelled illness episodes, then no comparison between two detectors will reach significance. Establish the achievable N early so that the claims are sized to the evidence rather than the other way round.

---

## Tier 2: implementation-risk. Resolve before building, not before designing.

### U14. Agent-computer interface: typed tools or generated code?

The prior work took the code-generation pattern (LLM writes pandas, sandbox executes) as settled best practice. That pattern exists because its originating system answers *arbitrary open-ended user questions over arbitrary personal data*. Our system has a **fixed, small feature set and a fixed set of computations**. In that regime a handful of typed, deterministic tools with validated arguments is plausibly strictly better: no sandbox, no code-injection surface, no syntax-error retry loop, lower latency, and fully reproducible. Which is right here is an open question, and the answer is not "copy the paper."

### U15. LLM access, cost, latency, and provider.

Available API keys, rate limits, and per-run cost. Whether a local model is required for any privacy claim. Whether latency matters for the demo.

### U16. Compute.

CPU only or GPU available, and how much. Directly gates whether any foundation model larger than a few hundred million parameters is usable.

### U17. Safety and regulatory framing appropriate to the deliverable.

Wellness-tool versus medical-device framing, the disclaimer language that belongs in the output contract, and the deterministic red-flag path. Not a research burden, but it must be written down before any user-facing text is generated.

---

## Dependency order

```
U3, U4 (ask the user, costs nothing, unblocks everything)
 |
 v
U1, U2 (hands-on dataset spikes: what data exists, what labels exist)
 |
 +--> U5, U13 (cadence and sample size fall out of the data)
 |
 +--> U6, U7, U12 (small head-to-head experiments)
 |
 +--> U8, U9, U10, U11 (design-the-evaluation reading)
 |
 v
 U14 .. U17 (implementation risk, resolved during build planning)
```
