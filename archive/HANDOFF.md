# HANDOFF: build this

> ### THIS DESCRIBES A JOB THAT IS FINISHED
>
> **Read [`STATUS.md`](STATUS.md) first.** It describes where the project actually stands.
>
> This file was written on 1 September 2026 to brief an agent starting from an empty
> `src/`. That work is complete and has since been reviewed and repaired four times.
> Section 0 below still says "State of the code: **There is none**", which was true then
> and is not now: as of 4 September 2026 there are **546 passing tests, 1 skipped**, and
> **all 11 frozen scenarios pass end to end against the live model**.
>
> The rest of this file is still worth reading. The traps in section 8 and the constraints
> throughout still hold, and several of them turned out to describe defects that were
> actually present. It is the *status* that is out of date, not the *rules*.
>
> **One rule has been amended by the user since, and section 5 rule 3 is no longer
> absolute.** See the note under it. This banner and that note were written into this file
> on the user's explicit instruction, which is the only reason a read-only file was
> edited.

**Read this file to the end before doing anything else.**

You have no prior knowledge of this project. This file gives you everything you need to start.
Nothing else at the repository root is a specification, and two files there **will actively mislead
you** if you treat them as one. Section 1 names them.

---

## 0. Situation

| | |
|---|---|
| **What this is** | A **Python** project: a wearable health monitoring system |
| **State of the code** | **There is none.** `src/` does not exist. `tests/` contains only fixtures. **You are starting from zero** |
| **Your job** | Write the code by executing a finished plan, one task at a time. **67 tasks** |
| **The plan** | Already written and frozen, in `history/plan/`. **Do not add to it, extend it, or redesign it** |
| **Machine** | **Windows.** Run every command **from the repository root** |
| **Python** | Managed by **uv**, already installed and on PATH. Full path if needed: `C:\Users\Admin\.local\bin\uv.exe` |
| **Credentials** | Already configured in `.env`, which is gitignored. **But none are REQUIRED for any task.** Every test and every demo runs with no key, no token, no phone and no endpoint |
| **Network** | **Not required.** Five tasks (A-24 to A-28) download two public datasets; block them and continue. Everything else is offline |
| **Questions** | **You cannot ask any.** Nobody is watching. When stuck, write to `BLOCKERS.md` and move on |

### The instruction you were given is ambiguous. It means this.

**"Complete the implementation plan" means execute the plan by writing code.** It does **not** mean
finish writing a plan. The plan is complete. Writing more plan is out of scope and is the single
most likely way to waste this entire run.

---

## 1. Every path in this repository, and what to do with it

**This list is complete.** If something is not on it, it does not exist yet or you created it.

### Read these

| Path | What it is | When |
|---|---|---|
| **`history/HANDOFF.md`** | You are reading it | Once, now, to the end |
| **`AGENTS.md`** | The hard rules. Kept short so it can stay in context | First, and keep it loaded |
| **`GEMINI.md`** | A pointer to the two files above, in case your version prefers this filename | If it loaded, follow it here |
| **`.agents/rules/`** | Four files: environment, prohibitions, Python conventions, task workflow | Read three of them once. `30-python-conventions.md` when you write the first module |
| **`docs/CONTRACTS.md`** | Schemas, models, constants, service signatures, errors. **The contract** | In full, before task one, and again whenever unsure |
| **`history/plan/tasks/<id>.md`** | What to build, which tests, the exit command | **One at a time.** Only the current task |
| **`history/plan/components/NN-*.md`** | Design for one area | **Only the one your current task names** |
| **`history/plan/01-overview.md`** | System shape, control tiers, scope | Once, for orientation |
| **`history/plan/phases/*.md`** | Ordering, dependencies, critical path | Once, for orientation |
| **`history/plan/04-decisions.md`** | Why each choice was made | Only when tempted to change one |
| **`tools/make_synthetic.py`** | **Authoritative** record of the real device payload schema, observed on hardware | Before writing the ingestion parser. Task A-05 |

### Write these

| Path | What it is |
|---|---|
| **`history/plan/PROGRESS.md`** | Your checklist. **Update after every task.** The only reason a dead session can resume |
| **`BLOCKERS.md`** | What you could not do, and why. Append, never rewrite |
| **`src/wha/`** | **Does not exist yet. You create it.** All the code you write lives here |
| **`tests/unit/`, `tests/integration/`, `tests/scenario/`, `tests/ui/`** | **Do not exist yet. You create them.** Task A-01 |

### Load in code, but never edit

| Path | What it is |
|---|---|
| **`data/knowledge/`** | Four cited YAML tables: causes, probes, red flags, source allow-list. **The project's medical content, authored by a human.** Your code loads and validates them |
| **`tests/fixtures/scenarios/`** | Eleven frozen scenarios. Their `expect` blocks are the contract. **If one fails, fix the code** |
| **`tests/fixtures/llm_cassettes/`** | Nineteen authored LLM responses, so everything runs offline |
| **`.env`** | Already written and gitignored. Configuration and secrets. **Never commit it, never log a value from it** |

### Do not read, or read only narrowly

| Path | What it is | What to do |
|---|---|---|
| **`history/PROPOSAL.md`** (754 lines) | A narrative design document written **before** the plan. **Out of date in fourteen documented ways**, naming components that were dropped | **Do not read it. Do not build from it.** If you already have, disregard it entirely |
| **`README.md`** | Public-facing overview | Ignore. Task C-10 rewrites it |
| **`research/`** | 126,000 words of evidence and citations | Read **only** to find a number or a citation. **Never take a design decision from it.** Several notes are superseded and state the opposite of the current design |
| **`archive/`** | An earlier, weaker generation | **Never read it.** It holds figures found under audit to be fabricated |
| **`DISCLAIMER.md`**, **`LICENSE`**, **`.gitignore`** | Legal and repository config | Leave alone |

Where `history/PROPOSAL.md` and `history/plan/` disagree, **`history/plan/` wins, always.** Every disagreement is catalogued
in `history/plan/04-decisions.md` Part B, items B-1 to B-14.

---

## 2. Start here, in this order

**Read these four files first. All of them. They are short and they are the whole operating manual.**

```
AGENTS.md                          the hard rules
.agents/rules/10-environment.md    how to run anything on this machine
.agents/rules/20-prohibitions.md   what is forbidden, and why each one is silent if broken
.agents/rules/40-task-workflow.md  the loop, blockers, definition of done
```

`.agents/rules/30-python-conventions.md` is a reference. Read it once when you write the first
module.

**Then read `docs/CONTRACTS.md` in full.** It defines every schema, model, constant, service
signature and error class. Every task depends on it and no task may contradict it.

> **THIS LOOP IS OVER.** 63 of the 67 tasks are `[x]`; the remaining four are recorded at the
> top of `history/plan/PROGRESS.md` and carried into `STATUS.md` and `BLOCKERS.md`, so there is
> nothing to pick up here. `history/plan/PROGRESS.md` is now a frozen build log and `history/plan/tasks/` is
> history. Read **`STATUS.md`** for what the work is now, and **`BLOCKERS.md`** for what is
> open. The rest of this section is kept because it records how the build was structured, not
> because there is a loop to enter.

**Then begin the loop:**

1. Open `history/plan/PROGRESS.md`. Find the **first row not marked `[x]`**. It will be `A-01`.
2. Open **only** `history/plan/tasks/A-01.md`.
3. Do exactly what it says. Write the tests it names first, then the code.
4. Run **its** exit command. Not the component's.
5. Green? Tick the row in `history/plan/PROGRESS.md` with today's date, then **commit**.
   Blocked? Append to `BLOCKERS.md`, mark the row `[!]`, and go to the next task that does not
   depend on it.
6. Next row. **Work through all 67, skipping only what is genuinely blocked.**

Your first command will be from inside `history/plan/tasks/A-01.md`. Do not run `uv sync` before that;
`pyproject.toml` does not exist yet, and creating it **is** task A-01.

That is the whole job.

---

## 3. How you will be judged

The human running you will review by **running the demo**. Not by reading your code, and not by
reading your summary. These commands must work on a clean checkout:

```bash
uv sync
uv run wha doctor                       # no fail rows
uv run wha demo run illness-onset       # a full episode, offline, no endpoint needed
uv run wha demo run red-flag            # deterministic escalation
uv run wha demo run injection-poisoned  # and injection-clean, same disposition
uv run wha serve                        # every page renders
uv run pytest                           # green in full
```

**Everything above runs offline.** No network, no phone, no live model. The cassettes are authored
and committed, the scenarios are frozen, and `wha demo run` forces the `cassette` provider unless
`--live` is passed.

If any of these cannot work, that is the most important thing to put in your final report, ahead of
everything else.

---

## 4. What you need to run this. Two answers.

### Data: you need none

**Every test and every demo runs on synthetic data you generate yourself**, from the eleven frozen
scenarios in `tests/fixtures/scenarios/`. Each has a fixed seed, so two runs produce byte-identical
input. No wearable, no phone, no export, no personal data of any kind.

| What | Data it needs | Blocks if absent |
|---|---|---|
| Every unit test | Synthetic, generated in-process | Nothing |
| Every scenario test | Synthetic, from the frozen fixtures | Nothing |
| Every `wha demo run` | Synthetic | Nothing |
| Tasks **A-24 to A-28** only | Two **public** cohort datasets, roughly 5 GB, downloaded by `uv run wha data fetch` | **Only those five tasks.** Block them and continue |

There is also a subject called `me` for real wearable data. **It has almost none**, and that is the
correct state: the system reports rung `COLD` and disposition `INSUFFICIENT_DATA` until it has three
usable nights. That behaviour is deliberate, is tested by the `cold-start` scenario, and is not a
problem to fix.

### LLM: configured, but tests never touch it

`.env` at the repository root is already written and gitignored. It points at a live
OpenAI-compatible endpoint.

| Context | Provider | Why |
|---|---|---|
| **`pytest`, always** | `cassette` | An **autouse fixture in `tests/conftest.py` overrides `.env`.** Non-negotiable |
| `wha demo run` | `cassette` | Deterministic, so the frozen `expect` blocks hold. `--live` opts in |
| `wha doctor`, `serve`, `episode step`, `llm record` | live, from `.env` | Real model for anything a human runs |

**Why tests never use the live endpoint:** you will run the suite hundreds of times across 67 tasks.
A live provider would make that slow, costly, and nondeterministic enough to break every frozen
scenario assertion.

Nineteen cassettes are already committed under `tests/fixtures/llm_cassettes/`, so **you never need
the endpoint to be up.** If it is down, everything still works.

---

## 5. The five rules that override everything

1. **Never modify, weaken, delete or skip a test to make it pass.** Not a loosened assertion, not a
   widened tolerance, not an `xfail`, not a changed expected value. If a test looks wrong, that is a
   **blocker**: write it to `BLOCKERS.md` and move to the next independent task.
2. **Never invent a number.** Every threshold is in `src/wha/constants.py`. Every clinical figure is
   in `data/knowledge/`. If a value you need is not there, that is a blocker.
3. **Never edit `data/knowledge/`, `history/plan/` (except `PROGRESS.md` and `BLOCKERS.md`), `history/PROPOSAL.md`,
   `history/HANDOFF.md`, `research/` or `archive/`.** They are read-only inputs.

   > **AMENDED 4 September 2026, by the user, narrowly.** A clinical figure in
   > `data/knowledge/` or `src/wha/constants.py` **may** be corrected in exactly one
   > circumstance: the published source it cites can be quoted saying something different.
   > Not a judgement that a number looks wrong, not a better number from elsewhere, not the
   > model's own knowledge. Every such change goes in `docs/KNOWLEDGE-CHANGELOG.md` with
   > the old value, the new value and the quoted source sentence. Three changes have been
   > made under this exception so far. **Everything else in rule 3 still holds**, and
   > inventing or "improving" a clinical figure remains the one line this project must not
   > cross. If the source does not settle it, it is still a blocker.
4. **Always `uv run`.** Never bare `python`, never bare `pip`. On this machine `python` resolves to
   an unrelated project's virtual environment and your imports will fail in a way that looks like a
   code bug and is not.
5. **Never `git push`.** Commit locally when a task says to. Never push, force, rebase or rewrite
   history.

A recorded blocker is a **good outcome**. A silent workaround is the worst one.

---

## 6. How the plan is organised

Three layers. Load only what a task names.

| Layer | What | When you read it |
|---|---|---|
| `docs/CONTRACTS.md` | Schemas, models, constants, service signatures, errors. **The contract.** | Every task |
| `history/plan/components/NN-*.md` | The design for one area: logic, edge cases, named tests | Only the one your task names |
| `history/plan/tasks/<id>.md` | What to build, which tests, the exit command, the do-not list | One at a time |
| `history/plan/phases/*.md` | Ordering, dependencies, critical path | For orientation, once |
| `history/plan/01-overview.md` | System shape, where agency lives, scope | For orientation, once |
| `history/plan/04-decisions.md` | Why each choice was made | Only when tempted to change one |

> **Follow the exit command in the TASK file, not the one in the component document.** Component
> exits describe the finished area and may reference commands a later task creates.

---

## 7. What this system is, in sixty seconds

A wearable detects that something changed but cannot say why. A raised overnight resting heart rate
is produced by infection, alcohol, hard training, short sleep, stress, vaccination or the luteal
phase, and to a wrist sensor they look nearly identical.

**The monitor is deterministic.** Every morning it derives resting heart rate from the 00:00 to 07:00
window, compares it against the person's own baseline, and decides whether anything happened. No
language model. Most nights are quiet and cost zero.

**The agent is the investigation.** When a deviation is flagged, an LLM-driven agent opens an
*episode*. It chooses its own read-only tool calls, reads history, retrieves clinical evidence,
writes its own questions and runs the interview. A deterministic model tracks which of twelve causes
are contributing.

**One decision is not the model's:** whether to interrupt the human. That is expected value of
sample information against an interruption cost, in numpy, outside the model. It is the project's
contribution and it is the reason the policy can be benchmarked rather than merely demonstrated.

---

## 8. Traps that fail silently

Each of these produces code that runs and is wrong.

| Trap | Rule |
|---|---|
| `python` on PATH | Points at another project's venv. **Always `uv run`** |
| LangGraph `interrupt()` | Re-runs the **whole node** on resume, not from the interrupt. Everything before it must be idempotent |
| Thinking models | `max_tokens` below `LLM_MAX_TOKENS_FLOOR` returns an **empty string**, not an error |
| Provider JSON mode | Not uniform across providers. Always validate with Pydantic. One repair round, then raise |
| **YAML booleans** | Bare `no`, `yes`, `on`, `off` parse as booleans. An `option_id: no` becomes `False` and the slot silently breaks **while still passing YAML validation** |
| Log-space inference | Products of 4096 Gaussian densities underflow to zero within a few nights. You get a uniform posterior and never notice |
| MAD floor | MAD is **exactly zero** on quantised data. Without `BASELINE_SCALE_FLOOR_BPM` you divide by zero and every night becomes an infinite deviation |
| Telegram `callback_data` | Hard 64-byte limit |
| Windows paths | `pathlib.Path` only. Never a hard-coded separator |
| Shell heredocs | This repository has already lost file content to them. Use a file-writing tool |

---

## 9. What already exists and works

- **`data/knowledge/`** -- the cited medical tables. Twelve causes, nine probes, the red-flag rules,
  the endpoint allow-list. **Read-only.** Every number labelled `CITED`, `DERIVED` or `ASSUMED`.
- **`tests/fixtures/scenarios/`** -- eleven frozen scenarios. Their `expect` blocks are the contract.
  **If a scenario fails, fix the code, never the fixture.**
- **`tools/make_synthetic.py`** -- documents the **real device payload schema**, observed on hardware.
  Authoritative. Read it before writing the ingestion parser. Do not invent field names.
- **`tools/probe_healthconnect.py`** -- the bridge probe, structure-only, prints no health values.
- **`tools/kaggle_serve_qwen27b.ipynb`** -- the self-hosted LLM endpoint, measured on hardware.

---

## 10. Facts measured on real hardware, not assumed

- The bridge delivers **heart rate in 1-minute buckets** and **steps in daily buckets**. There is no
  per-minute step data, which is why the published activity-masking method is impossible and the
  detector uses the nocturnal window instead.
- Samsung Health writes **heart rate, steps, sleep stages, exercise, blood oxygen, distance and
  total calories** to Health Connect. Still **no HRV, no respiratory rate, no skin temperature, no
  resting heart rate**. **Any design assuming those will not run.** Sleep and exercise may never
  arrive at all; treat them as optional everywhere.

  > **Corrected 3 September 2026.** This previously read "only heart rate, steps, sleep stages and
  > exercise", which was the state on day zero. A probe of the live bridge found blood oxygen,
  > distance and total calories as well, stable across 7, 30 and 90-day windows. All seven are now
  > ingested. The second half of the claim still holds and was re-verified at the same time. Skin
  > temperature is Galaxy Watch 6 and later, so it will not appear on this device at all.
  > See `docs/DESIGN-DATA-CHANNELS.md`.
- The self-hosted endpoint sustains about **9.2 tokens per second** and its URL and key regenerate
  every session. **It is expected to be down most of the time.** Every test runs against recorded
  cassettes with `WHA_LLM_PROVIDER=cassette`, and `LLMUnavailable` parks an episode rather than
  fabricating or closing it.
- About **33 GB free disk and no second drive.** Extract datasets selectively, convert to parquet,
  delete intermediates.

---

## 11. `research/` is evidence, not design

You may read `research/` to find a citation or a measured figure. **You must never take an
architectural conclusion from it.** Several of those notes are superseded and say the opposite of
the current design: one recommends building on a manual export that has been ruled out, another
assumes a team of four. `archive/` is an earlier, weaker generation and is not a source of fact.

**Design comes from `history/plan/` only.**

---

## 12. What a human still owes you, and what to do meanwhile

None of these blocks starting. All are recorded in `history/plan/PROGRESS.md`.

| Owed | Blocks | Do this instead |
|---|---|---|
| ~~`data/knowledge/corpus.yaml`~~ | nothing | **Delivered.** Generated by `wha corpus build` from the authored knowledge tables, 33 documents. The fetched MedlinePlus layer is deliberately not in it; see `src/wha/service/corpus.py` |
| `data/knowledge/cohort_labels.yaml` | A-25 to A-28 only | Still absent, so detection accuracy is reported as "not evaluated" rather than given a number. Whether to fetch the public cohort datasets was **delegated to the agent** by the user and is not yet decided. See `BLOCKERS.md` |
| Whether a manual heart-rate reading reaches Health Connect | nothing | Implement `MEASURE` with **both** kinds. If the spot reading proves unavailable later, `wear_tonight` is the fallback |

**LLM cassettes are already authored and committed.** Nineteen files under
`tests/fixtures/llm_cassettes/`. There is no recording step, and **you never need the endpoint**.

---

## 13. Definition of done, per task

All six, or it is not done:

1. The task's exit command exits zero.
2. `uv run pytest` green **in full**, not only the new tests.
3. `uv run ruff check src tests` clean.
4. No test weakened, skipped or deleted.
5. No contract changed.
6. `history/plan/PROGRESS.md` updated with the date.
7. **The work is committed.** One task, one commit. Never push.

## 14. When you finish, or cannot continue

> **The commands below are still right, with two corrections.** Add `--live` to the demo runs if
> you want them to exercise the model rather than cassettes, and run the eleven in two batches:
> back to back they take longer than ten minutes, and a killed run leaves an orphaned `python.exe`
> holding `data/demo.sqlite` open so the next one fails with `WinError 32`. Then **use the
> dashboard**, which is how every serious defect in this project was actually found.
>
> The reporting checklist below still applies except item 1: there is no task count to report any
> more. Report what you measured instead.

Run all of these:

```bash
uv run pytest
uv run ruff check src tests
uv run wha doctor
for s in illness-onset alcohol-night workout-explained red-flag cold-start nonwear-gap          no-response-timeout stress-mimic budget-exhausted injection-poisoned injection-clean; do
  uv run wha demo run $s
done
```

Then write the final summary at the end of `history/plan/PROGRESS.md` and repeat it in your report:

1. **How many of the 67 tasks are `[x]`**, by phase.
2. **Which demo commands work**, one line each, because that is how you will be reviewed.
3. **Every blocker**, with the one-line reason. Do not bury these.
4. **Anything you had to guess.** If you invented a name, a shape or a value that the contract did
   not give you, say so explicitly. A guess you flag is fine. A guess you hide is not.
5. **Anything you noticed that a human should look at**, including anywhere the plan seemed wrong.

**Then stop.** Do not start improving things nobody asked for, do not begin Phase D, and do not
refactor code no task named.

---

## 15. Project history, for context only

Research, design and implementation planning are complete and are not to be redone.

`research/findings/` holds nine investigations, roughly 126,000 words with about 2,100 citations,
each carrying explicit `UNVERIFIED` flags where a claim could not be sourced. `history/PROPOSAL.md` is the
written narrative artefact and **is not the thing to code from**; where it and `history/plan/` disagree,
`history/plan/` wins, and `history/plan/04-decisions.md` Part B records all fourteen contradictions and how each is
resolved.

Two prior corrections are worth knowing because they set the standard for this repository. An
earlier generation of the research was audited and found to carry fabricated performance figures.
And a preprint flagged as a required read was left unread while the design was written; reading it
falsified a sentence in the project's own summary, and the claim was narrowed rather than defended.

**State the evidence and its strength. Do not round a suspicion up to a fact.**
