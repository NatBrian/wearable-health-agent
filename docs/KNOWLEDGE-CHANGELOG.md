# Changes to the clinical knowledge files

`data/knowledge/` and the clinical constants in `src/wha/constants.py` are under change
control. The rule exists because a wrong number in them becomes a retrievable, citable
passage, and the citation makes it look more trustworthy rather than less.

A figure may change when, and only when, one of two things holds:

1. **The published source it cites can be quoted contradicting it.**
2. **A measurement made in this repository, on real data, with the script committed**,
   contradicts it.

No new clinical content may be added, no figure may be changed on judgement, and every edit
is recorded here with the old value, the new value, what it changed downstream, and either
the quoted source sentence or the command that reproduces the measurement.

If an entry below cannot be checked against its paper, or re-run from the command given, it
should not have been made.

---

## 2026-09-05 — `causes.yaml`, the infection row

The most consequential row in the file. Four changes, one deliberate non-change.

**`effect_mean_bpm: 1.60` is UNCHANGED, and that is the finding.** An earlier draft of
this project's review said it was badly wrong and called replacing it the highest priority
in the document. It is not wrong.

Measured on 30 labelled COVID-19 cases and 138 matched healthy windows from the Mishra
et al. 2020 cohort, using this system's own `compute_baseline`:

| Mean nightly elevation above own baseline, 7 nights | Median | SD |
|---|---|---|
| Healthy people, matched windows (n=138) | -0.25 bpm | 3.32 |
| COVID-19, the 7 nights before symptoms (n=22) | +1.93 bpm | 3.75 |
| **Difference** | **+2.18 bpm** | standard error about 0.85 |

1.60 sits inside that interval. It is kept rather than moved to a point estimate the data
cannot separate from it. Reproduce with `uv run python tools/cohort/infection.py`.

**`effect_sd_bpm`: 1.00 to 1.75.** 1.00 had no source at all. The between-person spread of
the mean pre-symptomatic elevation is SD 3.75 bpm in cases against 3.32 in controls; the
excess, under an independence assumption, is 1.75. Imprecise at n=22, and said so in the
file rather than dressed up. Raising it lets infection explain a wider range of residuals,
which is the direction this system's utilities prefer, weighing a miss nine times a false
alarm.

**`base_rate`: 0.025 to 0.038.** 0.025 had no source and means about nine days of
infection a year. **Source:** CDC, *About Common Cold*, updated 19 February 2026: *"Every
year in the United States, adults have an average of two to three colds"* and *"Colds
usually last less than a week"*. The low end is 2 x 7 = 14 days, which is 0.038 of days.
Taken at the low end deliberately. It remains a floor: it counts colds only, and every
other infection is additional.

**The citation was pointing at the wrong paper.** "1.8 percent for females and 3.4 percent
for males" was credited to Mishra et al. 2020. Those figures are not in that paper. They
are Natarajan A, Su H-W, Heneghan C. Occurrence of Relative Bradycardia and Relative
Tachycardia in Individuals Diagnosed With COVID-19. *Front Physiol.* 2022;13:898251,
n=7,200, which reads: *"elevated during symptom onset, with average peak increases
relative to the baseline of 1.8% (3.4%) for females (males)"*. Fetched and quoted, not
taken from a search summary. Nothing in this repository cited it before.

**The `profile` is unchanged, on purpose.** The same measurement gives the day-by-day
median elevation relative to onset, and it does support the shape being rising then
falling with a peak just after onset. It does not support refitting the nine weights:
at about 22 people per day the medians swing between 0.0 and +3.0 bpm on adjacent days,
and fitting a nine-point curve to that is fitting noise. The regime a raised profile would
capture is the symptomatic one, where the person already knows they are ill and this
system adds least.

---

## 2026-09-05 — `constants.py`, the band's width no longer borrows a between-person spread

**Changed:** the quantity `compute_baseline` shrinks `scale_bpm` toward, from
`POP_PRIOR_RHR_SD_BPM = 8.64` to a new `WITHIN_PERSON_SCALE_PRIOR_BPM = 3.71`.
`POP_PRIOR_RHR_SD_BPM` is unchanged and still correct for what it describes.

**Why this is a correction and not a preference.** 8.64 bpm is Bloomfield et al. 2024's
reported spread across 525 different adults: *"Participants had an average RHR of 62.75
bpm (SD = 8.64 bpm)."* That is a **between-person** quantity. `scale_bpm` sets the width
of the band around one person's own median, and `robust_z` is the residual divided by it,
so it is a **within-person** quantity: how far one person's nights sit from their own
usual. They are different things, and the paper is not being contradicted, it is being
read as answering a question it was never asked. This is the same category error already
corrected on the **centre** on 3 September, in the other direction.

**Source: a measurement, with the script committed.** The median scaled MAD of 107
participants' own overnight readings across 8,508 nights of the Mishra et al. 2020 cohort
is **3.71 bpm** (IQR 2.97 to 4.45). Reproduce with:

```bash
uv run python tools/cohort/band_width.py
```

**Downstream effect, measured on the same 8,508 nights.**

| | Mature band width | Nights at abs(robust z) > 6 | One extreme alert every |
|---|---|---|---|
| Before, toward 8.64 | 4.10 bpm | 9 of 7,079 | 112 person-weeks |
| After, toward 3.71 | 3.11 bpm | 33 of 7,079 | 31 person-weeks |
| A fully personal scale, for comparison | 2.97 bpm | 39 of 7,079 | 26 person-weeks |

Nothing else moves. Detection levels are decided on `residual_bpm` in beats, not on
`robust_z`, so sensitivity and alert burden are unchanged. What changes is `robust_z`,
which is the unit the two extreme heart rate rules in `red_flags.yaml` are written in.
Their stated rationale, *"six robust standard deviations is well beyond any confounder in
the table"*, is only true when the standard deviation is the person's own.

**A fully personal scale was considered and rejected.** The refinement plan proposed it.
Measured, it is barely different from a corrected prior (2.97 against 3.11) and it is
badly quantised: heart rates are whole numbers, so a personal MAD lands on multiples of
1.4826 and the band jumps in steps rather than moving smoothly. Shrinkage is what smooths
that, and a MAD over seven nights is noisy enough to need it.

**Limitations, stated rather than buried.** Those 107 people wore Fitbits and were
measured over the midnight-to-07:00 clock window, not this build's recorded-sleep window,
and a research cohort is healthier than a general population. It is a starting guess that
stops mattering once the person's own nights arrive, which is what a prior is for.

**`docs/CONTRACTS.md` line 149 now disagrees with the code** and says the scale shrinks
from `POP_PRIOR_RHR_SD_BPM`. The contract is not edited here. Recorded in `BLOCKERS.md`.

---

## 2026-09-05 — `causes.yaml`, `exertion.effect_mean_bpm`

**Changed:** `4.14` to `2.91`.

**Source:** Leota J, et al. Dose-response relationship between evening exercise and sleep.
*Nat Commun.* 2025;16:3297. Paper at `research/papers/leota-2025-nat-commun-16-3297.pdf`.

**Working:** the paper's table gives incremental contrasts between adjacent strain levels.
High strain against no exercise is their sum: 1.58 bpm at -6h, 1.87 at -4h, 2.91 at -2h,
5.59 at sleep onset. **4.14 appears nowhere in that table.** A session ending 0 to 2 hours
before sleep takes the value at the edge of the band furthest from sleep onset, 2.91,
which is the smallest figure the paper supports for the band and the same rule already
applied to `EXERCISE_EFFECT_BPM`.

**Why it was still here.** The twin of this figure in `constants.py` was corrected on
4 September 2026 under the entry below. This one was missed, so the two files disagreed
about the same quantity for a day, and the corpus passage generated from `causes.yaml`
carried the unsourced number.

**Downstream effect:** exertion competes with infection to explain a raised night, and it
is the second largest effect in the table. Lowering it makes exertion explain slightly
less and leaves slightly more residual for everything else, which is the direction this
system's own utilities prefer.

---

## 2026-09-05 — every file, the authorship header

**Changed:** every `Authored by a human` and equivalent claim removed. `READ ONLY` kept.
Also removed: fourteen "Swept." annotations across `causes.yaml` and `probes.yaml`, the
header line requiring that every `ASSUMED` figure "MUST appear in the sweep", and the
sentence in `probes.yaml` claiming "All are swept in the sensitivity analysis".

**Source: this repository, checked directly.** These files were generated by a language
model, not written by a person. The `Swept` claims are separately false: the only sweep in
the codebase is `COST_WEIGHT_SWEEP` in `src/wha/eval/policy_oracle.py`, which ranges over
`POLICY_COST_PER_INTERRUPT` and nothing else. No effect size and no likelihood row in
either file has ever been varied by any code here. The claim is the same shape as the one
`STATUS.md` already records against `POLICY_COST_PER_INTERRUPT`, which was annotated
"Swept" and had never been swept, repeated fourteen more times.

**No figure changed.** This entry moves no number. It removes claims about where numbers
came from and what was done to them.

**Downstream effect:** `data/knowledge/corpus.yaml` regenerated, because its header is
emitted by `src/wha/service/corpus.py` and carried the same claim into every retrievable
passage.

**What replaces the file-level claim: nothing.** Provenance belongs on the individual
number, where `CITED`, `DERIVED` and `ASSUMED` already carry it, and roughly 140 of these
numbers are `ASSUMED`. A file-level label cannot be true of a file that contains both.

---

## 2026-09-04 — `causes.yaml`, luteal citation string

**Changed:** wrist skin temperature `+0.44 C` to `+0.45 C`, respiratory rate `+0.60/min` to
`+0.47/min`.

**Source:** Goodale BM, Shilaih M, Falco L, Dammeier F, Hamvas G, Leeners B. Wearable
sensors reveal menses-driven changes in physiology and enable prediction of the fertile
window. *J Med Internet Res.* 2019;21(4):e13404.

**Working:** the paper reports phase means. Late luteal wrist skin temperature 34.32 C
against follicular 33.87 C, a difference of **0.45**. Late luteal respiratory rate 17.04
breaths/min against follicular 16.57, a difference of **0.47**.

**Downstream effect: none.** Neither wrist skin temperature nor respiratory rate is
ingested by this build; the Galaxy Watch 5 does not provide either at a usable sampling
rate. The heart rate figure in the same string, +3.91 bpm, is the only one the belief model
computes with, and it was already exactly right (60.47 - 56.56).

**Why it mattered anyway:** that string is rendered into the retrievable corpus as a
citable passage. A reader checking the agent's evidence would have found two figures that
do not match the paper, which undermines every figure beside them.

---

## 2026-09-04 — `constants.py`, `EXERCISE_EFFECT_BPM`

**Changed:** `{"0-2h": 4.14, "2-4h": 2.91, "4-6h": 1.58}` to
`{"0-2h": 2.91, "2-4h": 1.87, "4-6h": 1.58}`.

**Source:** Leota J, et al. Dose-response relationship between evening exercise and sleep.
*Nat Commun.* 2025;16:3297. Kept at `research/papers/leota-2025-nat-commun-16-3297.pdf`
(open access, CC BY), because the publisher blocks automated fetching and a figure that
cannot be re-checked is not really verified.

**Working:** the paper's table gives incremental contrasts between adjacent strain levels.
High strain against no exercise is their sum: 1.58 bpm at -6h, 1.87 at -4h, 2.91 at -2h,
5.59 at sleep onset. Of the three stored values, 2.91 and 1.58 are exactly the paper's
figures at -2h and -6h, and 4.14 appears nowhere in the table. The two traceable values
were also assigned to bands one step apart from each other, so there was no single
convention. Full derivation in `docs/CORPUS-VERIFICATION.md`.

**Rule applied:** each band takes the paper's value at the edge furthest from sleep onset,
which is the smallest figure the paper supports for that band.

**Downstream effect, measured.** This quantity is subtracted from the observed elevation,
so lowering it raises the residual and makes the system slightly more likely to
investigate. That is the direction this system's own utilities prefer, weighing a missed
illness nine times a false alarm. All eleven frozen scenarios still pass, including
`workout-explained`, which is the one that depends on a workout explaining a night away.
Two unit tests asserted the literal 4.14; both were corrected to the sourced value with the
reason recorded, and neither assertion was weakened.


---

## 2026-09-04 - `sources.yaml`, MedlinePlus URL

**Changed:** the single hardcoded `url` replaced with `index_url` plus a documented
`url_pattern`.

**Why:** the recorded URL, `https://medlineplus.gov/xml/mplus_topics_compressed.zip`,
returns **404**. MedlinePlus publishes dated snapshots Tuesday to Saturday, named
`mplus_topics_compressed_YYYY-MM-DD.zip`, and no undated file exists or appears ever to
have existed. The recorded size, 29 MB, matches the uncompressed XML rather than the zip,
which is about 4.6 MB, so the entry looks like it was written from the documentation page
without the download ever being attempted.

**Consequence at the time:** none visible, which is the problem. `wha data fetch corpus`
returned "Corpus target verified" having checked nothing and downloaded nothing, so the
command reported success while the consumer health layer stayed absent and the agent went
on refusing every question about a condition.

**Now:** the newest snapshot is resolved from the index page at fetch time, so the entry
cannot rot again, and the snapshot actually used is recorded with its SHA-256 in
`data/knowledge/corpus-sources.json`.
