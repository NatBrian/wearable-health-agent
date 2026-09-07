# What this system changed from the algorithm it cites, and what the evidence says

**Written 5 September 2026.**

The detection thresholds here, 3 bpm and 4 bpm, come from NightSignal: Alavi et al.,
*Nature Medicine* 2022;28:175-184. That paper reports **78 percent sensitivity**, and this
project has quoted that figure as support for its own thresholds.

That number was measured on NightSignal's algorithm. This one is not NightSignal. Five
defining choices differ, and until this note existed a reader could not tell which parts of
the published evidence transfer.

Three of the five turn out to be justified, one was reverted, and one is untested. That is
a better story than silence, and it is what this file is for.

---

## The five differences

| | NightSignal, as its authors wrote it | This system | Verdict |
|---|---|---|---|
| **The window** | midnight to 06:59 | the sleep the watch recorded | **justified**, and narrower than previously claimed. See below and `docs/DESIGN-SLEEP-WINDOW.md` |
| **Which minutes** | only minutes with zero steps | every minute in the window | **justified**, measured. See below |
| **The night's number** | the **mean** | the **median** | **justified**, and it is why the step filter is unnecessary |
| **The baseline** | every previous night, including tonight, as a streaming median | the last 28 nights, excluding tonight | **reasonable, untested.** Nothing here measures the difference |
| **The alert rule** | two consecutive nights at or above baseline + 4 | *was* two raised nights with at least one at +4 | **was not justified. Reverted 5 September 2026** |

---

## The step filter, measured

NightSignal takes only minutes where the step count is zero. This system takes every
minute inside the window. An earlier draft of the review recommended adopting the filter,
on the theory that it removes movement artefact.

It was tested on 101 real people, scoring the same nights both ways:

| | Night-to-night wobble (scaled MAD) |
|---|---|
| Every minute in the window | **2.97 bpm** |
| Only minutes with zero steps | **2.97 bpm** |

Only 15 of 101 people improved. The median change was zero.

**And the reason is the row above it in the table.** NightSignal takes the **mean** of the
night, which a handful of moving minutes drags upward, so it has to filter them out. This
system takes the **median**, which is already robust to a minority of high minutes. The
step filter is redundant here *because* of the median.

Two deviations that look independent are one choice and its consequence. Together they are
sound, and adopting the filter would add a data requirement, a failure mode when step data
is missing, and nothing else.

---

## The alert rule, reverted

This is the one that was wrong, and it was quietly wrong: the project cited NightSignal's
sensitivity while running a looser rule than NightSignal's.

NightSignal raises a red alert on **two consecutive nights at or above baseline + 4**. This
system flagged **two consecutive raised nights with at least one at +4**, so a red night
followed by a yellow one fired as well.

Measured on 30 labelled COVID-19 cases and 76 people with no illness label, over 738
person-weeks, in a window of **7 days before symptom onset to 1 day after**
(`uv run python experiments/detection/cohort/sweep.py`).

That is a NARROWER window than the "7 days before, 3 after" row in the results table below,
which is why the same rule reads 53.3 percent here and 66.7 percent there. Both were called
"the seven day window" in an earlier draft of this file, which made one rule look like two
results. The sweep is deliberately the tighter of the two: a threshold that only wins on a
wide window has not shown pre-symptomatic detection.

| Yellow | Red | Rule | Sensitivity | Investigations per person-week |
|---|---|---|---|---|
| 3 | 4 | at least one RED | 60.0% | 0.272 |
| 3 | 4 | **both RED** | **53.3%** | **0.198** |
| 4 | 5 | at least one RED | 53.3% | 0.195 |
| 5 | 6 | at least one RED | 50.0% | 0.144 |

The looser rule bought 6.7 points of sensitivity, which is two cases in thirty, for **37
percent more investigations** on people who were not ill. Every investigation opened on a
healthy person is a chance to interrupt them for nothing.

Changed to the published rule on 5 September 2026. The thresholds themselves stay at 3.0
and 4.0: a sweep over both fixed and personal thresholds gives no reason to move them.

**What that cost, measured after the change.** Re-scored on the same cohort, the two
algorithms now agree case for case:

| Alert fired within | This system | Published NightSignal | Random, same rate |
|---|---|---|---|
| 3 days before onset, 1 after | 46.7% | 46.7% | 16.5% |
| 7 days before onset, 3 after | 66.7% | 66.7% | 34.2% |
| 21 days before onset, 7 after | 80.0% | 80.0% | 66.1% |

Before the change this system was about six points ahead at every window. **It no longer
beats NightSignal, and any claim that it does is now false.** That advantage was bought by
running a looser rule than the one being cited, which is not an advantage worth keeping.

Two things survive the change, and they are the honest claims:

- **It warns earlier.** Median lead time at the seven day window is **3.0 days** against
  NightSignal's 1.5.
- **It is quieter.** 150 investigations against 163 over 738 person-weeks on people who
  were never ill, one every 4.9 weeks against one every 4.5.

Both come from the other three differences, not from the alert rule.

---

## A personal threshold was tested, and is worse

The system computes `robust_z`, the rise divided by that person's own night-to-night
wobble, and has never used it to decide anything. The obvious question is whether it
should.

At every matched alert rate, the fixed threshold in beats is equal or better:

| At most this many alerts per person-week | Fixed, in bpm | Personal, in robust z |
|---|---|---|
| 0.28 | **60.0%** | 46.7% |
| 0.20 | **53.3%** | 46.7% |
| 0.15 | **50.0%** | 46.7% |
| 0.10 | **33.3%** | 26.7% |
| 0.05 | **26.7%** | 23.3% |

Dividing by a person's own wobble shrinks a noisy person's real signal along with their
noise. It is also badly quantised: heart rates are whole numbers, so a personal MAD lands
on multiples of 1.4826 and the threshold jumps in steps.

---

## The window, justified more narrowly than before

`docs/DESIGN-SLEEP-WINDOW.md` presented measuring over recorded sleep as a general
improvement. Measured on 21 people in the cohort who have sleep staging, the
night-to-night wobble got **better for 6, worse for 5, and stayed the same for 10**,
because only 3 of the 21 sleep much outside midnight to 07:00.

It is strongly justified for somebody who sleeps 03:00 to 11:00, which is this system's
first real subject, and roughly neutral for a conventional sleeper. Corrected in that file.

---

## What transfers, and what does not

**Transfers.** The 3 and 4 bpm thresholds, the seven-night baseline establishment figure,
and now the two-consecutive-RED alert rule, because all three are used as published.

**Does not transfer.** The 78 percent sensitivity figure. It was measured on NightSignal's
mean-of-zero-step-minutes over a clock window with an expanding streaming median, and this
system uses a median over recorded sleep with a 28 night trailing window. What this system
achieves is measured separately, on the same public cohort, and is published in
`RESULTS.md` beside a rate-matched chance floor.

**Untested.** The trailing 28 night window against an expanding one. Nothing here measures
it, and it is recorded as untested rather than assumed to be equivalent.
