# Wearable Health Agent (WHA)

Agentic early-warning and causal attribution for consumer wearable data.

WHA separates continuous physiological deviation monitoring from episodic investigation. Every morning it computes resting heart rate from wearable sensors against an empirical shrinkage baseline without invoking a language model. On quiet nights, execution cost is zero. When a physiological anomaly is flagged, a bounded agent investigates: it tracks exact causal probabilities over 12 candidate causes, calculates the Expected Value of Sample Information (EVSI) against quantified interruption costs to determine whether to ask questions or order watch measurements, and terminates at a schema-validated grounded disposition.

---

## Key Features

- **Zero-LLM Passive Monitoring**: Daily overnight processing uses robust statistics (MAD shrinkage, empirical Bayes) running locally on CPU in milliseconds.
- **Deterministic Red-Flag Intercept**: Hard-coded clinical safety filters execute before any model reasoning and escalate severe presentations directly to clinical triage.
- **Exact 12-Cause Belief State**: Discrete Bayesian update over 4,096 causal states using peer-reviewed effect sizes and temporal curves.
- **Arithmetic Value-of-Information Policy**: Decides whether to stay silent (OBSERVE), ask a question (ASK), or request a test (MEASURE) based on EVSI minus interruption cost.
- **Grounded Clinical Differential**: Strict source attribution requiring retrieved knowledge passages for every non-tautological claim.
- **Auditable & Tamper-Evident**: Cryptographic SHA-256 hash-chained audit log with human approval checkpoints for safety-critical actions.
- **Offline & Deterministic Testing**: Full cassette recording and synthetic data generators for reproducible offline verification.

---

## Quickstart

### 1. Installation

Requires Python 3.12 and `uv`:

```bash
# Clone the repository
git clone https://github.com/NatBrian/wearable-health-agent.git
cd wearable-health-agent

# Install dependencies and sync environment
uv sync
```

### 2. Verify System Health

Run the doctor command to initialize the SQLite database, apply migrations, and verify knowledge tables:

```bash
uv run wha doctor
```

### 3. Run Scenario Demonstrations

Execute deterministic demonstration scenarios with offline cassette replays:

```bash
# Standard illness onset scenario
uv run wha demo run illness-onset

# Deterministic red-flag safety intercept scenario
uv run wha demo run red-flag
```

### 4. Launch Dashboard & Scheduler

Start the local Streamlit web application and background scheduler:

```bash
uv run wha serve --port 8501
```

Access the dashboard at `http://localhost:8501`.

---

## Architecture & Daily Lifecycle

```
  Overnight: Wearable records HR, steps, sleep, exercise -> Local bridge
      |
  Morning Batch: `wha nightly`
      | Ingestion -> Quality Gate -> Baseline Estimation -> Anomaly Detection
      |
      +-- Normal Night -> Write record, Cost = $0, 0 LLM calls
      |
      +-- Deviation Flagged -> Deterministic Red-Flag Safety Check
              |
              +-- Crossed -> ESCALATE (Immediate Clinical Referral)
              |
              +-- Clear -> Open Bounded Investigation Episode
                      |
                      | 1. Read history & local surveillance
                      | 2. Update 12-cause Bayesian belief distribution
                      | 3. Compute EVSI policy vs Interruption Cost
                      | 4. Execute Action:
                      |    - OBSERVE: Wait for next night
                      |    - ASK: Send targeted inline questionnaire
                      |    - MEASURE: Prompt spot physiological test
                      |    - CONCLUDE: Output grounded differential
```

---

## Command-Line Interface Reference

| Command | Description |
|---|---|
| `wha doctor` | Check database, knowledge tables, and external connectivity |
| `wha ingest` | Pull and normalize raw wearable payloads from configured source |
| `wha nightly` | Execute daily baseline computation, detection, and forecasting |
| `wha demo list` | List available offline scenario replay fixtures |
| `wha demo run <scenario>` | Run end-to-end scenario with deterministic cassette verification |
| `wha belief explain` | Print multi-night marginal cause distributions |
| `wha episode list` | List open and closed investigation episodes |
| `wha episode step <id>` | Advance an episode state machine by one cycle |
| `wha eval <suite>` | Run offline benchmark suites (detection, policy, ablation) |
| `wha serve` | Start Streamlit web interface and APScheduler background thread |
| `wha data fetch <dataset>` | Download external datasets or model weights |
| `wha llm record` | Record LLM interaction fixtures against live provider |

---

## User Interface

The Streamlit dashboard provides transparent inspection into the agent's reasoning:

1. **Today**: Unified inbox for active questionnaires and spot test requests; summary of last night's physiology and active episodes.
2. **History**: Longitudinal Resting Heart Rate charts with adaptive baseline maturity bands and interactive episode spans.
3. **Episode Panel**:
   - *Summary*: Grounded differential, probability ranking, and rule-outs.
   - *Trace*: Chronological pipeline execution log detailing tool calls, EVSI decisions, and latencies.
   - *Conversation*: Interactive probe Q&A with EVSI scores and rejected question rationale.
   - *Evidence*: Retrieved clinical literature passages and stripped claim validation.
4. **Audit**: Complete SHA-256 hash-chain verification tool with JSON/CSV export.
5. **Evaluation**: Offline benchmark metric comparison against heuristic and never-ask baselines.
6. **Settings**: Connection test diagnostics for Bridge, LLM, and Telegram; subject data purge tools.

---

## Identifiability Boundaries & Limitations

- **Signal vs Confounder**: Acute respiratory infection elevates resting HR by 1.1 to 2.1 bpm, whereas acute alcohol consumption or intense training can elevate HR by 2.4 to 6.0 bpm. The system cannot distinguish these on night one without asking.
- **Etiological Granularity**: Wearable sensors observe host autonomic response, not pathogens. The system cannot differentiate Influenza from COVID-19 without symptom reports or rapid antigen test inputs.
- **Early Detection vs Prediction**: WHA detects early physiological deviation after incubation begins. It does not predict future exposure.
- **Baseline Requirement**: Requires 14 to 28 nights of baseline data to reach full sensitivity and transition from cold-start priors to personal shrinkage baselines.

---

## Corpus Layers & Licensing

- **Medical Knowledge Base (`data/knowledge/`)**: Curated tables of effect sizes, likelihood ratios, and clinical red-flag rules compiled from peer-reviewed literature under CC-BY 4.0.
- **Synthetic Scenarios (`tests/fixtures/`)**: Procedurally generated physiological time series modeling canonical clinical courses.
- **Foundation Models**: Optional Chronos-Bolt forecasting weights under Apache 2.0.

---

## Disclaimer

This software is a research prototype designed for personal wellness tracking and educational exploration. It is **not a certified medical device**, does not provide clinical diagnoses, and must not be used as a substitute for professional medical advice or emergency care.
