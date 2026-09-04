# Phase A. Offline core

**No LLM, no LangGraph, no interface.** Everything here runs offline, deterministically, and is
fully testable without a network, a phone or a model.

**Done when** `uv run wha eval detection`, `uv run wha eval baseline-age` and
`uv run wha eval policy` produce real numbers on real cohort data.

**Why this order.** The policy benchmark is the project's headline result and it needs none of the
agent machinery. Finishing it first means the most valuable finding arrives before anything depends
on it, and it cannot be sacrificed at the end, which is what happens to evaluation in practice.

> **Gate at the end of Phase A.** If the policy suite shows the EVSI policy indistinguishable from
> the threshold-only baseline, **stop and report it before Phase B**. That result would mean the
> elaborate machinery has not earned its place, and it is cheapest to act on before the agent,
> retrieval and interface are built on top of it. See `components/16-evaluation.md` section 4.

---

## Tasks

| ID | Title | Depends on | Component |
|---|---|---|---|
| A-01 | Project skeleton, `pyproject.toml`, `uv lock`, ruff config, `.env.example` | - | - |
| A-02 | `constants.py`, `models.py`, `errors.py` transcribed from the contract | A-01 | 02-contracts |
| A-03 | Database: `schema.sql`, `connect`, `transaction`, `apply_schema` | A-02 | 02 |
| A-04 | Audit hash chain: `append_audit`, `verify_chain` | A-03 | 02 |
| A-05 | `DataSource` protocol, `RawPayload`, pure `normalise()` | A-02 | 01 |
| A-06 | Synthetic generator and the scenario fixture format | A-05 | 01 |
| A-07 | `LiveBridge` client, against a stubbed transport | A-05 | 01 |
| A-08 | `store_raw`, `normalise_and_store` | A-03, A-05 | 01 |
| A-09 | Nocturnal window, `rhr_bpm`, coverage, `usable` | A-08 | 03 |
| A-10 | Covariates: previous-day steps, sleep hours, exercise offset | A-09 | 03 |
| A-11 | Shrinkage baseline and the maturity ladder | A-10 | 04 |
| A-12 | Explained-variance subtraction | A-11 | 05 |
| A-13 | Levels, persistence, alert events | A-12 | 05 |
| A-14 | The two mandatory detection baselines | A-13 | 05 |
| A-15 | Chronos forecast wrapper, with a stubbed pipeline | A-11 | 06 |
| A-16 | `causes.yaml` loader and validation | A-02 | 07 |
| A-17 | Belief: presence matrix and exact enumeration | A-16 | 07 |
| A-18 | Belief: evidence factors | A-17, A-13 | 07 |
| A-19 | `probes.yaml` loader and validation | A-16 | 08 |
| A-20 | Policy: EVSI and the gates | A-18, A-19 | 08 |
| A-21 | Policy: action selection and dispositions | A-20 | 08 |
| A-22 | Policy: the four benchmark policies | A-21 | 08 |
| A-23 | CLI: `doctor`, `ingest`, `nightly`, `data fetch` | A-13, A-15 | 17 |
| A-24 | Cohort loaders: Stanford and PMData to parquet | A-08, A-23 | 01 |
| A-25 | Eval: detection suite | A-14, A-24 | 16 |
| A-26 | Eval: baseline-age suite | A-25 | 16 |
| A-27 | Eval: policy suite on the hidden-self-report oracle | A-22, A-24 | 16 |
| A-28 | Eval: ablation suite | A-27 | 16 |

---

## Critical path

```
A-01 -> A-02 -> A-03 -> A-08 -> A-09 -> A-11 -> A-13 -> A-18 -> A-20 -> A-22 -> A-27
```

A-06, A-07, A-15 and A-16 are off the critical path and can be done whenever their dependency is
met.

---

## Order notes

**A-02 before anything.** Every later task references a constant or a model. Transcribing the
contract once, exactly, prevents the whole class of drift this plan exists to avoid.

**A-16 and A-19 are data-authoring gates, not code.** `causes.yaml` and `probes.yaml` are authored by
a human and are read-only. Those tasks build the loader and the validation; **they do not write the
files**. If the files are absent, the loader tests use fixtures and the task is still completable.

**A-24 needs disk and network.** About 5 GB across the two datasets and roughly 33 GB free. Convert
to parquet, delete intermediates. Every task before A-24 runs with no dataset present.

**A-15 never downloads a model in a test.** The pipeline is stubbed. `wha data fetch chronos`
pre-downloads for real runs.

---

## Exit condition

```bash
uv run pytest -q                       # whole suite green
uv run ruff check src tests            # clean
uv run wha doctor                      # no fail rows
uv run wha demo run illness-onset --dry-run
uv run wha data fetch stanford && uv run wha data fetch pmdata
uv run wha eval detection
uv run wha eval baseline-age
uv run wha eval policy
uv run wha eval ablation
```

Four `EvaluationResult` files exist with real numbers, exact confidence intervals, both mandatory
detection baselines, and all four policies compared.

**Then stop and read the policy result before starting Phase B.**
