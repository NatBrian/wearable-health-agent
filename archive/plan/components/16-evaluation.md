# Component 16. Evaluation

**Phase:** A. **Module:** `src/wha/eval/`. **Depends on:** 01 ingestion, 04 baseline,
05 detection, 06 forecast, 07 belief, 08 policy.

**Built in Phase A, not last.** The policy benchmark is the project's headline result and it needs
no LLM, no agent graph, no retrieval and no interface. Finishing it before anything else exists is
what stops it being sacrificed at the end, which is what happens to evaluation in practice.

---

## 1. Suites

```bash
uv run wha eval detection     # cohort detection metrics plus the two mandatory baselines
uv run wha eval baseline-age  # THE unpublished result
uv run wha eval policy        # four policies against a real-self-report oracle
uv run wha eval ablation      # what each component is worth
uv run wha eval adversarial   # Phase B. Injection containment
```

Each writes an `EvaluationResult` to `data/eval/<suite>.json` plus figures. The interface renders
stored results and **never computes on page load**.

---

## 2. Detection

On the illness-labelled cohort. Labels come from `data/knowledge/cohort_labels.yaml`, **not from the
archive**, which contains none.

**Definitions, stated so they cannot drift:**

- **Decision epoch** is one day.
- **Alert event** is a maximal run of consecutive alerting days, minimum run length
  `DETECT_PERSISTENCE_NIGHTS`. Report at run lengths 1, 2 and 3.
- **Detection window** is `[onset - 7 days, onset + 1 day]`. Sensitivity analysis at
  `L_max` in `{3, 5, 7, 10, 14}`.
- **Detected** means at least one alert event has its **first** day inside the window. Using the
  first day is what makes lead time well defined.
- **Lead time** is `onset - first_alert`, positive meaning early.
- **False alert event** is one whose first day falls in no episode's window.

**Report all seven:**

1. Episode-level recall with a **Clopper-Pearson exact 95% interval**. The count is small and a
   normal approximation is wrong.
2. Lead-time **distribution**: median, IQR, min, max, and the full per-episode list in an appendix.
   Conditioned on detection, stated explicitly.
3. False alert rate in **two units**: events per user-week of non-episode time, and fraction of
   person-days alerting. Both, because the literature uses both and this makes the numbers directly
   comparable.
4. **Number needed to evaluate**, `1 / PPV` at event level. The number a non-technical reader
   actually understands.
5. **AUPRC at day level, with the prevalence printed next to it**, because AUPRC's no-skill baseline
   *is* the prevalence and a number without it is meaningless.
6. **Precision at k%**, with the random baseline and an oracle on the same axes.
7. The raw contingency counts, per episode, with lead time.

### What is never reported

| Never | Why | Instead |
|---|---|---|
| **Point-adjusted F1** | A *random* score reaches 0.969 on a standard benchmark under point adjustment | Episode recall plus false alerts per user-week |
| Point-wise accuracy | At 0.1% prevalence, "always healthy" scores 99.9% | AUPRC with prevalence |
| Point-wise F1 at one tuned threshold | Threshold shopping | AUPRC plus one clearly labelled operating point |
| A best-of-N seed result | Some metrics reach 0.98 by N=41 | Single run, N disclosed |
| A calibration curve on 30 events | Needs roughly 200 per class | Observed-to-expected ratio only, with a statement that finer calibration is not estimable |

### The two mandatory baselines

Both from component 05, and there is no configuration that omits them.

1. **Random detector matched on alert rate**, 1000 draws, report the recall distribution.
2. **Trivial detector**: alert whenever resting heart rate exceeds the all-time median by
   `DETECT_RED_BPM`. No window, no shrinkage, no explained variance, no persistence.

**If the real detector does not beat the trivial one, that is the finding.** Reporting it is worth
more than hiding it.

---

## 3. Baseline age: the unpublished result

For each participant, truncate history to `N` usable nights and recompute detection, for
`N` in `{3, 5, 7, 10, 14, 21, 28}`, under two estimators:

1. the shrinkage baseline from component 04
2. the Chronos forecast from component 06

Plot recall and false alerts per user-week against `N`, two lines each.

**The question: does a foundation model extend usable detection to earlier nights than statistics
can?** Nobody has published this curve. It runs offline on the cohort and costs one extra line on a
plot the detection suite already produces.

Two possible headlines, both worth having:

- Chronos is usable at `N = 5` where the shrinkage baseline is not. A real, novel, useful result.
- The two are indistinguishable. **Then the honest headline is that a 47M-parameter foundation model
  bought nothing over a rolling median, and the page says so.**

The truncation must reuse the real code path, `compute_baseline_truncated`, not a reimplementation,
or the result measures the reimplementation.

---

## 4. Policy: the headline

On the confounder-annotated cohort, whose daily self-reports of alcohol, training load, stress and
sleep quality are the **oracle**.

**The construction**, which is the strongest evaluation idea available to this project:

1. Take real, healthy, confounder-annotated wearable data. Background noise, missingness, diurnal
   structure and confounders are all authentic.
2. Inject a physiologically calibrated illness signature: **+4 bpm sustained over 4 days**, taken
   from the deployed detector's own thresholds and cluster duration. The event is synthetic so the
   ground truth is exact.
3. **Hide the self-reports. Reveal one only when the policy asks for it.**
4. Score each policy on: illness episodes correctly identified, false conclusions, **interruptions
   spent**, and accuracy gained per interruption.

> This is a **simulated oracle over real human answers**, which is strictly better than inventing
> user responses with a language model, and it is the single most defensible design available for
> the agentic part of this project.

**Sweep the injection.** Amplitude 1 to 8 bpm, duration 1 to 7 days, and report a detection heat map.
That converts "we made up the ground truth" into "we characterised the detection boundary".

**Four policies, same loop:** the EVSI policy, never-ask, always-ask, threshold-only.

**The threshold-only comparison is the uncomfortable one and must be reported prominently.** It asks
whether the EVSI term adds anything over a simple probability band. If it does not, the machinery
has not earned its place, and the honest move is to say so and simplify.

**Sweep the free parameters:** the miss-to-false-alarm utility ratio and
`POLICY_COST_PER_INTERRUPT`. Report the **accuracy-versus-interruption frontier**, not a single
operating point, because no published study fixes a point on it.

**The oracle's limits, stated in the write-up.** A simulated oracle is noiseless and never fatigues,
whereas real people misremember and stop answering. That is a known critique of this protocol and it
is cited rather than discovered by a reviewer.

---

## 5. Ablation

Each with a **paired bootstrap interval over participants**, never over days, because days within a
participant are not independent and bootstrapping them gives fraudulently narrow intervals.

| Removed | Question |
|---|---|
| Explained-variance subtraction | Does subtracting recorded workouts reduce false alerts? |
| Persistence rule | Is multi-night debouncing doing the work? |
| Chronos evidence | Does the forecast contribute anything to the belief? |
| Temporal profiles, flat instead | **Is multi-night reasoning the discriminator we claim?** |
| Shrinkage, fixed 28-night window instead | Does the ladder help or only enable early operation? |
| Asking | never-ask, from the policy suite |

The temporal-profile ablation is the one that tests component 07's central claim. If flat profiles
perform identically, alcohol and infection are not being separated by shape and the write-up must
say so.

---

## 6. Small samples

The cohort yields tens of labelled episodes, not hundreds. The protocol is fixed in advance:

1. **Clopper-Pearson exact intervals** on every proportion. Show the interval next to every
   sensitivity claim.
2. **Cluster bootstrap over participants**, never over days.
3. **Permutation test**: permute onset dates within each participant 10,000 times, preserving the
   alert series, and report the null distribution of recall. This directly answers "could this have
   been achieved by alerting at this rate at random times".
4. **Print the raw counts.** At this sample size, aggregate statistics hide too much.
5. **Say the sentence**, in the report and on the Evaluation page:

> With N positive episodes the 95% confidence interval on sensitivity spans X percentage points.
> This study is powered to establish that the signal exists and to characterise the false-alarm
> rate. **It is not powered to rank detector variants against one another, and no such ranking is
> claimed.**

Never report four-decimal figures. Never sweep and report only the best configuration; report the
whole sweep.

---

## 7. The evidence hierarchy

Printed at the top of the Evaluation page, because the failure that destroys projects is claiming
the bottom row while evidencing the top one.

| Claim | Ground truth | Status |
|---|---|---|
| The physiological anomaly occurred | Real labelled episodes | **Grounded**, exact intervals |
| The alert rate in healthy periods is X | Real unlabelled data | **Grounded**, no labels needed |
| The system detects an illness-shaped perturbation | Semi-synthetic injection into real backgrounds | **Constructed ground truth**, effect size swept |
| The agent asks the right question at the right time | Hidden real self-reports revealed on query | **Simulated oracle over real answers** |
| The agent improves user outcomes | None available | **Not claimed** |

---

## 8. Reproducibility

Every suite: explicit seed, pinned data version, `EvaluationResult` recording the git commit,
`uv.lock` hash, the constants in force, and `sample_size` and `caveats`. Re-running a suite with the
same inputs produces byte-identical numbers.

No suite requires the network or the LLM. Adversarial is Phase B and uses cassettes.

---

## 9. Tests

`tests/unit/eval/` uses small synthetic fixtures with known answers. **The suites themselves run on
datasets and are `skipif`-gated.**

| Test | Asserts |
|---|---|
| `test_alert_event_definition` | Runs of 1, 2 and 3 are counted correctly, and a gap breaks a run |
| `test_detection_window_boundaries` | Onset minus 7 detects, onset minus 8 does not |
| `test_lead_time_uses_first_alert_day` | Not any day in the run |
| `test_clopper_pearson_matches_scipy` | 26 of 32 gives roughly 63.6% to 92.8% |
| `test_cluster_bootstrap_resamples_participants` | Not days. Asserted on the resample indices |
| `test_permutation_test_null_is_centred` | On data with no signal |
| `test_point_adjusted_f1_is_not_computed` | The function does not exist. A grep test, deliberately |
| `test_auprc_reported_with_prevalence` | Both keys present in the result |
| `test_baseline_age_uses_real_code_path` | Calls `compute_baseline_truncated`, not a copy |
| `test_oracle_only_reveals_on_ask` | A never-ask policy sees zero self-reports |
| `test_four_policies_run_on_same_fixture` | Same input, four different interruption counts |
| `test_result_records_provenance` | Commit, lock hash, constants, seed all present |
| `test_caveats_non_empty_when_underpowered` | Below 50 episodes, the caveat string is populated |

---

## 10. Exit condition

```bash
uv run wha data fetch stanford && uv run wha data fetch pmdata
uv run wha eval detection
uv run wha eval baseline-age
uv run wha eval policy
```

Three `EvaluationResult` files with real numbers on real cohort data, and the Phase A gate is met.
**If the policy suite shows the EVSI policy indistinguishable from threshold-only, stop and report
it before Phase B begins.** That is the single most valuable thing this suite can tell us, and it is
cheapest to act on before anything depends on it.
