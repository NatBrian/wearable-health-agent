# F1 — Clinical & Academic Wearable Illness/Infection Detection Studies

Research territory: peer-reviewed wearable infection / illness early-warning systems.
Compiled 2026-08-30. Every factual claim below carries a URL. Anything I could not
confirm against a primary source is marked **UNVERIFIED** explicitly.

Verification method: primary sources only — Nature/PLOS/JAMA/Oxford article pages, PMC
full text, Crossref and Europe PMC metadata APIs, the GitHub REST API, and direct HTTP
range requests against the actual dataset ZIP files (I read the ZIP central directories
to enumerate real file contents rather than trusting the papers' prose).

---

## 1. Executive summary

1. **The headline citation in the prior notes was wrong.** Mishra et al. 2020 is
 DOI `10.1038/s41551-020-00640-6` (Nature Biomedical Engineering), not `s41598`.
 Everything else in that citation was right.
2. **The NightSignal performance numbers in the prior notes were fabricated or garbled.**
 Real numbers: NightSignal 80% sensitivity, CuSum 72%, RHRAD 69% — not 78/54/44.
3. **NightSignal is a 6-state DFA, not 4-state.** I read both the paper's Extended Data
 Fig. 3 image and the 674-line `nightsignal.py` source. States S0–S5, three alert
 colours (green/yellow/red), thresholds baseline+3 bpm (yellow) and baseline+4 bpm (red),
 where baseline = streaming median of nightly mean resting HR.
4. **The single most useful practical fact:** the Stanford MyPHD wearable data is an
 **open, unauthenticated, no-registration HTTP download**. Phase 2 is 5.54 GB
 (2,123 participants), Phase 1 is 378 MB (117 participants). I verified both with HTTP
 HEAD and enumerated their contents. This is by far the easiest real data to build on.
5. **But those open ZIPs contain heart rate and step counts only.** No temperature, no
 HRV, no respiratory rate, no SpO2, **no illness labels, and no confounder annotations**.
 The confounder surveys (alcohol, exercise, travel, stress, vaccination) were collected
 by Alavi et al. and are discussed in the paper, but they are *not* in the public download.
6. **Almost every other dataset is gated.** TemPredict/Oura is effectively closed (Oura's
 data use policy plus a DoD restriction on the classifier code). Scripps DETECT is
 "register and pledge, email the corresponding author". CovIdentify is on PhysioNet but
 needs credentialing + CITI training + a DUA. Warrior Watch has no data statement at all.
7. **Only one dataset I found has explicit confounder annotations: COVID-RED** (Ava
 bracelet, daily diary of alcohol/drug/medication use), and its download is gated behind
 a UMC Utrecht request form.
8. **The literature's most important result is the one nobody cites:** COVID-RED, the only
 large randomised controlled trial (n=17,825), found the wearable algorithm achieved
 93.8–99.2% sensitivity at **0.8–4.2% specificity**. In a real prospective deployment
 the algorithm essentially alerted everyone. This should temper every retrospective
 AUC in this field.
9. **The retrospective literature systematically flatters itself** through 21-day and
 45-day detection windows, subgroup selection ("participants with ≥28 days of prior
 data"), operating points tuned on the evaluation data, and reporting training-set
 metrics as headline results. Details in §6.
10. **No study in this territory uses an LLM, an agent, or RAG.** Fields J–M in the A–V
 schema are "No" for every single system. That is the gap this project sits in.
11. Personalisation is universally "individual streaming baseline over ~7–28 nights",
 not population norms. This is the one architectural lesson every paper agrees on.
12. Non-respiratory illness detection does exist and is credible: **IBD flares**
 (Hirten, Gastroenterology 2025, n=309, signals up to 7 weeks pre-flare),
 **malaria** (npj Digital Medicine 2026, rural Kenya, n=300), and **Lyme disease**
 (Li, PLoS Biology 2017) — though the Lyme dataset URL is now dead (HTTP 404).
13. Viral-challenge studies (Grzesiak, Temple) are the only ones with a *known* infection
 time. They report the best numbers (88–94%) on the smallest cohorts (n=17–31) with
 thresholds fitted on the same data.
14. Skin/dermal temperature does measurably help — but the one real number is
 **+4.9 percentage points AUC (0.770 → 0.819)** from Mason 2022, on the training set.
15. Nothing here is a deployable pretrained model. NightSignal and the Duke ITA model are
 the only genuinely runnable public artefacts, and NightSignal is a rules engine with
 no learned parameters at all.

---

## 2. Verification verdict table

| # | Claim as given in prior notes | Verdict | Correct version | Source |
|---|---|---|---|---|
| 1 | Mishra et al. (2020), *Pre-symptomatic detection of COVID-19 from smartwatch data*, Nat Biomed Eng 4:1208–1220. DOI 10.1038/**s41598**-020-00640-6 | **CORRECTED** | Title, journal, volume, pages and year are all correct. The DOI is wrong: it is `10.1038/`**`s41551`**`-020-00640-6`. PMID 33208926, PMCID PMC9020268. (`s41598` is Scientific Reports; `s41551` is Nat Biomed Eng.) | [nature.com/articles/s41551-020-00640-6](https://www.nature.com/articles/s41551-020-00640-6) · [Europe PMC record](https://europepmc.org/article/MED/33208926) |
| 2 | Alavi et al. (2022), *Real-time alerting system for COVID-19 and other stress events using wearable data*, Nat Med 28:175–184. DOI 10.1038/s41591-021-01593-2 | **VERIFIED** | Exactly correct. PMID 34845389, PMCID PMC8799466. | [nature.com/articles/s41591-021-01593-2](https://www.nature.com/articles/s41591-021-01593-2) · [PMC8799466](https://pmc.ncbi.nlm.nih.gov/articles/PMC8799466/) |
| 3a | "NightSignal: 78% sensitivity" | **CORRECTED** | **80%** — "Of the 84 participants who tested positive for COVID-19 (66 symptomatic and 18 asymptomatic), 67 received NightSignal alerts at or before symptom onset (pre-symptomatic cases) or diagnosis date (asymptomatic cases) for a sensitivity (TP rate) of 80%." Fitbit 77%, Apple Watch 83%. | [PMC8799466](https://pmc.ncbi.nlm.nih.gov/articles/PMC8799466/) |
| 3b | "3-day median lead time" | **VERIFIED** | "Pre-symptomatic signals were observed at a median of 3 days before symptom onset." Symptomatic cases only. | [PMC8799466](https://pmc.ncbi.nlm.nih.gov/articles/PMC8799466/) |
| 3c | "~0.3 false alerts per user-week" | **NOT FOUND (number not stated in the paper)** | The paper never expresses false alerts per user-week. It reports **1.15 alert days per person** for non-COVID events vs **3.42 alert days per person** for COVID cases, both over a **21-day window** (≈0.38 vs 1.14 alert-days per user-week if you divide, which the authors do not do). Separately it reports alert-day-level specificity of **87.7%** (87,124 TN / (87,124 TN + 12,186 FP)), which implies ≈0.86 false-alert days per user-week — inconsistent with the 1.15/21-day figure. Treat "0.3/user-week" as unsupported. | [PMC8799466](https://pmc.ncbi.nlm.nih.gov/articles/PMC8799466/) |
| 3d | "compared to 54% for CuSum and 44% for RHRAD" | **CORRECTED** | **CuSum 72% (29/40)** and **RHRAD 69% (29/42)**. Both were evaluated on Fitbit users only, because they need hourly-resolution data. Specificity: NightSignal 87.7%, RHRAD 87.7%, CuSum 83.7%. | [PMC8799466](https://pmc.ncbi.nlm.nih.gov/articles/PMC8799466/) |
| 4 | "NightSignal is a 4-state deterministic finite state machine" | **REFUTED** | **Six states.** Paper: "The state machine consists of six states … (S0, S1 and S2 labeled with green alert, S3 and S4 labeled with yellow alert and S5 labeled with red alert) and three symbols." Inputs: Aᵢ < Mᵢ+3, Aᵢ = Mᵢ+3, Aᵢ ≥ Mᵢ+4, where Aᵢ = mean overnight RHR for night i and Mᵢ = streaming median of those means up to night i. Confirmed independently by reading `images/NightSignal_DFA.png` and `nightsignal.py`. | [PMC8799466](https://pmc.ncbi.nlm.nih.gov/articles/PMC8799466/) · [NightSignal_DFA.png](https://github.com/StanfordBioinformatics/wearable-infection/blob/main/images/NightSignal_DFA.png) |
| 5 | "GitHub repository: StanfordBioinformatics/wearable-infection" | **VERIFIED** | Repo exists. Details in §3.2 / §5. Apache-2.0, 63 commits, last push **2021-09-20**, 16 stars, 8 forks, 1 open issue, not archived. Contains `nightsignal.py` (674 lines), `isolationforest/isolationforest.py`, `requirements.txt`, README, and sample CSVs for exactly **two** participants. Runnable. | [github.com/StanfordBioinformatics/wearable-infection](https://github.com/StanfordBioinformatics/wearable-infection) |
| 6a | "TemPredict/Oura: 82% sensitivity" | **VERIFIED, with a major caveat** | 82% is correct but it is measured on the **73-participant training set**, over a 21-day "DX region". | [nature.com/articles/s41598-022-07314-0](https://www.nature.com/articles/s41598-022-07314-0) |
| 6b | "63–80% specificity" | **MISLEADING CONFLATION** | These are two different cohorts. **63%** = specificity on the n=73 training set. **80%** = specificity on a separate n=**10** antibody-confirmed validation group (where sensitivity was 90%). Presenting it as a range implies a single reported interval; it is not. | [nature.com/articles/s41598-022-07314-0](https://www.nature.com/articles/s41598-022-07314-0) |
| 6c | "2.75 day lead time (51 ± 12 hours)" | **PARTLY CORRECTED — "51 ± 12 hours" NOT FOUND** | "2.75 days" is verified but it is **2.75 days before participants sought diagnostic testing (DX)**, not before symptom onset. The paper separately notes symptom onset (SX) occurred a mean of 1.98 days before DX. "51 ± 12 hours" appears nowhere in Mason 2022; it is also arithmetically inconsistent (2.75 d = 66 h). Nearest real figure in the wider literature is Temple et al. 2023, "on average 58 hours postinoculation and 23 hours before the symptom onset" — a different study entirely. | [nature.com/articles/s41598-022-07314-0](https://www.nature.com/articles/s41598-022-07314-0) · [Temple, JID 2023](https://doi.org/10.1093/infdis/jiac262) |
| 6d | "76% of cases showed temperature elevation before symptoms" | **VERIFIED but weakly grounded** | Smarr 2020: "We applied our digital bioreviewers across the 45 days prior to symptom onset. **38/50 subjects had fever-like days before reporting symptoms**" = 76%. Note: a 45-day lookback window, assessed by visual inspection, with no false-positive control. Coincidentally 38/50 (76%) also self-reported a fever. | [nature.com/articles/s41598-020-78355-6](https://www.nature.com/articles/s41598-020-78355-6) |
| 7a | Mason et al. (2022) Sci Rep 12, 3463, DOI 10.1038/s41598-022-07314-0 | **VERIFIED** | *Detection of COVID-19 using multimodal data from a wearable device: results from the first TemPredict Study.* Sci Rep 12, article 3463, 2 March 2022. | [Crossref](https://api.crossref.org/works/10.1038/s41598-022-07314-0) · [nature.com](https://www.nature.com/articles/s41598-022-07314-0) |
| 7b | Smarr et al. (2020) Sci Rep 10, 21640, DOI 10.1038/s41598-020-78355-6 | **VERIFIED** | *Feasibility of continuous fever monitoring using wearable devices.* Sci Rep 10, article 21640, 14 Dec 2020. (A correction exists: 10.1038/s41598-022-08621-2.) | [Crossref](https://api.crossref.org/works/10.1038/s41598-020-78355-6) · [nature.com](https://www.nature.com/articles/s41598-020-78355-6) |
| 8 | "Scripps DETECT: AUC 0.80 combined, 0.71 symptoms only, 0.68 sensor only" | **PARTLY CORRECTED** | Combined **0.80 (IQR 0.73–0.86)** ✓. Symptoms-only **0.71 (0.63–0.79)** ✓. Sensor-only is **0.72 (0.64–0.80)** ✗ — 0.68 is the *sleep metric alone* (0.68, 0.57–0.79); activity alone was 0.69 (0.61–0.77). **The task is not early detection.** It is discriminating COVID-positive from COVID-negative *among 333 already-symptomatic individuals who had been tested* (54 positive, 279 negative). | [nature.com/articles/s41591-020-1123-x](https://www.nature.com/articles/s41591-020-1123-x) |
| 9 | "Adding distal skin temperature to cardiac metrics boosts infection classification AUC by 5–8%" | **UNSUBSTANTIATED as stated** | I could not find any source for a "5–8%" range. The one specific, verifiable figure is Mason 2022: "Including dermal temperature improved ROC AUC from **0.770 to 0.819 (4.9% absolute improvement)**" — a single study, on its 73-participant training set, using Oura finger dermal temperature (not wrist "distal skin temperature"). Do not cite "5–8%". | [nature.com/articles/s41598-022-07314-0](https://www.nature.com/articles/s41598-022-07314-0) |
| 10a | "TemPredict enrolled >63,000 participants" | **VERIFIED** | "We gathered daily questionnaire data and physiological data using a consumer wearable (Oura Ring) from **63,153 participants**, of whom 704 self-reported possible COVID-19 disease." | [nature.com/articles/s41598-022-07314-0](https://www.nature.com/articles/s41598-022-07314-0) |
| 10b | "NightSignal real-time trial had 3,317 participants" | **CORRECTED (off by one)** | **3,318** enrolled, between 27 Nov 2020 and 20 Jul 2021. Of those, 2,155 had wearable data, 2,117 received daily alerts, and 84 COVID-positive cases had sufficient wearable data for evaluation. | [PMC8799466](https://pmc.ncbi.nlm.nih.gov/articles/PMC8799466/) |

---

## 3. Per-system A–V writeups

### 3.1 Stanford / Snyder Lab — Mishra et al. 2020 (retrospective COVID detection)

Mishra T, Wang M, Metwally AA, et al. *Pre-symptomatic detection of COVID-19 from
smartwatch data.* Nature Biomedical Engineering 4:1208–1220 (2020).
DOI [10.1038/s41551-020-00640-6](https://doi.org/10.1038/s41551-020-00640-6) ·
[PMC9020268](https://pmc.ncbi.nlm.nih.gov/articles/PMC9020268/)

- **A. Problem.** Detect COVID-19 infection from consumer smartwatch data at or before
 self-reported symptom onset.
- **B. Input data.** Fitbit minute-level heart rate and step counts; sleep records where
 available. Long-term pre-pandemic data (2019 or earlier) for 7 iPOP participants.
- **C. Device.** Predominantly Fitbit; also other HealthKit/Google Fit-compatible devices
 via the MyPHD app.
- **D. Signals.** Resting heart rate (RHR), steps, sleep duration. A derived feature
 "HROS" = heart rate divided by steps.
- **E. Processing.** RHR computed from HR readings where steps are zero; hourly
 aggregation; standardised residuals against a personal baseline; missing-data imputation
 examined explicitly (one result held only *with* imputation).
- **F. Personalisation.** Individual baseline. CuSum uses a **28-day sliding window**
 personalised baseline; the system restarts if >14 successive days are missing, and
 processes data in 56-day chunks.
- **G. Method.** Three algorithms, all statistical/unsupervised, no supervised training:
 (i) **RHR-Diff** — offline detection of significantly elevated RHR intervals from
 standardised residuals over the *global* dataset; (ii) **HROS-AD** — anomaly detection
 on HROS via Gaussian density estimation; (iii) **CuSum** — online cumulative-sum change
 detection with a two-tier (yellow/red) alarm at 95% quantile of baseline CuSum statistics.
- **H. Training required?** No supervised training. Baselines are fitted per person.
- **I. Pretrained models?** No — there are no learned weights to ship.
- **J. LLM?** No. **K. Agent?** No. **L. Agent tools?** N/A. **M. RAG?** No.
- **N. User interaction.** None in this paper — retrospective analysis. MyPHD app used
 for data collection only.
- **O. Real-time vs batch.** RHR-Diff and HROS-AD are offline/batch. CuSum is a prototype
 online detector, evaluated retrospectively by replay.
- **P. Output.** Interval-level "elevated RHR" annotations (offline); two-tier
 yellow/red alarm days (online).
- **Q. Evaluation.** Cohort of 5,262 enrolled; 32 COVID-positive individuals identified;
 25 with symptom-onset information. Ground truth = self-reported symptom onset date and
 self-reported diagnosis date, at day granularity. Controls: 73 individuals reporting no
 illness in the same period, plus 13 individuals with 15 non-COVID illnesses.
- **R. Reported performance (exact).**
 - "26 of them (81%)" of 32 COVID-positive individuals "had alterations in their heart
 rate, number of daily steps or time asleep" — retrospective, whole dataset, no split.
 - "Of the 25 cases … with detected physiological alterations for which we had symptom
 information, 22 were detected before (or at) symptom onset, with four cases detected
 at least nine days earlier."
 - Online CuSum: "**62.5% (15/24)** had an alarm on or before COVID-19 symptom onset" —
 the 63% headline. **This is a subgroup**: only "24 individuals who had at least 28 d of
 data ahead of symptom onset".
 - False alarm rate: "we were able to detect 63% of known COVID-19 infections with an
 **alarming frequency of 0.66 per month in the healthy individuals**." Also: average
 alarm counts per 30 days for COVID participants were **0.29 before vs 1.35 after**
 infection; 11 individuals had non-COVID alarms "ranging from 0.14 to 1 alarms per month".
 - Non-COVID illnesses: "gave a signal at or before the illness in **nine of 15 cases**".
- **S. Open-source availability.** Paper open at PMC. Data:
 `https://storage.googleapis.com/gbsc-gcp-project-ipop_public/COVID-19/COVID-19-Wearables.zip`
 — I verified HTTP 200, **378,380,920 bytes**, last modified 2020-10-19. Code:
 [github.com/mwgrassgreen/WearableDetection](https://github.com/mwgrassgreen/WearableDetection)
 (RHR-Diff, CuSum) and
 [github.com/gireeshkbogu/AnomalyDetect](https://github.com/gireeshkbogu/AnomalyDetect) (HROS-AD).
- **T. Reusable.** RHR-Diff / CuSum / HROS-AD reference implementations; the open data ZIP.
- **U. Limitations (authors' own).** "our study is still modest in size"; devices not
 FDA-approved for illness detection; "some individuals do not wear their devices (or let
 their charge expire) when symptomatic"; "cannot distinguish infections with SARS-COV-2
 from those caused by other viruses"; alarms occur in healthy periods "by statistical
 chance"; "63% is likely to be an overestimate for COVID-19 as asymptomatic cases are not
 accounted for". Confounders named but not measured: "medication, alcohol, travel and
 emotional or other stress inducers"; four of seven participants with December-holiday
 data showed long elevations (the "holiday bump").
- **V. Architectural lesson.** Personal streaming baselines beat population norms, and
 RHR alone is enough for a *signal* but not for *specificity*. The authors explicitly
 predict that HRV, respiration rate, skin temperature and SpO2 would be needed to
 discriminate illness types — a direct hint at what a multi-signal system should ingest.

---

### 3.2 Stanford / Snyder Lab — Alavi et al. 2022, NightSignal (prospective alerting)

Alavi A, Bogu GK, Wang M, et al. *Real-time alerting system for COVID-19 and other stress
events using wearable data.* Nature Medicine 28:175–184 (2022).
DOI [10.1038/s41591-021-01593-2](https://doi.org/10.1038/s41591-021-01593-2) ·
[PMC8799466](https://pmc.ncbi.nlm.nih.gov/articles/PMC8799466/)

- **A. Problem.** Deliver *real-time* daily alerts for physiological stress events
 (primarily SARS-CoV-2 onset) to users' phones, at a scale of millions, across
 heterogeneous smartwatches.
- **B. Input data.** Fitbit heart rate + steps (roughly minute resolution: "300 to 500 RHR
 overnight data points" per night); Apple Watch HR + steps at irregular resolution
 (5–15 min ranges, activity-dependent). Overnight window defined as **24:00 to 07:00**.
 Study ran 27 Nov 2020 – 20 Jul 2021.
- **C. Device.** Fitbit (1,031 users), Apple Watch (970), Garmin (98, excluded from
 analysis for lack of COVID cases), other (56). Data ingested via Fitbit OAuth 2.0 API
 and Apple HealthKit / Google Fit through the MyPHD app.
- **D. Signals.** Overnight resting heart rate only (HR filtered to intervals where step
 count is zero). Steps used solely as a gate for "resting".
- **E. Processing.** Take HR records where steps = 0; average across 24:00–07:00 to get
 Aᵢ, the nightly mean RHR. Missing nights imputed **only up to one night**, as the mean
 of the preceding and following nights. Deliberately **no minimum data-point threshold
 per night** — the authors argue a few resting points suffice and a threshold would
 discard too many nights.
- **F. Personalisation.** Baseline Mᵢ = **streaming median of all nightly means up to
 night i**. Empirically stable after **7 nights** for >80% of participants (within ±2 bpm
 of the 3-month baseline). Median 3-month range of the baseline was 3 bpm, SD 0.8.
- **G. Method.** A **deterministic finite state machine with 6 states** (S0–S5) and
 3 input symbols. S0/S1/S2 → green, S3/S4 → yellow, S5 → red. Symbols: Aᵢ < Mᵢ+3,
 Aᵢ = Mᵢ+3, Aᵢ ≥ Mᵢ+4. A red alert fires when the nightly mean RHR is ≥4 bpm above
 baseline for **two consecutive nights**; yellow when ≥3 but <4 bpm for two consecutive
 nights. Source (`nightsignal.py` lines 85–86): `yellow_threshold = 3`, `red_threshold = 4`.
 Two baseline modes in code: `MedianOfAvgs` (default, matches paper) and `AbsoluteMedian`.
 Comparators: online RHRAD (anomaly detection on hourly RHR, 744 h/1 month training
 window, 0.02 threshold, red if anomalies persist >5 h within 24 h), online CuSum
 (28-day baseline, 1 h resolution, evaluated every 12 h, alarm sent 21:00 daily), and
 scikit-learn Isolation Forest (contamination `auto` and `0.095`).
- **H. Training required?** **No.** NightSignal has zero learned parameters; the two
 thresholds are hand-chosen from the observed 3 bpm baseline fluctuation. RHRAD/CuSum fit
 a personal baseline window. Isolation Forest is unsupervised.
- **I. Pretrained models?** Not applicable — nothing to pretrain. This is a strength for
 reuse: NightSignal runs cold on any new user after 7 nights.
- **J. LLM?** No. **K. Agent?** No. **L. Agent tools?** N/A. **M. RAG?** No.
- **N. User interaction.** MyPHD iOS/Android app. Alerts rendered as a **calendar**
 (deliberately, not push notifications — to reduce annotation bias, since "participants
 who do not get alerts might not annotate events"). Users annotate any day via surveys:
 COVID-19 test, activities, symptoms (severity 1–5), medications, vaccination.
 **Medical recommendations were forbidden under the IRB protocol.** Post-study survey:
 "73% found that the frequency of red alerts was acceptable".
- **O. Real-time vs batch.** Genuinely real-time / online. Cloud back-end; the authors note
 NightSignal is light enough to run on-device.
- **P. Output.** One alert per day per user: JSON `{"date": ..., "alert": "0|1|2"}` plus a
 plot. 0 = green, 1 = yellow, 2 = red.
- **Q. Evaluation.** 3,318 enrolled → 2,155 with wearable data → 2,117 received alerts.
 278 self-reported a positive COVID test; 84 had sufficient wearable data (49 Fitbit,
 35 Apple Watch; 66 symptomatic, 18 asymptomatic). **50 of the 84 were retrospective**
 (tested positive *before* enrolment); only **34 were prospective**. Ground truth:
 self-reported symptom onset date (symptomatic) or self-reported diagnosis date
 (asymptomatic), day granularity; 45 of 84 had written or verbal confirmation of the test
 result. TP defined as **any red alert within a 21-day window before symptom onset /
 diagnosis**. FP defined at the alert-day level over COVID-negative periods
 (21 days before a negative test; entire timeline for untested participants).
 Controls: 1,213 tested-negative, 1,825 untested, 189 vaccinated.
- **R. Reported performance (exact).**
 - Sensitivity (per-person, 21-day window): **NightSignal 67/84 = 80%**
 (Fitbit 77%, Apple Watch 83%); **online CuSum 29/40 = 72%**;
 **online RHRAD 29/42 = 69%**. Symptomatic breakdown: 53/66 pre-symptomatic,
 5/66 post-symptomatic within 21 days, 8/66 no alert at all.
 Asymptomatic: 14/18 alerted within 21 days before diagnosis.
 - Specificity (per alert-day): NightSignal **87,124/(87,124+12,186) = 87.7%**;
 RHRAD **57,108/(57,108+7,971) = 87.7%**; CuSum **35,451/(35,451+6,889) = 83.7%**.
 - Lead time: **median 3 days** before symptom onset.
 - Alert burden: **3.42 alert days per person** (COVID-positive, 21-day window) vs
 **1.30** (COVID-negative) and **1.09** (untested); abstract quotes **1.15**
 for non-COVID events.
 - Alert clustering peaked in a window of **−4 to +11 days** around symptom onset.
- **S. Open-source availability.**
 - Paper: open access at [nature.com](https://www.nature.com/articles/s41591-021-01593-2).
 - **Data (open, no registration):**
 `https://storage.googleapis.com/gbsc-gcp-project-ipop_public/COVID-19-Phase2/COVID-19-Phase2-Wearables.zip`
 — verified HTTP 200, **5,537,624,129 bytes** (5.54 GB), last modified 2021-08-13.
 - Code: [StanfordBioinformatics/wearable-infection](https://github.com/StanfordBioinformatics/wearable-infection)
 (NightSignal + Isolation Forest),
 [gireeshkbogu/AnomalyDetect/scripts/rhrad_online_24hr_alerts_v6.py](https://github.com/gireeshkbogu/AnomalyDetect/blob/master/scripts/rhrad_online_24hr_alerts_v6.py) (RHRAD),
 [mwgrassgreen/Alarm](https://github.com/mwgrassgreen/Alarm) (CuSum).
- **T. Reusable code/models/APIs — repo audit (verified via GitHub REST API).**
 - Licence **Apache-2.0**; 63 commits; last commit **2021-09-20T16:51:09Z** ("Delete
 .DS_Store"); 16 stars, 8 forks, 4 watchers, 1 open issue; not archived; default
 branch `main`.
 - Full file tree: `LICENSE`, `README.md`, `requirements.txt`, `nightsignal.py`
 (27,938 bytes / 674 lines), `images/` (5 PNGs including the DFA diagram),
 `isolationforest/` (`isolationforest.py` 7,135 bytes, `README.md`, 4 sample CSVs),
 and three top-level sample CSVs: `P355472-AppleWatch-hr.csv` (6.5 MB),
 `P355472-AppleWatch-st.csv` (946 KB), `P682517-Fitbit-rhr.csv` (11.1 MB).
 **Only two participants of sample data.**
 - Runnable: `pip install -r requirements.txt` (Python 3, matplotlib, numpy, pandas), then
 `python3 nightsignal.py --device=Fitbit --restinghr=<FILE>` or
 `python3 nightsignal.py --device=AppleWatch --heartrate=<HR> --step=<ST>`.
 - Parsers: yes, two. Apple Watch HR schema `Device,Start_Date,Start_Time,Heartrate`;
 Apple Watch steps `Device,Start_Date,Start_Time,End_Date,End_Time,Steps`;
 Fitbit `Datetime,HR_Value,f0_,ST_Value`. Note the sample CSVs carry **date-shifted**
 timestamps (2025/2026 dates) — de-identification shifts dates and the MyPHD app
 re-identifies them locally.
 - Code smells worth knowing before reuse: it writes and then `os.system("rm ...")`
 temporary CSVs (`potenital_reds.csv` — sic, misspelled) in the working directory,
 and the Fitbit and Apple Watch code paths are near-duplicate blocks.
- **U. Limitations (authors' own).** "It is unclear why COVID-19 is not detected in all
 cases. Some of these individuals have an unstable baseline"; missing data when watches
 are being charged, "especially in the case of the Apple Watch"; alerts triggered by
 "poor sleep, stress, alcohol consumption, intense exercise, travel"; "The large number of
 unannotated alerts might be due to (1) failure to annotate an alert, (2) asymptomatic
 infections or (3) other stressors"; ground truth is fundamentally weak — "having a
 perfect ground truth is very hard … all the alerts within the assumed detection window
 might not necessarily be related to COVID-19, so a higher sensitivity does not by itself
 mean a greater accurate detection rate" (their own words). Vaccination reliably triggers
 alerts (max alerts on night 1–2 post-dose).
- **V. Architectural lesson.** The most important design decision in the whole territory:
 **restrict to overnight resting HR**. Extended Data Fig. 7 shows this is what suppresses
 false positives from daytime exercise, stress and travel. Second lesson: a 6-state
 hysteresis machine requiring two consecutive abnormal nights is what converts a noisy
 per-night signal into a tolerable alert rate — and it needs no training data at all.
 Third: the calendar-not-notification UI was a deliberate debiasing choice.

---

### 3.3 Scripps Research — DETECT (Quer et al. 2021; Gadaleta et al. 2021; Radin et al. 2022)

**Quer G, Radin JM, Gadaleta M, et al.** *Wearable sensor data and self-reported symptoms
for COVID-19 detection.* Nature Medicine 27:73–77 (2021).
DOI [10.1038/s41591-020-1123-x](https://doi.org/10.1038/s41591-020-1123-x)

- **A.** Improve on symptom-only COVID triage by adding passive sensor data.
- **B/C/D.** Daily-aggregate data only: DailyRHR, DailySleep (minutes), DailyActivity
 (total step count), from any device connecting to MyDataHelps via Apple HealthKit or
 Google Fit (Fitbit, Apple Watch, Garmin, etc.). Enrolment 25 Mar – 7 Jun 2020.
- **E/F.** Per-individual baseline; deviations from personal norm.
- **G.** **Not a trained ML model.** "A simple manual metric aggregation strategy
 **without optimization** was used" — hand-built metrics (RHRMetric, SleepMetric,
 ActivityMetric → SensorMetric; SymptomMetric from a published Menni logistic model with
 fixed coefficients) combined into an OverallMetric.
- **H.** No training. **I.** No pretrained model. **J/K/L/M.** No LLM, no agent, no RAG.
- **N.** MyDataHelps smartphone app; self-report surveys.
- **O.** Retrospective batch analysis.
- **P.** A continuous score; AUC reported.
- **Q. Evaluation — read this carefully.** 30,529 enrolled; 3,811 reported symptoms; of
 those, **54 reported testing positive and 279 negative**. The classification task is
 **positive vs negative among 333 already-symptomatic, already-tested individuals**.
 This is differential diagnosis, *not* pre-symptomatic early warning. Ground truth =
 self-reported test result; onset = self-reported symptom onset, day granularity.
- **R. Exact figures.** OverallMetric (symptoms + sensors) **AUC 0.80 (IQR 0.73–0.86)**;
 SymptomMetric **0.71 (0.63–0.79)**; SensorMetric (RHR+sleep+activity) **0.72 (0.64–0.80)**;
 SleepMetric alone **0.68 (0.57–0.79)**; ActivityMetric alone **0.69 (0.61–0.77)**.
 Improvement of combined over either alone: P < 0.01.
- **S/T.** No public dataset URL, no code. "All interested investigators will be allowed
 access to the analysis dataset following registration and pledging to not re-identify
 individuals or share the data with a third party. All data inquiries should be addressed
 to the corresponding author."
- **U.** Tiny positive class (n=54); self-reported test results; symptomatic-only cohort;
 no held-out split because there was no fitting.
- **V.** Sensor data adds ~0.09 AUC on top of symptoms — real but modest, and only
 demonstrated in a population that already knew it was ill.

**Gadaleta M, Radin JM, Baca-Motes K, et al.** *Passive detection of COVID-19 with wearable
sensors and explainable machine learning algorithms.* npj Digital Medicine 4:166 (2021).
DOI [10.1038/s41746-021-00533-1](https://doi.org/10.1038/s41746-021-00533-1)

- **G.** **Gradient-boosted decision trees**, explicitly designed to degrade gracefully
 when symptoms or particular sensor streams are missing, with per-feature importance
 explanations. This is the most methodologically mature model in the territory.
- **H.** Yes, supervised training. **I.** No released weights. **J/K/M.** No LLM/agent/RAG.
- **Q.** 38,911 enrolled 25 Mar 2020 – 3 Apr 2021; **1,118 PCR-positive, 7,032 PCR-negative**
 (nasopharyngeal swab). Much stronger label base than Quer 2021.
- **R. Exact figures.**
 - Symptomatic cohort: **AUC 0.83 [0.81–0.85]**; restricted to data **before the test
 date**: **AUC 0.78 [0.75–0.80]**.
 - All individuals (including asymptomatic and pre-symptomatic), symptoms excluded:
 **AUC 0.78 [0.76–0.79]**; before test date only: **AUC 0.70 [0.69–0.72]**.
 - The drop from 0.78 → 0.70 when you remove post-test data is the honest measure of
 genuine early-detection capability. **0.70 is the realistic ceiling for
 passive-sensor-only COVID detection at population scale.**
- **S/T.** Same gated access as Quer 2021. No code released.
- **U/V.** Confirms that self-reported symptoms carry most of the signal; passive-only
 detection is materially harder. The graceful-degradation design (handling absent
 channels) is the single most transferable idea here.

**Radin JM, Quer G, Ramos E, et al.** *Sensor-based surveillance for digitising real-time
COVID-19 tracking in the USA (DETECT): a multivariable, population-based, modelling study.*
Lancet Digital Health 4(11):e777–e786 (2022).
DOI [10.1016/S2589-7500(22)00156-X](https://doi.org/10.1016/S2589-7500(22)00156-X) ·
[PMC9499390](https://pmc.ncbi.nlm.nih.gov/articles/PMC9499390/)
— Population-level *nowcasting*, not individual alerting. Flags "anomalous sensor days"
(RHR above and step count below personal thresholds), aggregates the proportion of
anomalous users into a 7-day moving average per region. Model development cohort
1 Apr 2020 – 14 Jan 2022; validation cohort 15 Jan – 15 Feb 2022. Relevant as a
demonstration that the same per-person anomaly primitive scales to epidemiology.

**Radin JM, Wineinger NE, Topol EJ, Steinhubl SR.** *Harnessing wearable device data to
improve state-level real-time surveillance of influenza-like illness in the USA.*
Lancet Digital Health 2(2):e85–e93 (2020).
DOI [10.1016/S2589-7500(19)30222-5](https://doi.org/10.1016/S2589-7500(19)30222-5) ·
[PMC8048388](https://pmc.ncbi.nlm.nih.gov/articles/PMC8048388/) — the Fitbit ILI
surveillance precursor. **UNVERIFIED in detail:** the PMC page returned no extractable
body text in this session; I confirmed the citation metadata only.

---

### 3.4 TemPredict / Oura (Mason et al. 2022; Smarr et al. 2020)

**Mason AE, Hecht FM, Davis SW, et al.** *Detection of COVID-19 using multimodal data from
a wearable device: results from the first TemPredict Study.* Scientific Reports 12:3463 (2022).
DOI [10.1038/s41598-022-07314-0](https://doi.org/10.1038/s41598-022-07314-0)

- **A.** Early COVID detection using a device that measures continuous **dermal
 temperature** — the differentiator versus every Fitbit/Apple Watch study.
- **B/C/D.** Oura Ring. Channels: dermal (finger) temperature, heart rate, heart rate
 variability, respiratory rate, MET/activity. Non-wear detected via a MET threshold, with
 MET and temperature discarded during non-wear.
- **E.** Baseline periods require ≥13 usable baseline days; means computed over baseline
 HR and RR time series; 21-day "DX region"; SciPy 1.6.3 peak-finding on 21-day sequences
 of absolute deviations.
- **F. Personalisation — and this is the clever bit.** Because self-reported diagnosis
 dates are unreliable, they impute a **physiological onset date PX** = the temporal
 midpoint between the date of maximal HR deviation and the date of maximal RR deviation
 in the neighbourhood of illness. Models trained aligned to PX outperformed models
 aligned to symptom onset (SX) or diagnosis (DX). SX occurred a mean of 1.98 days before
 DX; PX **2.75 days** before DX.
- **G.** An ensemble of **five Random Forest models** on "normalized data sketches and
 trend time series", each model taking a different positive-class time frame near PX.
- **H.** Yes — supervised training. **I.** No: "Distribution of the classifier code is
 limited by the Department of Defense and therefore it cannot be shared."
- **J/K/L/M.** No LLM, no agent, no RAG.
- **N.** Daily questionnaires; no alerting back to users in this paper.
- **O.** Offline/retrospective.
- **P.** Binary COVID/not classification aligned to PX.
- **Q. Evaluation — the critical caveat.** 63,153 participants enrolled; 704 self-reported
 possible COVID; 306 with a confirmed self-reported positive PCR/antigen result;
 **73 selected into the training set** (needing ≥20 usable baseline days, ≥7 days before
 DX, ≥14 days after DX, and <4 concurrent symptoms). The headline sensitivity/specificity
 are computed **on those 73**. A further **10 participants** with antibody confirmation
 form the only external validation. Onset labels: DX = self-reported positive-test date;
 SX = self-reported symptom onset; PX = imputed. Day granularity.
- **R. Exact figures.**
 - **Sensitivity 82%, specificity 63%, n = 73**, "across the 21-day DX region".
 - **ROC AUC 0.819 (95% CI 0.809–0.830)**.
 - **Dermal temperature: AUC 0.770 → 0.819, described by the authors as a "4.9% absolute
 improvement".** Removing *any* one data stream reduced performance.
 - Validation subset (**n = 10**): sensitivity **90%**, specificity **80%**.
 - Lead time: identified COVID an average of **2.75 days before participants sought
 diagnostic testing**.
 - "substantial variation in accuracy based on age and biological sex."
- **S. Availability — effectively closed.** "Oura's data use policy does not permit us to
 make the data available to third parties without approval. Therefore, those seeking to
 reproduce our findings should contact Ashley Mason, PhD, and Benjamin Smarr, PhD for an
 online application to access the study data portal. This application process will require
 requesters to make a written commitment expressing agreements to not duplicate data, to
 not share data with third parties, and/or other confidentiality precautions."
 Classifier code blocked by DoD. **No usable URL. Do not plan around this dataset.**
- **T.** Nothing reusable beyond the PX-alignment idea.
- **U.** n=73 training / n=10 validation is very small relative to 63,153 enrolled; heavy
 inclusion filtering (excluded people with ≥4 concurrent symptoms, which removes the
 sickest); self-reported test results; the authors themselves flag that some in the
 training set may have had false-positive tests or misreported results; demographic
 performance variation.
- **V.** Two transferable ideas: (1) **align training labels to a physiologically imputed
 onset rather than a self-reported date** — self-report is the noisiest part of the
 pipeline; (2) continuous temperature is worth roughly +0.05 AUC and is the strongest
 argument for a temperature-bearing device.

**Smarr BL, Aschbacher K, Fisher SM, et al.** *Feasibility of continuous fever monitoring
using wearable devices.* Scientific Reports 10:21640 (2020).
DOI [10.1038/s41598-020-78355-6](https://doi.org/10.1038/s41598-020-78355-6)

- Descriptive feasibility study on the **first 50 TemPredict subjects reporting COVID-19**.
 Oura Ring peripheral temperature, plus HR, HRV, RR.
- **Method:** threshold-based "digital bioreviewers" on **daily maximum and daily minimum**
 normalised temperature, identifying "fever-like days". Smoothing radius 360 minutes.
- **R. Exact figures.** "participants who reported a fever (**n = 38; 76%**) also appeared
 to exhibit elevated maximum temperature concordant with symptom onset";
 "We applied our digital bioreviewers across the **45 days prior to symptom onset**.
 **38/50 subjects had fever-like days before reporting symptoms**." No sensitivity,
 specificity or AUC is reported — this is explicitly a feasibility paper.
- **S. Data IS available**, unlike Mason 2022: UC San Diego Library Digital Collections,
 DOI [10.6075/J0ZW1JFX](https://doi.org/10.6075/J0ZW1JFX), which resolves (verified,
 HTTP 302 → 200) to
 [library.ucsd.edu/dc/object/bb4886760b](https://library.ucsd.edu/dc/object/bb4886760b).
 Includes the associated MATLAB code. **UNVERIFIED:** I did not enumerate the individual
 files or their exact channels/cadence at that repository.
- **U.** No control group, no false-positive rate, a 45-day lookback window, and the key
 cross-check ("we examined other physiological outputs … We **visually inspected** the
 changes") is subjective. This paper supports "temperature moves during illness"; it does
 not support any operating point.

---

### 3.5 Mount Sinai — Warrior Watch (Hirten et al. 2021)

Hirten RP, Danieletto M, Tomalin L, et al. *Use of Physiological Data From a Wearable
Device to Identify SARS-CoV-2 Infection and Symptoms and Predict COVID-19 Diagnosis:
Observational Study.* J Med Internet Res 23(2):e26107 (2021).
DOI [10.2196/26107](https://doi.org/10.2196/26107) ·
[PMC7901594](https://pmc.ncbi.nlm.nih.gov/articles/PMC7901594/)

- **A.** Detect SARS-CoV-2 infection and symptoms from autonomic-nervous-system changes.
- **B/C/D.** **Apple Watch HRV only** — specifically SDNN (standard deviation of the
 interbeat interval of normal sinus beats). Health-care workers in the Mount Sinai system,
 followed prospectively with daily surveys via the custom Warrior Watch app.
- **E/F.** Circadian modelling per participant.
- **G.** **Mixed-effect cosinor models** — this is a statistical inference study, not a
 classifier. It models the *circadian amplitude and mean* of SDNN.
- **H.** No supervised training. **I.** No model artefact. **J/K/L/M.** No LLM/agent/RAG.
- **N.** Warrior Watch iPhone app, daily infection and symptom surveys.
- **O.** Retrospective statistical analysis of prospectively collected data.
- **P.** Group-level statistical differences — **not per-person alerts**.
- **Q.** ~297 health-care workers (per Mount Sinai's own release), 29 Apr – 29 Sep 2020.
 Ground truth: nasal-swab PCR date and daily self-reported symptoms.
- **R. Exact figures — note that these are p-values, not detection metrics.**
 - Mean amplitude of the SDNN circadian pattern differed between subjects with and without
 COVID-19: **P = .006**.
 - Mean amplitude differed in the **7 days before and 7 days after** a COVID-19 diagnosis
 versus uninfected periods: **P = .01**.
 - Mean and amplitude differed on the first day of reporting a COVID-related symptom
 versus all symptom-free days: **P = .01**.
 - **There is no sensitivity, specificity, AUC, lead time or false-alert rate in this
 paper.** Press coverage claiming detection "up to seven days before" diagnosis is a
 restatement of the ±7-day analysis window, not a measured lead time. Treat any
 headline detection number attributed to Warrior Watch as unsupported.
- **S/T.** **No data availability statement.** No code. Nothing reusable.
- **U.** Small, homogeneous, high-exposure cohort (health-care workers during a peak);
 Apple Watch SDNN is sampled sparsely and irregularly; no per-person decision rule was
 built or evaluated.
- **V.** HRV circadian *amplitude* — not the raw HRV value — is where the signal lives.
 That is a genuinely useful feature-engineering hint, and it is the one signal type the
 Stanford work does not use.

---

### 3.6 Duke — CovIdentify (Shandhi et al. 2022)

Shandhi MMH, Cho PJ, Roghanizad AR, et al. *A method for intelligent allocation of
diagnostic testing by leveraging data from commercial wearable devices: a case study on
COVID-19.* npj Digital Medicine 5:130 (2022).
DOI [10.1038/s41746-022-00672-z](https://doi.org/10.1038/s41746-022-00672-z) ·
[PMC9434073](https://pmc.ncbi.nlm.nih.gov/articles/PMC9434073/)

- **A.** Reframes the problem: not "alert the user" but **allocate scarce diagnostic tests**
 — target testing at the people most likely to be infected, to raise test positivity rate.
 This is the most operationally honest framing in the territory.
- **B/C/D.** Resting heart rate and step features. Devices: Garmin (1,689), Fitbit (1,091),
 Apple (107). Best results came from **Fitbit alone with minute-level resolution**.
- **E/F.** Personal baselines; systematic search over aggregation windows.
- **G.** Supervised ML with an explicit **cross-validated training set and an independent
 test set** — one of very few studies here that does this properly.
- **H.** Yes. **I.** No released weights, but the training code is public.
- **J/K/L/M.** No LLM, no agent, no RAG.
- **N.** CovIdentify iOS app, daily symptom surveys, SMS and email.
- **O.** Retrospective, designed for prospective deployment.
- **P.** A ranking used to select who to test.
- **Q.** CovIdentify (6,765 enrolled) + MyPHD (8,580); smartwatch data from **1,265
 individuals of whom 126 tested positive**. Ground truth: self-reported diagnostic test
 results, day granularity relative to enrolment.
- **R. Exact figures.**
 - **AUC-ROC 0.73 ± 0.14 (cross-validated training) and 0.77 (independent test set)**;
 **AUC-PR 0.55 ± 0.21 and 0.24** — note the large AUC-PR drop on the test set, which is
 the realistic picture under low prevalence.
 - RHR features separated positives from negatives **as early as 10 days** before the
 diagnostic test; step features **5 days** before.
 - Adding step features raised AUC-ROC by **7–11%** over RHR alone; adding RHR features
 raised AUC-PR by **38–50%** over steps alone.
 - Testing positivity rate improved **up to 6.5-fold** (training) and **up to 4.5-fold**
 (independent test set), including up to **27% asymptomatic** individuals.
- **S. Availability.**
 - **Data: PhysioNet, credentialed access.** *CovIdentify Dataset v1.0.0*, published
 25 Nov 2024, DOI [10.13026/ncq1-vp79](https://doi.org/10.13026/ncq1-vp79) —
 [physionet.org/content/covidentify/1.0.0/](https://physionet.org/content/covidentify/1.0.0/).
 Requires PhysioNet credentialed-user status, **CITI "Data or Specimens Only Research"
 training**, and signing the PhysioNet Credentialed Health Data Use Agreement 1.5.0.
 - Code: [github.com/DigitalBiomarkerDiscoveryPipeline/CovIdentify](https://github.com/DigitalBiomarkerDiscoveryPipeline/CovIdentify)
 — verified to exist; MIT licence; last push 2022-04-02; contains `ita_model_development.py`,
 README, LICENSE and one figure. Small but real.
 - Index repo: [Digital_Health_Data_Repository](https://github.com/DigitalBiomarkerDiscoveryPipeline/Digital_Health_Data_Repository)
 (Apache-2.0, last push 2025-04-22) — its `COVID-19/BigIdeasLab_CovIdentify` file is a
 pointer to the PhysioNet release, and its `COVID-19/README.md` points at the Stanford
 Phase 2 ZIP.
- **T.** ITA training script; DBDP `Pre-process` and `wearablecompute` modules.
- **U.** Self-reported test results with "no external validation of their testing results"
 (their own words); device heterogeneity degrades performance; the public release is
 **daily-aggregate only**, not the minute-level data that produced the best results.
- **V.** Two lessons. (1) Framing the output as *test allocation* sidesteps the impossible
 specificity requirement of a consumer alert. (2) Report AUC-PR, not just AUC-ROC — under
 realistic prevalence the precision-recall picture is far bleaker and it is the number
 that determines whether users trust the alerts.

---

### 3.7 COVID-RED — the only large randomised controlled trial (Zwiers et al. 2025)

Zwiers LC, Brakenhoff TB, Grobbee DE, et al. *Remote early detection of SARS-CoV-2
infections using a wearable-based algorithm: Results from the COVID-RED study, a
prospective randomised single-blinded crossover trial.* PLoS ONE 20(6):e0325116 (2025).
DOI [10.1371/journal.pone.0325116](https://doi.org/10.1371/journal.pone.0325116) ·
[PMC12140236](https://pmc.ncbi.nlm.nih.gov/articles/PMC12140236/) ·
Netherlands Trial Register NL9320.

**This is the highest-evidence-grade study in the entire territory and it is the one the
rest of the literature does not cite. Read it before believing any AUC above.**

- **A.** Does a wearable-based algorithm detect SARS-CoV-2 earlier than symptom reporting
 alone, in a real prospective deployment?
- **B/C/D.** **Ava bracelet** — "three sensors that measure five physiological parameters
 **every 10 seconds**: respiratory rate, heart rate, heart rate variability (ms),
 wrist-skin temperature (°C), and skin perfusion." Worn **while sleeping**, synced on waking.
 Originally a fertility-tracking device, repurposed.
- **E/F.** Proprietary Ava algorithm (version 2 deployed in real time; a version 3 exists
 but is out of scope of this paper).
- **G.** Proprietary ML algorithm combining wearable + self-reported symptom data
 (experimental arm) vs a symptom-only algorithm (control arm).
- **H/I.** Trained; not released. **J/K/L/M.** No LLM, no agent, no RAG.
- **N.** "Ava COVID-RED" smartphone app. Real-time red alerts. Subjects were **asked to get
 tested when alerted**. Daily diary of symptoms **and of confounding factors**:
 "factors that could affect their physiological parameters (e.g., **alcohol, drug, or
 medication use**)".
- **O.** Genuinely real-time, in a randomised crossover design.
- **P.** Red/green infection indication per day.
- **Q. Evaluation.** **17,825 subjects randomised.** Prospective, single-blinded,
 two-period, two-sequence, randomised controlled crossover. Ground truth: PCR/antigen test
 results plus **periodic SARS-CoV-2 serology**. Compliance threshold had to be lowered
 from 80% to 60% and the analysis population was still "much lower than the number of
 participants initially randomised".
- **R. Exact figures — the important ones.**
 - Alert timing: experimental arm received an alert significantly earlier than control —
 **median 0 versus 7 days before a positive SARS-CoV-2 test**.
 - **Detecting infection during a specified period:** experimental algorithm
 **sensitivity 93.8–99.2%, specificity 0.8–4.2%**. Control (symptom-only):
 **sensitivity 43.3–46.4%, specificity 66.4–65.0%**.
 - **Detecting infection on a given day:** experimental **sensitivity 45–52%,
 specificity 38–50%**; control **sensitivity 28–33%, specificity 93–97%**.
 - Authors' conclusion: "The experimental algorithm **overestimated infections**".
- **S. Data availability — publicly deposited, but download is gated.**
 DataverseNL, DOI [10.34894/FW9PO7](https://doi.org/10.34894/FW9PO7) —
 [dataverse.nl/dataset.xhtml?persistentId=doi:10.34894/FW9PO7](https://dataverse.nl/dataset.xhtml?persistentId=doi:10.34894/FW9PO7).
 I enumerated the file list via the Dataverse API: 19 files including
 `wd_20230515.csv` (**181,611,101 bytes** — the wearable data), `bc_20230515.csv` (35.6 MB),
 `ct_20230515.csv` (15.0 MB), `hu_20230515.csv` (14.6 MB), `ov_20230515.csv` (5.9 MB),
 `ser_20230515.csv` (2.9 MB, serology), `pcr_20230515.csv` (26.6 KB), `dm_20230515.csv`
 (demographics), `mh_`, `si_`, `sc_`, `cv_`, `ie_`, `ho_`, plus `variable_descriptions.csv`,
 `field_options.csv`, a README HTML and two PDFs (Data Processing Plan and Report).
 **Access caveat:** the dataset's Terms of Access read "The data is **not available for
 download directly via DataverseNL**. Data is available on request by completing the
 [UMC Utrecht request form] … In addition to a completed request form, the Data Sharing
 Agreement (DSA) in line with GDPR regulations". My direct download attempts were blocked
 by an anti-bot challenge, so I could not inspect file *contents* —
 **UNVERIFIED: the exact columns of `wd_20230515.csv`.**
- **T.** No code. The data itself is the asset.
- **U. Limitations (authors' own).** Only first-time infections were studied ("subjects
 were not followed up after reporting a first-time infection due to the assumption that
 people could only get infected with SARS-CoV-2 once"); poor compliance; "the exact timing
 of infection could not be determined from only positive serology tests"; the
 epidemiological context shifted continuously during the trial.
- **V. The lesson.** A retrospective AUC of 0.8 and a prospective specificity of 2% are
 compatible. Any system in this space must be evaluated on **false alerts per user-week
 at a fixed sensitivity**, in a real deployment, or the evaluation is meaningless.
 COVID-RED is also the best candidate dataset for confounder-aware modelling, because its
 diary explicitly captured alcohol, drug and medication use.

---

### 3.8 Viral challenge studies — the only studies with a known infection time

**Grzesiak E, Bent B, McClain MT, et al.** *Assessment of the Feasibility of Using
Noninvasive Wearable Biometric Monitoring Sensors to Detect Influenza and the Common Cold
Before Symptom Onset.* JAMA Network Open 4(9):e2128534 (2021).
DOI [10.1001/jamanetworkopen.2021.28534](https://doi.org/10.1001/jamanetworkopen.2021.28534) ·
[PMC8482058](https://pmc.ncbi.nlm.nih.gov/articles/PMC8482058/)

- **C/D.** **Empatica E4 wristband** (a research device, not consumer): heart rate, skin
 temperature, electrodermal activity, movement. Worn 1 day before and 11 days after
 inoculation.
- **G.** **Random forest** classifiers, with exhaustive feature selection (mlxtend
 `ExhaustiveFeatureSelector`) over feature sets.
- **Q.** Two human challenge studies. H1N1: 39 recruited, **31 analysed** (24 men, mean age
 34.7), inoculated intranasally with influenza A/California/03/09 (H1N1) at 10⁶ TCID50,
 isolated in clinic ≥8 days (data collected Sep 2017 – May 2018). Rhinovirus: 24 recruited,
 **18 analysed** (mean age 21.7), human rhinovirus type 16 at 100 TCID50, **not isolated**,
 on a college campus (Sep 2015). **Infection time is known exactly** — this is the only
 design in the territory where "pre-symptomatic" is unambiguous.
- **R. Exact figures.** Infection vs non-infection, wearable data only:
 **up to 92% accuracy for H1N1** (90% precision, 90% sensitivity, 93% specificity,
 90% F1, **AUC 0.85 [95% CI 0.70–1.00]**) and **88% for rhinovirus**.
 Distinguishing mild from moderate infection **24 hours before symptom onset**:
 **90% (H1N1) and 89% (rhinovirus)** accuracy. All metrics are **cross-validated**, not
 held-out — and note the phrase "**up to**", i.e. the best of a searched model space.
- **S/T.** No public dataset URL in the paper; supplementary tables list the features used.
 No code repository.
- **U/V.** n=31 and n=18 with exhaustive feature search is a textbook overfitting risk; the
 95% CI on AUC reaches 1.00. Research-grade wrist sensor, not a consumer device. But the
 design is the gold standard for label quality, and it shows electrodermal activity and
 skin temperature carry usable signal.

**Temple DS, Hegarty-Craver M, Furberg RD, et al.** *Wearable Sensor-Based Detection of
Influenza in Presymptomatic and Asymptomatic Individuals.* Journal of Infectious Diseases
227(7):864–872 (2023; online 27 Jun 2022).
DOI [10.1093/infdis/jiac262](https://doi.org/10.1093/infdis/jiac262) ·
[PMC9384446](https://pmc.ncbi.nlm.nih.gov/articles/PMC9384446/) · NCT04204493.

- **C/D.** Wearable **electrocardiogram** and physical activity sensors (not a consumer
 smartwatch).
- **G.** **Semi-supervised multivariable anomaly detection**, trained per participant on
 pre-inoculation data only, then applied to post-inoculation data. This "train on the
 person's healthy period, score everything after" pattern is the cleanest personalisation
 design in the literature.
- **Q.** 20 healthy adults challenged with influenza A (H3N2), monitored from 7 days before
 to 10 days after inoculation. Infection rate 85% (17 infected).
- **R. Exact figures.** "With the model classification threshold set so that **no alarms
 were recorded in the 170 healthy days recorded**, the algorithm correctly identified
 **16 of 17 (94%)** positive presymptomatic and asymptomatic individuals, on average
 **58 hours postinoculation and 23 hours before the symptom onset**."
 **Flag:** the threshold was chosen to give zero false alarms *on the same 170 days used
 to report zero false alarms*. The specificity is therefore fitted, not measured.
- **U.** Authors' own: the method "needs to be validated in large heterogeneous cohorts in
 normal living conditions". n=20, clinical confinement, ECG hardware.
- **V.** Confirms a ~1-day pre-symptomatic window is physiologically real under ideal
 conditions. The gap between 94% here and COVID-RED's 2% specificity in the field is the
 entire engineering problem.

---

### 3.9 Non-respiratory illness detection

**Inflammatory bowel disease flares — Hirten RP, et al.** *Physiological Data Collected
From Wearable Devices Identify and Predict Inflammatory Bowel Disease Flares.*
Gastroenterology (2025).
DOI [10.1053/j.gastro.2024.12.024](https://doi.org/10.1053/j.gastro.2024.12.024) ·
[PMC12206379](https://pmc.ncbi.nlm.nih.gov/articles/PMC12206379/)

- **The strongest non-infection wearable early-warning result I found.**
- **C/D.** Apple Watch, Fitbit **or Oura Ring**. Channels: HR, RHR, **HRV**, steps, **SpO2**.
- **G.** Linear mixed-effect models for HR/RHR/steps/SpO2; **cosinor mixed-effect models**
 for HRV circadian features; mixed-effect logistic regression for prediction.
- **Q.** **309 participants across 36 US states.** Ground truth is unusually strong:
 daily disease-activity surveys **plus C-reactive protein, erythrocyte sedimentation rate
 and faecal calprotectin** collected as standard of care — i.e. an objective
 inflammatory biomarker, not self-report.
- **R.** "Circadian patterns of HRV significantly differed between periods of inflammatory
 flare and remission, and symptomatic flare and remission." "HRV, HR, RHR, steps, and SpO2
 were **significantly altered up to 7 weeks prior** to inflammatory and symptomatic flares."
 HRV/HR/RHR "differentiated whether participants with symptoms had inflammation" — i.e.
 they separate *inflammatory* from merely *symptomatic* flares, which is clinically the
 hard part. **No AUC, sensitivity or specificity is reported in the abstract.**
- **S.** "Data collected as part of this study will be made available upon reasonable
 requests. **Analytic methods, and study materials will not be made available** to other
 researchers beyond what is described in the current study." Closed.
- **V.** A 7-week prodrome is a completely different time constant from a 3-day respiratory
 prodrome. A general illness early-warning architecture needs multi-scale baselines, not
 one window.

**Malaria — Wallukhan J, et al.** *Overcoming Data Loss in Wearable Disease Detection with
GAN-Based Imputation.* npj Digital Medicine (2026).
DOI [10.1038/s41746-026-02518-4](https://doi.org/10.1038/s41746-026-02518-4) ·
[PMC13043753](https://pmc.ncbi.nlm.nih.gov/articles/PMC13043753/)

- Directly relevant: a **lightweight GAN** imputes missing heart-rate data, feeding a
 rule-based anomaly detector. Cohort: **rural Kenya, n = 300, 161 malaria-positive**.
- **R.** "our system triggered early alerts in 100 cases, including **42 solely with
 imputation**. Alerts preceded symptom onset by **11.9 days**, aligning with the
 11.7-day parasitemia window from controlled trials. Despite **50% data coverage**,
 alerts occurred on 3.5 consecutive days during the infection window, improving early
 detection by 35%. The GAN, **trained only on external COVID-19 data (n = 3318)**,
 generalized to malaria, reducing reconstruction error by 58%."
- **The n = 3,318 is the Alavi/Stanford cohort** — this is a live demonstration that the
 open Stanford Phase 2 ZIP is reusable as a pretraining corpus for a different pathogen
 on a different continent.
- **S/T.** Code: [github.com/jwallukhd/gan-imputation-wearable-data](https://github.com/jwallukhd/gan-imputation-wearable-data)
 — verified to exist; last push 2026-03-19; contains `src/`, `notebooks/`, `outputs/`,
 `requirements.txt`, README. **No licence file** (so no explicit reuse grant). 0 stars.
- **V.** Missing data is the dominant real-world failure mode, and it is tractable
 separately from detection. Also the first cross-pathogen transfer result in this area.

**Lyme disease and inflammation — Li X, Dunn J, Salins D, et al.** *Digital Health:
Tracking Physiomes and Activity Using Wearable Biosensors Reveals Useful Health-Related
Information.* PLoS Biology 15(1):e2001402 (2017).
DOI [10.1371/journal.pbio.2001402](https://doi.org/10.1371/journal.pbio.2001402) ·
[PMC5230763](https://pmc.ncbi.nlm.nih.gov/articles/PMC5230763/)

- The origin paper for the whole Snyder-lab line. 43 individuals, >250,000 daily
 measurements, multiple simultaneous devices (including a pulse oximeter and radiation
 sensor). Reports early detection of **Lyme disease** and inflammatory responses, and
 introduces "a personalized, activity-based normalization framework to identify abnormal
 physiological signals from longitudinal data" — the direct ancestor of RHR-Diff.
 Also detects physiological effects of airline flights (SpO2 drop) and separates
 insulin-sensitive from insulin-resistant individuals.
- **S. Data link is DEAD.** The stated location `http://hmpdacc.org/data/wearable/stanford.tar`
 redirects to `https://www.hmpdacc.org/data/wearable/stanford.tar` and returns
 **HTTP 404** (verified 2026-08-30). **Mark this dataset as unobtainable at the published URL.**

**Long COVID — Uwakwe C, Rangan E, Kumar S, et al.** *Longitudinal wearable sensor data
enhance precision of Long COVID detection.* PLOS Digital Health (2025).
DOI [10.1371/journal.pdig.0001093](https://doi.org/10.1371/journal.pdig.0001093) ·
[PMC12633932](https://pmc.ncbi.nlm.nih.gov/articles/PMC12633932/)

- 126 individuals with acute SARS-CoV-2 infection. HR features across six analytical
 families: time-domain, Poincaré nonlinear, raw signal, **Kullback-Leibler divergence**,
 variational mode decomposition, and Shannon energy envelope — "quantification of
 day-to-day shifts in HR distributions". A rich, directly reusable feature vocabulary.
- **R.** Combined HR + symptom model: **ROC-AUC 95.1%, PR-AUC 85.9%**, "approximately 5%"
 improvement in both over the symptoms-only model. Note: this is *classification of Long
 COVID status*, not early warning, and the discriminative symptom features (brain fog,
 memory loss, heart palpitations) do most of the work.
- **S. Openly available:** [snyderlabs.stanford.edu/long-covid/](https://snyderlabs.stanford.edu/long-covid/)
 and Stanford Digital Repository [purl.stanford.edu/cb174pb4851](https://purl.stanford.edu/cb174pb4851)
 (DOI [10.25740/cb174pb4851](https://doi.org/10.25740/cb174pb4851)), **Open Data Commons
 Attribution License v1.0**, version 2 published 12 Jul 2025, data creation window
 10 Mar 2020 – 7 Feb 2025. Contains "both smartwatch data as well as **daily/periodic
 symptom surveys**" — i.e. unlike the Phase 1/Phase 2 ZIPs, this one ships labels.
 Both URLs verified HTTP 200.

---

### 3.10 Systematic review anchor

Mitratza M, Goodale BM, Shagadatova A, et al. *The performance of wearable sensors in the
detection of SARS-CoV-2 infection: a systematic review.* Lancet Digital Health
4(5):e370–e383 (2022).
DOI [10.1016/S2589-7500(22)00019-X](https://doi.org/10.1016/S2589-7500(22)00019-X) ·
[PMC9020803](https://pmc.ncbi.nlm.nih.gov/articles/PMC9020803/)

Searched to 27 July 2021; 3,196 records screened, **12 articles and 12 protocols** analysed.
Key sentences to quote in any write-up:

> "Most included articles had a **moderate risk of bias**… The accuracy of algorithmic
> models to detect SARS-CoV-2 infection **varied greatly (area under the curve 0·52–0·92)**.
> An algorithm's ability to detect presymptomatic infection **varied greatly (from 20% to
> 88% of cases), from 14 days to 1 day before symptom onset**. Increased heart rate was
> most frequently associated with SARS-CoV-2 infection, along with increased skin
> temperature and respiratory rate."

An AUC lower bound of 0.52 is chance. The reviewers' verdict: "The evidence … is still in
an early stage… Large prospective, and preferably controlled, studies … are needed."
COVID-RED (§3.7) is one of the two RCTs they anticipated, and it came back weak.

---

## 4. Dataset availability table — the practical output

| Dataset | Obtainable? | Exact access URL | Channels present | Cadence | Participants | Participant-days / volume | Illness episodes | Onset label type & granularity | Confounder annotations? |
|---|---|---|---|---|---|---|---|---|---|
| **Stanford MyPHD Phase 2 (Alavi 2022)** | **YES — open, no registration** | `https://storage.googleapis.com/gbsc-gcp-project-ipop_public/COVID-19-Phase2/COVID-19-Phase2-Wearables.zip` (verified HTTP 200, 5,537,624,129 bytes, modified 2021-08-13) | **Heart rate and step count ONLY.** Per participant: `Orig_Fitbit_HR.csv` + `Orig_Fitbit_ST.csv`, or `Orig_NonFitbit_HR.csv` + `Orig_NonFitbit_ST.csv`. No temperature, HRV, RR, SpO2 or sleep. | Fitbit ~1 min ("300 to 500 RHR overnight data points" per night); Apple Watch irregular, 5–15 min, activity-dependent | **2,123 participant folders** (1,027 Fitbit pairs, 1,096 non-Fitbit pairs) — verified by reading the ZIP central directory | ~**36.3 GB uncompressed** across 4,246 CSV files; study window 27 Nov 2020 – 20 Jul 2021 | **NOT IN THE DOWNLOAD.** Paper reports 84 evaluable COVID+ (66 symptomatic, 18 asymptomatic), 1,213 negative, 1,825 untested, 189 vaccinated. Labels live only in the paper's Source Data Fig. 4 xlsx (I could not download it — **UNVERIFIED whether its IDs join to the ZIP**) | Self-reported symptom onset (symptomatic) / self-reported diagnosis date (asymptomatic). **Day** granularity. Dates are shifted in de-identified data | **NO** in the public download. The surveys existed (activities: intense exercise, alcohol, travel, stress; plus symptoms, medication, vaccination, diagnosis) but are not in the ZIP |
| **Stanford MyPHD Phase 1 (Mishra 2020)** | **YES — open, no registration** | `https://storage.googleapis.com/gbsc-gcp-project-ipop_public/COVID-19/COVID-19-Wearables.zip` (verified HTTP 200, 378,380,920 bytes, modified 2020-10-19) | **Heart rate, steps, and SLEEP.** Files: `<ID>_hr.csv`, `<ID>_steps.csv`, `<ID>_sleep.csv`, plus 4 `_hr_longterm.csv` / `_steps_longterm.csv` pairs | Fitbit minute-level HR | **117** participants with HR+steps; **32** of those also have sleep; 4 with long-term pre-pandemic series | 378 MB compressed; 281 files | **NOT IN THE DOWNLOAD.** Paper: 32 COVID+ (25 with symptom dates), 15 non-COVID illnesses in 13 people, 73 healthy controls. Processed labels are in the paper's Supplementary Data 1 | Self-reported symptom onset and self-reported diagnosis date. **Day** granularity | **NO** |
| **Snyder Lab Long COVID (Uwakwe 2025)** | **YES — open, ODC-By licence** | [purl.stanford.edu/cb174pb4851](https://purl.stanford.edu/cb174pb4851) (DOI [10.25740/cb174pb4851](https://doi.org/10.25740/cb174pb4851)); portal [snyderlabs.stanford.edu/long-covid](https://snyderlabs.stanford.edu/long-covid/). Both verified HTTP 200 | Smartwatch HR **plus daily/periodic symptom surveys** — this one ships labels | **UNVERIFIED** (I did not enumerate files) | 126 analysed in the paper; repository total **UNVERIFIED** | Data creation 10 Mar 2020 – 7 Feb 2025 | Long COVID status per participant; acute infection episodes | Symptom surveys; exact date fields **UNVERIFIED** | **UNVERIFIED** — symptom surveys present, confounder fields not confirmed |
| **CovIdentify (Duke)** | **GATED — credentialed** | [physionet.org/content/covidentify/1.0.0/](https://physionet.org/content/covidentify/1.0.0/), DOI [10.13026/ncq1-vp79](https://doi.org/10.13026/ncq1-vp79). Requires: PhysioNet credentialed user + **CITI "Data or Specimens Only Research"** + signed DUA 1.5.0 | `rhr` file (device-reported daily resting HR, plus per-day observation count, `heartrate_min`, `heartrate_median`, `heartrate_mean`, `heartrate_q10`) and `step` file (daily total steps); `covidentify_survey_upload.csv` (enrolment + daily surveys) | **DAILY aggregates only** (derived from underlying minute- or 15-min-level data, which is *not* released) | 7,348 e-consented; 6,765 enrolled; **2,887 connected a smartwatch** (1,689 Garmin, 1,091 Fitbit, 107 Apple) | 362,108 daily surveys from 5,859 unique participants (mean 62, median 37 per person); 2 Apr 2020 – 25 May 2021 | **1,289 participants reported ≥1 test result: 132 positive, 1,157 negative** | Self-reported diagnostic test result. **Dates are removed** — only days relative to enrolment. Day granularity | **PARTIAL.** Surveys cover symptoms, social distancing, test results, and (from Feb 2021) **vaccination date, brand, dose number and vaccine-related symptoms**. Alcohol/exercise/menstrual/travel: **UNVERIFIED, likely absent** |
| **COVID-RED (Ava bracelet)** | **GATED — deposited but download requires a request form + DSA** | [dataverse.nl/dataset.xhtml?persistentId=doi:10.34894/FW9PO7](https://dataverse.nl/dataset.xhtml?persistentId=doi:10.34894/FW9PO7), DOI [10.34894/FW9PO7](https://doi.org/10.34894/FW9PO7). Request form: [umcutrecht.nl/en/data-request-form-umc-utrecht](https://www.umcutrecht.nl/en/data-request-form-umc-utrecht) | Device measures **respiratory rate, heart rate, HRV (ms), wrist-skin temperature (°C), skin perfusion**. Files present: `wd_*.csv` (181.6 MB, wearable data), `ser_*.csv` (serology), `pcr_*.csv`, `dm_*` (demographics), `cv_*`, `si_*`, `sc_*`, `mh_*`, `hu_*`, `ho_*`, `ie_*`, `bc_*`, `ct_*`, `ov_*`, `variable_descriptions.csv`, `field_options.csv`, README + 2 PDFs | Raw sensing every **10 seconds** during sleep; released cadence **UNVERIFIED** (download blocked) | **17,825 randomised** | `wd_*.csv` alone is 181.6 MB; extraction date 2023-05-15 | First-time SARS-CoV-2 infections confirmed by PCR/antigen **and periodic serology** | PCR/antigen test date + serology conversion. Authors note "the exact timing of infection could not be determined from only positive serology tests". Day granularity | **YES — the only one.** Daily diary explicitly recorded "factors that could affect their physiological parameters (e.g., **alcohol, drug, or medication use**)" alongside symptoms |
| **TemPredict fever subset (Smarr 2020)** | **Likely open (repository page resolves)** | DOI [10.6075/J0ZW1JFX](https://doi.org/10.6075/J0ZW1JFX) → [library.ucsd.edu/dc/object/bb4886760b](https://library.ucsd.edu/dc/object/bb4886760b) (verified 302 → 200). Includes associated MATLAB code | Oura: peripheral temperature, HR, HRV, respiratory rate | **UNVERIFIED** (Oura is typically ~1-min or 5-min during sleep) | **50** COVID-reporting subjects | 65-day windows per subject shown in figures; totals **UNVERIFIED** | 50 self-reported COVID-19 infections; 38 reported fever | Self-reported symptom onset and self-reported fever. Day granularity | **UNVERIFIED — assume NO** |
| **TemPredict main (Mason 2022)** | **NO** | None. "Oura's data use policy does not permit us to make the data available to third parties without approval… contact Ashley Mason, PhD, and Benjamin Smarr, PhD for an online application". Classifier code blocked by the **Department of Defense** | Would be: dermal temperature, HR, HRV, RR, MET | ~1-min | 63,153 enrolled | — | 306 confirmed positives; 73 used for training; 10 antibody-confirmed for validation | DX = self-reported positive test date; SX = self-reported symptom onset; PX = imputed physiological onset. Day granularity | Daily questionnaires exist; contents **UNVERIFIED**; irrelevant since data is not obtainable |
| **Scripps DETECT (Quer / Gadaleta / Radin)** | **GATED — no URL** | No repository. "All interested investigators will be allowed access to the analysis dataset following registration and pledging to not re-identify individuals or share the data with a third party. All data inquiries should be addressed to the corresponding author." | Daily RHR, daily sleep minutes, daily step count | **DAILY aggregates** | 30,529 (Quer) / 38,911 (Gadaleta) | 25 Mar 2020 – 3 Apr 2021 | Gadaleta: **1,118 PCR-positive, 7,032 PCR-negative**. Quer: 54 positive, 279 negative among symptomatic | Nasopharyngeal **PCR** test date + self-reported symptom onset. Day granularity | **NO** (symptoms only) |
| **Mount Sinai Warrior Watch (Hirten 2021)** | **NO** | **No data availability statement in the paper.** No code | Apple Watch HRV (SDNN) | Apple Watch HRV is sparse and irregular | ~297 health-care workers | 29 Apr – 29 Sep 2020 | Not stated in the abstract | Nasal-swab **PCR** date + daily symptom survey. Day granularity | **NO** |
| **IBD flares (Hirten 2025)** | **NO** | "made available upon reasonable requests. **Analytic methods, and study materials will not be made available**" | HR, RHR, HRV, steps, SpO2 (Apple Watch / Fitbit / Oura) | Device-dependent | **309** across 36 US states | Not stated | Inflammatory and symptomatic flares, with **CRP, ESR, faecal calprotectin** as objective ground truth | Objective biomarker + daily symptom survey. Day granularity | **NO** (not stated) |
| **Li 2017 (Lyme, iPOP)** | **NO — published URL is dead** | `https://www.hmpdacc.org/data/wearable/stanford.tar` returns **HTTP 404** (verified 2026-08-30) | HR, skin temperature, SpO2, activity, radiation | Continuous, multi-device | 43 individuals, >250,000 daily measurements | — | 1 Lyme case + inflammatory episodes | Clinical diagnosis. Granularity **UNVERIFIED** | **NO** |
| **Grzesiak 2021 / Temple 2023 (viral challenge)** | **NO** | No dataset URL in either paper | Grzesiak: Empatica E4 — HR, skin temperature, electrodermal activity, movement. Temple: ECG + activity | Continuous | 31 (H1N1) + 18 (rhinovirus); 20 (H3N2) | Grzesiak: −1 to +11 days around inoculation. Temple: −7 to +10 days | 31 + 18 + 17 challenge infections | **Inoculation timestamp — exact, hour-level.** The only true infection timing in the field | **N/A** — confounders controlled by clinical confinement (H1N1, H3N2); the rhinovirus arm was not isolated |

### Confounder annotation summary — explicit yes/no

| Confounder | Stanford Ph1/Ph2 (public files) | CovIdentify (PhysioNet) | COVID-RED (DataverseNL) | DETECT | TemPredict | Warrior Watch |
|---|---|---|---|---|---|---|
| Alcohol | **No** (collected in-app, not released) | Unverified, likely no | **Yes** | No | Unverified | No |
| Exercise | **No** (collected, not released) | Unverified, likely no | Unverified | No | Unverified | No |
| Stress | **No** (collected, not released) | Unverified, likely no | Unverified | No | Unverified | No |
| Sleep | Phase 1 **yes** (sleep CSVs), Phase 2 **no** | No | Device measures during sleep only | No (sleep minutes are a *feature*, not an annotation) | Unverified | No |
| Menstrual phase | **No** | **No** | Unverified (Ava is a fertility device, so possible) | No | **No** | No |
| Vaccination | **No** (collected, not released) | **Yes** — date, brand, dose, symptoms, from Feb 2021 | Unverified | No | Unverified | No |
| Travel | **No** (collected, not released) | Unverified, likely no | Unverified | No | Unverified | No |
| Medication | **No** (collected, not released) | Unverified, likely no | **Yes** (drug/medication use) | No | Unverified | No |

**Bottom line for this project:** if you need confounder labels, the only candidate is
COVID-RED, and you must request it. If you need volume and can live without labels or
confounders, the Stanford Phase 2 ZIP is free and immediate. If you need labels *and* open
access, the Snyder Long COVID dataset (ODC-By) is the best option, though it is
Long-COVID-framed rather than acute-onset.

---

## 5. Cross-system comparison

| System | Device(s) | Signals | Method | Trained? | Real-time? | Cohort (evaluable cases) | Headline metric | Evidence class | Data | Code |
|---|---|---|---|---|---|---|---|---|---|---|
| Mishra 2020 (RHR-Diff / HROS-AD / CuSum) | Fitbit | RHR, steps, sleep | Statistical change detection + density-based anomaly | No | Prototype online, evaluated by replay | 5,262 enrolled / 32 COVID+ | 81% (26/32) any alteration; 63% (15/24) online CuSum at/before onset | Retrospective, no held-out split; headline is a subgroup | **Open (378 MB)** | Open (2 repos) |
| Alavi 2022 (NightSignal) | Fitbit, Apple Watch | Overnight RHR (steps as gate) | **6-state DFA**, streaming median baseline, +3/+4 bpm | **No** | **Yes, deployed** | 3,318 enrolled / 84 COVID+ (only 34 prospective) | **80% sens (67/84)**, 87.7% spec (alert-day), median 3 d lead | Mixed: prospective deployment, but 50/84 cases retrospective; 21-day TP window | **Open (5.5 GB)** | **Open, Apache-2.0, runnable** |
| Quer 2021 (DETECT) | Any HealthKit/GoogleFit | Daily RHR, sleep, steps | Hand-built metric, **no optimisation** | No | No | 30,529 / 54 pos vs 279 neg (symptomatic only) | **AUC 0.80** combined | Retrospective; task is diagnosis among the symptomatic, not early warning | Gated | None |
| Gadaleta 2021 (DETECT) | Any | Daily RHR, sleep, steps + symptoms | **Gradient-boosted trees**, missing-channel tolerant | Yes | No | 38,911 / 1,118 PCR+ | AUC 0.83 symptomatic; **0.70 sensors-only, pre-test-date** | Retrospective with proper modelling; the 0.70 is the honest number | Gated | None |
| Mason 2022 (TemPredict) | Oura Ring | **Dermal temp**, HR, HRV, RR, MET | 5× Random Forest ensemble, PX-aligned labels | Yes | No | 63,153 / **73 training**, 10 validation | 82% sens / 63% spec (**training set**); AUC 0.819 | Training-set metrics as headline; n=10 external validation | **Closed** | **Closed (DoD)** |
| Smarr 2020 (TemPredict) | Oura Ring | Peripheral temperature | Threshold on daily max/min | No | No | 50 COVID-reporting | 38/50 (76%) fever-like days in the 45 d before symptoms | Descriptive feasibility; no controls, no operating point | **Open (UCSD)** | MATLAB, with data |
| Hirten 2021 (Warrior Watch) | Apple Watch | **HRV (SDNN) circadian amplitude** | Mixed-effect cosinor | No | No | ~297 HCWs | **P = .006 / .01** — no sens/spec/AUC exists | Statistical association only | **None** | None |
| Shandhi 2022 (CovIdentify ITA) | Garmin/Fitbit/Apple | RHR, steps | Supervised ML, **train + independent test** | Yes | No | 1,265 with watches / 126 positive | **AUC-ROC 0.77 test; AUC-PR 0.24 test**; 4.5× positivity uplift | Retrospective **with a genuine held-out test set** | PhysioNet, credentialed | **Open, MIT** |
| **Zwiers 2025 (COVID-RED)** | Ava bracelet | RR, HR, HRV, **wrist skin temp**, perfusion @10 s | Proprietary ML, deployed live | Yes | **Yes** | **17,825 randomised** | **Sens 93.8–99.2% at spec 0.8–4.2%** (period); 45–52% / 38–50% (per day) | **Randomised controlled trial — the only one** | Deposited, request-gated | None |
| Grzesiak 2021 | Empatica E4 | HR, skin temp, EDA, motion | Random forest + exhaustive feature search | Yes | No | 31 H1N1 + 18 rhinovirus | 92% / 88% accuracy (**cross-validated**, "up to") | Challenge study; exact infection time; severe overfitting risk at n≈30 | None | None |
| Temple 2023 | ECG patch + activity | ECG-derived, activity | Semi-supervised per-person anomaly detection | Per-person | No | 20 challenged, 17 infected | **16/17 (94%)**, 23 h before symptoms, **threshold fitted for 0 FP** | Challenge study; specificity is fitted not measured | None | None |
| Hirten 2025 (IBD) | Apple/Fitbit/Oura | HR, RHR, HRV, steps, SpO2 | Mixed-effect + cosinor + logistic | Partly | No | 309 | Signals altered **up to 7 weeks** pre-flare; no AUC given | Prospective collection, retrospective analysis; **objective biomarker ground truth** | Closed | Closed |
| Wallukhan 2026 (malaria) | Wearable HR | HR | **GAN imputation** + rule-based detector | Yes (GAN) | Designed for it | 300, 161 malaria+ | Alerts 11.9 d before symptom onset at 50% data coverage | Retrospective; cross-pathogen transfer from the Stanford n=3,318 | Kenya cohort not released | **Open (no licence)** |

**Universal across every row: J (LLM) = No, K (agent) = No, L (agent tools) = N/A,
M (RAG) = No.** Not one system in this literature uses a language model, an agent loop,
tool calls, or external knowledge retrieval. The most "agentic" behaviour anywhere is
NightSignal's calendar UI asking the user to self-annotate an alert.

---

## 6. What is genuinely demonstrated versus what is claimed

### Demonstrated in a prospective evaluation
- **Alavi 2022 / NightSignal** genuinely ran live: 2,117 people received real daily alerts
 from a deployed cloud system across two device ecosystems for eight months, and 73%
 found the alert frequency acceptable. **The engineering is demonstrated.**
- **COVID-RED** genuinely randomised 17,825 people and measured what happened.
 **This is the only true efficacy evidence in the field, and it is discouraging:
 specificity of 0.8–4.2% for period-level detection.**

### Shown retrospectively on held-out data
- **Shandhi 2022 (CovIdentify ITA)** — a real independent test set. AUC-ROC 0.77,
 AUC-PR 0.24. This is the most trustworthy retrospective number in the territory,
 precisely because it is unimpressive.
- **Gadaleta 2021** — large label base (1,118 PCR+), and the authors report the
 before-test-date restriction separately: **AUC 0.70 for sensors-only pre-test detection.**
 Treat 0.70 as the realistic ceiling.

### Shown on training data or with unclear splits
- **Mason 2022 (TemPredict).** The headline "82% sensitivity, 63% specificity, AUC 0.819"
 is measured on the **73-participant training set**. The only external validation is
 **10 participants**. The abstract does not make this distinction prominent.
- **Mishra 2020.** RHR-Diff "detects significant intervals based on the global dataset" —
 the authors say so themselves. There is no held-out split. The 81% figure is descriptive.
- **Grzesiak 2021.** Cross-validated, but on n=31 and n=18 with exhaustive feature-set
 search. The reported AUC 0.85 has a 95% CI reaching 1.00.
- **Temple 2023.** The operating threshold was set to produce zero alarms on the same
 170 healthy days then used to report zero false alarms.

### Claims in abstracts that the results do not support
- **Warrior Watch.** Every secondary source (and the Mount Sinai press release) states that
 HRV changes were detected "up to seven days before" diagnosis. The paper reports a
 p-value on a **±7-day analysis window**. There is no sensitivity, specificity, AUC or
 lead-time estimate anywhere in the paper. **Do not cite a detection performance number
 for Warrior Watch — none exists.**
- **Smarr 2020.** "prediction of illness onset is possible" is stated as a supported
 hypothesis; the evidence is 38/50 subjects having a threshold crossing somewhere in a
 **45-day** window, verified by visual inspection, with no control group.

### Headline numbers that come from a favourable subgroup — flag these explicitly
1. **Mishra 2020, "63%"** = 15/24 participants **who had at least 28 days of data before
 symptom onset**. Of the full 32 COVID-positive set, this is a filtered 75% of cases,
 selected on data completeness — which correlates with adherence, which correlates with
 detectability.
2. **Alavi 2022, "80%"** = 67/84 where the denominator has already excluded anyone with
 ">two days missing in a week before symptom onset" (symptomatic) or ">a week missing
 data in 21 days before the diagnosis date" (asymptomatic). It also pools **50
 retrospective cases with 34 prospective ones** in a paper framed as prospective.
 And a "true positive" is any red alert anywhere in a **21-day window**.
3. **Quer 2021, "AUC 0.80"** = discriminating positives from negatives among **333
 already-symptomatic people who had already sought a test**. Not early detection.
 The paper's own title says "for COVID-19 detection", which invites the misreading.
4. **Mason 2022, "82%/63%"** = the n=73 training set, after excluding people with ≥4
 concurrent symptoms and anyone with sparse baseline data.
5. **Temple 2023, "94%"** = 16/17, at a threshold fitted for zero false positives on the
 evaluation data.

### The asymmetry that inflates this entire literature
Almost every study defines a **true positive at the person level over a wide window**
(21 days in Alavi, 21 days in Mason, 45 days in Smarr) but defines a **false positive at
the alert-day level**. A person-level TP with a 21-day window and a day-level FP rate are
not commensurable, and combining them into a "sensitivity/specificity" pair is not a valid
ROC point. Alavi et al. are unusually candid about this: *"having a perfect ground truth is
very hard… all the alerts within the assumed detection window might not necessarily be
related to COVID-19, so a higher sensitivity does not by itself mean a greater accurate
detection rate."*

### False alert rate per user-week / user-month, and assumed base rate

| System | Reported false-alert burden | Base rate context |
|---|---|---|
| Mishra 2020 | **0.66 alarms per month in healthy individuals** (≈0.15/user-week). Also 0.29 alarms/30 d before vs 1.35 after infection in COVID cases; range 0.14–1 alarms/month across 11 individuals | 32 COVID cases in 5,262 enrolled ≈ 0.6% over the study period |
| Alavi 2022 | **1.15 alert days per person per 21-day window** for non-COVID events (≈0.38/user-week) vs 3.42 for COVID cases. Separately, alert-day specificity 87.7% implies ≈**0.86 false-alert days per user-week** — the two figures are not reconcilable from the published text | 84 evaluable cases in 2,155 with data ≈ 3.9% over 8 months |
| COVID-RED | Not expressed per user-week, but **specificity 0.8–4.2%** for period detection means essentially every participant received alerts. Per-day specificity 38–50% implies roughly **3.5–4.3 false-alert days per user-week** | Community incidence in the Netherlands, 2021 |
| CovIdentify | Not expressed per user-week; expressed instead as **testing positivity uplift (4.5× on the test set)**, which is the more useful operational framing | 126 positives / 1,265 with watches ≈ 10% |
| DETECT, TemPredict, Warrior Watch | **Not reported in any form.** | — |

Only Mishra and Alavi report anything resembling a per-user alert burden, they disagree
with each other by roughly 2–6×, and Alavi's two internal figures disagree with each other.
**Treat any per-user-week false-alert figure in this literature as approximately unknown.**

---

## 7. Bibliography

Primary studies (all URLs verified 2026-08-30):

1. Mishra T, Wang M, Metwally AA, et al. Pre-symptomatic detection of COVID-19 from
 smartwatch data. *Nature Biomedical Engineering* 2020;4:1208–1220.
 DOI [10.1038/s41551-020-00640-6](https://doi.org/10.1038/s41551-020-00640-6) ·
 PMID 33208926 · [PMC9020268](https://pmc.ncbi.nlm.nih.gov/articles/PMC9020268/)
2. Alavi A, Bogu GK, Wang M, et al. Real-time alerting system for COVID-19 and other stress
 events using wearable data. *Nature Medicine* 2022;28:175–184.
 DOI [10.1038/s41591-021-01593-2](https://doi.org/10.1038/s41591-021-01593-2) ·
 PMID 34845389 · [PMC8799466](https://pmc.ncbi.nlm.nih.gov/articles/PMC8799466/) ·
 preprint [medRxiv 2021.06.13.21258795](https://doi.org/10.1101/2021.06.13.21258795)
3. Quer G, Radin JM, Gadaleta M, et al. Wearable sensor data and self-reported symptoms for
 COVID-19 detection. *Nature Medicine* 2021;27:73–77.
 DOI [10.1038/s41591-020-1123-x](https://doi.org/10.1038/s41591-020-1123-x) · PMID 33122860
4. Gadaleta M, Radin JM, Baca-Motes K, et al. Passive detection of COVID-19 with wearable
 sensors and explainable machine learning algorithms. *npj Digital Medicine* 2021;4:166.
 DOI [10.1038/s41746-021-00533-1](https://doi.org/10.1038/s41746-021-00533-1) ·
 [PMC8655005](https://pmc.ncbi.nlm.nih.gov/articles/PMC8655005/)
5. Radin JM, Quer G, Ramos E, et al. Sensor-based surveillance for digitising real-time
 COVID-19 tracking in the USA (DETECT). *Lancet Digital Health* 2022;4:e777–e786.
 DOI [10.1016/S2589-7500(22)00156-X](https://doi.org/10.1016/S2589-7500(22)00156-X) ·
 [PMC9499390](https://pmc.ncbi.nlm.nih.gov/articles/PMC9499390/)
6. Radin JM, Wineinger NE, Topol EJ, Steinhubl SR. Harnessing wearable device data to
 improve state-level real-time surveillance of influenza-like illness in the USA.
 *Lancet Digital Health* 2020;2:e85–e93.
 DOI [10.1016/S2589-7500(19)30222-5](https://doi.org/10.1016/S2589-7500(19)30222-5) ·
 [PMC8048388](https://pmc.ncbi.nlm.nih.gov/articles/PMC8048388/) — **details UNVERIFIED**
7. Mason AE, Hecht FM, Davis SW, et al. Detection of COVID-19 using multimodal data from a
 wearable device: results from the first TemPredict Study. *Scientific Reports*
 2022;12:3463. DOI [10.1038/s41598-022-07314-0](https://doi.org/10.1038/s41598-022-07314-0)
8. Smarr BL, Aschbacher K, Fisher SM, et al. Feasibility of continuous fever monitoring
 using wearable devices. *Scientific Reports* 2020;10:21640.
 DOI [10.1038/s41598-020-78355-6](https://doi.org/10.1038/s41598-020-78355-6) ·
 correction [10.1038/s41598-022-08621-2](https://doi.org/10.1038/s41598-022-08621-2)
9. Hirten RP, Danieletto M, Tomalin L, et al. Use of Physiological Data From a Wearable
 Device to Identify SARS-CoV-2 Infection and Symptoms and Predict COVID-19 Diagnosis.
 *JMIR* 2021;23(2):e26107. DOI [10.2196/26107](https://doi.org/10.2196/26107) ·
 [PMC7901594](https://pmc.ncbi.nlm.nih.gov/articles/PMC7901594/)
10. Shandhi MMH, Cho PJ, Roghanizad AR, et al. A method for intelligent allocation of
 diagnostic testing by leveraging data from commercial wearable devices: a case study on
 COVID-19. *npj Digital Medicine* 2022;5:130.
 DOI [10.1038/s41746-022-00672-z](https://doi.org/10.1038/s41746-022-00672-z) ·
 [PMC9434073](https://pmc.ncbi.nlm.nih.gov/articles/PMC9434073/)
11. Zwiers LC, Brakenhoff TB, Grobbee DE, et al. Remote early detection of SARS-CoV-2
 infections using a wearable-based algorithm: Results from the COVID-RED study.
 *PLoS ONE* 2025;20(6):e0325116.
 DOI [10.1371/journal.pone.0325116](https://doi.org/10.1371/journal.pone.0325116) ·
 [PMC12140236](https://pmc.ncbi.nlm.nih.gov/articles/PMC12140236/) · NL9320
12. Grzesiak E, Bent B, McClain MT, et al. Assessment of the Feasibility of Using
 Noninvasive Wearable Biometric Monitoring Sensors to Detect Influenza and the Common
 Cold Before Symptom Onset. *JAMA Network Open* 2021;4(9):e2128534.
 DOI [10.1001/jamanetworkopen.2021.28534](https://doi.org/10.1001/jamanetworkopen.2021.28534) ·
 [PMC8482058](https://pmc.ncbi.nlm.nih.gov/articles/PMC8482058/)
13. Temple DS, Hegarty-Craver M, Furberg RD, et al. Wearable Sensor-Based Detection of
 Influenza in Presymptomatic and Asymptomatic Individuals. *J Infect Dis*
 2023;227(7):864–872. DOI [10.1093/infdis/jiac262](https://doi.org/10.1093/infdis/jiac262) ·
 [PMC9384446](https://pmc.ncbi.nlm.nih.gov/articles/PMC9384446/) · NCT04204493
14. Mitratza M, Goodale BM, Shagadatova A, et al. The performance of wearable sensors in the
 detection of SARS-CoV-2 infection: a systematic review. *Lancet Digital Health*
 2022;4(5):e370–e383.
 DOI [10.1016/S2589-7500(22)00019-X](https://doi.org/10.1016/S2589-7500(22)00019-X) ·
 [PMC9020803](https://pmc.ncbi.nlm.nih.gov/articles/PMC9020803/)
15. Hirten RP, et al. Physiological Data Collected From Wearable Devices Identify and
 Predict Inflammatory Bowel Disease Flares. *Gastroenterology* 2025.
 DOI [10.1053/j.gastro.2024.12.024](https://doi.org/10.1053/j.gastro.2024.12.024) ·
 [PMC12206379](https://pmc.ncbi.nlm.nih.gov/articles/PMC12206379/)
16. Li X, Dunn J, Salins D, et al. Digital Health: Tracking Physiomes and Activity Using
 Wearable Biosensors Reveals Useful Health-Related Information. *PLoS Biology*
 2017;15(1):e2001402.
 DOI [10.1371/journal.pbio.2001402](https://doi.org/10.1371/journal.pbio.2001402) ·
 [PMC5230763](https://pmc.ncbi.nlm.nih.gov/articles/PMC5230763/)
17. Uwakwe C, Rangan E, Kumar S, et al. Longitudinal wearable sensor data enhance precision
 of Long COVID detection. *PLOS Digital Health* 2025.
 DOI [10.1371/journal.pdig.0001093](https://doi.org/10.1371/journal.pdig.0001093) ·
 [PMC12633932](https://pmc.ncbi.nlm.nih.gov/articles/PMC12633932/)
18. Wallukhan J, et al. Overcoming Data Loss in Wearable Disease Detection with GAN-Based
 Imputation. *npj Digital Medicine* 2026.
 DOI [10.1038/s41746-026-02518-4](https://doi.org/10.1038/s41746-026-02518-4) ·
 [PMC13043753](https://pmc.ncbi.nlm.nih.gov/articles/PMC13043753/)

Datasets:

19. Stanford MyPHD Phase 1 wearables (Mishra 2020) —
 `https://storage.googleapis.com/gbsc-gcp-project-ipop_public/COVID-19/COVID-19-Wearables.zip`
20. Stanford MyPHD Phase 2 wearables (Alavi 2022) —
 `https://storage.googleapis.com/gbsc-gcp-project-ipop_public/COVID-19-Phase2/COVID-19-Phase2-Wearables.zip`
21. Cho P, Shandhi MMH, Roghanizad A, Dunn J. CovIdentify Dataset v1.0.0. PhysioNet, 2024.
 DOI [10.13026/ncq1-vp79](https://doi.org/10.13026/ncq1-vp79) ·
 [physionet.org/content/covidentify/1.0.0/](https://physionet.org/content/covidentify/1.0.0/)
22. COVID-RED study data. DataverseNL.
 DOI [10.34894/FW9PO7](https://doi.org/10.34894/FW9PO7)
23. Smarr BL, et al. Data from: Feasibility of continuous fever monitoring using wearable
 devices. UC San Diego Library Digital Collections.
 DOI [10.6075/J0ZW1JFX](https://doi.org/10.6075/J0ZW1JFX) →
 [library.ucsd.edu/dc/object/bb4886760b](https://library.ucsd.edu/dc/object/bb4886760b)
24. Uwakwe C, et al. Snyder Lab Long COVID Study Dataset v2. Stanford Digital Repository,
 12 Jul 2025. DOI [10.25740/cb174pb4851](https://doi.org/10.25740/cb174pb4851) ·
 [purl.stanford.edu/cb174pb4851](https://purl.stanford.edu/cb174pb4851) · ODC-By v1.0
25. Li X, et al. iPOP wearables data — `https://www.hmpdacc.org/data/wearable/stanford.tar`
 — **HTTP 404, dead as of 2026-08-30**

Code repositories (all existence-verified via the GitHub REST API):

26. [StanfordBioinformatics/wearable-infection](https://github.com/StanfordBioinformatics/wearable-infection)
 — NightSignal + Isolation Forest. Apache-2.0, 63 commits, last push 2021-09-20.
27. [gireeshkbogu/AnomalyDetect](https://github.com/gireeshkbogu/AnomalyDetect) — RHRAD /
 HROS-AD; online variant at
 [`scripts/rhrad_online_24hr_alerts_v6.py`](https://github.com/gireeshkbogu/AnomalyDetect/blob/master/scripts/rhrad_online_24hr_alerts_v6.py)
28. [mwgrassgreen/Alarm](https://github.com/mwgrassgreen/Alarm) — CuSum online detection
29. [mwgrassgreen/WearableDetection](https://github.com/mwgrassgreen/WearableDetection) —
 RHR-Diff and CuSum from Mishra 2020
30. [DigitalBiomarkerDiscoveryPipeline/CovIdentify](https://github.com/DigitalBiomarkerDiscoveryPipeline/CovIdentify)
 — ITA model development. MIT, last push 2022-04-02.
31. [DigitalBiomarkerDiscoveryPipeline/Digital_Health_Data_Repository](https://github.com/DigitalBiomarkerDiscoveryPipeline/Digital_Health_Data_Repository)
 — DHDR dataset index. Apache-2.0, last push 2025-04-22.
32. [jwallukhd/gan-imputation-wearable-data](https://github.com/jwallukhd/gan-imputation-wearable-data)
 — GAN imputation for wearable infection detection. **No licence file.** Last push 2026-03-19.

### Explicit UNVERIFIED list

- Exact file inventory, channels and cadence of the UCSD Smarr 2020 deposit.
- Exact file inventory and channels of the Snyder Lab Long COVID dataset.
- Column schema of COVID-RED `wd_20230515.csv` (download blocked by an anti-bot challenge).
- Whether the Alavi 2022 Source Data Fig. 4 spreadsheet contains participant IDs that join
 to the public Phase 2 ZIP (download blocked).
- Full body text and figures of Radin 2020 (Lancet Digital Health ILI surveillance).
- Whether CovIdentify's PhysioNet survey file contains alcohol, exercise or travel fields.
- Any FDA/CE regulatory status for any of these algorithms beyond Mishra's statement that
 none were approved as of 2020.
