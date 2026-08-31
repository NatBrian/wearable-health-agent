# 03. Map of Research Areas

**Status:** Phase 1 output.
**Date:** 2026-08-30

Thirteen areas. For each: what it is, the specific question we need it to answer, and what would change in the project depending on the answer. Areas are ordered by how much leverage they have over the design, not by conventional presentation order.

Areas A, B, and M are load-bearing. Areas E and F are where the prior work concentrated and where it is closest to being usable. Areas C, G, and L are where the prior work is thinnest and where the project's actual contribution is most likely to be found.

---

## A. Data availability, access, and provenance

**What it covers.** Public wearable cohorts with illness labels; access mechanics (open download, registration, data-use agreement, institutional gate); consumer device export paths (Apple Health export, Fitbit/Google export and API, Garmin, Oura API, Samsung Health, Health Connect); third-party aggregators; synthetic and simulated data generators.

**Question we need answered.** Precisely which bytes can we have, by when, containing which channels, at what cadence, for how many participant-days, with what labels.

**What changes.** Everything. This determines the target condition, the feature set, the cadence, the evaluation design, and the honest scope of every claim. See U1 and U4.

---

## B. Ground truth, labelling, and evaluation design for illness detection

**What it covers.** How illness onset is defined and dated (PCR date, antigen date, self-reported symptom onset, clinician diagnosis); the gap between infection, physiological onset, and symptom awareness; label noise; how "detection" is scored against an episode rather than a point; the meaning of lead time; alerts-per-user-week as the false-positive currency; base rates and PPV.

Also covers the known pathologies of time-series anomaly detection evaluation: point-adjusted F1 being misleading enough that trivial baselines can beat published methods, and criticism of the standard benchmark suites. Any evaluation we write must be immune to that criticism.

**Question we need answered.** What is the correct, defensible scoring protocol for an event-based early-warning system on a small cohort, and what sample size do we actually have.

**What changes.** The entire results section. Getting this wrong invalidates the project regardless of how good the system is. This is the highest-leverage low-cost area.

---

## C. Active sensing, value of information, and human-in-the-loop decision policy

**What it covers.** Expected value of information and Bayesian experimental design; expected information gain and mutual-information acquisition; active learning acquisition functions; optimal stopping; POMDPs and cost-sensitive sequential decision making; the "budgeted query" literature; interruption cost and attention economics in ubiquitous computing.

**Question we need answered.** What is the cheapest formalism that gives a *principled*, *reportable* ask/don't-ask policy over a small discrete hypothesis space, and how do we compare it against (i) never asking, (ii) always asking, and (iii) an LLM choosing freely.

**What changes.** This is the most likely home of the project's genuine contribution. If a clean information-gain policy is implementable in a day (plausible, given a small hypothesis set), then the project has a real decision-theoretic core rather than a prompt that says "ask if unsure." It also reframes what the LLM is for.

**Why this matters more than the prior work realised.** The prior documents asserted agentic value and then proposed a ReAct loop. A ReAct loop is a mechanism, not a policy. Without an explicit objective the agent's questioning behaviour cannot be evaluated, only demonstrated.

---

## D. Physiological anomaly detection and personalized baselines

**What it covers.** Robust personalized baselines (rolling median and MAD, quantile bands, exclusion of known-sick days from the baseline window); statistical process control (EWMA, CUSUM, Shewhart); Bayesian online change-point detection; circadian modelling (cosinor and its overfitting failure modes under irregular sleep); residualizing heart rate against activity; multivariate approaches (Mahalanobis distance, isolation forest, autoencoders); handling missingness and non-wear.

**Question we need answered.** What is the strongest simple baseline, and what is the right baseline window length. Both are needed before any comparison against a fancier model means anything.

**What changes.** Defines the control arm of every experiment. A weak baseline makes all downstream results uninterpretable.

---

## E. Published clinical and commercial illness-detection systems

**What it covers.** The academic cohorts (Stanford/Snyder smartwatch COVID detection and the NightSignal real-time follow-up; Scripps DETECT; TemPredict/Oura; Mount Sinai Warrior Watch; Duke CovIdentify) and the commercial products (Oura Symptom Radar and temperature trend, WHOOP health monitor and respiratory rate, Garmin and Samsung readiness features, Apple's vitals and wrist temperature features).

**Question we need answered.** What has already been demonstrated, at what operating point, with what device and channels; what code and data are actually released; and specifically what each system *cannot* do, since that gap is the project's opening.

**What changes.** Sets the bar. Determines whether the project is a reimplementation with an LLM attached (bad) or an attack on a documented open failure mode (good). Also supplies the baseline numbers the project must compare against, which is why every one of them must be verified at source rather than taken from the archived notes.

---

## F. Confounders and the physiology of false positives

**What it covers.** Quantified physiological signatures and time courses of alcohol, acute and delayed exercise response, sleep restriction, psychological and academic stress, menstrual cycle phase, vaccination reactogenicity, travel and jet lag, altitude, ambient heat, illness recovery tails, and sensor artifact.

**Question we need answered.** For each confounder: which channels move, in which direction, by how much, over what time course, and how distinguishable it is from infection using the channels we will actually have.

**What changes.** This is the substance of the attribution problem (P2). It defines the hypothesis set, the likelihood model, the question bank, and (if a simulator is needed) the generative parameters. It is also the content that would go into any knowledge base or RAG corpus.

---

## G. Grounded generation, retrieval, and factual reliability

**What it covers.** Whether retrieval is warranted at the corpus size we need; open medical corpora and their licences; chunking and metadata filtering; hybrid dense/sparse retrieval; citation-grounded generation; measuring faithfulness, citation precision, and hallucination; structured-output enforcement; LLM-as-judge and its biases.

**Question we need answered.** Does grounding measurably beat a well-prompted model with the same facts inlined, on our specific output type, and how do we show it.

**What changes.** Whether RAG is in the system at all, and if so, whether it is presented as a component or as a measured comparison. A negative result here ("retrieval did not beat inlining for a corpus this small, so we inlined and measured it") is a *better* deliverable than an unjustified vector store.

---

## H. LLM agents over time-series and structured health data

**What it covers.** How numeric series are presented to a language model (raw serialization, summarized statistics, code execution over dataframes, tool calls returning typed values); the evidence on numerical hallucination; agent patterns (single-shot structured extraction, ReAct, plan-and-solve, tool-calling loops); event-driven gating so the model is invoked rarely; structured output and schema enforcement; memory over longitudinal history; cost and latency control.

**Question we need answered.** For a system with a *fixed small feature set*, what is the right agent-computer interface, and how much agent machinery is actually load-bearing versus ceremonial. See U14.

**What changes.** Determines complexity, failure modes, and latency of the whole reasoning layer. Also determines how defensible the system is against the "this is a chatbot wrapper" criticism.

---

## I. Time-series foundation models and pretrained physiological encoders

**What it covers.** General time-series foundation models offering zero-shot forecasting or reconstruction; self-supervised encoders pretrained on physiological signals; what weights are actually open and installable; context length, channel handling, missing-data behaviour, and compute footprint.

**Question we need answered.** Do they beat a strong classical baseline on short, gappy, daily-cadence wearable features, and is the difference worth the dependency.

**What changes.** Whether a foundation model is in the pipeline or is reported as a tested-and-rejected alternative. Both are acceptable outcomes; only the untested inclusion is not.

---

## J. Wearable signal processing and feature extraction

**What it covers.** Biosignal toolkits for HRV, respiratory-rate derivation, PPG quality assessment and artifact rejection; multi-rate stream alignment; what is necessary if the data arrives as pre-computed daily summaries rather than raw waveforms.

**Question we need answered.** Given the actual granularity of the data we obtain (U1), is any DSP required at all, or does the dataset already ship the derived features.

**What changes.** Potentially removes an entire layer. If the data arrives as nightly summaries, raw-waveform DSP is unnecessary work with no bearing on the research question.

---

## K. Alert design, alarm fatigue, and adherence

**What it covers.** Alarm fatigue in clinical monitoring; notification burden and habituation; question and micro-survey design (ecological momentary assessment, single-tap prompts); survey attrition; communicating uncertainty and risk to non-experts; trust calibration and over-reliance on automated advice.

**Question we need answered.** What interaction cost model is empirically defensible, and what does the evidence say about how many prompts per week a user tolerates. This supplies the c_q term in the value-of-information objective, which otherwise is a made-up number.

**What changes.** Turns the interaction-cost parameter from an arbitrary constant into a cited one, which is the difference between a toy objective and a defensible one.

---

## L. Safety, regulation, and ethics for a non-clinical build

**What it covers.** The wellness-versus-medical-device boundary and why the output must not be a diagnosis; deterministic red-flag interception that never passes through a language model; disclaimer and escalation language; failure modes of automated health advice; data privacy for personal physiological data; ethics and consent considerations if the developer's own body is the data source.

**Question we need answered.** What is the minimum defensible safety envelope, and what belongs in the output contract.

**What changes.** Small implementation cost, large credibility effect. Also a likely explicit requirement if this is course project (U3).

---

## M. Streaming, storage, and the demonstration harness

**What it covers.** Time-warped replay of historical data as a stand-in for live streaming; append-only local time-series storage; incremental baseline updating; state management for a long-running monitor; and the interface layer (notebook, Streamlit-class app, or full web stack).

**Question we need answered.** How much of "real-time" is a genuine requirement versus a presentation device, and what is the cheapest harness that makes the behaviour legible to an audience.

**What changes.** Time budget allocation. This area is the classic sink for a two-week project: it is visible, it feels productive, and it contains zero AI/ML content. It should be deliberately minimized.

---

## Areas the prior work over-weighted, and why

| Over-weighted | Why it is less important than it appeared |
|---|---|
| Wearable vendor API mechanics (HealthKit, Fitbit, Garmin, Oura auth flows) | Only matters if live ingestion is chosen, which depends on U4. Weeks of platform plumbing with no AI/ML content. |
| Foundation model architecture internals | We are not training anything. What matters is whether they win on our data, which is one experiment, not a survey. |
| Raw-waveform DSP (QRS detection, PPG morphology) | Almost certainly irrelevant if the data arrives as nightly summaries. Gated by U1 and area J. |
| Multi-agent orchestration patterns | No evidence any of this problem needs more than one model invocation per event. Complexity without a stated benefit is a liability. |

## Areas the prior work under-weighted, and why they matter

| Under-weighted | Why it matters |
|---|---|
| C. Active sensing and value of information | It is the only thing that turns "agentic" into a measurable claim. |
| B. Evaluation design and anomaly-detection metric pathologies | It determines whether any result survives scrutiny. |
| U2 (confounder ground truth) and the circularity problem | It is the sharpest objection to the proposed contribution, and it was never raised. |
| K. Interaction cost evidence | Without it, the central objective function contains an invented constant. |
