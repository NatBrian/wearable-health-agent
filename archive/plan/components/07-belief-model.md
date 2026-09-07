# Component 07. Belief model

**Phase:** A. **Module:** `src/wha/belief/`. **Depends on:** 04 baseline, 05 detection,
`data/knowledge/causes.yaml`.

The reasoning core. Twelve independent binary causes, additive effects, exact inference by
enumeration. **About 80 lines of numpy and no probabilistic-graphical-model library.**

---

## 1. The generative story

State it as physics, because that is what makes the likelihood obvious.

```
Each cause i is present tonight with probability base_rate_i, independently.

A present cause contributes  effect_mean_bpm_i * profile_i[t]  to the residual,
where t is nights since the episode opened, and profile_i is that cause's
published temporal shape.

The observed residual on night t is Normal about the sum of contributions.
```

That is it. Everything else is bookkeeping.

**The temporal profile is what discriminates.** Alcohol contributes on night one and then stops;
infection rises across nights and persists; the luteal plateau lasts about twelve. A single-night
model cannot separate alcohol from early infection at all, which `research/findings/F8` states
outright. **The profile is where multi-night reasoning earns its place**, and every profile comes
from the published onset-latency and duration columns.

---

## 2. Why binary and additive, not one categorical variable

Recorded in `04-decisions.md` D-107. The short form, because it will be questioned:

- **It matches the evidence.** F8's confounder table is a list of additive bpm effects. A "which
  single cause" model cannot use that structure at all.
- **It needs about a quarter of the elicited numbers.** A probe about drinking depends on whether
  the person drank, not on whether they also happen to be stressed. The categorical model needed
  twelve rows per probe where eleven were nuisance entries, and those are the rows a model would
  fabricate most confidently.
- **It is true.** Someone can drink and be stressed on the same night and both contribute.

**Consequence that must not be smoothed over: the marginals do not sum to 1.** They are per-cause
probabilities of contributing. A clinician's differential does not sum to 1 either. Any interface or
prose that presents them as a partition is wrong.

---

## 3. Files

```
src/wha/belief/
  __init__.py     update_belief(), the only public entry point
  causes.py       load causes.yaml, validate, cache
  states.py       the 4096 x 12 presence matrix, built once
  likelihood.py   residual, sensor and answer likelihood factors
  inference.py    enumerate, normalise, marginals
```

---

## 4. Exact inference

```python
PRESENT: np.ndarray  # shape (4096, 12), bool. PRESENT[s, i] is bit i of s. Built once at import.
```

```python
# log prior over states
log_prior = PRESENT @ np.log(p) + (~PRESENT) @ np.log(1 - p)          # (4096,)

# per night t, with profile weights w[t] of shape (12,)
mu  = (PRESENT * (mu_eff * w[t])).sum(axis=1)                          # (4096,)
var = RESIDUAL_OBS_SD_BPM**2 + (PRESENT * (sd_eff * w[t])**2).sum(axis=1)

log_lik_t = -0.5 * (np.log(2*np.pi*var) + (r[t] - mu)**2 / var)        # (4096,)

log_post = log_prior + sum_t log_lik_t + sum(evidence log-factors)
post     = softmax(log_post)                                            # (4096,)

marginals = PRESENT.T @ post                                            # (12,)
p_illness = marginals[CauseId.INFECTION]
```

**Always work in log space and normalise with a max-subtraction softmax.** Products of 4096 Gaussian
densities underflow to zero in float64 within a handful of nights, and the failure is silent: you get
a uniform posterior and never notice.

Cost is a few 4096x12 array operations. Microseconds. There is no approximation anywhere and no
sampling, so results are exactly reproducible, which the frozen scenario suite depends on.

---

## 5. `causes.yaml`

Read-only, authored by a human, twelve rows. Every field carries `provenance` of `CITED`, `DERIVED`
or `ASSUMED`, per `04-decisions.md` D-124.

```yaml
- cause: alcohol
  base_rate: 0.299          # P(present on any night)
  effect_mean_bpm: 2.60
  effect_sd_bpm: 1.10
  profile: [1.0, 0.15, 0.0] # night 1 full, night 2 residual, gone
  evidence_grade: B
  provenance: CITED
  citation: "Grosicki et al. 2026, PLOS Digit Health 5(3):e0001284, n=20,968, 5.1M person-days"
```

**`base_rate` is a plain published base rate.** There is no `P(cause | a flag fired)` conditioning.
The residual likelihood does that work generatively, which removes a step that was easy to get
backwards and would have inflated infection roughly twentyfold.

`profile` is indexed by nights since the episode opened, and the **last value repeats** for anything
beyond its length. So `[1.0, 0.15, 0.0]` means alcohol is gone from night three onward, while a
luteal profile of twelve `1.0` values followed by `0.0` encodes a plateau.

Loading validates: exactly twelve causes, all `CauseId` members present, base rates in `(0, 1)`,
effect standard deviations positive, profiles non-empty and non-negative, every row carrying a
citation or an explicit assumption. **A malformed file raises `ConfigError` at startup**, not at
first use.

---

## 6. Evidence beyond the residual

Each contributes a log-likelihood factor over states. All are optional; a missing input contributes
nothing rather than a default.

| Evidence | Affects | Rule |
|---|---|---|
| **Recorded exercise** | `exertion` | Component 05 already subtracted the recorded effect, so **`exertion` here means unrecorded or under-recorded exertion**: swimming, cycling, lifting, or a device that was off. When a session was recorded and subtracted, the prior on additional unrecorded exertion drops sharply. When none was recorded, it stays at the base rate of untracked activity |
| **Sleep hours** | `sleep_restriction` | Below `SHORT_SLEEP_HOURS` is evidence for. Above is weak evidence against. Absent contributes nothing |
| **Coverage and implausible count** | `sensor_artifact` | Low coverage, many dropped values, or a single-channel step change with no corroboration is evidence for |
| **Prior closed illness episode** | `recovery_tail` | Within the published tail window, the prior rises. **This comes from system state, not from sensors and not from asking** |
| **Cycle phase, if configured** | `luteal` | Sets the prior for that night. If the subject has said it is not applicable, the base rate is 0 and the cause is inert |
| **`forecast_z`** | all, via a second residual observation | Behind `FORECAST_AS_EVIDENCE`. Deliberately wide noise, because it observes the same night and must not double-count |
| **A user answer** | the probe's target cause | `p(answer given target present)` and `p(answer given target absent)` from `probes.yaml`. Two rows, not twelve |
| **A measurement result** | `infection`, `sensor_artifact` | A spot resting reading consistent with the elevated overnight value is evidence against artifact |

---

## 7. Interface

```python
def update_belief(
    episode_nights: Sequence[Detection],          # oldest first, from episode open
    features: Sequence[NightlyFeatures],
    answers: Sequence[Answer],
    measurements: Sequence[MeasurementResult],
    context: EpisodeContext,                      # prior episodes, cycle config, subject settings
) -> BeliefState:
    """Recompute the belief from scratch over the whole episode. Pure and deterministic."""
```

**Recompute from scratch every time.** Do not maintain an incremental posterior. It costs
microseconds, it removes an entire class of ordering bug, and it means a late-arriving night or a
corrected answer produces exactly the right answer with no reconciliation logic.

Every call writes a `beliefs` row with the `trigger` that caused it, so the interface can draw the
distribution evolving and label each step.

---

## 8. Edge cases

| Case | Behaviour |
|---|---|
| One night, no answers | Priors plus a single residual likelihood. Weak, wide, correct |
| Residual near zero | Posterior close to the prior. `p_illness` near its base rate. **Correct, not a bug** |
| Very large residual, 15 bpm | Multi-cause states dominate, and `unexplained` rises because no single published effect is that large. **This is what `unexplained` is for** |
| Two answers about the same cause, contradicting | Both applied. The likelihood handles the conflict; do not deduplicate |
| An answer arrives after the episode closed | Ignored, logged. Closed is closed |
| `luteal` not applicable | Base rate 0. That state's prior is zero and it contributes nothing. **Do not renormalise the other eleven manually**; the arithmetic handles it |
| All twelve base rates near zero | `unexplained` absorbs the mass. Correct |
| A night is unusable | It contributes **no residual likelihood factor** and does not advance the profile index. An absent night is not a night with zero residual |

That last row is the subtle one. Profile index `t` counts **elapsed nights since the episode opened**,
not usable nights, because physiology keeps going during non-wear. But an unusable night supplies no
observation. Both facts are true at once and the implementation must reflect it.

---

## 9. Tests

`tests/unit/belief/`

| Test | Asserts |
|---|---|
| `test_state_matrix_shape_and_content` | `PRESENT` is (4096, 12) and row 5 has bits 0 and 2 set |
| `test_posterior_sums_to_one` | Over states, within 1e-9 |
| `test_marginals_do_not_sum_to_one` | Explicitly. This is a property, not a defect |
| `test_no_evidence_returns_priors` | With no nights and no answers, marginals equal the base rates |
| `test_log_space_no_underflow` | Ten nights of large residuals still gives a non-uniform, finite posterior |
| `test_alcohol_falls_on_second_night` | Two elevated nights drop `alcohol` sharply. **The single most important behavioural test in the project** |
| `test_infection_rises_on_persistence` | The same two nights raise `infection` |
| `test_recorded_exercise_lowers_exertion` | A subtracted workout drops unrecorded exertion |
| `test_unusable_night_contributes_no_likelihood` | Belief identical with the night absent versus present-and-unusable |
| `test_unusable_night_still_advances_profile` | Night three after a gap uses profile index 2, not 1 |
| `test_answer_updates_only_target_cause_materially` | A drinking answer moves `alcohol` far more than `stress` |
| `test_large_residual_raises_unexplained` | 15 bpm with no answers |
| `test_luteal_zero_when_not_applicable` | Marginal is exactly 0 and others are unchanged in ratio |
| `test_recompute_is_deterministic` | Same inputs, bit-identical marginals, twice |
| `test_recompute_order_independent` | Answers supplied in a different order give identical results |
| `test_causes_yaml_validates` | A missing cause, a base rate of 1.1, or a missing citation raises `ConfigError` |
| `test_every_row_has_provenance` | All twelve carry `CITED`, `DERIVED` or `ASSUMED` |
| `test_assumed_rows_appear_in_sweep_config` | Anything `ASSUMED` is listed in the sensitivity sweep |

The last two are guards on `04-decisions.md` D-124, so that the labelling scheme cannot quietly rot.

---

## 10. Exit condition

```bash
uv run pytest tests/unit/belief -q
uv run wha belief explain --subject demo-illness-onset --nights 2026-08-25:2026-09-01
```

The second prints the marginals night by night with the trigger for each update, and shows `alcohol`
collapsing between night one and night two while `infection` rises. That single printout is the
clearest demonstration that the model reasons across nights.
