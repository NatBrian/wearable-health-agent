# Component 05. Detection

**Phase:** A. **Module:** `src/wha/detect/`. **Depends on:** 03 features, 04 baseline.

The deterministic monitor. **This component alone sets `level` and `flagged`.** No model inference
touches this path, and that property is what lets the write-up claim there is no AI in the
safety-critical numeric path.

---

## 1. The chain

```
rhr_bpm  -  baseline.centre_bpm            = deviation_bpm
deviation_bpm  -  explained_bpm            = residual_bpm
residual_bpm  /  max(scale, floor)         = robust_z
residual_bpm  ->  level                    GREEN / YELLOW / RED
level over consecutive nights  ->  flagged
```

**The detector operates on the residual, not the raw deviation.** A 5 bpm rise on a night with a
recorded evening workout is not the same event as a 5 bpm rise with nothing on record, and treating
them alike is how a wearable alerting system reaches a 4% positive predictive value.

---

## 2. Explained-variance subtraction

```python
def explained_bpm(features: NightlyFeatures) -> tuple[float, list[str]]:
    """Deviation already accounted for by an AUTOMATICALLY RECORDED event."""
```

Only exercise is subtracted. The lookup is keyed on `exercise_end_offset_h`:

```python
EXERCISE_EFFECT_BPM = {"0-2h": 4.14, "2-4h": 2.91, "4-6h": 1.58}
```

From Leota et al. 2025, *Nature Communications* 16:3297, n=14,689, 4.08 million person-nights, the
"high strain" column. The full grid spans light to maximal; the high column is used as a
conservative middle, because strain is not recoverable from the data we have.

Beyond `EXERCISE_LOOKBACK_HOURS`, nothing is subtracted. The published finding is that sessions
ending four or more hours before sleep have little effect, so the 4 to 6 hour bucket is already
small.

### What is never subtracted, and why

**Short sleep.** The published effect on heart rate is small and poorly quantified, the meta-analytic
HRV effect is `SMD = -0.24`, and the authors caution it may be limited to specific conditions.
Subtracting an uncertain quantity would manufacture confidence. `sleep_hours` becomes a **covariate
for the belief model** instead, where it is evidence rather than an adjustment.

**Alcohol and stress.** Not recorded by any device. **That is precisely the gap the questions
exist to fill**, and it is the whole argument for the project. If they were subtractable there
would be nothing to ask.

Every subtraction appends a human-readable reason to `Detection.reasons`, for example
`"exercise ended 1.5h before the window, -4.14 bpm (Leota 2025)"`. Those strings appear in the
episode trace, which is where a reader sees the system deciding rather than executing.

---

## 3. Levels

```python
level = NA      if not features.usable
        GREEN   if residual_bpm < DETECT_YELLOW_BPM
        YELLOW  if DETECT_YELLOW_BPM <= residual_bpm < DETECT_RED_BPM
        RED     if residual_bpm >= DETECT_RED_BPM
```

Thresholds `3.0` and `4.0` bpm come from NightSignal (Alavi et al. 2022, *Nature Medicine*
28:175-184), which transitions at 3 and raises red at 4, on **overnight resting heart rate against a
streaming median**. Reported performance: 78% of symptomatic cases alerted at or before onset,
median 3 days early, 86.9% specificity per person-day.

**Absolute bpm, not the robust z, sets the level.** `robust_z` is computed and stored because it is
informative in the trace and in the evaluation, but the published thresholds are in bpm and using
them directly keeps the comparison honest. A z-based rule would tighten as the baseline matures and
would not be the method the citation describes.

`NA` is not a level between GREEN and YELLOW. It means the question was not asked.

---

## 4. Persistence and alert events

A single elevated night is not an alert. **A run is.**

```python
alert_event = a maximal run of consecutive nights at YELLOW or above,
              containing at least one RED,
              of length >= DETECT_PERSISTENCE_NIGHTS
flagged     = True on the night the run first satisfies that
```

Consecutive means consecutive **calendar** nights. An unusable night **breaks the run**, because
absence of evidence is not evidence of GREEN, and treating a gap as continuity would let a run span
a week of non-wear.

Persistence is the single strongest sensor-only discriminator available. In the deployed cohort,
red-alert clusters averaged **4.3 days in COVID-positive** participants against **1.9 days in
negatives**. Duration separates true from false alerts on its own, for free.

> **Concordance, honestly.** `history/PROPOSAL.md` F5 borrows credibility from a "two of five metrics are
> outliers together" rule. With heart rate, steps and possibly sleep there is realistically **one**
> physiological channel. So concordance here means **multi-night persistence plus cross-channel
> corroboration where available**, and the weight sits on persistence. This is a genuine weakening
> against the original design, it is recorded in `04-decisions.md` B-6, and it must be stated as a
> limitation rather than glossed. It also strengthens the case for asking: fewer causes are
> separable from sensors alone.

---

## 5. The mandatory baselines

Two comparators are implemented **here**, in the same module, so the evaluation cannot quietly skip
them.

```python
def detect_random(alert_rate: float, n_days: int, rng) -> list[bool]:
    """Alerts uniformly at random, matched to the real detector's alert rate."""

def detect_trivial(nights, all_time_median: float) -> list[bool]:
    """Alert whenever rhr exceeds the all-time median by DETECT_RED_BPM.
    No window, no shrinkage, no explained variance, no persistence."""
```

The first answers "could this recall have been achieved by alerting at this rate at random times",
which is the reviewer's real question and which a widely cited critique showed defeats many
published anomaly detectors. The second is the triviality check: **if the sophisticated method does
not beat five lines of code, that is the finding**, and reporting it honestly is worth more than
hiding it.

Both appear in every detection result. There is no configuration that omits them.

---

## 6. Idempotency

```python
def detect_night(subject_id: str, night_date: date) -> Detection: ...
def detect_range(subject_id: str, start: date, end: date) -> list[Detection]: ...
```

`INSERT OR REPLACE`. Recomputation after late-arriving data must produce an identical row.

Persistence needs the preceding `DETECT_PERSISTENCE_NIGHTS - 1` nights, so `detect_night` reads
backwards and never forwards. **The detector never sees the future**, which is what makes the
offline evaluation an honest simulation of online behaviour.

---

## 7. Edge cases

| Case | Behaviour |
|---|---|
| Night not usable | `level = NA`, `flagged = False`, `deviation_bpm = None`. Run broken |
| Gap inside a run | Run broken. Two separate events, not one long one |
| `scale_bpm` at the floor | `robust_z` is large but the **level is unaffected**, because level is bpm-based. Deliberate |
| Residual negative | `GREEN`. Below baseline is not interesting for this target condition |
| Explained exceeds deviation | `residual_bpm` is negative, `GREEN`. Do not clamp to zero; the negative value is informative in the trace |
| Rung is `COLD` | Detection still computes and stores. **The gate on acting is in the policy, not here.** Recording what the detector would have said at low `n` is exactly what the baseline-age curve needs |
| Two exercise sessions | Component 03 already picked the latest-ending one |
| First ever night | `n = 0`, baseline is the population prior, detection runs, almost certainly `GREEN` |

---

## 8. Tests

`tests/unit/detect/test_detection.py`

| Test | Asserts |
|---|---|
| `test_level_thresholds_exact` | 2.99 GREEN, 3.0 YELLOW, 3.99 YELLOW, 4.0 RED |
| `test_level_uses_residual_not_deviation` | 5 bpm deviation with 4.14 explained is GREEN |
| `test_exercise_subtraction_by_bucket` | Each of the three buckets subtracts its exact constant |
| `test_exercise_beyond_lookback_subtracts_nothing` | |
| `test_short_sleep_is_never_subtracted` | 4 hours of sleep changes `explained_bpm` by zero |
| `test_reasons_recorded_for_every_subtraction` | The string names the effect and its source |
| `test_single_red_night_does_not_flag` | Persistence requires a run |
| `test_two_consecutive_with_one_red_flags` | YELLOW then RED flags on the second night |
| `test_two_yellows_without_red_does_not_flag` | At least one RED is required |
| `test_unusable_night_breaks_the_run` | RED, NA, RED does not flag |
| `test_flag_fires_on_the_night_the_run_completes` | Not retroactively on the first night |
| `test_detector_never_reads_future_nights` | Computing night N with N+1 present gives the same result as without |
| `test_negative_residual_is_green_not_clamped` | The stored value stays negative |
| `test_cold_rung_still_computes_detection` | Storage happens; gating is elsewhere |
| `test_random_baseline_matches_alert_rate` | Over 1000 runs, mean rate is within tolerance |
| `test_trivial_baseline_is_implemented` | Runs and returns alerts on a fixture |
| `test_recompute_is_idempotent` | |

---

## 9. Exit condition

```bash
uv run pytest tests/unit/detect -q
uv run wha nightly --subject demo-illness-onset --range 2026-08-03:2026-09-01
```

The second prints a night-by-night table with level and reasons, and flags exactly the night the
scenario fixture expects.
