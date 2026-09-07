# Component 04. Personal baseline and the maturity ladder

**Phase:** A. **Module:** `src/wha/detect/baseline.py`. **Depends on:** 03 features.

Answers "what is normal for this person tonight?" when there may be one night of history. **This is
the component that makes the system usable from day one**, and it is the source of the project's
one unpublished result.

---

## 1. The problem

Every published method needs 7 to 28 nights and refuses until it has them. Oura needs 7 nights in
14, WHOOP 21 days, and the reference implementations use a 28 or 31 day trailing window. **None of
them says what they can tell you in the meantime.**

A new subject has none of that. So the baseline starts from a **population prior** and shrinks
toward the personal estimate as usable nights accrue. Closed-form conjugate updating, nothing
trained, every number citable. `history/PROPOSAL.md` Appendix A already blesses the mechanism; here it is
core rather than a stretch goal.

---

## 2. The estimator

```python
def compute_baseline(history: Sequence[NightlyFeatures]) -> Baseline:
    """Shrinkage estimate of tonight's expected resting heart rate and its spread.

    `history` is the usable nights within the trailing BASELINE_WINDOW_NIGHTS,
    EXCLUDING tonight. Order does not matter.
    """
```

```
n            = len(history)                       # usable nights only
w            = n / (n + SHRINKAGE_PSEUDO_NIGHTS)  # 0 at n=0, 0.5 at n=7, 0.8 at n=28

centre_bpm   = w * median(history.rhr) + (1 - w) * POP_PRIOR_RHR_MEAN_BPM

personal_sd  = MAD_TO_SD_FACTOR * median_abs_deviation(history.rhr)
scale_bpm    = max(w * personal_sd + (1 - w) * POP_PRIOR_RHR_SD_BPM,
                   BASELINE_SCALE_FLOOR_BPM)
```

Four things about this that are deliberate:

**Median and MAD, not mean and standard deviation.** A single illness night inside the window would
drag a mean upward and inflate a standard deviation, raising the bar exactly when it should not.
Robust statistics are the standard choice in this literature for that reason.

**`SHRINKAGE_PSEUDO_NIGHTS = 7.0` means the population prior carries the weight of seven nights.**
At 7 usable nights the personal estimate has equal weight; at 28 it has 80%. That single constant is
the whole ladder, and it is swept in the evaluation.

**The scale floor is not cosmetic.** MAD is **exactly zero** whenever more than half the window
holds identical values, which happens constantly on quantised heart-rate data at small `n`. Without
`BASELINE_SCALE_FLOOR_BPM` the robust z divides by zero and every night becomes an infinite
deviation. This is the single most likely way to get this component silently wrong.

**Tonight is excluded from its own baseline.** Otherwise a large deviation partly explains itself
and the detector loses sensitivity precisely on the nights that matter.

---

## 3. Sick-night exclusion

Nights belonging to a **closed episode** with disposition `LIKELY_ILLNESS` or `ESCALATED` are
excluded from the history window. An illness inside the baseline raises the bar and masks the next
one.

Nights inside an **open** episode are **not** excluded, because the disposition is not known yet and
excluding them pre-judges the outcome. They fall out later on recomputation, which is why
`computed_at_utc` exists.

Nights closed as `EXPLAINED_BY_EVENT`, `LIKELY_BENIGN`, `UNRESOLVED` or `INSUFFICIENT_DATA` stay in.
They are normal life, and removing them would bias the baseline downward.

---

## 4. The ladder

```python
def rung_for(usable_nights: int) -> BaselineRung: ...
```

| Usable nights | Rung | The agent may |
|---|---|---|
| 0 to 2 | `COLD` | Nothing. `INSUFFICIENT_DATA` only. **Never opens an episode** |
| 3 to 6 | `PRIOR_DOMINATED` | Flag only extreme deviations. Disposition capped at `INSUFFICIENT_DATA` or `LIKELY_BENIGN`. **May not ASK** |
| 7 to 13 | `SHRINKING` | Open episodes and ask. Confidence discounted. The outcome states its baseline age |
| 14 to 27 | `PERSONAL` | Full behaviour |
| 28 and above | `MATURE` | Full behaviour, matching the published standard |

**The gating is enforced in code, not by convention.** `policy/` asserts the rung before returning
`ASK`, and the agent graph asserts it before opening an episode. A `COLD` subject that somehow
reaches the policy is an assertion failure, not a warning.

Rationale for the rung boundaries, stated so they can be argued with: `COLD` at three nights is the
minimum for a median to mean anything; `PRIOR_DOMINATED` ends at seven, where `w` reaches 0.5 and
the personal estimate first outweighs the prior; `PERSONAL` begins at fourteen, the shortest window
any published system uses; `MATURE` at twenty-eight matches the reference implementations. **Every
boundary is swept in the evaluation** and reported as a curve, not asserted as correct.

---

## 5. The population prior

```python
POP_PRIOR_RHR_MEAN_BPM = 62.75   # Bloomfield et al. 2024, PLOS Digital Health 3(4):e0000473
POP_PRIOR_RHR_SD_BPM   = 8.64    # n=525 first-year students, Oura, nocturnal RHR
```

Chosen because it is a **nocturnal** resting heart rate from a **wearable** in a **young adult**
cohort, which matches the measurement and the likely user. A clinical daytime resting heart rate
would be the wrong quantity.

**Stated limitation, and it belongs in the write-up:** a single population prior is wrong for
someone whose true resting heart rate is 45 or 85. The shrinkage weight is what limits the damage,
and it is why the ladder caps what the agent may claim at low `n` rather than pretending the
estimate is good. An age-stratified or self-reported prior is named as future work and is not built.

---

## 6. The baseline-age experiment

This component produces the project's one unpublished result, and it is cheap.

For each cohort participant, truncate history to `N` usable nights and recompute detection for every
`N` in `{3, 5, 7, 10, 14, 21, 28}`. Plot episode-level recall and false alerts per user-week against
`N`, for two estimators:

1. the shrinkage baseline in this component
2. the Chronos forecast from component 06

**The question is whether a foundation model extends usable detection to earlier nights than
statistics can.** Nobody has published this curve. It runs entirely offline on the cohort, needs no
LLM, and is one extra line on a plot the evaluation already produces.

Implementation lives in component 16; this component exposes what it needs:

```python
def compute_baseline_truncated(history, max_nights: int) -> Baseline: ...
```

---

## 7. Edge cases

| Case | Behaviour |
|---|---|
| `n = 0` | `w = 0`, baseline is exactly the population prior, rung `COLD` |
| All history identical | MAD is 0, `scale_bpm` becomes the floor. **This is the common case at small `n`, not an edge case** |
| One usable night in the last 28, but 40 nights of unusable ones | `n = 1`. Unusable nights never count |
| History contains an illness episode | Excluded once that episode is closed as illness. Present while open |
| Subject's true baseline drifts, for instance detraining | The 28-night window follows it, slowly. Accepted. `medication` and `recovery_tail` are modelled causes for step changes |
| `usable_nights` exceeds 28 | Window caps at `BASELINE_WINDOW_NIGHTS`. Rung is still `MATURE` |
| Recompute after a night flips from usable to unusable | Baseline changes. Idempotent, and `computed_at_utc` updates |

---

## 8. Tests

`tests/unit/detect/test_baseline.py`

| Test | Asserts |
|---|---|
| `test_zero_nights_returns_population_prior` | `centre == POP_PRIOR_RHR_MEAN_BPM` exactly, `w == 0` |
| `test_shrink_weight_is_half_at_pseudo_nights` | `w == 0.5` at `n == 7` |
| `test_shrink_weight_monotonic` | `w` strictly increases with `n` |
| `test_mad_floor_applies_when_window_is_constant` | 10 identical nights give `scale_bpm == BASELINE_SCALE_FLOOR_BPM`, **not zero, not a division error** |
| `test_median_resists_one_outlier` | One 95 bpm night among 20 at 58 moves `centre` by under 0.5 |
| `test_tonight_excluded_from_own_baseline` | The value for `night_date` never appears in its own history |
| `test_illness_nights_excluded_when_closed` | A closed `LIKELY_ILLNESS` episode's nights are absent from the window |
| `test_open_episode_nights_are_included` | Not pre-judged |
| `test_benign_closed_nights_are_included` | `LIKELY_BENIGN` stays in |
| `test_rung_boundaries_exact` | 2 is `COLD`, 3 is `PRIOR_DOMINATED`, 6 is `PRIOR_DOMINATED`, 7 is `SHRINKING`, 13 is `SHRINKING`, 14 is `PERSONAL`, 27 is `PERSONAL`, 28 is `MATURE` |
| `test_unusable_nights_do_not_count` | 40 unusable plus 1 usable gives `n == 1` and rung `COLD` |
| `test_window_caps_at_28` | 60 nights of history uses 28 |
| `test_truncated_baseline_matches_full_at_same_n` | The evaluation helper agrees with the normal path |
| `test_recompute_is_idempotent` | |

`test_mad_floor_applies_when_window_is_constant` and `test_rung_boundaries_exact` are the two that
matter most. The first prevents a silent division blow-up; the second is what the whole ladder rests
on.

---

## 9. Exit condition

```bash
uv run pytest tests/unit/detect/test_baseline.py -q
```

Green, with every rung boundary asserted exactly.
