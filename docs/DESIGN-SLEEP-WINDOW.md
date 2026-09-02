# Which window a night is measured over

**Decision.** A night's resting heart rate is measured over the **main overnight sleep
session the watch recorded**, using only its non-awake spans. Where the watch recorded no
sleep, local 00:00 to 07:00 is used and the night is labelled as such.

This replaces a fixed local 00:00 to 07:00 window for every night and every person.

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

This divergence from the source is deliberate and is recorded in `plan/02-contracts.md`.

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
