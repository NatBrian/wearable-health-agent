# Deep Technical Discovery: Wearable Ecosystem APIs, Data Latency, and Medical RAG Grounding & Safety
## Research Track 4

---

## Executive Summary & Engineering Feasibility Matrix

| Platform / Area | Access Tier & Gatekeeping | Granularity (RHR, HRV, SpO2, Temp) | Latency & Delivery Model | Best Integration Path for AI/ML |
| :--- | :--- | :--- | :--- | :--- |
| **Apple Health / HealthKit** | Open on-device (iOS App); No native cloud REST API | Daily RHR, Intermittent HR (1-10 min), SDNN HRV (periodic), Spot SpO2, Nocturnal wrist temp deviation | Batch/Opportunistic (iOS power managed, background wake); No native real-time streaming | Native Swift background worker (`HKAnchoredObjectQuery`) or **Health Auto Export** REST Bridge |
| **Fitbit / Google Health API** | Legacy Fitbit API deprecated Sept 2026; Migrating to Google Health API & Health Connect | 1-sec/1-min Intraday HR, daily/5-min HRV (RMSSD), SpO2, skin temp deviation | Cloud Webhook notifications (Ping/Pull), on-device Health Connect reads | Health Connect SDK on Android + Google Health Cloud API |
| **Garmin Health API** | Enterprise B2B only (Vetted, NDA, fee/volume minimums) | 1-min RHR/HR, Epoch stress, Pulse Ox, Respiration | Cloud Push Webhooks (post-BLE sync); Live BLE via Companion SDK | Aggregator (Terra/Vital) for dev; Companion SDK for live streaming |
| **Oura Ring API v2** | Self-serve (Instant Personal Access Token / OAuth 2.0) | 5-min HR, 5-min sleep HRV (RMSSD), SpO2, Nightly temperature deviation | Push Webhooks (~30s post-mobile sync); 5,000 req / 5 min limit | **Oura Cloud API v2** (`/usercollection/`) + Webhooks |
| **Medical RAG & Safety** | Open Access (NCBI StatPearls, PubMed OA, CDC, WHO) | Peer-reviewed prodromes, viral trajectories & confounders | Sub-second inference with structured JSON guardrails | **Instructor (Pydantic)** + **Deterministic Triage** + **Llama Guard 3** |

---

# PART 1: Commercial Wearable APIs & Data Access

## 1. Apple Health / HealthKit

### Data Export & Access Methods
Apple does not provide a direct cloud REST API for HealthKit. All HealthKit data resides in the local on-device SQLite encrypted store. Access requires one of three architectures:

1. **Native iOS App with Background Delivery:**
 - **Mechanism:** Register an `HKObserverQuery` and call `healthStore.enableBackgroundDelivery(for: sampleType, frequency: .immediate)`.
 - When new samples are written by Apple Watch, iOS wakes the app in the background for a brief execution window (~10–30 seconds).
 - The app must execute an `HKAnchoredObjectQuery` to fetch incremental delta records using an anchor token and POST them to your backend ingestion endpoint.
 - **Documentation:** [Apple HealthKit Framework](https://developer.apple.com/documentation/healthkit), [Enabling Background Delivery](https://developer.apple.com/documentation/healthkit/hkhealthstore/1614175-enablebackgrounddelivery)

2. **Apple Health Export XML (`export.xml`):**
 - Manual user-triggered export generates an uncompressed ZIP containing `export.xml` and `export_cda.xml` (often 500MB–2GB+).
 - **Schema:**
 ```xml
 <Record type="HKQuantityTypeIdentifierHeartRate"
 sourceName="Apple Watch"
 unit="count/min"
 creationDate="2026-08-28 08:15:00 +0800"
 startDate="2026-08-28 08:14:00 +0800"
 endDate="2026-08-28 08:15:00 +0800"
 value="72"/>
 ```
 - **Engineering Note:** Monolithic XML parsing requires streaming parsers (e.g., Python `lxml.etree.iterparse` or SAX) to prevent out-of-memory crashes.

3. **Auto Export Apps (Bridge Layer):**
 - Third-party apps like **Health Auto Export** ([Health Auto Export](https://www.healthyapp.dev/)) run as background agents on iOS, querying HealthKit and streaming formatted JSON payloads directly to a custom REST API, MQTT broker, or Home Assistant.

### Metric Granularity & Identifiers
* **Resting Heart Rate (`HKQuantityTypeIdentifierRestingHeartRate`):** Discrete daily summary computed by Apple's proprietary algorithm during rest/sleep. Typically 1 sample per day.
* **Intraday Heart Rate (`HKQuantityTypeIdentifierHeartRate`):** Intermittent background readings (every 1–10 minutes depending on motion) or continuous 1-second samples during active workout sessions.
* **Heart Rate Variability (`HKQuantityTypeIdentifierHeartRateVariabilitySDNN`):** Apple calculates **SDNN** in milliseconds from periodic optical readings or Breathe/Mindfulness sessions. **Limitation:** Apple does *not* log continuous 1-minute RMSSD natively unless calculated from raw `HKQuantityTypeIdentifierBeatToBeatCorrelation` (where accessible) or during active workouts.
* **Oxygen Saturation (`HKQuantityTypeIdentifierOxygenSaturation`):** Spot checks throughout the day and periodic nocturnal measurements (values represented as percentage fractions `0.0`–`1.0`). *Note: US-sold Series 9/Ultra 2 models after Jan 2024 have hardware SpO2 disabled due to patent disputes.*
* **Wrist Temperature (`HKQuantityTypeIdentifierAppleSleepingWristTemperature`):** Available on Series 8/9/Ultra. Samples sensor readings every 5 seconds during sleep, aggregated into a **relative temperature deviation (°C)** against the user's established 5-night baseline. Read-only.

### Streaming Latency & Real-Time Limitations
* **No True Real-Time Streaming:** HealthKit background delivery is **opportunistic**. iOS throttles background wakes under Low Power Mode, battery below 20%, or if the user force-quits the host app.
* **Latency:** Background delivery latency ranges from **15 minutes to several hours** during standard wear.
* **Real-time Exception:** True 1Hz streaming is only supported on watchOS with an active `HKWorkoutSession` / `HKLiveWorkoutBuilder` running in the foreground.

---

## 2. Google Health Connect & Fitbit Web API

### Ecosystem Migration Notice
* **Fitbit Web API Sunset:** The legacy Fitbit Web API is being **decommissioned in September 2026**.
* **Successor Architecture:** Google is transitioning server-to-server cloud sync to the **Google Health API** (Cloud REST/gRPC via Google Cloud Console) while using **Google Health Connect** as the Android on-device repository.

### Data Types & Intraday Permissions
* **Health Connect (Android SDK):**
 - `HeartRateRecord` (Series of timestamps + BPM)
 - `RestingHeartRateRecord`
 - `HeartRateVariabilityRmssdRecord` (RMSSD in ms)
 - `SkinTemperatureRecord` (Delta baseline or absolute values)
 - `OxygenSaturationRecord`
 - `RespiratoryRateRecord`
 - **Background Access Requirement:** Requires `android.permission.health.READ_HEALTH_DATA_IN_BACKGROUND` in `AndroidManifest.xml` and explicit user runtime authorization (Android 14+).
 - **Doc URL:** [Google Health Connect Guides](https://developer.android.com/health-and-fitness/guides/health-connect)

* **Legacy Fitbit Web API & Intraday Access:**
 - **Intraday Permission:** Access to 1-second or 1-minute granular heart rate / steps (`/1/user/-/activities/heart/date/today/1d/1min.json`) is restricted.
 - **Personal Apps:** Granted automatic intraday access for the developer's *own* account only.
 - **Third-Party/Multi-User Apps:** Requires submitting a formal Intraday Access Request form to Fitbit/Google. Without approval, multi-user requests return `403 Forbidden`.
 - **Doc URL:** [Fitbit Web API Documentation](https://dev.fitbit.com/build/reference/web-api/)

### Rate Limits, Webhooks & Sync Latency
* **Fitbit Rate Limits:** 150 requests per hour per user access token (tracked via headers `fitbit-rate-limit-limit`, `fitbit-rate-limit-remaining`, `fitbit-rate-limit-reset`).
* **Webhook Subscriptions:** Fitbit Subscription API sends lightweight notifications (`collectionType: "activities"`, `"sleep"`, `"body"`) via HTTP POST when a device syncs. The server must then execute a `GET` request to pull the updated records (Ping/Pull architecture).
* **Sync Latency:** Real-world latency is tied to Bluetooth synchronization between the tracker and the mobile app (typically hourly or when the user opens the Fitbit/Google app).

---

## 3. Garmin Health API

### Access Requirements & Gatekeeping
* **Enterprise/B2B Model:** Garmin Connect Developer Program is **not self-serve** for individual developers or hobbyists.
* **Requirements:** Requires a registered legal entity, commercial business proposal, published privacy policy, NDA, and formal enterprise contract approval. Minimum annual device volume or licensing fees may apply.
* **Doc URL:** [Garmin Health Enterprise Solutions](https://developer.garmin.com/garmin-health/overview/)

### Architecture: Cloud Push vs. Real-Time Companion SDK
* **Cloud Health API (Push Architecture):**
 - Garmin Connect server automatically pushes JSON data packages via HTTP POST to the developer's registered webhook endpoints whenever a user syncs their Garmin device.
 - Payload endpoints: Dailies, Epochs (15-min or 1-min summaries), Sleep, Stress, Pulse Ox, Respiration.
* **Real-Time Streaming via Companion SDK:**
 - If sub-second real-time streaming is required, Garmin provides the **Garmin Health Companion SDK** (Android & iOS).
 - Enables the host mobile app to establish a direct Bluetooth Low Energy (BLE) connection to the Garmin wearable, streaming live Heart Rate, Inter-Beat Intervals (IBI), Accelerometry, and Live Stress without routing through Garmin Cloud. (Requires specific enterprise licensing).

---

## 4. Oura Gen3 API v2

### Endpoints Overview
Base URL: `https://api.ouraring.com/v2/usercollection/`

| Resource Endpoint | Key Fields & Metrics | Granularity / Frequency |
| :--- | :--- | :--- |
| `GET /daily_sleep` | `score`, `contributors` (deep, rem, efficiency) | 1 summary per day |
| `GET /daily_readiness` | `score`, `temperature_deviation`, `temperature_trend_deviation` | 1 summary per day |
| `GET /heartrate` | `bpm`, `source` (`awake`, `rest`, `sleep`, `session`) | 5-minute time-series intervals |
| `GET /daily_spo2` | `spo2_percentage` (average), `breathing_disturbance_index` | 1 summary per day |
| `GET /sleep` | `hrv.items` (RMSSD in ms), `heart_rate.items`, `readiness_score_delta` | 5-minute epoch arrays across sleep |
| `GET /daily_stress` | `stress_high`, `recovery_high`, `day_summary` | Daily aggregated durations (seconds) |
| `GET /daily_resilience` | `level` (`exceptional`, `strong`, `solid`, `adequate`, `limited`) | Daily state calculation |

### Developer Access, Rate Limits & Webhooks
* **Access Ease:** Extremely developer-friendly. Instant generation of **Personal Access Tokens (PAT)** via the [Oura Cloud Portal](https://cloud.ouraring.com/personal-access-tokens) for immediate prototyping. OAuth 2.0 supported for production multi-tenant apps.
* **Rate Limits:** **5,000 requests per 5 minutes** per access token (returns HTTP `429 Too Many Requests` on breach).
* **Webhooks:** Oura supports webhook subscriptions for data types (`daily_sleep`, `daily_readiness`, `sleep`, `workout`, `session`). Webhook notifications fire approximately **30 seconds** after the user opens the Oura app and syncs ring data to Oura Cloud.
* **Doc URL:** [Oura API v2 Documentation](https://cloud.ouraring.com/v2/docs)

---

## 5. Simulated Streaming & Replay Architectures for Live Demos

Given hardware sync latencies (minutes to hours), a live demo requires a dedicated **Simulation / Replay Engine**:

```
 ┌─────────────────────────────────────────────────────────────────────────┐
 │ Physiological Data Engine │
 │ │
 │ ┌───────────────────────┐ ┌─────────────────────────┐ │
 │ │ Open Source Dataset │ │ Synthetic Generator │ │
 │ │ (Mishra/TemPredict) │ │ (Circadian + Prodrome) │ │
 │ └───────────┬───────────┘ └────────────┬────────────┘ │
 └──────────────┼──────────────────────────────────────────┼───────────────┘
 │ │
 ▼ ▼
 ┌─────────────────────────────────────────────────────────────────────────┐
 │ FastAPI / Python Time-Warp Replay Server │
 │ │
 │ • Configurable speed multiplier (1x, 60x, 300x) │
 │ • Confounder injection toggles (Alcohol, Overtraining, Luteal Phase) │
 │ • Emits standardized JSON via WebSockets / Server-Sent Events (SSE) │
 └────────────────────────────────────┬────────────────────────────────────┘
 │
 ▼
 ┌─────────────────────────────────────────────────────────────────────────┐
 │ Downstream ML / RAG Pipeline │
 └─────────────────────────────────────────────────────────────────────────┘
```

### 1. Open Source Dataset Replay Sources
* **Stanford COVID-19 Wearable Dataset (Mishra et al. / Snyder Lab):** Contains longitudinal 1-minute Fitbit and Apple Watch time-series (RHR, steps) across pre-symptomatic, symptomatic, and recovery infection phases. Available on [Stanford Digital Repository](https://purl.stanford.edu/bx987vn9177) and [Nature Biomedical Engineering](https://doi.org/10.1038/s41551-020-00640-6).
* **TemPredict UCSF/Oura Dataset (Smarr et al.):** High-resolution dermal temperature deviations, nocturnal RHR, and HRV curves capturing viral incubation. Published in [Scientific Reports](https://doi.org/10.1038/s41598-020-78652-0).
* **WESAD / PhysioNet PPG-DaLiA:** Multi-modal wearable datasets on [PhysioNet](https://physionet.org/) providing raw continuous PPG, HR, EDA, and motion data.

### 2. Mathematical Prodrome & Confounder Generator
A lightweight script can generate circadian sinusoidal baselines and simulate physiological perturbations:
* **Baseline Model:** $RHR(t) = RHR_{base} + A \cdot \sin\left(\frac{2\pi(t - \phi)}{24}\right) + \epsilon$
* **Infection Prodrome Ramp (Day -3 to Day 0):**
 - Nocturnal RHR: $+8$ to $+15\text{ bpm}$ above rolling 14-day median.
 - HRV (RMSSD): Suppressed by $35\%\text{--}50\%$.
 - Skin Temp Deviation: Ramps $+0.8^\circ\text{C}$ to $+1.8^\circ\text{C}$.
 - Respiratory Rate: Increases $+2$ to $+4\text{ breaths/min}$.
* **Confounder Injections (To test RAG differential diagnosis):**
 - *Alcohol:* Overnight RHR spike (+10 bpm), deep HRV crash (-60%), but normal body temperature and immediate recovery within 24–48 hours.
 - *Luteal Phase:* Steady $+0.3^\circ\text{C}$ to $+0.5^\circ\text{C}$ basal body temperature elevation and slight RHR increase sustained cyclically for 10–14 days.
 - *Overtraining:* Elevated sleeping HR with high HRV variability, without thermal deviation.

---

# PART 2: Medical RAG, Clinical Grounding & Safety Guardrails

## 1. Open Clinical Guideline Sources

| Source | Domain / Coverage | API / Access Method | License & Accessibility |
| :--- | :--- | :--- | :--- |
| **StatPearls (NCBI Bookshelf)** | Comprehensive clinical reviews, prodromal timelines, differential diagnosis, fever etiology | NCBI E-utilities API: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=books` | Open Access / CC BY-NC-ND on [NCBI Bookshelf](https://www.ncbi.nlm.nih.gov/books/) |
| **PubMed Central (PMC) OA Subset** | Peer-reviewed wearable biomarker studies, infection detection algorithms, confounder dynamics | NCBI Entrez Direct API & AWS S3 Bucket: `s3://pmc-oa-opendata/` | Open Access / Creative Commons |
| **CDC Clinical Guidelines** | Respiratory viral guidelines (Influenza, COVID-19, RSV), incubation periods, triage red flags | CDC Open Data API (Socrata): `https://data.cdc.gov/` and [CDC Public Health API](https://www.cdc.gov/) | US Public Domain |
| **WHO Guidelines (IRIS)** | Global infection management protocols, clinical triage algorithms, pediatric/adult fever management | WHO GHO OData API: `https://ghoapi.azureedge.net/api/` & [WHO IRIS](https://iris.who.int/) | Open Access (WHO Open Use) |
| **NIH MedlinePlus XML** | Patient-facing symptoms, disease descriptions, drug-biomarker interactions | MedlinePlus XML Web Service: `https://medlineplus.gov/xml.html` | Free Public Access (US NLM) |

---

## 2. Preventing Hallucinations & Clinical Grounding

Top medical AI architectures (e.g., Med-PaLM 2, AMIE, Google Health AI) employ strict **Grounded Generation** and **Regulatory Boundaries**:

### 1. Corrective RAG (CRAG) & Claim Attribution
- **Context Injection:** Ingest only chunked, versioned guideline paragraphs tagged with unique `SourceID` (e.g., `[CDC-FLU-2025-P4]`, `[STATPEARLS-NBK430685]`).
- **Chain-of-Verification (CoVe):** A post-generation verification step parses every sentence from the draft response and executes natural language inference (NLI) against retrieved chunks. If an assertion is not strictly entailed, it is excised.

### 2. FDA SaMD vs. Non-Device CDS Compliance
- Under FDA guidelines for *Clinical Decision Support (CDS)* and *General Wellness*:
 - **Prohibited:** Generating affirmative medical diagnoses (e.g., *"You have Influenza A"*), prescribing dosages, or commanding medical actions.
 - **Permitted:** Presenting physiological data deviations compared to historical baselines, summarizing published medical literature correlates, and prompting user self-reflection.
 - **Language Formulation:** Output must use non-prescriptive, correlational language:
 > *"Your wearable logged a nocturnal resting heart rate elevation of +11 bpm above your 14-day baseline, alongside a 1.2°C temperature elevation. According to CDC and StatPearls clinical literature, this biomarker pattern is commonly observed during immune activation/viral prodromes, but can also be influenced by acute confounders (alcohol, intense physical exertion, or cycle phase). Consult a healthcare professional if symptoms develop."*

### 3. Hardcoded Emergency Red-Flag Triage
Before any LLM call, a deterministic rule-based classifier scans the user query and physiological inputs for critical emergency red flags:
- *Red Flags:* Sepsis indicators, resting HR > 140 bpm, SpO2 < 90%, chest pain, severe dyspnea, acute neurological deficits.
- *Action:* Bypasses the RAG pipeline entirely and renders an immediate, unalterable Emergency Medical Disclaimer directing the user to 911 / nearest emergency department.

---

## 3. Safety Guardrail Frameworks for a 2-Week Implementation

For rapid 2-week execution, deploy a modular 4-tier guardrail pipeline:

```
 User Prompt & Wearable Metrics
 │
 ▼
 ┌────────────────────────────────────────────────────────┐
 │ Layer 1: Deterministic Red-Flag Interceptor │ --> Immediate Emergency Triage Alert
 │ (Regex / Keyword Triage: Chest Pain, SpO2 < 90, Sepsis)│ (Bypasses LLM)
 └─────────────────────────────┬──────────────────────────┘
 │ (Pass)
 ▼
 ┌────────────────────────────────────────────────────────┐
 │ Layer 2: Fast Safety Classifier (Llama Guard 3 / 8B) │ --> Block jailbreaks, unapproved advice,
 │ Categorizes input against medical harm taxonomy │ or off-topic queries
 └─────────────────────────────┬──────────────────────────┘
 │ (Safe)
 ▼
 ┌────────────────────────────────────────────────────────┐
 │ Layer 3: Vector RAG Retrieval (BM25 + Semantic) │
 │ Chunks from StatPearls + CDC Respiratory Protocols │
 └─────────────────────────────┬──────────────────────────┘
 │
 ▼
 ┌────────────────────────────────────────────────────────┐
 │ Layer 4: Instructor + Pydantic Schema Enforcement │ --> Strict JSON structure:
 │ Guarantees structured output, citations & disclaimers │ • Baseline deltas
 └─────────────────────────────┬──────────────────────────┘ • Confounders evaluated
 │ • Verified source citations
 ▼ • Educational disclaimer
 Validated Output
```

### Python Schema Enforcement Pattern with `Instructor`
```python
from pydantic import BaseModel, Field
from typing import List
import instructor
from openai import OpenAI

class ClinicalCitation(BaseModel):
 source_id: str = Field(description="Exact ID of the cited clinical guideline (e.g. STATPEARLS-NBK430685)")
 verbatim_quote: str = Field(description="Direct snippet from the retrieved source supporting the statement")

class WearableInsightResponse(BaseModel):
 physiological_summary: str = Field(description="Summary of baseline vs current anomaly metrics")
 identified_pattern: str = Field(description="Non-diagnostic physiological pattern description")
 potential_confounders: List[str] = Field(description="Lifestyle or environmental confounders (alcohol, exertion, cycle)")
 clinical_correlates: List[str] = Field(description="Educational explanations grounded in retrieved literature")
 citations: List[ClinicalCitation] = Field(description="Mandatory list of clinical citations")
 confidence_score: float = Field(ge=0.0, le=1.0, description="Model grounding confidence")
 triage_guidance: str = Field(description="Non-prescriptive wellness advice and symptom monitoring guidance")
 mandatory_disclaimer: str = Field(
 default="This information is for educational purposes based on wearable trends and is not a medical diagnosis.",
 description="Static legal/clinical disclaimer"
 )
```

---

## 4. Key Recommendations for 2-Week Sprint Execution
1. **Wearable Data:** Use **Oura API v2** (instant PAT) for cloud data access and write an **SSE/WebSocket Replay Server** playing back the Stanford Snyder COVID-19 dataset for real-time live demonstrations.
2. **Clinical Knowledge Base:** Ingest the **NCBI StatPearls Bookshelf** (respiratory prodromes, infectious diseases) + **CDC Clinical Guidelines** into a ChromaDB / Qdrant vector store.
3. **Guardrails:** Implement **Instructor (Pydantic)** for JSON schema enforcement + **Regex Red-Flag Triage**, ensuring 100% compliance with non-diagnostic CDS principles.
