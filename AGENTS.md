# AGENTS.md

Instructions for any coding agent working in this repository. This file is in context on every
turn. Detailed rules live in `.agents/rules/`. The design lives in `plan/`.

---

## The five rules that override everything

1. **Never modify, weaken, delete or skip a test to make something pass.** If a test looks wrong,
   that is a blocker. Write it to `plan/BLOCKERS.md` and move to the next task.
2. **Never invent a number.** Every threshold comes from `src/wha/constants.py`. Every clinical
   figure comes from `data/knowledge/`. If a value you need does not exist, that is a blocker.
3. **Never edit `data/knowledge/`, `PROPOSAL.md`, `HANDOFF.md`, `research/`, `archive/`, or
   anything in `plan/` EXCEPT `plan/PROGRESS.md` and `plan/BLOCKERS.md`.** Those two are yours to
   write and you must keep them current. Everything else there is a read-only input.
4. **Always `uv run`.** Never bare `python`, never bare `pip`. On this machine `python` resolves to
   an unrelated project's virtual environment and your imports will fail in confusing ways.
5. **Commit after every green task. Never `git push`.** One task, one commit, only when the task is
   fully done. Never push, never force, never rewrite history.

---

## How to work

```
1. Read plan/PROGRESS.md
2. Find the first task not marked done
3. Open ONLY that task file: plan/tasks/<id>.md
4. Read plan/02-contracts.md and the one component document the task names
5. Do the task
6. Run the exit command the task gives you
7. Green -> tick it in plan/PROGRESS.md with the date, COMMIT, and continue
   Red   -> fix your code, not the test
   Stuck -> append to plan/BLOCKERS.md and go to the next independent task
```

Do **one task at a time**. Do not read ahead. Do not batch. Each task is sized to be finished and
verified before the next one starts.

---

## Where things are

| Path | What it is | Writable? |
|---|---|---|
| `plan/02-contracts.md` | Schemas, models, constants, errors. **The contract** | No |
| `plan/components/NN-*.md` | Design for one area. Read the one your task names | No |
| `plan/tasks/*.md` | What to do, and the test that proves it | No |
| `plan/PROGRESS.md` | Your checklist. **Update after every task** | Yes |
| `plan/BLOCKERS.md` | What you could not do, and why | Yes |
| `data/knowledge/` | Cited medical tables. Authored by a human | **No** |
| `src/wha/` | The code you write | Yes |
| `tests/` | Tests. You may add, never weaken | Add only |
| `research/` | Evidence and citations. **Not design** | No |

**`research/` is evidence, not design.** You may read it to find a citation or a measured figure.
You must never take an architectural conclusion from it. Several of those documents are superseded
and say the opposite of the current design. Design comes from `plan/` only.

---

## Commands

```bash
uv sync                        # install
uv run pytest                  # the whole suite
uv run pytest tests/unit -q    # fast loop
uv run ruff check src tests    # lint
uv run ruff format src tests   # format
uv run wha doctor              # check every dependency and print pass/fail
```

Tests run **offline** with `WHA_LLM_PROVIDER=cassette`, forced by an **autouse fixture** in
`tests/conftest.py` that overrides `.env`. `.env` configures a live provider for development; tests
must never reach it. If a test needs the network, it is wrong. That is a blocker.

---

## Traps that fail silently

| | |
|---|---|
| `python` on PATH | Points at another project's venv. Always `uv run` |
| LangGraph `interrupt()` | Re-runs the **whole node** on resume. Everything before it must be idempotent |
| Thinking models | `max_tokens` below `LLM_MAX_TOKENS_FLOOR` returns an **empty string**, not an error |
| Provider JSON mode | Not uniform. Always validate with Pydantic. One repair round, then raise |
| **MAD floor** | MAD is **exactly zero** on quantised data. Without `BASELINE_SCALE_FLOOR_BPM` you divide by zero and every night becomes an infinite deviation |
| **Log-space inference** | Products of 4096 Gaussian densities underflow to zero within a few nights. You get a uniform posterior and never notice. Always log space, max-subtraction softmax |
| **YAML booleans** | Bare `no`, `yes`, `on`, `off` parse as booleans. An `option_id: no` becomes `False` and the slot silently breaks **while still passing YAML validation** |
| Telegram `callback_data` | Hard 64-byte limit |
| Windows paths | `pathlib.Path` only. Never a hard-coded separator |
| Shell heredocs | This repo has already lost file content to them. Use a file-writing tool |

---

## When you are stuck

Append to `plan/BLOCKERS.md`:

```markdown
## <task-id> — <one line>
**What I tried:** ...
**What happened:** exact error text
**What I think is wrong:** ...
**What I need:** a decision, a missing constant, a corrected test
```

Then move on. **Do not** invent a workaround, relax a type, catch and swallow an exception, add a
`# type: ignore`, or change a contract. A recorded blocker is a good outcome. A silent workaround is
the worst one.

---

## Style, in one paragraph

Python 3.12. Full type hints. Pydantic v2 for every boundary. Small functions with one job. No
business logic in `ui/`. No database access outside `db/` and `service/`. Docstrings say *why*, not
*what*. Match the surrounding code. No em-dashes in any output, comment or commit message.

**Commit after every green task**, before starting the next:

```bash
git add -A && git commit -m "Add nightly feature derivation and the coverage gate"
```

Imperative mood, one line, under 72 characters, **no attribution trailer, no co-author line, no tool
name, no em-dash**. One task, one commit. This is what gives a long unattended run recovery points
and a reviewable history. **Never push.**
