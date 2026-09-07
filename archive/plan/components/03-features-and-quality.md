# Component 03. Nightly features and the quality gate

**Phase:** A. **Module:** `src/wha/features/`. **Depends on:** 01 ingestion, 02 storage.

Turns raw samples into one `NightlyFeatures` row per night, and decides whether that night is
usable at all. **The refusal path is the point of this component**, not an afterthought.

---

## 1. Responsibilities

1. Resolve the nocturnal window in the subject's local time.
2. Derive `rhr_bpm`.
3. Count coverage and implausible values.
4. Decide `usable`.
5. Attach the covariates the belief model needs: previous-day steps, sleep hours, exercise offset.

It computes **no baseline and no deviation**. Those are component 04 and 05.

---

## 2. The nocturnal window

Defined in `docs/CONTRACTS.md` section 3 and repeated here because everything hinges on it.

`night_date` is the local calendar date on which the sleep period **ends**. The window is local
**00:00 to 07:00** on that date.

```python
def nocturnal_window(night_date: date, tz: str) -> tuple[datetime, datetime]:
    """Return the UTC instants bounding local 00:00-07:00 on night_date."""
```

Use `zoneinfo.ZoneInfo`, never a fixed offset. The subject's zone is on the `subjects` row. A fixed
`+08:00` would be wrong the moment anyone travels, and travel is one of the twelve causes.

**Why a fixed clock window rather than the detected sleep period:** it needs no sleep-stage data,
which may never arrive, and it is the definition used by the published detector this design follows.
Sleep hours are recorded as a covariate when available, but the window never depends on them.

---

## 3. Deriving `rhr_bpm`

```python
def nocturnal_rhr(samples: Sequence[HeartRateSample]) -> float | None:
    """Median of per-minute `avg` inside the window, after dropping implausible values."""
```

- **Median, not mean.** A single motion artefact moves a mean by several bpm, and the whole detector
  works on a 3 to 4 bpm threshold. The median is unaffected by a handful of outliers.
- Only the `avg` field. `min` and `max` are stored but unused; they describe within-minute spread,
  not resting level.
- Samples outside `[HR_PLAUSIBLE_MIN_BPM, HR_PLAUSIBLE_MAX_BPM]` are dropped here and counted in
  `implausible_dropped`.
- Returns `None` when no plausible sample remains. `None` is a refusal, not a zero.

> The published Mishra method masks heart rate to windows with zero rolling steps. **Steps arrive as
> daily buckets, so that is impossible.** The nocturnal window achieves the same purpose. Do not
> attempt to reconstruct per-minute steps.

---

## 4. Coverage and usability

```python
coverage_minutes = number of DISTINCT minutes in the window with at least one plausible sample
```

Distinct minutes, not sample count. Two samples in the same minute are one minute of coverage.
Maximum is 420.

```python
usable = coverage_minutes >= MIN_NOCTURNAL_MINUTES and rhr_bpm is not None
```

**Only usable nights count toward the baseline ladder.** A night with 90 minutes of coverage is not
a weak observation to be down-weighted; it is not an observation.

### The refusal path

An unusable night produces a `NightlyFeatures` row with `usable = False` and a `Detection` row with
`level = NA` and `flagged = False`. It does **not** produce a deviation, does not advance the
baseline, and does not open or extend an episode.

> **Never impute across a coverage gap.** The published guidance is explicit that imputing missing
> wearable epochs is fine for weekly summaries and catastrophic for anomaly detection, because it
> manufactures normality exactly where there is no evidence. There is no interpolation anywhere in
> this component, and the night chart draws gaps rather than lines.

**Wear time is itself a signal.** Reduced wear correlates with feeling unwell, and it is also a
confounder such as a forgotten charge. Coverage is therefore stored, surfaced on the night table,
and available to the belief model as evidence for `sensor_artifact`. It is never silently repaired.

---

## 5. Covariates

| Field | Definition | Missing when |
|---|---|---|
| `steps_prev_day` | Count from the step bucket whose local day is `night_date - 1` | No bucket covers that day |
| `sleep_hours` | Total of non-`AWAKE` sleep stages overlapping the window | Sleep stages never arrive |
| `exercise_end_offset_h` | Hours between the end of the **latest** exercise session and the window start, if within `EXERCISE_LOOKBACK_HOURS` | No session, or ended too long before |

All three are `float | None`. **`None` means unknown and must never be coerced to zero.** Zero steps
and unknown steps are different facts and the belief model treats them differently.

Where several exercise sessions qualify, take the **latest ending**, since the published effect grid
is keyed on time-to-sleep and the nearest session dominates.

---

## 6. Idempotency

```python
def compute_night(subject_id: str, night_date: date) -> NightlyFeatures: ...
def compute_range(subject_id: str, start: date, end: date) -> list[NightlyFeatures]: ...
```

Recomputing a night must produce an identical row and replace the old one. `INSERT OR REPLACE`. The
nightly batch is safe to run twice, and the backfill path recomputes history when new data arrives
late, which it routinely does.

`computed_at_utc` records when, which is how a stale row is detected after a knowledge-table change.

---

## 7. Edge cases

| Case | Behaviour |
|---|---|
| Zero samples in the window | `rhr_bpm=None`, `coverage=0`, `usable=False`. Not an error |
| All samples implausible | Same, with `implausible_dropped` set. The count is what makes this diagnosable |
| Window crosses a DST transition | `ZoneInfo` handles it. The window may be 6 or 8 hours; coverage is counted against actual minutes, not 420 |
| Subject travels, zone unchanged in settings | Window is wrong for those nights. **Accepted and documented**: `travel` is a modelled cause and the interview resolves it. Do not attempt automatic zone detection |
| Sample timestamped in the future | Outside the window. Excluded |
| Two step buckets overlap `night_date - 1` | Take the bucket with the greater overlap. Log once |
| Sleep session spans midnight | Count only the portion inside the window |
| Exercise session with no end time | Ignore for the offset. Do not guess a duration |

---

## 8. Tests

`tests/unit/features/`

| Test | Asserts |
|---|---|
| `test_window_uses_subject_timezone` | Asia/Singapore gives 16:00Z to 23:00Z |
| `test_window_handles_dst_transition` | A zone with DST yields the correct UTC bounds, not a 7-hour assumption |
| `test_rhr_is_median_not_mean` | One 180 bpm artefact among 300 samples moves the result by under 0.5 bpm |
| `test_implausible_values_dropped_and_counted` | A 300 bpm sample is excluded and `implausible_dropped == 1` |
| `test_coverage_counts_distinct_minutes` | Three samples in one minute give coverage 1 |
| `test_below_min_coverage_is_not_usable` | At `MIN_NOCTURNAL_MINUTES - 1`, `usable is False` |
| `test_at_min_coverage_is_usable` | The boundary is inclusive |
| `test_no_samples_returns_none_not_zero` | `rhr_bpm is None` |
| `test_gap_is_not_interpolated` | A 3-hour gap does not produce values inside it |
| `test_missing_covariate_is_none_not_zero` | `steps_prev_day is None` when no bucket exists |
| `test_latest_exercise_session_wins` | Two sessions, the later-ending one sets the offset |
| `test_exercise_beyond_lookback_is_ignored` | Ending 7 hours before the window gives `None` |
| `test_recompute_is_idempotent` | Twice gives one row with identical values |
| `test_sleep_spanning_midnight_counts_only_window_portion` | |

---

## 9. Exit condition

```bash
uv run pytest tests/unit/features -q
uv run wha nightly --subject demo-illness-onset --date 2026-09-01
```

The second writes exactly one `nightly_features` row and prints it.
