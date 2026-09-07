# Changes to the clinical knowledge files

> ## You do not need to read this file. You need to WRITE to it.
>
> This is the record of every clinical figure that has changed, and why. It is an
> obligation, not reference reading: **if you change any number in `data/knowledge/` or any
> clinical constant in `src/wha/constants.py`, you add an entry here**, with the old value,
> the new value, and either the sentence quoted from the source or the command that
> reproduces the measurement.
>
> The format is obvious from any entry below. Read one, then write yours. You do not have to
> read the rest.
>
> The rule this enforces is rule 4 in `AGENTS.md`. A clinical number that moves without
> evidence is the single worst thing that can happen in this repository, because it becomes
> a retrievable, citable passage and the citation makes it look more trustworthy rather than
> less.

`data/knowledge/` and the clinical constants in `src/wha/constants.py` are under change
control. The rule exists because a wrong number in them becomes a retrievable, citable
passage, and the citation makes it look more trustworthy rather than less.

A figure may change when, and only when, one of two things holds:

1. **The published source it cites can be quoted contradicting it.**
2. **A measurement made in this repository, on real data, with the script committed**,
   contradicts it.

> **What "measurement" means in this file, and what it does not.** It means an analysis run
> by this project, on an archive of data collected by somebody else for another purpose,
> with the script committed so anybody can re-run it. It does **not** mean a clinical trial,
> peer review, or validation against any clinical outcome, because this project has none of
> those. A figure derived that way is good enough to choose a parameter and is not evidence
> that this system works. Where such a derivation appears below, it is labelled and the
> reproducing command is given. See `experiments/README.md`.

No new clinical content may be added, no figure may be changed on judgement, and every edit
is recorded here with the old value, the new value, what it changed downstream, and either
the quoted source sentence or the command that reproduces the measurement.

If an entry below cannot be checked against its paper, or re-run from the command given, it
should not have been made.

---

## 2026-09-05. `causes.yaml`, the infection row

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
cannot separate from it. Reproduce with `uv run python experiments/detection/cohort/infection.py`.

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

## 2026-09-05. `constants.py`, the band's width no longer borrows a between-person spread

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
uv run python experiments/detection/cohort/band_width.py
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
from `POP_PRIOR_RHR_SD_BPM`. The contract is not edited here. Recorded in `docs/DISCLOSURES.md`.

---

## 2026-09-05. `causes.yaml`, `exertion.effect_mean_bpm`

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

## 2026-09-05. every file, the authorship header

**Changed:** every `Authored by a human` and equivalent claim removed. `READ ONLY` kept.
Also removed: fourteen "Swept." annotations across `causes.yaml` and `probes.yaml`, the
header line requiring that every `ASSUMED` figure "MUST appear in the sweep", and the
sentence in `probes.yaml` claiming "All are swept in the sensitivity analysis".

**Source: this repository, checked directly.** These files were generated by a language
model, not written by a person. The `Swept` claims are separately false: the only sweep in
the codebase is `COST_WEIGHT_SWEEP` in `src/wha/eval/policy_oracle.py`, which ranges over
`POLICY_COST_PER_INTERRUPT` and nothing else. No effect size and no likelihood row in
either file has ever been varied by any code here. The claim is the same shape as the one
`README.md` already records against `POLICY_COST_PER_INTERRUPT`, which was annotated
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

## 2026-09-04. `causes.yaml`, luteal citation string

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

## 2026-09-04. `constants.py`, `EXERCISE_EFFECT_BPM`

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

---

## 2026-09-05. `probes.yaml`, the alcohol question drops to two options

**Changed:** `probe_alcohol.answer_space` from `None / 1 to 2 / 3 to 4 / 5 or more` to
`None / Yes`, and the likelihood rows from four columns to two, summing the three drinking
columns.

**Why.** The belief model has a single on-off alcohol switch. All three drinking answers
produced exactly the same posterior, so a whole interruption was being spent collecting a
detail nothing could use, and the question implied a precision the model does not have.
The merge is the only one that leaves the belief unchanged for anyone who would have
answered any of the three.

**Not scaled by amount, deliberately.** The paper supports dose dependence, but no
published figure maps "3 to 4 drinks" to a number of beats. Building that would mean
inventing exactly the kind of number this directory is not allowed to contain. The free
text is still recorded, so the detail is not lost.

**Two tests restated, not weakened.** One passed `option_id="three"`, which no longer
exists, so it contributed no likelihood factor at all and measured a zero shift. The other
passed two labels against a four-slot probe to trigger a mismatch, and two now matches; it
passes three instead. Both are about the mechanism, not about a particular count.

---

## 2026-09-05. `causes.yaml`, what the alcohol figures actually measure

**Changed:** the `citation` block. No figure moved.

**Why.** It presented Grosicki's 2.8 and 2.4 bpm as per-drink effects. They are the
contrast between **one drink above** a person's own average and **one drink below** it, a
two-drink span, not the effect of drinking against not drinking. Reading them as per-drink
and taking the midpoint gives the stored 2.60. That is defensible for "drank last night"
only because the span brackets it, and the file now says so rather than leaving a reader
to infer a measurement the paper did not make.

## 2026-09-05. `triage_rules.yaml`, the blood oxygen thresholds were credited to WHO

**Changed:** the attribution and the caveats on `spo2_home_thresholds`. The numbers
themselves, 92 and 94 percent, did not move.

**Was:** "WHO guidance as reported in the wearable SpO2 literature: above 94 percent can be
cared for at home, below 93 percent warrants medical attention."

**Is:** NHS England's COVID Oximetry @home pathway, with the British Thoracic Society's
target range for the upper band, and a population caveat attached.

**Why, with the sources.** WHO's January 2021 guidance recommends *using* home pulse
oximetry; it does not publish these levels. The levels are NHS England's: 92 percent or less
means attend an emergency department within the hour or call 999, and 93 or 94 percent means
contact 111 or a GP. The 94 to 98 percent range is the British Thoracic Society's target
range for oxygen therapy in adults. Crediting a specific numeric threshold to the wrong body
is the same class of error as inventing it, because a reader who checks WHO will not find it.

**The caveat that matters more than the correction.** That pathway is written for people
**already diagnosed with COVID-19 and being monitored at home**. It is not a screening rule
for somebody who is well, and this system applies it to somebody who is well. That is now
stated in the file, and it is the reason this rule may only ever raise urgency and says "get
a proper reading taken" rather than naming a condition.

**One line was also removed for being wrong in the person's favour.** The file said these
sensors "read high on darker skin, so a genuine fall can be missed entirely". Singh et al.,
*J Med Internet Res* 2024;26:e62769, found overestimation "for both light and dark skin
pigmentation", so the warning applies to everybody rather than only to darker skin. The same
review concludes the overestimation "may not be clinically relevant", and that qualification
is now stated rather than left out because it weakens the point.

---

## 2026-09-05. `triage_rules.yaml`, Downie is quoted with its population attached

**Changed:** a comment, not a number, and it is here because the comment is what justifies
the design.

Downie et al. was quoted as the reason not to trust a single matched phrase. The quotation
is accurate, but it is **a review of red flags for cancer and fracture in low back pain**.
It was not measured on chest pain or on any presentation this system routes. The file now
says so, and the argument for what to *do* instead is carried by Sutaria et al., *BMC Health
Serv Res* 2025;25:1263, which measured online symptom checkers seeking only 36.9 percent of
relevant red flags against 71.8 percent for primary care physicians. That paper is about
symptom checkers, which is what this is.

A citation that supports a design in spirit but was measured on a different population is
still worth quoting. Quoting it without its population is not.

---

## 2026-09-05. `red_flags.yaml`, `outcome_guidance` added

**Changed:** two lines of care-pathway text moved into this file. **No new clinical content.**

They were `DEFAULT_ESCALATION_CRITERIA` in `src/wha/safety/output_checks.py` and are moved
unchanged, so every care-pathway sentence lives in one file and the corpus can cite all of
them. They are the tier A and tier B lists in this same file, summarised: chest pain,
breathlessness at rest, fainting and confusion are `rf_chest_pain`, `rf_breathless_at_rest`,
`rf_syncope` and `rf_confusion`; fever and body aches are `rf_fever` and `rf_body_aches`, and
"see a doctor today" is `rf_fever`'s own guidance.

**Why.** The "when to seek care" text was previously free text from the language model and
was the only text in the system that passed through no check at all. A live run produced
"Seek care if fever persists beyond 72 hours or exceeds 103 degrees F (39.4 C)". Both
thresholds came out of the model. They are close to mainstream advice, which is luck rather
than sourcing, and is exactly why this class of error is hard to catch by reading. Nothing is
generated now, so there is nothing left to guard.

---

## 2026-09-05. `probes.yaml`, `probe_cycle` retired

**Changed:** one question removed. **No figure changed.**

The luteal cause is a plain on-off in the belief model, and `cycle_last_period_start` was
never read by anything. The fact the model actually needs, whether the person menstruates at
all, is a standing fact about a person rather than something to spend part of a weekly
interruption budget on, so it moved to the Settings profile. An already-answered probe is
still honoured through `wha.agent.nodes._cycle_applicability`, so nobody who answered it is
asked again.

**Why this is a knowledge change and not just a code change.** The question was priced at
0.4 of an interruption on the grounds that it was a one-off setup question. Removing it
returns that allowance, and it removes a question whose answer could not reach the belief
model at all: no production caller passed the cycle fact into `update_belief`, so luteal sat
clamped at 0.0 on every live run. Asking for something that changes nothing is the worst
possible use of an interruption budget.

## 2026-09-05. `red_flags.yaml`, every safety number now says where it came from

**Changed:** provenance labels added to eleven numbers. **No number moved.**

**Why.** This is the standing rule, applied to the file that needs it most, and until now
it was not applied here at all. `causes.yaml` and `probes.yaml` have carried a per-row
`provenance` since they were written, validated on load and pinned by tests. This file
carried none, while its own footer says its numbers are "the only place in this project
where a wrong number has a real-world consequence".

| Number | Label | Basis |
|---|---|---|
| `rf_rhr_extreme_high` robust z above 6.0 | **DERIVED** | The largest single effect in `causes.yaml` is the luteal plateau at 3.91 bpm and the measured within-person scale is 3.71 bpm, so six scaled MADs is about 22 bpm, beyond any combination in the table. Fires on 0.6 percent of 7,865 cohort nights. `experiments/detection/cohort/band_width.py` |
| `rf_rhr_extreme_low` robust z below -6.0 | **DERIVED** | The mirror of the above, from the same two numbers |
| `cold_rung_fallback_bpm_above: 100` | **ASSUMED** | **No evidence found.** The conventional resting tachycardia boundary, but no source was fetched and verified here and none is claimed |
| `cold_rung_fallback_bpm_below: 40` | **ASSUMED** | **No evidence found.** A conventional marked-bradycardia boundary; trained endurance athletes sleep below it routinely, which is why it can only raise urgency |
| Six `persist_nights` windows: 3, 4, 4, 2, 2, 2 | **ASSUMED** | **No evidence found.** No study was located measuring how many nights a tier B symptom should persist before it is worth a same-day appointment |

**What was NOT done, deliberately.** No citation was invented for any of the eight ASSUMED
numbers, and no number was moved to match a figure that sounded better sourced. The
standing rule says to state plainly that no evidence was found and label it, not to fill
the gap, and each `assumption` field begins with the words "NO EVIDENCE FOUND".

**Both halves of the rule.** `load_red_flags` now refuses to load a file where any of these
numbers lacks a provenance, so the labels cannot quietly fall off, and the Audit page
renders the table with a warning naming how many of them have no published source. A test
strips one label and asserts loading fails, because a guard that has never fired proves
nothing.

## 2026-09-05. `causes.yaml`, the last three CITED rows were not cited

**Changed:** `provenance` on alcohol, luteal and recovery_tail, from CITED to DERIVED, each
with a `derivation` naming which of its numbers comes from the paper and which does not.
**No number moved.**

**Why.** An audit checked every CITED row against its source. All three failed, and one of
them said so in its own text.

**alcohol.** The citation already read: "That is a defensible figure for 'drank last night'
only because the span brackets it; **it is not what the paper measured**." The row was
labelled CITED anyway. Grosicki reports +2.8 bpm in females and +2.4 in males for the
contrast between one drink *above* a person's own average and one drink *below* it, a
two-drink span. 2.60 is the midpoint. The base rate of 0.299 **is** the paper's, directly.
`effect_sd_bpm` 1.10 is in no paper: NO EVIDENCE FOUND.

**luteal.** `effect_mean_bpm` 3.91 **is** Goodale's, read off the paper's own phase means.
`base_rate` 0.450 is derived from "roughly 12 to 14 luteal days per 28-day cycle", which the
paper states; 13/28 = 0.464, rounded down. `effect_sd_bpm` 1.20 is in no paper: NO EVIDENCE
FOUND.

**recovery_tail.** The weakest of the three. Radin supports the recovery *window*, roughly
79 days, and nothing else in the row. `base_rate` 0.020, `effect_mean_bpm` 1.50 and
`effect_sd_bpm` 1.50 are all NO EVIDENCE FOUND. Radin's "13.7 percent remained more than 5
bpm above baseline beyond 133 days" bounds the tail but gives no mean for the population
inside the window.

**The structural cause, which is the part worth keeping.** A row carries ONE `provenance`
for four or more numbers of different standing. The rule that resolves it already existed
in this repository, in a comment on the episode panel: *a row is only as sourced as its
weakest load-bearing number*. It was applied to the temporal profile and to nothing else.
It now applies to the label as well, which is why `causes.yaml` has no CITED rows left: not
because the evidence got worse, but because the labels stopped rounding up.

**On screen too.** The panel marked a cause unsourced only when its provenance was ASSUMED
or its profile had no source, so every DERIVED row read "from a study". Alcohol is one of
the largest confounders in the table and read as sourced while holding an unevidenced
spread. `get_knowledge_provenance` now reports `has_unevidenced_number` when a derivation
contains the words NO EVIDENCE FOUND, and the panel marks those rows "not measured". Two
tests: one asserts no CITED row's own backing contradicts its label, the other asserts every
row naming an unevidenced number is marked on screen. Putting alcohol back to CITED fails
the first with "its own citation says the paper did not measure it".

---

## 7 September 2026: `red_flags.yaml` gains a tracked tier, and a half-fictional header is corrected

**What changed in the knowledge file.**

1. **A `tracked:` section**, holding one symptom: `sx_dizziness`. Recorded over time,
   escalates on nothing.
2. **The header's Tier B line, corrected.** It read "two or more, or persistence beyond a
   stated duration". The second half had never been true.

**Why the header was fiction, and how that was established.** Not by reading the code, by
running it. `check_red_flags_deterministic` accepts a `symptom_history` argument. Grep
finds three references across the repository: the parameter itself, a pass-through in
`tier_c.py`, and one unit test that supplies the dict by hand. No production caller ever
passed it. So `history.get(rule_id, 1)` returned 1 on every call, and 1 is never greater
than 2, 3 or 4. Five nights of a worsening fever through the real path:

```
night 1 'I have a fever'          -> escalate=False
night 2 'still feverish today'    -> escalate=False
night 3 'fever is worse'          -> escalate=False
night 4 'burning up, fourth day'  -> escalate=False
night 5 'still got a fever'       -> escalate=False
```

All six Tier B `persist_nights` values were unreachable. Each carries a written safety
argument, of the form "a SHORTER window escalates sooner, so the error this carries is an
unnecessary appointment rather than a missed one". Those paragraphs described behaviour the
system did not have. **No number changed. They simply began to be read.**

"Two or more co-occurring" was separately implemented as two or more *in the same message*,
so a fever on Monday and vomiting on Tuesday scored as two unrelated singletons. Co-occurrence
now spans `SYMPTOM_COOCCURRENCE_WINDOW_NIGHTS`, which is DERIVED from the shortest
`persist_nights` in this file (`rf_poor_intake` and `rf_persistent_vomiting`, both 2) rather
than invented.

**Why `tracked` exists rather than a new tier.** Dizziness had no good home. Putting it in
Tier A or Tier B asserts a routing threshold no source supports; leaving it out means a
person can report it, have it worsen for three nights, and have the system record nothing
and ask nothing. Tracking asserts nothing clinical. It says only "you told us, so we will
remember and ask". A tracked symptom counts toward nothing in Tier B's arithmetic; it keeps
an investigation from closing as benign while outstanding, and gives the follow-up rule
something to ask about. Neither is a claim about care, which is exactly why it is the right
home for a symptom with no evidence base.

**What was deliberately NOT added, and the prediction recorded before testing it.** Severe
abdominal pain. It is a WHO and CDC dengue warning sign and would be defensible in Tier B.
It is held out on purpose as a live test of whether the agent can recognise the significance
of a symptom nobody hand-coded for it. Pre-registered prediction, written before the test
was run: **it will fail.** `corpus.yaml` contains the word "dengue" zero times, so
`enforce_grounding`'s verbatim containment test makes a grounded dengue claim impossible,
and Tier C is handed only the Tier A and Tier B ids and can return nothing else. The only
surviving route is an uncited note.

**Related constants, outside this file but carrying its reasoning.** `SYMPTOM_RUN_GAP_DAYS`
is CITED at 7: respiratory illness surveillance conventionally separates two episodes by at
least seven symptom-free days, and it is checked against saddleback dengue, whose second
fever peak arrives one to two days after defervescence, so a biphasic fever stays one
illness. `SYMPTOM_FOLLOWUP_MAX_PER_EPISODE` is ASSUMED at 3 and marked unevidenced on the
dashboard.
