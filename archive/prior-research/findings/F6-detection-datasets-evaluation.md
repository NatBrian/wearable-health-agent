# F6: Detection Methods, Open Datasets, and Evaluation Methodology

Research date: 2026-08-30
Scope: (1) anomaly and change-point detection for personalised physiological time series,
(2) every open dataset that could support an agentic wearable early-warning project,
(3) evaluation methodology that survives a hostile reviewer.

Every factual claim carries a URL. Claims I could not confirm against a primary source are
marked **UNVERIFIED**. Where I downloaded and inspected a dataset myself, that is stated
explicitly as **first-hand**.

---

## 1. Executive summary

### 1.1 Answers to the five questions, up front

**Q1. Does any public dataset contain both illness labels AND confounder annotations?**

**Not in a single freely-downloadable file. Yes, but only behind institutional gating.**

- **No open-download dataset has both.** Every dataset you can `curl` today falls into one of
 two camps. Camp A has illness labels and essentially no lifestyle confounders (Stanford
 COVID-19-Wearables, Homekit2020, CovIdentify). Camp B has rich confounders and no illness
 labels (PMData, TILES-2018, LifeSnaps, MMASH).
- **The one genuine "both" resource is the All of Us Research Program Controlled Tier**, which
 co-locates minute-level Fitbit heart rate and steps (`heart_rate_minute_level`,
 `steps_intraday` BigQuery tables) with Electronic Health Records, physical measurements and
 lifestyle surveys for the same participants
 ([All of Us Fitbit resources](https://support.researchallofus.org/hc/en-us/articles/20281023493908-Resources-for-Using-Fitbit-Data),
 [Controlled CDR directory](https://support.researchallofus.org/hc/en-us/articles/4616869437204)).
 It contains Fitbit data from more than 59,000 participants spanning 14 years, with more than
 39 million step observations and 31 million sleep observations, and 46% of Fitbit contributors
 also have EHR, physical measurements, genomics and survey data
 ([Nature Medicine 2026, PMC13278962](https://pmc.ncbi.nlm.nih.gov/articles/PMC13278962/)).
 Access requires an institutional agreement and work inside the Researcher Workbench; data
 cannot be bulk-exported. Realistic lead time for a course project: too long.
- **The closest partial match you can actually get is CovIdentify**
 ([PhysioNet](https://physionet.org/content/covidentify/1.0.0/)): 132 self-reported COVID-positive
 and 1,157 negative participants, daily symptom surveys, plus **vaccination annotations**
 (date, brand, dose, related symptoms) and social-distancing behaviour. It has *some* confounder
 annotation but not alcohol, menstrual cycle, medication or exercise intensity. It needs a
 PhysioNet credentialed account, a signed DUA and CITI "Data or Specimens Only Research" training.
- **Practical consequence for this project:** you will have to *pair* datasets rather than find
 one. The defensible design is to estimate detection sensitivity and lead time on an
 illness-labelled set (Stanford COVID-19-Wearables, which is a single unauthenticated download),
 and estimate the false-alarm rate and confounder attribution on a confounder-rich unlabelled set
 (PMData, which records daily alcohol consumption, meals, training load, mood, stress and sleep
 quality for 16 people over 5 months, CC BY 4.0, 1.4 GB). Section 7 explains how to make that
 pairing defensible rather than a fudge.

**Q2. Strongest evidence-backed simple baseline detector, implementable in under 100 lines?**

**Resting-heart-rate anomaly detection (RHR-AD) as published by the Snyder lab, in its offline
Gaussian-envelope form or its online z-score form.** It is the only simple detector with a
published, peer-reviewed, wearable-specific performance record, and the reference implementation
is roughly 250 lines of pandas plus scikit-learn that compresses to well under 100.

The recipe, taken directly from the published source
([rhrad_offline.py](https://github.com/gireeshkbogu/AnomalyDetect/blob/master/scripts/rhrad_offline.py),
MIT licence):

1. Define resting heart rate as the heart-rate samples where the rolling 12-minute sum of steps is
 zero (`df1['steps_window_12'] = df1['steps'].rolling(12).sum()`, keep rows where it equals 0).
 This is the "residualise HR against activity" step, done by masking rather than regression.
2. Smooth with a 400-sample rolling mean, then resample to hourly means.
3. Remove a seasonal (diurnal) component with `statsmodels.tsa.seasonal.seasonal_decompose`.
4. Standardise against a trailing baseline window of 744 hours (31 days) and flag hours whose
 standardised residual falls outside a Gaussian envelope fitted on that window
 (`sklearn.covariance.EllipticEnvelope`, which is Mahalanobis distance with a robust covariance,
 `support_fraction=0.7`, `contamination=0.1`).
5. Debounce: raise a RED alert for a day if it contains 6 or more anomalous hours, YELLOW if 1 to 5,
 GREEN otherwise
 ([rhrad_online_24hr_alerts_v7.py, lines 272-312](https://github.com/gireeshkbogu/AnomalyDetect/blob/master/scripts/rhrad_online_24hr_alerts_v7.py)).

Published performance on the original cohort: 26 of 32 COVID-19 cases (81%) showed physiological
alterations; 22 of 25 cases with symptom information (88%) were detected at or before symptom onset,
median 4 days early; the online CuSum variant detected 15 of 24 (62.5%) pre-symptomatically; false
positive rate in healthy controls was **0.29 alarms per 30 days**
([Mishra et al., Nat Biomed Eng 2020, PMC9020268](https://pmc.ncbi.nlm.nih.gov/articles/PMC9020268/)).

An even simpler variant with an independent publication record is **NightSignal**: a six-state
finite state machine on overnight (00:00-07:00) resting heart rate, using the *streaming median*
as the baseline, transitioning on deviations of 3 bpm and raising RED at 4 bpm or more above
baseline. On 3,246 enrolled participants (2,112 with wearable data, 68 COVID-positive with usable
data) it gave pre-symptomatic detection in 45 participants at a median of **3 days** before symptom
onset, and 53 of 58 symptomatic cases (78%) alerted at or before onset, with specificity 86.9%
computed per person-day (169,980 green person-days versus 25,610 alerting person-days)
([Alavi et al., Nat Med 2022, PMC8240687](https://pmc.ncbi.nlm.nih.gov/articles/PMC8240687/)).

NightSignal is the choice if you want under 100 lines. RHR-AD is the choice if you want the
Mahalanobis machinery to talk about in a report. Both use the same underlying signal.

**Q3. Correct way to report early-warning performance so a sceptical reviewer cannot dismiss the
metric choice?**

Six rules, each with a citation, spelled out fully in Section 5:

1. **Never report point-adjusted F1.** Kim et al. showed a *random* anomaly score reaches
 F1_PA = 0.969 on SWaT while its unadjusted F1 is 0.216
 ([arXiv:2109.05257](https://arxiv.org/abs/2109.05257), AAAI 2022).
2. **Report event-level (episode-level) recall and a per-user-time false-alert rate**, not
 point-wise F1. This is what the wearable-infection literature actually does: "0.29 alarms per
 30 days" (Mishra), specificity per person-day (Alavi), "number needed to evaluate" (Wong).
3. **Report a threshold-free curve metric that is precision-recall based**, because PR-based
 metrics are the only family shown to resist both random-score inflation and best-of-N
 seed-shopping ([TSB-AD, NeurIPS 2024](https://github.com/TheDatumOrg/TSB-AD) recommends
 **VUS-PR**; [Lyu 2026, arXiv:2607.11969](https://arxiv.org/abs/2607.11969) shows affiliation-F1
 becomes gameable on 25% of series by N=3 and reaches 0.98 at N=41, while PR-based metrics and
 PA%K stay "near-flat at every N").
4. **Define the detection window explicitly and justify it**, following the PhysioNet 2019 Sepsis
 Challenge utility function, which rewards predictions between 12 hours before and 3 hours after
 onset and penalises both too-early and late predictions
 ([challenge description](https://physionet.org/content/challenge-2019/1.0.0/)).
5. **Report lead time as a distribution, not a mean**: median plus IQR plus the full per-episode
 list, conditioned on detected episodes only, and say so explicitly.
6. **Report the alert burden in operational units**: alerts per user-week, and the implied
 number-needed-to-evaluate. Wong et al. reported NNE = 8 at hospitalisation level and NNE = 109
 at a 4-hour horizon for the Epic Sepsis Model, which is what actually destroyed the model's
 credibility ([JAMA Intern Med 2021, PMC8218233](https://pmc.ncbi.nlm.nih.gov/articles/PMC8218233/)).

**Q4. Is there evidence on optimal baseline window length?**

**There is convergent practice evidence at roughly 28 to 31 days, and essentially no head-to-head
evidence comparing 7 vs 14 vs 21 vs 28 days for illness detection.** Do not claim otherwise.

- Mishra et al. used a **28-day** sliding baseline for RHR-Diff, HROS-AD and the online CuSum
 ([PMC9020268](https://pmc.ncbi.nlm.nih.gov/articles/PMC9020268/)).
- The released online implementation defaults to `--baseline_window 744` hours = **31 days**, with
 a 1-hour sliding window
 ([source line 58](https://github.com/gireeshkbogu/AnomalyDetect/blob/master/scripts/rhrad_online_24hr_alerts_v7.py)).
- Alavi et al.'s NightSignal sidesteps the question by using an **expanding streaming median**
 rather than a fixed window ([PMC8240687](https://pmc.ncbi.nlm.nih.gov/articles/PMC8240687/)).
- The one systematic parameter sweep on this dataset (Sci Rep 2022) swept the *smoothing* window
 (k = 400, 350, 300 samples) and the detector family (Minimum Covariance Determinant, One-Class
 SVM, Isolation Forest), not the baseline length
 ([PMC9097889](https://pmc.ncbi.nlm.nih.gov/articles/PMC9097889/)).
- The nearest thing to reliability evidence comes from physical-activity measurement: 6 days for
 light activity, 8 for sedentary time, 10 for moderate-to-vigorous activity to reach ICC >= 0.80,
 and the authors warn that the conventional Spearman-Brown prophecy formula **substantially
 overestimates** test-retest reliability
 ([Hilden et al., PLOS ONE 2023, PMC9956594](https://pmc.ncbi.nlm.nih.gov/articles/PMC9956594/)).
 No equivalent study for resting heart rate was found.

So: 28 days is defensible by citation; 7 and 14 are not ruled out by evidence; **running the sweep
yourself on Stanford COVID-19-Wearables is a genuine contribution**, because nobody has published it.

**Q5. Published semi-synthetic evaluation designs for health monitoring to learn from?**

Yes, three families, in descending order of authority:

1. **The UVA/Padova Type 1 Diabetes simulator**, accepted by the FDA in 2008 as a substitute for
 animal trials in pre-clinical testing of closed-loop insulin controllers. This is the strongest
 available precedent that a simulator can be a *legitimate* evaluation substrate in health
 monitoring ([Kovatchev et al., J Diabetes Sci Technol 2009,
 PMC2681269](https://pmc.ncbi.nlm.nih.gov/articles/PMC2681269/); companion methodology paper
 [PMC2771529](https://pmc.ncbi.nlm.nih.gov/articles/PMC2771529/)).
2. **Block-gap injection into real wearable data to characterise metric stability under
 missingness.** Van Der Donckt et al. compute reference features on gap-free segments, inject
 block-structured gaps that simulate non-wear, and report the spread of each derived feature as a
 function of data-retention ratio ([Sci Rep 2024,
 PMC11289092](https://pmc.ncbi.nlm.nih.gov/articles/PMC11289092/)). This is directly reusable and
 cheap.
3. **Curated semi-synthetic anomaly benchmarks in the time-series community**: the UCR Anomaly
 Archive, built precisely because existing benchmarks were shown to be trivial, mislabelled or to
 have unrealistic anomaly density ([Wu and Keogh, TKDE 2021,
 arXiv:2009.13807](https://arxiv.org/abs/2009.13807)), and TSB-AD, which re-curated 1,070 series
 from 40 datasets combining human perception and model interpretation
 ([Liu and Paparrizos, NeurIPS 2024](https://github.com/TheDatumOrg/TSB-AD)).

### 1.2 The single most important structural finding

The Stanford COVID-19-Wearables archive that everyone cites **does not contain any labels**. I
downloaded and unpacked it (Section 2.1): 280 CSV files, all of them heart rate, steps or sleep,
and nothing else. The COVID status, symptom-onset dates and diagnosis dates live in the paper's
Supplementary Information. If your pipeline assumes the labels are in the zip, it will silently
train on nothing. Plan for this.

---

## 2. THE DATASET TABLE

Legend for "obtainable?": **A** = one unauthenticated download, works today; **B** = free account
plus a click-through or short application; **C** = credentialed account, signed DUA and training;
**D** = institutional agreement, analysis inside a walled workbench; **E** = not publicly available.

### 2.0 Master table

| # | Name | Obtainable? | Access URL | Access conditions | Participants | Participant-days | Exact channels + cadence | Label type | Illness episodes | **Confounder annotations?** | Licence | Size |
|---|------|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Stanford COVID-19-Wearables** (Mishra et al. 2020) | **A** | [zip, 378 MB](https://storage.googleapis.com/gbsc-gcp-project-ipop_public/COVID-19/COVID-19-Wearables.zip) | None. Public GCS bucket, verified HTTP 200 on 2026-08-30 | 119 unique IDs in the zip (first-hand count); 32 COVID+ / 74 COVID- in the analysed cohort | **11,186** (first-hand: sum of HR-file spans); median 88.5 d/participant, range 29-524 | `hr.csv`: user, datetime, heartrate, irregular ~5-15 s. `steps.csv`: user, datetime, steps, 1/min. `sleep.csv`: user, datetime, stage_duration, stage (event rows). 87.6 M HR rows total (first-hand) | **Not in the archive.** COVID status, symptom-onset and diagnosis dates are in Supplementary Data 1 / Supplementary Info of the paper | 32 COVID-19 cases (27 confirmed) | **NO** | Not stated on the bucket. **UNVERIFIED** | 378 MB zipped, 3.64 GB unzipped (first-hand) |
| 2 | **Homekit2020** (Merrill et al. 2023) | **B** | [Synapse syn51476306](https://www.synapse.org/Synapse:syn51476306) via [GitHub](https://github.com/behavioral-data/Homekit2020) | Synapse account, certification, 1-3 paragraph research statement, several business days. Synapse API reports `restrictionLevel: OPEN` but `canDownload: false` and `isCertificationRequired: true` for anonymous users (first-hand API query) | 5,196 (Section 1 of paper) / 5,034 (Section 3.1 of paper). **Discrepancy is in the paper itself** | >14 million hours = **>583,000 participant-days** of minute-level data | Minute-level heart rate, steps, sleep state (sleep split into light / deep / awake binaries). Plus day-level features: resting HR, sleep efficiency, total asleep minutes, missing sleep, missing steps | Daily ILI symptom survey; symptomatic participants shipped a home nasal-swab kit; **laboratory PCR** for influenza and other respiratory viruses | **206 flu-PCR-positive participants** (the paper contrasts this with Mishra's 32) | **NO** (initial questionnaire + daily ILI symptom survey only; the survey CRF PDF `syn25378453` is login-gated so the exact field list is **UNVERIFIED**) | Code MIT. Data licence **UNVERIFIED** | Not stated |
| 3 | **CovIdentify** (Duke BIG IDEAs Lab) | **C** | [PhysioNet](https://physionet.org/content/covidentify/1.0.0/), DOI 10.13026/ncq1-vp79 | PhysioNet credentialed user + signed DUA + CITI "Data or Specimens Only Research" training | 2,887 (1,689 Garmin, 1,091 Fitbit, 107 Apple) | 2020-04-02 to 2021-05-21 (PhysioNet release date-shifted, ends 2021-03-21); 362,108 daily surveys, mean 62 / median 37 per person | **Day-level derived**: resting heart rate (daily value, min, median, mean, 10th percentile) and daily step count. Not minute-level | Self-reported COVID test results (not externally validated), daily symptom surveys | **132 self-reported positive**, 1,157 negative | **PARTIAL YES**: vaccination (date, brand, dose, related symptoms, added Feb 2021), symptoms, social-distancing behaviour. **No** alcohol, menstrual, medication, exercise intensity | PhysioNet Credentialed Health Data License 1.5.0 | Not stated |
| 4 | **LifeSnaps** | **A** | [Zenodo 7229547](https://zenodo.org/records/7229547) | Open, CC BY 4.0, code-of-conduct click-through | 71 (42 M / 29 F), 2 rounds | mean 41.37 d/participant, ~2,940 total; >71 M rows | HR <1 min; steps/distance/calories 3 min; estimated SpO2 variation 2 min; wrist temperature 3 min; HRV 5 min; sleep, active/sedentary minutes, resting HR, stress score, SpO2, respiratory rate daily; VO2max and HR-zone time ~2-daily; ECG ad hoc (15 users, 73 records) | Validated surveys (IPIP-50, STAI, PANAS, BREQ-2, TTM) + EMA (context and mood 3x/day, step goal daily) | **NONE** | **PARTIAL YES**: mood, affect, stress score, exercise, sleep. **No** alcohol, medication, menstrual, illness | CC BY 4.0 (verified via Zenodo API) | `rais_anonymized.zip` 615,037,493 bytes (615 MB); >9 GB uncompressed |
| 5 | **PMData** (SimulaMet) | **A** | [datasets.simula.no/pmdata](https://datasets.simula.no/pmdata/), mirror [OSF](https://osf.io/vx4bk) | Open, CC BY 4.0 | 16 | 5 months each, ~2,400 | Fitbit Versa 2: calories/min, distance/min, steps/min, heart_rate (intraday bpm), exercise sessions, sedentary/lightly/moderately/very active minutes daily, resting_heart_rate daily, sleep stages, sleep_score, HR-zone minutes. Totals: 2,440 activity sessions, 20,991,392 HR measurements, 1,836 days of sleep scores | PMSys subjective reports + Google Forms daily reporting | **NONE** (225 injury reports only) | **YES, the richest of any open dataset.** `reporting.csv` records meals eaten, weight, glasses of water and **whether alcohol was consumed**, daily, 1,569 reports. `wellness.csv` records fatigue, mood, readiness, sleep duration, **sleep quality**, soreness + area, **stress** on 1-5 scales, 1,747 reports. `srpe.csv` records session RPE and duration for 783 training sessions. Plus 644 food photos for 3 participants | CC BY 4.0 | `pmdata.zip` 1.4 GB |
| 6 | **TILES-2018** (+ TILES-2019) | **A** | [tiles-data.isi.edu](https://tiles-data.isi.edu/) | Open, cite the paper | 212 hospital workers (2018); 57 (2019) | 10 weeks each, ~14,840 (2018) | Fitbit Charge 2 24/7 (HR, steps, sleep); OMsignal garment during shifts (ECG, breathing, motion); Unihertz Jelly Pro audio *features* during shifts; 244 Owl-in-One BLE hubs at 1 Hz proximity; Minew environmental sensors | Baseline battery + daily EMA | **NONE** | **YES**: baseline includes AUDIT (alcohol), GATS (tobacco), PSQI (sleep), IPAQ (activity), BFI-2, STAI, PANAS. **Daily EMA includes tobacco and alcohol consumption**, stress, anxiety, PANAS-short, sleep hours, vigorous/moderate activity minutes | CC BY 4.0 | ~100 GB compressed |
| 7 | **GLOBEM** | **C** | [PhysioNet globem/1.1](https://physionet.org/content/globem/1.1/), code at [UW-EXP/GLOBEM](https://github.com/UW-EXP/GLOBEM) | Credentialed + DUA + CITI training | 497 unique, 155/218/137/195 per year 2018-2021 | **705 person-years**; ~10 weeks/year, mean 77.5 +/- 8.9 days | **Feature level only, no raw signals.** RAPIDS-derived features over morning/afternoon/evening/night/24h/7d-history/14d-history/weekday/weekend segments for location, phone usage, Bluetooth, calls, physical activity, sleep, WiFi. Fitbit supplies activity and sleep | BDI-II, PHQ-4, UCLA Loneliness, PSS, PANAS, STAI, CES-D, BRS, ERQ | **NONE** (depression is the outcome) | **PARTIAL**: perceived stress (PSS), affect, sleep features. **No** alcohol, medication, menstrual | PhysioNet Credentialed Health Data License 1.5.0 | Not stated |
| 8 | **MMASH** | **A** | [PhysioNet mmash/1.0.0](https://physionet.org/content/mmash/1.0.0/), DOI 10.13026/cerq-fc86 | Open | 22 healthy young males | **22** (24 h each) | Polar H7 beat-to-beat RR intervals, continuous. ActiGraph wGT3X-BT triaxial accelerometer, steps, HR, inclinometer, per second | Questionnaires + hourly activity log + saliva assays | **NONE** | **YES**: hourly activity log with 12 categories including **alcohol consumption, caffeinated drinks and smoking**; PANAS at 5 timepoints/day; MEQ, STAI-Y, PSQI, BIS/BAS, Daily Stress Inventory; saliva cortisol and melatonin x2 | Open Data Commons ODbL v1.0 | 23.5 MB |
| 9 | **AI-READI** | **B** | [FAIRhub, DOI 10.60775/fairhub.3](https://fairhub.io/datasets/2), docs at [docs.aireadi.org](https://docs.aireadi.org/) | Open-access terms for bona fide research, FAIRhub registration | 2,280 across 3 sites | 10-day wear per participant, ~22,800 | Garmin Vivosmart 5 at **5-second sampling**: heart rate, oxygen saturation, steps, activity calories, respiratory rate, sleep duration and stages, stress score 0-100. Dexcom G6 CGM every 5 min for 10 days. Some participants also Fitbit / Google Pixel Watch. mHealth-standard JSON | Diabetes / glycaemic state (normoglycaemia, prediabetes, T2D oral, T2D insulin) | **NONE** (cross-sectional) | **PARTIAL / UNVERIFIED** (15 modalities including clinical and survey data; I could not enumerate the survey instruments from the public docs) | "Health Data License", [Zenodo 10.5281/zenodo.10642459](https://doi.org/10.5281/zenodo.10642459) | v3.0.0: 2.01 TB, 165,051 files. v2.0.0 was 3.82 TB, 356,343 files. The repository page notes it is "under review for potential modification in compliance with Administration directives" |
| 10 | **All of Us Fitbit (Controlled Tier)** | **D** | [researchallofus.org data sources](https://www.researchallofus.org/data-tools/data-sources/), Fitbit docs [here](https://support.researchallofus.org/hc/en-us/articles/20281023493908-Resources-for-Using-Fitbit-Data) | Institutional agreement, Researcher Workbench only, **no bulk export**. Non-US institutional eligibility **UNVERIFIED** | **>59,000** with Fitbit data; 58,527 adults via Bring-Your-Own-Device + the WEAR study | Spanning 14 years; >39 M step observations, >31 M sleep observations | BigQuery tables: `heart_rate_summary`, **`heart_rate_minute_level`**, `sleep_daily_summary`, `sleep_daily_summary_30dayavg`, `sleep_level`, `sleep_level_short`, `activity_summary`, **`steps_intraday`**, `device`. Data are "as generated by Fitbit webAPI", with no additional cleaning | **EHR diagnoses**, physical measurements, genomics, surveys. 46% of Fitbit contributors also have EHR | **YES, via EHR** (any ICD-coded illness episode) | **YES** (the Controlled Tier CDR contains Survey + EHR + Wearable + Physical Measurement for the same participants) | All of Us Data Use Policies | N/A, cloud-resident |
| 11 | **UK Biobank accelerometry** (Category 1008) | **D** | [Showcase category 1008](https://biobank.ndph.ox.ac.uk/showcase/label.cgi?id=1008) | UK Biobank application + access fee. Gated | 236,519 invited, 106,053 agreed, 103,712 datasets received, **96,600 valid** | 7 days per participant, ~676,000 | **Axivity AX3 wrist accelerometer, 100 Hz, +/-8 g**, triaxial raw. Median 58.6 M readings per participant (IQR 56.0-60.1 M). **No heart rate** | Outcomes via linked hospital episode statistics, primary care, cancer and death registries | **YES via linkage**, but accelerometry is a single 7-day window per person, so episode-concurrent wearable data is largely absent | **YES at baseline** (alcohol, smoking, medication, diet touchscreen questionnaires), **not daily** | UK Biobank Material Transfer Agreement | Raw data on the order of tens of TB |
| 12 | **BIG IDEAs Lab Glycemic Variability and Wearable Device Data** | **A** | [PhysioNet](https://physionet.org/content/big-ideas-glycemic-wearable/1.1.2/), DOI 10.13026/zthx-5212 | Open | 16, aged 35-65, HbA1c 5.2-6.4% | 8-10 days each, ~144 | Dexcom G6 interstitial glucose every 5 min. Empatica E4: PPG 64 Hz, EDA 4 Hz, skin temperature 4 Hz, triaxial ACC 32 Hz | Demographics + HbA1c | **NONE** | **PARTIAL YES**: timestamped **food logs** with carbohydrate, protein, fat, sugar, fibre, calories and meal amount | Open Data Commons Attribution License v1.0 | 34.1 GB uncompressed, 4.7 GB compressed |
| 13 | **HRV + sleep diaries** (figshare) | **A** | [figshare DOI 10.6084/m9.figshare.28509740](https://doi.org/10.6084/m9.figshare.28509740), paper [PMC12375003](https://pmc.ncbi.nlm.nih.gov/articles/PMC12375003/) | Open, CC BY 4.0 | 49 healthy (mean 28.4 y, 51% female) | 4 weeks each, ~1,372; 33,600 hours total, mean 672 h/person | PPG 10 Hz; accelerometer XYZ 10 Hz; gyroscope XYZ 10 Hz; gyro rotation vector XYZW 10 Hz; pedometer (steps, distance, calories) 10 Hz; ambient light 10 Hz; HRV computed on 5-minute segments | Sleep diaries | **NONE** | **NO**. Diaries capture only bedtime, sleep onset, wake time, nighttime awakenings. No alcohol, caffeine, exercise, stress, medication | CC BY 4.0 | Not stated |
| 14 | **UCI COVID-lockdown college students** | **A** | [Dryad DOI 10.7280/D1WH6T](https://doi.org/10.7280/D1WH6T), paper [PMC11637128](https://pmc.ncbi.nlm.nih.gov/articles/PMC11637128/) | Open, CC BY; some free-text fields restricted on request | 21 (14 F, 6 M, 1 other, aged 18-22) | mean **7.8 months** each (SD 3.8, range 1.0-13.4), ~4,900 | Samsung Galaxy Gear Sport: IMU (accel, gyro), PPG, pressure; raw plus HRV features at 1-min and 5-min windows; watch worn ~51% of the time (SD 20). Oura Ring v1: activity, sleep, readiness, HR, HRV, sleep stages | Daily EMA (PANAS 20 items 0-100, COVID worry, health worry); weekly EMA; monthly BDI-II, BSI, GAD-7, UCLA Loneliness, MSPSS; event-impact surveys | **NONE** (COVID *worry*, not COVID infection) | **PARTIAL**: mood/affect daily, health worry. **No** alcohol, medication, menstrual | CC BY | Not stated |
| 15 | **WESAD** | **A** | [UCI dataset 465](https://archive.ics.uci.edu/dataset/465/wesad+wearable+stress+and+affect+detection) | Open | 15 | ~2 h each, **<2 participant-days in total** | RespiBAN chest at 700 Hz: ECG, EDA, EMG, respiration, body temperature, triaxial ACC. Empatica E4 wrist: BVP 64 Hz, EDA 4 Hz, TEMP 4 Hz, ACC 32 Hz | Protocol condition: baseline / stress (TSST) / amusement / meditation | **NONE** | **NO** (lab conditions, not lifestyle confounders) | CC BY 4.0 | ~2 GB |
| 16 | **PPG-DaLiA** | **A** | [UCI dataset 495](https://archive.ics.uci.edu/dataset/495/ppg+dalia) | Open | 15 (8 F, 7 M, 21-55 y) | ~2.5 h each, **<2 participant-days in total**; 64,697 labelled samples | Wrist Empatica E4: PPG 64 Hz, triaxial ACC 32 Hz. Chest RespiBAN: ECG, respiration, ACC | Ground-truth heart rate from chest ECG; 8 daily-life activities | **NONE** | **NO** | CC BY 4.0 | ~1 GB |
| 17 | **DAPHNET Freezing of Gait** | **A** | [UCI dataset 245](https://archive.ics.uci.edu/dataset/245/daphnet+freezing+of+gait), DOI 10.24432/C56K78 | Open | Parkinson's patients; exact count not stated on the UCI page (**UNVERIFIED**, widely cited as 10) | ~8 h in total | 3 accelerometers (ankle, thigh, trunk), 3 axes each in mg, plus timestamp and label = 10 columns. Sampling rate not stated on the UCI page (**UNVERIFIED**, widely cited as 64 Hz) | Manual annotation: 0 = non-experimental, 1 = experiment without freeze, 2 = freeze | **NONE** (freezing events, not illness) | **NO** | CC BY 4.0 | 20.5 MB |
| 18 | **SWELL-KW** | **A** | [Kaggle mirror](https://www.kaggle.com/datasets/qiriro/swell-heart-rate-variability-hrv) | Kaggle account | 25 knowledge workers (**UNVERIFIED**) | ~3 h each, **<4 participant-days in total** | HRV features, computer-interaction logs, facial expression, body posture | Condition labels: neutral, time pressure, interruption | **NONE** | **NO** | Kaggle terms; original licence **UNVERIFIED** | Small |
| 19 | **German Corona Data Donation (RKI)** | **E** | Contact corona-datenspende@rki.de; paper [PNAS Nexus 2023, PMC10368316](https://pmc.ncbi.nlm.nih.gov/articles/PMC10368316/) | **Not publicly downloadable.** GDPR special-category data; registration with the RKI Data Privacy Officer | 535,557 app installs Apr 2020 to Apr 2022, ~190,000 monthly active | ~2 years | Daily resting heart rate, daily step count, daily sleep duration from consumer trackers | Self-reported PCR test results and dates; vaccination status and dose timing | **YES** (self-reported PCR) | **PARTIAL** (vaccination) | N/A | N/A |
| 20 | **TemPredict (UCSF / Oura)** | **E** | Paper [Sci Rep 2022, DOI 10.1038/s41598-022-07314-0](https://doi.org/10.1038/s41598-022-07314-0) | **Raw data not shared** due to confidentiality agreements and re-identification risk | Enrolment count **UNVERIFIED** | N/A | Oura Ring standard metrics plus research-enabled continuous temperature sampled through the day | Daily self-reported symptom questionnaires; COVID diagnosis | **YES** | **UNVERIFIED** | N/A | N/A |
| 21 | **DETECT (Scripps)** | **E** | Paper [Nat Med 2021, DOI 10.1038/s41591-020-1123-x](https://doi.org/10.1038/s41591-020-1123-x) | No open download located; the Nature page blocked automated fetch | **UNVERIFIED** | N/A | Fitbit / Garmin / Apple resting heart rate, sleep, activity | Self-reported symptoms and test results | **YES** | **UNVERIFIED** | N/A | N/A |
| 22 | **Snyder Lab Long COVID Study Dataset** | **B** | [purl.stanford.edu/cb174pb4851](https://purl.stanford.edu/cb174pb4851) | Stanford Digital Repository; no re-identification; the depositor may add further restrictions | Not stated (**UNVERIFIED**) | 2020-03-10 to 2025-02-07 | Smartwatch heart rate (continuous) plus daily/periodic symptom surveys. Exact channels **UNVERIFIED** | Prior SARS-CoV-2 infection; symptom surveys | **YES** (Long COVID cohort) | **UNVERIFIED** | Open Data Commons Attribution License v1.0 | Not stated |
| 23 | **DREAMT** (PhysioNet, published 2026-06-02) | **C** | [PhysioNet wearable index](https://physionet.org/content/?topic=wearable) | Restricted access | Not fetched | Sleep-lab sessions | Multisensor wearable for real-time sleep-stage estimation | PSG-derived sleep stages | **NONE** | **NO** | Restricted | Not fetched |
| 24 | **Wearable Device Dataset from Induced Stress and Structured Exercise Sessions** (PhysioNet, 2025-06-24) | **A** | [PhysioNet](https://physionet.org/content/wearable-device-dataset/1.0.1/) | Open | Not fetched | Lab sessions | Wearable multimodal | Induced stress / structured exercise conditions | **NONE** | **NO** | Open | Not fetched |
| 25 | **Motion and heart rate from a wrist-worn wearable + PSG sleep labels** | **A** | [PhysioNet](https://physionet.org/content/sleep-accel/1.0.0/) | Open | 31 (**UNVERIFIED**) | one night each | Apple Watch motion and heart rate; PSG labels | PSG sleep stages | **NONE** | **NO** | Open | Small |

### 2.1 Stanford COVID-19-Wearables: first-hand inspection

I downloaded the 378,380,920-byte archive on 2026-08-30 and unpacked it. Verified contents:

- **281 zip entries, 280 CSV files, 3,642,179,790 bytes uncompressed.**
- File-type counts: **120** `*_hr.csv`, **4** `*_hr_longterm.csv`, **120** `*_steps.csv`,
 **4** `*_steps_longterm.csv`, **32** `*_sleep.csv`.
- **119 unique participant identifiers** (120 if you count `AA0HAI1_1` and `AA0HAI1_2` as separate
 device deployments). Only 32 participants have sleep data.
- Column headers, verbatim:
 - `"user","datetime","heartrate"` (irregular sampling, observed as close as 5 s apart)
 - `"user","datetime","steps"` (exactly one row per minute)
 - `"user","datetime","stage_duration","stage"` (event rows; `stage` values observed: `wake`, `light`)
- **Dates are shifted per participant.** Observed global range 2022-01-18 to 2030-09-03, for a study
 conducted in 2020. **Only within-participant relative time is meaningful.** Any code that joins on
 absolute calendar date across participants will be wrong.
- **Total heart-rate span: 11,186 participant-days.** Median 88.5 days per HR file, minimum 29,
 maximum 524. **87,597,892 heart-rate rows.**
- **Steps files are effectively gap-free** (99.9% to 100.0% of minutes in the span have a row, with
 zeros filled in). This means **you cannot infer non-wear from the steps file**.
- **Heart-rate minute coverage in a 6-participant sample: 88.2%, 93.8%, 94.3%, 96.6%, 96.7%, 98.6%**
 (fraction of minutes in the participant's span containing at least one HR sample). This is the
 usable non-wear proxy. Median around 95%, so roughly one hour in twenty has no heart rate.
- **There is no label file of any kind.** The COVID status, symptom-onset date and diagnosis date
 live in the paper's supplementary material. The PMC author manuscript
 ([PMC9020268](https://pmc.ncbi.nlm.nih.gov/articles/PMC9020268/)) lists two supplementary files:
 `NIHMS1786877-supplement-Supplementary_Data_1.xlsx` and
 `NIHMS1786877-supplement-Supplementary_Info.pdf`. Download them from the article page; automated
 fetching is JavaScript-gated.
- Cohort composition per the independent re-analysis: 32 COVID-positive (3 excluded for insufficient
 data or a missing symptom-onset report) and 74 COVID-negative, from an original 4,652 smartwatch
 users ([Sci Rep 2022, PMC9097889](https://pmc.ncbi.nlm.nih.gov/articles/PMC9097889/)).

**Known data quality issues (Stanford):** per-participant date shifting; sleep data for only 32 of
119 participants; 5% to 12% of minutes missing heart rate; steps zero-filled so missingness is
invisible in that stream; no per-participant device model in the archive (the cohort mixed Fitbit,
Apple Watch, Garmin and others).

### 2.2 Notes on the datasets that matter most

**PMData is the confounder gold standard.** It is the only open dataset I found that records, per
day, whether the participant drank alcohol, what they ate, their subjective stress, mood, fatigue,
sleep quality and soreness, and their training load, alongside intraday Fitbit heart rate. If you
need to demonstrate that your agent can attribute a heart-rate elevation to a confounder rather
than to illness, PMData is the substrate. Its weakness is that it has zero illness episodes, so it
can only support false-alarm characterisation and confounder-attribution demonstrations, not
sensitivity.

**MMASH is the smallest useful confounder dataset.** 22 participants, 24 hours each, 23.5 MB, with
an hourly log containing explicit alcohol, caffeine and smoking categories. Far too short for
personalised baselines, but excellent as a quick illustrative example.

**TILES-2018 is the largest open dataset with daily alcohol and tobacco EMA.** 212 people, 10 weeks,
Fitbit Charge 2 worn 24/7 plus daily surveys, CC BY 4.0. Its ~100 GB compressed footprint is the
only real barrier.

**Homekit2020 is the best-labelled dataset in existence** (206 PCR-confirmed influenza cases,
minute-level Fitbit, 14 million hours), and it is worth applying for even if approval takes a week.
It also ships an evaluation framework and a pip-installable toolkit, so the benchmark's own metric
choices are auditable.

**LifeSnaps known data quality issues** (from the data descriptor,
[PMC9622868](https://pmc.ncbi.nlm.nih.gov/articles/PMC9622868/)): approximately 3% of export files
missing for steps, heart rate, exercise and distance; approximately 3% of participants changed time
zone mid-study; SEMA3/Fitbit compliance decayed by roughly 18% over the study; approximately 1%
device incompatibility with the EMA app; corrupted entries (weight errors, wrong dates from a server
misconfiguration); **approximately 50% of participants did not wear the device during sleep or
bathing**; swimming data excluded because of false positives.

### 2.3 Simulated and synthetic wearable data generators

| Tool | What it generates | URL | Notes |
|---|---|---|---|
| **wearipedia** | Synthetic data matching the schemas of Fitbit, Whoop, Oura, Garmin, Dexcom and others, plus real-device extraction | [PyPI 0.1.7](https://pypi.org/project/wearipedia/) | Stanford project. Schema-faithful but the physiology is simple; adequate for pipeline testing, not for detector benchmarking |
| **NeuroKit2** | `ppg_simulate`, `ecg_simulate`, `rsp_simulate`, `eda_simulate` with controllable heart rate, HRV, respiratory modulation and noise | [PyPI](https://pypi.org/project/neurokit2/), [GitHub](https://github.com/neuropsychology/NeuroKit) | Best option for generating a realistic raw PPG or ECG trace with a controlled ground-truth heart rate. Useful for constructing a semi-synthetic illness episode |
| **SDV (Synthetic Data Vault), PAR model** | Sequential and multi-sequence synthetic tabular time series | [sdv.dev](https://sdv.dev/) | General purpose; needs real training data |
| **TimeGAN / DoppelGANger** | GAN-based time-series synthesis | [TimeGAN](https://github.com/jsyoon0823/TimeGAN) | Widely used but hard to validate |

**Health warning, with a citation:** a 2025 review argues that current generative approaches to
wearable sensor synthesis have material limitations for downstream health tasks
([arXiv:2505.14206, "Challenges and Limitations of Generative AI in Synthesizing Wearable Sensor
Data"](https://arxiv.org/abs/2505.14206)). Do not build a headline claim on synthetic data alone.

---

## 3. Detection method comparison

### 3.0 Summary table

| Method family | What it does | Computational cost | Interpretability | Published wearable-health use | Python implementation | Known failure modes |
|---|---|---|---|---|---|---|
| **Shewhart chart** (individual-value control chart, "mean +/- k sigma") | Flags any single point beyond control limits set from a baseline period | O(1) per point, O(n) total. Trivially streamable | Highest of any method. One number, one threshold, directly plottable | Used as the conceptual base of every RHR-alerting system. Directly applied to passive sensing to predict bipolar episodes ([J Psychopathol Clin Sci 2025, DOI 10.1037/abn0001002](https://doi.org/10.1037/abn0001002)) | `pyspc` ([GitHub](https://github.com/carlosqsilva/pyspc)); trivially hand-coded with pandas `rolling().mean()` and `.std()` | Insensitive to small sustained shifts (that is exactly what an incubating infection looks like). Very sensitive to a non-Gaussian, right-skewed RHR distribution. Baseline contamination: if the baseline window contains an illness, limits inflate and you miss the next one |
| **CUSUM** (cumulative sum) | Accumulates signed deviations from a target and alarms when the running sum exceeds a decision interval. Designed for small persistent shifts | O(1) per point. The cheapest possible sequential detector | High. The CUSUM statistic itself is a plottable "evidence accumulator", which is a good story for an agentic system | **Used as the online detector in Mishra et al.**, 28-day baseline, two-tier alerting: yellow at p < 0.01, red when sustained over 24 h. Detected 15 of 24 (62.5%) COVID cases pre-symptomatically ([PMC9020268](https://pmc.ncbi.nlm.nih.gov/articles/PMC9020268/)). Also compared head-to-head in Alavi et al., specificity 87.4% per person-day ([PMC8240687](https://pmc.ncbi.nlm.nih.gov/articles/PMC8240687/)) | `banpei` ([PyPI](https://pypi.org/project/banpei/)); `river.drift.PageHinkley` ([riverml.xyz](https://riverml.xyz/)); ~15 lines by hand | Needs a reset rule after an alarm or it stays latched. Assumes a known target mean and variance, so it inherits every problem of the baseline estimate. Reference value `k` and decision interval `h` are two free parameters that most papers do not report |
| **EWMA** (exponentially weighted moving average) | Weighted average with geometrically decaying weights, with control limits derived from the smoothing parameter lambda | O(1) per point | High. A single smoothed line with a band | Applied in multivariate SPC form to HRV features for epileptic seizure prediction ([IEEE TBME 2016, DOI 10.1109/tbme.2015.2512276](https://doi.org/10.1109/tbme.2015.2512276)) and in adaptive form to anaesthesia HR trends ([IEEE TBME 2006, DOI 10.1109/tbme.2006.877107](https://doi.org/10.1109/tbme.2006.877107)) | `statsmodels` / `pandas.Series.ewm`; `river` | The smoothing that gives it sensitivity also delays detection, which directly costs lead time. Control limits for small lambda assume steady state and are wrong during the warm-up period |
| **Bayesian online change-point detection (BOCPD)** | Maintains a posterior over "run length since the last change point" and updates it recursively; a change point is a collapse of that posterior | O(t) per step naively, O(1) with run-length truncation. Heavier than CUSUM by one to two orders of magnitude | Medium. The run-length posterior is a beautiful diagnostic plot, but the hazard rate and conjugate prior are not intuitive to a clinician | **Poor track record on the one benchmark that scored it.** The Numenta Anomaly Benchmark scoreboard rates "Bayesian Changepoint" at **17.7 / 100** on the standard profile and **3.2** on the reward-low-false-positive profile, versus 11.0 and 1.2 for a random detector ([NAB README](https://github.com/numenta/NAB)). I found **no** published use of BOCPD for consumer-wearable infection detection | `bayesian-changepoint-detection` v0.2.dev1 ([GitHub](https://github.com/hildensia/bayesian_changepoint_detection)); `changefinder` ([PyPI](https://pypi.org/project/changefinder/)); `ruptures` v1.1.10 for offline change points ([GitHub](https://github.com/deepcharles/ruptures/)) | Requires a conjugate observation model, which physiological data violate (skewed, heteroscedastic, non-stationary diurnally). The hazard rate is a free parameter that dominates behaviour. Detects the change *after* enough evidence accumulates, so it is not obviously better than CUSUM for lead time while costing far more. **If you use it, expect to defend the NAB result** |
| **Rolling median + MAD** (robust personalised baseline) | Centre by the trailing median, scale by median absolute deviation, flag on a robust z-score | O(n log w) with a naive rolling median, O(n) with a monotonic deque | Very high. "Your resting heart rate is 4 bpm above your own median" is a sentence a user understands | **NightSignal uses exactly this**: streaming median of overnight RHR as baseline, transition at 3 bpm, red at 4 bpm. 78% of symptomatic COVID cases alerted at or before onset, median 3 days early ([PMC8240687](https://pmc.ncbi.nlm.nih.gov/articles/PMC8240687/)) | `pandas.Series.rolling(w).median()` and `.apply(median_abs_deviation)`; `scipy.stats.median_abs_deviation` | MAD is zero when more than half the window is identical (common for quantised RHR). Needs a floor on the scale estimate. Slow to adapt after a genuine regime change (detraining, new medication) |
| **Quantile bands** | Flag values outside the trailing p-th and (1-p)-th empirical quantiles | O(n log w) | High | No infection-specific citation found; standard in the wearable-metrics literature as a personal-normal-range display | `pandas.Series.rolling(w).quantile(q)` | Requires a long window to estimate extreme quantiles at all. With a 28-day hourly window (672 points) the 1st percentile is estimated from ~7 observations |
| **Seasonal decomposition (STL / classical)** | Split the series into trend, seasonal (24 h) and residual; detect on the residual | O(n) for classical, O(n) for STL with a few passes | High. Three plots, each meaningful | **Used inside the published RHR-AD pipeline**: `seasonal_decompose(model='additive')` applied to standardised RHR and steps before the outlier model ([source](https://github.com/gireeshkbogu/AnomalyDetect/blob/master/scripts/rhrad_offline.py)) | `statsmodels.tsa.seasonal.seasonal_decompose`, `statsmodels.tsa.seasonal.STL` | Requires a fixed, known period. Breaks under shift work, jet lag and irregular sleep. Classical decomposition loses half a period at each end, which matters when you are trying to detect at the trailing edge |
| **Cosinor analysis** | Fit `y = M + A*cos(2*pi*t/T + phi)` and monitor MESOR, amplitude and acrophase | O(n) least squares | High, and clinically familiar in chronobiology | Standard in circadian actigraphy research; reviewed in [Gao et al., Curr Sleep Med Rep 2023, PMC12829919](https://pmc.ncbi.nlm.nih.gov/articles/PMC12829919/) | `CosinorPy` v3.1 ([GitHub](https://github.com/mmoskon/CosinorPy)); `pyActigraphy` v1.2.2 ([GitHub](https://github.com/ghammad/pyActigraphy)) | **Three documented failure modes, all of which bite here.** (1) Shape: "criticism exists in applying the cosine curve fitting to actigraphy signals, as these data are often non-sinusoidal in shape". (2) Stationarity: the method "fundamentally assumes that the analyzed data are stationary", which circadian data are not. (3) Fixing it with more harmonics adds "complexity both methodologically and interpretation-wise". All quotes from PMC12829919. **With irregular sleep schedules the acrophase estimate becomes unstable and the amplitude is attenuated**, so a cosinor-based alarm fires on schedule changes, not on illness. Prefer non-parametric circadian metrics (interdaily stability IS, intradaily variability IV, relative amplitude RA, L5, M10) which make no shape assumption, all available in `pyActigraphy` |
| **Residualising HR against activity** | Model HR as a function of concurrent movement and monitor the residual, or mask to zero-activity periods | Masking: O(n). Regression: O(n) per fit | High for masking ("this is your heart rate while you were still"). Medium for regression | **Masking is the published approach.** Mishra et al. define RHR as "the HR measurements recorded when there were less than two steps taken during a rolling time window of the preceding 12 minutes" ([implementation comment, line 130](https://github.com/gireeshkbogu/AnomalyDetect/blob/master/scripts/rhrad_online_24hr_alerts_v7.py)). The HROS variant instead uses the heart-rate-over-steps *ratio* | 5 lines of pandas. `statsmodels` OLS or `sklearn` if you want a regression form | Masking throws away 80% to 95% of the data and biases towards sedentary periods, so it confounds "resting HR" with "how much the person sat still today". The HROS ratio is undefined at zero steps and explodes near zero. Neither approach handles the fact that fever raises HR *and* lowers activity simultaneously, so the two channels are not independent |
| **Mahalanobis distance / Minimum Covariance Determinant** | Distance from the multivariate centre, scaled by a robust covariance estimate | O(d^3) for the covariance, O(d^2) per point. Refit per sliding window makes it O(n*d^2) | Medium. A single scalar distance, but the direction of the deviation is lost unless you decompose it | **This is what the published RHR-AD actually uses**: `sklearn.covariance.EllipticEnvelope(support_fraction=0.7, contamination=0.1)` refit on every 744-hour window ([source lines 219-225](https://github.com/gireeshkbogu/AnomalyDetect/blob/master/scripts/rhrad_online_24hr_alerts_v7.py)). Also compared as "MD-MCD" against One-Class SVM and Isolation Forest in [PMC9097889](https://pmc.ncbi.nlm.nih.gov/articles/PMC9097889/) | `sklearn.covariance.EllipticEnvelope`, `sklearn.covariance.MinCovDet` | The `contamination` parameter *forces* a fixed fraction of every window to be anomalous. With `contamination=0.1` you are guaranteed roughly 10% of hours flagged, forever, regardless of health. **This is the single biggest defensibility problem with the published baseline** and you should say so in your report. Also assumes elliptical, unimodal data |
| **Isolation Forest** | Random axis-parallel splits; anomalies need fewer splits to isolate | O(n log n) to fit, O(log n) per query | Low to medium. Feature importance is available but the score has no physical units | Compared against MD-MCD and One-Class SVM on the Stanford data; the One-Class SVM variants won ([PMC9097889](https://pmc.ncbi.nlm.nih.gov/articles/PMC9097889/)). Also applied to home-monitoring deterioration ([Biomed Phys Eng Express 2026, DOI 10.1088/2057-1976/ae55a9](https://doi.org/10.1088/2057-1976/ae55a9)) | `sklearn.ensemble.IsolationForest`; `pyod` v3.6.5 ([GitHub](https://github.com/yzhao062/pyod)) | Same forced-contamination problem. Axis-parallel splits ignore temporal order entirely, so it cannot distinguish "high HR for one hour" from "high HR for three days". Needs feature engineering to see time at all |
| **Autoencoders / VAE / LSTM-AE** | Reconstruct the window; large reconstruction error implies anomaly | Training O(epochs * n). GPU desirable. Inference cheap | Low. Reconstruction error is not a clinical quantity | **PCovNet** (LSTM-VAE) and **PCovNet+** (CNN-VAE with LSTM embeddings) both trained on the Stanford COVID-19-Wearables data ([Comput Biol Med 2022, PMC9170596](https://pmc.ncbi.nlm.nih.gov/articles/PMC9170596/); [Eng Appl Artif Intell 2023, PMC10047244](https://pmc.ncbi.nlm.nih.gov/articles/PMC10047244/)). **LAAD** from the Snyder lab ([GitHub](https://github.com/gireeshkbogu/LAAD)) | `pyod`, `alibi-detect` v0.13.0 ([GitHub](https://github.com/SeldonIO/alibi-detect)), `darts.ad`, `salesforce-merlion` v2.0.4 | **The benchmark evidence is against them.** TSB-AD (NeurIPS 2024) concludes that "simpler architectures and statistical methods often yield better performance" than advanced neural architectures across 1,070 curated series and 40 algorithms ([TSB-AD](https://github.com/TheDatumOrg/TSB-AD)). Kim et al. showed untrained models match published deep methods once point adjustment is forbidden ([arXiv:2109.05257](https://arxiv.org/abs/2109.05257)). With 32 positive episodes you cannot train one honestly |
| **Matrix profile / discord discovery** | Nearest-neighbour distance profile over all subsequences; discords are subsequences with the largest nearest-neighbour distance | O(n log n) with FFT-based STOMP; streaming variants exist | Medium to high. You can always show the nearest neighbour that the anomalous window failed to match | Not found in the wearable-infection literature. Heavily used in the UCR Anomaly Archive that Wu and Keogh built ([arXiv:2009.13807](https://arxiv.org/abs/2009.13807)) | `stumpy` v1.14.1 ([GitHub](https://github.com/stumpy-dev/stumpy)), which includes streaming (`stumpi`) and the DAMP discord detector | Needs a subsequence length parameter. Finds *the* most unusual subsequence by construction, so "always returns something" unless you threshold carefully |

### 3.1 Handling missing data and non-wear, and whether missingness is informative

**Missingness in wearable data is informative, and there is a citation for it.**

Van Der Donckt et al. state that missing wearable data "can stem from non-random processes where
the likelihood of missing data depends on other unobserved symptoms", and specifically observed that
**participants wore the device less frequently during headache episodes**
([Sci Rep 2024, PMC11289092](https://pmc.ncbi.nlm.nih.gov/articles/PMC11289092/)). The same paper
reports that daytime data quality is substantially worse than nighttime (defined as 20:00 to 08:00),
that motion artefact is the most prevalent corruption source, and that streaming mode loses more
data than on-device logging.

Practical consequences:

- **Treat wear-time as a channel, not as a nuisance.** A drop in wear time is a candidate illness
 signal in its own right. It is also a candidate confounder (holiday, forgot to charge). The
 Homekit2020 day-level feature set explicitly includes `missing sleep` and `missing steps` as
 features ([PMLR v209](https://proceedings.mlr.press/v209/merrill23b.html)), which is a
 peer-reviewed precedent for doing this.
- **Never impute across a non-wear gap and then run a detector on the imputed values.** UK Biobank's
 published pipeline imputes missing epochs using "average of similar time-of-day vector magnitude
 and intensity distribution data points with one minute granularity on different days"
 ([Doherty et al., PLOS ONE 2017, PMC5287488](https://pmc.ncbi.nlm.nih.gov/articles/PMC5287488/)),
 which is fine for computing a weekly activity summary and catastrophic for anomaly detection,
 because it manufactures normality exactly where you have no evidence.
- **Non-wear detection algorithms.** UK Biobank defines non-wear as consecutive stationary episodes
 of at least 60 minutes where all three accelerometer axes have standard deviation below 13.0 mg
 ([PMC5287488](https://pmc.ncbi.nlm.nih.gov/articles/PMC5287488/)). For heart-rate-based devices
 the practical rule is "no HR sample in the minute". Implementations: `accelerometer` v7.5.0
 (the Oxford biobankAccelerometerAnalysis package,
 [GitHub](https://github.com/activityMonitoring/biobankAccelerometerAnalysis)),
 `scikit-digital-health` v0.17.17, `pyActigraphy` v1.2.2.
- **The recommended evaluation move**: compute your feature on gap-free segments, then inject
 block-structured gaps of realistic length and report how much your feature moves as a function of
 retention ratio ([PMC11289092](https://pmc.ncbi.nlm.nih.gov/articles/PMC11289092/)). This turns a
 weakness into a robustness result.

### 3.2 Debouncing and persistence rules

Every published wearable alerting system debounces. None of them justify the specific numbers, which
means you are free to choose yours as long as you state and sweep them.

| System | Persistence rule | Source |
|---|---|---|
| Mishra RHR-Diff (offline) | Minimum detection duration **greater than 24 hours** of continuous elevation | [PMC9020268](https://pmc.ncbi.nlm.nih.gov/articles/PMC9020268/) |
| Mishra CuSum (online) | Two tiers: yellow at p < 0.01, **red only when sustained beyond 24 hours** | [PMC9020268](https://pmc.ncbi.nlm.nih.gov/articles/PMC9020268/) |
| Bogu RHRAD online | Per 24-hour block ending at 21:00: **RED if >= 6 anomalous hours**, YELLOW if 1 to 5, GREEN if 0. Days with no heart rate are emitted as `NA`, not as GREEN | [source lines 272-345](https://github.com/gireeshkbogu/AnomalyDetect/blob/master/scripts/rhrad_online_24hr_alerts_v7.py) |
| Alavi NightSignal | Six-state finite state machine over successive nights; state transitions require deviations on consecutive nights. **"Red alert clusters" are defined as two or more consecutive red-alert days**; mean cluster duration 4.3 days in COVID-positives versus 1.9 days in negatives | [PMC8240687](https://pmc.ncbi.nlm.nih.gov/articles/PMC8240687/) |

The last row is the most useful finding for an early-warning system: **cluster duration itself
separates true from false alerts** (4.3 days versus 1.9 days). That is a free, defensible feature.

### 3.3 What "at most 100 lines" should actually contain

Ranked by evidence-per-line:

1. **NightSignal-style overnight RHR versus streaming median, with a 2-consecutive-night rule.**
 Approximately 40 lines. Cited sensitivity 78% at symptom onset, median 3 days lead, specificity
 86.9% per person-day.
2. **Add the RHRAD hourly z-score with a 28-day trailing window and the ">= 6 anomalous hours in 24 h"
 debounce.** Approximately 80 lines. Cited 81% detection, 88% pre-symptomatic among detected,
 0.29 false alarms per 30 days.
3. **Do not use `EllipticEnvelope` with a fixed `contamination`** unless you also report what happens
 when you replace it with a fixed z-threshold. The forced-contamination behaviour is the easiest
 thing for a reviewer to attack, and defusing it pre-emptively is worth marks.

---

## 4. Evaluation methodology: the critiques and the recommended protocols

This is the section that decides whether the project survives review. The literature here is
unusually blunt.

### 4.1 The point-adjustment critique (the load-bearing one)

**Point adjustment (PA)** is the protocol where, if a detector flags *at least one* timestamp inside
a ground-truth anomaly segment, *every* timestamp in that segment is relabelled as correctly
detected before computing precision, recall and F1.

**Kim, Choi, Choi, Lee and Yoon, "Towards a Rigorous Evaluation of Time-series Anomaly Detection",
AAAI 2022** ([arXiv:2109.05257](https://arxiv.org/abs/2109.05257), code at
[tuslkkk/tadpak](https://github.com/tuslkkk/tadpak)) demonstrated:

- A **random anomaly score** achieves **F1_PA = 0.969 on SWaT** while its **unadjusted F1 is 0.216**.
 Across datasets the pattern is the same: random scores get F1 in the range 0.080 to 0.227 without
 PA, and roughly 0.8 to 0.97 with PA.
- Under PA, a random score "can easily turn into a state-of-the-art TAD method", so **rankings of
 published methods under PA are not meaningful**.
- An **untrained** model achieves detection performance comparable to published methods even when PA
 is forbidden, which implies the reported progress in the field was largely an artefact.

Their proposed replacement, **PA%K**: apply point adjustment to a segment only when the fraction of
points inside that segment which exceed the anomaly threshold is greater than K. Their recommendation
is to sweep K from 0 to 100 and report the **area under the F1_PA%K curve**, so that no single
arbitrary K is being exploited.

**Practical rule for this project: if the word "point-adjusted" appears anywhere in your results,
a reviewer who knows this paper will discount the entire table.**

### 4.2 The benchmark critique

**Wu and Keogh, "Current Time Series Anomaly Detection Benchmarks are Flawed and are Creating the
Illusion of Progress", IEEE TKDE 2021** ([arXiv:2009.13807](https://arxiv.org/abs/2009.13807)).
They examined the standard benchmarks from Yahoo, Numenta, NASA and others and argued that the
majority of individual exemplars suffer from at least one of four flaws:

1. **Triviality** (a one-line rule solves them),
2. **Unrealistic anomaly density**,
3. **Mislabelled ground truth**,
4. **Run-to-failure bias**.

Their remedy was the **UCR Time Series Anomaly Archive**, deliberately constructed so that
comparisons are meaningful.

**Liu and Paparrizos, "The Elephant in the Room: Towards A Reliable Time-Series Anomaly Detection
Benchmark", NeurIPS 2024** ([TSB-AD](https://github.com/TheDatumOrg/TSB-AD),
[leaderboard](https://thedatumorg.github.io/TSB-AD/)) continued the argument on three axes:
dataset integrity (1,070 curated series from 40 datasets, curated by combining "human perception
and model interpretation"), measure reliability, and benchmarking consistency (40 algorithms with
hyperparameter tuning under a unified setup). Two conclusions matter here:

- **They identify VUS-PR as "the most reliable and accurate measure".**
- **"Simpler architectures and statistical methods often yield better performance"** than advanced
 neural architectures. This is direct, citable cover for choosing a simple detector.

### 4.3 The proposed replacement metrics, and the critique of the replacements

| Metric | Proposal | Source | Python |
|---|---|---|---|
| **Range-based precision and recall** | Generalises precision and recall to *ranges* with tunable components for existence, size, position and cardinality, so that domain preferences (for example "reward early detection") are explicit parameters | Tatbul, Lee, Zdonik, Alam, Gottschlich, "Precision and Recall for Time Series", NeurIPS 2018 ([arXiv:1803.03639](https://arxiv.org/abs/1803.03639), [PDF](https://people.csail.mit.edu/tatbul/publications/NeurIPS18.pdf)) | `prts` v1.0.0.3 ([PyPI](https://pypi.org/project/prts/), [GitHub](https://github.com/CompML/PRTS)) |
| **Time-series aware precision and recall (TaPR)** | Precision/recall that account for detection-result variety and ambiguous labelling | Hwang et al., CIKM 2019 ([DOI 10.1145/3357384.3358118](https://doi.org/10.1145/3357384.3358118)); follow-up "Do you know existing accuracy metrics overrate time-series anomaly detections?", SAC 2022 ([DOI 10.1145/3477314.3507024](https://doi.org/10.1145/3477314.3507024)) | eTaPR reference implementation on GitHub |
| **Affiliation precision and recall** | Parameter-free, distance-based. Every predicted point is "affiliated" to its nearest ground-truth event; precision and recall are built from average temporal distances and normalised against a random baseline | Huet, Navarro, Rossi, "Local Evaluation of Time Series Anomaly Detection Algorithms", KDD 2022 ([arXiv:2206.13167](https://arxiv.org/abs/2206.13167), [DOI 10.1145/3534678.3539339](https://doi.org/10.1145/3534678.3539339)) | [ahstat/affiliation-metrics-py](https://github.com/ahstat/affiliation-metrics-py) |
| **VUS-ROC and VUS-PR** (Volume Under the Surface) | Threshold-independent and parameter-free. Sweeps both the detection threshold and a label-buffer width, integrating the resulting surface | Paparrizos, Boniol, Palpanas, Tsay, Elmore, Franklin, PVLDB 15(11):2774-2787, 2022 ([PDF](https://www.vldb.org/pvldb/vol15/p2774-paparrizos.pdf)); journal version [VLDB J 2025](https://link.springer.com/article/10.1007/s00778-025-00907-x) | `vus` v0.0.6 ([GitHub](https://github.com/TheDatumOrg/VUS)) |
| **PATE** (Proximity-Aware Time series anomaly Evaluation) | Buffer zones around each anomaly interval with proximity-based weighting on the temporal relationship between prediction and anomaly interval; produces a **weighted area under the precision-recall curve**. Shows that "Point-Adjusted F1 Score fails to characterize the detection performances well" | Ghorbani, Reinders, Tax, KDD 2024 ([arXiv:2405.12096](https://arxiv.org/abs/2405.12096)) | [Raminghorbanii/PATE](https://github.com/Raminghorbanii/PATE) |
| **NAB score** | Anomaly windows plus a **scaled sigmoid that gives higher credit the earlier inside the window a detection occurs**: `S = 2*sigmoid(-5*relativePositionInWindow) - 1`, so the leading edge of the window scores 0.9866, the midpoint 0.8483, the right edge 0.0, and after the window it goes negative down to -0.9866. Weighted by application profile: standard `tp=1.0, fn=1.0, fp=0.11`; reward-low-FP `fp=0.22`; reward-low-FN `fn=2.0`. Normalised so a perfect detector scores 100 and a null detector 0 | Lavin and Ahmad, [arXiv:1510.03336](https://arxiv.org/abs/1510.03336); Ahmad, Lavin, Purdy, Agha, Neurocomputing 2017, [DOI 10.1016/j.neucom.2017.04.070](https://doi.org/10.1016/j.neucom.2017.04.070); [profiles.json](https://github.com/numenta/NAB/blob/master/config/profiles.json), [sweeper.py](https://github.com/numenta/NAB/blob/master/nab/sweeper.py) | [numenta/NAB](https://github.com/numenta/NAB) |

**The critique of the replacements.** Do not assume the problem is solved.

**Lyu, "Did We Actually Fix It? An Independent Adversarial Stress-Test of Post-Point-Adjustment
Evaluation Metrics for Time-Series Anomaly Detection", 2026**
([arXiv:2607.11969](https://arxiv.org/abs/2607.11969)) stress-tested PA%K, range-based
precision/recall, affiliation precision/recall, VUS, ROC and PR across UCR, SMD, SMAP, MSL, NAB and
PSM:

- **Under a single honest run (N=1) the replacements hold up.** A random detector reaches at most
 11% of the best real detector's affiliation-F1, 5% on ROC-based metrics, 2% on PR-based metrics
 and PA%K.
- **Under best-of-N reporting (seed-shopping) they diverge sharply.** Affiliation-F1 becomes
 "gameable (25% of series) by N=3" and reaches **0.98 at N=41**. ROC-based metrics cross gameable
 thresholds at N=9 to 11. **PR-based metrics and PA%K remain "near-flat at every N".**
 VUS-ROC inflated on 131 series where VUS-PR did not.
- **Recommendation: report single-run scores, disclose N, and prefer PR-based metrics.**

**Yang, Liu, Song, Yang, Zhou, "A Problem-Oriented Taxonomy of Evaluation Metrics for Time Series
Anomaly Detection", 2025** ([arXiv:2511.18739](https://arxiv.org/abs/2511.18739)) organises metrics
along six dimensions: basic accuracy, timeliness rewards, labelling tolerance, human-audit cost,
robustness against score inflation, and cross-dataset comparability. They find that Point-Adjust has
"limited resistance to random-score inflation" and that "most event-level metrics exhibit strong
separability", concluding that metric selection should be "task-dependent and aligned with
operational objectives".

**Sørbø and Ruocco, "Navigating the Metric Maze: A Taxonomy of Evaluation Metrics for Anomaly
Detection in Time Series"** ([arXiv:2303.01272](https://arxiv.org/abs/2303.01272), published in
Data Mining and Knowledge Discovery) surveys twenty metrics against a set of desirable properties
and concludes there is no universal winner, only task-appropriate choices.

**Additional 2025-2026 entries worth knowing about** (found but not read in full, listed for
completeness): "Formally Exploring Time-Series Anomaly Detection Evaluation Metrics"
([arXiv:2510.17562](https://arxiv.org/abs/2510.17562)) and "CCE: Confidence-Consistency Evaluation"
([arXiv:2509.01098](https://arxiv.org/abs/2509.01098)).

### 4.4 How the health-monitoring literature reports early warning specifically

This is where generic TSAD metrics stop being enough. The clinical and wearable literature has its
own conventions, and they are the ones a healthcare-AI reviewer will expect.

**Lead time.** Reported as a distribution over *detected* episodes, with a median:

- Mishra: "22 of 25 cases detected before or at symptom onset, **median 4 days**, four cases at least
 nine days earlier" ([PMC9020268](https://pmc.ncbi.nlm.nih.gov/articles/PMC9020268/)).
- Alavi: "pre-symptomatic detection in 45 participants, **median of three days** prior to symptom
 onset" ([PMC8240687](https://pmc.ncbi.nlm.nih.gov/articles/PMC8240687/)).

Note the survivorship: both medians are conditioned on detection. **You must state that
conditioning**, or a reviewer will read it as an unconditional expectation.

**Detection window.** The strongest formalisation in health is the **PhysioNet/Computing in
Cardiology Challenge 2019 utility function** for early sepsis prediction
([challenge page](https://physionet.org/content/challenge-2019/1.0.0/)):

- Predictions between **12 hours before** and **3 hours after** `t_sepsis` receive a positive score,
 maximum reward 1.0.
- Predictions **more than 12 hours before** `t_sepsis` receive a penalty, maximum 0.05.
- Predictions **after** the 3-hour window receive a penalty, maximum -2.0.
- On non-sepsis patients, false positives incur a penalty of at most 0.05, and true negatives score 0.
- The total is normalised: `U_normalized = (U_total - U_no_predictions) / (U_optimal - U_no_predictions)`,
 so 0 = never predict, 1 = optimal.

This design is worth copying wholesale because it simultaneously encodes the detection window, the
lead-time reward, the too-early penalty and the false-alarm cost in one number that reviewers in
health informatics recognise.

**False alerts.** Three counting conventions appear, and you should report at least two:

| Convention | Example from the literature | Source |
|---|---|---|
| **Alarms per unit of person-time** | "false positive rate among healthy controls: **0.29 alarms per 30 days**" | Mishra, [PMC9020268](https://pmc.ncbi.nlm.nih.gov/articles/PMC9020268/) |
| **Per person-day specificity** | NightSignal 169,980 / (169,980 + 25,610) = **86.9%**; online RHRAD 87.2%; online CuSum 87.4%. That is roughly **13% of all person-days alerting** | Alavi, [PMC8240687](https://pmc.ncbi.nlm.nih.gov/articles/PMC8240687/) |
| **Number needed to evaluate (NNE) and share of subjects alerted** | Epic Sepsis Model: 18% of hospitalisations (6,971 of 38,455) alerted at score >= 6; **NNE = 8** at hospitalisation level, **NNE = 109** at a 4-hour horizon; sensitivity 33%, specificity 83%, PPV 12% | Wong et al., JAMA Intern Med 2021, [PMC8218233](https://pmc.ncbi.nlm.nih.gov/articles/PMC8218233/) |

The Wong paper also contains the single most important cautionary lesson for this project: the
vendor's reported AUC of 0.76 to 0.83 could be reproduced (AUC 0.80) **only by allowing predictions
made up to 3 hours after sepsis onset to count**. External validation with correct timing gave
**AUC 0.63**. In other words, **the entire apparent performance was a leak through the detection
window definition.** Define your window before you look at results, and say when you defined it.

**Alert clustering as a discriminator.** Alavi reported mean red-alert cluster duration of **4.3
days in COVID-positives versus 1.9 days in negatives**, over 4,217 total red-alert clusters (defined
as two or more consecutive red-alert days), of which only 678 had participant annotations
([PMC8240687](https://pmc.ncbi.nlm.nih.gov/articles/PMC8240687/)). That last number is itself a
lesson: **most alerts in a real deployment are never adjudicated**, so specificity in the wild is a
lower bound at best.

### 4.5 Calibration under extreme class imbalance

**The reference framework is the calibration hierarchy.** Van Calster, McLernon, van Smeden,
Wynants, Steyerberg, "Calibration: the Achilles heel of predictive analytics", BMC Medicine
2019;17:230 ([PMC6912996](https://pmc.ncbi.nlm.nih.gov/articles/PMC6912996/),
[DOI 10.1186/s12916-019-1466-7](https://doi.org/10.1186/s12916-019-1466-7)) defines four increasing
levels:

1. **Mean calibration**: average predicted risk versus overall event rate (the observed-to-expected
 ratio).
2. **Weak calibration**: calibration **intercept** (target 0) and **slope** (target 1).
3. **Moderate calibration**: "estimated risks correspond to observed proportions, e.g. among
 patients with an estimated risk of 10%, 10 in 100 have or develop the event". Assessed with a
 **flexible calibration curve** fitted by loess or splines.
4. **Strong calibration**: correct for every combination of predictor values. Described as "a utopic
 goal".

Two operational points from that paper:

- **Do not use the Hosmer-Lemeshow test.** Quoting: "it is based on artificially grouping patients
 into risk strata, gives a P value that is uninformative with respect to the type and extent of
 miscalibration, and suffers from low statistical power."
- **Sample size**: "a minimum of 200 patients with and 200 patients without the event has been
 suggested" for a precise calibration curve. **You will have 20 to 50 events. Therefore you cannot
 produce a trustworthy calibration curve, and you should say so rather than plot one.**

**Brier score behaviour under imbalance.** The Van Calster paper does not discuss the Brier score.
The relevant properties, which I state here as standard decision-theory results rather than as
citations to a specific wearable paper:

- The Brier score is a proper scoring rule, so it is minimised by the true probabilities.
- It decomposes (Murphy decomposition) into **reliability minus resolution plus uncertainty**, where
 uncertainty is `p(1-p)` for base rate `p`. With `p = 0.001`, uncertainty is 0.000999, so **the raw
 Brier score is dominated by the base rate and is nearly identical for a useful model and for a
 constant predictor**. Reporting a raw Brier score at 0.1% prevalence is therefore uninformative.
- The fix is the **Brier Skill Score**, `BSS = 1 - BS_model / BS_reference`, with the reference being
 the constant base-rate predictor. Report BSS, not BS. **Mark as UNVERIFIED against a specific
 primary source in this review**: I did not locate a single canonical citation for the BSS
 recommendation in the wearable-health literature during this search, so cite a general forecasting
 reference if you use it.

**Minimum sample size for external validation.** Riley et al., "Minimum sample size for external
validation of a clinical prediction model with a binary outcome", Statistics in Medicine 2021
([DOI 10.1002/sim.9025](https://doi.org/10.1002/sim.9025)) gives the formal machinery. The
practical takeaway is the same as above: at 20 to 50 events you are below any recommended threshold
for calibration assessment.

**Reporting standard to follow:** TRIPOD+AI, BMJ 2024
([PMC11019967](https://pmc.ncbi.nlm.nih.gov/articles/PMC11019967/),
[DOI 10.1136/bmj-2023-078378](https://doi.org/10.1136/bmj-2023-078378)). Citing that you followed
TRIPOD+AI is cheap and buys a lot of credibility in a healthcare-AI course.

---

## 5. Recommended metric definitions for an early-warning system, precisely stated

These are written so they can be dropped into a report and implemented without ambiguity.

### 5.1 Primitives

Let each user `u` contribute a continuous observation period. Let the ground truth be a set of
**episodes** `E = {e_1, ..., e_m}`, where episode `e_i` is characterised by an **onset time**
`t_onset(e_i)` (for infection studies, the self-reported symptom-onset date) and, optionally, a
**resolution time** `t_end(e_i)`.

Let the detector emit a binary alert per **decision epoch**. **Fix the decision epoch to one day**
(this matches the alerting cadence of every published wearable system and matches what a user would
tolerate). Let `A(u)` be the set of alerting days for user `u`.

**Definition 1 (Alert event).** An **alert event** is a maximal run of consecutive alerting days.
This is the debouncing unit. Following Alavi, require **a minimum run length of 2 days** for an
alert event to count, and report results at run lengths 1, 2 and 3
([PMC8240687](https://pmc.ncbi.nlm.nih.gov/articles/PMC8240687/)).

**Definition 2 (Detection window).** For episode `e`, the detection window is
`W(e) = [t_onset(e) - L_max, t_onset(e) + L_grace]`.
Set **`L_max = 7 days`** and **`L_grace = 1 day`** as the primary analysis, and pre-register a
sensitivity analysis at `L_max` in {3, 5, 7, 10, 14}. Justification for the shape: the PhysioNet
2019 sepsis utility function uses a bounded window with a too-early penalty
([challenge page](https://physionet.org/content/challenge-2019/1.0.0/)); the maximum published lead
times in this domain are 9 days (Mishra) so a 7-day primary window is neither generous nor
restrictive.

**Definition 3 (Episode detected).** Episode `e` is **detected** if at least one alert event has its
**first** alerting day inside `W(e)`. Using the first day, not any day, is what makes lead time
well defined.

**Definition 4 (Lead time).** For a detected episode, `lead(e) = t_onset(e) - t_firstalert(e)`,
in days, positive meaning early. **Report the median, the interquartile range and the full sorted
list of per-episode lead times, and state explicitly that these are conditioned on detection.**

**Definition 5 (False alert event).** An alert event whose first day falls in no `W(e)` for any
episode `e` of that user.

### 5.2 The metrics to report

Report all seven. They take five minutes each and they close off every avenue of attack.

1. **Episode-level recall (sensitivity)** = `|detected episodes| / |episodes|`. With a
 **Clopper-Pearson exact 95% confidence interval**, because the count is small.
2. **Lead-time distribution**: median, IQR, min, max, and the full per-episode list in an appendix.
3. **False alert rate**, in two units:
 - **alert events per user-week of monitored (non-episode) time**, and
 - **fraction of person-days alerting**.
 Both units appear in the literature (Mishra used alarms per 30 days, Alavi used per person-day
 specificity), so reporting both makes your numbers directly comparable to theirs.
4. **Number needed to evaluate (NNE)** = `1 / PPV` at the operating threshold, computed at
 **event level**, following Wong et al.
 ([PMC8218233](https://pmc.ncbi.nlm.nih.gov/articles/PMC8218233/)). This is the number a
 non-technical reader actually understands.
5. **Threshold-free curve metric: AUPRC at the day level, and VUS-PR.** AUPRC because it is the
 PR-family metric that survived the Lyu stress test; VUS-PR because TSB-AD names it the most
 reliable measure ([TSB-AD](https://github.com/TheDatumOrg/TSB-AD)). Implementation:
 `sklearn.metrics.average_precision_score` and `vus` v0.0.6
 ([GitHub](https://github.com/TheDatumOrg/VUS)).
 **Always print the prevalence next to the AUPRC**, because AUPRC's no-skill baseline *is* the
 prevalence. Homekit2020 does exactly this, reporting "3.9% precision at k = 0.05%, a 100x lift
 over the baseline prevalence of 0.036%"
 ([PMLR v209](https://proceedings.mlr.press/v209/merrill23b.html)).
6. **Precision at k%**, that is, precision among the model's k% most confident days, with the
 random baseline (equal to prevalence) and an oracle drawn on the same axes. This is the
 Homekit2020 presentation and it is the honest way to show usefulness at extreme imbalance.
7. **A lead-time-weighted single number, if you want one**: implement the PhysioNet 2019 normalised
 utility with your own `L_max` and `L_grace` and report `U_normalized`. State that 0 means "never
 alert" and 1 means "optimal".

### 5.3 The metrics not to report, and what to say instead

| Do not report | Why | Report instead |
|---|---|---|
| Point-adjusted F1 | Random scores reach 0.969 ([arXiv:2109.05257](https://arxiv.org/abs/2109.05257)) | Episode-level recall + false alerts per user-week |
| Point-wise accuracy | At 0.1% prevalence, "always healthy" scores 99.9% | AUPRC with prevalence stated |
| Point-wise F1 at a single tuned threshold | Threshold shopping | AUPRC / VUS-PR plus one clearly-labelled operating point |
| A single best-of-N seed result | Affiliation-F1 reaches 0.98 at N=41 ([arXiv:2607.11969](https://arxiv.org/abs/2607.11969)) | Single-run scores, with N disclosed |
| A calibration curve on 30 events | Needs ~200 events per class ([PMC6912996](https://pmc.ncbi.nlm.nih.gov/articles/PMC6912996/)) | Observed-to-expected ratio only, with an explicit statement that finer calibration is not estimable |
| Raw Brier score at 0.1% prevalence | Dominated by base-rate uncertainty | Brier Skill Score against the base-rate predictor |

### 5.4 The two baselines you must beat, and must show

1. **A random detector matched on alert rate.** Generate alerts at the same per-day rate as your
 detector, uniformly at random, 1,000 times, and report the distribution of episode-level recall.
 This is the direct answer to Kim et al. and it takes ten lines.
2. **A trivial detector.** "Alert whenever today's resting heart rate exceeds the person's all-time
 median by 4 bpm" with no windowing, no decomposition and no debouncing. Wu and Keogh's triviality
 critique ([arXiv:2009.13807](https://arxiv.org/abs/2009.13807)) exists precisely because papers
 omit this. If your sophisticated method does not beat it, that *is* the finding, and reporting it
 honestly is worth more marks than hiding it.

---

## 6. How to evaluate with very few positive episodes (20 to 50)

The honest answer is: **mostly descriptively, with exact intervals, and with an explicit statement
that the study is underpowered for ranking methods.** There is good precedent for saying this out
loud.

### 6.1 What the field actually does

**Homekit2020 is the best worked example** and its evaluation section is worth copying almost
verbatim ([PMLR v209, Section 4.3](https://proceedings.mlr.press/v209/merrill23b.html)):

- They state the imbalance explicitly: **1:2,760 in their dataset**, comparable to the CDC's 10%
 annual symptomatic influenza risk which implies 1:3,650 at the day level.
- They give the statistical reason ranking is hard: **under the DeLong test the variance of the
 difference in AUCs is proportional to `1 / ((N - m) * m)`**, where `m` is the number of positives,
 so the variance is maximised as `m` shrinks toward 1
 ([DeLong et al. 1988](https://doi.org/10.2307/2531595)).
- Their solution is **hierarchical bootstrapping**: resample both the model list and the test data,
 200 times, take the 2.5th and 97.5th percentiles. This "relaxes the normal assumption of a
 t-distribution" and gives tighter bounds than averaging per-model bootstrap CIs.
- For **ranking across tasks** they use **critical difference diagrams**: Friedman's test for the
 null that models are equivalent, then pairwise Wilcoxon signed-rank tests, with a thick line
 connecting models that are not significantly different
 ([Brazdil and Soares 2000](https://doi.org/10.1007/3-540-45164-1_9);
 [Demsar 2006](https://www.jmlr.org/papers/v7/demsar06a.html)).
- **They explicitly refuse to compare classifiers on individual tasks**: "the substantial class
 imbalance inherent in these data limits comparisons between classifiers on individual tasks".

### 6.2 Concrete recipe for 20 to 50 episodes

1. **Exact binomial (Clopper-Pearson) confidence intervals for episode-level recall.** With 26 of 32
 detected, the point estimate is 81.3% and the exact 95% CI is approximately 63.6% to 92.8%.
 `scipy.stats.binomtest(26, 32).proportion_ci(method='exact')`. **Show this interval next to every
 sensitivity claim.** It immediately tells the reviewer you know the study is small.
2. **Cluster bootstrap over users, not over days.** Resample *users* with replacement and recompute
 every metric. Days within a user are not independent, so bootstrapping days will give you
 fraudulently narrow intervals.
3. **Leave-one-user-out for anything that involves fitting.** With 32 positives, any train/test split
 is dominated by which episodes land where.
4. **Permutation test for "is this better than chance".** Permute the episode onset dates within each
 user (preserving the alert series) 10,000 times and compute the null distribution of episode-level
 recall. This directly tests "could my detector have got this recall by alerting at this rate at
 random times", which is the reviewer's real question.
5. **Report the raw contingency counts.** With 32 episodes you can and should print the full table:
 detected / not detected, per episode, with lead time. Aggregate statistics hide too much at this
 sample size.
6. **Say the sentence.** Something like: "With 32 positive episodes, the 95% confidence interval on
 sensitivity spans 29 percentage points. This study is powered to establish that the signal exists
 and to characterise the false-alarm rate; it is not powered to rank detector variants against one
 another, and no such ranking is claimed." A reviewer cannot attack a limitation you have already
 stated more precisely than they would have.

### 6.3 What not to do

- Do not report a 4-decimal-place F1. Precision beyond two significant figures is not supported by
 32 events.
- Do not run a hyperparameter sweep and report only the best configuration. If you sweep, report the
 full sweep, because best-of-N inflation is now a documented and testable failure
 ([arXiv:2607.11969](https://arxiv.org/abs/2607.11969)).
- Do not compute a per-point AUROC over hundreds of thousands of person-days and present it as if it
 were the headline. It will be high and it will mean nothing.

---

## 7. Evaluating when the ground truth for the claim does not exist

This is the hard case for an *agentic* early-warning system: the claim is not just "the heart rate
was anomalous" (for which there is a proxy ground truth) but something like "the agent asked the
right clarifying question", "the agent correctly attributed the anomaly to alcohol rather than
infection", or "the agent's escalation policy was appropriate". No dataset labels those.

Four established strategies, in descending order of how defensible they are.

### 7.1 Simulator-as-oracle, with a regulatory precedent

**The strongest precedent in all of health monitoring** is the UVA/Padova Type 1 Diabetes simulator,
which the FDA accepted in January 2008 as a **substitute for animal trials** in the pre-clinical
testing of closed-loop insulin control algorithms
([Kovatchev, Breton, Dalla Man, Cobelli, "In silico preclinical trials: a proof of concept in
closed-loop control of type 1 diabetes", J Diabetes Sci Technol 2009,
PMC2681269](https://pmc.ncbi.nlm.nih.gov/articles/PMC2681269/); methodology companion
[PMC2771529](https://pmc.ncbi.nlm.nih.gov/articles/PMC2771529/)). Two decades later, artificial
pancreas papers still routinely evaluate "in silico" on this simulator and it is accepted at review
(for example [in silico evaluation of pramlintide dosing algorithms, Comput Biol Med 2025,
DOI 10.1016/j.compbiomed.2025.110447](https://doi.org/10.1016/j.compbiomed.2025.110447)).

**How to use this precedent.** Build an explicit generative model of a user: a baseline circadian
resting-heart-rate process, a confounder process (alcohol on Friday, hard training on Tuesday,
poor sleep), and an illness process with a known onset time and a known physiological signature.
Then the ground truth for "did the agent attribute correctly" **exists by construction**, because
you wrote it. Cite the UVA/Padova precedent as the reason this is a legitimate evaluation and not
a toy. Be explicit that simulator results are an upper bound on real-world performance.

Practical generators: `NeuroKit2` for realistic PPG/ECG traces with controlled heart rate,
`wearipedia` for schema-faithful device payloads, plus a hand-written additive model for the
resting-heart-rate day series. Cite the limitations review
([arXiv:2505.14206](https://arxiv.org/abs/2505.14206)) so you are seen to know the caveats.

### 7.2 Semi-synthetic: inject a known perturbation into real data

Take real, healthy, confounder-annotated wearable data (PMData, TILES-2018, LifeSnaps) and inject a
synthetic illness signature with a known onset. The background is real, so the noise, missingness,
diurnal structure and confounders are all authentic; the event is synthetic, so the ground truth is
exact.

Precedents:

- **Van Der Donckt et al.** inject block-structured gaps that simulate non-wear into gap-free real
 wearable data and report feature-value spread as a function of retention ratio
 ([Sci Rep 2024, PMC11289092](https://pmc.ncbi.nlm.nih.gov/articles/PMC11289092/)). Same technique,
 different perturbation.
- **The UCR Anomaly Archive** is exactly this construction at scale: real signals with carefully
 controlled, curated anomalies, built because the alternative benchmarks were shown to be flawed
 ([Wu and Keogh, arXiv:2009.13807](https://arxiv.org/abs/2009.13807)).
- **TSB-AD** re-curated 1,070 series by combining "human perception and model interpretation",
 which is the same acknowledgement that labels have to be manufactured carefully
 ([TSB-AD](https://github.com/TheDatumOrg/TSB-AD)).

**Design the injection from published effect sizes, not from imagination.** NightSignal's thresholds
tell you the effect size that matters: **3 to 4 bpm elevation in overnight resting heart rate**,
sustained over a **red-alert cluster averaging 4.3 days**
([PMC8240687](https://pmc.ncbi.nlm.nih.gov/articles/PMC8240687/)). Injecting a +4 bpm, 4-day
overnight-RHR bump into PMData and asking whether the agent distinguishes it from the participant's
genuine alcohol-and-hard-training days is a well-founded, citable experimental design, and it is the
single strongest evaluation idea in this document for a project with no illness-labelled
confounder-annotated data.

**Report the sensitivity of your conclusions to the injected effect size.** Sweep the bump amplitude
from 1 to 8 bpm and the duration from 1 to 7 days and report a detection heat map. That turns
"we made up the ground truth" into "we characterised the detection boundary", which is a much
stronger claim.

### 7.3 Simulated oracles, as the active learning community does it

The active learning literature has evaluated query policies without real annotators for thirty
years, by the simple device of taking a **fully labelled pool, hiding the labels, and revealing a
label only when the policy queries it**. The policy is then scored by its learning curve
(performance versus number of queries). This is the standard protocol in Settles' survey
([Burr Settles, "Active Learning Literature Survey", University of Wisconsin-Madison Computer
Sciences Technical Report 1648, 2009](https://minds.wisconsin.edu/handle/1793/60660)).

**The community's own critique of that protocol is what you should cite**, because it is the exact
critique a reviewer will make of your agent evaluation:

- The simulated oracle is **noiseless and never fatigues**, whereas real users mislabel and stop
 responding. Noisy-oracle and cost-sensitive variants exist precisely for this reason.
- Results are **highly sensitive to implementation details and random seeds**, and several
 reproducibility studies have found that reported active learning gains do not survive careful
 re-implementation (Munjal et al., "Towards Robust and Reproducible Active Learning Using Neural
 Networks", CVPR 2022, [arXiv:2002.09564](https://arxiv.org/abs/2002.09564)). **UNVERIFIED**: I did
 not fetch this paper during this search; verify the venue and claims before citing.
- Active learning induces a **non-i.i.d. sample**, so the usual estimators are biased; see
 Farquhar, Gal, Rainforth, "On Statistical Bias In Active Learning: How and When To Fix It",
 ICLR 2021 ([arXiv:2101.11665](https://arxiv.org/abs/2101.11665)). **UNVERIFIED**: also not fetched
 during this search.

**How this maps onto your project.** If the agent's job is to decide *when to ask the user a
question*, then the equivalent construction is: take a dataset that already contains dense daily
self-reports (PMData: 1,747 wellness reports, 1,569 daily reports over 16 users and 5 months; or
TILES-2018: daily EMA including alcohol and tobacco for 212 users over 10 weeks), **hide those
self-reports, and reveal one only when the agent chooses to ask**. Then score the agent on
(a) how many questions it needed, (b) how much its detection performance improved per question,
and (c) whether the revealed answers were the ones that actually explained the anomaly. **This is a
genuine simulated-oracle evaluation with a real oracle behind it**, which is strictly better than
inventing user responses with a language model, and it is the single most defensible design
available for the agentic part of this project.

### 7.4 Off-policy and counterfactual evaluation, and its known limits

If the claim is about a *policy* (when to alert, when to escalate) rather than a detector, the
principled framework is off-policy evaluation: estimate the value of a new policy from data
collected under a different one, using importance weighting or doubly-robust estimators.

**The essential caution for healthcare is Gottesman et al., "Guidelines for reinforcement learning
in healthcare", Nature Medicine 2019
([DOI 10.1038/s41591-018-0310-5](https://doi.org/10.1038/s41591-018-0310-5))**, which argues that
off-policy evaluation in health data is frequently unreliable because of limited overlap between
the logged and evaluated policies. **For a course project with 32 episodes, off-policy
evaluation is not viable.** Mention it as the principled approach and explain why you did not use
it; that is a stronger move than attempting it badly.

### 7.5 The framing to use in the report

State the evaluation hierarchy explicitly, from most to least grounded:

| Claim | Ground truth source | Status |
|---|---|---|
| "The physiological anomaly occurred" | Real labelled episodes (Stanford, 32 cases) | **Grounded**, with exact CIs |
| "The alert rate in healthy periods is X" | Real unlabelled data (PMData, TILES) | **Grounded**, no labels required |
| "The system detects an illness-shaped perturbation" | Semi-synthetic injection into real backgrounds | **Constructed ground truth**, effect size swept |
| "The agent asks the right question at the right time" | Hidden real self-reports revealed on query | **Simulated oracle over real answers** |
| "The agent improves user outcomes" | None available | **Not claimed.** State this |

Putting that table in the report is itself the defence. The failure mode that gets projects torn
apart is claiming row 5 while only evidencing row 1.

---

## 8. Bibliography

All URLs checked on 2026-08-30.

### 8.1 Datasets

- Stanford COVID-19-Wearables archive: https://storage.googleapis.com/gbsc-gcp-project-ipop_public/COVID-19/COVID-19-Wearables.zip
- Mishra T, et al. Pre-symptomatic detection of COVID-19 from smartwatch data. Nat Biomed Eng 2020. https://pmc.ncbi.nlm.nih.gov/articles/PMC9020268/ | https://doi.org/10.1038/s41551-020-00640-6
- Merrill MA, et al. Homekit2020: A Benchmark for Time Series Classification on a Large Mobile Sensing Dataset with Laboratory Tested Ground Truth of Influenza Infections. PMLR v209, 2023. https://proceedings.mlr.press/v209/merrill23b.html | code https://github.com/behavioral-data/Homekit2020 | data https://www.synapse.org/Synapse:syn51476306
- CovIdentify Dataset v1.0.0, PhysioNet. https://physionet.org/content/covidentify/1.0.0/ | DOI 10.13026/ncq1-vp79
- Yfantidou S, et al. LifeSnaps, a 4-month multi-modal dataset. Sci Data 2022. https://pmc.ncbi.nlm.nih.gov/articles/PMC9622868/ | data https://zenodo.org/records/7229547
- Thambawita V, et al. PMData: A Sports Logging Dataset. ACM MMSys 2020. https://doi.org/10.1145/3339825.3394926 | data https://datasets.simula.no/pmdata/ | mirror https://osf.io/vx4bk
- Mundnich K, et al. TILES-2018, a longitudinal physiologic and behavioral data set of hospital workers. Sci Data 2020. https://pmc.ncbi.nlm.nih.gov/articles/PMC7567859/ | data https://tiles-data.isi.edu/
- Xu X, et al. GLOBEM Dataset v1.1, PhysioNet. https://physionet.org/content/globem/1.1/ | code https://github.com/UW-EXP/GLOBEM
- Rossi A, et al. MMASH: Multilevel Monitoring of Activity and Sleep in Healthy People, PhysioNet. https://physionet.org/content/mmash/1.0.0/ | DOI 10.13026/cerq-fc86
- AI-READI Consortium. AI-READI Flagship Dataset. https://fairhub.io/datasets/2 | docs https://docs.aireadi.org/ | DOI 10.60775/fairhub.3
- All of Us Research Program. The All of Us Research Program's wearables dataset. Nat Med 2026. https://pmc.ncbi.nlm.nih.gov/articles/PMC13278962/ | DOI 10.1038/s41591-026-04352-3
- All of Us. Resources for Using Fitbit Data. https://support.researchallofus.org/hc/en-us/articles/20281023493908-Resources-for-Using-Fitbit-Data
- All of Us. Controlled CDR Directory. https://support.researchallofus.org/hc/en-us/articles/4616869437204
- Doherty A, et al. Large Scale Population Assessment of Physical Activity Using Wrist Worn Accelerometers: The UK Biobank Study. PLOS ONE 2017. https://pmc.ncbi.nlm.nih.gov/articles/PMC5287488/ | showcase https://biobank.ndph.ox.ac.uk/showcase/label.cgi?id=1008 | code https://github.com/activityMonitoring/biobankAccelerometerAnalysis
- BIG IDEAs Lab Glycemic Variability and Wearable Device Data, PhysioNet. https://physionet.org/content/big-ideas-glycemic-wearable/1.1.2/ | DOI 10.13026/zthx-5212
- A continuous real-world dataset comprising wearable-based heart rate variability alongside sleep diaries. https://pmc.ncbi.nlm.nih.gov/articles/PMC12375003/ | data https://doi.org/10.6084/m9.figshare.28509740
- Physiological and emotional assessment of college students during the 2020 COVID-19 lockdown. https://pmc.ncbi.nlm.nih.gov/articles/PMC11637128/ | data https://doi.org/10.7280/D1WH6T
- WESAD, UCI ML Repository dataset 465. https://archive.ics.uci.edu/dataset/465/wesad+wearable+stress+and+affect+detection
- PPG-DaLiA, UCI ML Repository dataset 495. https://archive.ics.uci.edu/dataset/495/ppg+dalia
- Daphnet Freezing of Gait, UCI ML Repository dataset 245. https://archive.ics.uci.edu/dataset/245/daphnet+freezing+of+gait | DOI 10.24432/C56K78
- SWELL heart rate variability (Kaggle mirror). https://www.kaggle.com/datasets/qiriro/swell-heart-rate-variability-hrv
- PhysioNet wearable-sensor dataset index. https://physionet.org/content/?topic=wearable
- Wiedermann M, et al. Evidence for positive long- and short-term effects of vaccinations against COVID-19 in wearable sensor metrics (German Corona Data Donation). PNAS Nexus 2023. https://pmc.ncbi.nlm.nih.gov/articles/PMC10368316/
- Mason AE, et al. Detection of COVID-19 using multimodal data from a wearable device: results from the first TemPredict Study. Sci Rep 2022. https://doi.org/10.1038/s41598-022-07314-0
- Quer G, et al. Wearable sensor data and self-reported symptoms for COVID-19 detection. Nat Med 2021. https://doi.org/10.1038/s41591-020-1123-x
- Snyder Lab Long COVID Study Dataset, Stanford Digital Repository. https://purl.stanford.edu/cb174pb4851

### 8.2 Detection methods and wearable applications

- Bogu GK, Snyder MP. AnomalyDetect (RHR-AD, HROS-AD, online RHRAD). https://github.com/gireeshkbogu/AnomalyDetect
- Bogu GK, Snyder MP. LAAD (LSTM autoencoder anomaly detection). https://github.com/gireeshkbogu/LAAD
- Alavi A, et al. Real-time alerting system for COVID-19 and other stress events using wearable data. Nat Med 2022. https://pmc.ncbi.nlm.nih.gov/articles/PMC8240687/
- Nestor B, et al. (Sci Rep 2022) Machine learning-based optimization of pre-symptomatic COVID-19 detection through smartwatch. https://pmc.ncbi.nlm.nih.gov/articles/PMC9097889/ | DOI 10.1038/s41598-022-11329-y
- Alam MAU, et al. PCovNet: A presymptomatic COVID-19 detection framework using deep learning on wearables data. Comput Biol Med 2022. https://pmc.ncbi.nlm.nih.gov/articles/PMC9170596/
- PCovNet+: A CNN-VAE anomaly detection framework with LSTM embeddings. Eng Appl Artif Intell 2023. https://pmc.ncbi.nlm.nih.gov/articles/PMC10047244/
- Statistical process control on passive sensing to predict bipolar episodes. J Psychopathol Clin Sci 2025. https://doi.org/10.1037/abn0001002
- Epileptic Seizure Prediction Based on Multivariate Statistical Process Control of HRV Features. IEEE TBME 2016. https://doi.org/10.1109/tbme.2015.2512276
- Adaptive change detection in heart rate trend monitoring in anesthetized children. IEEE TBME 2006. https://doi.org/10.1109/tbme.2006.877107
- Adams RP, MacKay DJC. Bayesian Online Changepoint Detection. 2007. https://arxiv.org/abs/0710.3742
- Gao C, et al. Approaches for assessing circadian rest-activity patterns using actigraphy in cohort and population-based studies. Curr Sleep Med Rep 2023. https://pmc.ncbi.nlm.nih.gov/articles/PMC12829919/
- Van Der Donckt J, et al. Mitigating data quality challenges in ambulatory wrist-worn wearable monitoring. Sci Rep 2024;14:17545. https://pmc.ncbi.nlm.nih.gov/articles/PMC11289092/
- Hilden P, et al. How many days are needed? Measurement reliability of wearable device data to assess physical activity. PLOS ONE 2023. https://pmc.ncbi.nlm.nih.gov/articles/PMC9956594/
- Long-term changes in wearable sensor data in people with and without Long Covid. npj Digit Med 2024. https://pmc.ncbi.nlm.nih.gov/articles/PMC11399345/

### 8.3 Python packages (versions verified on PyPI, 2026-08-30)

| Package | Version | Purpose | URL |
|---|---|---|---|
| `ruptures` | 1.1.10 | Offline change point detection | https://github.com/deepcharles/ruptures/ |
| `bayesian-changepoint-detection` | 0.2.dev1 | BOCPD | https://github.com/hildensia/bayesian_changepoint_detection |
| `changefinder` | 0.03 | Online SDAR change point | https://pypi.org/project/changefinder/ |
| `river` | 0.26.1 | Online ML, drift detectors (ADWIN, Page-Hinkley) | https://riverml.xyz/ |
| `pyod` | 3.6.5 | Outlier detection (IForest, ECOD, autoencoders) | https://github.com/yzhao062/pyod |
| `alibi-detect` | 0.13.0 | Outlier and drift detection | https://github.com/SeldonIO/alibi-detect |
| `statsmodels` | 0.15.0 | `seasonal_decompose`, STL, EWMA | https://www.statsmodels.org/ |
| `CosinorPy` | 3.1 | Cosinor rhythmometry | https://github.com/mmoskon/CosinorPy |
| `pyActigraphy` | 1.2.2 | Actigraphy, IS/IV/RA/L5/M10, non-wear | https://github.com/ghammad/pyActigraphy |
| `stumpy` | 1.14.1 | Matrix profile, streaming discords (DAMP) | https://github.com/stumpy-dev/stumpy |
| `salesforce-merlion` | 2.0.4 | Time-series anomaly detection framework | https://github.com/salesforce/Merlion |
| `darts` | 0.46.1 | Forecasting + `darts.ad` anomaly module | https://unit8co.github.io/darts/ |
| `aeon` | 1.5.0 | Time-series ML toolkit | https://www.aeon-toolkit.org |
| `sktime` | 1.1.0 | Time-series ML framework | https://www.sktime.net |
| `orion-ml` | 0.7.1 | Unsupervised time-series anomaly detection | https://github.com/sintel-dev/Orion |
| `adtk` | 0.6.2 | Rule-based anomaly detection toolkit | https://github.com/arundo/adtk |
| `prts` | 1.0.0.3 | Range-based precision and recall (Tatbul) | https://github.com/CompML/PRTS |
| `vus` | 0.0.6 | VUS-ROC and VUS-PR | https://github.com/TheDatumOrg/VUS |
| `TSB-AD` | on PyPI | Benchmark + `get_metrics` evaluation suite | https://github.com/TheDatumOrg/TSB-AD |
| (repo only) | n/a | Affiliation precision and recall | https://github.com/ahstat/affiliation-metrics-py |
| (repo only) | n/a | PATE metric | https://github.com/Raminghorbanii/PATE |
| (repo only) | n/a | PA%K reference implementation | https://github.com/tuslkkk/tadpak |
| `pyspc` | 0.4 | SPC control charts | https://github.com/carlosqsilva/pyspc |
| `banpei` | 0.1.2 | CUSUM, SST change detection | https://pypi.org/project/banpei/ |
| `scikit-digital-health` | 0.17.17 | Accelerometry processing, non-wear | https://pypi.org/project/scikit-digital-health/ |
| `accelerometer` | 7.5.0 | UK Biobank accelerometry pipeline | https://github.com/activityMonitoring/biobankAccelerometerAnalysis |
| `neurokit2` | current | PPG/ECG/EDA simulation and processing | https://github.com/neuropsychology/NeuroKit |
| `wearipedia` | 0.1.7 | Wearable device schemas + synthetic data | https://pypi.org/project/wearipedia/ |
| `flirt` | current | Wearable feature generation (Empatica-oriented) | https://pypi.org/project/flirt/ |

### 8.4 Evaluation methodology

- Kim S, Choi K, Choi HS, Lee B, Yoon S. Towards a Rigorous Evaluation of Time-series Anomaly Detection. AAAI 2022. https://arxiv.org/abs/2109.05257 | https://ojs.aaai.org/index.php/AAAI/article/view/20680 | code https://github.com/tuslkkk/tadpak
- Wu R, Keogh EJ. Current Time Series Anomaly Detection Benchmarks are Flawed and are Creating the Illusion of Progress. IEEE TKDE 2021. https://arxiv.org/abs/2009.13807
- Liu Q, Paparrizos J. The Elephant in the Room: Towards A Reliable Time-Series Anomaly Detection Benchmark. NeurIPS 2024. https://github.com/TheDatumOrg/TSB-AD | https://thedatumorg.github.io/TSB-AD/
- Tatbul N, Lee TJ, Zdonik S, Alam M, Gottschlich J. Precision and Recall for Time Series. NeurIPS 2018. https://arxiv.org/abs/1803.03639 | https://people.csail.mit.edu/tatbul/publications/NeurIPS18.pdf
- Huet A, Navarro JM, Rossi D. Local Evaluation of Time Series Anomaly Detection Algorithms. KDD 2022. https://arxiv.org/abs/2206.13167 | https://doi.org/10.1145/3534678.3539339
- Paparrizos J, Boniol P, Palpanas T, Tsay RS, Elmore A, Franklin MJ. Volume Under the Surface. PVLDB 15(11):2774-2787, 2022. https://www.vldb.org/pvldb/vol15/p2774-paparrizos.pdf | journal version https://link.springer.com/article/10.1007/s00778-025-00907-x
- Paparrizos J, et al. TSB-UAD: An End-to-End Benchmark Suite for Univariate Time-Series Anomaly Detection. PVLDB 15(8):1697-1711, 2022. https://github.com/TheDatumOrg/TSB-UAD
- Ghorbani R, Reinders MJT, Tax DMJ. PATE: Proximity-Aware Time series anomaly Evaluation. KDD 2024. https://arxiv.org/abs/2405.12096 | code https://github.com/Raminghorbanii/PATE
- Hwang WS, et al. Time-Series Aware Precision and Recall for Anomaly Detection. CIKM 2019. https://doi.org/10.1145/3357384.3358118
- Hwang WS, et al. "Do you know existing accuracy metrics overrate time-series anomaly detections?" SAC 2022. https://doi.org/10.1145/3477314.3507024
- Lyu Z. Did We Actually Fix It? An Independent Adversarial Stress-Test of Post-Point-Adjustment Evaluation Metrics for Time-Series Anomaly Detection. 2026. https://arxiv.org/abs/2607.11969
- Yang K, Liu J, Song Y, Yang S, Zhou Y. A Problem-Oriented Taxonomy of Evaluation Metrics for Time Series Anomaly Detection. 2025. https://arxiv.org/abs/2511.18739
- Sørbø S, Ruocco M. Navigating the Metric Maze: A Taxonomy of Evaluation Metrics for Anomaly Detection in Time Series. 2023. https://arxiv.org/abs/2303.01272
- Formally Exploring Time-Series Anomaly Detection Evaluation Metrics. 2025. https://arxiv.org/abs/2510.17562
- CCE: Confidence-Consistency Evaluation for Time Series Anomaly Detection. 2025. https://arxiv.org/abs/2509.01098
- Lavin A, Ahmad S. Evaluating Real-time Anomaly Detection Algorithms: the Numenta Anomaly Benchmark. 2015. https://arxiv.org/abs/1510.03336
- Ahmad S, Lavin A, Purdy S, Agha Z. Unsupervised real-time anomaly detection for streaming data. Neurocomputing 2017. https://doi.org/10.1016/j.neucom.2017.04.070 | benchmark https://github.com/numenta/NAB
- PhysioNet/CinC Challenge 2019: Early Prediction of Sepsis from Clinical Data (utility function). https://physionet.org/content/challenge-2019/1.0.0/
- Wong A, et al. External Validation of a Widely Implemented Proprietary Sepsis Prediction Model in Hospitalized Patients. JAMA Intern Med 2021. https://pmc.ncbi.nlm.nih.gov/articles/PMC8218233/ | DOI 10.1001/jamainternmed.2021.2626
- Van Calster B, McLernon DJ, van Smeden M, Wynants L, Steyerberg EW. Calibration: the Achilles heel of predictive analytics. BMC Med 2019;17:230. https://pmc.ncbi.nlm.nih.gov/articles/PMC6912996/
- Riley RD, et al. Minimum sample size for external validation of a clinical prediction model with a binary outcome. Stat Med 2021. https://doi.org/10.1002/sim.9025
- Collins GS, et al. TRIPOD+AI statement. BMJ 2024. https://pmc.ncbi.nlm.nih.gov/articles/PMC11019967/ | DOI 10.1136/bmj-2023-078378
- DeLong ER, DeLong DM, Clarke-Pearson DL. Comparing the areas under two or more correlated receiver operating characteristic curves. Biometrics 1988. https://doi.org/10.2307/2531595
- Demsar J. Statistical Comparisons of Classifiers over Multiple Data Sets. JMLR 2006. https://www.jmlr.org/papers/v7/demsar06a.html

### 8.5 Evaluation without ground truth

- Kovatchev BP, Breton M, Dalla Man C, Cobelli C. In silico preclinical trials: a proof of concept in closed-loop control of type 1 diabetes. J Diabetes Sci Technol 2009. https://pmc.ncbi.nlm.nih.gov/articles/PMC2681269/
- Kovatchev BP, et al. In silico preclinical trials: methodology and engineering guide to closed-loop control in type 1 diabetes mellitus. J Diabetes Sci Technol 2009. https://pmc.ncbi.nlm.nih.gov/articles/PMC2771529/
- Gottesman O, et al. Guidelines for reinforcement learning in healthcare. Nat Med 2019. https://doi.org/10.1038/s41591-018-0310-5
- Settles B. Active Learning Literature Survey. UW-Madison CS Technical Report 1648, 2009. https://minds.wisconsin.edu/handle/1793/60660
- Munjal P, et al. Towards Robust and Reproducible Active Learning Using Neural Networks. CVPR 2022. https://arxiv.org/abs/2002.09564 **(UNVERIFIED: not fetched during this review)**
- Farquhar S, Gal Y, Rainforth T. On Statistical Bias In Active Learning: How and When To Fix It. ICLR 2021. https://arxiv.org/abs/2101.11665 **(UNVERIFIED: not fetched during this review)**
- Challenges and Limitations of Generative AI in Synthesizing Wearable Sensor Data. 2025. https://arxiv.org/abs/2505.14206

---

## 9. Open items and things I could not verify

1. **Homekit2020 participant count**: the paper states 5,196 in one place and 5,034 in another. Both
 numbers are in the published PDF. Resolve with the authors if it matters.
2. **Homekit2020 survey field list**: the CRF PDF (`syn25378453`) requires a Synapse login. Whether
 the baseline questionnaire contains alcohol, medication or menstrual items is **UNVERIFIED**.
3. **All of Us eligibility for a non-US institution** is **UNVERIFIED**. Check before planning around it.
4. **AI-READI survey instruments** could not be enumerated from the public documentation, so its
 confounder coverage is **PARTIAL / UNVERIFIED**. Note also that the FAIRhub page states the
 repository is under review for possible modification.
5. **DAPHNET sampling rate and participant count** are not stated on the UCI landing page.
6. **SWELL-KW** participant count, duration and licence were not confirmed from a primary source.
7. **Brier Skill Score recommendation** for rare-event calibration is stated from first principles,
 not from a wearable-specific citation. **UNVERIFIED**.
8. **Two active-learning critique papers** (Munjal et al., Farquhar et al.) were identified by title
 only and not fetched. Verify before citing.
9. **Stanford COVID-19-Wearables licence** is not stated anywhere on the hosting bucket. Treat as
 "released for research by the authors" and cite the paper's data availability statement rather
 than claiming a licence.
10. **DETECT and TemPredict**: no open download located. Both are marked E in the table on the basis
 of absence of evidence rather than an explicit refusal statement, except for TemPredict where the
 lack of raw-data sharing is documented.


