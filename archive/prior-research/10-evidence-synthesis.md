# 10. Evidence Synthesis and the Evidence-Derived Reference Architecture

**Status:** Phase 3 output. **This is NOT the final architecture.** It is what the evidence collectively suggests, with every component graded by how well it is supported.
**Date:** 2026-08-30
**Basis:** `findings/F0` to `F9`, roughly 126,000 words and 2,100 citations.

Earlier implied architectures (the archived prior work's "Unified Biomarker Sentry", and anything implied by my own Phase 1 docs) are set aside. This reasons from the evidence.

---

## 0. The compute constraint, stated first because it changes the ranking

Confirmed constraints: free Colab/Kaggle GPU with models hosted there and reached over an API from a local PC; OpenRouter free tier as fallback, with a **low daily request cap that makes many-call systems infeasible**; development on a local machine.

This is not a footnote. **The scarcest resource in this project is LLM calls, and the second scarcest is build hours.** Three consequences fall out immediately, and each one happens to coincide with what the evidence already recommends.

**1. The evaluation, not the demo, is what burns the call budget.** A demo run is perhaps 10 to 30 LLM calls. An ablation matrix across 5 configurations x 200 scenarios is 1,000+, and an adversarial suite of 40 to 80 cases re-run on every prompt change multiplies that again. Under a low daily cap, a naive design cannot be evaluated at all. This makes F9's top-ranked item, **a frozen scenario suite with cached and replayed model responses**, not a nice-to-have but the enabling infrastructure for every quantitative claim the project will make. Cache once, replay free, re-run in CI at zero cost.

**2. Multi-agent is now ruled out three times over.** The lecture prefers single agent for bounded tasks; F7's auditability argument prefers one action log; and the rate limit makes N agents x M turns arithmetically impossible. This is settled.

**3. A clean local/remote split exists and should be exploited.** Almost nothing in this system needs a GPU:

| Component | Where it runs | Why |
|---|---|---|
| Feature extraction, personal baseline, detector | **Local CPU** | Pandas and NumPy. Microseconds |
| Chronos-Bolt comparison arm | **Local CPU** | 9M to 200M params, NaN-native, CPU-documented |
| Bayesian inference over causes (pgmpy) | **Local CPU** | ~10 causes x ~8 questions. 320 multiply-adds |
| Information-gain question selection | **Local CPU** | Same order. Microseconds (F8 section 6) |
| Embeddings for retrieval | **Local CPU** | sentence-transformers on a corpus of tens of documents |
| Deterministic validators, red-flag checks, audit log | **Local CPU** | Must be deterministic by design |
| **LLM** | **Remote (Colab/Kaggle self-hosted, or OpenRouter)** | The only component that needs one |

So the GPU question reduces to: where does the single LLM live. A self-hosted open-weight model on Colab or Kaggle gives **unlimited calls inside a session**, which is what high-volume evaluation needs, at the cost of ephemeral sessions and weaker reasoning. OpenRouter's free tier gives stronger models at a hard daily cap, which suits the small number of demo and quality-critical calls.

That tension is worth converting into a result rather than merely managing: **run the evaluation suite under both a small self-hosted model and a stronger hosted model, and report whether model capability actually matters for this task.** F3 found that contextual framing beats parameter count in this domain, so a negative result is plausible and would be genuinely interesting. This is an honest experiment that the constraint forces on us, which is the best kind.

---

## 1. The strongest architectural patterns supported by existing systems

Ten patterns, each with what supports it and how strongly.

### P1. Two-tier gating: a cheap deterministic detector runs always, the LLM wakes only on events
The LLM is asleep more than 95% of the time. HiMe measured **49x to 121x token savings** from statistical event triggers versus periodic polling, with the honest caveat that trigger recall degraded for two of four backbones. Every proactive system found (HiMe, SAGE, VitalAgent, AI on the Pulse) uses some version of this. Under our rate limit it is mandatory rather than merely efficient.
**Grade: PROVEN.**

### P2. Measure during the nocturnal sleep window
Oura, WHOOP, NightSignal and TemPredict all restrict primary illness inference to sleep. Daytime motion, posture, meals and stress dominate the signal otherwise. Note the awkward corollary from F5: this is also the window in which **no vendor cloud API can give you data in real time**.
**Grade: PROVEN.**

### P3. Personalized rolling baseline using robust statistics
Population thresholds are invalid; resting HR spans roughly 45 to 85 bpm across healthy individuals. NightSignal uses a streaming median of overnight RHR with +3 bpm (yellow) and +4 bpm (red) transitions; Mishra used a 28-day rolling window; the released RHR-AD implementation defaults to 744 hours (31 days). Robust statistics (median, MAD) rather than mean and standard deviation, because the baseline window will contain outliers.
**Grade: PROVEN.** Caveat: **no published head-to-head of 7 versus 14 versus 21 versus 28 days exists**, which makes running that sweep a small genuine contribution.

### P4. Multi-channel concordance, not a single-metric threshold
This is the pattern I most under-weighted before reading F8, and the quantitative reason for it is stark: **the population-mean resting-HR rise from acute respiratory infection is +1.1 to +2.1 bpm, which is smaller than one alcoholic drink (+2.4 to +2.8), moderate evening exercise (+3.34), and the luteal phase (+3.91).** Single-channel detection of infection is not merely noisy, it is attempting to detect the *smallest* effect in the confounder set. Detection works at all only because it is multi-channel, within-person and multi-day. Apple implements this as a 2-of-5-metrics-outlier concordance rule; Oura fuses autonomic, thermal and pulmonary channels.
**Grade: PROVEN.**

### P5. Temporal persistence and debouncing
Alavi requires alert runs of minimum length; F6 recommends a minimum run of 2 consecutive alerting days as the alert-event unit, reporting run lengths 1, 2 and 3. Single-night excursions are overwhelmingly confounders.
**Grade: PROVEN.**

### P6. Describe the schema to the model; never paste the numbers; let deterministic code compute
Five independent systems converge (PHIA ships a pandas column dictionary, HiMe an entity-attribute-value inventory plus SQL, SAGE a query surface, openCHA pass-by-reference handles, VitalAgent typed DSP tools). The two systems that *do* serialize raw numbers into context, Health-LLM and PH-LLM, are exactly the two scoring 22% and **0%** on PHIA's numeric benchmark.
**Grade: PROVEN.** Important refinement: the archived claim that *code generation* specifically is the answer does **not** survive. The only controlled ablation found (arXiv:2606.16545) shows hybrid beating code-only, and **direct text serialization beating code generation on anomaly detection (54.8 vs 48.8), outlier detection (74.0 vs 64.8) and structural breaks (52.0 vs 44.0)** which is precisely our task family. The durable principle is schema-not-data plus deterministic computation, not code generation.

### P7. Plan-Then-Execute with a typed terminal disposition, an iteration cap, and a human interrupt
Anthropic's agent taxonomy and the prompt-injection security-patterns literature (arXiv:2506.08837) converge independently on the same shape. The plan is fixed **before** untrusted content is retrieved, so retrieved content can change the data but not the control flow. Three composable stop mechanisms: semantic (a disposition from a closed enum), an iteration cap as a safety net, and a wait deadline.
**Grade: PROVEN in agent engineering. Not yet demonstrated in wearable health, which is the opening.**

### P8. Deterministic red-flag interception, outside and above the model
The model never adjudicates a potential emergency. F7 supplies an unusually good justification: the FDA's revised wellness boundary (6 January 2026) permits alerts that do not name a disease, do not characterise output as pathological, do not include clinical thresholds, and do not provide ongoing disease monitoring. **Those four convert directly into deterministic output checks**, which means the safety layer is specified by a regulator rather than invented by us.
**Grade: PROVEN.**

### P9. Typed, enumerated, least-privilege tool set; no open-ended execution
The Action-Selector pattern: the model picks from a predefined enumerated set and cannot emit arbitrary commands. OWASP LLM06 mitigation 3 names "avoid open-ended extensions such as run a shell command" explicitly; the lecture's tier X ("agent can expand scope or act without bounded permissions") is labelled not appropriate; F7 adds the deeper principle from mitigation 7, **authorize in downstream systems rather than in the LLM**.
**Grade: PROVEN.**

### P10. Event-contingent prompting, never time-contingent
The EMA literature is clear that **event-contingent prompting outperforms time-contingent**, and that prompt frequency was *not* a significant moderator of compliance in a meta-analysis of 126 studies (n=19,431, pooled compliance 75.06%). So "ask less often" is not the principle; "ask only when something happened" is. WHOOP's daily journal is time-contingent and unconditional, which is precisely the design this evidence argues against.
**Grade: PROVEN.**

### P11. An explicit belief state with information-gain question selection
Horvitz, Jacobs and Hovel's *Attention-Sensitive Alerting* (UAI 1999) defines net expected value of alerting, NEVA = EVTA - ECA, alerts only when NEVA is positive, and was deployed as PRIORITIES. Pauker and Kassirer's threshold model gives the same shape clinically: acquire information only when the posterior sits between the testing and test-treatment thresholds. PROMIS computerized adaptive testing deploys item-level information maximisation in healthcare at scale (FAMCAT uses 22 of 60 items; FRIDA 11 items at r = 0.94 to 0.97).
**Grade: PROVEN in adjacent domains (attention management, clinical test selection, adaptive testing). Never applied to physiological monitoring. This is the single clearest opening.**

### P12. LLM extracts evidence; a small explicit probabilistic model does the inference
Precedent in AutoElicit (arXiv:2411.17284), From Word Models to World Models (arXiv:2306.12672), LLM-BI (arXiv:2508.08300). The LLM proposes hypotheses and extracts structured evidence from free text; a hand-specified discrete Bayesian network does the belief updating, so the arithmetic is auditable and the model never does maths.
**Grade: PROMISING. Published precedent exists, but not in this application.**

### P13. Simulator-as-oracle and semi-synthetic injection, for claims with no ground truth
The UVA/Padova Type 1 Diabetes simulator was accepted by the FDA in January 2008 as a **substitute for animal trials** in closed-loop insulin control, and in-silico evaluation on it is still accepted at review two decades later. The UCR Anomaly Archive and TSB-AD are the same construction for time series.
**Grade: PROVEN as a methodology, with regulatory precedent. This is what dissolves the circularity objection.**

---

## 2. What works, by capability area

| Area | What works, with evidence | What fails |
|---|---|---|
| **Continuous monitoring** | Append-only local store at nightly cadence; device-direct BLE or an on-watch app if genuine real time is required. F5's measured reality: **cloud APIs are 6 to 14 hours behind for a nocturnal event, and WHOOP recovery does not exist until the sleep cycle closes** | Expecting real-time from any vendor cloud API. Aggregators (300 to 450 USD/month) sit downstream of the same clouds and cannot beat it |
| **Personal baseline** | Rolling median plus MAD over 14 to 31 days, sick days excluded, recomputed nightly. Robust statistics, not mean and SD | Population thresholds. Mean/SD baselines corrupted by the very outliers you are hunting |
| **Anomaly detection** | Overnight RHR versus streaming median with a small state machine (NightSignal: 80% sensitivity, 87.7% specificity, median 3-day lead, n=84 cases, deployed prospectively, Apache-2.0 implementation under 100 lines) | `EllipticEnvelope(contamination=0.1)` as shipped in RHR-AD, which **forces roughly 10% of every window to be flagged regardless of health**. The easiest thing in this project for a reviewer to attack |
| **Early illness detection** | Multi-channel concordance plus multi-day persistence. Nothing else clears the confounder noise floor | Any single-channel threshold, for the effect-size reason in P4 |
| **Reducing false alerts** | Two proven levers: multi-channel concordance (Apple, silent, zero burden) and persistence/debouncing. One evidenced-but-unbuilt lever: **targeted questions, which address the ~45% of false alerts attributed to stress, poor sleep, exercise and alcohol** in the Northwell/Fitbit evaluation | Alerting on single-night excursions. Unconditional daily surveys (WHOOP Journal) which impose burden without conditioning on anything |
| **Contextual reasoning** | Schema-to-model, deterministic computation, structured extraction of free text into typed slots | Pasting numeric series into context (22% and 0% benchmark scores). Asking the model to do arithmetic |
| **Interacting with users** | Event-contingent, low-friction, single-tap. Budget of roughly **2 questions per week**, driven by habituation rather than compliance: HeartSteps' effect decayed from +66% to +24% over 6 weeks, and there is essentially no evidence beyond 6 weeks | Time-contingent daily questionnaires. Note users already receive roughly **63.5 notifications/day** from all sources |
| **Grounding medical knowledge** | Small curated corpus with source-linked claims and an unsupported-claim stripping pass. MedlinePlus XML (~29 MB, daily, attribution-only) is the cleanest source. **PMC legacy bulk FTP was removed the week of 24 Aug 2026** | Large uncurated corpora. Also: **retrieval over the user's own history**, where HealthClaw measured structured retrieval at **15 points worse than simply passing the full history** (45.7% vs 61.2%) |
| **Actionable output** | Natural-frequency statements, a ranked *set* of candidate causes rather than a single verdict, the specific observation that drove it, and an explicit action threshold | A bare percentage. A bare verbal hedge. "Readiness: 62". Anything that names a disease |

---

## 3. What must stay separate, and why

Seven boundaries. The first four are conventional; the last three are the ones this evidence base argues for specifically.

| Boundary | Why it must hold |
|---|---|
| **Signal processing and baseline modelling, separate from the LLM** | Must be continuous, deterministic, microsecond-scale and free. Under our rate limit, anything invoking an LLM per epoch is arithmetically impossible, not merely wasteful |
| **Primary detection, separate from explanation** | Detection is a scoring problem with a measurable operating point; explanation is a language problem. Coupling them makes the detector unevaluable and the explanation unfalsifiable |
| **All arithmetic, separate from the LLM** | The 22% and 0% benchmark results are the empirical case. There is no ambiguity here |
| **Deterministic safety checks, outside and above the model** | The FDA four-part test is a specification for *code*, not for a prompt. A prompt-based guardrail is negotiable by construction; the lecture's own worked failure case is an agent talking itself past a soft guardrail |
| **Belief updating, separate from the LLM** | The arithmetic of a posterior over causes must be auditable and reproducible. This is the F9 P12 pattern, and it is also what makes the ask/don't-ask decision measurable rather than asserted. An LLM asked to "decide if you're unsure" cannot be scored |
| **Personal data retrieval, separate from medical knowledge retrieval** | Different mechanisms, not merely different corpora. Personal history is relational and should be queried, not embedded (HealthClaw's 15-point deficit). Medical knowledge is textual and needs citations. Conflating them produces the worst of both |
| **The control plane, separate from untrusted content** | Plan-Then-Execute exists precisely so retrieved documents and free-text symptom reports can influence *data* but never *control flow*. This is the only injection defence with real evidence: eight published prompt-level defences were broken with over 50% adaptive attack success |

---

## 4. What must NOT be delegated to an LLM

1. **Arithmetic of any kind.** Baseline deltas, z-scores, aggregations, posterior updates.
2. **Primary anomaly scoring.** "Does this look anomalous" is a detector's job with a measurable operating point.
3. **Red-flag triage.** A potential emergency must never depend on model reasoning.
4. **The ask/don't-ask decision itself.** If the LLM decides when to interrupt, the policy cannot be compared against never-ask and always-ask baselines, and the project's central claim becomes unmeasurable. **This is the delegation that would quietly destroy the contribution.**
5. **Its own confidence calibration.** Verbalised confidence shows ECE above 0.25 on hard tasks and systematic overconfidence. Never ship a raw verbalised number.
6. **Output validation.** Schema conformance, citation-to-claim linking, and the four FDA checks are deterministic passes.
7. **Any state-changing commit.** Draft and pend only; the human signs.
8. **Interpreting retrieved content as instructions.** Structurally prevented, not prompted against.

The lecture compresses this correctly: *agents draft, deterministic validators check, and people sign.*

---

## 5. Where an LLM adds measurable value

Five places, each with a proposed measurement so the claim is testable rather than assumed.

| Role | Why an LLM | How to measure it |
|---|---|---|
| **Free-text to typed slots** | The user answers "had a few beers and slept badly." Turning that into structured evidence is exactly what language models are for, and the alternative is a rigid form | Slot-extraction accuracy against a labelled set of synthetic and real replies |
| **Question wording, context-aware** | *Which* question to ask is a decision-theoretic computation; *how to phrase it* given the user's history and the time of day is a language task | Human or rubric-scored naturalness and non-alarmism; RubricsTree-style atomic Boolean rubrics raised inter-rater ICC from 0.291 to 0.876 |
| **Explanation with source links** | Translating a multi-channel deviation into a lay narrative | Unsupported-claim rate and citation accuracy, both on the lecture's own metric list |
| **Hypothesis proposal, not scoring** | Suggesting a candidate cause the fixed hypothesis set missed | Ablation: does the LLM-proposed set beat the fixed set on attribution accuracy |
| **Open-ended exploration mode** | The personal-use goal genuinely wants arbitrary questions over one's own history, which typed tools cannot serve | Answer accuracy on a held-out question set |

Note what is absent: attribution *scoring*, detection, arithmetic, and the interruption decision. F3's evidence base does not support the LLM in any of those roles, and F9 offers a better mechanism (P12) for the one that matters.

---

## 6. Where an agent adds value beyond a normal workflow

A workflow is right when the next step is fixed. An agent earns its place only when **the next action genuinely depends on the ambiguity of intermediate results.** Three quantitative findings establish that this condition holds here, and they were not available before Phase 2.

1. **Confounder nights outnumber prodrome nights by roughly 20 to 40 : 1.** Even a 5:1 sensor likelihood ratio leaves the posterior probability of infection well under 50% after an anomaly. Acting on sensors alone is not defensible; acquiring more information is the rational move.
2. **Five confounders are genuinely not separable from early infection on consumer channels**: acute alcohol on night one, acute psychological stress, luteal phase without cycle history, vaccine reactogenicity, and medication changes. For these, asking is the only resolution. Equally important for honesty: for altitude, late meals, and device-recorded workouts, asking is redundant burden. **A policy that can say "no question needed" as readily as "ask" is the thing with value.**
3. **Roughly 45% of real false alerts had askable causes** (stress 16.0%, poor sleep 13.7%, exercise 9.7%, alcohol 6.0%) in an independent evaluation whose measured PPV was **4%**.

Beyond the asking decision, one more property is genuinely agentic rather than workflow-shaped: **state held across waits of days.** An episode investigation spans multiple nights and pauses for a human answer. F3 found most health LLM systems are single-session; the few that are not (HiMe, VitalAgent, HealthClaw) are the exception.

What does **not** add value: multiple agents, replanning loops (VitalAgent's own ablation shows its validate and replan stages do nothing, and removing validation is *better* on one tier), and an LLM controller choosing freely among actions without a stated objective.

---

## 7. RAG: necessary, optional, unnecessary

| Use | Verdict | Reasoning |
|---|---|---|
| **Source-linked health guidance in user-facing output** | **NECESSARY** | The brief requires grounding. "Unsupported-claim rate" and "source/citation accuracy" are two of the six metrics on the lecture's own list. Without retrieval there is nothing to link a claim to |
| **Confounder physiology facts** | **OPTIONAL, and probably better inlined** | F8's confounder table is roughly 13 rows. That fits in a prompt with room to spare, and inlining is faster, cheaper and reproducible. The honest move is to build both and measure the difference, which converts a design question into a finding |
| **Prodromal timelines and differential checklists** | **NECESSARY if claimed at all** | These are exactly where LLMs confabulate specific numbers |
| **Personal history and metrics** | **UNNECESSARY, and actively harmful** | HealthClaw measured structured retrieval at **15 points worse than passing full history**. Personal data is relational. Query it, do not embed it |
| **Primary detection** | **UNNECESSARY** | Purely mathematical |
| **Under our rate limit** | Note | Retrieval is local and free; it is the *generation* call that costs. RAG does not worsen the budget problem |

---

## 8. Pretrained wearable/time-series models: the strongest evidence both ways

**For.** One directly on-point result exists: Chronos zero-shot on consumer smartwatch HRV achieved **MASE 0.82 versus EWMA's 0.84**, statistically significant at p<0.001. That same paper used context lengths of **32 and 64**, which refutes the "you need 512 points of history" objection I had been carrying. Chronos-Bolt and Chronos-2 are Apache-2.0, CPU-runnable, NaN-native, and reachable in 2 to 5 hours. Chronos-2 additionally does joint multivariate forecasting with covariates zero-shot. There is also a useful positive lesson from Apple's unavailable wearable model: a model over *derived daily metrics* beat their raw-PPG sensor model on most dynamic health tasks, which reframes working at metric level as a defensible choice rather than a compromise.

**Against.** The gain is **2.4% over a one-line baseline**. Counter-evidence is broad and consistent: linear baselines outperforming foundation models on other operational data, classical methods winning at sub-hourly cadence on public benchmarks, and a 2025 workshop finding no consistent gain over small dedicated models. Anomaly-detection evidence specifically is compromised: MOMENT's own notebook scores with point-adjusted best F1, on which **random noise scores about 0.89**. MOMENT is disqualified on a mechanism: its authors state it "struggles to differentiate between vertically shifted time series as it normalizes signals prior to modeling", and **a sustained multi-night resting-HR elevation is exactly a vertical shift**. IBM's TTM has a hard 512-timestep minimum, which at nightly cadence is 1.4 years, disqualifying it. Every wearable-native foundation model (Apple WBM, Google LSM-2, SensorFM) has no released weights. Licence traps: TimesFM 3.0 is non-commercial, Moirai is non-commercial, MOMENT is MIT rather than Apache.

**Synthesis.** Include Chronos-Bolt as a **measured comparison arm, not as the operating detector**. Two to five hours converts an open question into a reportable result, and reporting honestly that a 2.4%-class gain does not justify the dependency is a stronger finding than silently shipping it.

---

## 9. Statistical personalized anomaly detection alone: the strongest evidence both ways

**For.** NightSignal is the best-evidenced simple detector in the field: **80% sensitivity (67 of 84 cases), 87.7% specificity, median 3-day lead time**, from a prospective deployment with 3,318 enrolled participants, published in Nature Medicine, with an Apache-2.0 implementation that compresses to under 100 lines and runs in microseconds on a CPU. Under our compute constraint, "runs locally and free" is not a minor virtue. It is fully auditable, has zero hallucination surface, and needs no training.

**Against.** The honest ceiling is set by **COVID-RED, the only randomised controlled trial in this territory (n=17,825)**, where the wearable algorithm achieved 93.8 to 99.2% sensitivity at **0.8 to 4.2% specificity**. Under trial conditions it alerted very nearly everyone. Separately, the headline figures elsewhere in this literature are systematically inflated by favourable subgroups: Mishra's 63% is 15 of 24 participants who had at least 28 days of prior data; Alavi's 80% pools retrospective and prospective cases and counts any alert in a 21-day window; one cited 94% uses a threshold fitted for zero false positives on the same data. The released RHR-AD implementation forces roughly 10% of every window to be flagged. And no published head-to-head of baseline window lengths exists, so the standard choice is convention rather than evidence.

**Synthesis.** Yes as the operating detector, and it must be shown against **two mandatory baselines**: a random detector rate-matched to its alert rate (1,000 draws, report the recall distribution), and a trivial "today's RHR exceeds all-time median by 4 bpm" rule with no windowing or debouncing. If the sophisticated version does not beat the trivial one, that is the finding and reporting it earns more than hiding it.

---

## 10. What makes "predict whether the user is sick" genuinely hard

Ordered by how fundamental the obstacle is.

1. **Identifiability.** Five confounders are not separable from early infection on the available channels. This is a property of the sensing modality, not an algorithmic deficiency.
2. **Adverse effect size.** Infection's mean RHR rise (+1.1 to +2.1 bpm) is the *smallest* effect in the confounder set. We are hunting the faintest signal in the room.
3. **Base rates.** 20 to 40 confounder nights per prodrome night. Alcohol alone occupies 29.9% of person-days.
4. **Measured precision is 4%**, with roughly 24 false alerts per true one, and the only RCT in the field reports near-zero specificity.
5. **No dataset has both illness labels and confounder annotations.** Open datasets split into "labels, no confounders" (Stanford, Homekit2020, CovIdentify) and "confounders, no illness" (PMData, TILES, LifeSnaps, MMASH). The one resource with both, All of Us Controlled Tier, cannot be obtained in time.
6. **Label noise.** Symptom onset is self-reported and day-granular. Lead time measured against it means "time before the person noticed", not "time before infection took hold".
7. **Device ceilings.** The Samsung Health Data SDK has **no HRV type and no respiratory-rate type**. WHOOP REST gives five scalars once per night and no heart-rate series at all.
8. **Informative missingness.** Non-wear is not random; someone who feels awful may stop wearing the device. Stanford's step files are zero-filled, so non-wear can only be inferred from HR.
9. **Long recovery tails.** Resting HR does not return to baseline until roughly 79 days after COVID onset, and 13.7% remain more than 5 bpm elevated past 133 days. A residual looks like a new event.
10. **Broken evaluation conventions.** Point-adjusted F1 gives random scores 0.969. The Epic Sepsis Model's published AUC of 0.76 to 0.83 collapsed to 0.63 once the detection window was defined correctly, which is exactly how a result leaks through a metric definition.
11. **The regulatory boundary.** Naming a disease, characterising output as pathological, stating clinical thresholds, or providing ongoing disease monitoring crosses out of wellness. An Oura class action was filed on 20 August 2026 over accuracy claims.

---

## 11. What can realistically be demonstrated in two weeks

Against roughly 45 build hours, with the rest going to the report, test artefacts, proposal and rehearsal.

**Demonstrable with high confidence:**

| Deliverable | Hours | Why it is safe |
|---|---|---|
| Nightly feature extraction and personal baseline on real replayed cohort data | 4-6 | Pandas over an open, unauthenticated download |
| NightSignal-class detector plus both mandatory baselines and the seven F6 metrics | 6-8 | Published implementation exists; metrics are precisely specified |
| Bounded episode-investigation agent: Plan-Then-Execute, typed disposition enum, iteration cap, human interrupt, audit log falling out of the checkpointer | 8-10 | LangChain `HumanInTheLoopMiddleware` exposes `approve/edit/reject/respond` directly |
| Explicit belief state over ~10 causes plus information-gain question selection | 5-7 | 320 multiply-adds. The likelihood table is the real work, and F8's confounder table supplies it |
| Retrieval over a small curated corpus with claim-to-source linking and an unsupported-claim stripping pass | 4-6 | Corpus is tens of documents; MedlinePlus is clean |
| Frozen scenario suite with cached and replayed LLM responses | 6-10 | Enables everything else under the rate limit |
| Deterministic safety layer implementing the FDA four-part test plus red-flag interception | 3-4 | Pure code |
| Semi-synthetic evaluation: inject a +4 bpm, 4-day RHR bump into PMData, sweep amplitude 1-8 bpm and duration 1-7 days, report a detection heat map | 5-7 | Effect size taken from NightSignal's own thresholds |
| Adversarial suite of 40 to 80 injection cases from a taxonomy, with measured attack success rate | 5-8 | Template generation, no optimisation needed |

That totals more than 45 hours, so the ordered cut list in doc 09 section 6 governs. The Chronos comparison (2-5h) sits above the line only if hours remain.

**The evaluation design that makes the central claim non-circular**, and which is the single most valuable thing Phase 2 produced: **pair the datasets.** Estimate detection sensitivity and lead time on the illness-labelled Stanford set. Estimate false-alarm rate and confounder attribution on PMData, which records **daily alcohol, meals, training load, mood, stress and sleep quality for 16 people over 5 months under CC BY 4.0**. Then hide PMData's real self-reports and reveal one **only when the agent asks for it**. That is a simulated-oracle evaluation whose answers are *real human self-reports*, not values we invented, with the UVA/Padova FDA precedent as justification for the injected-event half. The circularity objection I flagged in doc 00 as the sharpest available attack does not survive this design.

**Not demonstrable, and should be stated as such:** any claim of clinical validity; any population-level performance claim; detection of illness in the team's own two-person live deployment (nobody is likely to fall ill on schedule); anything requiring COVID-RED or All of Us access.

---

## 12. The Evidence-Derived Reference Architecture

**This is not our final architecture.** It is what the evidence collectively suggests. Every block carries a grade:
**[PROVEN]** deployed and measured in published systems ·
**[PROMISING]** proven in an adjacent domain, not yet in this one ·
**[SPECULATIVE]** plausible, no direct evidence.

```
=====================================================================================
 LAYER 0 DATA all local, CPU
=====================================================================================
 [PROVEN] Replayed cohort data, nightly cadence
 Stanford COVID-19-Wearables (open, HR + steps, no labels in archive)
 PMData (confounder-annotated, no illness) --> paired, see section 11
 [PROVEN] Personal device export (Samsung ZIP: per-minute HR, ungated)
 [PROMISING] Live device-direct path for silent-mode demo
 WHOOP BLE broadcast (~1 s, BPM + RR) -- overnight survival UNTESTED
 [SPECULATIVE] On-watch Wear OS app (true 1 Hz multi-channel, 2-5 days build)

=====================================================================================
 LAYER 1 PERCEIVE deterministic, local, free
=====================================================================================
 [PROVEN] Nocturnal window isolation
 [PROVEN] Data-quality gate: coverage, non-wear, implausible jumps
 --> insufficient coverage is a REFUSAL, not a silent guess
 [PROVEN] Personal rolling baseline: median + MAD, 14-31 d, sick days excluded
 [PROMISING] Baseline-window sweep 7/14/21/28 (no published head-to-head exists)

=====================================================================================
 LAYER 2 DETECT deterministic, local, free
=====================================================================================
 [PROVEN] NightSignal-class state machine on overnight RHR vs streaming median
 [PROVEN] Multi-channel concordance (>=2 of N channels), not single-metric
 [PROVEN] Persistence / debounce: minimum 2-night run
 [PROVEN] Mandatory comparison arms: rate-matched random + trivial +4 bpm rule
 [PROMISING] Chronos-Bolt zero-shot forecast band, as a MEASURED ARM only
 |
 deviation flagged? --NO--> silent log, no LLM call
 | YES
 v
=====================================================================================
 LAYER 3 SAFETY INTERCEPT deterministic, before any model sees anything
=====================================================================================
 [PROVEN] Red-flag thresholds -> escalate, bypass model entirely
 [PROVEN] FDA four-part wellness test as executable checks

=====================================================================================
 LAYER 4 BOUNDED EPISODE INVESTIGATION <-- the ONLY agentic component
=====================================================================================
 [PROVEN] Plan-Then-Execute; plan fixed BEFORE untrusted content is retrieved
 [PROVEN] Typed terminal disposition enum = the stop condition
 {explained_by_confounder | escalated | resolved | unresolved | timed_out}
 [PROVEN] Iteration cap (safety net) + wait deadline (third bound)
 [PROVEN] State across waits: thread-scoped checkpoint per episode,
 cross-thread store for the personal baseline
 [PROVEN] Typed, enumerated, least-privilege tools. No open-ended execution
 [PROVEN] Human checkpoint: approve / edit / reject / respond

 +--------------------------+ +--------------------------+ +-------------------+
 | [PROMISING] BELIEF STATE | | [PROMISING] ASK POLICY | | [PROVEN] RETRIEVAL|
 | ~10 causes, explicit |-->| Expected information gain| | small curated |
 | Bayesian net (pgmpy) | | vs interruption cost | | corpus, claim-to- |
 | LLM extracts evidence, | | (Horvitz NEVA form) | | source linking |
 | NEVER does the maths | | c_q SWEPT, not assumed | | LOCAL, free |
 | local, CPU, microseconds | | Must be able to say | | |
 | | | "no question needed" | | |
 +--------------------------+ +--------------------------+ +-------------------+
 |
 [PROVEN] LLM used ONLY for: free-text -> typed slots,
 question phrasing, narrative explanation, hypothesis proposal
 Remote (Colab/Kaggle self-hosted, or OpenRouter). Rare calls.

=====================================================================================
 LAYER 5 VALIDATE (agents draft, deterministic validators check, people sign)
=====================================================================================
 [PROVEN] Schema conformance; validation failure is a handled event, not a crash
 [PROVEN] Every claim source-linked; unsupported statements stripped and COUNTED
 [PROVEN] FDA four-part re-check on generated text
 [SPECULATIVE] Calibrated confidence via self-consistency + post-hoc recalibration

=====================================================================================
 LAYER 6 AUDIT + INTERFACE
=====================================================================================
 [PROVEN] Audit log FALLS OUT of the checkpointer, not a parallel logger
 input | action | source | timestamp | output | human_decision
 + self-expansion attempts + claims stripped + terminal state
 [PROVEN] Visible perceive/reason/act cycles, state transitions, tool calls
 [PROVEN] Time-warped replay for the presentation (a multi-day episode cannot
 be shown live in a 10-minute slot that includes setup and Q&A)

=====================================================================================
 EVALUATION HARNESS (not a layer; the thing that makes claims credible)
=====================================================================================
 [PROVEN] Frozen scenario suite, cached/replayed LLM responses, CI on change
 ^ mandatory under the rate limit, not optional
 [PROVEN] Seven F6 metrics; never point-adjusted F1; both baselines shown
 [PROVEN] Semi-synthetic injection into PMData, amplitude+duration sweep
 [PROMISING] Simulated oracle: reveal PMData's REAL self-reports only when asked
 [PROMISING] Adversarial persona simulated user (non-response, recall error)
 [PROMISING] Ablation matrix with paired bootstrap CIs + cost-controlled baseline
 [SPECULATIVE] Small self-hosted vs large hosted model, measured
```

### Grade summary

| Grade | Count | Character |
|---|---|---|
| **PROVEN** | 27 blocks | Deployed and measured somewhere. Low risk. Most of the system |
| **PROMISING** | 9 blocks | Proven in an adjacent domain. **This is where the contribution lives** |
| **SPECULATIVE** | 4 blocks | Plausible, unevidenced. First on the cut list |

The distribution is deliberate. A system built only from PROVEN blocks is a competent reimplementation. The PROMISING blocks, principally the explicit belief state, the information-gain asking policy, and the simulated-oracle evaluation on real self-reports, are what make it more than that, and each is individually cheap because the hypothesis set is small.

---

## 13. What this synthesis does NOT decide

Deliberately left open for the design phase:

- Which LLM, and the self-hosted versus hosted split.
- Whether the belief state is a Bayesian network, a flat categorical posterior, or a rule set. Only that it must be explicit and outside the LLM.
- Exact hypothesis set and question bank membership.
- Whether the exploration mode (sandboxed, off the safety-critical path) is in scope at all.
- Which dataset is primary, pending the PMData and Stanford inspections.
- Whether live device ingestion survives the cut list.
- The interface framework.

Three things must happen before design begins: **read Project Hermes (arXiv:2602.18643)**, which reports approximately the result this project would aim for; **inspect PMData** to confirm its self-report fields are what F6 describes; and **run the two overnight hardware experiments** if the live element is to be kept.
