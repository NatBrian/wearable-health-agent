# Evidence-Derived Landscape Synthesis & Reference Architecture
## Phase 3: Landscape Synthesis, Component Boundaries & Evidence-Derived Architecture

**Project:** Adaptive Agentic Wearable Early-Warning & Health Monitoring System
**Objective:** Synthesize empirical findings from Phase 2 to establish clear component boundaries, determine genuine AI/Agent value-adds, and construct the Evidence-Derived Reference Architecture.

---

## 1. Top 8 Architectural Patterns Supported by Existing Systems

Based on empirical evidence across Stanford NightSignal, Oura/TemPredict, Scripps DETECT, WHOOP, Google PHIA, and HiMe:

```
+--------------------------------------------------------------------------------------------------+
| 1. TWO-TIER DECOUPLED ANOMALY GATING (HiMe / Apple Vitals Pattern) |
| Continuous sensor processing runs on fast, deterministic filters/models. The LLM is asleep |
| 95%+ of the time and only wakes on verified statistical trigger events. |
+--------------------------------------------------------------------------------------------------+
| 2. PROGRAM-AIDED EXECUTION / CODEACT OVER DATAFRAMES (Google PHIA Pattern) |
| LLM never receives raw time-series numbers in context; it writes Python/Pandas code executed |
| in a sandboxed REPL to compute exact scalars, eliminating numerical hallucinations. |
+--------------------------------------------------------------------------------------------------+
| 3. NOCTURNAL SLEEP & SWS QUIESCENCE FILTERING (Oura / WHOOP / NightSignal Pattern) |
| Primary infection surveillance is gated strictly to sleep (especially Slow-Wave Sleep), |
| stripping away >95% of daytime motion, posture, meal, and emotional stress artifacts. |
+--------------------------------------------------------------------------------------------------+
| 4. PERSONALIZED ROLLING BASELINE NORMALIZATION (Stanford / Scripps Pattern) |
| Static universal thresholds fail completely. Baseline is computed over a rolling 14-to-30 day|
| window per individual: Delta = (x_t - mu_{14-day}) / sigma_{14-day}. |
+--------------------------------------------------------------------------------------------------+
| 5. MULTIMODAL BIOPHYSICAL TRIAD FUSION (Oura / TemPredict Pattern) |
| Fuses Autonomic (RHR/HRV) + Thermal (Skin Temp) + Pulmonary (Respiratory Rate) to capture |
| progressive stages of immune response, outperforming single-sensor models by +5-8% AUC. |
+--------------------------------------------------------------------------------------------------+
| 6. ADAPTIVE EVENT-TRIGGERED MICRO-INQUIRIES (Scripps DETECT / Active Learning Adaptation) |
| Passive sensors cannot distinguish alcohol/overtraining from infection; daily surveys suffer |
| >70% dropout. Single-tap micro-inquiries triggered ONLY on ambiguous anomalies bridge the gap.|
+--------------------------------------------------------------------------------------------------+
| 7. TWO-STAGE ANOMALY-TO-TEXT DECOUPLING (AI on the Pulse / VitalAgent Pattern) |
| Specialized time-series models/DSP handle numerical anomaly scoring; LLM is reserved |
| strictly for translating numeric embeddings into clinical explanations. |
+--------------------------------------------------------------------------------------------------+
| 8. DETERMINISTIC HARDCODED EMERGENCY TRIAGE (Clinical CDS Pattern) |
| Critical vitals (SpO2 < 90%, HR > 140) bypass the LLM entirely and immediately render |
| unalterable emergency clinical redirection. |
+--------------------------------------------------------------------------------------------------+
```

---

## 2. What Approaches Work Well Across Key System Dimensions

| System Dimension | What Empirically Works Best | What Fails or Underperforms |
| :--- | :--- | :--- |
| **Continuous Wearable Monitoring** | Ingesting into an append-only local time-series store (SQLite/Parquet); background BLE/webhook sync; downsampling to 1-min / 5-min epochs. | Streaming raw 250Hz waveforms straight to cloud or LLM. |
| **Personal Baseline Modeling** | 14-to-30 day rolling median and Median Absolute Deviation (MAD); Cosinor circadian detrending; excluding sick days from baselines. | Static population thresholds (e.g. "HR > 75 bpm = fever"). |
| **Anomaly Detection** | CUSUM / EWMA statistical process control or Zero-Shot Foundation Model quantile forecasting (Chronos-Bolt 95% upper bound). | Unconstrained end-to-end black-box deep neural networks without baseline normalization. |
| **Early Illness Detection** | The Biophysical Triad: Distal skin temp rise ($+0.5\text{--}1.5^\circ\text{C}$) + Nocturnal RHR surge ($+5\text{--}15\text{ bpm}$) + HRV drop + Respiratory rate surge. | Single-metric heart rate monitoring during active daytime hours. |
| **Reducing False Alerts** | Multi-night / multi-hour temporal persistence requirements (debouncing) + Active confounder filtering (alcohol, overtraining, luteal phase). | Alerting immediately on isolated, transient 1-hour heart rate spikes. |
| **Contextual Reasoning** | Program-aided CodeAct over longitudinal historical logs (Pandas) + multi-hypothesis causal evaluation. | Direct zero-shot LLM reasoning over raw un-aggregated sensor data. |
| **User Interaction** | Low-friction, single-tap micro-inquiries with discrete choices ("Had alcohol", "Hard workout", "Feeling sick", "Normal"). | Mandatory daily multi-page symptom questionnaires (>70% user attrition). |
| **Medical Knowledge Grounding** | Curated vector index of peer-reviewed prodromal timelines and CDC/StatPearls guidelines with Pydantic citation enforcement (`Instructor`). | Uncurated generic web searches or broad medical textbook dumps. |
| **Generating Actionable Outputs** | Non-prescriptive, calibrated educational insights highlighting baseline deltas, ruled-out confounders, and non-pharmacological recovery tips. | Vague score summaries ("Readiness: 62") or unauthorized medical diagnoses ("You have Flu A"). |

---

## 3. Component Separation & Decoupling Rationale

To ensure clinical safety, low latency, testability, and zero hallucination, the following 6 components **must remain strictly decoupled**:

```
 ┌─────────────────────────────────────────────────────────────────────────┐
 │ Layer 1: Time-Series DSP & Feature Extraction (NeuroKit2 / FLIRT) │
 └────────────────────────────────────┬────────────────────────────────────┘
 │ Extracted Epoch Metrics
 ▼
 ┌─────────────────────────────────────────────────────────────────────────┐
 │ Layer 2: Deterministic & Foundation Anomaly Engine (CUSUM / Chronos) │
 └────────────────────────────────────┬────────────────────────────────────┘
 │ Anomaly Event & Residuals
 ▼
 ┌─────────────────────────────────────────────────────────────────────────┐
 │ Layer 3: Deterministic Emergency Red-Flag Interceptor (Regex / Limits) │
 └────────────────────────────────────┬────────────────────────────────────┘
 │ Non-Emergency Event Passed
 ▼
 ┌─────────────────────────────────────────────────────────────────────────┐
 │ Layer 4: Agentic Orchestrator & Inquiry Policy (ReAct / CodeAct) │
 ├────────────────────────────────────┼────────────────────────────────────┤
 │ Layer 5: Sandboxed Code REPL │ Layer 6: Grounded Medical RAG │
 │ (Pandas Longitudinal Analysis) │ (StatPearls / CDC Vector Store) │
 └────────────────────────────────────┴────────────────────────────────────┘
```

### Why They Must Remain Separate:
1. **Signal Processing vs. LLM:** Raw PPG/ECG waveforms (25–250Hz) are continuous analog biosignals. Feeding them to an LLM exhausts tokens in seconds and produces severe mathematical errors. DSP belongs in compiled C/Python libraries (`neurokit2`).
2. **Primary Anomaly Detection vs. Agent Orchestration:** Anomaly detection must be continuous, fast ($<15\text{ms}$), deterministic, and cheap. Running an LLM on every heartbeat or 5-minute epoch is economically and computationally impossible. Anomaly filters must gate the agent.
3. **Emergency Interceptor vs. LLM Reasoning:** If a user's $SpO_2 < 88\%$ or resting $HR > 145\text{ bpm}$, this is a potential medical emergency. An LLM must never be allowed to "reason" or hallucinate wellness advice; a deterministic rule must immediately take over.
4. **Calculations vs. Text Generation:** LLMs are autoregressive token predictors, not calculators. All statistical aggregations, correlations, and baseline deltas must be computed in Python/Pandas before the LLM writes a word.
5. **Medical Knowledge RAG vs. Agent Memory:** Clinical guidelines must be strictly sourced from versioned medical corpora with verified citations, isolated from the user's personal longitudinal session memory.

---

## 4. What Tasks Should NOT Be Delegated to an LLM

1. ❌ **Raw Signal Processing & Peak Detection:** Never use an LLM to detect QRS complexes, filter PPG artifacts, or calculate IBI.
2. ❌ **Continuous 24/7 Stream Surveillance:** Never poll an LLM on regular time-series intervals.
3. ❌ **Mathematical & Statistical Aggregations:** Never ask an LLM "What was my average HRV last week?" without a code tool.
4. ❌ **Emergency Clinical Triage:** Never let an LLM decide if a life-threatening vital sign is safe.
5. ❌ **Primary Anomaly Scoring:** Never ask an LLM "Does this curve look like an anomaly?" (Use MOMENT, Chronos, or CUSUM).

---

## 5. Where an LLM Actually Adds Measurable Value

1. **Translating Multi-Metric Biophysical Deviations into Clinical Narratives:** Explaining *why* elevated RHR (+9 bpm) paired with high skin temperature (+1.1°C) and dropped HRV indicates immune activation rather than simple fatigue.
2. **Multi-Hypothesis Causal Synthesis:** Weighing multiple conflicting signals simultaneously (wearable anomalies + user-reported symptoms + alcohol/workout history + clinical guideline timelines).
3. **Dynamic Code Generation for Ad-Hoc Longitudinal Queries:** Generating custom Pandas filtering and correlation scripts on the fly based on user questions.
4. **Formulating Context-Aware Micro-Inquiries:** Crafting natural, non-alarmist, context-specific questions to clarify ambiguous anomalies (e.g. factoring in that the user had an intense workout logged yesterday).

---

## 6. Where an Agent Adds Value Beyond a Normal Pipeline

A static pipeline executes a fixed sequence: `Data -> Filter -> Classify -> Output`. An **Agentic Decision Policy** ($\pi(a_t \mid h_t)$) provides unique value when the next action depends dynamically on the ambiguity of intermediate results:

```
 Agentic Value Decision Tree
 |
 Is Anomaly Ambiguous?
 |
 +----------------+----------------+
 | YES | NO (Clear Viral Signature)
 v v
 [Action: Micro-Inquiry] [Action: Query RAG & Warn]
 "Did you drink alcohol or Retrieve prodromal timelines
 exercise intensely?" and issue grounded warning.
 |
 +-----------+-----------+
 | User: "Had 3 beers" | User: "No confounders"
 v v
 [Action: Log Confounder] [Action: Escalate Risk & Query RAG]
 Suppress infection alarm. Issue early warning.
```

* **Dynamic Information Acquisition:** The agent actively decides *when* to ask the user for information, minimizing user burden while maximizing diagnostic confidence.
* **Multi-Step Tool Orchestration:** The agent queries user history, inspects baseline distributions, runs RAG lookups, and synthesizes evidence only when needed.

---

## 7. Medical RAG: Necessary, Optional, or Unnecessary?

| Project Subsystem | RAG Necessity Tier | Justification |
| :--- | :--- | :--- |
| **Prodromal Timelines & Differential Checklists** | **NECESSARY** | LLMs hallucinate incubation timelines and symptom progressions. Grounding responses in CDC/StatPearls corpora is essential for clinical accuracy and citation provenance. |
| **Non-Pharmacological Recovery Guidance** | **NECESSARY** | Grounding hydration, rest, and symptom-monitoring guidance in verified clinical literature prevents unauthorized medical prescription. |
| **Confounder Reference Profiles** | **OPTIONAL** | Knowledge of how alcohol or overtraining affects HRV can be prompt-engineered, but a RAG reference improves technical precision. |
| **Primary Anomaly Detection** | **UNNECESSARY** | Anomaly detection is purely mathematical; searching medical text adds zero value. |
| **Personal Baseline & Metric Calculations** | **UNNECESSARY** | User data lives in relational DataFrames/SQL, accessed via code execution, not vector search. |

---

## 8. Evidence For and Against Pretrained Foundation Models vs. Statistical Baselines

### Pretrained Time-Series Foundation Models (Chronos-Bolt, MOMENT)
* **Strongest Evidence FOR:**
 * **Zero-Shot Baseline Envelope Forecasting:** Chronos-Bolt predicts 24-hour circadian quantile envelopes without requiring per-user model training or manual tuning.
 * **Multivariate Reconstruction Loss:** MOMENT computes zero-shot reconstruction error across masked patches, capturing multi-sensor deviations directly.
 * **AI/ML Engineering Novelty:** Demonstrates cutting-edge time-series foundation model application in health.
* **Strongest Evidence AGAINST:**
 * **Channel Independence:** Chronos and MOMENT process channels independently, failing to model joint physiological interactions natively without downstream fusion.
 * **Inference Overhead:** Higher compute footprint than simple statistical filters (though Chronos-Bolt runs in <15ms on CPU).

### Personalized Statistical Anomaly Detection (NightSignal FSM, CUSUM, Cosinor)
* **Strongest Evidence FOR:**
 * **Proven Clinical Efficacy:** Stanford NightSignal achieved 78–81% sensitivity with a 3-day lead time using a purely deterministic FSM on RHR residuals.
 * **Zero Compute & Zero Hallucination:** Executes in microseconds, runs locally, and is 100% mathematically interpretable.
* **Strongest Evidence AGAINST:**
 * **Brittle Threshold Tuning:** Requires manual heuristics ($k \times MAD$) that may not generalize across all wearable device brands.
 * **Univariate Focus:** Struggles with complex non-linear interactions across 5+ asynchronous sensor streams.

**Synthesis / Verdict:** **Use a Hybrid Engine.** Deploy a fast statistical filter (NightSignal/CUSUM) for the continuous primary anomaly trigger, paired with Chronos-Bolt for zero-shot 24-hour baseline envelope forecasting.

---

## 9. Major Limitations Making "Predict Whether User Is Sick" Difficult

1. **Etiological Non-Specificity:** Wearables measure host inflammatory responses, not pathogens. Flu, COVID-19, RSV, common cold, and bacterial infections produce identical systemic biometric signatures.
2. **Behavioral Confounder Overlap:** Acute alcohol consumption, intense late-night workouts, travel jet lag, and acute emotional stress mimic viral prodromes (RHR spike, HRV crash).
3. **Hormonal & Menstrual Confounding:** The ovulatory luteal phase causes a sustained +0.3°C to +0.5°C body temperature rise and RHR increase for 10–14 days.
4. **User Compliance & Missing Nocturnal Data:** Users forgetting to charge devices or taking them off before bed breaks longitudinal continuity.
5. **Active Survey Fatigue:** Users abandon daily symptom questionnaires (>70% drop within 30 days).

---

## 10. What Can Realistically Be Demonstrated in 2 Weeks

```
+--------------------------------------------------------------------------------------------------+
| 2-WEEK FEASIBLE DELIVERABLES (High Impact, Zero Gimmick) |
| |
| 1. High-Fidelity Time-Warp Replay Server (FastAPI / WebSockets / SSE) |
| Streams real longitudinal wearable data from the Stanford COVID-19 / TemPredict cohorts with |
| interactive speed controls (1x, 60x, 300x) and confounder injection toggles (Alcohol, Workout)|
| |
| 2. Dual Anomaly Detection Engine (Local Python) |
| • Fast Statistical Anomaly Gate (CUSUM + 14-day rolling baseline) |
| • Zero-Shot Foundation Model Forecasting (Chronos-Bolt-Base 24h baseline envelope) |
| |
| 3. Adaptive Agentic Orchestrator (ReAct / CodeAct with LLM) |
| • Tool 1: `query_biometric_history(metric, window)` -> Executes Pandas code in sandbox |
| • Tool 2: `evaluate_confounder(event_type)` -> Analyzes activity/alcohol log correlation |
| • Tool 3: `trigger_micro_inquiry(question_type)` -> Dispatches interactive prompt to user |
| • Tool 4: `retrieve_clinical_guidelines(bioreviewers, symptoms)` -> Queries StatPearls/CDC RAG |
| |
| 4. Medical RAG & Safety Guardrail Pipeline |
| • ChromaDB vector store indexing StatPearls respiratory prodromes & CDC protocols |
| • Instructor + Pydantic schema enforcement (guaranteed structured output + verified citations)|
| • Hardcoded emergency red-flag interceptor |
| |
| 5. Interactive Streamlit / Web Visualizer |
| • Multi-metric longitudinal telemetry charts with live baseline envelopes |
| • Interactive time scrubber & event injector |
| • Live agent thought trace & tool execution log inspector |
| • Interactive micro-inquiry response widget & grounded clinical early-warning card |
+--------------------------------------------------------------------------------------------------+
```

---

## 11. Evidence-Derived Reference Architecture

```
====================================================================================================
 EVIDENCE-DERIVED REFERENCE ARCHITECTURE
====================================================================================================

 [ INPUT LAYER ]
 +------------------------------------+ +------------------------------------+
 | [PROVEN] Stanford COVID Benchmark | | [PROVEN] Synthetic Generator & |
 | Longitudinal Fitbit/Apple Data | | Confounder Injector (Alcohol/Ex) |
 +-----------------+------------------+ +-----------------+------------------+
 | |
 +-------------------+-------------------+
 |
 v
 [ STREAMING & INGESTION LAYER ]
 +----------------------------------------------------------------------------+
 | [PROVEN] FastAPI / WebSocket Time-Warp Replay Server |
 | Ingests raw telemetry, downsamples to 5-min epochs, maintains SQLite store |
 +-------------------------------------+--------------------------------------+
 |
 v
 [ FEATURE & BASELINE ENGINE ]
 +----------------------------------------------------------------------------+
 | [PROVEN] FLIRT / NeuroKit2 Feature Extractor |
 | Extracts Nocturnal RHR, HRV (rMSSD), Temp Deviation, Respiratory Rate |
 | Computes 14-day Rolling Baselines: mu_base, sigma_base |
 +-------------------------------------+--------------------------------------+
 |
 v
 [ DUAL ANOMALY GATE ]
 +-------------------------------------+--------------------------------------+
 | [PROVEN] Fast Statistical Anomaly | [PROMISING] Chronos-Bolt Foundation |
 | Filter: CUSUM / NightSignal FSM | 24h Baseline Quantile Forecasting |
 +-------------------------------------+--------------------------------------+
 |
 Is Anomaly >= Threshold?
 |
 +----------------+----------------+
 | NO | YES
 v v
 +-----------------+ +----------------------------------------+
 | [PROVEN] Silent | | [PROVEN] Deterministic Emergency |
 | Log (No LLM) | | Red-Flag Interceptor (SpO2/HR limits) |
 +-----------------+ +-------------------+--------------------+
 | Non-Emergency Anomaly
 v
 [ AGENTIC REASONING & ACTIVE DISAMBIGUATION LAYER ]
 +----------------------------------------------------------------------------+
 | [PROMISING] Adaptive Agent Orchestrator (ReAct / CodeAct Planner) |
 | Dynamically chooses investigative actions based on anomaly ambiguity: |
 +--------------------+-------------------+--------------------+--------------+
 | | |
 v v v
 +----------------------+ +--------------------+ +----------------------+
 | [PROVEN] CodeAct REPL| | [PROMISING] Active | | [PROVEN] Medical RAG |
 | Pandas Execution | | Micro-Inquiry | | StatPearls / CDC |
 | Sandbox (PHIA) | | Dispatcher | | ChromaDB Vector Store|
 +----------------------+ +--------------------+ +----------------------+
 | | |
 +-------------------+--------------------+
 |
 v
 [ GROUNDED OUTPUT & INTERFACE LAYER ]
 +----------------------------------------------------------------------------+
 | [PROVEN] Instructor Pydantic Safety Guardrail & Clinical Formatter |
 | Emits structured, non-diagnostic early warning with literature citations |
 +-------------------------------------+--------------------------------------+
 |
 v
 +----------------------------------------------------------------------------+
 | [PROVEN] Interactive Streamlit Demonstration Dashboard |
 | Visualizes time-series envelopes, live agent traces & micro-inquiry widgets|
 +----------------------------------------------------------------------------+
====================================================================================================
```

### Architecture Component Maturity Classification

| Component | Maturity Tier | Evidence Source |
| :--- | :--- | :--- |
| **Nocturnal Quiescence Gating** | **[PROVEN]** | Oura, WHOOP, NightSignal, TemPredict |
| **14-to-30 Day Baseline Subtraction** | **[PROVEN]** | Stanford Snyder Lab, Scripps DETECT |
| **Statistical CUSUM / FSM Anomaly Filter** | **[PROVEN]** | Stanford NightSignal (*Nat Med* 2022) |
| **Code-over-DataFrame Execution (PHIA)** | **[PROVEN]** | Google PHIA (*Nat Commun* 2026) |
| **Deterministic Emergency Triage Interceptor** | **[PROVEN]** | Standard Clinical CDS Guidelines |
| **Pydantic Schema Enforcement (`Instructor`)** | **[PROVEN]** | Production LLM engineering best practice |
| **Zero-Shot TS Foundation Model Forecasting** | **[PROMISING]** | Chronos-Bolt (Amazon), MOMENT (CMU) |
| **Event-Triggered Active Micro-Inquiries** | **[PROMISING]** | Scripps DETECT active learning adaptation |
| **Two-Stage Anomaly-to-Text Decoupling** | **[PROMISING]** | AI on the Pulse (*ACM CIKM* 2025) |
| **24/7 Continuous Intraday Streaming LLM Agent** | **[SPECULATIVE]** | Brittle; unproven signal-to-noise ratio in wild |
| **Direct Waveform Tokenization into LLMs** | **[SPECULATIVE]** | Proven to cause severe arithmetic hallucinations |
| **Autonomous Multi-Agent Debating Swarms** | **[SPECULATIVE]** | Excessive latency/cost; no proven accuracy gain |
