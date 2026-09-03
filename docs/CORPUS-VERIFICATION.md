# Verifying the corpus against the papers it cites

**Written 4 September 2026, while building `data/knowledge/corpus.yaml`.**

The corpus the agent retrieves from is generated from three files a human authored:
`data/knowledge/causes.yaml`, `data/knowledge/red_flags.yaml` and `src/wha/constants.py`.
No medical content is written by the agent. That constraint stops fabrication, but it does
not by itself make the corpus correct: a wrong number in `causes.yaml` would become a
retrievable, citable passage and the citation would make it look more trustworthy, not
less.

So every figure that reaches a corpus passage was checked against the published source.
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
| alcohol `effect_mean_bpm = 2.60` | Grosicki et al. 2026, PLOS Digit Health 5(3):e0001284 | One drink above personal average against one below: RHR +2.8 bpm in females, +2.4 bpm in males. n=20,968, 5,109,185 person-days, within-person. The 2.60 in `causes.yaml` is the midpoint. |
| vaccination `effect_mean_bpm = 1.52` | Quer et al. 2022, npj Digit Med 5:49 | "+1.52 beats per minute with respect to baseline following the second dose", +0.56 after the first, peak on day 2, back to baseline on day 6 after dose two. Every element of the profile checks out. |
| infection `effect_mean_bpm = 1.60`, DERIVED | Mishra et al. 2020, Nat Biomed Eng 4:1208-20 | "average peak increases relative to baseline of 1.8% for females and 3.4% for males". On the 62.75 bpm population mean that is +1.13 and +2.13 bpm, so the repo's "1.1 to 2.1 bpm, midpoint 1.6" is arithmetically correct. |
| recovery_tail, every figure | Radin et al. 2021, JAMA Netw Open 4(7):e2115959 | 234 positive against 641 symptomatic negative. RHR "did not return to baseline, on average, until 79 days after symptom onset". "32 participants [13.7%]" stayed more than 5 bpm above baseline for more than 133 days. Sleep at 24 days, steps at 32. |
| sleep_restriction base rate 0.348 | Liu et al. 2016, MMWR 65(6):137-41 | 65.2 percent of 444,306 respondents reported a healthy duration of seven hours or more, so 34.8 percent did not. |
| The 0.10 testing threshold | Pauker and Kassirer 1980, NEJM 302(20):1109-17 | The threshold approach, and the derivation of a testing threshold from the utilities of the competing errors, is the paper's subject. The repo derives P* from its own utilities and notes the coincidence rather than borrowing the number. |
| Exercise study identity and direction | Leota et al. 2025, Nat Commun 16:3297 | n=14,689 and 4,084,354 person-nights both confirmed exactly. Later timing and higher strain are associated with higher nocturnal resting heart rate. |

## Not confirmed, and what that means

**1. `EXERCISE_EFFECT_BPM` per-band figures could not be read from an open copy.**
`{"0-2h": 4.14, "2-4h": 2.91, "4-6h": 1.58}` sits behind the publisher's paywall in every
route tried. The study, its cohort size, and the direction and shape of the effect are all
confirmed. The three bpm values are not independently confirmed here.

There is also a tension worth a human's eye. The paper's own summary states that "exercise
bouts ending >=4 hours before sleep onset are not associated with changes in sleep",
while `EXERCISE_EFFECT_BPM` assigns 1.58 bpm to the 4 to 6 hour band. Those may be
reconcilable, since the quoted sentence is about sleep measures and the table entry is
about nocturnal heart rate, and the paper reports both. They may not be. Recorded in
`plan/BLOCKERS.md`; nothing was changed on a guess.

**2. Two of the three Goodale figures in the `luteal` citation string are wrong.**
The load-bearing one, +3.91 bpm, is exactly right. Alongside it the citation says
"wrist skin temperature +0.44 C, respiratory rate +0.60/min". Read off the paper's phase
means, late luteal against follicular, those are +0.45 C and +0.47 breaths per minute.

Neither channel is ingested by this system and neither number enters any computation, so
this is a citation-accuracy defect rather than a clinical one. `causes.yaml` is read-only
to the agent, so it was not edited. Recorded in `plan/BLOCKERS.md` for a human.

**3. Mishica et al. 2022 is eleven adolescent endurance athletes.**
The quotation the code relies on is verbatim and correct. The cohort is n=11, aged 16 +/- 1,
cross-country skiers and biathletes. That is a narrow basis for a general claim about
sleep being the quieter measurement window, and the paper's own result partly cuts against
its framing: "Contrary to the hypothesis, the current study showed significantly higher
variation and higher RMSSD values during morning tests" — the variability result runs in
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

- **Layer 1, MedlinePlus consumer health text: absent.** It is a 29 MB external download
  that has not been fetched. Writing consumer-language health passages without it would be
  inventing medical content, which is the one thing this build must not do.
- **Layer 2, clinical reference register: present but narrow.** It is the measurement and
  detection method, drawn from `constants.py` and the papers above. It is not StatPearls.
- **Layer 3, escalation and care pathways: present.** Generated from `red_flags.yaml`,
  which is the human-authored safety floor, including its Singapore care-pathway wording.
- **Layer 4, confounder evidence: present.** Generated from `causes.yaml`.

The consequence, stated plainly: the agent can cite the reason a night was flagged, the
evidence behind each competing explanation, and the rule behind any escalation. It cannot
cite consumer health information about a condition, because this repository holds none.
Disclosed in `docs/DISCLOSURES.md` and on the dashboard.
