# F8 — Confounder physiology and active sensing / value-of-information

Research note for the agentic wearable early-warning project (the course, the university).
Compiled 2026-08-30. Pure research: no design, no architecture, no recommendations.

---

## 0. How to read this document

### Evidence grades used throughout

| Grade | Meaning |
|---|---|
| **A** | Peer-reviewed **controlled / experimental** study (RCT, randomised crossover, laboratory dose-response, human challenge study) |
| **B** | Peer-reviewed **large observational** study (wearable cohort, epidemiological survey, meta-analysis of observational data) |
| **C** | Peer-reviewed **small observational / pilot** study, or a preprint |
| **D** | **Company data blog** — often very large n, methodologically opaque, not peer reviewed (Oura, WHOOP) |
| **F** | **Folklore** — circulating claim with no traceable primary source |

### Verification flags

- `[verified]` — I fetched the primary source (abstract or full text) in this research pass and read the number.
- `[secondary]` — the number came from a search-engine summary of the paper's full text and I could not independently open the passage. Treat as provisional.
- `[my arithmetic]` — a derived number I computed from published figures; the derivation is stated.

Every numeric claim below carries a grade and a flag. Where I could not find a primary source, I say so explicitly rather than filling the gap. Section 10 lists everything I failed to source.

---

## 1. Executive summary

**1. The load-bearing finding: on any single night, the strongest confounders are not separable from early infection using consumer wearable channels alone.**

Three confounders — **acute psychological stress**, **luteal-phase menstrual physiology**, and **vaccine reactogenicity** — move the *same* channels in the *same* direction, over the *same* timescale, and at a *larger or comparable magnitude*, as early respiratory infection. This is not a hand-wave; it is directly measured:

- **Luteal phase** (Goodale et al. 2019, n=193, 708 cycles, grade B `[verified]`): wrist skin temperature **+0.44 °C**, heart rate **+3.91 bpm**, respiratory rate **+0.60 breaths/min**, HRV **-0.32 ms** versus follicular. All four channels move in the infection direction.
- **Vaccine dose 2** (Gepner et al. 2022, n=160 chest-patch, grade B `[verified]`): heart rate **+9.85 % (90 % CI 7.71-11.99)** within 48 h, skin temperature and respiratory rate up, **SpO2 unchanged**, returning to baseline by day 3. That is a near-exact replica of a 48-72 h infection prodrome.
- **Acute stress** (Bloomfield et al. 2024, n=525 students, Oura, grade B `[verified]`): each +1 bpm resting HR OR = 1.036, each +1 breath/min OR = **1.230**, each +1 ms HRV OR = 0.988 for moderate-to-high perceived stress. Stress raises HR and RR and lowers HRV — three of the four infection channels.

**2. Alcohol and exercise ARE partially separable, but only by using a channel other than the autonomic ones, or by waiting.**

- **Alcohol** is separable primarily by **duration**: nocturnal RHR normalises the very next alcohol-free night (Strüven et al. 2025, grade B `[verified]`). But on *night one* — which is exactly when an early-warning system wants to act — its magnitude **exceeds** typical infection signal: **+2.4 to +2.8 bpm per drink**, **-3.3 to -3.8 ms HRV per drink** (Grosicki et al. 2026, n=20,968, 5.1 M person-days, grade B `[verified]`).
- **Exercise** is separable by the **activity/step channel moving up** while infection drives it down. But the magnitude is enormous: maximal-strain exercise ending 0-2 h before sleep gives **+5.94 bpm RHR and -17.02 ms HRV** (Leota et al. 2025, n=14,689, 4.08 M person-nights, grade B `[verified]`) — larger than most reported infection signals. Separability fails for exercise the device does not capture (swimming, cycling, resistance work with a step-based device) and for day-2 residuals.

**3. The base rates are brutal and they are the real argument for asking.**
Alcohol is consumed on **29.9 % of person-days** in a large wearable cohort (Grosicki et al. 2026, grade B `[verified]`). For a menstruating user, roughly **45 % of days are luteal** `[my arithmetic]`. **34.8 % of US adults** habitually sleep <7 h (Liu et al. 2016, grade B `[verified]`). **64 % of student-weeks** are moderate-to-high stress (Bloomfield 2024, grade B `[verified]`). Against this, a new symptomatic respiratory infection prodrome occupies on the order of **2-3 % of nights per year** `[my arithmetic]`. Confounders outnumber the target roughly **20-40 : 1** on any given night. Stanford's deployed alerting system measured this directly: **1.15 alert-days per person per 21-day window in COVID-negative individuals** versus 3.42 in COVID-positive (Alavi et al. 2022, grade B `[verified]`) — i.e. roughly **20 false alert-days per person-year** `[my arithmetic]`.

**4. Exact expected information gain over ~10 causes x ~8 questions is computationally free.**
The full myopic computation is **O(M·K·R)** ~= **320 multiply-adds plus ~320 logarithms** for M=8 questions, K=10 hypotheses, R=4 answers. That is microseconds. Even 2-step lookahead (**O(M²KR²)** ~= 9,000 operations) is free. The binding cost is **specifying the likelihood table p(answer | cause, question)** — 320 conditional probabilities, most without empirical support — not evaluating the expectation. See §6.1.

**5. There is a real gap in the literature.**
Information-theoretic **question selection** in health is well established (Pathfinder; PROMIS computerized adaptive testing; Benish's mutual-information framework; RL symptom-checkers). Information-gain-based **survey shortening** in mobile health exists and is recent (Li, Ponnada, Wang, Dunton & Intille, IMWUT 2024 — 34-56 % survey-length reduction `[verified]`). But I found **no published system that decides *whether it is worth interrupting the user at all right now*, on a continuous passive physiological stream, using an explicit expected-information-gain-minus-cost criterion, in order to disambiguate a physiological anomaly.** The pieces exist separately; the combination appears unpublished. See §7 — and note this is "not found", not "does not exist".

**6. Honest weak spots in this review.** Alcohol's effect on nocturnal *respiratory rate* and *skin temperature* has no peer-reviewed wearable quantification I could find (only company blog data). Ambient bedroom temperature's contamination of skin-temperature deviation is under-quantified. Consumer SpO2's behaviour in mild URI is essentially unstudied. Long-horizon (6-12 month) question-burden tolerance has **almost no evidence base** — nearly every EMA meta-analysis covers 2-42 day protocols.

---

## 2. THE CONFOUNDER TABLE

Direction symbols: ↑ increase, ↓ decrease, → no meaningful change, **?** no primary evidence found.

| # | Confounder | Resting HR | HRV (rMSSD) | Resp. rate | Skin temp | Sleep | Onset latency | Duration | Infection-like? | Grade | Key citation |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Acute alcohol** | ↑ **+2.4-2.8 bpm per drink**; +3.0 bpm (95 % CI 1.37-4.77) at 40-60 g; Oura blog +8.2 % | ↓ **-3.3 to -3.8 ms per drink**; -10.8 ms (-15.6 %) blog | **?** no peer-reviewed wearable number | **?** vasodilation predicts ↑ distal temp; unquantified | TST -35 min (blog); PSG deep sleep n.s. at 40-60 g; fragmentation late-night | Same night, within 1-3 h of intake | **1 night**; normalised by next alcohol-free night | **Yes on night 1** | B (A for lab dose-response) | Grosicki 2026; Strüven 2025; de Zambotti 2021; Pietilä 2018; Oura blog (D) |
| 2 | **Acute / intense exercise** | ↑ **+2.02 (light) → +5.94 bpm (maximal)** if ending 0-2 h pre-sleep; **+0.40 → +2.82 bpm** at 4-6 h | ↓ **-4.55 → -17.02 ms** at 0-2 h; **-1.18 → -5.76 ms** at 4-6 h | ↑ mild, not well quantified | **?** | Sleep onset **+3.99 → +39.99 min**; TST **-8.35 → -30.62 min** | Same night | 1 night if ≥4 h pre-sleep; day-2 residual unquantified | **Yes, but steps ↑** | B (A for lab) | Leota 2025; Myllymäki 2012 |
| 3 | **Sleep restriction / fragmentation** | ↑ modest (magnitude poorly quantified in wearables) | ↓ **rMSSD SMD = -0.24**; LF and LF/HF ↑; SDNN and HF n.s. | ↑ small | **?** | TST directly reduced — **the channel is the confounder** | Same night | 1-2 nights | Partly | B (meta-analysis) | Zhang et al. 2025 (11 studies, n=549); Castro-Diehl 2016 |
| 4 | **Acute psychological / exam stress** | ↑ OR = **1.036 per bpm** for high perceived stress | ↓ OR = **0.988 per ms** | ↑ OR = **1.230 per breath/min** (strongest single predictor) | ↓ expected (peripheral vasoconstriction) — **not quantified in wearables** | TST ↓ (OR 0.617 per hour) | Hours-days | Days to weeks (exam periods) | **Yes — worst mimic** | B | Bloomfield 2024 (n=525 students, Oura) |
| 5 | **Menstrual luteal phase** | ↑ **+3.91 bpm** (late luteal vs follicular); ECG studies 2.3-3 bpm; wearable range 2-7 bpm | ↓ **-0.32 ms** (Ava); rMSSD ↓ late luteal in young women (p=0.019, Oura) | ↑ **+0.60 breaths/min** | ↑ **+0.44 °C** wrist (Ava); **+0.30 °C (SD 0.12)** finger (Oura); oral BBT +0.23 °C | No significant Oura sleep-metric change | Gradual, post-ovulation | **~10-14 days per cycle**, periodic | **Yes — all 4 channels** | B | Goodale 2019 (n=193); Maijala 2019 (n=22); Alzueta 2024 (n=96) |
| 6 | **Vaccine reactogenicity (mRNA)** | ↑ smartwatch mean **+0.56 bpm dose 1**, **+1.52 bpm dose 2** (95 % CI 1.42-1.63); chest-patch **+9.85 %** peak | ↓ (associated with antibody response); chest-patch found "no robust HRV signal" | ↑ significant in first 48 h | ↑ dermal temp deviation night 0 after dose 2 | Sleep **+35 min** day 1; steps **-1,628** day 1 | **~12-24 h**, peak **day 2** | Baseline by **day 4 (dose 1)** / **day 6 (dose 2)**; chest-patch by day 3 | **Yes — near-identical** | B | Quer 2022 (n=5,674); Gepner 2022 (n=160); Mason 2022 |
| 7 | **Travel / jet lag** | ↑ (magnitude not separately published in the large cohort) | ↓ | ? | ? | Pre-travel night TST **-17.9 min** (short E), **-61.9 min** (long E); post-travel **-12 to -15 min**; **sleep timing does not recover within 15 days**; WASO ↑, deep + REM ↓ for **5-6 days** | Night before departure | Duration recovers ~2 days; **timing and architecture 5-15 days** | Partly | B | Willoughby 2025 (n=57,240 Oura users, 1.47 M sleep periods) |
| 7b | **Altitude** | ↑ | ↓ parasympathetic indices | ↑ (periodic breathing) | ? | Fragmented | Hours | Days (acclimatisation) | **No — SpO2 discriminates** | B/C | Lang 2026 (SpO2 **97.6 ± 0.5 %** sea level → **87.8 ± 3.0 %** at ~3,800 m); Patterson 2026 (**87.8 ± 1.8 %** at 3,620 m) |
| 8 | **Ambient heat / cold** | ↑ in heat | ↓ in heat | → | **↑↓ directly** — skin temp deviation is *definitionally* contaminated by room temperature | Fragmented in heat | Same night | Duration of exposure | Temp channel only | **Weak evidence — no quantification found** | Kräuchi 2004; Romeijn 2012 |
| 9a | **Caffeine** | small ↑ or → (baroreflex can lower HR) | mixed / poorly established | → | → | **TST -45 min, efficiency -7 %, SOL +9 min, WASO +12 min, N3 -11.4 min**; cut-off **8.8 h** (107 mg coffee) or **13.2 h** (217.5 mg) before bed | 30-60 min | ~6-9 h | Sleep channel only | A (meta-analysis of RCTs) | Gardiner 2023 (Sleep Med Rev) |
| 9b | **Late meals** | ↑ **+0.73 bpm** nocturnal HR for heavier evening meals | ? | ? | ? | TST **+7.7 min** | Same night | 1 night | Negligible | **C (preprint)** | Shkolnik 2026 (medRxiv) |
| 9c | **Nicotine** | ↑ acutely (large) | ↓ acutely; chronic smokers lower HRV | ? | ↓ distal (vasoconstriction) | ↓ quality | Minutes | Minutes-hours acute | Partly | **No clean meta-analysis retrieved — magnitudes unverified** | — |
| 10a | **Beta blockers** | ↓ **-8 to -14 bpm** (MERIT-HF quintiles) | ↑ typically | → | → | → | Days to steady state | Chronic | Blunts detection | B | Gullestad 2005 (MERIT-HF) |
| 10b | **Stimulants / antihistamines / SSRIs** | Stimulants ↑; anticholinergic antihistamines ↑ and impair sweating; SSRIs small ↑ HR, HRV ↓ | varies | → | Anticholinergics impair thermoregulation | Stimulants ↓ TST | Hours | Chronic if daily; **step change on start/stop/missed dose** | Baseline shift, not acute confound | **Not verified in this pass** | — |
| 11 | **Illness recovery tail** | ↑ **relative tachycardia persisting to ~79 days** post symptom onset; **13.7 % remain >5 bpm above baseline for >133 days**; transient *bradycardia* phase ~days 9-15 | ↓ prolonged | ↑ prolonged | ↑ prolonged | Sleep back to baseline **day 24**; steps **day 32** | — | **Months** | **Contaminates baseline** | B | Radin 2021 (n=234 COVID+ vs 641 symptomatic COVID-) |
| 12 | **Sensor artifact / poor wear** | Fitbit Charge HR **underestimates by -5.96 bpm (SE 0.18)** overall, **-16.2 bpm (SE 0.74)** during MVPA; ICC 0.83 | Unreliable under motion | Unreliable | Loose fit → ambient-dominated readings | Wake/sleep misclassification | Instant | Duration of poor wear | Looks like *anything* | B | Gorny 2017; Reithe 2025 |
| **13** | **Acute respiratory viral infection (TARGET)** | ↑ (see §5) | ↓ | ↑ | ↑ (**+0.63 °C** mean fever-like deviation `[secondary]`) | TST ↑, fragmented | HR anomaly precedes symptoms by **73 h (influenza)**, **23 h (COVID)**, **62 h (GAS)** | Acute days, tail to months | — | B (A for challenge study) | Snir 2024; Mishra 2020; Grzesiak 2021; Radin 2021 |

### 2.1 Confounder detail notes

#### Alcohol — the single most cited confounder, so getting it right matters

Four independent, methodologically different sources agree on direction and roughly on magnitude:

1. **Laboratory dose-response, grade A `[verified]`.** de Zambotti M, Forouzanfar M, Javitz H, Goldstone A, Claudatos S, Alschuler V, Baker FC, Colrain IM. *Sleep* 2021;44:zsaa135. n = 26 healthy adults aged 30-60 (11 women), 3 nights of laboratory PSG, randomised order, placebo / low (1 drink W, 2 M) / high (3 drinks W, 4 M). Result: "presleep alcohol ingestion resulted in an overall increase in nocturnal heart rate, suppressed total and high-frequency HR variability, reduced baroreflex sensitivity, and increased sympathetic activity", with dose- and time-dependence. The abstract does not give per-index magnitudes; those are in the full text which I did not open.
2. **Large real-world wearable, grade B `[verified]`.** Grosicki GJ et al. *PLOS Digital Health* 2026;5(3):e0001284. n = 20,968 (10,025 F / 10,943 M), 5,109,185 person-days, WHOOP 4.0, within-person comparison. Per-drink deviation: RHR **+2.8 bpm (99.9 % CI 2.7-2.9) females**, **+2.4 bpm (99.9 % CI 2.3-2.4) males**; HRV **-3.8 ms (99.9 % CI -4.1 to -3.5) females**, **-3.3 ms (-3.5 to -3.1) males**. At five drinks above baseline: HRV **-5.6 ms F / -5.1 ms M** — note this is *less than 5x* the per-drink figure, i.e. the response **saturates**; do not extrapolate linearly. Effects larger in females and in 20-29 year-olds. Timing matters: drinking 60 min earlier gave **-0.87 bpm RHR and +1.5 ms HRV** in females.
3. **Prospective controlled exposure with a smartwatch, grade B `[verified]`.** Strüven A, Schlichtiger J, Hoppe JM, Thiessen I, Brunner S, Stremmel C. *Nutrients* 2025;17(9):1470. n = 40 (63 % female, mean age 30.5). Protocol: 3 alcohol-free baseline days → 3 evenings at **40 g/day (women) / 60 g/day (men)** → 3 post-exposure days. Nocturnal RHR **63.6 ± 9.2 → 66.6 ± 9.0 bpm**, i.e. **+3.0 bpm (95 % CI 1.37-4.77, p < 0.001)**, falling to 64.9 ± 9.3 in post-exposure. **Critically: light sleep p = 0.339, deep sleep p = 0.116, sleep latency, awakenings and TST all unchanged** — at this dose the *cardiac* signal moved but the *sleep-architecture* signal did not. HRV, respiratory rate and skin temperature were **not measured**.
4. **Large free-living observational, grade B `[verified]`.** Pietilä J, Helander E, Korhonen I, Myllymäki T, Kujala UM, Lindholm H. *JMIR Mental Health* 2018;5(1):e23. n = **4,098** Finnish employees, beat-to-beat HR during the first 3 hours of sleep. Dose-dependent: physiological recovery decreased by approximately **9 %, 24 % and 39 %** for low, moderate and high alcohol dose respectively. Effect stronger in younger participants and those with lower baseline sleep HR. `[secondary]` A commonly quoted set of rMSSD figures from this paper's full text — **-2.0 ms (low), -5.7 ms (moderate), -12.9 ms (high)**, and **-10.9 ms at high dose for a 30-year-old vs -4.7 ms for a 60-year-old** — I could not open and verify directly. Use with the caveat.
5. **Company data blog, grade D.** Oura's own member-data analysis: on alcohol-tagged nights, **average HR +9.6 %**, **lowest resting HR +8.2 %**, **HRV -10.8 ms (-15.6 %)**, **TST -35 min**, **Sleep Score -6.8 %** relative to surrounding alcohol-free nights. Large n, no published methods, no peer review, self-tagged exposure. Directionally consistent with the peer-reviewed work but the percentage magnitudes are larger than the controlled studies — likely because self-tagging selects heavier drinking occasions.

**The folklore check.** The circulating claim *"alcohol raises resting heart rate by ~10 bpm"* is **grade F / folklore**. The best peer-reviewed within-person estimates are **+2.4 to +3.0 bpm** for one to several drinks (Grosicki; Strüven). A 10 bpm figure would require a very large dose in a young, sensitive individual, and no controlled study I found reports a group mean anywhere near it.

**What alcohol does to respiratory rate, skin temperature and SpO2: an evidence gap.** Physiologically, ethanol causes cutaneous vasodilation (distal skin temperature should rise) and relaxes upper-airway musculature (snoring, apnoea, SpO2 dips). I found **no peer-reviewed wearable study quantifying alcohol's effect on nocturnal respiratory rate, skin-temperature deviation, or SpO2**. Oura's blog asserts airway relaxation and reduced saturation but supplies no numbers. **Mark any claim in this area as unsourced.** This matters: it means we do not know whether alcohol produces a *temperature* signature that would separate it from, or make it indistinguishable from, an infection.

#### Exercise — timing dominates strain

Leota J, Presby DM, Le F, Czeisler MÉ, Mascaro L, Capodilupo ER, Wiley JF, Drummond SPA, Rajaratnam SMW, Facer-Childs ER. *Nature Communications* 2025;16:3297 `[verified]`. n = 14,689 physically active individuals, **4,084,354 person-nights**, WHOOP, one year. Full effect grid (change vs reference night, SE in parentheses):

| Exercise ends | Light strain | Moderate | High | Maximal |
|---|---|---|---|---|
| **RHR (bpm)** 0-2 h pre-sleep | +2.02 (0.05) | +3.34 (0.07) | +4.14 (0.09) | **+5.94 (0.22)** |
| 2-4 h | +0.45 (0.02) | +1.77 (0.04) | +2.91 (0.07) | +4.34 (0.15) |
| 4-6 h | +0.40 (0.01) | +0.94 (0.03) | +1.58 (0.06) | +2.82 (0.11) |
| **HRV (ms)** 0-2 h | -4.55 (0.14) | -9.87 (0.24) | -12.47 (0.39) | **-17.02 (0.72)** |
| 2-4 h | -1.18 (0.05) | -3.81 (0.12) | -6.41 (0.19) | -9.48 (0.42) |
| 4-6 h | -1.18 (0.04) | -2.44 (0.08) | -3.80 (0.12) | -5.76 (0.29) |
| **Sleep onset delay (min)** 0-2 h | +3.99 (0.27) | +15.14 (0.65) | +25.36 (0.97) | **+39.99 (2.38)** |
| **TST change (min)** 0-2 h | -8.35 (0.27) | -15.03 (0.65) | -20.69 (0.98) | **-30.62 (2.13)** |

Authors' conclusion: "exercise bouts ending ≥4 hours before sleep onset are not associated with changes in sleep."

Supporting controlled work: Myllymäki T, Rusko H, Syväoja H, Juuti T, Kinnunen ML, Kyröläinen H. *Eur J Appl Physiol* 2012 `[verified]`. n = 14 healthy men, five running sessions (45/60/75 % VO2max x 30/60/90 min). Increased **intensity** raised nocturnal HR (p < 0.001) but **did not** change nocturnal HRV; only the **90-minute duration** lowered nocturnal HRV (p < 0.01). Subjective and actigraphic sleep quality were unaffected. **Take-away: intensity moves HR, duration moves HRV.** That is a usable pattern distinction.

**On delayed / next-night effects and DOMS:** I found **no** well-powered study quantifying a *second-night* elevation in overnight HR/HRV attributable specifically to delayed-onset muscle soreness in a consumer-wearable population. This is a real evidence gap and is exactly the regime where exercise becomes hard to distinguish from infection (the workout was two days ago, steps yesterday were normal, but recovery metrics are still suppressed). **Treat "DOMS suppresses next-night HRV" as physiologically plausible but not established in this literature.**

#### Sleep restriction

Zhang et al. 2025, *Frontiers in Neurology* 16:1556784 `[verified via search summary]`. Systematic review and meta-analysis, **11 studies, 549 participants**: sleep deprivation → **rMSSD SMD = -0.24** (significant), **SDNN reduction non-significant**, **LF and LF/HF significantly increased**, **HF decreasing but non-significant**. The authors explicitly caution the physiological impact "may be limited or only significant under specific conditions." So: sleep loss is a **real but small** HRV confounder — much smaller than alcohol or evening exercise. Note this meta-analysis is on *total* sleep deprivation; partial restriction (the realistic student case) will be smaller still.

#### Stress

Bloomfield LSP, Fudolig MI, Kim J et al. *PLOS Digital Health* 2024;3(4):e0000473 `[verified]`. n = **525 first-year college students**, Oura Ring, Oct-Dec 2022 (i.e. through a midterm/finals period). Cohort means: TST 7.41 h (SD 0.83), RHR 62.75 bpm (SD 8.64), HRV 68.24 ms (SD 33.09), respiratory rate 15.56 breaths/min (SD 1.61). **64 % of weekly responses indicated moderate-to-high stress (PSS ≥ 14).** Odds of high stress per unit increase: TST +1 h **OR 0.617** (p<0.01); RHR +1 bpm **OR 1.036** (p<0.01); HRV +1 ms **OR 0.988** (p<0.05); respiratory rate +1 breath/min **OR 1.230** (p<0.01).

This is the most directly relevant paper in the whole review for our user population, and it says the wearable channels we would use to detect infection are also the channels that detect stress. Note the base rate too: **64 % of student-weeks are moderate-to-high stress.**

#### Menstrual cycle — exact magnitudes

- Goodale BM, Shilaih M, Falco L et al. "Wearable Sensors Reveal Menses-Driven Changes in Physiology and Enable Prediction of the Fertile Window." *J Med Internet Res* 2019;21(4):e13404 `[verified]`. n = **193 participants, 708 analysed cycles**, Ava bracelet worn on dorsal wrist during sleep. Late luteal vs follicular: **wrist skin temperature +0.44 °C (P<.001)**, **heart rate +3.91 bpm (P<.001)**, **HRV -0.32 ms (P<.05)**, **respiratory rate +0.60 breaths/min (P<.001)**. Fertile-window detection accuracy 90 % (95 % CI 0.89-0.92).
- Maijala A, Kinnunen H, Koskimäki H, Jämsä T, Kangas M. *BMC Womens Health* 2019;19:150 `[verified]`. n = 22 (Oura ring). Nocturnal **finger skin temperature difference luteal vs follicular = 0.30 °C (SD 0.12, p<0.001)**; oral basal body temperature difference **0.23 °C (SD 0.09)**; the skin-temperature difference was significantly *larger* than oral BBT (mean difference 0.07 °C, p = 0.003). **21 of 22 participants showed ≥0.15 °C separation.**
- Alzueta E et al. *J Biol Rhythms* 2024;39(5):395-412 `[verified]`. n = **96** (56 aged 18-35, 40 aged 42-55), Oura Gen 2. HR **higher in ovulatory, mid- and late-luteal phases vs menses in both age groups (p < 0.01)**. rMSSD **significantly lower in late luteal vs menses only in the young group (p = 0.019)**. **No significant change** in Oura sleep duration, sleep-onset latency or WASO across the cycle.
- ECG gold standard (reported across this literature): luteal-phase resting HR rise of **2.3-3 bpm**; wearable studies span **2-7 bpm**; one prospective study of 91 women found **+3.8 bpm** mid-luteal vs menses.

#### Vaccination

- Quer G, Gadaleta M, Radin JM et al. *npj Digital Medicine* 2022;5:49 `[verified]`. n = **5,674** with adequate RHR data (76 % Fitbit, 20 % Apple Watch). Mean RHR increase **dose 1: +0.56 bpm (95 % CI 0.48-0.65)**, peak day 2, baseline by **day 4**; **dose 2: +1.52 bpm (95 % CI 1.42-1.63)**, peak day 2, baseline by **day 6**. 71 % / 76 % had any increase; **37 % / 47 % exceeded one SD above their normal**. Moderna +0.85 vs Pfizer +0.44 bpm (dose 2, p<0.001). Age <40: +0.79 vs ≥40: +0.60 bpm (p=0.011). Sex (dose 1 only): female +0.37 vs male +0.21 (p=0.014). Prior COVID infection (dose 1): +0.66 vs +0.28 bpm (p=0.008). Sleep **+35 min day 1 (CI 33-39)**, steps **-1,628 day 1 (CI -1,726 to -1,530)**, both back to baseline by day 2. **Correlation between RHR change and sleep/activity change was near zero (r = -0.01 to 0.02)** — the autonomic and behavioural responses are essentially independent.
- Gepner Y et al. (Yechezkel et al.) *Communications Medicine* 2022;2:27 `[verified]`. n = **160** (median age 40, 56 % female), FDA-cleared Biobeat chest-patch PPG, **13 vitals at 10-minute resolution**. After **dose 2**: heart rate peak **+9.85 % (90 % CI 7.71-11.99)** within the first 48 h, back to baseline by **day 3**; respiratory rate and skin temperature significantly increased over the same 48 h; **"no robust signal from the HRV measure"**; **no significant change in SpO2**. After **dose 1** (n = 24 subset): **no difference in vitals during the first 48 h.**
- **Why the two studies disagree in magnitude:** Quer's +1.52 bpm is a *nightly-average smartwatch RHR* over a 24 h day; Gepner's +9.85 % is a *continuous peak* over 48 h. The continuous measure captures a transient the nightly aggregate dilutes. Both are correct; they measure different things. Our system sees the *nightly aggregate*, so **Quer's +1.5 bpm mean / 47 % exceeding 1 SD is the operationally relevant figure.**

#### Travel

Willoughby AR, Vallat R, Ong JL, Chee MWL. *Sleep* 2025;48(7):zsaf077 `[verified]`. **64,847 trips from 57,240 Oura Gen3 users, 1,469,123 sleep periods**, ages 18-80 (mean ~44, 56 % female). Night-before-travel TST change: short eastward **-17.88 min**, short westward **-13.57 min**, long eastward **-61.87 min**, long westward **-20.22 min**. Duration recovers to within ~12 min of baseline after ~2 days; **sleep timing did not fully return to baseline within the 15-day post-travel window**, with ~1 h shifts in wake time. Long eastward travel: sustained increased WASO and light sleep, decreased deep and REM, for **5-6 days**; REM reduction "could last over a week". Older individuals showed smaller duration reduction (0.37 min per year of age); sex differences minimal (men -7.15 min, women -4.47 min). No heart-rate results reported in the material I retrieved.

#### Altitude

- Lang et al. 2026, *Frontiers in Physiology* 17, doi:10.3389/fphys.2026.1747092 `[verified]`: miners at ~3,800 m, nocturnal **SpO2 97.6 ± 0.5 % (sea level) → 87.8 ± 3.0 % (high altitude)**, nocturnal BP increased, "parasympathetic-related HRV indices decreased significantly at HA."
- Patterson et al. 2026, *J Sleep Res* 35(4), doi:10.1111/jsr.70326 `[verified]`: adolescents resident at 3,620 m, mean nocturnal SpO2 **87.8 ± 1.8 %**; at 4,060 m, **84.8 ± 2.2 %**.
- **Gap:** I could not find good data for the *moderate* altitude band (1,500-3,000 m) that a typical traveller actually encounters, nor for the acute-ascent time course in a consumer-wearable population. Treat moderate-altitude effects as unquantified.

#### Ambient temperature

This is the weakest-evidenced item in the table and I want to be explicit about that. Skin temperature deviation is, by construction, a measurement of the skin, and the skin sits at the boundary between the body and the room. The classic thermoregulatory work (Kräuchi, Cajochen & Wirz-Justice, *J Sleep Res* 2004, doi:10.1111/j.1365-2869.2004.00398.x; Romeijn et al., *Sleep* 2012;35:1673-83, doi:10.5665/sleep.2242) establishes that the **distal-proximal skin temperature gradient** is the physiologically meaningful quantity and that it is strongly modulated by both sleep state and environment. **I found no study quantifying, in a consumer wearable, how many degrees of apparent "temperature deviation" a given change in bedroom temperature produces.** Any claim in this area in our project should be flagged as an assumption, not a finding.

#### Medications

Beta blockers reduce resting HR by roughly **8-14 bpm** across dose quintiles (Gullestad et al., MERIT-HF, *JACC* 2005, doi:10.1016/j.jacc.2004.10.032 `[verified]`); Kjekshus 1986 notes ≥15 bpm reduction is achievable. **I did not verify magnitudes for stimulants, antihistamines or SSRIs in this pass** — the general pharmacology (stimulants and anticholinergic antihistamines raise HR and antihistamines impair sweating/thermoregulation; SSRIs modestly raise HR and reduce HRV) is textbook but I am not citing a specific effect size and should not pretend to. **The structurally important point is that medications are mostly a *baseline* problem, not an *acute* one** — they shift where the personal baseline sits, and they only look like an event when the drug is started, stopped, or a dose is missed. Beta blockers additionally create a *false-negative* risk by capping the HR response to infection.

#### Sensor artifact

Gorny AW et al. *JMIR mHealth uHealth* 2017;5(10):e157 `[verified]`: Fitbit Charge HR under free-living conditions, ICC 0.83, mean underestimation **-5.96 bpm (SE 0.18)** overall, **-4.22 bpm (SE 0.15)** at low intensity, **-16.2 bpm (SE 0.74)** during MVPA; sensitivity for detecting MVPA only 52.9 %, declining over extended monitoring. Reithe H et al., *Biomed Eng Online* 2025;24:22 `[verified]`: three consumer devices "are not interchangeable", with the Oura ring showing particular limitations in concurrent HR and movement recording. Guerrero-Blázquez et al. 2026 (*Sensors* 26(3):828) report **MDC90 = 19.57 bpm** in a motion-affected population, and identify "involuntary movements, altered muscle tone, low body weight, and reflective sensors on the wrist" as accuracy-compromising factors.

For contrast, the *best-case* measurement noise floor: a 2025 validation in *Physiological Reports* (Dial et al., doi:10.14814/phy2.70527) reports **Oura Gen 4 nocturnal HRV CCC = 0.99, MAPE 5.96 ± 5.12 %; Oura Gen 3 CCC = 0.97, MAPE 7.15 ± 5.48 %** `[secondary]`. At a cohort mean rMSSD of ~68 ms, a 6 % MAPE is **~4 ms of measurement noise** — which is the *same size* as the per-drink alcohol effect (-3.3 to -3.8 ms). **For a single night, the alcohol HRV effect sits roughly at the device's own noise floor.** Reliable inference requires either multi-night aggregation or corroboration across channels.

---

## 3. THE SEPARABILITY MATRIX

The question: given only **resting HR, HRV, respiratory rate, skin-temperature deviation, SpO2, sleep stages/duration, steps**, can the system distinguish this confounder from acute respiratory infection *without asking the user*?

Verdict codes: **SEP** = separable from sensors alone; **PART** = partly separable, fails in an important regime; **NO** = genuinely not separable without asking.

| # | Confounder | Verdict | Basis for separation (or why it fails) | Question that would resolve it |
|---|---|---|---|---|
| 1 | **Acute alcohol** | **NO on night 1; SEP by night 3** | *Channel pattern is identical* to early infection (RHR↑, HRV↓, sleep worse) and magnitude is comparable or larger. The only sensor-visible discriminator is **duration**: alcohol resolves in one night (Strüven: RHR back to near-baseline immediately post-exposure), infection persists and escalates. But waiting 2 nights destroys the point of early warning. Secondary weak cue: alcohol's effect is largest in the **first 3 h of sleep** and decays across the night (Pietilä); infection's elevation is flat across the night. That within-night shape exists in intraday HR but not in nightly summaries. | "Did you drink alcohol last night? Roughly how many drinks?" |
| 2 | **Acute / intense exercise** | **PART** | **Steps / activity move in opposite directions**: exercise → activity ↑ on the preceding day; infection → activity ↓ (but Snir 2024 shows the activity drop happens *after* testing, i.e. after symptoms, so it may not help pre-symptomatically). Also **Myllymäki's dissociation**: high intensity moves HR without moving HRV; long duration moves HRV. Infection moves both plus temperature. **Fails when:** the workout is not step-based (swimming, cycling, lifting), the device was off, or the confound is a day-2 residual with normal intervening activity. | "Did you train hard yesterday or the day before? How hard, and what time did you finish?" |
| 3 | **Sleep restriction / fragmentation** | **PART** | **TST and sleep continuity are directly measured** — the cause is visible in the channel. If TST is 4.5 h and RHR is up 3 bpm, short sleep is a sufficient explanation. **Fails because** it does not tell you *why* sleep was short: infection also fragments sleep, so short-sleep-plus-elevated-RHR is consistent with both, and the sensor cannot distinguish "chose to stay up" from "woke feeling awful". Magnitude helps a little: the sleep-loss HRV effect is small (SMD -0.24) relative to infection. | "Was last night's short sleep by choice, or were you feeling unwell?" |
| 4 | **Acute psychological stress** | **NO** | **The worst mimic.** Bloomfield 2024 shows stress raises RHR and respiratory rate and lowers HRV and TST — three or four of the same channels, in the same direction, over days. There is *one* theoretical discriminator: stress causes peripheral **vasoconstriction** (distal skin temperature should fall) while infection causes fever (distal skin temperature rises). **But I found no wearable study quantifying the stress → distal skin temperature effect**, so this discriminator is unvalidated. Until it is, treat stress and infection as physiologically indistinguishable on these channels. | "Anything unusually stressful going on — deadline, exam, bad news?" |
| 5 | **Menstrual luteal phase** | **NO from raw physiology; SEP given cycle history** | All four channels move in the infection direction (temp +0.44 °C, HR +3.91 bpm, RR +0.60 br/min, HRV -0.32 ms). Magnitude is *larger* than the mean vaccine response and comparable to a mild infection. Two discriminators exist but neither is available from one night: (a) **periodicity** — the pattern recurs every ~28 days, so with ≥2 cycles of history the phase is predictable; (b) **shape** — the luteal rise is a sustained ~10-14 day plateau, not a 3-5 day spike. **For a new user with no history, this is unresolvable without asking.** | Once: "Do you menstruate? When did your last period start?" Then it becomes a modelled covariate, not a repeated question. |
| 6 | **Vaccine reactogenicity** | **NO** | Physiologically it *is* an immune response — the same effector pathway as infection (cytokine-driven fever and tachycardia). Peak day 2, resolution days 3-6, same channels, same direction. Gepner's "no SpO2 change" is shared with mild infection, so SpO2 does not help. There is no sensor basis for separation, and none should be expected. **However it is the cheapest confounder to resolve**: the event is discrete, recent, memorable and perfectly known to the user, so a single binary question carries close to a full bit. | "Did you get a vaccination in the last 3 days?" |
| 7 | **Travel / jet lag** | **PART → SEP** | **Sleep timing (midpoint) shifts by ~1 h and does not recover for >15 days** — a phase jump of that size has no infectious analogue. That is a strong sensor-visible signature. Also: the disruption starts the *night before* departure (TST -18 to -62 min), i.e. it *precedes* rather than follows the physiological anomaly. **Fails for** short trips within a time zone; the first night is ambiguous. (Phone timezone would make this trivial, but timezone is not in the listed channel set.) | "Have you flown or changed time zone in the last week?" |
| 7b | **Altitude** | **SEP** | **SpO2 is the discriminator and it is unique to this confounder.** Nothing else on the list drops nocturnal SpO2 by ~10 points; mild URI does not. A large SpO2 drop with elevated HR is altitude (or a serious respiratory event), not a cold. **Caveats:** consumer SpO2 accuracy is poor; moderate altitude (1,500-2,500 m) produces much smaller drops that may not clear the noise floor; and I found no moderate-altitude data. | "Are you somewhere high up?" (rarely worth asking — sensor usually settles it) |
| 8 | **Ambient heat / cold** | **PART (weak)** | Structural argument: an environmental thermal offset should move **skin temperature alone**, with HR/HRV/RR either unmoved or moved much less; an infection moves them together. So a *lone* temperature excursion with no autonomic corroboration is more likely environmental. **This is reasoning, not evidence** — I found no study quantifying it, and heat exposure does also raise HR. Treat as a hypothesis. | "Was your room unusually hot or cold last night?" |
| 9a | **Caffeine** | **PART** | Caffeine's footprint is overwhelmingly in the **sleep** channel (TST -45 min, efficiency -7 %, N3 -11.4 min) with weak and inconsistent HR/HRV effects. So: degraded sleep **without** temperature, respiratory-rate or strong HR movement points away from infection. **Fails** if the dose is large and late enough to produce sympathetic arousal. | "Did you have caffeine late yesterday?" (low value — small effect, and the sleep channel already shows it) |
| 9b | **Late meals** | **SEP (by irrelevance)** | Effect is **+0.73 bpm** nocturnal HR (preprint, grade C) — below the measurement noise floor of most devices. It cannot generate a false alert on its own. | Not worth asking. |
| 9c | **Nicotine** | **NO (but unquantified)** | Acute nicotine raises HR and lowers HRV like everything else on this list, and constricts peripherally so may lower distal temperature. Because habitual smokers smoke daily, this is mostly folded into the **personal baseline** rather than appearing as an event — except for changes in pattern. **Magnitudes not verified in this pass.** | "Has your smoking/vaping changed recently?" (asked rarely) |
| 10 | **Medications** | **NO from sensors; SEP from a one-off profile** | Chronic medication shifts the *baseline*, and a baseline shift is invisible to a deviation-from-baseline detector once it has re-converged. The dangerous cases are **starting, stopping, or missing a dose** — a step change in RHR with no other channel moving. That pattern is suggestive but not diagnostic. Beta blockers additionally **blunt sensitivity** (a false-negative risk, not a false-positive one). | Once at enrolment: "Are you on any regular medication?" Then only on change. |
| 11 | **Illness recovery tail** | **SEP from system memory, NO from physiology alone** | Radin 2021: RHR does not return to baseline until **~79 days** after COVID symptom onset; 13.7 % remain >5 bpm elevated for >133 days; sleep recovers at day 24, steps at day 32. There is a **transient bradycardia phase around days 9-15** that is actually a distinctive marker. Physiologically a residual elevation looks like a new elevation. **But the system knows it detected an episode 6 weeks ago** — resolvable from state, not from sensors, and not by asking. | "Are you still recovering from the illness in [month]?" — useful for confirming, not detecting. |
| 12 | **Sensor artifact / poor wear** | **PART → SEP if SQI is exposed** | Diagnosable from **data-quality signatures**: coverage gaps, physiologically implausible jumps, single-channel step changes with no cross-channel corroboration, and known bias directions (Fitbit under-reads HR by ~6 bpm, up to 16 bpm under motion). Loose fit tends to make skin temperature drift toward ambient. **Fails when** the consumer API exposes only smoothed nightly aggregates with no signal-quality index — which is common. A platform limitation, not a physiological one. | "Did you wear the device normally last night?" (low information; users often do not know) |

### 3.1 Summary of the separability finding

**Genuinely separable from sensors alone:** altitude (via SpO2), late meals (too small to matter), sensor artifact (if quality metrics are available), illness recovery tail (from system state).

**Partly separable — works in the common case, fails in the important edge case:** exercise, sleep restriction, travel, caffeine, ambient temperature.

**Genuinely NOT separable — asking is the only resolution:** **acute alcohol on the first night, acute psychological stress, luteal phase in a user without cycle history, vaccine reactogenicity, medication changes.**

Those five cover, by base rate, the large majority of nights on which a wearable early-warning system will produce an anomaly in a healthy young adult. **This is the evidential basis for the claim that an asking policy is necessary rather than decorative.** The converse deserves equal honesty: for altitude, for late meals, and for large late-evening workouts the device recorded, asking is redundant and would be pure burden. A well-designed policy must be able to say "no question needed" as readily as "ask".

### 3.2 The strongest empirical corroboration

The most direct evidence that these confounders actually fire in a deployed system is Alavi et al. 2022 `[verified]`:

> Alavi A, Bogu GK, Wang M, et al. "Real-time alerting system for COVID-19 and other stress events using wearable data." *Nature Medicine* 2022;28(1):175-184. doi:10.1038/s41591-021-01593-2

n = 3,318 enrolled, 2,155 with wearable data, 84 confirmed COVID-19 cases with sufficient data. NightSignal algorithm: **80 % sensitivity** (67 of 84 detected at or before symptom onset), **87.7 % specificity**, pre-symptomatic detection at a **median of 3 days before symptom onset**. Critically: **1.15 alert-days per person** in COVID-negative individuals versus **3.42 alert-days per person** in COVID-positive, over a 21-day window. The paper explicitly enumerates non-COVID alert triggers: **stress and work stress, alcohol consumption, intense exercise, travel, poor sleep, COVID-19 vaccination (both doses), altitude changes, other respiratory infections (*Mycoplasma pneumoniae*), and the winter holiday period (1.4-fold increase in alerts).** 73 % of participants found the red-alert frequency acceptable.

`[my arithmetic]` 1.15 alert-days per 21 days annualises to roughly **20 alert-days per person-year** from non-infectious causes. Against ~2-3 genuine respiratory infections per year, that implies a **positive predictive value on the order of 10-15 %** — consistent with the ~20-40 : 1 prior odds computed from base rates in §4.

---

## 4. BASE RATE TABLE

These are the priors. Where a figure is a survey self-report I say so, because self-report and sensor-measured behaviour frequencies differ.

| Event | Population frequency | Population / method | Grade | Citation | Flag |
|---|---|---|---|---|---|
| **Alcohol consumed on a given day** | **29.9 %** of person-days (1,529,080 of 5,109,185) | 20,968 WHOOP users, self-logged, 1 year | B | Grosicki et al. 2026, *PLOS Digit Health* 5(3):e0001284 | `[verified]` |
| Drinking pattern | Males drink more frequently and in greater quantity at all ages; older adults drink **more frequently but fewer drinks per occasion** | same | B | same | `[verified]` |
| **Insufficient physical activity (adults, global)** | **31.3 % (95 % CI 28.6-34.0)** in 2022; 26.4 % in 2010; 23.4 % in 2000. Female 33.8 %, male 28.7 % | 507 surveys, 163 countries | B | Strain et al. 2024, *Lancet Glob Health* 12(8):e1232-43 | `[verified]` |
| ⇒ **~69 % of adults meet activity guidelines** — a majority are exposed to the exercise confounder | — | derived | — | — | `[my arithmetic]` |
| **Habitual short sleep (<7 h)** | **34.8 %** of US adults | BRFSS, self-report | B | Liu et al. 2016, *MMWR* 65(6):137-41 | `[verified]` |
| **Moderate-to-high perceived stress (students)** | **64 %** of weekly responses (PSS ≥ 14) | 525 first-year college students, autumn term | B | Bloomfield et al. 2024 | `[verified]` |
| **Luteal phase (menstruating user)** | **~45 % of days** (≈12-14 luteal days per ≈28-day cycle) | derived from standard cycle physiology | — | Goodale 2019; Maijala 2019 for phase definition | `[my arithmetic]` |
| **Symptomatic influenza per season** | **8.3 % (95 % CI 7.3-9.7)** all ages; **8.9 % (8.2-9.9)** adults 18-64. Meta-analytic estimate lower: 7.1 % all ages, **5.1 % (3.6-6.6)** adults. Season range **3-11 %** | US, 2010-2016 | B | Tokars, Olsen & Reed 2018, *Clin Infect Dis* | `[verified]` |
| **Influenza infection (incl. asymptomatic) per winter, unvaccinated** | **18 % (95 % CI 16-22)** | Flu Watch, UK community cohort | B | Hayward et al. 2014, *Lancet Respir Med* | `[verified]` |
| **Respiratory illnesses per 100 person-influenza-seasons** | **44** in influenza-uninfected; **69** in influenza-infected; attributable ≈ 23 per 100 | Flu Watch | B | Hayward et al. 2014 | `[verified]` |
| Healthcare-seeking | Only **17 %** of PCR-confirmed influenza cases consulted a doctor; only **25 %** of serologically confirmed infections were PCR-confirmed | Flu Watch | B | Hayward et al. 2014 | `[verified]` |
| **Respiratory virus detected in a given person-week** | **26 %** of 4,166 person-weeks; symptoms reported in **23 %** of person-weeks; of 783 viral detection episodes, **56 % were symptomatic** | 26 households, 108 individuals, weekly PCR, 1 year (households included young children — over-states the adult rate) | B | Byington et al. 2015, *Clin Infect Dis* (BIG-LoVE) | `[verified]` |
| **New symptomatic ARI prodrome nights per year (adult)** | ≈ **2.5 % of nights** (≈3 symptomatic episodes/year x ≈3 prodromal nights ÷ 365) | derived | — | — | `[my arithmetic]` — the "3 colds/year" input is **grade F folklore**; see note |
| **Non-infectious wearable alert-days** | **1.15 per person per 21 days** in COVID-negative individuals (≈ **20 per person-year**) | 3,318-participant deployed smartwatch alerting study | B | Alavi et al. 2022, *Nat Med* 28:175-84 | `[verified]` + `[my arithmetic]` for annualisation |
| **Winter holiday period** | **1.4-fold increase** in alerts | same | B | Alavi et al. 2022 | `[verified]` |
| **Notifications received per day (all sources)** | **63.5 per day** | 15 users, 1 week, in-situ logging | C (small n) | Pielot, Church & de Oliveira 2014, MobileHCI | `[verified]` |
| **Vaccination events per adult per year** | **Not reliably sourced.** Order of magnitude 1-2/year for someone taking annual influenza vaccination plus occasional COVID boosters. US adult influenza coverage is commonly cited near 45-50 % but I did **not** verify a primary source. | — | **F / unverified** | — | gap |
| **Trips crossing ≥2 time zones per person-year** | **Not sourced.** Willoughby's dataset has 64,847 trips from 57,240 users, suggestive of ~1 trip/user/period, but I did not verify the denominator. | — | **unverified** | Willoughby 2025 | gap |

**A note on "adults get 2-3 colds a year".** This figure is ubiquitous and usually attributed vaguely to CDC. In this research pass I **could not retrieve a primary epidemiological source for it.** The defensible peer-reviewed anchors are: Flu Watch's **44 respiratory illnesses per 100 person-winter-seasons** in influenza-uninfected people, and BIG-LoVE's **26 % of person-weeks with a virus detected, 56 % of detections symptomatic** in households containing young children. Both put the "2-3 per year" figure in the right region for adults but **it should be marked grade F until a primary source is attached.**

**The prior-odds calculation that matters.** On a randomly chosen night for a young adult user:

| Event | P(on a given night) | Source |
|---|---|---|
| Drank alcohol | ≈ 0.30 | Grosicki 2026 `[verified]` |
| Luteal phase (if menstruating) | ≈ 0.45 | derived `[my arithmetic]` |
| Moderate-to-high stress week (student) | ≈ 0.64 | Bloomfield 2024 `[verified]` |
| Short sleep | ≈ 0.20-0.35 | Liu 2016 `[verified]` |
| Hard evening exercise | ≈ 0.10-0.30 | **not directly sourced** |
| **New ARI prodrome night** | **≈ 0.025** | derived `[my arithmetic]` |

`[my arithmetic]` Even counting only alcohol + luteal + hard exercise as roughly disjoint causes, confounder nights outnumber prodrome nights by roughly **20-40 : 1**. This single ratio determines everything downstream: with a likelihood ratio of even 5:1 from sensors alone, the posterior probability of infection after an anomaly stays well below 50 %. That is the quantitative case for acquiring more information rather than alerting.

---

## 5. ACUTE RESPIRATORY VIRAL INFECTION — the target signature

### 5.1 Timing relative to symptom onset

| Source | Finding | n | Grade | Flag |
|---|---|---|---|---|
| Snir S, Chen Y, Yechezkel M, Patalon T, Shmueli E, Brandeau ML, Yamin D. *Lancet Reg Health Eur* 2024;42:100934 | Heart-rate anomalies precede **symptom onset** by **73 h (95 % CI 67-78) for influenza**, **23 h (18-27) for COVID-19**, **62 h (54-68) for GAS**. Largest HR changes occur **67.6 h (62.8-72.5) before testing for influenza**, **64.1 h (61.4-66.7) for COVID-19**, **58.2 h (52.1-64.2) for GAS**. Delay from symptom onset to testing: **39 h influenza, 53 h COVID-19, 38 h GAS**. Reductions in physical activity and social contact occurred **after** testing. | 4,795 | B | `[verified]` |
| Mishra T, Wang M, Metwally AA, et al. *Nat Biomed Eng* 2020;4:1208-20 | 32 COVID-19 cases from ~5,300 participants. **26/32 (81 %)** had alterations in HR, daily steps or sleep. **22 of 25** with symptom information were detected **at or before symptom onset**; 4 detected **≥9 days earlier**. A two-tier RHR-elevation warning system would have detected **63 %** pre-symptomatically in real time. | 32 cases | B | `[verified]` |
| Alavi A, et al. *Nat Med* 2022;28:175-84 | Pre-symptomatic signals at a **median of 3 days before symptom onset**; **80 %** of infected individuals alerted; specificity 87.7 %. | 84 cases / 3,318 | B | `[verified]` |
| Mason AE, et al. *Sci Rep* 2022;12:3463 (TemPredict) | Oura data from **63,153** participants; algorithm identified COVID-19 an average of **2.75 days before participants sought testing**, **sensitivity 82 %, specificity 63 %**. | 63,153 cohort / 73 training cases | B | `[verified]` |
| Grzesiak E, et al. *JAMA Netw Open* 2021;4(9):e2128534 | **Human challenge study** — the only grade-A design here. 31 participants inoculated with H1N1, 18 with rhinovirus, E4 wristband (skin temperature, HR, movement). Infection vs non-infection classified with **92 % accuracy (H1N1)** and **88 % (rhinovirus)**; mild vs moderate severity distinguished **24 h before symptom onset** with 90 % / 89 % accuracy; models exceeded 80 % accuracy **12-36 h before symptom onset**. | 49 | **A** | `[verified]` |

**A discrepancy worth flagging:** Snir gives ~1 day of pre-symptomatic lead for COVID and ~3 days for influenza; Alavi and Mason give ~3 days for COVID; Mishra reports outliers at ≥9 days. The honest summary is **a lead time of roughly 1-3 days, occasionally longer, differing by pathogen** — influenza appears to give more warning than SARS-CoV-2.

### 5.2 Magnitudes

- **Skin temperature:** mean **+0.63 °C** fever-like deviation, with **93 % of cases showing a fever-like abnormality within seven days before symptom onset** `[secondary]` — this came via a search summary of the wearable-infection literature and I could not attach it to a specific paper with confidence. **Provisional; re-verify before citing.**
- **Resting heart rate:** average peak increase relative to baseline of **1.8 % (females)** and **3.4 % (males)** `[secondary]`, followed by a nadir ~13 days after symptom onset, a second peak ~28 days, and return to baseline ~112 days. This trajectory description is consistent with Radin 2021's transient-bradycardia-then-prolonged-tachycardia pattern but the specific percentages came from a search summary. **Provisional.**
- `[my arithmetic]` A 1.8-3.4 % RHR increase on a base of ~63 bpm is **+1.1 to +2.1 bpm**. **That is smaller than the alcohol effect at one drink (+2.4 to +2.8 bpm), smaller than moderate evening exercise (+3.34 bpm), and smaller than the luteal-phase effect (+3.91 bpm).** This is arguably the single most important quantitative fact in this document: **at the population-mean level, the infection signal is smaller than three of its most common confounders.** Detection works at all only because it is (a) multi-channel, (b) within-person, and (c) sustained over multiple days.
- **Prolonged tail** (Radin JM, Quer G, Ramos E, Baca-Motes K, Gadaleta M, Topol EJ, Steinhubl SR, *JAMA Netw Open* 2021;4(7):e2115959 `[verified]`): n = 234 COVID-positive (mean age 45.3, 70.9 % female) vs 641 symptomatic COVID-negative. **Transient bradycardia at ~days 9-15**, then prolonged relative tachycardia that did **not return to baseline until ~79 days** after symptom onset. **13.7 % (32/234) sustained RHR >5 bpm above baseline for >133 days.** Sleep returned to baseline at **day 24**, step count at **day 32**.
- **SpO2:** Gepner 2022 found **no significant SpO2 change** after vaccination; I found **no study establishing a reliable consumer-SpO2 drop in mild uncomplicated URI in adults**. The outpatient pulse-oximetry literature is about pneumonia and bronchiolitis, not colds. **Working assumption: SpO2 is not a useful channel for detecting mild respiratory infection, and its main diagnostic value in this system is negative — it discriminates altitude.** Mark as an evidence gap, not a finding.
- **Steps / activity:** Snir 2024 is explicit that **reductions in physical activity and social contact occurred *after* testing**, i.e. after the person already knew they were ill. So the activity channel is **confirmatory, not pre-symptomatic**.

### 5.3 The signature in one line

Multi-day, multi-channel, monotonically escalating: **skin temperature ↑, resting HR ↑, respiratory rate ↑, HRV ↓, sleep more fragmented, SpO2 unchanged, activity unchanged until symptoms then ↓**, with an onset 1-3 days before the person feels anything and a decay tail measured in weeks to months.

---

## 6. ACTIVE SENSING, VALUE OF INFORMATION, AND WHEN TO INTERRUPT

### 6.1 Question 1 — how cheap is exact expected information gain over a small discrete hypothesis set?

**Answer: it is free. The cost is entirely in the likelihood model, not in the computation.**

**Setup.** Let the cause of tonight's anomaly be a discrete latent variable
- H ∈ {h₁ … h_K}, K ≈ 10 (infection, alcohol, exercise, short sleep, stress, luteal, vaccine, travel, altitude, artifact)
- with current posterior p(h) from the sensor evidence.

Let the candidate questions be
- q ∈ {q₁ … q_M}, M ≈ 8
- each with a discrete answer set A_q of size R (binary → R = 2; "how many drinks: 0 / 1-2 / 3-4 / 5+" → R = 4).

Assume a likelihood table **p(a | h, q)** — a K x R matrix per question — encoding both the causal link and the user's answer noise (recall error, under-reporting).

**Exact expected information gain (Lindley 1956).**

```
 Prior entropy: H(H) = - Sum_h p(h) log p(h)

 Answer predictive: p(a | q) = Sum_h p(h) * p(a | h, q)

 Posterior on answer: p(h | a,q) = p(h) * p(a | h,q) / p(a | q)

 Posterior entropy: H(H | a,q) = - Sum_h p(h|a,q) log p(h|a,q)

 EIG(q) = H(H) - Sum_a p(a|q) * H(H | a,q) = I(H ; A_q)
```

EIG(q) is exactly the mutual information between the cause variable and the answer variable. It is non-negative, bounded above by min(H(H), log R), and equals zero iff the answer is independent of the cause.

**Computational cost, exactly.**

| Step | Cost |
|---|---|
| p(a\|q) for all q, a | **M · R · K** multiply-adds |
| p(h\|a,q) for all q, a, h | **M · R · K** multiplies + M·R divisions |
| H(H\|a,q) for all q, a | **M · R · K** log-multiply-adds |
| Outer expectation | M · R |
| **Total** | **Θ(M · K · R)** ≈ **3·M·K·R** flops and **M·K·R** logarithms |

With **M = 8, K = 10, R = 4**: **M·K·R = 320**. So roughly **~1,000 flops and ~320 logarithm evaluations per decision.** In NumPy this is a single (M, R, K) tensor contraction; wall-clock is **tens of microseconds** including interpreter overhead, and **sub-microsecond** in compiled code. Doing it once per night per user is computationally invisible. Even at M = 50, K = 100, R = 10 it is 50,000 operations.

**Two-step (non-myopic) lookahead.** Cost is **Θ(M² · K · R²)** = 8 · 7 · 10 · 16 ≈ **9,000** operations — still free. This matters because myopic EIG is **provably suboptimal** in the classic parity/XOR case: two questions can be jointly informative while each is individually worthless, and a one-step-lookahead policy will refuse to ask either. Given 2-step lookahead costs ~9k operations here, there is no computational excuse for being myopic.

**Full-horizon exact planning.** Optimising the entire question *ordering* with adaptive branching is **Θ(M! · R^M)** in the worst case: 8! · 4⁸ ≈ 40,320 · 65,536 ≈ **2.6 x 10⁹** — this is where it stops being free. So: **exact myopic and exact 2-3-step lookahead are trivial; exact full-horizon is not.** That is the precise feasibility boundary.

**The real cost.** Everything above assumes p(a | h, q) is known. It is not. Populating a 10 x 4 table for each of 8 questions means specifying **320 conditional probabilities**, most of which have no direct empirical support — and this includes modelling the user's *answer reliability* (a person asked "did you drink three nights ago?" has meaningfully imperfect recall, which strictly reduces the mutual information the question can supply; see Benish's channel-capacity result in §6.5). **The bottleneck is knowledge engineering, not compute.** That is the honest answer to the feasibility question.

### 6.2 Question 2 — the standard ways to trade information gain against query cost

Five formulations appear in the literature. They are **not** equivalent and the differences matter.

**(a) Expected net gain of sampling / net value of information — the decision-theoretic gold standard.**
```
 EVSI(q) = E_a [ max_d E_{h|a,q} U(d, h) ] - max_d E_h U(d, h)

 Ask q iff ENGS(q) = EVSI(q) - c(q) > 0
```
U is a utility over decisions d (alert / stay silent / keep watching) and causes h; c(q) is the query cost in the same utility units. Source: Howard RA, "Information Value Theory," *IEEE Trans Syst Sci Cybernetics* 1966;2(1):22-26, doi:10.1109/TSSC.1966.300074 (1,014 citations) `[verified]`; Raiffa & Schlaifer, *Applied Statistical Decision Theory*, 1961.

**The property that separates this from all the others: VoI is exactly zero if the information cannot change the decision.** No matter how much entropy an answer would remove, if you would alert either way, the answer is worth nothing. Entropy-based EIG does **not** have this property — it will happily pay to reduce uncertainty with no action consequence. If our project uses EIG rather than EVSI, that is a real modelling compromise and should be stated as one.

**(b) Lagrangian / penalised objective — the standard in cost-sensitive ML.**
```
 score(q) = EIG(q) - lambda * c(q)
 ask argmax_q score(q); stop when max_q score(q) <= 0
```
lambda converts bits into cost units and is the single tuning knob. This is exactly the reward structure used in **Classification with Costly Features** (Janisch J, Pevný T, Lisý V, AAAI 2019, doi:10.1609/aaai.v33i01.33013959 `[verified]`), where the agent receives a per-feature acquisition penalty plus a terminal classification reward.

**(c) Information per unit cost (ratio / knapsack).**
```
 score(q) = EIG(q) / c(q)
```
Used in budgeted active learning. Simple and scale-free, but has no principled stopping rule — the ratio is always positive, so a separate threshold or budget is needed.

**(d) Explicit budget constraint.**
```
 maximise Sum_{q in S} EIG(q) subject to Sum_{q in S} c(q) <= B
```
The budgeted-querying formulation. Mutual information is **submodular** for many (not all) observation-selection problems, giving greedy selection a (1 - 1/e) approximation guarantee — worth knowing, though the guarantee does not hold universally for *adaptive* information gain.

**(e) Full POMDP.** State = (true cause, user state, time); actions = {ask q₁…q_M, alert, stay silent, wait}; reward = terminal decision utility - Σ query costs. Solving exactly is intractable (POMDP planning is PSPACE-hard; Papadimitriou & Tsitsiklis 1987), which is precisely why myopic and short-horizon approximations dominate practice. Medical precedent: Hauskrecht M & Fraser H, "Planning treatment of ischemic heart disease with partially observable Markov decision processes," *Artificial Intelligence in Medicine* 2000, doi:10.1016/S0933-3657(99)00042-1 (178 citations) `[verified]`.

### 6.3 The full formal toolkit, mapped

| Machinery | Canonical reference | What it gives our problem |
|---|---|---|
| **Value of information** | Howard 1966, *IEEE TSSC* 2(1):22-26 `[verified]` | The correct decision-theoretic criterion; the zero-value-if-no-action-change property |
| **EVPI / EVSI in health** | Siebert, Rochau & Claxton 2013; McCullagh, Walsh & Barry 2012, *PharmacoEconomics* 30(10):941-59; Kim, Trikalinos & Wong 2019, *Med Decis Making* 39(2):119-29 `[verified]` | **Caution:** the health-economics VoI literature is about *research prioritisation* (is another trial worth funding?), not per-patient questioning. Formally identical, operationally different. Cite carefully. |
| **VoI on Bayesian networks** | Constantinou, Yet, Fenton et al. 2015, *Artif Intell Med* 66:41-52 `[verified]` — average value gains of **11-60 %** from resolving unknown risk factors | The closest health application of VoI to *individual-case* evidence gathering |
| **Bayesian experimental design / EIG** | Lindley DV 1956, *Ann Math Stat*, doi:10.1214/aoms/1177728069 (1,536 citations) `[verified]`; Chaloner & Verdinelli 1995 | The EIG formulation in §6.1 |
| **Modern BED** | Rainforth T, Foster A, Ivanova DR, Bickford Smith F, "Modern Bayesian Experimental Design," arXiv:2302.14545, 2023 `[verified]` | Survey; explicitly frames BED's problem as **computational** ("deployment often poses substantial computational challenges"). Useful background, but our discrete case is exactly the regime where those challenges vanish — worth saying so explicitly rather than importing their pessimism. |
| **Uncertainty sampling** | Lewis & Gale 1994 | Simplest acquisition function |
| **Query by committee** | Seung, Opper & Sompolinsky 1992 | Disagreement-based acquisition |
| **BALD** | Houlsby N, Huszár F, Ghahramani Z, Lengyel M, arXiv:1112.5745, 2011 `[verified]` | I[y ; θ \| x, D] — mutual information between the **prediction and the model parameters**, separating epistemic from aleatoric uncertainty. **Important distinction for us:** BALD is about learning the *model*; our problem is identifying the *current cause*, so the correct analogue is plain Lindley EIG over a latent discrete variable, **not** BALD. Do not import BALD by analogy without noting this. |
| **BatchBALD** | Kirsch A, van Amersfoort J, Gal Y, arXiv:1906.08158, 2019 `[verified]` | Batch acquisition accounting for redundancy between simultaneously chosen queries — directly relevant if we ever ask **two questions at once**, because individually-informative questions can be jointly redundant |
| **Sequential hypothesis testing** | Wald A, *Ann Math Stat* 1945, doi:10.1214/aoms/1177731118 (1,679 citations) `[verified]` | The SPRT: accumulate the log-likelihood ratio; stop and accept H₁ at boundary A, accept H₀ at boundary B, otherwise keep observing. Boundaries set directly from target α and β. The natural stopping rule for "watch another night vs decide now". |
| **SPRT deployed in health surveillance** | Kulldorff M, Davis RL, Kolczak MS, Lewis E, Lieu TA, Platt R, *Sequential Analysis* 2011;30(1):58-78, doi:10.1080/07474946.2011.539924 (227 citations) `[verified]` | MaxSPRT — SPRT with a composite alternative, because classical SPRT is "overly sensitive to the alternative hypothesis specification". Used in the US Vaccine Safety Datalink. Precedent for sequential testing on continuously arriving health data. |
| **POMDP** | Kaelbling, Littman & Cassandra 1998; Hauskrecht & Fraser 2000 (medical) `[verified]` | The full formulation; intractable exactly, motivating myopic approximation |
| **Cost-sensitive feature acquisition** | Janisch, Pevný & Lisý, AAAI 2019 `[verified]`; Kachuee et al., "Opportunistic Learning," ICLR 2019 | The Lagrangian formulation; deep-RL policies for "which feature to buy next" |
| **Active feature acquisition with generative surrogate** | Li Y & Oliva JB, ICML 2021 / arXiv:2010.02433 `[verified]` | Reformulates AFA as a generative modelling task; the surrogate "captures the dependencies among input features to **assess potential information gain** from acquisitions" and supplies intermediate rewards. **Note:** the abstract does **not** state the reward is conditional mutual information — I checked specifically. Do not cite it as such without opening the method section. |
| **Active sensing in clinical time series** | Yoon J, Jordon J, van der Schaar M, "ASAC: Active Sensing using Actor-Critic models," MLHC 2019, arXiv:1906.06796 `[verified]` | A selector network chooses what to observe next and a predictor evaluates predictiveness, "balanc[ing] the cost of observing the selected variables with their predictive power", evaluated on real medical datasets. **The closest ML analogue to our sensing problem**, though the "cost" is measurement cost, not user-interruption cost. |
| **RL symptom checking** | Peng YS, Tang KF, Lin HT, Chang EY, "REFUEL," NeurIPS 2018 `[verified]` | Learns which symptom to query next to reach a diagnosis fast; reward shaping plus feature rebuilding. The learned policy implicitly approximates information-efficient querying. |
| **Interruptibility modelling** | Hudson S, Fogarty J, Atkeson C, Avrahami D, Forlizzi J, Kiesler S, Lee J, Yang J, *ACM TOCHI* 2005, doi:10.1145/1057237.1057243 (344 citations) `[verified]` | Simple sensors predict interruptibility "as well as people do"; ~78 % accuracy; a cost-optimised variant avoided unwanted interruptions **90 % of the time at 75 % overall accuracy** |
| **Expected cost of interruption** | Horvitz E & Apacible J, ICMI 2003, doi:10.1145/958432.958440 (270 citations) `[verified]` | Learns models that "estimate the expected user cost of interruptions" from device logs, acoustic/visual analysis and calendar. **This supplies the c(q) term.** But it models only the *cost* of interrupting, never the *gain* from it. |
| **Attention-sensitive alerting** | Horvitz, Jacobs & Hovel, UAI 1999 | Decision-theoretic alerting under attention constraints `[not re-verified this pass]` |
| **Mixed-initiative principles** | Horvitz E, CHI 1999 | Expected utility applied to whether to act or ask `[not re-verified this pass]` |
| **Threshold model for testing** | Pauker SG & Kassirer JP, *NEJM* 1980;302(20):1109-17 `[verified]` | See §6.5 — the most directly transferable idea in the whole literature |
| **Information theory of diagnostic tests** | Benish WA, five papers 1999-2020 `[verified via author search]` | See §6.5 |

### 6.4 A note on Pathfinder

Pathfinder (Heckerman DE, Horvitz EJ, Nathwani BN, "Toward normative expert systems: Part I. The Pathfinder project," *Methods Inf Med* 1992;31(2):90-105; Part II *ibid.* 106-116 `[citation verified]`) is the standard example cited for **myopic expected-value-of-information-driven test recommendation** in a deployed medical diagnostic system (lymph-node pathology). **`[unverified]` I was unable to open the full text in this pass to confirm the VoI mechanism from the primary source.** The citation is solid; the mechanism claim should be checked against the paper before being asserted in the writeup.

### 6.5 Question 5 — what the medical diagnostic test-selection literature transfers

**(i) The threshold model — the single most transferable idea.**
Pauker & Kassirer 1980 `[verified]` define two probabilities: the **testing threshold** (below which you neither test nor treat) and the **test-treatment threshold** (above which you treat without testing). "The test should be performed (with treatment depending on the test outcome) **only if the probability of disease is between the two thresholds**."

Translated directly: **asking the user a question is only worth it if the current posterior probability of infection lies in the ambiguous band.** If the evidence is so weak you would stay silent regardless of the answer, do not ask. If it is so strong you would alert regardless, do not ask. This yields a *probability-band gate* on asking that is far simpler than a full VoI computation and captures most of its benefit. It is also the formal reason a system should be *quiet* most of the time.

**(ii) Mutual information is the right scalar measure of a question's diagnostic value.**
Benish WA has built out this framework over two decades `[verified via author search]`:
- *Med Decis Making* 1999;19(2):202-6 — relative entropy (KL divergence between post-test and pre-test probability distributions) as the measure of diagnostic information.
- *Methods Inf Med* 2003;42(3):260-4 — **mutual information I(D;R)** as "the average amount of information the test result provides about the disease state", explicitly contrasted with ROC analysis and explicitly applicable to **multiple diagnoses** — exactly our situation: ten candidate causes, not two. (ROC/AUC is unusable here for that reason.)
- *Methods Inf Med* 2009;48(6):552-7 — axiomatic derivation: diagnostic information is "the average amount that diagnostic testing reduces our surprise."
- *Methods Inf Med* 2002;41(2):114-18 — **information graphs**: plotting diagnostic information as a function of pre-test probability. This gives the *shape* of when a question is worth asking — information peaks near p ≈ 0.5 and falls to zero at both extremes, the information-theoretic mirror of the Pauker-Kassirer threshold band.
- *Stat Methods Med Res* 2015;24(6):1044-52 — **channel capacity of a diagnostic test as a function of sensitivity and specificity.** This bounds how many bits a question can possibly supply. **Directly applicable: a binary question answered with perfect recall supplies at most 1 bit; a question about three nights ago, answered with imperfect memory, supplies strictly less.** Our likelihood table must encode answer noise or we will systematically over-value questions.
- *Entropy* 2020;22(1):97 — review of information theory applied to clinical diagnostic testing, single and multiple tests.

**(iii) Sequential stopping.** Wald's SPRT gives the stopping rule for "one more night of observation vs decide now", and MaxSPRT (Kulldorff 2011) is the version actually deployed on streaming health data in the Vaccine Safety Datalink, with the practical fix that a composite alternative avoids over-sensitivity to a mis-specified H₁.

**(iv) Cost-sensitive test ordering.** The modern ML re-derivation of this problem (CwCF, REFUEL, Opportunistic Learning, AFA-GSM, ASAC) is formally the same problem with learned rather than elicited likelihoods. Worth noting that the classical literature elicits p(result | disease) from experts while the ML literature learns it from data — and for our confounders, **neither route is fully available**, because there is no dataset labelled with "the true cause of tonight's anomaly."

**(v) The uncomfortable transfer.** In clinical test selection, the "test" is objective and its operating characteristics are measurable. In our problem the "test" is a **human self-report**, whose sensitivity and specificity depend on recall, honesty and framing, and are essentially unmeasured. **The medical test-selection literature transfers the mathematics cleanly and the measurement discipline not at all.** State that limitation up front.

---

## 7. Question 3 — does any published system decide *when to ask* using an explicit information-theoretic criterion, in a health or monitoring context?

**Short answer: partially, and the exact combination we need appears to be unpublished.**

### 7.1 Yes — for *which question to ask*, within a session

| System | Criterion | Domain | Status |
|---|---|---|---|
| **Computerized adaptive testing (PROMIS and successors)** | Maximum-information item selection under item response theory | Clinical patient-reported outcomes — **deployed at scale in real healthcare** | Real, and the strongest existing proof that information-criterion-driven questioning works in health and is tolerated by patients. Numbers `[verified]`: FAMCAT averages **22.05 items (SD 7.98)** from a 60-item bank (Wang et al., *Arch Phys Med Rehabil* 2022;103(5S):S3-S14); FRIDA screening averages **11 items in real patients, 7.8 in simulation, r = 0.94-0.97** vs full scale (Belvederi Murri et al., *J Clin Med* 2025;14(19):6992); multidimensional CATs are **20-25 % shorter** than unidimensional equivalents (Paap et al., *Appl Psychol Meas* 2018;42(5):327-42). |
| **Pathfinder** | Myopic expected value of information (mechanism `[unverified]`) | Lymph-node pathology diagnosis | Historical, influential |
| **Benish's framework** | Mutual information I(D;R) | Diagnostic test evaluation | Theoretical framework, widely cited |
| **REFUEL / CwCF / Opportunistic Learning / AFA-GSM / ASAC** | Learned RL policies approximating cost-aware information gain | Symptom checking, clinical feature acquisition | Research systems, not deployed |
| **MediQ** (Li SS, Balachandran V, Feng S, Ilgen JS, Pierson E, Koh PW, Tsvetkov Y, arXiv:2406.00922, 2024 `[verified]`) | **Confidence and abstention, NOT an information-theoretic criterion** — I checked specifically | LLM interactive clinical reasoning | Benchmark. Notable cautionary finding: "directly prompting state-of-the-art LLMs to ask questions **degrades** performance"; an abstention strategy recovered **+22.3 %** diagnostic accuracy. |

### 7.2 Yes — the closest published work, and it is recent

> **Li J, Ponnada A, Wang WL, Dunton GF, Intille SS. "Ask Less, Learn More: Adapting Ecological Momentary Assessment Survey Length by Modeling Question-Answer Information Gain." *Proc ACM Interact Mob Wearable Ubiquitous Technol (IMWUT)* 2024;8(4):166. doi:10.1145/3699735. PMID 39664111, PMCID PMC11633767.** `[verified]`

This estimates "the potential information gain of each EMA question using question-answer prediction models", then "prioritize[s] the presentation of the most informative question in a question-by-question sequence and skip[s] uninformative questions." Reported results: **mean survey length reduced by 34-56 %**, **real-time prediction accuracy of 72-95 % for the skipped questions**, and when skipping 50 % of questions, **imputation errors 15-52 % lower** than random omission.

This is genuinely a mobile-health system using explicit information gain to decide what to ask a user. **But it decides *which questions to include once a survey has already been triggered* — it does not decide *whether to trigger a prompt at all*, and the trigger is not driven by a physiological anomaly.**

### 7.3 No — for *whether to interrupt at all*, gated on sensor-derived uncertainty

I found **no published system** that:
1. monitors a continuous passive physiological stream,
2. maintains a posterior over a set of candidate causes of an anomaly,
3. computes an explicit expected information gain (or EVSI) for each candidate question,
4. compares it against an explicit interruption cost, and
5. asks only when the net value is positive.

The adjacent work stops one step short in each direction:
- **Horvitz & Apacible 2003** models the **expected cost of interruption** with real sensor data — but there is no information-gain term at all. It answers "how bad would it be to interrupt now", never "how much would interrupting be worth".
- **Hudson / Fogarty et al. 2005** predicts interruptibility from sensors at ~78 % accuracy — same gap.
- **Alavi et al. 2022** deploys a real wearable alerting system, explicitly enumerates the confounders that cause its false alerts, and **asks the user nothing**. It alerts and leaves the user to work it out.
- **The JITAI literature** (Nahum-Shani I, Smith SN, Spring BJ, Collins LM, Witkiewitz K, Tewari A, Murphy SA, *Ann Behav Med* 2018;52(6):446-62, 1,284 citations `[verified]`) decides when to deliver an **intervention**, not when to acquire **information**. The decision variable is "should I nudge", not "should I ask".
- **CAT / PROMIS** selects the next item optimally but only once a session has been initiated by a clinician.

**Assessment for the project: this is a defensible novelty claim, if stated carefully.** The claim is *not* "no one has ever thought of this" — every component is well-established, and the composition is fairly obvious to anyone who knows both literatures. The claim is that **the specific composition — VoI-gated user questioning for confounder disambiguation on a passive wearable stream — does not appear in the published literature I could locate**, and that the confounder evidence in §2-§3 shows the composition is *necessary* rather than gratuitous. State it as "we found no published instance", not "there is none".

---

## 8. NOTIFICATION BURDEN AND EMA COMPLIANCE — the cost parameter

### 8.1 The competitive baseline

Users already receive **63.5 notifications per day** (Pielot M, Church K, de Oliveira R, MobileHCI 2014, n = 15, one week of in-situ logging, doi:10.1145/2628363.2628364, 348 citations `[verified]`). Notifications were "typically viewed within minutes, regardless of whether the phone was in silent mode", driven by social pressure and personal communication. More notifications correlated with negative emotions but also with feelings of connection.

`[my arithmetic]` 63.5/day ≈ **445 notifications per week**. A health agent asking even 7 questions per week adds **1.6 %** to the user's notification load. The relevant burden is therefore almost certainly not volume but **relevance and interruption timing** — which is exactly what Horvitz & Apacible's cost model addresses.

Complementary large-scale data: Shirazi AS, Henze N, Dingler T, Pielot M, Weber D, Schmidt A, "Large-scale assessment of mobile notifications," CHI 2014, doi:10.1145/2556288.2557189, 345 citations `[verified]` — nearly **200 million notifications from over 40,000 users**; identifies what users like and dislike, though the abstract does not give per-user daily rates.

### 8.2 EMA compliance — the hard numbers

| Meta-analysis | Scope | Pooled compliance | Effect of prompt frequency |
|---|---|---|---|
| **Jones A, Remmerswaal D, Verveer I, Robinson E, Franken IHA, Wen CKF, Field M.** *Addiction* 2019;114(4):609-19, doi:10.1111/add.14503 `[verified]` | **126 studies, 19,431 participants** (substance use) | **75.06 % (95 % CI 72.37-77.65)** — below the conventional 80 % target | **No significant association with prompt frequency** (Q(3) = 7.35, p = 0.061); none with assessment-period length (Q(2) = 2.40, p = 0.301) or device (Q(4) = 4.28, p = 0.369). Dependent samples **69.80 %** vs non-dependent **76.02 %**. |
| **Wen CKF, Schneider S, Stone AA, Spruijt-Metz D.** *J Med Internet Res* 2017;19(4):e132, doi:10.2196/jmir.6641 `[verified]` | 42 studies, children and adolescents | **78.3 %** weighted average (clinical 76.9 %, non-clinical 79.2 %) | **Non-clinical:** 2-3 prompts/day → **91.7 %**; 4-5/day → **77.4 %**; 6+/day → **75.0 %** (monotonic decline). **Clinical:** 2-3/day → 73.5 %; 4-5/day → 66.9 %; 6+/day → **89.3 %** (non-monotonic). 95 % of studies used 2-9 prompts/day; duration 2-42 days. Adding a wearable slightly reduced compliance (77.4 % → 73.0 %). |
| **Wrzus C & Neubauer AB.** *Assessment* 2023;30(3):825-46, PMID 35016567 `[verified]` | **477 articles, 496 samples, N = 677,536** | **79 %** | Studies averaged **6 assessments/day over 7 days**. "Studies with more assessments per day scheduled fewer assessment days, yet **the number of assessments did not predict compliance**." |
| **Liao Y et al.** *J Med Internet Res* 2016;18(6):e151, PMID 27328833 `[verified]` | Nutrition / physical activity in youth | Range **44-96 %, mean 71 %** | Prompt rates ranged **2 to 68 per day**; 46 % of studies failed to report compliance at all. |
| **Burke LE et al.** (EMPOWER) *J Med Internet Res* 2017;19(3):e77, PMID 28298264 `[verified]` | 151 participants, **12 months** | **88.3 %** completion of random assessments in first 6 months; ~90 % for time-contingent | **87.4 % retention at 12 months (132/151)**. The only long-horizon data point I found. |
| **May M, Junghaenel DU, Ono M, Stone AA, Schneider S.** *J Pain* 2018;19(7):699-716, PMID 29371113 `[verified]` | 105 chronic-pain EMA articles | — | "Completion rates were not reported in nearly one third of studies." |

### 8.3 Habituation is real even when compliance is not the metric

**Klasnja P, Smith SN, Seewald NJ, Lee JS, Hall K, Luers B, Hekler EB, Murphy SA. "Efficacy of Contextually Tailored Suggestions for Physical Activity: A Micro-randomized Optimization Trial of HeartSteps." *Ann Behav Med* 2019;53(6):573-82, doi:10.1093/abm/kay067, 270 citations `[verified]`.** n = 44 adults, 6 weeks, **up to five suggestions per day** at user-selected times, micro-randomised. Overall effect: **+14 % steps (p = 0.06)** on a 253-step baseline. **The effect decayed sharply: +66 % (167 extra steps, p < 0.01) at the start, falling to +24 % (59 steps, p = 0.02) by the end of six weeks.** Anti-sedentary suggestions had no detectable effect.

`[my arithmetic]` That is a **~64 % loss of effect over six weeks at five prompts per day.** The compliance meta-analyses measure *whether people answer*; HeartSteps measures *whether the prompt still does anything*. The second decays faster than the first, and it is the one that matters for a system whose value depends on the user actually engaging with the answer.

### 8.4 What this supplies as a cost parameter, and what it does not

**What we can say with evidence:**
- EMA protocols at **2-9 prompts/day for 2-42 days** sustain **~75-80 % compliance**. A system asking **≤1 question/day, realistically 1-3 per week**, sits one to two orders of magnitude below that load.
- Within the range studied, **prompt frequency is a surprisingly weak predictor of compliance** (Jones 2019, n.s.; Wrzus & Neubauer 2023, "did not predict"). Wen 2017's non-clinical stratification is the one clear monotonic frequency effect: **91.7 % at 2-3/day → 75.0 % at 6+/day.**
- 73 % of participants in a deployed wearable alerting study found the alert frequency acceptable at roughly **1.15 non-infection alert-days per 21 days** (Alavi 2022 `[verified]`).
- **Habituation is the binding constraint, not compliance** (HeartSteps: -64 % effect over 6 weeks).

**What we cannot say — a genuine, citable evidence gap:**
- Nearly every EMA meta-analysis covers protocols of **2-42 days**; Wrzus & Neubauer report an average study duration of **7 days**. Our system's horizon is months to years. **The only 12-month data point I found is Burke's EMPOWER study (88.3 % compliance, 87.4 % retention), a single heavily-supported clinical trial, not a naturalistic deployment.** Any claim about what a user will tolerate at month 9 is extrapolation.
- No study I found measures tolerance for **event-triggered, physiologically-justified** questions as opposed to **time-sampled** questions. The entire EMA literature samples on a schedule; our questions would arrive only when something looked odd. It is plausible that contingent questions are better tolerated (they are relevant) or worse (they are unpredictable and mildly alarming). **There is no evidence either way.**

**Defensible cost parameter:** a budget of **≤2 questions per week** is comfortably inside every published tolerance envelope; **≤1 per day** is inside the envelope but sits at the frequency where Wen's non-clinical stratification begins to show decline; **>3 per day** exceeds what the evidence supports for a multi-month deployment. The 6-month-plus horizon should be stated as unevidenced.

---

## 9. BIBLIOGRAPHY

All URLs checked 2026-08-30. Grade in brackets where applicable.

### Alcohol
1. **[A]** de Zambotti M, Forouzanfar M, Javitz H, Goldstone A, Claudatos S, Alschuler V, Baker FC, Colrain IM. Impact of evening alcohol consumption on nocturnal autonomic and cardiovascular function in adult men and women: a dose-response laboratory investigation. *Sleep*. 2021;44:zsaa135. doi:10.1093/sleep/zsaa135. PMID 32663278. https://doi.org/10.1093/sleep/zsaa135
2. **[B]** Grosicki GJ, et al. Real-world effects of alcohol on heart rate, sleep, and physical activity by age and sex. *PLOS Digital Health*. 2026;5(3):e0001284. doi:10.1371/journal.pdig.0001284. https://journals.plos.org/digitalhealth/article?id=10.1371/journal.pdig.0001284
3. **[B]** Strüven A, Schlichtiger J, Hoppe JM, Thiessen I, Brunner S, Stremmel C. The Impact of Alcohol on Sleep Physiology: A Prospective Observational Study on Nocturnal Resting Heart Rate Using Smartwatch Technology. *Nutrients*. 2025;17(9):1470. doi:10.3390/nu17091470. https://pmc.ncbi.nlm.nih.gov/articles/PMC12073130/
4. **[B]** Pietilä J, Helander E, Korhonen I, Myllymäki T, Kujala UM, Lindholm H. Acute Effect of Alcohol Intake on Cardiovascular Autonomic Regulation During the First Hours of Sleep in a Large Real-World Sample of Finnish Employees: Observational Study. *JMIR Mental Health*. 2018;5(1):e23. doi:10.2196/mental.9519. PMID 29549064. https://mental.jmir.org/2018/1/e23/
5. **[D]** Oura Health. "Oura Data Reveals the True Impact of Alcohol on Sleep." Company blog. https://ouraring.com/blog/how-does-alcohol-impact-oura-members/ — **company data blog, not peer reviewed.**

### Exercise
6. **[B]** Leota J, Presby DM, Le F, Czeisler MÉ, Mascaro L, Capodilupo ER, Wiley JF, Drummond SPA, Rajaratnam SMW, Facer-Childs ER. Dose-response relationship between evening exercise and sleep. *Nature Communications*. 2025;16(1):3297. doi:10.1038/s41467-025-58271-x. PMID 40234380. PMCID PMC12000559. https://pmc.ncbi.nlm.nih.gov/articles/PMC12000559/
7. **[A]** Myllymäki T, Rusko H, Syväoja H, Juuti T, Kinnunen ML, Kyröläinen H. Effects of exercise intensity and duration on nocturnal heart rate variability and sleep quality. *Eur J Appl Physiol*. 2012;112(3):801-9. doi:10.1007/s00421-011-2034-9. PMID 21667290.

### Sleep
8. **[B]** Zhang, Niu, et al. Effects of sleep deprivation on heart rate variability: a systematic review and meta-analysis. *Frontiers in Neurology*. 2025;16:1556784. doi:10.3389/fneur.2025.1556784. PMCID PMC12394884. https://pmc.ncbi.nlm.nih.gov/articles/PMC12394884/
9. **[B]** Castro-Diehl C, et al. Sleep Duration and Quality in Relation to Autonomic Nervous System Measures. *Sleep*. 2016;39(11):1927-40. doi:10.5665/sleep.6218
10. **[B]** Liu Y, Wheaton AG, Chapman DP, Cunningham TJ, Lu H, Croft JB. Prevalence of Healthy Sleep Duration among Adults — United States, 2014. *MMWR*. 2016;65(6):137-41. doi:10.15585/mmwr.mm6506a1. PMID 26890214.

### Stress
11. **[B]** Bloomfield LSP, Fudolig MI, Kim J, et al. Predicting stress in first-year college students using sleep data from wearable devices. *PLOS Digital Health*. 2024;3(4):e0000473. doi:10.1371/journal.pdig.0000473. PMCID PMC11008774. https://pmc.ncbi.nlm.nih.gov/articles/PMC11008774/

### Menstrual cycle
12. **[B]** Goodale BM, Shilaih M, Falco L, et al. Wearable Sensors Reveal Menses-Driven Changes in Physiology and Enable Prediction of the Fertile Window: Observational Study. *J Med Internet Res*. 2019;21(4):e13404. doi:10.2196/13404. PMCID PMC6495289. https://pmc.ncbi.nlm.nih.gov/articles/PMC6495289/
13. **[C]** Maijala A, Kinnunen H, Koskimäki H, Jämsä T, Kangas M. Nocturnal finger skin temperature in menstrual cycle tracking: ambulatory pilot study using a wearable Oura ring. *BMC Womens Health*. 2019;19:150. doi:10.1186/s12905-019-0844-9. PMCID PMC6883568. https://pmc.ncbi.nlm.nih.gov/articles/PMC6883568/
14. **[B]** Alzueta E, et al. Menstrual Cycle Variations in Wearable-detected Finger Temperature and Heart Rate, but not in Sleep Metrics, in Young and Midlife Individuals. *J Biol Rhythms*. 2024;39(5):395-412. doi:10.1177/07487304241265018. PMID 39108015. PMCID PMC11416332.

### Vaccination
15. **[B]** Quer G, Gadaleta M, Radin JM, et al. Inter-individual variation in objective measure of reactogenicity following COVID-19 vaccination via smartwatches and fitness bands. *npj Digital Medicine*. 2022;5:49. doi:10.1038/s41746-022-00591-z. PMCID PMC9019018. https://pmc.ncbi.nlm.nih.gov/articles/PMC9019018/
16. **[B]** Gepner Y, Yechezkel M, et al. Utilizing wearable sensors for continuous and highly-sensitive monitoring of reactions to the BNT162b2 mRNA COVID-19 vaccine. *Communications Medicine*. 2022;2:27. PMID 35603274. PMCID PMC9053261. https://pmc.ncbi.nlm.nih.gov/articles/PMC9053261/
17. **[B]** Mason AE, Kasl P, Hartogensis W, et al. Metrics from Wearable Devices as Candidate Predictors of Antibody Response Following Vaccination against COVID-19: Data from the Second TemPredict Study. *Vaccines (Basel)*. 2022;10(2):264. doi:10.3390/vaccines10020264. PMCID PMC8877860.

### Travel and altitude
18. **[B]** Willoughby AR, Vallat R, Ong JL, Chee MWL. Insights about travel-related sleep disruption from 1.5 million nights of data. *Sleep*. 2025;48(7):zsaf077. doi:10.1093/sleep/zsaf077. https://academic.oup.com/sleep/article/48/7/zsaf077/8092480
19. **[C]** Lang, et al. Cardiovascular and autonomic modulation during nighttime rest under real-world conditions in miners exposed to chronic intermittent hypoxia. *Frontiers in Physiology*. 2026;17. doi:10.3389/fphys.2026.1747092
20. **[C]** Patterson, et al. Nocturnal Sleep Breathing Patterns in Healthy Adolescents Residing at Very High Altitudes in Bolivia. *J Sleep Res*. 2026;35(4). doi:10.1111/jsr.70326

### Thermoregulation
21. **[C]** Kräuchi K, Cajochen C, Wirz-Justice A. Waking up properly: is there a role of thermoregulation in sleep inertia? *J Sleep Res*. 2004;13(2):121-7. doi:10.1111/j.1365-2869.2004.00398.x
22. **[A]** Romeijn N, Verweij IM, et al. Cold hands, warm feet: sleep deprivation disrupts thermoregulation and its association with vigilance. *Sleep*. 2012;35(12):1673-83. doi:10.5665/sleep.2242

### Caffeine, meals
23. **[A]** Gardiner C, Weakley J, Burke LM, Roach GD, Sargent C, Maniar N, Townshend A, Halson SL. The effect of caffeine on subsequent sleep: A systematic review and meta-analysis. *Sleep Medicine Reviews*. 2023;69:101764. doi:10.1016/j.smrv.2023.101764. PMID 36870101.
24. **[C, preprint]** Shkolnik M, et al. Dietary variation and sleep physiology. medRxiv 2026. doi:10.64898/2026.02.17.26346471
25. **[A]** Chellappa SL, et al. Daytime eating during simulated night work. *Nature Communications*. 2025;16(1):3186. doi:10.1038/s41467-025-57846-y

### Medications
26. **[B]** Gullestad L, et al. (MERIT-HF). *J Am Coll Cardiol*. 2005;45(2):252-9. doi:10.1016/j.jacc.2004.10.032
27. **[B]** Kjekshus JK. Importance of heart rate in determining beta-blocker efficacy in acute and long-term acute myocardial infarction intervention trials. *Am J Cardiol*. 1986. doi:10.1016/0002-9149(86)90888-X

### Infection detection and trajectory
28. **[B]** Alavi A, Bogu GK, Wang M, et al. Real-time alerting system for COVID-19 and other stress events using wearable data. *Nature Medicine*. 2022;28(1):175-184. doi:10.1038/s41591-021-01593-2. PMID 34845389. PMCID PMC8799466. https://pmc.ncbi.nlm.nih.gov/articles/PMC8799466/
29. **[B]** Mishra T, Wang M, Metwally AA, et al. Pre-symptomatic detection of COVID-19 from smartwatch data. *Nature Biomedical Engineering*. 2020;4(12):1208-1220. doi:10.1038/s41551-020-00640-6. PMID 33208926.
30. **[B]** Radin JM, Quer G, Ramos E, Baca-Motes K, Gadaleta M, Topol EJ, Steinhubl SR. Assessment of Prolonged Physiological and Behavioral Changes Associated With COVID-19 Infection. *JAMA Network Open*. 2021;4(7):e2115959. doi:10.1001/jamanetworkopen.2021.15959. PMID 34232306. PMCID PMC8264646. https://pmc.ncbi.nlm.nih.gov/articles/PMC8264646/
31. **[B]** Snir S, Chen Y, Yechezkel M, Patalon T, Shmueli E, Brandeau ML, Yamin D. Changes in behavior and bioreviewers during the diagnostic decision period for COVID-19, influenza, and group A streptococcus: a two-year prospective cohort study in Israel. *Lancet Regional Health – Europe*. 2024;42:100934. doi:10.1016/j.lanepe.2024.100934. PMID 38800112.
32. **[A]** Grzesiak E, et al. Assessment of the Feasibility of Using Noninvasive Wearable Biometric Monitoring Sensors to Detect Influenza and the Common Cold Before Symptom Onset. *JAMA Network Open*. 2021;4(9):e2128534. doi:10.1001/jamanetworkopen.2021.28534. PMID 34586364. PMCID PMC8482058.
33. **[B]** Mason AE, et al. Detection of COVID-19 using multimodal data from a wearable device: results from the first TemPredict Study. *Scientific Reports*. 2022;12:3463. doi:10.1038/s41598-022-07314-0. PMID 35236896.

### Epidemiology / base rates
34. **[B]** Tokars JI, Olsen SJ, Reed C. Seasonal Incidence of Symptomatic Influenza in the United States. *Clinical Infectious Diseases*. 2018;66(10):1511-1518. doi:10.1093/cid/cix1060. PMID 29206909.
35. **[B]** Hayward AC, Fragaszy EB, Bermingham A, et al. Comparative community burden and severity of seasonal and pandemic influenza: results of the Flu Watch cohort study. *Lancet Respiratory Medicine*. 2014;2(6):445-54. doi:10.1016/S2213-2600(14)70034-7. PMID 24717637.
36. **[B]** Byington CL, Ampofo K, Stockmann C, et al. Community Surveillance of Respiratory Viruses Among Families in the Utah Better Identification of Germs-Longitudinal Viral Epidemiology (BIG-LoVE) Study. *Clinical Infectious Diseases*. 2015;61(8):1217-24. doi:10.1093/cid/civ486. PMID 26245665.
37. **[B]** Strain T, et al. National, regional, and global trends in insufficient physical activity among adults from 2000 to 2022. *Lancet Global Health*. 2024;12(8):e1232-e1243. doi:10.1016/S2214-109X(24)00150-5. PMID 38942042.

### Sensor validity
38. **[B]** Gorny AW, Liew SJ, Tan CS, Müller-Riemenschneider F. Fitbit Charge HR Wireless Heart Rate Monitor: Validation Study Conducted Under Free-Living Conditions. *JMIR mHealth and uHealth*. 2017;5(10):e157. doi:10.2196/mhealth.8233. PMID 29055881.
39. **[B]** Reithe H, et al. Cross-evaluation of wearable data for use in Parkinson's disease research. *Biomedical Engineering Online*. 2025;24:22. PMID 39985029.
40. **[B]** Dial, et al. Validation of nocturnal resting heart rate and heart rate variability in consumer wearables. *Physiological Reports*. 2025. doi:10.14814/phy2.70527. `[secondary]`
41. **[C]** Guerrero-Blázquez A, et al. Validity and Reliability of a Smart Band for Monitoring Cardiorespiratory Parameters in Children and Adolescents with Severe Cerebral Palsy. *Sensors*. 2026;26(3):828. PMID 41682344.

### Value of information, Bayesian experimental design, active learning
42. Howard RA. Information Value Theory. *IEEE Transactions on Systems Science and Cybernetics*. 1966;2(1):22-26. doi:10.1109/TSSC.1966.300074
43. Lindley DV. On a Measure of the Information Provided by an Experiment. *Annals of Mathematical Statistics*. 1956;27(4):986-1005. doi:10.1214/aoms/1177728069
44. Raiffa H, Schlaifer R. *Applied Statistical Decision Theory*. Harvard Business School, 1961.
45. Chaloner K, Verdinelli I. Bayesian Experimental Design: A Review. *Statistical Science*. 1995;10(3):273-304.
46. Rainforth T, Foster A, Ivanova DR, Bickford Smith F. Modern Bayesian Experimental Design. arXiv:2302.14545, 2023. https://arxiv.org/abs/2302.14545
47. Houlsby N, Huszár F, Ghahramani Z, Lengyel M. Bayesian Active Learning for Classification and Preference Learning. arXiv:1112.5745, 2011. https://arxiv.org/abs/1112.5745
48. Kirsch A, van Amersfoort J, Gal Y. BatchBALD: Efficient and Diverse Batch Acquisition for Deep Bayesian Active Learning. arXiv:1906.08158, NeurIPS 2019. doi:10.48550/arXiv.1906.08158
49. Settles B. Active Learning Literature Survey. University of Wisconsin-Madison TR1648, 2009. `[not re-verified this pass]`
50. Siebert U, Rochau U, Claxton K. When is enough evidence enough? Using systematic decision analysis and value-of-information analysis to determine the need for further evidence. *Z Evid Fortbild Qual Gesundhwes*. 2013;107(9-10):575-84. PMID 24315327.
51. Constantinou AC, Yet B, Fenton N, et al. Value of information analysis for interventional and counterfactual Bayesian networks in forensic medical sciences. *Artificial Intelligence in Medicine*. 2015;66:41-52. PMID 26395654.
52. McCullagh L, Walsh C, Barry M. Value-of-information analysis to reduce decision uncertainty associated with the choice of thromboprophylaxis after total hip replacement in the Irish healthcare setting. *PharmacoEconomics*. 2012;30(10):941-59. PMID 22667458.
53. Kim DD, Trikalinos TA, Wong JB. Leveraging Cumulative Network Meta-analysis and Value of Information Analysis to Understand the Evolving Value of Medical Research. *Medical Decision Making*. 2019;39(2):119-129. PMID 30678537.

### Sequential testing and POMDPs
54. Wald A. Sequential Tests of Statistical Hypotheses. *Annals of Mathematical Statistics*. 1945;16(2):117-186. doi:10.1214/aoms/1177731118
55. Kulldorff M, Davis RL, Kolczak MS, Lewis E, Lieu TA, Platt R. A Maximized Sequential Probability Ratio Test for Drug and Vaccine Safety Surveillance. *Sequential Analysis*. 2011;30(1):58-78. doi:10.1080/07474946.2011.539924
56. Hauskrecht M, Fraser H. Planning treatment of ischemic heart disease with partially observable Markov decision processes. *Artificial Intelligence in Medicine*. 2000;18(3):221-244. doi:10.1016/S0933-3657(99)00042-1
57. Kaelbling LP, Littman ML, Cassandra AR. Planning and acting in partially observable stochastic domains. *Artificial Intelligence*. 1998;101(1-2):99-134. `[not re-verified this pass]`
58. Papadimitriou CH, Tsitsiklis JN. The complexity of Markov decision processes. *Mathematics of Operations Research*. 1987;12(3):441-450. `[not re-verified this pass]`

### Cost-sensitive feature acquisition and active sensing
59. Janisch J, Pevný T, Lisý V. Classification with Costly Features Using Deep Reinforcement Learning. AAAI 2019;33(1):3959-3966. doi:10.1609/aaai.v33i01.33013959
60. Peng YS, Tang KF, Lin HT, Chang EY. REFUEL: Exploring Sparse Features in Deep Reinforcement Learning for Fast Disease Diagnosis. NeurIPS 2018.
61. Li Y, Oliva JB. Active Feature Acquisition with Generative Surrogate Models. ICML 2021; arXiv:2010.02433. https://arxiv.org/abs/2010.02433
62. Yoon J, Jordon J, van der Schaar M. ASAC: Active Sensing using Actor-Critic models. MLHC 2019; arXiv:1906.06796. https://arxiv.org/abs/1906.06796
63. Kachuee M, Karkkainen K, Goldstein O, Zamanzadeh D, Sarrafzadeh M. Opportunistic Learning: Budgeted Cost-Sensitive Learning from Data Streams. ICLR 2019. `[not re-verified this pass]`

### Medical test selection and diagnostic information theory
64. Pauker SG, Kassirer JP. The threshold approach to clinical decision making. *New England Journal of Medicine*. 1980;302(20):1109-1117. doi:10.1056/NEJM198005153022003. PMID 7366635.
65. Benish WA. Relative entropy as a measure of diagnostic information. *Medical Decision Making*. 1999;19(2):202-206. PMID 10231083.
66. Benish WA. Mutual information as an index of diagnostic test performance. *Methods of Information in Medicine*. 2003;42(3):260-264. PMID 12874659.
67. Benish WA. The use of information graphs to evaluate and compare diagnostic tests. *Methods of Information in Medicine*. 2002;41(2):114-118. PMID 12061117.
68. Benish WA. Intuitive and axiomatic arguments for quantifying diagnostic test performance in units of information. *Methods of Information in Medicine*. 2009;48(6):552-557. PMID 19562229.
69. Benish WA. The channel capacity of a diagnostic test as a function of test sensitivity and specificity. *Statistical Methods in Medical Research*. 2015;24(6):1044-1052. PMID 22368178.
70. Benish WA. A Review of the Application of Information Theory to Clinical Diagnostic Testing. *Entropy*. 2020;22(1):97. PMID 33285872.
71. Heckerman DE, Horvitz EJ, Nathwani BN. Toward normative expert systems: Part I. The Pathfinder project. *Methods of Information in Medicine*. 1992;31(2):90-105.
72. Heckerman DE, Nathwani BN. Toward normative expert systems: Part II. Probability-based representations for efficient knowledge acquisition and inference. *Methods of Information in Medicine*. 1992;31(2):106-116.

### Computerized adaptive testing
73. Wang C, et al. Adaptive item selection with joint stopping rules (FAMCAT). *Archives of Physical Medicine and Rehabilitation*. 2022;103(5S):S3-S14. doi:10.1016/j.apmr.2022.01.002
74. Paap MCS, et al. Multidimensional vs unidimensional CAT efficiency. *Applied Psychological Measurement*. 2018;42(5):327-342. doi:10.1177/0146621617733954
75. Belvederi Murri M, et al. FRIDA adaptive screening tool. *Journal of Clinical Medicine*. 2025;14(19):6992. doi:10.3390/jcm14196992
76. Loe BS, Stillwell D, Gibbons C. Computerized Adaptive Testing Provides Reliable and Efficient Depression Measurement Using the CES-D Scale. *Journal of Medical Internet Research*. 2017;19(9):e302. doi:10.2196/jmir.7453

### Interruptibility, notifications, EMA, JITAI
77. Hudson S, Fogarty J, Atkeson C, Avrahami D, Forlizzi J, Kiesler S, Lee J, Yang J. Predicting human interruptibility with sensors. *ACM Transactions on Computer-Human Interaction*. 2005;12(1):119-146. doi:10.1145/1057237.1057243
78. Horvitz E, Apacible J. Learning and reasoning about interruption. ICMI 2003:20-27. doi:10.1145/958432.958440
79. Horvitz E, Jacobs A, Hovel D. Attention-sensitive alerting. UAI 1999:305-313. `[not re-verified this pass]`
80. Horvitz E. Principles of mixed-initiative user interfaces. CHI 1999:159-166. `[not re-verified this pass]`
81. Pielot M, Church K, de Oliveira R. An in-situ study of mobile phone notifications. MobileHCI 2014:233-242. doi:10.1145/2628363.2628364
82. Shirazi AS, Henze N, Dingler T, Pielot M, Weber D, Schmidt A. Large-scale assessment of mobile notifications. CHI 2014:3055-3064. doi:10.1145/2556288.2557189
83. Jones A, Remmerswaal D, Verveer I, Robinson E, Franken IHA, Wen CKF, Field M. Compliance with ecological momentary assessment protocols in substance users: a meta-analysis. *Addiction*. 2019;114(4):609-619. doi:10.1111/add.14503. PMID 30461120.
84. Wen CKF, Schneider S, Stone AA, Spruijt-Metz D. Compliance With Mobile Ecological Momentary Assessment Protocols in Children and Adolescents: A Systematic Review and Meta-Analysis. *Journal of Medical Internet Research*. 2017;19(4):e132. doi:10.2196/jmir.6641. PMID 28446418.
85. Wrzus C, Neubauer AB. Ecological Momentary Assessment: A Meta-Analysis on Designs, Samples, and Compliance Across Research Fields. *Assessment*. 2023;30(3):825-846. PMID 35016567.
86. Liao Y, Skelton K, Dunton G, Bruening M. A Systematic Review of Methods and Procedures Used in Ecological Momentary Assessments of Diet and Physical Activity Research in Youth. *Journal of Medical Internet Research*. 2016;18(6):e151. PMID 27328833.
87. Burke LE, et al. Ecological Momentary Assessment in Behavioral Research: Addressing Technological and Human Participant Challenges (EMPOWER). *Journal of Medical Internet Research*. 2017;19(3):e77. PMID 28298264.
88. May M, Junghaenel DU, Ono M, Stone AA, Schneider S. Ecological Momentary Assessment Methodology in Chronic Pain Research: A Systematic Review. *The Journal of Pain*. 2018;19(7):699-716. PMID 29371113.
89. Klasnja P, Smith SN, Seewald NJ, Lee JS, Hall K, Luers B, Hekler EB, Murphy SA. Efficacy of Contextually Tailored Suggestions for Physical Activity: A Micro-randomized Optimization Trial of HeartSteps. *Annals of Behavioral Medicine*. 2019;53(6):573-582. doi:10.1093/abm/kay067
90. Nahum-Shani I, Smith SN, Spring BJ, Collins LM, Witkiewitz K, Tewari A, Murphy SA. Just-in-Time Adaptive Interventions (JITAIs) in Mobile Health: Key Components and Design Principles for Ongoing Health Behavior Support. *Annals of Behavioral Medicine*. 2018;52(6):446-462. PMID 27663578.
91. Li J, Ponnada A, Wang WL, Dunton GF, Intille SS. Ask Less, Learn More: Adapting Ecological Momentary Assessment Survey Length by Modeling Question-Answer Information Gain. *Proc ACM Interact Mob Wearable Ubiquitous Technol*. 2024;8(4):166. doi:10.1145/3699735. PMID 39664111. PMCID PMC11633767.
92. Li SS, Balachandran V, Feng S, Ilgen JS, Pierson E, Koh PW, Tsvetkov Y. MediQ: Question-Asking LLMs and a Benchmark for Reliable Interactive Clinical Reasoning. arXiv:2406.00922, 2024. https://arxiv.org/abs/2406.00922

---

## 10. Explicit list of things I could NOT source

Do not fill these with folklore. If the project needs them, they need a dedicated search or an explicit assumption.

1. **Alcohol's effect on nocturnal respiratory rate, skin temperature deviation, or SpO2** — no peer-reviewed wearable quantification found. Only Oura's blog, which gives no numbers for these channels.
2. **"Adults get 2-3 colds per year"** — no primary source retrieved. Grade F until one is attached.
3. **Stress → distal skin temperature** in a wearable — the theoretical discriminator between stress and infection is unvalidated.
4. **Ambient bedroom temperature → apparent skin temperature deviation**, in degrees, for any consumer device.
5. **Delayed (day-2 / DOMS) effect of hard exercise on overnight HRV** in a wearable population.
6. **Moderate altitude (1,500-3,000 m)** effects on nocturnal SpO2/HR in consumer devices.
7. **Nicotine** acute effect sizes on nocturnal HR/HRV — no clean meta-analysis retrieved.
8. **Stimulant / antihistamine / SSRI** effect sizes on resting HR — not verified in this pass.
9. **Consumer SpO2 behaviour in mild uncomplicated URI in adults** — the outpatient pulse-oximetry literature is all about pneumonia and bronchiolitis.
10. **Vaccination events per adult per year** and **time-zone-crossing trips per person per year** — no verified population statistics.
11. **Question/notification tolerance beyond ~6 weeks** in a naturalistic (non-trial) setting — the single 12-month data point (EMPOWER) is a supported clinical trial.
12. **Tolerance for event-triggered vs schedule-triggered questions** — no study found either way.
13. **Pathfinder's use of myopic VoI** — citation verified, mechanism not verified from primary text.
14. Two magnitude figures in §5.2 (skin temp **+0.63 °C**; RHR peak **+1.8 % F / +3.4 % M**) are `[secondary]` — retrieved via search summary, not attached to a specific verified paper. Re-verify before use.

---

## 11. Method note

WebSearch budget for this session was exhausted after 200 queries partway through Part 1. The remainder of the research was conducted through the **Europe PMC REST search API**, the **OpenAlex works API**, and direct fetches of PMC / arXiv / publisher pages. Both APIs return title, authors, venue, DOI and (for Europe PMC) abstract text, so the sourcing quality was not degraded — but coverage of grey literature and company blogs after that point is thinner than it would otherwise have been. PubMed's own pages return a cookie wall to automated fetching; PMC and Europe PMC do not.
