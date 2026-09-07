# What a night is compared against

**Decision.** Once a subject has `BASELINE_MIN_NIGHTS_PERSONAL` (7) usable nights, the
baseline centre is **their own median**, with no population blending. Below that the
shrinkage estimate is kept and **nothing is flagged at all**.

This replaces a centre that was always shrunk toward the population mean.

---

## The defect

`compute_baseline` blended the person's median with the population prior of 62.75 bpm at
weight `w = n / (n + 7)`. Because `BASELINE_WINDOW_NIGHTS` truncates the history to 28
nights, `n` never exceeds 28, so **`w` caps at 28/35 = 0.800 permanently**. A fifth of the
population prior never washes out, however long someone uses the system.

Detection compares tonight against that centre. So every subject carries a constant
residual offset proportional to how far their true resting heart rate sits from 62.75.

Measured on a steady subject after **200 nights** of their own data:

| True sleeping RHR | Centre | Residual every night | Level |
|---|---|---|---|
| 42 | 46.1 | -4.1 | GREEN |
| 45 | 48.5 | -3.5 | GREEN |
| 62.75 | 62.8 | 0.0 | GREEN |
| 75 | 72.5 | +2.5 | GREEN |
| 80 | 76.5 | +3.5 | **YELLOW every night** |

The consequences are severe at both ends:

- A subject at **45 bpm** needed a **6.5 bpm rise** to reach YELLOW. Infection raises
  nocturnal RHR by roughly **1.6 to 5 bpm** (`data/knowledge/causes.yaml`). **They would
  never have been flagged for an infection.** The first real subject of this system sits
  at 44 to 47.
- A subject at **80 bpm** sat at YELLOW every night while perfectly healthy.

The detector is tuned to a 3 to 4 bpm change while carrying up to a 4 bpm bias from the
prior alone. Its sensitivity depended on how close the subject happened to sit to the
population average.

---

## Why the personal median is the correct reference

The thresholds are not ours. `DETECT_YELLOW_BPM = 3.0` and `DETECT_RED_BPM = 4.0` come from
**Alavi et al. 2022, Nature Medicine 28:175-184**, the NightSignal algorithm. That paper
states its baseline plainly:

> "For each individual, we use the **streaming median of average overnight RHR** as the
> baseline."

No population blending. Its 3 and 4 bpm transitions are deviations **above the person's own
median**. Applying those numbers to a shrunk centre is a category error: the thresholds
were never calibrated against a reference that carries a population offset.

**Seven nights** comes from the same paper: "for over 80% of the participants, the proper
baseline was observed after only seven nights", to within two bpm. It also coincides with
where this system's own rung ladder already begins `SHRINKING`, so no new concept is
introduced.

---

## What is kept, and why

**The scale keeps its shrinkage.** `scale_bpm` sets the width of the displayed band and
`robust_z`. It never sets the level, which is decided by fixed bpm thresholds against the
centre. Borrowing spread from the population while little is known is a truthful statement
of uncertainty, not a bias in the decision, so it stays.

**Below seven nights the shrinkage centre is kept**, because a median over one or two
nights is noise, and a wide band around a borrowed centre is the honest picture. The
History page already labels this state: "This band is not yet yours."

**Nothing is flagged below seven nights.** There was no such guard: a subject with two
nights of history could be flagged and have an investigation opened against a baseline
that was 78 percent population guess. Levels are still computed and stored, so the night is
charted and feeds the baseline; it simply cannot raise an alert. This is what the source
algorithm does over the same period.

---

## The step at seven nights

The centre moves discontinuously when the seventh usable night arrives: for a subject at
45 bpm it drops from about 54.6 to 45.0. This is visible on the History chart.

It is deliberate and is not smoothed. It marks the transition from "compared against a
typical adult" to "compared against you", which is a real change in what the number means,
and the interface says so on both sides of it. Smoothing it would blur the one moment the
reader most needs to understand.

---

## What this does not change

Detection remains one-sided: only elevation is investigated. See
`docs/DESIGN-SLEEP-WINDOW.md` for that and for the sleep apnoea limitation, neither of
which this change touches.
