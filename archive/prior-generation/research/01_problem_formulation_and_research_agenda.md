# Research Agenda & Technical Problem Formulation
## Phase 1: Establish Context, Constraints, and Research Agenda

**Project:** Adaptive Agentic Wearable Early-Warning & Health Monitoring System
**Timeline Constraint:** ~2 Weeks Rapid Research & Development
**Core Directive:** Ground all architectural and modeling decisions in empirical evidence and literature before designing or coding.

---

## 1. Problem Formulation in Precise Technical Terms

The objective is not merely to build a generic conversational health chatbot or a simplistic threshold alert, but to solve an **active, partially observable, multimodal inference and sequential decision-making problem**.

```
 +-----------------------------------------------+
 | Multimodal Ingestion Stream |
 | X_t = [PPG, RHR, HRV, Temp, SpO2, Sleep] |
 +-----------------------+-----------------------+
 |
 v
 +-----------------------------------------------+
 | Statistical / Model Baseline |
 | Personalized Circadian Residual Engine |
 | r_t = x_t - mu_u(t), z_t = ... |
 +-----------------------+-----------------------+
 | Anomaly Score a_t
 v
 +-----------------------------------------------+
 | Agentic Decision Policy |
 | pi(a_t | h_t) |
 +----+------------------+------------------+----+
 | | |
 [Low Ambiguity / | [Ambiguous Anomaly / | [Clear Anomaly /
 Benign Noise] | Needs Verification] | High Confidence]
 v v v
 +----------------+ +----------------+ +----------------+
 | No Action | | Active Inquiry | | Medical RAG |
 | (Silent Log) | | (Symptom/Act) | | & Warning Gen |
 +----------------+ +-------+--------+ +-------+--------+
 | |
 +-------->+<-------+
 |
 v
 +-------------------------------+
 | Grounded Risk Assessment & |
 | Calibrated Early Warning |
 +-------------------------------+
```

### 1.1 Formal State Space & Input Telemetry
Let continuous time be indexed by $t$. The system observes:
1. **High-Frequency & Summary Time-Series Stream ($X_{1:t}$):**
 $$X_{1:t} = \{ \mathbf{x}_\tau \}_{\tau=1}^t, \quad \mathbf{x}_\tau \in \mathbb{R}^d$$
 Where features include:
 - Resting Heart Rate ($RHR$, bpm)
 - Heart Rate Variability ($HRV$, specifically nocturnal $rMSSD$, $SDNN$, High-Frequency power)
 - Peripheral Oxygen Saturation ($SpO_2$, %)
 - Skin Temperature Deviation ($\Delta T_{skin}$, $^\circ\text{C}$ relative to nocturnal baseline)
 - Respiratory Rate ($RR$, breaths/min during sleep)
 - Sleep Architecture Metrics (total sleep time, sleep efficiency, REM/Deep/Light duration, sleep onset latency)
 - Actigraphy & Circadian Activity Indices (step count, METs, sedentary duration, circadian phase estimate)

2. **Longitudinal Personal Baseline ($\mathcal{B}_u$):**
 $$\mathcal{B}_u = \{ \mu_{u,k}(\tau), \sigma_{u,k}(\tau), \text{Quantiles}_{u,k} \}_{\tau \in [0, 24h), k \in \{1,\dots,d\}}$$
 Capturing user-specific circadian periodicity, weekday/weekend variations, and long-term moving averages over a historical rolling window $W$ (e.g., 14–30 days).

3. **Sparse Asynchronous Context & User Feedback ($S_{1:t}, C_{1:t}$):**
 - Subjective Symptom Reports $S_t \in \mathcal{S}$ (e.g., scratchy throat, fatigue, chills, headache, muscle ache, cough).
 - Behavioral & Environmental Confounders $C_t \in \mathcal{C}$ (e.g., late-night alcohol ingestion, strenuous exercise / delayed onset muscle soreness, altitude change, travel / jet lag, acute psychological stress, menstrual cycle phase, vaccination).

### 1.2 Latent Variable Inference
The true underlying physiological state is a latent discrete variable $Y_t \in \{0, 1, 2\}$:
- $Y_t = 0$: **Homeostasis / Benign Variance** (normal fluctuation or known non-pathological confounder).
- $Y_t = 1$: **Subclinical Physiological Strain / Pre-Symptomatic Prodrome** (incipient immune response, viral/bacterial infection incubation).
- $Y_t = 2$: **Symptomatic Acute Infection / Illness**.

The inference task is to continually compute the posterior probability:
$$P(Y_t \ge 1 \mid X_{1:t}, S_{1:t}, C_{1:t}, \mathcal{B}_u, \mathcal{M}_{med})$$
where $\mathcal{M}_{med}$ represents verified clinical knowledge.

### 1.3 Active Sequential Decision Policy (Agentic Orchestration)
The agent operates under a sequential decision policy $\pi(a_t \mid h_t)$, where the history vector is $h_t = (X_{1:t}, S_{1:t}, C_{1:t}, \mathcal{B}_u)$, choosing an action $a_t \in \mathcal{A}$:
- $a_t = \text{Observe}$: Continue passive background monitoring; no user interruption.
- $a_t = \text{ActiveQuery}(q)$: Proactively formulate a targeted, low-friction micro-inquiry to disambiguate a physiological anomaly from a confounder (e.g., "Elevated nocturnal RHR (+7 bpm) and drop in HRV detected. Did you consume alcohol or exercise intensely before bed?").
- $a_t = \text{RetrieveKnowledge}(k)$: Query a clinical RAG vector store for verified prodromal illness trajectories, differential symptom patterns, or non-pharmacological care protocols.
- $a_t = \text{IssueEarlyWarning}(\text{level}, \text{explanation})$: Trigger a calibrated early warning with multi-signal attribution (e.g., "Elevated resting heart rate +4.8 $\sigma$, elevated skin temp $+0.9^\circ\text{C}$, suppressed HRV $-35\%$, after ruling out strenuous workout. Estimated 82% probability of acute viral prodrome").

### 1.4 Objective Function
The agentic system seeks to maximize detection lead time (earliness $\Delta t_{early} = t_{symptom\_onset} - t_{detect}$) and precision, while strictly bounding false alarm rates and user query fatigue:

$$\max_\pi \mathbb{E} \left[ \text{Reward}(Y_t, \hat{Y}_t, \Delta t_{early}) - \lambda_1 \mathbb{I}(\text{False Alarm}) - \lambda_2 \sum \text{QueryCost}(a_t) \right]$$

---

## 2. Key Unknowns to Research Before Architecture Decisions

| Domain | Critical Unknown | Impact on Project Architecture |
|---|---|---|
| **Data Realism** | What public wearable datasets contain high-resolution physiological streams paired with verified, timestamped infection/illness ground truth? | If no continuous live open stream exists, we must design a realistic continuous time-series streaming simulator based on benchmark datasets (e.g., Stanford COVID-19, Scripps DETECT, WESAD). |
| **Model Feasibility** | Do pretrained time-series foundation models (TimesFM, Chronos, MOMENT) provide meaningful zero-shot anomaly detection on circadian wearable data, or are statistical/Kalman baseline algorithms superior in accuracy, latency, and compute? | Determines whether the primary anomaly engine is a zero-shot TS foundation model, a specialized digital biomarker extractor, or a robust statistical circadian filter. |
| **Agentic Boundary** | Where does an LLM agent genuinely create unique value compared to a deterministic Bayesian belief network or rule engine? | Prevents building a "gimmick agent." The LLM must be reserved for multi-hypothesis causal reasoning, dynamic inquiry generation, unstructured user input extraction, and grounded synthesis. |
| **RAG Utility** | What specific medical corpus is required, and how is retrieval triggered without polluting the context with irrelevant clinical textbooks? | Dictates vector store schema, metadata filtering (e.g., filtering by validated prodromal symptoms, viral timelines, confounder profiles), and strict grounding/safety prompts. |
| **False-Positive Physics** | What are the primary non-infectious physiological confounders (alcohol, overtraining, stress, circadian shifts) and their exact multi-metric signatures? | Defines the feature extraction pipeline and the agent's active disambiguation inquiry tree. |

---

## 3. Major Research Areas & Taxonomy Breakdown

```
========================================================================================
 TAXONOMY OF RESEARCH DOMAINS
========================================================================================

 1. Wearable Sensing & Physiological Telemetry
 |-- Photoplethysmography (PPG) -> Inter-beat intervals (IBI), Pulse Wave Velocity
 |-- Nocturnal Resting Heart Rate (RHR) & Respiratory Rate (RR)
 |-- Heart Rate Variability (HRV): Time-domain (rMSSD, SDNN) & Frequency-domain (HF, LF)
 +-- Peripheral Temperature Deviation (Dermal thermistor / nocturnal baseline offset)

 2. Digital Bioreviewers & Circadian Dynamics
 |-- Cosinor analysis & Circadian Phase Alignment (detrending daily cycles)
 |-- Sleep Architecture: REM/Deep/Light transitions & Sleep Efficiency
 +-- Multi-day rolling physiological strain & allostatic load index

 3. Physiological Anomaly Detection & Baseline Personalization
 |-- Robust z-score deviation over diurnal baselines
 |-- Statistical Changepoint Detection: CUSUM, EWMA, Bayesian Online Changepoint (BOCPD)
 +-- Multivariate anomaly detection: Isolation Forests, Autoencoders, Mahalanobis distance

 4. Pretrained Foundation Models & Wearable ML
 |-- Time-series Foundation Models: Chronos (Amazon), TimesFM (Google), MOMENT (CMU)
 |-- Self-Supervised Physiological Encoders: HeartBEiT, SleepPPG-Net, UniTS
 +-- Feature-based lightweight ML: XGBoost / LightGBM on engineered biomarker aggregates

 5. Infection & Illness Prediction Literature
 |-- Stanford Snyder Lab Studies: Mishra et al. (Nat Biomed Eng 2020), Alavi et al. (2021)
 |-- Scripps DETECT Trial: Quer et al. (Nat Med 2021)
 |-- Commercial systems: WHOOP "Strain/Recovery" & Oura "Readiness / Temperature Trend"
 +-- Typical viral prodromal signature: RHR rise 24-48h prior, HRV drop, nocturnal temp spike

 6. Agentic Orchestration & Time-Series Reasoning
 |-- Agent-computer interface (ACI): Tool calling over time-series aggregates & summaries
 |-- Multi-step hypothesis generation: Infectious prodrome vs. Confounder disambiguation
 |-- Proactive prompting policies: When to speak vs. when to remain silent
 +-- Structured observation schemas (JSON summaries vs. raw token serialization)

 7. Grounded Medical Retrieval-Augmented Generation (RAG)
 |-- Evidence base: CDC / WHO clinical guidelines on infectious prodromes & viral trajectories
 |-- Chunking & indexing: Symptom-biomarker mapping, differential timelines
 +-- Safety & Clinical Guardrails: Hallucination mitigation, non-diagnostic disclaimers

 8. Alarm Fatigue & Human-in-the-Loop Interaction
 |-- Sensitivity vs. Specificity Pareto frontier in continuous wearable alerting
 |-- Micro-inquiries (single-tap low-friction prompts) to minimize user burden
 +-- Calibrated epistemic uncertainty communication (explaining confidence & evidence)
========================================================================================
```

---

## 4. Structured Research Checklist

### Track A: Clinical & Physiological Biomarker Grounding
- [ ] **A.1** Review key landmark papers on wearable infection detection (Mishra et al. 2020, Quer et al. 2021, Hirten et al. 2021, Miller et al. 2020).
- [ ] **A.2** Document the exact multi-metric physiological trajectory of acute viral respiratory infection (e.g., onset timing of RHR elevation, HRV collapse, skin temperature rise, respiratory rate shifts).
- [ ] **A.3** Catalogue common non-pathological confounders and their mathematical/biomarker profiles (alcohol consumption, vigorous late-night exercise, jet lag, poor sleep hygiene, psychological stress, menstrual luteal phase).

### Track B: Open Datasets & Evaluation Benchmarks
- [ ] **B.1** Survey publicly available datasets featuring continuous wearable streams and illness/stress ground truth (e.g., Stanford COVID-19 Wearables dataset, PhysioNet / MIMIC subsets, WESAD stress dataset, Apple Heart & Movement study open subsets, Synthetic generative streams).
- [ ] **B.2** Determine ground truth format (daily symptom logs, PCR test dates, stress annotations, anomaly labels).
- [ ] **B.3** Establish standard evaluation metrics: Detection Lead Time (hours before symptom onset), Sensitivity/Recall, Specificity, False Positive Rate per user-week (FPR/week), and F1/AUC-ROC.

### Track C: Pretrained Models & Anomaly Algorithms
- [ ] **C.1** Evaluate open-source time-series foundation models (TimesFM, Chronos-Bolt, MOMENT) for zero-shot wearable forecasting and residual-based anomaly detection.
- [ ] **C.2** Benchmark classic statistical and signal processing baselines: Circadian Detrended z-scores, CUSUM, EWMA, Kalman Filter state tracking, and Bayesian Online Changepoint Detection (BOCPD).
- [ ] **C.3** Compare compute footprint, inference latency, dependency complexity, and local execution viability for a 2-week build.

### Track D: Agentic Architecture & Orchestration
- [ ] **D.1** Define the division of labor between deterministic statistical layers (fast, continuous anomaly screening) and the LLM Agent (hypothesis testing, dynamic query generation, narrative synthesis).
- [ ] **D.2** Specify agent tools: `get_baseline_deviation()`, `query_user_history()`, `trigger_micro_inquiry()`, `retrieve_clinical_guidelines()`, `log_confounder()`.
- [ ] **D.3** Formulate proactive interaction triggers (hysteresis, anomaly confidence thresholds) to prevent excessive user prompting.

### Track E: Medical RAG & Knowledge Grounding
- [ ] **E.1** Curate a concise, high-authority clinical corpus: CDC/WHO prodromal illness guidelines, peer-reviewed biomarker correlation tables, and confounder differential reference guides.
- [ ] **E.2** Define retrieval schema: Hybrid dense/sparse search, metadata-filtered queries (by flagged biomarker and reported symptom).
- [ ] **E.3** Implement clinical guardrails: Explicit attribution verification, hallucination checks, and FDA/medical non-diagnostic compliance language.

### Track F: Feasibility, Scoping & 2-Week Delivery Plan
- [ ] **F.1** Define the Minimum Viable Demonstrator (MVD): Streaming time-series replay engine + Real-time Anomaly Pipeline + Proactive Agent + Grounded RAG + Interactive Dashboard.
- [ ] **F.2** Eliminate high-risk dependencies (e.g., requiring live physical hardware pairing or full custom model training).
- [ ] **F.3** Specify demonstration scenario: A multi-day timeline simulation transitioning from normal baseline -> subtle nocturnal anomaly -> agent proactive inquiry -> user confounder denial -> infection risk escalation -> grounded clinical warning.

---

## 5. Critical Assumptions NOT to Make Yet (Anti-Assumptions)

1. **Do NOT assume raw time-series points should be fed directly into an LLM context window.**
 * *Rationale:* High-frequency raw sensor data (e.g., 25Hz PPG or minute-level heart rate) will blow up token limits, introduce hallucinated numerical pattern recognition, and incur unacceptable latency/cost. Tokenization must occur over structured statistical representations, circadian residuals, and aggregated biomarker summaries.
2. **Do NOT assume the LLM should perform primary anomaly detection.**
 * *Rationale:* LLMs are poor substitutes for deterministic signal processing, FFTs, Kalman filters, or specialized time-series statistical models. The primary anomaly detection filter should be fast, mathematical, and deterministic.
3. **Do NOT assume a physical smartwatch connection is required for a convincing 2-week AI/ML system.**
 * *Rationale:* Building Bluetooth/iOS/Android background ingestion pipelines takes weeks of pure mobile dev and offers zero AI/ML novelty. A high-fidelity streaming playback harness over real benchmark datasets provides identical or superior demonstration value.
4. **Do NOT assume illness detection must identify specific pathogens (e.g., Influenza A vs. SARS-CoV-2 vs. Rhinovirus).**
 * *Rationale:* Non-invasive wearable sensors measure systemic autonomic and metabolic host responses (systemic inflammatory response), not microbiological pathogen identities. The claim must be calibrated as *systemic physiological strain / illness risk*, not molecular pathogen diagnosis.
5. **Do NOT assume RAG requires indexing millions of general medical web pages.**
 * *Rationale:* Generic medical vector dumps lead to irrelevant retrieval and hallucinations. A tightly curated, highly structured clinical reference corpus on prodromal signatures, viral timelines, and confounders is vastly more reliable and verifiable.
6. **Do NOT assume the system must alert the user at every anomaly.**
 * *Rationale:* A single night of elevated heart rate is usually alcohol, poor sleep, or late meals. Alerting on every deviation causes immediate alarm fatigue and abandonment. The system must support silent multi-day accumulation and proactive disambiguation.
7. **Do NOT assume a single universal baseline fits all users.**
 * *Rationale:* Normal resting heart rate varies from 45 to 85+ bpm across individuals. An absolute threshold (e.g., RHR > 75 bpm) is clinically invalid. All anomaly metrics must be relative to personalized, diurnal-adjusted baselines.
8. **Do NOT assume agent autonomy should be unconstrained.**
 * *Rationale:* Autonomous agents operating without deterministic guardrails in healthcare can generate inappropriate advice or prompt users relentlessly. Tool execution and prompting policies must have rigid deterministic guardrails.

---

## 6. Architectural Pivot Questions

The answers to the following questions will materially dictate our system design:

1. **Streaming Granularity vs. Sleep Rollup:**
 * *Option A:* Real-time intraday streaming anomaly detection (checking every hour).
 * *Option B:* Daily nocturnal sleep window rollup (analyzing clean overnight data where motion artifacts are minimized and circadian baseline is cleanest).
 * *Trade-off:* Published research (Stanford/Scripps) shows nocturnal metrics (sleeping RHR, nocturnal HRV, overnight skin temperature) have vastly higher signal-to-noise ratio than noisy daytime data.
2. **Time-Series Anomaly Engine Selection:**
 * *Option A:* Time-Series Foundation Model (e.g., TimesFM / Chronos) for zero-shot residual anomaly detection.
 * *Option B:* Deterministic Statistical Circadian Residual Filter (e.g., Cosinor + EWMA / CUSUM) + Lightweight Classifier.
 * *Trade-off:* Foundation models offer high AI engineering novelty; statistical filters offer rock-solid reliability, zero hallucination, and instantaneous inference. A hybrid approach may be optimal.
3. **Agent Orchestration Pattern:**
 * *Option A:* Single ReAct Agent with dynamic tool use (interpreting metrics, issuing queries, searching RAG).
 * *Option B:* Multi-Agent Hierarchical Architecture (Telemetry Analyst Agent + Diagnostic Verification Agent + User Communication Agent).
 * *Trade-off:* Single agent is simpler and faster; hierarchical agent separates clinical reasoning from user dialogue safety.
4. **Interactive Ingestion Interface:**
 * *Option A:* Streamlit / Gradio interactive timeline visualizer where users can scrub time, inject events (e.g., drink alcohol, simulate virus infection), and inspect the agent's live reasoning trace.
 * *Option B:* Full-stack Next.js + FastAPI web app with chat & chart interfaces.
 * *Trade-off:* Streamlit/Gradio maximizes time spent on ML/Agent engineering within 2 weeks; full-stack risks spending 70% of time on CSS/frontend plumbing.
