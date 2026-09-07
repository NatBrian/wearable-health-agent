# Deep Technical Discovery: Commercial & Clinical Wearable Illness Detection Systems & Studies
## Research Track 1

This report provides an in-depth technical analysis of state-of-the-art commercial and clinical wearable illness detection systems and benchmark studies.

---

## System 1: Oura Symptom Radar / Readiness & Temperature Trend Algorithms (TemPredict Study)

### A. Problem Being Solved
Pre-symptomatic and early-stage detection of acute respiratory viral infections (including SARS-CoV-2, influenza, and common cold) and continuous tracking of systemic physiological strain/fever prior to clinical symptom awareness or diagnostic confirmation.

### B. Input Data
* **Sampling Frequency:** Minute-level dermal temperature (sampled every 1–5 minutes continuously or aggregated per 5-minute epochs during sleep); PPG optical sensor sampling pulse waveform at 250 Hz to extract interbeat intervals (IBI); 3D accelerometer at 50 Hz.
* **Duration:** Longitudinal continuous tracking, primarily overnight sleep sessions (typically 6–9 hours per night) accumulated over months/years.
* **Metrics:** Continuous nocturnal dermal temperature, resting heart rate (RHR), root mean square of successive differences (rMSSD for HRV), respiratory rate, total sleep duration, sleep stage durations (Deep, REM, Light, Awake), movement index, METs.

### C. Wearable / Device Used
* **Oura Ring** (Gen 2, Gen 3, and Ring 4; titanium form factor with internal negative temperature coefficient [NTC] thermistors and infrared/red/green optical PPG sensors).

### D. Physiological Signals Used
* **Skin Temperature:** Distal dermal finger temperature (°C relative deviation).
* **Resting Heart Rate (RHR):** Lowest and average nocturnal resting heart rate (bpm).
* **Heart Rate Variability (HRV):** rMSSD (ms).
* **Respiratory Rate (RR):** Nocturnal breaths per minute (derived from PPG pulse wave amplitude and frequency modulations).
* **Sleep Architecture:** Sleep duration, sleep efficiency, latency, restfulness.
* **Activity & Motion:** Daily active/inactive METs, step counts, inactivity alerts.

### E. Data Processing & Artifact Handling
* **Circadian & Environmental Filtering:** Restricting primary illness detection windows to overnight sleep episodes to eliminate daytime ambient thermal fluctuations, solar radiation, metabolic shifts from meals, and physical exertion noise.
* **Baseline Subtraction:** Daily computation of temperature deviation ($\Delta T = T_{night} - T_{baseline}$) and autonomic metric deviations ($\Delta RHR$, $\Delta HRV$).
* **Motion & Artifact Rejection:** Filtering PPG and temperature segments during high accelerometer motion or ring displacement.
* **Circadian Detrending (TemPredict Research):** Cosinor rhythmicity analysis and non-linear least squares sinusoidal fitting across 24-hour cycles to measure circadian phase shifts and amplitude flattening during infection.

### F. Personalization Strategy
* **Baseline Normalization:** Intra-individual rolling baseline computed over 14 to 30 days of healthy/asymptomatic sleep data.
* **Dynamic Distribution Bands:** Calculating intra-subject variance ($\sigma_{baseline}$) where deviations exceeding +0.5°C to +1.0°C or >2 standard deviations flag anomalies.

### G. ML Model or Statistical Method
* **TemPredict Study (Mason et al., 2022; Smarr et al., 2020):** Balanced Random Forest (BRF) classifiers and Elastic Net Logistic Regression trained on multimodal feature vectors (temperature deviation, RHR deviation, HRV delta, respiratory rate, sleep duration).
* **Commercial Oura Symptom Radar / Readiness:** Multidimensional heuristic scoring matrix combined with dynamic rule-based thresholding and anomaly scoring across 40+ biometric strain contributors.

### H. Training Requirement
* **Research (TemPredict):** Supervised model training required on labeled cohorts (PCR-positive vs PCR-negative/healthy baseline).
* **Commercial (Oura Readiness / Symptom Radar):** Rule-based / expert-heuristic system calibrated over population datasets, operating without per-user model training.

### I. Pretrained Models Available
* Model architectures, feature parameters, and decision boundary weights are documented in peer-reviewed publications; commercial binary model weights are proprietary to Oura Health Oy.

### J. LLM Utilization
* **No.** Traditional statistical time-series signal processing and supervised decision forest classifiers.

### K. Agentic Systems Used
* **No.** Deterministic batch evaluation pipeline.

### L. Agent Tools / Actions
* **N/A.**

### M. RAG / Knowledge Retrieval
* **No.** Pure continuous biophysical sensor time-series processing.

### N. User Interaction & Workflow
* **Daily Morning Push Notification:** Upon waking and syncing the ring, the mobile app presents the daily Readiness Score (0–100) and Symptom Radar status ("No signs", "Minor signs", "Major signs").
* **Proactive Interventions:** Prompts users to engage "Rest Mode" (disables activity goals, adjusts recovery baselines) when major biometric deviations occur. In TemPredict, active daily symptom logging surveys were integrated.

### O. Real-Time vs Offline / Batch Operation
* **Batch / Sleep Rollup:** Batch inference executed upon completion of the nocturnal sleep session. (Intraday daytime stress features operate in near real-time 15-minute intervals in Gen 3/4 firmware).

### P. Output Produced
* **Research Model:** Continuous COVID-19 infection probability (0.0 to 1.0) and binary infection alert.
* **Commercial App:** 3-tier categorical status ("No signs", "Minor signs", "Major signs") + continuous 0–100 Readiness Score with itemized contributor flags (Body Temperature, RHR, HRV Balance, Recovery Index).

### Q. Evaluation Methodology
* Prospective multicenter decentralized cohort study (TemPredict, >63,000 enrolled participants); RT-PCR/antigen confirmed COVID-19 diagnoses; antibody serology validation; paired symptom onset tracking.

### R. Reported Performance
* **Sensitivity:** 82% overall sensitivity in identifying COVID-19 onset (90% sensitivity in antibody-confirmed cohorts).
* **Specificity:** 63% (unadjusted overall cohort) to 80% (antibody-confirmed cohort).
* **Lead Time:** Average lead time of 2.75 days (51 ± 12 hours) prior to diagnostic testing or symptom onset.
* **Fever Detection (Smarr et al., 2020):** 76% of COVID-19 cases exhibited significant dermal temperature elevations prior to self-reported fever or symptoms.

### S. Open-Source Availability & Citations
* **Papers:**
 * Mason et al. (2022), *"Detection of COVID-19 using multimodal data from a wearable device: results from the first TemPredict Study"*, *Scientific Reports*, 12, 3463. DOI: `10.1038/s41598-022-07314-0`.
 * Smarr et al. (2020), *"Feasibility of continuous fever monitoring using wearable devices"*, *Scientific Reports*, 10, 21640. DOI: `10.1038/s41598-020-78355-6`.
* **API / Integrations:** Oura Web API v2 (`https://api.ouraring.com/v2/usercollection/daily_readiness`, `temperature_trend`, `sleep`).

### T. Reusable Code / Models / APIs
* Oura Cloud REST API provides programmatic access to 5-minute dermal temperature trends, HRV rMSSD, nocturnal respiratory rate, and sleep architecture vectors.

### U. Major Limitations & Failure Modes
* **Menstrual Cycle Confounding:** The ovulatory luteal phase induces a sustained basal body temperature increase (+0.3°C to +0.5°C) and slight RHR increase, causing periodic false positive strain alerts unless cycle tracking is actively synchronized.
* **Alcohol Ingestion:** Moderate-to-heavy alcohol consumption sharply increases overnight RHR (+5–15 bpm), reduces HRV, and disrupts thermoregulation, perfectly mimicking acute viral prodrome.
* **Ambient Thermal Noise:** Sleeping with heated blankets, cold extremities (Raynaud's), or erratic sleep environments can distort peripheral skin temperature readings.

### V. Architectural Lessons
* **Distal Skin Temperature is the Single Strongest Early Biomarker:** Adding dermal temperature to cardiac metrics boosted infection classification AUC by ~5–8% compared to cardiac-only models.
* **Nighttime Quiescence Isolates Signal:** Restricting illness surveillance to nocturnal sleep eliminates >95% of daytime motion, posture, and metabolic artifacts.

---

## System 2: Stanford Wearable Infection Detection & NightSignal (Mishra et al., 2020; Alavi et al., 2022)

### A. Problem Being Solved
Real-time, pre-symptomatic, and asymptomatic alerting for COVID-19, other acute respiratory infections, and systemic physiological stress events using continuous smartwatch telemetry.

### B. Input Data
* **Sampling Frequency:** Minute-level heart rate (PPG, 1 sample/min or continuous optical sensing); minute-level step counts (accelerometer, 1-min epochs); sleep stage intervals.
* **Duration:** Longitudinal streaming data (weeks to months) collected 24/7.
* **Metrics:** Heart rate (bpm), step count (steps/min), sleep start/stop, nocturnal resting heart rate.

### C. Wearable / Device Used
* **Fitbit** (Charge, Versa, Sense), **Apple Watch** (Series 2 through 8), Garmin devices, Empatica E4.

### D. Physiological Signals Used
* **Resting Heart Rate (RHR):** Isolated during zero-step periods.
* **Heart Rate Over Steps (HROS):** Continuous ratio and regression residual of HR relative to physical movement.
* **Sleep Quiescent Heart Rate:** Median and distribution of nocturnal heart rate.

### E. Data Processing & Artifact Handling
* **Mishra et al. (HROS-AD & RHR-Diff):** Residualization of heart rate against physical activity steps ($HR_{residual} = HR_{observed} - f(Steps)$); hourly median aggregation; removal of movement-corrupted epochs; hourly baseline subtraction.
* **NightSignal (Alavi et al.):** Extraction of nocturnal heart rate exclusively during confirmed sleep/inactive periods (0 steps); computation of rolling hourly median nocturnal HR; debouncing isolated transient single-hour heart rate spikes using a finite-state buffer.

### F. Personalization Strategy
* **Mishra et al.:** 28-day rolling window baseline calculation for each participant, updating mean and standard deviation dynamically.
* **NightSignal:** Streaming median and Median Absolute Deviation (MAD) of nocturnal RHR calculated over an initial 7-day calibration phase, updated dynamically via a rolling 7-to-21 day window.

### G. ML Model or Statistical Method
* **Mishra et al. (2020):**
 * *CUSUM (Cumulative Sum Control Chart):* Statistical change-point detection on hourly RHR-Diff residuals to detect sustained upward shifts.
 * *HROS-AD:* Anomaly detection on heart-rate-to-step regression residuals.
* **NightSignal (Alavi et al., 2022):**
 * *Deterministic Finite State Machine (FSM):* A lightweight 4-state automaton ($S_0$: Baseline/Normal, $S_1$: Warning, $S_2$: Alert/Infection, $S_3$: Recovery). Transitions occur when consecutive nocturnal hourly RHR values exceed baseline thresholds by $k \times MAD$.

### H. Training Requirement
* **No Machine Learning Training Required for NightSignal:** NightSignal is a purely analytical, deterministic statistical finite-state algorithm, making it universally deployable without training labeled neural networks.

### I. Pretrained Models Available
* NightSignal deterministic algorithm and Python/R implementation are fully open-sourced.

### J. LLM Utilization
* **No.**

### K. Agentic Systems Used
* **No.**

### L. Agent Tools / Actions
* **N/A.**

### M. RAG / Knowledge Retrieval
* **No.**

### N. User Interaction & Workflow
* **Mobile App (MyPHD / Vito):** Ingests wearable data in real-time or daily morning sync; presents a 2-color traffic light dashboard:
 * **Green:** Normal physiological baseline.
 * **Red Alert:** Abnormal physiological stress detected (prompts user to self-isolate, take a rapid antigen/PCR test, and log symptom surveys).

### O. Real-Time vs Offline / Batch Operation
* **Hybrid / Streaming Real-Time:** Mishra et al. ran intraday streaming 1-hour CUSUM updates; NightSignal runs daily morning batch rollup immediately following overnight sleep data sync.

### P. Output Produced
* **Binary / Discrete Alert:** Green (Normal) vs Red (Infection / Aberrant Stress Event) + severity magnitude index (deviation in bpm above baseline).

### Q. Evaluation Methodology
* Prospective decentralized clinical cohort (>5,000 participants in MyPHD study; 3,317 participants in NightSignal real-time trial); gold standard RT-PCR nasal swabs, antigen testing, and longitudinal daily symptom surveys.

### R. Reported Performance
* **Sensitivity:** 78% for real-time COVID-19 detection in NightSignal (compared to 54% for standard CuSum and 44% for RHRAD alone); up to 80–81% in symptomatic cohorts.
* **Lead Time:** Detected COVID-19 at or prior to symptom onset in 80% of symptomatic cases, with a median lead time of 3 days (and up to 7 days) prior to symptoms.
* **False Positive Rate / Specificity:** ~0.26 to 0.34 alerts per user-week (roughly 1 false alert every 3–4 weeks). False positives were clinically attributable to non-COVID viral infections, vaccinations, alcohol consumption, high psychological stress, or intense athletic workouts.

### S. Open-Source Availability & Citations
* **Papers:**
 * Mishra et al. (2020), *"Pre-symptomatic detection of COVID-19 from smartwatch data"*, *Nature Biomedical Engineering*, 4, 1208–1220. DOI: `10.1038/s41598-020-00640-6`.
 * Alavi et al. (2022), *"Real-time alerting system for COVID-19 and other stress events using wearable data"*, *Nature Medicine*, 28, 175–184. DOI: `10.1038/s41591-021-01593-2`.
* **GitHub Repository:**
 * Official Stanford Bioinformatics Repo: `https://github.com/StanfordBioinformatics/wearable-infection`

### T. Reusable Code / Models / APIs
* The `StanfordBioinformatics/wearable-infection` repository contains complete Python implementations for NightSignal, CUSUM change-point detection, RHRAD, data parsers for Apple Health and Fitbit export files, and baseline tracking scripts.

### U. Major Limitations & Failure Modes
* **Etiological Non-Specificity:** NightSignal detects *systemic physiological stress* rather than COVID-19 specifically. Influenza, bacterial infections, COVID-19 vaccines, alcohol, travel jetlag, and emotional stress all trigger red alerts.
* **User Compliance (Apple Watch Overnight Wear):** Apple Watch users frequently charge their devices overnight, creating substantial missing data gaps during the critical sleep monitoring window.

### V. Architectural Lessons
* **Deterministic FSMs Match or Outperform Complex ML:** A simple, explainable Finite State Machine operating on nocturnal RHR median deviations outperformed deep learning classifiers while requiring zero model training, zero parameter drift retraining, and executing in <1 millisecond per user.

---

## System 3: Scripps DETECT Study & Algorithm (Quer et al., 2021; Radin et al., 2020; Gadaleta et al., 2021)

### A. Problem Being Solved
Decentralized population-scale and individual-scale early detection of viral illness (influenza-like illness and COVID-19) by fusing passive multi-brand wearable sensor streams with active self-reported symptom questionnaires.

### B. Input Data
* **Sampling Frequency:** Daily aggregate summaries and intraday epoch streams (RHR, daily sleep duration, step counts, continuous intraday HR).
* **Duration:** Longitudinal tracking over months to years across tens of thousands of participants.
* **Metrics:** Daily resting heart rate, daily sleep duration, daily step volume, self-reported symptoms (cough, fever, loss of taste/smell, fatigue, dyspnea).

### C. Wearable / Device Used
* **Cross-Platform Bring-Your-Own-Device (BYOD):** Apple Watch, Fitbit (all models), Garmin, Oura Ring, Withings, Google Fit-compatible devices.

### D. Physiological Signals Used
* **Resting Heart Rate (RHR):** Daily baseline-subtracted RHR ($\Delta RHR$).
* **Sleep Metrics:** Total sleep duration, delta from baseline sleep ($\Delta Sleep$).
* **Physical Activity:** Daily total step count, active minutes, delta steps ($\Delta Steps$).
* **Symptom Vector:** Multi-hot binary symptom indicators.

### E. Data Processing & Artifact Handling
* **Heterogeneous Device Harmonization:** Standardizing data definitions across Apple HealthKit, Fitbit Web API, and Garmin Connect to a unified schema.
* **Feature Engineering (Gadaleta et al., 2021):** Generation of over 300 temporal and statistical features:
 * 1-day, 2-day, 3-day, 7-day rolling baseline deltas ($\Delta RHR_t = RHR_t - \mu_{14-day}$).
 * Difference-of-differences (acceleration of RHR increase).
 * Sleep-to-activity ratios ($\Delta Sleep / \Delta Steps$).
* **Missing Data Imputation:** Forward-filling and linear interpolation for missing daily sensor sync records.

### F. Personalization Strategy
* **Intra-Individual Baseline:** Calculating personalized mean and standard deviation for RHR, sleep, and steps over a 14-day to 30-day healthy baseline window (excluding known sick days).

### G. ML Model or Statistical Method
* **Quer et al. (2021, Nature Medicine):** L1/L2-regularized Logistic Regression and Random Forest comparing models trained on (1) Symptoms only, (2) Sensor data only, and (3) Sensor + Symptoms combined.
* **Gadaleta et al. (2021, NPJ Digital Medicine):** Explainable Gradient Boosted Decision Trees (GBDT / LightGBM / XGBoost) with TreeSHAP (SHapley Additive exPlanations) for local and global feature attribution.
* **Radin et al. (2020, Lancet Digital Health):** Autoregressive state-space and hierarchical time-series models for state-level CDC ILINet surveillance.

### H. Training Requirement
* **Supervised Training Required:** Supervised classification models trained on historical cohorts of PCR-positive vs PCR-negative individuals.

### I. Pretrained Models Available
* The feature engineering pipeline and model architecture are published; trained model binaries are withheld under clinical participant privacy protections.

### J. LLM Utilization
* **No.**

### K. Agentic Systems Used
* **No.**

### L. Agent Tools / Actions
* **N/A.**

### M. RAG / Knowledge Retrieval
* **No.**

### N. User Interaction & Workflow
* **CareEvolution myDataHelps App:** Integrates passive wearable data sync in the background; delivers push notifications prompting users to complete weekly or on-demand symptom surveys; facilitates direct shipment of home nasal swab PCR test kits upon risk threshold activation.

### O. Real-Time vs Offline / Batch Operation
* **Batch Daily Rollup:** Ingests and processes synced sensor summaries once per 24-hour cycle (nightly/morning batch).

### P. Output Produced
* **Continuous Infection Risk Score:** Probability metric ($P_{infection} \in [0.0, 1.0]$) and binary classification (High Risk vs Low Risk).

### Q. Evaluation Methodology
* Prospective decentralized clinical study (DETECT cohort: >38,000 enrolled US participants); laboratory RT-PCR diagnostic test ground truth; validation across symptomatic COVID-positive, symptomatic COVID-negative, and asymptomatic control groups.

### R. Reported Performance
* **Quer et al. (2021):**
 * Combined Sensor + Symptoms Model: **AUC = 0.80** (IQR: 0.73–0.86).
 * Symptoms-Only Model: **AUC = 0.71** (IQR: 0.63–0.79).
 * Sensor-Only Model: **AUC = 0.68–0.72**.
 * Statistically significant improvement ($P < 0.01$) when fusing wearable data with symptoms.
* **Gadaleta et al. (2021):**
 * Fully Passive Sensor-Only GBDT Model: **AUC = 0.78** (0.70 pre-test date) on general cohort; **AUC = 0.83** on symptomatic cohort.
 * Sensitivity ~70–75% at 75–80% specificity.

### S. Open-Source Availability & Citations
* **Papers:**
 * Quer et al. (2021), *"Wearable sensor data and self-reported symptoms for COVID-19 detection"*, *Nature Medicine*, 27, 73–77. DOI: `10.1038/s41591-020-1123-x`.
 * Radin et al. (2020), *"Harnessing wearable device data to improve state-level real-time surveillance of influenza-like illness"*, *The Lancet Digital Health*, 2(2), e85–e93. DOI: `10.1016/S2589-7500(19)30222-5`.
 * Gadaleta et al. (2021), *"Passive detection of COVID-19 with wearable sensors and explainable machine learning algorithms"*, *npj Digital Medicine*, 4, 166. DOI: `10.1038/s41746-021-00533-w`.
* **Platform:** CareEvolution myDataHelps research engine (`https://mydatahelps.org`).

### T. Reusable Code / Models / APIs
* CareEvolution myDataHelps SDK / REST APIs for decentralized clinical sensor aggregation; Gadaleta et al. published complete mathematical formulations of their 300+ feature extraction algorithms in paper supplements.

### U. Major Limitations & Failure Modes
* **High Participant Dropout on Active Surveys:** Daily/weekly active symptom reporting suffered >70% attrition over 6 months, proving that active survey reliance degrades real-world utility.
* **Device Interoperability Discrepancies:** Fitbit vs Apple Watch vs Oura calculate RHR and sleep duration differently, introducing non-trivial cross-device feature distribution shifts.

### V. Architectural Lessons
* **Multimodal Fusion Superiority:** Combining passive physiological telemetry with active sparse symptom reporting creates a synergistic boost (+0.09 AUC), compensating for sensor non-specificity.
* **Explainability via TreeSHAP:** Tree-based GBDTs with SHAP attribution provide interpretable clinical explanations for which physiological feature drove the alert.

---

## System 4: WHOOP COVID-19 / Respiratory Rate Algorithm (Miller et al., 2020; Capodilupo et al.)

### A. Problem Being Solved
Early detection of SARS-CoV-2 infection and lower respiratory tract inflammation by identifying subtle deviations in nocturnal respiratory rate prior to and during early symptom manifestation.

### B. Input Data
* **Sampling Frequency:** Continuous photoplethysmography (PPG) at 25–52 Hz; 3-axis accelerometer at 25 Hz; continuous sampling throughout nocturnal sleep episodes.
* **Duration:** Nightly sleep sessions (accumulated over 14–30+ consecutive days).
* **Metrics:** Interbeat intervals, pulse wave morphology, nocturnal respiratory rate, resting heart rate, HRV (rMSSD), sleep stage architecture.

### C. Wearable / Device Used
* **WHOOP Strap** (WHOOP 3.0 and WHOOP 4.0; screenless, wrist/bicep-worn continuous physiological monitor).

### D. Physiological Signals Used
* **Nocturnal Respiratory Rate (RR):** Extracted in breaths per minute (bpm/rpm).
* **Resting Heart Rate (RHR):** Minimum and average nocturnal heart rate.
* **Heart Rate Variability (HRV):** Nocturnal rMSSD during Slow-Wave Sleep.
* **Sleep Architecture:** Duration of Slow-Wave Sleep (SWS), REM sleep, sleep disturbances.

### E. Data Processing & Artifact Handling
* **Slow-Wave Sleep (SWS) Isolation:** Extracting respiratory metrics specifically during SWS (deep sleep) where autonomic control is stable.
* **Respiratory Sinus Arrhythmia (RSA) Derivation:** Computing respiratory rate from PPG-derived RSA using frequency-domain peak detection and time-domain peak-to-trough modulation.
* **Nightly Median Rollup:** Filtering out movement-corrupted epochs and computing a single, stable median breaths-per-minute value for the sleep episode.

### F. Personalization Strategy
* **Intra-Individual Baseline:** Respiratory rate varies by <0.5–1.0 breaths/min in health. Baseline is computed over a rolling 21-to-30 day window.
* **Personalized Normal Range:** Establishing standard deviation bands ($\pm 1.0$ to $\pm 1.5$ standard deviations) around the user's historical median.

### G. ML Model or Statistical Method
* Statistical process control and multivariable logistic regression on intra-individual standardized z-scores of nocturnal respiratory rate ($\Delta RR = (RR_{night} - \mu_{baseline}) / \sigma_{baseline}$), RHR, and HRV.

### H. Training Requirement
* **No Continuous User Training Required:** Algorithm relies on personal statistical baseline tracking.

### I. Pretrained Models Available
* Proprietary to WHOOP, Inc.

### J. LLM Utilization
* **No.**

### K. Agentic Systems Used
* **No.**

### N. User Interaction & Workflow
* **Morning Health Monitor Push Notification:** In the WHOOP app, users view their morning Recovery Score (0–100%) and the **Health Monitor** dashboard (Green, Yellow, Red).

### O. Real-Time vs Offline / Batch Operation
* **Batch / Sleep Rollup:** Calculated immediately upon the conclusion of each sleep session.

### P. Output Produced
* Breaths per minute (rpm), deviation from baseline ($\Delta rpm$), and 3-state indicator (Green, Yellow, Red).

### Q. Evaluation Methodology
* Observational clinical cohort of 271 symptomatic WHOOP users with verified diagnostic laboratory COVID-19 PCR/antigen test ground truth.

### R. Reported Performance
* **Pre-symptomatic Sensitivity:** 20% in the 2 days *prior* to symptom onset.
* **Post-symptom Sensitivity:** 80% by day 3 *after* symptom onset.
* **Specificity:** High specificity (>90%) for distinguishing COVID-19 lower respiratory infection from common non-respiratory strains when respiratory rate surge was present.
* **Biomarker Delta:** Average nocturnal respiratory rate increase of **+1.5 to +2.5 breaths/minute** above baseline in COVID-19 cases.

### S. Open-Source Availability & Citations
* **Paper:** Miller et al. (2020), *"Analyzing changes in respiratory rate to predict the risk of COVID-19 infection"*, *PLOS ONE*, 15(12), e0243694. DOI: `10.1371/journal.pone.0243694`.
* **Developer Portal:** WHOOP Developer API (`https://developer.whoop.com/api`).

### U. Major Limitations & Failure Modes
* **Lagging Prodromal Indicator:** Respiratory rate surges predominantly when lower airway inflammation develops, lagging behind autonomic (HRV) or thermal deviations.
* **Confounders:** Altitude changes, high bedroom humidity/temperature, asthma, and alcohol.

### V. Architectural Lessons
* **Nocturnal Respiratory Rate is the Most Stable Biophysical Baseline:** Unlike RHR and HRV, nocturnal respiratory rate during Slow-Wave Sleep has near-zero baseline variance in healthy states, making even slight deviations (+1.0 rpm) highly specific indicators of lower respiratory pulmonary strain.

---

## System 5: CovIdentify (Duke University) & Behavioral Foundation Models (Dunn et al.; Merrill & Althoff)

### A. Problem Being Solved
Multi-device digital biomarker discovery, decentralized public health infection surveillance, Intelligent Testing Allocation (ITA), and foundation model transfer learning for cross-pathogen respiratory illness detection.

### B. Input Data
* Minute-level and daily aggregate sensor data (optical PPG HR, accelerometer step count, SpO2, sleep staging).

### C. Wearable / Device Used
* Apple Watch, Fitbit, Garmin, Withings, Empatica, Samsung Galaxy Watch.

### D. Physiological Signals Used
* Resting heart rate, continuous intraday heart rate, step count epochs, sleep stage durations, SpO2, survey responses.

### E. Data Processing & Artifact Handling
* **Cross-Device Feature Harmonization:** Standardizing vendor-specific metrics into normalized canonical representations.
* **Circadian Rhythm Modeling:** 24-hour Cosinor regression and Fourier harmonic parameterization of locomotor activity.
* **Tokenization & Masking:** Discretizing continuous multimodal time-series streams into behavioral and physiological tokens with masked autoencoding.

### F. Personalization Strategy
* Intra-individual rolling baseline subtraction ($\Delta x = (x_t - \mu_{t-28}) / \sigma_{t-28}$) and self-supervised transfer learning.

### G. ML Model or Statistical Method
* Supervised ensemble classifiers (Random Forest, XGBoost, SVM) + Self-Supervised Masked Autoencoders & Contrastive Transformers (SimCLR/CPC style).

### H. Training Requirement
* **Yes:** Requires self-supervised pretraining and supervised fine-tuning.

### I. Pretrained Models Available
* Homekit2020 benchmark codebase and self-supervised pretrained encoder weights are publicly hosted on GitHub / Hugging Face.

### J. LLM Utilization
* Adapts LLM-style Transformer architectures, tokenizers, and self-supervised masked pretraining objectives directly to time-series wearable behavioral data.

### K. Agentic Systems Used
* **No.**

### Q. Evaluation Methodology
* CovIdentify (>6,700 participants); Apple Heart & Movement Study (>160,000 participants); Homekit2020 public benchmark (>3,000 participants with RT-PCR ground truth).

### R. Reported Performance
* Self-supervised pretraining boosted classification **AUROC from 0.65–0.70 to 0.78–0.84** on small sample-size infection cohorts.
* Homekit2020 Benchmark: Transformer/CNN models achieved AUROC of **0.75–0.82** for lab-confirmed acute influenza/COVID detection using minute-level Fitbit sensor streams.

### S. Open-Source Availability & Citations
* **Papers:**
 * Dunn et al. (2021), *Cell Systems / Lancet Digital Health*.
 * Merrill et al. (2023), *NeurIPS / Nature Communications*, arXiv: `2306.09540`.
 * Merrill & Althoff (2023), *JMIR / arXiv:2210.02476*.
 * Merrill et al. (2025/2026), *ICML / arXiv:2501.18567*.
* **GitHub Repos:**
 * `https://github.com/behavioral-data/self-supervised-wearables`
 * `https://github.com/behavioral-data/homekit2020`

### V. Architectural Lessons
* **Self-Supervised Pretraining Solves the Small Clinical Data Bottleneck:** Pretraining masked autoencoders on unlabeled data and fine-tuning on labeled cohorts yields the highest generalizable accuracy.

---

## Master Comparison Matrix

| System / Study | Wearable Devices | Primary Biometrics | Algorithmic Core | Personalization Strategy | Sensitivity | Specificity | Lead Time Before Symptoms | Code / API Availability |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Oura Symptom Radar / TemPredict** | Oura Ring (Gen 2/3/4) | Skin Temp, RHR, HRV (rMSSD), RR, Sleep Stages | Balanced Random Forest & Heuristic Strain Matrix | 14–30 day rolling baseline; $\Delta T, \Delta RHR$ | 82% (90% in antibody cohort) | 63%–80% | 2.75 days (51 ± 12 hrs) | Oura Cloud API v2; Paper equations |
| **Stanford NightSignal** | Apple Watch, Fitbit, Garmin | Nocturnal RHR, Inactive HR, Step counts | Deterministic Finite State Machine (FSM) + Streaming Median | 7–21 day rolling median & MAD baseline | 78% | ~0.3 false alerts / week | 3.0 days (up to 7 days) | **Fully Open Source** (`StanfordBioinformatics/wearable-infection`) |
| **Scripps DETECT** | Apple Watch, Fitbit, Garmin, Oura | RHR, Sleep Duration, Step Count, Symptoms | GBDT (LightGBM/XGBoost) + TreeSHAP + Elastic Net | 14–30 day healthy baseline deltas | 70%–75% (0.80 AUC combined) | 75%–80% | 1–3 days | CareEvolution myDataHelps API; Feature formulation published |
| **WHOOP COVID / Resp Rate** | WHOOP 3.0 / 4.0 | Nocturnal RR (via RSA), RHR, HRV (SWS-gated) | Statistical Process Control & Logistic Regression on z-scores | 21-day intra-individual baseline distribution | 20% pre-symptom; 80% by Day 3 symptoms | >90% (for lower respiratory strain) | 0–2 days pre-symptoms | WHOOP Developer REST API; PLOS ONE paper |
| **Duke CovIdentify / Foundation Models** | Multi-brand (Apple, Fitbit, Garmin) | RHR, HRV, SpO2, Steps, Circadian Locomotor Tokens | Self-Supervised Transformers, 1D-CNNs, ITA Bayesian Models | Contrastive pretraining + intra-subject z-scores | 78%–84% AUROC | High (optimized by ITA) | 2–3 days | **Open Source** (`behavioral-data/self-supervised-wearables`, PhysioNet dataset) |
