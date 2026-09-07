# data/knowledge

This directory is the project's intellectual core. It is what the novelty claim rests on, and it is
the one place where a fabricated number would be invisible and consequential.

A language model asked to produce hundreds of cited conditional probabilities will produce hundreds
of plausible fabrications. This repository already contains a documented case: an earlier generation
of the research was found under audit to carry performance figures that were fabricated or badly
distorted.

So do not trust this directory at the level of the file. Trust it at the level of the
number. Every figure carries its own `provenance`, which is either a citation you can open
and check or an `ASSUMED` label meaning no published value exists for it. Those are the
only two things a reader should rely on, and `docs/DISCLOSURES.md` lists where each
`ASSUMED` figure is disclosed on screen.

---

## Files

| File | Contents | Status |
|---|---|---|
| `causes.yaml` | Twelve causes: base rate, effect size, temporal profile | Generated, then verified |
| `probes.yaml` | **Eight** probes: answer space and likelihood, two rows each | Generated, every likelihood ASSUMED |
| `red_flags.yaml` | Three tiers plus vitals. The deterministic safety floor | Generated, then verified |
| `triage_rules.yaml` | The Marburg Heart Score, transcribed item by item | Transcribed from the paper |
| `sources.yaml` | The complete allow-list of endpoints and corpus sources | Generated |
| `corpus.yaml` | Which documents are in the retrieval corpus | Built by `wha corpus build` |

`probe_cycle` was retired on 5 September 2026, taking the probe bank from nine to eight: the fact
it asked for is a standing one about a person and now lives in the Settings profile, so spending
part of a weekly interruption allowance on it was the wrong trade.

`cohort_labels.yaml` was listed here as pending and **it was never needed**. The labels are in the
Mishra et al. 2020 supplementary workbook on the same date shift as the public files, and
`experiments/detection/cohort/labels.py` extracts them into `data/cohort/labels.json`.

---

## Provenance, on every number

| Label | Meaning | Requirement |
|---|---|---|
| `CITED` | A published number | Full citation, and the study's n |
| `DERIVED` | Computed from published numbers | The derivation is written out in the row |
| `ASSUMED` | **No published value exists** | States the assumption and the direction it is conservative in. Begins with the words NO EVIDENCE FOUND |

**The `ASSUMED` category is unavoidable and must not be disguised.** The research corpus is explicit
that answer-reliability, meaning how accurately a person reports drinking or stress to an app, is
"essentially unmeasured", and that the medical test-selection literature "transfers the mathematics
cleanly and the measurement discipline not at all".

Better training data does not fix this. The measurement does not exist.

**A sensitivity sweep is NOT a requirement, and this table used to say it was.** Fourteen figures
carried a "Swept." annotation for an analysis that does not exist anywhere in this repository, and
both the annotations and the requirement are gone. `tests/unit/policy/test_probes.py` has a test
named `test_assumed_rows_appear_in_sweep_config` which checks no sweep config; it checks each
likelihood dict has two entries. Do not read the name as evidence a sweep exists.

**Every assumed value is set conservatively**, meaning it under-states how informative a question is.
Over-stating it would make the system interrupt more, which is the failure this project exists to
fix.

---

## What the operator should actually review

Not everything. Most rows quote studies with thousands to tens of thousands of participants and do
not need a second opinion.

**In `causes.yaml`**, six fields:

| Cause | Field | Why |
|---|---|---|
| `sleep_restriction` | effect mean and sd | `ASSUMED`. No reliable bpm effect published |
| `travel` | effect mean and sd | `ASSUMED`. The cited paper reports no heart-rate result at all |
| `unexplained` | effect sd | `ASSUMED` by construction, a leak term |
| `exertion` | base rate | `DERIVED` and genuinely uncertain |
| `stress` | base rate and effect mean | `DERIVED` by inverting an odds ratio, not a reported mean |
| `infection` | effect mean | `DERIVED`, and re-verified in September 2026 because the original note flagged it as read from a search summary |

**In `probes.yaml`**, all nine likelihood tables, roughly thirty numbers. Every one is `ASSUMED`.

**In `red_flags.yaml`**, the tier-A list, the two vitals thresholds, and the tier-B persistence
windows. This is the only place in the project where a wrong number has a real-world consequence
rather than a metric consequence.

That is about five minutes of reading, and it is the five minutes worth spending.

---

## Traps

**YAML parses bare `no`, `yes`, `on` and `off` as booleans.** An `option_id` of `no` becomes `False`
and the slot silently breaks while still passing YAML validation. Quote anything that could read as
a boolean. The loader asserts every `option_id` is a string for exactly this reason.

**Every likelihood row must sum to 1 and must cover exactly the probe's answer slots.** The loader
checks both and raises `ConfigError` at startup rather than at first use.

**Option ids are at most 8 characters** so that `callback_data` fits inside Telegram's 64-byte limit.
Current maximum in use is 18 bytes.

---

## Changing anything here

A change to any of these files is a **behaviour change**. It re-runs the full regression suite and it
invalidates any evaluation result computed under the old values. The `EvaluationResult` records which
constants were in force, so a stale result is detectable rather than silently misleading.
