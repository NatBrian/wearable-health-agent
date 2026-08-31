# Component 08. The policy

**Phase:** A. **Module:** `src/wha/policy/`. **Depends on:** 07 belief,
`data/knowledge/probes.yaml`.

Decides the action. **This is the project's contribution and the one thing the LLM never touches.**

---

## 1. What it decides

Given a belief state, a budget and a rung, return exactly one `Action`:

```
OBSERVE   stay silent, wait for another night
ASK       a specific Probe is worth an interruption
MEASURE   a reading is worth requesting
ESCALATE  the belief itself warrants care guidance
CONCLUDE  no further evidence would change the outcome
```

The LLM is not consulted, does not see this code path, and cannot influence it. What it may do is
**veto**: having read the case, it can cancel an authorised `ASK` if it can see the question is
redundant. It can never authorise one the policy declined. Same asymmetry as the red-flag rule: the
model can make the system quieter, never louder.

---

## 2. The decision that matters

Everything reduces to one binary: does the system tell you this might be illness needing action?

```
                       infection present   infection absent
conclude illness           0.0                  -1.0        UTILITY_FALSE_ALARM
conclude benign           -9.0                   0.0        UTILITY_MISS_ILLNESS
```

```python
EU_illness = -(1 - p)          # p is BeliefState.p_illness
EU_benign  = -9 * p
EU_now     = max(EU_illness, EU_benign)
```

**The testing threshold is derived, not asserted.** Indifference sits where `-(1-p) = -9p`, that is
`p = 1/10 = 0.10`, which coincides with the Pauker and Kassirer testing threshold. It is a
consequence of the stated utilities rather than a number chosen to match a paper, and the ratio is
swept in the evaluation.

The 9 to 1 asymmetry is the one value judgement in the file, and it should be argued with: missing an
illness is worse than one unnecessary "consider seeing someone", but not infinitely worse, because a
system that always escalates is the alarm-fatigue failure this project exists to fix.

---

## 3. Expected value of sample information

```python
def evsi(belief: BeliefState, probe: Probe) -> float:
    """Utility gained by asking, before subtracting the cost of asking."""
```

```
for each answer a in probe.answer_space:
    P(a)        = p * L[a | target present] + (1 - p) * L[a | target absent]
    p_after(a)  = p * L[a | present] / P(a)
    EU_after(a) = max( -(1 - p_after(a)),  -9 * p_after(a) )

EVSI = sum_a P(a) * EU_after(a)  -  EU_now
```

**EVSI is never negative**, because you can always ignore the answer. It is **exactly zero when no
answer could change the decision**, which is the property that separates it from entropy-based
information gain and the reason `research/findings/F8` names it the gold standard while flagging
plain information gain as a real modelling compromise.

Two consequences worth stating in the write-up:

- Below `p = 0.10` the system would conclude benign whatever the answer, so **EVSI is zero and it
  stays silent by arithmetic, not by a rule.**
- Far above it the system would conclude illness whatever the answer, so **EVSI is zero again.** The
  quiet band at both ends emerges rather than being imposed. There is no upper threshold constant
  and one must not be reintroduced.

```python
score(probe) = evsi(belief, probe) - probe.interruption_cost * POLICY_COST_PER_INTERRUPT
```

Ask iff `max score > 0`, the budget allows, and the rung allows.

---

## 4. `probes.yaml`

Read-only, authored, roughly nine rows. **No question text**, except one plain fallback used when
the model is unavailable.

```yaml
- probe_id: probe_alcohol
  target_cause: alcohol
  interruption_cost: 1.0
  fallback_text: "Did you have any alcohol last night?"
  answer_space:
    - {option_id: none,  label: "None"}
    - {option_id: one2,  label: "1 to 2"}
    - {option_id: three, label: "3 to 4"}
    - {option_id: five,  label: "5 or more"}
  likelihood:
    present: {none: 0.10, one2: 0.40, three: 0.35, five: 0.15}
    absent:  {none: 0.92, one2: 0.06, three: 0.01, five: 0.01}
  provenance: ASSUMED
  assumption: >
    No published measurement exists of how accurately a person reports drinking to an
    app when prompted the next morning. Set conservatively: the `present` row is
    deliberately flatter than self-report validity studies suggest, which UNDERSTATES
    the value of asking. Over-stating it would make the system interrupt more, which
    is the failure this project exists to fix. Swept in the sensitivity analysis.
```

**Two likelihood rows, not twelve.** A probe about drinking depends on whether the person drank, not
on whether they also happen to be stressed. That is the parameter reduction the binary belief model
bought, and it removes precisely the rows that would otherwise be fabricated.

`interruption_cost` is relative, not absolute. A one-off setup question such as cycle status or
regular medication is cheaper than a recurring one, because it is asked once and then becomes a
modelled covariate.

Validation at load: every `target_cause` is a real `CauseId`, every likelihood row sums to 1, every
`option_id` is at most 8 characters so `callback_data` fits in 64 bytes, and every `ASSUMED` row
carries an `assumption` string and appears in the sweep config. **A malformed file raises
`ConfigError` at startup.**

---

## 5. Gates, in order

Checked before any EVSI is computed, because they are cheaper and they are hard limits.

| Gate | Rule | On failure |
|---|---|---|
| **Rung** | `COLD` never opens an episode. `PRIOR_DOMINATED` may not `ASK` | `OBSERVE`, reason recorded |
| **Interruption budget** | `INTERRUPTION_BUDGET_PER_WEEK` per rolling seven local days | `OBSERVE`, `BudgetExhausted` recorded, not raised to the user |
| **Depth budget** | `DEPTH_BUDGET_PER_EPISODE` questions per episode | No further `ASK`; the episode proceeds to conclude |
| **One pending interaction** | At most one `AWAITING_USER` per subject | `OBSERVE` until it resolves or times out |
| **Episode caps** | `EPISODE_MAX_NIGHTS`, `EPISODE_MAX_STEPS`, `MAX_TOOL_CALLS_PER_EPISODE` | `CONCLUDE` as `UNRESOLVED`, `safety_event` recorded |

**Declining consumes budget.** Tapping "Not now" means the interruption was spent, so the week's
count decrements. Anything else would let a declined question be re-asked indefinitely.

---

## 6. Action selection

```python
def select_action(belief, probes, budget, rung, episode) -> Action:
```

In order, first match wins:

1. **Caps exceeded** → `CONCLUDE(UNRESOLVED)`.
2. **Gates block asking** → skip to step 5.
3. **Best probe scores above zero** → `ASK(best)`. Ties break on lower `interruption_cost`, then on
   `probe_id` alphabetically, so the choice is deterministic and replayable.
4. **A measurement scores above zero** at its own lower cost → `MEASURE`.
5. **Another night would plausibly change the decision**, meaning the belief is inside the band and
   the episode is within `EPISODE_MAX_NIGHTS` → `OBSERVE`.
6. **Otherwise** → `CONCLUDE`, with the disposition chosen from the belief:

| Condition | Disposition |
|---|---|
| Rung is `COLD`, or too few usable nights | `INSUFFICIENT_DATA` |
| A non-illness cause dominates and explains the residual | `EXPLAINED_BY_EVENT` |
| `p_illness` above the derived threshold, with symptom evidence | `LIKELY_ILLNESS` |
| `p_illness` below the threshold | `LIKELY_BENIGN` |
| Budgets or caps exhausted while still inside the band | `UNRESOLVED` |

**Every `Action` records `rationale` and `rejected`**: every probe considered with its score. That
list is what the episode trace renders, and it is the difference between a system that decided and a
system that merely acted.

---

## 7. The baselines

Implemented **here**, in the same module, so the evaluation cannot skip them.

```python
def policy_never_ask(belief, ...) -> Action     # always OBSERVE or CONCLUDE
def policy_always_ask(belief, ...) -> Action    # ask the highest-EVSI probe whenever any exists
def policy_threshold(belief, ...) -> Action     # ask iff p_illness in [0.10, 0.75], ignore EVSI
def policy_random(belief, ...) -> Action        # ask at the same rate as the real policy, at random
```

`policy_threshold` is the sharpest test and the one most likely to be uncomfortable: **does the EVSI
term add anything over a simple probability band?** If it does not, the elaborate machinery has not
earned its place, and the honest move is to report that and simplify. That result would arrive in
Phase A, before anything depends on it.

All four share the same interface and are swapped by config, so the benchmark is one loop.

---

## 8. Edge cases

| Case | Behaviour |
|---|---|
| `p_illness` exactly 0.10 | `EU_illness == EU_benign`. Ties go to `conclude_illness`, the safer side. Asserted |
| Every probe scores below zero | `OBSERVE` or `CONCLUDE`. **This is the common case and the design working**, not a stuck state |
| Two probes tie exactly | Deterministic tie-break, so replay is exact |
| Budget resets mid-episode | Recomputed per call from `budgets`. An episode spanning a week boundary may ask again |
| An answer arrives after the episode closed | Ignored, logged |
| The belief barely moves after an answer | Fine. EVSI was an expectation, not a promise. **Do not re-ask the same probe**; a probe already answered is excluded |
| The LLM vetoes an authorised ASK | `OBSERVE`, budget **not** consumed, veto and its reason recorded. Reported as a count |

---

## 9. Tests

`tests/unit/policy/`

| Test | Asserts |
|---|---|
| `test_threshold_derived_from_utilities` | Indifference at exactly `p = 0.10` |
| `test_evsi_never_negative` | Over 1000 random beliefs and probes |
| `test_evsi_zero_when_decision_cannot_change` | At `p = 0.01` and at `p = 0.95`, EVSI is 0 for every probe |
| `test_quiet_band_emerges_without_a_constant` | No upper threshold exists in the code, yet high `p` stops asking |
| `test_asks_inside_the_band` | At `p = 0.30` with an informative probe, the action is `ASK` |
| `test_answered_probe_not_reasked` | |
| `test_budget_blocks_ask` | With the week's budget spent, `OBSERVE` and a recorded reason |
| `test_decline_consumes_budget` | |
| `test_cold_rung_never_asks` | |
| `test_prior_dominated_rung_never_asks` | |
| `test_depth_budget_ends_interview` | The sixth question does not happen |
| `test_tie_break_is_deterministic` | Two identical-scoring probes give the same choice across runs |
| `test_rejected_probes_recorded_with_scores` | Every considered probe appears in `Action.rejected` |
| `test_llm_veto_does_not_consume_budget` | And is recorded |
| `test_llm_cannot_authorise` | A veto in the other direction is rejected by the interface |
| `test_caps_produce_unresolved` | Exceeding `EPISODE_MAX_NIGHTS` closes as `UNRESOLVED` with a `safety_event` |
| `test_probes_yaml_validates` | Likelihood rows summing to 0.9, an unknown cause, or a 12-character option id all raise |
| `test_option_ids_fit_callback_data` | Every probe, every option, under 64 bytes |
| `test_four_baselines_share_the_interface` | All are callable and return an `Action` |
| `test_always_ask_asks_more_than_policy` | On the same fixture sequence, a sanity check that the comparison is real |

`test_evsi_zero_when_decision_cannot_change` and `test_quiet_band_emerges_without_a_constant` are the
two that prove the switch from information gain to EVSI actually happened, rather than being renamed.

---

## 10. Exit condition

```bash
uv run pytest tests/unit/policy -q
uv run wha eval policy --dataset pmdata --dry-run
```

The second runs the policy against the cohort with hidden self-reports as the oracle and prints the
accuracy-versus-interruption frontier for all four policies. **That output is the project's headline
result**, and it exists before any agent, retrieval or interface code is written.
