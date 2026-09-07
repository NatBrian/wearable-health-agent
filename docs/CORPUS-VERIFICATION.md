# Verifying the corpus against the papers it cites

**Written 4 September 2026, while building `data/knowledge/corpus.yaml`.**

The corpus the agent retrieves from is generated from three files in this repository:
`data/knowledge/causes.yaml`, `data/knowledge/red_flags.yaml` and `src/wha/constants.py`.
No medical content is written by the agent. That constraint stops fabrication, but it does
not by itself make the corpus correct: a wrong number in `causes.yaml` would become a
retrievable, citable passage and the citation would make it look more trustworthy, not
less.

So every figure that reaches a corpus passage was checked against the published source.

> **AMENDED 5 September 2026, and the amendment is the interesting part.** This check asked
> "does the paper support this row" and answered yes for rows where the paper supports SOME
> of it. A later audit asked the narrower question, "is this exact number in that paper", and
> three rows failed: `alcohol`, `luteal` and `recovery_tail`. None of their numbers moved,
> because the derivations behind them are sound; what moved is the label. **`causes.yaml` now
> has no `CITED` rows at all**, and each carries a `derivation` naming which of its figures
> comes from the paper, which is worked out from it, and which is `NO EVIDENCE FOUND`. The
> rows below are marked accordingly. A verification that checks the source and not the label
> lets a strong citation carry a weak number, which is precisely how a wrong figure comes to
> look more trustworthy rather than less.
What follows is what was checked, how, and what did not hold up. Each row was verified by
fetching the paper or its PubMed Central copy in September 2026 and reading the sentence
that carries the number.

---

## Confirmed, verbatim

| Figure, and where it lives | Source | What the paper says |
|---|---|---|
| `DETECT_YELLOW_BPM = 3.0`, `DETECT_RED_BPM = 4.0` | Alavi et al. 2022, Nat Med 28:175-184 | Three bpm chosen because "the median of fluctuation of medians of average RHR overnight over three months was only three bpm". A red alert triggers when overnight RHR is at least four bpm above baseline on two consecutive nights. |
| Baseline is the person's own median, not a blend | Alavi et al. 2022 | "For each individual, we use the streaming median of average overnight RHR as the baseline". No population blending appears anywhere in the method. |
| `BASELINE_MIN_NIGHTS_PERSONAL = 7` | Alavi et al. 2022 | "for over 80% of the participants, the proper baseline was observed after only seven nights" |
| 80 percent detection sensitivity | Alavi et al. 2022 | 67 of 84 infected participants alerted, in a cohort of 3,318. Pre-symptomatic signals at a median of 3 days before symptom onset. |
| `POP_PRIOR_RHR_MEAN_BPM = 62.75`, `POP_PRIOR_RHR_SD_BPM = 8.64` | Bloomfield et al. 2024, PLOS Digit Health 3(4):e0000473 | "Participants had an average RHR of 62.75 bpm (SD = 8.64 bpm)." n=525. |
| stress `effect_mean_bpm` derivation, OR 1.036 per bpm | Bloomfield et al. 2024 | "For every 1 bpm increase in RHR (model 2c), the odds of reporting symptoms of moderate-to-high stress increased by 1.036 (p<0.05)." |
| Naps excluded from the night window | Whitehurst, Naji, Mednick 2018, Neurobiol Sleep Circadian Rhythms 5:52-57 | "longer RR intervals and decreased heart rate during the night for both Stage 2 and SWS" compared with the nap. n=32, within-subjects, polysomnography with ECG. Direction is as the code states. |
| Sleep rather than daytime as the measurement window | Mishica et al. 2022, PLoS One 17(1):e0262333 | "During sleep, individuals are no longer affected by external stimuli and therefore, enhanced reliability may exist for recordings that occur during sleep." |
| luteal `effect_mean_bpm = 3.91` | Goodale et al. 2019, JMIR 21(4):e13404 | Late luteal mean 60.47 bpm (SD 6.45) against follicular mean 56.56 bpm (SD 6.29). The difference is 3.91 bpm exactly. n=193 participants, 708 cycles, both confirmed. |
| alcohol `effect_mean_bpm = 2.60`, **derived not cited** | Grosicki et al. 2026, PLOS Digit Health 5(3):e0001284 | One drink above personal average against one below: RHR +2.8 bpm in females, +2.4 bpm in males. n=20,968, 5,109,185 person-days, within-person. The 2.60 in `causes.yaml` is the midpoint of a TWO-DRINK SPAN and is not a per-drink effect the paper reports. The row was labelled CITED until 5 September 2026 and is now DERIVED; the base rate of 0.299 IS the paper's, and `effect_sd_bpm` 1.10 is in no paper. |
| vaccination `effect_mean_bpm = 1.52` | Quer et al. 2022, npj Digit Med 5:49 | "+1.52 beats per minute with respect to baseline following the second dose", +0.56 after the first, peak on day 2, back to baseline on day 6 after dose two. Every element of the profile checks out. |
| infection `effect_mean_bpm = 1.60`, DERIVED | **Corrected 5 September 2026.** Natarajan, Su and Heneghan 2022, Front Physiol 13:898251, n=7,200 | "elevated during symptom onset, with average peak increases relative to the baseline of 1.8% (3.4%) for females (males)". **This was credited to Mishra et al. 2020, which does not contain those figures.** The arithmetic on the 62.75 bpm population mean gives +1.13 and +2.13 bpm, but it multiplies a percentage from 7,200 Fitbit users by an average from 525 students, which is two different groups of people. The stored 1.60 is now backed by a direct measurement instead: +2.18 bpm against matched controls, standard error about 0.85, on the Mishra cohort. See `docs/KNOWLEDGE-CHANGELOG.md` and `experiments/detection/cohort/infection.py`. |
| recovery_tail, **the 79 day window ONLY** | Radin et al. 2021, JAMA Netw Open 4(7):e2115959 | 234 positive against 641 symptomatic negative. RHR "did not return to baseline, on average, until 79 days after symptom onset". "32 participants [13.7%]" stayed more than 5 bpm above baseline for more than 133 days. Sleep at 24 days, steps at 32. **This row said "every figure" and it verifies one.** An audit on 5 September 2026 found the paper supports the recovery WINDOW and none of the row's three numbers: `base_rate` 0.020, `effect_mean_bpm` 1.50 and `effect_sd_bpm` 1.50 are NO EVIDENCE FOUND. The row is now DERIVED and says so. |
| sleep_restriction base rate 0.348 | Liu et al. 2016, MMWR 65(6):137-41 | 65.2 percent of 444,306 respondents reported a healthy duration of seven hours or more, so 34.8 percent did not. |
| The 0.10 testing threshold | Pauker and Kassirer 1980, NEJM 302(20):1109-17 | The threshold approach, and the derivation of a testing threshold from the utilities of the competing errors, is the paper's subject. The repo derives P* from its own utilities and notes the coincidence rather than borrowing the number. |
| Exercise study identity and direction | Leota et al. 2025, Nat Commun 16:3297 | n=14,689 and 4,084,354 person-nights both confirmed exactly. Later timing and higher strain are associated with higher nocturnal resting heart rate. |

## Not confirmed, and what that means

**1. RESOLVED 4 September 2026. `EXERCISE_EFFECT_BPM` was two-thirds traceable and
one-third invented.**

The publisher blocks automated fetching, so the paper was obtained by hand and is kept at
`research/papers/leota-2025-nat-commun-16-3297.pdf` (Nature Communications is open access,
CC BY). Its table reports **incremental** contrasts between adjacent strain levels at each
ending time relative to habitual sleep onset, in beats per minute:

| contrast | -10h | -8h | -6h | -4h | -2h | 0 | +2h |
|---|---|---|---|---|---|---|---|
| Light - None | 0.49 | 0.47 | 0.40 | 0.33 | 0.45 | 2.02 | 6.50 |
| Mod. - Light | 0.37 | 0.48 | 0.54 | 0.74 | 1.32 | 2.39 | 3.69 |
| High - Mod. | 0.18 | 0.46 | 0.64 | 0.80 | 1.14 | 1.18 | 1.49 |
| Maximal - High | 0.88 | 1.09 | 1.24 | 1.34 | 1.43 | 1.80 | 4.25 |

High strain against no exercise is the sum of the first three rows:

| ending time | -10h | -8h | -6h | -4h | -2h | 0 | +2h |
|---|---|---|---|---|---|---|---|
| bpm above no exercise | 1.04 | 1.41 | **1.58** | **1.87** | **2.91** | 5.59 | 11.68 |

Against the stored `{"0-2h": 4.14, "2-4h": 2.91, "4-6h": 1.58}`:

- **2.91 is exactly the high-strain figure at -2h.** Traceable.
- **1.58 is exactly the high-strain figure at -6h.** Traceable.
- **4.14 appears nowhere.** It sits between the -2h value (2.91) and the 0h value (5.59),
  and is not the maximal-strain figure at -2h either (4.34). It was presumably
  interpolated, and nothing recorded that it had been.

Two exact matches to two decimal places establish the derivation method beyond reasonable
doubt. But the two traceable values were assigned to bands one step apart from each other:
2.91, the -2h figure, was labelled the 2-4h band, while 1.58, the -6h figure, was labelled
4-6h. There was no single convention.

**Corrected to `{"0-2h": 2.91, "2-4h": 1.87, "4-6h": 1.58}`**, under one rule: each band
takes the paper's value at the edge of the band furthest from sleep onset. That is the
smallest figure the paper supports for each band, and the direction matters. This quantity
is subtracted from the observed elevation, so overstating it hides real illness while
understating it only causes another look, and this system's own utilities weigh a missed
illness nine times a false alarm.

The apparent tension with the paper's summary line, "bouts ending >=4 hours before sleep
onset are not associated with changes in sleep", is resolved by the table: that sentence
concerns sleep measures, and the nocturnal heart rate column does show 1.58 bpm at -6h.
Both are the paper's own findings.

**2. Two of the three Goodale figures in the `luteal` citation string are wrong.**
The load-bearing one, +3.91 bpm, is exactly right. Alongside it the citation says
"wrist skin temperature +0.44 C, respiratory rate +0.60/min". Read off the paper's phase
means, late luteal against follicular, those are +0.45 C and +0.47 breaths per minute.

Neither channel is ingested by this system and neither number enters any computation, so
this is a citation-accuracy defect rather than a clinical one. `causes.yaml` is read-only
to the agent, so it was not edited. Recorded in `docs/DISCLOSURES.md` for a human.

**3. Mishica et al. 2022 is eleven adolescent endurance athletes.**
The quotation the code relies on is verbatim and correct. The cohort is n=11, aged 16 +/- 1,
cross-country skiers and biathletes. That is a narrow basis for a general claim about
sleep being the quieter measurement window, and the paper's own result partly cuts against
its framing: "Contrary to the hypothesis, the current study showed significantly higher
variation and higher RMSSD values during morning tests". The variability result runs in
the direction the code cites, but the authors report it as contrary to what they expected.
The corpus passage states the cohort so a reader can weigh it.

**4. Dial et al. 2025 does not validate this watch.**
The paper is real and is what `SLEEP_WINDOW_CITATION` says it is: validation of nocturnal
resting heart rate and heart rate variability in consumer wearables against ECG, 13 adults,
536 nights. The five devices are Garmin Fenix 6, Oura Gen 3, Oura Gen 4, Polar Grit X Pro
and Whoop 4.0. **The Galaxy Watch 5 this system actually reads is not among them**, and
across the devices tested the agreement ranged from good to poor. The corpus passage says
so rather than implying the device in use has been validated.

## What is absent

`sources.yaml` describes four corpus layers. Only three can be built from material already
in this repository:

- **Layer 1, MedlinePlus consumer health text: FETCHED 4 September 2026.** 1,013 English
  topics out of the 2,033 in the release; the remainder are Spanish, or summaries short
  enough to be a pointer rather than information. The snapshot date, URL and SHA-256 are
  recorded in `data/knowledge/corpus-sources.json`, and the raw release is kept out of
  version control. The URL `sources.yaml` named was a 404 and appears never to have
  existed, which is written up in `docs/KNOWLEDGE-CHANGELOG.md`.

  Measured before and after: the index went from 133 chunks to 1,852, a fourteenfold
  increase. The authored escalation rules still appear in the top six results for "chest
  pain", "I fainted" and "my chest hurts and I feel sick", and a test asserts it, because
  a thousand fetched topics burying this system's own safety rules is a real risk that
  would otherwise only be caught by someone reading citations closely. The deterministic
  safety floor does not consult retrieval at all, so what changed is what the person
  reads and what the model reasons over, not whether an escalation fires.
- **Layer 2, clinical reference register: present but narrow.** It is the measurement and
  detection method, drawn from `constants.py` and the papers above. It is not StatPearls.
- **Layer 3, escalation and care pathways: present.** Generated from `red_flags.yaml`,
  which is the safety floor, including its Singapore care-pathway wording.
- **Layer 4, confounder evidence: present.** Generated from `causes.yaml`.

The consequence, stated plainly: the agent can cite the reason a night was flagged, the
evidence behind each competing explanation, the rule behind any escalation, and general
consumer health background on a condition from MedlinePlus. It still cannot search the
web and cannot write clinical text of its own. MedlinePlus material is about a condition
in general and never about this person, which is said in every passage it produces, in
`docs/DISCLOSURES.md`, and on the dashboard.
