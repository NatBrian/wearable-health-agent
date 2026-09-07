# Deep Technical Discovery: Personal Health AI Agents, LLM-over-Wearable-Data Systems, & Time-Series Reasoning Agents
## Research Track 2

---

## 1. Executive Summary & Landscape Taxonomy

Wearable health intelligence is undergoing a foundational paradigm shift: moving from **static rule-based thresholding and hand-crafted dashboard aggregations** to **agentic, multi-modal, and program-aided time-series reasoning systems**.

Modern personal health agents fall into three distinct generations:
1. **Gen 1 (Statistical / ML Classifiers)**: Fixed feature-engineering pipelines (e.g., Apple Sleep Apnea detection, Oura Readiness scores) running on-device or in the cloud.
2. **Gen 2 (Direct Prompting / RAG over Wearable JSON)**: Naive serializations of raw sensor streams or JSON summaries directly into LLM context windows, plagued by severe numerical hallucination, context window exhaustion, and temporal blindness.
3. **Gen 3 (Agentic Code-Execution & Foundation Hybrid Systems)**: CodeAct/ReAct frameworks (e.g., Google PHIA, HiMe, VitalAgent, TS-Reasoner) where LLMs act as **orchestrators and code generators** over sandboxed data analysis engines (Pandas/DuckDB) or invoke specialized time-series foundation models (UniTS, Chronos), grounded in clinical knowledge retrieval and long-term hierarchical memory.

---

## 2. Deep Dive: Systematic Investigation (Attributes A – V)

### System 1: PHIA (Personal Health Insights Agent) & PHIA+ (Google Research / Nature Communications 2026)
* **A. Problem Solved**: LLMs struggle with complex multi-step numerical reasoning, longitudinal aggregation, and temporal indexing over dense wearable tracker data (sleep, activity, heart rate).
* **B. Input Data**: Multidimensional longitudinal time-series data stored as relational/tabular formats (daily summaries, 1-minute to 15-minute granularities).
* **C. Wearables/Devices**: Google Pixel Watch, Fitbit Charge/Sense series.
* **D. Physiological Signals**: Heart Rate (HR), Resting Heart Rate (RHR), Heart Rate Variability (HRV), Step count, Active Zone Minutes, Sleep stages, Sleep duration, Skin temperature, Caloric burn.
* **E. Data Processing**: Direct sandboxed code generation (Python/Pandas). Data is maintained in memory/files as Pandas DataFrames; agent generates dynamic code to filter, group, aggregate, and compute descriptive and inferential statistics.
* **F. Personalization Strategy**: Longitudinal baseline tracking (e.g., calculating 30-day personal baseline metrics) combined with user profile metadata and multi-session interaction history (HiMem).
* **G. ML / Statistical Methods**: Deterministic Python statistical libraries (NumPy, SciPy, Pandas) orchestrated by an LLM planner.
* **H. Training Required**: No mandatory model training for baseline PHIA; relies on prompt-engineered agentic loops (ReAct/CodeAct). PHIA+ incorporates medical retrieval fine-tuning.
* **I. Pretrained Models Available**: Uses API-accessible frontier LLMs (Gemini Ultra/Pro, PaLM 2).
* **J. LLM Used**: Gemini 1.0/1.5 Ultra, Gemini Pro, PaLM 2.
* **K. Agent Architecture**: ReAct (Reasoning + Acting) and CodeAct loops (Thought $\rightarrow$ Action [Code/Search] $\rightarrow$ Observation $\rightarrow$ Reflection $\rightarrow$ Final Answer).
* **L. Agent Tools / Actions**: Python REPL Sandbox (Pandas, NumPy, Matplotlib), Google Search API for clinical/health knowledge retrieval.
* **M. RAG / External Retrieval**: Yes. PHIA uses Google Search API; PHIA+ incorporates LLM-guided medical knowledge base retrieval (evidence grounding) and Hierarchical Memory (HiMem).
* **N. User Interaction**: Conversational natural language QA interface.
* **O. Real-Time vs. Offline**: Offline/Near-line interactive batch processing (analyzes historical synced wearable data upon user query).
* **P. Output Produced**: Grounded natural language health insights, numerical calculations, trend comparisons, and actionable behavioral recommendations.
* **Q. Evaluation Benchmarks**: Evaluated on two benchmark datasets containing >4,000 health insight questions spanning numerical calculations and open-ended wellness interpretation. Evaluated across 650 expert-hours with accredited health & wellness experts.
* **R. Reported Performance**:
 * **84% accuracy** on objective numerical queries (versus $<40\%$ for pure zero-shot LLM baselines).
 * **83% favorable ratings** on open-ended health interpretation.
 * Near-zero numerical hallucinations when computations were successfully offloaded to the Python sandbox.
* **S. Open-Source Availability**:
 * *Paper*: Nature Communications (Jan 2026) / arXiv:2406.06464 (*"Transforming Wearable Data into Personal Health Insights using Large Language Model Agents"*).
 * *GitHub*: `https://github.com/yahskapar/personal-health-insights-agent`.
* **T. Reusable Assets**: Prompt templates (`prompt_templates.py`), ReAct agent loop implementation, sandbox evaluation harness, and the 4,000+ question evaluation dataset.
* **U. Major Limitations**: High latency per query (multi-turn tool loop takes 5–15 seconds); dependency on cloud LLM APIs; inability to handle raw high-frequency waveform telemetry (e.g., 250Hz ECG) directly in Pandas without preprocessing.
* **V. Architectural Lesson**: **Never ask an LLM to do arithmetic on wearable data.** The LLM should only write Python/Pandas code to compute numbers and inspect the resulting scalar/table before generating natural language text.

---

### System 2: HiMe ("Say Hi to Healthy Me") (thinkwee / Wei Liu et al., arXiv:2607.21019)
* **A. Problem Solved**: Cloud-based wearable AI exposes highly sensitive personal biometric data to privacy risks; existing systems lack real-time continuous edge tracking and have prohibitive LLM inference costs.
* **B. Input Data**: Continuous physiological time-series streams and historical tabular records (real-time stream + hourly/daily historical tables).
* **C. Wearables/Devices**: Apple Watch (via companion iOS app), iPhone HealthKit.
* **D. Physiological Signals**: Continuous HR, Resting HR, HRV (SDNN), SpO2, Sleep stages/duration, VO2 max, Workout active calories, Step counts, Stand hours.
* **E. Data Processing**: Four-layer architecture with database-as-a-first-class component. Implements **"Agent-Authored Statistical Triggers"** (lightweight statistical rules generated by the LLM that execute on SQL/timeseries streams locally to detect anomalies before waking up the LLM).
* **F. Personalization Strategy**: Continuous user modeling in a local relational database; dynamically adjusted physiological baselines; digital twin persona adaptation.
* **G. ML / Statistical Methods**: Local rolling Z-score anomaly detectors, moving average baselines, coupled with local or API-based LLMs.
* **H. Training Required**: No; runs zero-shot with tool-use and localized prompt contexts.
* **I. Pretrained Models Available**: Works with local SLMs (via Ollama/vLLM) and cloud APIs (OpenAI, Anthropic, DeepSeek).
* **J. LLM Used**: Configurable: Local models (Llama 3 8B, Qwen 2.5 7B) or Cloud LLMs (GPT-4o, Claude 3.5 Sonnet).
* **K. Agent Architecture**: Plan-and-Solve with event-driven reactive agent triggers (Event Detector $\rightarrow$ State Aggregator $\rightarrow$ Agent Core $\rightarrow$ User Persona).
* **L. Agent Tools / Actions**: SQL queries over local SQLite/PostgreSQL health databases, statistical metric calculators, notification dispatchers, IM bot hooks.
* **M. RAG / External Retrieval**: User profile DB and longitudinal health history RAG via SQL time-windowing.
* **N. User Interaction**: Multi-channel conversational interface (iOS app, Telegram, Feishu, WeChat) + Interactive Visual "Digital Twin" (pixel-art avatar *HiMeow* reflecting physical strain/fatigue state).
* **O. Real-Time vs. Offline**: **Hybrid real-time & event-driven**: streaming ingestion on device/server + event-triggered agent execution + on-demand interactive QA.
* **P. Output Produced**: Proactive contextual notifications, daily health briefs, visual avatar state updates, conversational health advice.
* **Q. Evaluation Benchmarks**: Evaluated on self-hosted real-world longitudinal data; evaluated latency, event trigger precision, and user engagement metrics.
* **R. Reported Performance**: 90%+ reduction in LLM inference costs via statistical event triggers compared to continuous periodic LLM polling; zero external data leakage in fully local mode.
* **S. Open-Source Availability**:
 * *Paper*: arXiv:2607.21019 (*"HiMe: Real-Time Self-Hosted Personal Agent Platform for Health Insights with Wearable Devices"*).
 * *GitHub*: `https://github.com/thinkwee/HiMe`.
* **T. Reusable Assets**: Full self-hosted FastAPI server, iOS HealthKit bridge app, Docker deployment scripts, agent trigger engine.
* **U. Major Limitations**: Requires self-hosting server infrastructure; local SLMs on edge hardware exhibit weaker reasoning on subtle longitudinal correlations compared to frontier models.
* **V. Architectural Lesson**: **Event-driven statistical triggers are essential for scalable wearable agents.** Do not stream wearable telemetry straight into an LLM; let lightweight statistical triggers gate LLM invocations.

---

### System 3: AI on the Pulse (@HOME Anomaly Detection) (Gabrielli et al., CIKM 2025 / arXiv:2508.03436)
* **A. Problem Solved**: Unsupervised anomaly detection and clinical explanation in continuous patient monitoring without requiring expensive labeled clinical datasets or hospital-grade equipment.
* **B. Input Data**: Continuous multi-channel physiological and ambient time-series streams (sampled at 1 Hz – 1/60 Hz).
* **C. Wearables/Devices**: Consumer smartwatches (WearOS / Apple Watch) + ambient room sensors.
* **D. Physiological Signals**: Heart Rate, HRV, Accelerometry (3-axis activity count), ambient room temperature, motion telemetry.
* **E. Data Processing**: Universal time-series embedding extraction via **UniTS** foundation model; reconstruction loss and temporal contrastive scoring to calculate multi-channel anomaly vectors.
* **F. Personalization Strategy**: Unsupervised personalized baseline learning; learns subject-specific normal physiological manifold over initial 48–72 hour calibration.
* **G. ML / Statistical Methods**: **UniTS** (Universal Time Series foundation model) + Unsupervised Temporal Autoencoding & Anomaly Scoring.
* **H. Training Required**: Pretrained UniTS backbone; fine-tuning/adaptation on individual calibration window.
* **I. Pretrained Models Available**: Yes, UniTS foundation checkpoints are open-source.
* **J. LLM Used**: Llama 3 / Mistral / GPT-4 for translation layer.
* **K. Agent Architecture**: Two-stage Hybrid: Neural Time-Series Foundation Model (UniTS) $\rightarrow$ Anomaly Signal Interpreter Agent.
* **L. Agent Tools / Actions**: Feature attribution extractor, clinical symptom matcher, doctor alert generator.
* **M. RAG / External Retrieval**: Clinical rule database and home-care escalation protocols.
* **N. User Interaction**: Caregiver/Clinician dashboard + Patient emergency push notifications.
* **O. Real-Time vs. Offline**: Real-time continuous streaming inference with sub-minute alert generation.
* **P. Output Produced**: Real-time anomaly scores, risk alert cards, structured clinical summary for remote doctors.
* **Q. Evaluation Benchmarks**: Evaluated against 12 state-of-the-art multivariate time-series anomaly detection baselines across home-care monitoring cohorts.
* **R. Reported Performance**: ~**22% improvement in F1 score** over 12 baseline models; high clinical concordance on generated risk summaries.
* **S. Open-Source Availability**: arXiv:2508.03436 & ACM CIKM 2025.
* **T. Reusable Assets**: UniTS multi-task time-series backbone integration code and anomaly-to-text prompt pipeline.
* **V. Architectural Lesson**: **Decouple anomaly detection from semantic explanation.** Use specialized time-series foundation models (UniTS) for mathematical representation, and reserve LLMs strictly for translating numeric embeddings into clinical language.

---

### System 4: Health-LLM & HealthAlpaca Benchmark (Kim et al., MIT & Google / arXiv:2401.06866)
* **A. Problem Solved**: Comprehensive evaluation and benchmarking of LLMs' ability to perform zero-shot, few-shot, and fine-tuned health outcome predictions directly from wearable sensor time-series data.
* **B. Input Data**: Aggregated daily and intra-day wearable metrics paired with survey/ground-truth clinical scores.
* **C. Wearables/Devices**: Fitbit Charge/Versa/Sense, Apple Watch, Empatica E4.
* **D. Physiological Signals**: Resting Heart Rate, Sleep efficiency/duration, Intra-day Step counts, Caloric burn, Skin conductance (EDA).
* **E. Data Processing**: Tabular feature extraction + Context Enhancement (demographic context, temporal delta framing, health domain knowledge injection).
* **F. Personalization Strategy**: In-context demographic prompting (age, biological sex, chronic conditions, historical average baselines).
* **G. ML / Statistical Methods**: Parameter-Efficient Fine-Tuning (PEFT / LoRA) and Instruction Tuning on sensor-text pairs.
* **H. Training Required**: Yes for **HealthAlpaca** (fine-tuned on sensor-outcome pairs); No for zero-shot LLM benchmarks.
* **I. Pretrained Models Available**: HealthAlpaca weights and benchmark splits are open for research.
* **J. LLM Used**: Evaluated 12 models: GPT-4, GPT-3.5, Gemini Pro, PaLM 2, Claude 2, Llama 2 (7B/13B/70B), Alpaca 7B, Flan-T5.
* **R. Reported Performance**:
 * Context Enhancement improved prediction accuracy by up to **23.8%**.
 * **HealthAlpaca (7B/13B)** fine-tuned with LoRA outperformed base GPT-4 and Gemini Pro in **8 out of 10 consumer health prediction tasks**.
* **S. Open-Source Availability**: arXiv:2401.06866 / MIT SEA Lab repository.
* **V. Architectural Lesson**: **Contextual framing (user profile + baseline deltas) is more critical than LLM parameter count.** A 7B model with rich context beats a 1.7T parameter model fed raw numbers.

---

### System 5: VitalAgent & VitalBench (Tool-Augmented Waveform Agent / arXiv:2605.29483)
* **A. Problem Solved**: Enabling LLM agents to perform both **reactive question answering** and **proactive clinical monitoring** over raw high-frequency physiological waveforms (ECG, PPG) rather than just daily aggregate summaries.
* **B. Input Data**: Continuous multi-lead ECG (125–500 Hz) and optical PPG waveforms (25–100 Hz), downsampled/windowed into tool-callable buffers.
* **C. Physiological Signals**: Raw ECG waveforms, raw PPG pulse contours, instantaneous Inter-Beat Intervals (IBI), HRV time/frequency domain metrics.
* **E. Data Processing**: Tool-mediated signal processing: Wavelet denoising, Pan-Tompkins QRS peak detection, morphological feature extractors, and rhythm classification executed via modular Python tools.
* **F. Personalization Strategy**: **Longitudinal Physiological Memory (LPM)**: Persistent vector-and-relational memory tracking baseline morphology and alert frequency.
* **G. ML / Statistical Methods**: Specialized signal-processing tool library (BioSPPy, NeuroKit2, SciPy) invoked by an LLM planner.
* **J. LLM Used**: DeepSeek-V3/V4, GPT-4o, Claude 3.5 Sonnet.
* **K. Agent Architecture**: Plan-and-Solve with Longitudinal Physiological Memory and Dynamic Tool Invocation.
* **L. Agent Tools / Actions**: Waveform peak detection tool, Arrhythmia classifier tool, HRV spectral power tool, Stress index calculator, SQI evaluator.
* **M. RAG / External Retrieval**: Cardiology diagnostic guideline retrieval (AHA/ACC criteria) + Longitudinal Memory store.
* **N. User Interaction**: Dual: Conversational Chatbot (User QA) + Automated Proactive Alert Push.
* **R. Reported Performance**: 25%–30% relative improvement in diagnostic reasoning accuracy over standard ReAct and Direct Prompting baselines.
* **S. Open-Source Availability**: arXiv:2605.29483.
* **V. Architectural Lesson**: Wrap DSP algorithms (QRS detectors, FFT spectral filters) as deterministic tools that return symbolic event descriptors and summary statistics to the agent.

---

## 3. Comprehensive Cross-System Comparative Matrix

| Feature / Dimension | Google PHIA / PHIA+ | HiMe Agent | AI on the Pulse | Health-LLM (MIT/Google) | VitalAgent | Whoop Coach / Oura Advisor |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Primary Modality** | Tabular Wearable Metrics | Real-time HealthKit/Wearable | Multi-sensor + Ambient | Multi-dataset Tabular | ECG/PPG Waveforms + Logs | Proprietary Daily Scores |
| **Time Granularity** | 1-min to 1-day | 1-sec to 1-day | 1-sec to 1-min | Daily / Hourly Aggregates | 125–500 Hz Waveforms | Daily / Epoch Summary |
| **Core Architecture** | ReAct + Code Generation | 4-Layer + Stat Triggers | UniTS Foundation + LLM | Fine-Tuned PEFT LLM | Tool-Agent + Long Memory | Cloud LLM + Scoring API |
| **LLM Engine** | Gemini Ultra / PaLM 2 | Llama 3 / GPT-4o / Local | Llama 3 / GPT-4 | HealthAlpaca 7B / GPT-4 | DeepSeek-V3 / GPT-4o | GPT-4 / Proprietary Oura LLM |
| **Tool Execution** | Python Pandas Sandbox | SQLite / Postgres SQL | UniTS Feature Attribution | N/A (Direct Inference) | BioSPPy / NeuroKit2 DSP | Proprietary API Endpoints |
| **Knowledge RAG** | Google Search + HiMem | User Profile Store | Clinical Rule DB | Clinical Scoring Prompts | AHA/ACC Guidelines + LPM | Sports Science / Sleep DB |
| **Operation Mode** | Offline Interactive QA | Real-time & Event-Driven | Real-time Streaming | Offline Batch Benchmark | Real-time Daemon + QA | Interactive Chat QA |
| **Numerical Accuracy**| **84% (High)** | **High (SQL-based)** | **High (UniTS F1 +22%)** | Moderate (70-85%) | **High (DSP Tools)** | High (API-constrained) |
| **Open Source?** | Yes (Paper + GitHub) | Yes (Paper + Full App) | Yes (Paper + Framework) | Yes (Paper + Dataset/LoRA)| Yes (Paper + VitalBench)| No (Proprietary Commercial) |

---

## 4. Time-Series Serialization Paradigms

```
 TIME-SERIES SERIALIZATION SPECTRUM

 [ Raw Digit Strings ] [ JSON / CSV Text ] [ Token Quantization ] [ Code-over-DataFrame ]
 - e.g. "72, 74, 75..." - e.g. {"hr": 72...} - e.g. Chronos / Patch - e.g. PHIA / HiMe
 - Massive token bloat - Moderate bloat - Discrete vocabulary - ZERO raw data tokens
 - Numerical hallucination - Poor long-range trends - Great for forecasting - Pure Python/SQL logic
 - Context window crash - Token expensive - No natural language QA - Exact math & plotting
```

* **The Dominant Gold Standard (PHIA / HiMe / CodeAct)**: The LLM receives dataset schema and previews, generates Python/Pandas code, executes inside a sandboxed REPL, and receives exact calculated scalars/summaries. This eliminates numerical hallucinations, scales to multi-year histories, and allows dynamic feature engineering on the fly.
