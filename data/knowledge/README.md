# data/knowledge

**READ ONLY. The coding agent loads these files and never edits them.**

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
| `causes.yaml` | Twelve causes: base rate, effect size, temporal profile | Authored |
| `probes.yaml` | Nine probes: answer space and likelihood, two rows each | Authored |
| `red_flags.yaml` | Three tiers plus vitals. The deterministic safety floor | Authored |
| `sources.yaml` | The complete allow-list of endpoints and corpus sources | Authored |
| `corpus.yaml` | Which documents are in the retrieval corpus | Pending |
| `cohort_labels.yaml` | Illness labels for the cohort. **Not in the archive** | Pending, needs the paper's supplementary data |

---

## Provenance, on every number

| Label | Meaning | Requirement |
|---|---|---|
| `CITED` | A published number | Full citation, and the study's n |
| `DERIVED` | Computed from published numbers | The derivation is written out in the row |
| `ASSUMED` | **No published value exists** | States the assumption, the direction it is conservative in, and it must appear in the sensitivity sweep |

**The `ASSUMED` category is unavoidable and must not be disguised.** The research corpus is explicit
that answer-reliability, meaning how accurately a person reports drinking or stress to an app, is
"essentially unmeasured", and that the medical test-selection literature "transfers the mathematics
cleanly and the measurement discipline not at all".

Better training data does not fix this. The measurement does not exist.

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
