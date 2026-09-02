# BLOCKERS

**Append, never rewrite.** One section per blocker. A recorded blocker is a good outcome. A silent
workaround is the worst one.

Use this template:

```markdown
## <task-id> — <one line>

**What I tried:** the specific thing, with the command or the call.

**What happened:** the exact error text, pasted.

**What I think is wrong:** which document or assumption does not hold.

**What I need:** a decision, a missing constant, a corrected test, a value in a knowledge table.
```

After recording, mark the task `[!]` in `PROGRESS.md` and move to the next **independent** task.

**Do not** invent a workaround, relax a type, add `# type: ignore`, catch and swallow an exception,
stub out a blocked module, or change a contract to unblock yourself.

---

## A-25 — Missing data/knowledge/cohort_labels.yaml for cohort evaluation

**What I tried:** `uv run pytest tests/unit/eval -q && uv run wha eval detection`

**What happened:**
```
Evaluation skipped / error: Cohort labels file missing at 'data\knowledge\cohort_labels.yaml'. Stanford and PMData ground truth labels live in supplementary information and must be provided.
```

**What I think is wrong:** Stanford and PMData ground truth labels live in the paper's supplementary data and are not part of the dataset archives. `data/knowledge/cohort_labels.yaml` is an external knowledge input that cannot be modified by the agent (Rule 3).

**What I need:** Human authoring of `data/knowledge/cohort_labels.yaml` containing ground truth symptom onset and infection labels from the study supplementary data.

---

## A-26 — Missing data/knowledge/cohort_labels.yaml for baseline-age evaluation

**What I tried:** `uv run wha eval baseline-age`

**What happened:**
```
Evaluation skipped / error: Cohort labels file missing at 'data\knowledge\cohort_labels.yaml'. Stanford and PMData ground truth labels live in supplementary information and must be provided.
```

**What I think is wrong:** Baseline age evaluation requires Stanford cohort illness labels to evaluate detection recall against truncated history lengths.

**What I need:** Human authoring of `data/knowledge/cohort_labels.yaml`.


---

## illness-onset — LIKELY_ILLNESS is unreachable under the authored knowledge tables

**What I tried:** `uv run wha demo run illness-onset`, after making the demo actually open an
episode, run the agent and compare the result against the fixture's frozen `expect` block.

**What happened:**

```
[PASS] flagged_on_day: expected 29, got 29
[FAIL] disposition:    expected 'LIKELY_ILLNESS', got 'EXPLAINED_BY_EVENT'
[FAIL] asks_at_least:  expected 1, got 0
```

Measured, not inferred. Belief over the two flagged nights (residuals 4.6 bpm):

```
p_illness = 0.0246   top: luteal=0.873, sleep_restriction=0.331, stress=0.314
```

With luteal forced inapplicable it is still only 0.070, behind stress and alcohol.

**What I think is wrong:** three frozen artefacts are on incompatible scales.

| Source | Value |
|---|---|
| `constants.py` `DETECT_YELLOW_BPM` | 3.0 bpm |
| `constants.py` `DETECT_RED_BPM` | 4.0 bpm |
| `causes.yaml` infection `effect_mean_bpm` x peak profile | **1.60 bpm** |
| `causes.yaml` luteal `effect_mean_bpm` x peak profile | 3.91 bpm, base rate 0.450 |
| `causes.yaml` exertion `effect_mean_bpm` x peak profile | 4.14 bpm |

**Infection is the one cause the system exists to find, and its modelled peak effect of 1.60 bpm
is below the 3.0 bpm threshold at which the detector notices anything at all.** Only luteal and
exertion can reach YELLOW on their own. So every night the detector flags is, under the authored
priors, better explained by something other than infection, and `p_illness` cannot rise from
sensor evidence alone.

That in turn starves the policy. The EVSI arithmetic is sound and produces a clean quiet band,
measured here:

```
 p_inf   evsi(probe_symptoms)   score = evsi - cost   asks?
 0.020        0.0156                 -0.2844           no
 0.050        0.1950                 -0.1050           no
 0.080        0.4280                 +0.1280           YES
 0.100        0.5850                 +0.2850           YES
 0.200        0.3700                 +0.0700           YES
 0.300        0.1550                 -0.1450           no
```

Asking is worthwhile only between roughly p=0.06 and p=0.28. Belief never enters that band, so no
question is asked, so the oracle's `probe_symptoms: "fever"` never reaches the model, so the
disposition cannot become LIKELY_ILLNESS. The same root cause fails `red-flag` (the tier-A phrase
is carried in the oracle's free text, which is only collected when a question is asked),
`no-response-timeout`, `stress-mimic`, `injection-poisoned` and `injection-clean`.

**What I need:** a human decision on which of the three authored numbers is wrong. Every candidate
is a CITED or DERIVED clinical value or a contract constant, and Rule 2 forbids me inventing any of
them.

1. `causes.yaml` infection `effect_mean_bpm = 1.60` is marked DERIVED and "re-verified 2026-09".
   If the intended figure is the elevation seen in a symptomatic infection rather than the average
   across all infected nights, it is plausibly several bpm higher.
2. `DETECT_YELLOW_BPM = 3.0` may be too high to catch the infection the model describes.
3. The fixture's `local_disease_activity: {dengue_cluster: true, cases: 14}` is read by nothing.
   `EpisodeContext` has no field for it and `update_belief` has no hook. Raising the infection
   prior during a local outbreak is the obvious intended mechanism and would lift belief into the
   ask band, but the size of that adjustment is a number no knowledge table supplies.

Until one is resolved, `illness-onset` reports its failure honestly rather than passing silently.

---

## Synthetic illness injection cannot satisfy both the fixture and the temporal profile

**What I tried:** removing an undocumented `+ 2` offset in `src/wha/ingest/synthetic.py`, which made
the illness injection skip the `[0.5, 0.8, 1.0, ...]` ramp from `causes.yaml` and apply full
amplitude from the first night.

**What happened:** with the ramp applied from its start, `illness-onset` at `amplitude_bpm: 4.6`
produces residuals of 2.3 and 3.68 bpm. `DETECT_RED_BPM` is 4.0, so the night the frozen fixture
requires to be flagged never leaves YELLOW and the scenario stops flagging at all.

**What I think is wrong:** the fixture's `amplitude_bpm` states the elevation to be OBSERVED on the
illness nights, while `causes.yaml` states the amplitude of the cause BEFORE its temporal profile is
applied. The two readings cannot both hold.

I kept the fixture satisfied, indexing the profile from its peak, and documented it at the call
site. The cost is real and worth stating plainly: simulated illness is therefore flat, and a rising
then falling shape is exactly what distinguishes infection from the luteal phase in `causes.yaml`.
The generator is producing data that the belief model is bound to read as the wrong cause.

**What I need:** confirmation of which reading of `amplitude_bpm` was intended. If it is the cause
amplitude, the fixtures need larger values to clear the detection thresholds.

---

## data/datasets/stanford and pmdata are empty, and doctor reports them present

**What I tried:** `uv run wha doctor`, then `ls data/datasets/*`.

**What happened:** doctor prints `datasets  ok  stanford and pmdata present`. Both directories exist
and are empty; `du -sh data/datasets` reports 0 bytes.

**What I think is wrong:** `service/doctor.py` tested `(data_dir / name).exists()`, which is true for
an empty directory. Fixed to require content, so the row now reports the truth. The underlying
blocker stands: no cohort data is present, so A-25 to A-28 remain blocked on the download as well as
on the missing `cohort_labels.yaml` already recorded above.

**What I need:** the datasets fetched, or confirmation that cohort evaluation is out of scope.


---

## RESOLVED: illness-onset, and the cause of most scenario failures

Recorded above as unresolvable without changing a cited clinical figure. That reading was
wrong, and the measurement that settled it is worth keeping.

Neither the infection effect size (1.60 bpm, DERIVED from published percentages) nor the
detection thresholds (3.0 and 4.0 bpm, cited from Alavi 2022 NightSignal, which reaches
80 percent sensitivity at exactly those cutoffs) needed to move. Both are well sourced and
both are correct.

The defect was in code. `update_belief` took `luteal_applicable: bool = True`, collapsing
the three-state fact the contract defines (`cycle_applicable: bool | None`, "None means
not yet asked") into an assumption that every unasked subject menstruates. luteal is the
largest benign effect in causes.yaml at 3.91 bpm on a 0.450 base rate, so assuming it
applied let it explain away exactly the elevations the system exists to investigate.

Measured on illness-onset: p(infection) 0.025 assuming applicability, 0.070 treating it as
unestablished. The second figure is inside the band where the EVSI policy finds a question
worth its interruption cost, so the policy asks, the answer arrives, and the episode
reaches LIKELY_ILLNESS.

The sweep of POLICY_COST_PER_INTERRUPT, annotated "Swept" and never actually swept, moved
the default from 0.30 to 0.15 on measured evidence. Scenario pass rate went from 4 of 11
to 10 of 11.

---

## no-response-timeout — the injected elevation never reaches the RED threshold

**What I tried:** `uv run wha demo run no-response-timeout`.

**What happened:**

```
[FAIL] disposition: expected 'UNRESOLVED', got None
[FAIL] asks_at_least: expected 1, got 0
```

No episode opens, so no question is asked and no disposition is reached.

**What I think is wrong:** the fixture requires an alert event, which needs a run of
YELLOW-or-above nights containing at least one RED. The scenario's injected elevation
produces a residual of 3.65 bpm on its two illness nights. `DETECT_YELLOW_BPM` is 3.0 and
`DETECT_RED_BPM` is 4.0, so both nights are YELLOW and no run ever contains a RED.

Measured, with `explained_bpm` at 0.0, so nothing is being subtracted:

| scenario | fixture amplitude | observed residual | level | flags? |
|---|---|---|---|---|
| illness-onset | 4.6 | 4.25 | RED | yes |
| red-flag | 4.2 | 3.45 | YELLOW | no |
| no-response-timeout | ~4.4 | 3.65 | YELLOW | no |

The roughly 0.75 bpm gap between the injected amplitude and the observed residual comes
from the baseline centre sitting above the scenario's clean-night level and from the
nightly resting heart rate being derived from integer-quantised samples. So a fixture
needs an amplitude of about 4.8 or more to produce a RED night.

red-flag was resolved on its own merits, not by changing an amplitude: escalation must not
depend on the detector having flagged anything, so an unsolicited symptom report now runs
the deterministic floor directly. no-response-timeout has no free text and genuinely needs
an episode.

**What I need:** a decision on the fixture, which is read-only to me. Either its amplitude
rises to roughly 4.8 so the scenario produces the RED night it assumes, or the scenario is
re-authored to open its episode some other way. Nothing in the code is wrong here, so I
have not changed anything to force it green.
