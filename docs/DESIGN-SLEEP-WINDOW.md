# Which window a night is measured over

**Decision.** A night's resting heart rate is measured over the **main overnight sleep
session the watch recorded**, using only its non-awake spans. Where the watch recorded no
sleep, local 00:00 to 07:00 is used and the night is labelled as such.

This replaces a fixed local 00:00 to 07:00 window for every night and every person.

---

## Why sleep at all, and not the whole day

The watch reports heart rate around the clock. The system stores all of it and uses only
the part recorded while asleep: for the first real subject, 11,853 samples stored and 1,473
minutes used, about 12 percent.

**Daytime heart rate measures behaviour, not physiology.** Standing up, coffee, a phone
call or a flight of stairs move it by tens of beats per minute. An infection moves nocturnal
resting heart rate by roughly 1.6 to 5 (`data/knowledge/causes.yaml`). The signal exists in
daytime data and is buried under everything the person did that day.

Sleep is the closest a wrist device gets to a controlled measurement: one posture, no
motion artefact, no volitional input, at roughly the same point in the circadian cycle each
night.

**Evidence.** Mishica, Kyröläinen, Hynynen, Nummela, Holmberg and Linnamo 2022, *PLoS One*
17(1):e0262333, compared heart rate indices measured during nocturnal sleep against morning
orthostatic tests in young endurance athletes over three weeks. Morning values showed
significantly higher variation, and the authors state: *"During sleep, individuals are no
longer affected by external stimuli and therefore, enhanced reliability may exist for
recordings that occur during sleep."*

The two other sources this build depends on are built the same way: NightSignal (Alavi et
al. 2022), which supplies the detection thresholds, operates entirely on overnight RHR, and
Dial et al. 2025 validates nocturnal RHR in consumer wearables against ECG.

**Daytime data is not discarded, only daytime heart rate.** The previous day's step count
and any recorded exercise session are used as covariates, to subtract the elevation a
workout would be expected to produce before a night is judged. The first real subject's
night of 2 September carried 2.9 bpm of explained elevation from exercise for exactly this
reason.

**The cost, stated plainly.**

1. **One reading per night.** Detection requires two consecutive elevated nights, so the
   system runs up to about 48 hours behind. A daytime signal could in principle be faster;
   it would also be far noisier, and a false alarm costs the interruption budget the whole
   design exists to protect.
2. **No sleep, no reading.** A night the watch records heart rate for but no sleep produces
   nothing. The first real subject has six such nights, reported as `NA` rather than guessed.

---

## Why the fixed window was wrong

The fixed window is the NightSignal definition, from **Alavi et al. 2022, Nature Medicine
28:175-184**, and it was the right choice *for that study*: its data had no sleep staging,
so clock time was the only available proxy for "asleep". This build has staging. Keeping
the proxy while holding the real signal copies a limitation rather than a method.

The cost was measured, not assumed. The first real subject slept:

| Night | Actual sleep | Captured by 00:00-07:00 | Awake time counted as sleep |
|---|---|---|---|
| 31 Aug 2026 | 03:04 to 10:05 (5.9h) | 3.9h | 3.1h |
| 01 Sep 2026 | 03:39 to 10:55 (6.2h) | 3.4h | 3.6h |
| 02 Sep 2026 | 02:37 to 11:18 (6.8h) | 4.4h | 2.6h |

Roughly half of each measurement window was waking time, and about 40 percent of the
actual sleep was discarded. Recomputing the same nights over the recorded sleep:

| Night | RHR, clock window | RHR, sleep window | Change |
|---|---|---|---|
| 31 Aug | 51.0 | 44.0 | -7.0 |
| 01 Sep | 56.0 | 45.0 | -11.0 |
| 02 Sep | 48.0 | 45.0 | -3.0 |

The readings were 3 to 11 bpm too high. The **spread matters more than the level**: it
fell from 8 bpm (48 to 56) to 1 bpm (44 to 45). Because the baseline is computed the same
way as the observation, a constant offset largely cancels; variance does not. Inflated
variance raises the baseline's `scale`, which widens the detection band and makes the
system **less sensitive to the illness it exists to detect**. For this subject the personal
scale fell from about 4.5 bpm to the 1.5 bpm floor.

For anyone whose sleep does not align with the clock at all, a night-shift worker sleeping
08:00 to 16:00, the fixed window measured essentially none of their sleep.

**Supporting evidence for measuring over the device's reported sleep period:**
Dial et al. 2025, *Physiological Reports* 13:e70527, validation of nocturnal resting heart
rate and heart rate variability in consumer wearables.

---

## Who this helps, measured on more than one person

**CORRECTED 5 September 2026.** Everything above is measured on one subject, and it
presented this change as a general improvement. It is not one, and saying so is more
useful than the stronger claim.

Measured on the 21 participants in the Mishra 2020 cohort who have sleep staging, scoring
the same nights both ways (`uv run python experiments/detection/cohort/report.py`):

| Night-to-night wobble on the sleep window | People |
|---|---|
| **Better** (smaller spread) | 6 |
| **Worse** (larger spread) | 5 |
| **Unchanged** | 10 |

The reason is simple: only 3 of the 21 sleep much outside midnight to 07:00. For a
conventional sleeper the two windows cover nearly the same minutes, so there is nothing
for the change to improve.

**So the honest statement is conditional.** Measuring over recorded sleep is strongly
justified for somebody whose sleep does not align with the clock, which includes this
system's first real subject, who sleeps roughly 03:00 to 11:00 and for whom the fixed
window discarded about 40 percent of the sleep and counted three hours of waking time as
sleep. It is roughly neutral for somebody who sleeps 23:00 to 07:00.

It is still the right default, for a reason that does not depend on the average: the
system cannot know in advance which kind of sleeper it has, the clock window fails badly
for one kind and gains nothing for the other, and the failure is silent. A default that is
neutral for most people and important for some is worth having. That is a different
argument from "it is better", and it is the one the data supports.

---

## Naps are excluded

Only the **single longest sleep session ending on that local date** is used. A second sleep
block on the same day is ignored.

**Evidence.** Whitehurst, Naji and Mednick 2018, *Neurobiology of Sleep and Circadian
Rhythms* 5:52-57. Thirty-two adults, within-subjects, polysomnography and ECG, a daytime
nap and a night of sleep at least one week apart. RR intervals were **longer during
nighttime sleep than during daytime naps in both stage 2 and slow wave sleep**, meaning
heart rate is measurably higher during naps at matched sleep stages.

Pooling naps with overnight sleep would therefore mix two distributions with different
means, and shift a night's reading by however much the person happened to nap that day.
That is the same night-to-night noise this change exists to remove.

**Stated limitation:** a genuinely biphasic or polyphasic sleeper has part of their sleep
ignored. This is disclosed on the History page, not only here.

---

## What this does not fix

**Sleep apnoea.** Apnoea raises heart rate during sleep chronically. The baseline is
personal and adapts over a 28-night trailing window, so chronically elevated sleeping heart
rate is learned as the subject's normal and never flagged. A better window does not change
this. Detecting apnoea needs heart rate variability, respiratory rate, or a continuous
blood oxygen stream, none of which this device provides. Disclosed on the History page.

**Consumer sleep staging is not polysomnography.** This replaces a poor proxy for sleep
with a good one, not with ground truth. Samsung's staging is reasonable but imperfect, and
a night whose staging is wrong produces a window that is wrong in the same way.

---

## Divergence from the cited thresholds

The 3.0 and 4.0 bpm transitions come from NightSignal, which used the fixed window. Those
thresholds are applied to the **residual against the subject's own baseline**, and both the
baseline and the observation are computed with the same window, so the comparison stays
internally consistent. The change makes the underlying measurement cleaner, so a residual
of a given size is more meaningful than it was, not less. Thresholds calibrated on noisier
data are, if anything, conservative when applied to cleaner data.

This divergence from the source is deliberate and is recorded in `docs/CONTRACTS.md`.

---

## Implementation notes

- Sessions are reconstructed from `sleep_stages` by a `SLEEP_SESSION_GAP_MINUTES` (60)
  gap. Stored rows carry no session identifier; within a Health Connect session stages
  abut one another and separate sessions are hours apart, so this needs no migration.
- Awake spans **inside** a session are excluded. The first subject's nights contained 37 to
  58 separate asleep spans, so measuring from session start to session end would have
  reintroduced the same error in miniature.
- `MIN_NOCTURNAL_MINUTES` (180) is unchanged but now means 180 minutes of **recorded
  sleep** rather than of clock time.
- The exercise covariate now measures back from **sleep onset** rather than from midnight,
  which is what "how long before you fell asleep did you exercise" always meant.
- `nightly_features.rhr_window_source` records `sleep` or `clock` per night (schema v4).
- The nightly job no longer runs at a fixed 09:00. It re-scores a trailing window every few
  hours, so a night settles once its sleep has been recorded, whatever time the person
  wakes. A 09:00 cron assumed the subject was awake and synced by then; the first real
  subject wakes around 11:00.
