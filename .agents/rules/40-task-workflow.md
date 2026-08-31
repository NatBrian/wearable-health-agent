# Task workflow

You will run unattended for a long time, possibly across several sessions, with nobody watching.
This file is what makes that recoverable.

---

## The loop

```
1. Open plan/PROGRESS.md
2. Find the first row not marked [x]
3. Open ONLY that task file: plan/tasks/<id>.md
4. Read plan/02-contracts.md and the ONE component document the task names
5. Write the tests the task specifies, then the code
6. Run the exit command
7. Green  -> mark [x] with the date, COMMIT, then next task
   Red    -> fix your code
   Stuck  -> append to plan/BLOCKERS.md, mark [!], go to the next INDEPENDENT task
```

**One task at a time.** Do not read ahead, do not batch, do not start the next task before the
current one is green. Tasks are sized so that each is finished and verified before the next begins,
and that is the only thing keeping a long unattended run from drifting.

---

## Context discipline

For any task, load exactly:

- `AGENTS.md` (already in context)
- `plan/02-contracts.md`
- the **one** component document the task names
- the task file
- the source files the task names

**Not** the whole `plan/` folder, not every component, not `research/`. Loading more degrades your
attention over the material that matters and is the main cause of contract drift.

---

## PROGRESS.md

The single source of truth for where you are. Format:

```markdown
| Task | Title | Status | Date | Note |
|---|---|---|---|---|
| A-01 | Project skeleton and uv lock | [x] | 2026-09-02 | |
| A-02 | Database schema and migrations | [x] | 2026-09-02 | |
| A-03 | DataSource protocol and synthetic source | [ ] | | |
| A-04 | Verify manual HR reading reaches Health Connect | [!] | 2026-09-02 | blocked, see BLOCKERS |
```

`[x]` done and green. `[ ]` not started. `[~]` in progress. `[!]` blocked.

**Update it after every task, before starting the next.** If a session dies, the next one reads this
file and continues. If it is stale, work gets repeated or skipped.

---

## BLOCKERS.md

Append, never rewrite. One section per blocker:

```markdown
## A-07 — Chronos cannot load on CPU with 4 nights of context

**What I tried:** ChronosBoltPipeline.from_pretrained("amazon/chronos-bolt-tiny",
device_map="cpu"), then predict() with a length-4 context.

**What happened:** ValueError: context length 4 is below the minimum patch size.
Exact text: <paste it>

**What I think is wrong:** plan/components/06 assumes any context length works. The
model has a minimum I did not find documented.

**What I need:** a decision on the minimum nights before the forecast runs at all,
and a constant for it. Suggest FORECAST_MIN_NIGHTS, and status TOO_FEW_NIGHTS
below it, which the Forecast model already has.
```

Then move on. **A recorded blocker is a good outcome.** A silent workaround is the worst one.

---

## What counts as blocked

Blocked, record it and move on:

- A test asserts something the contract does not support
- A constant you need does not exist in `constants.py`
- A value you need does not exist in `data/knowledge/`
- A library behaves differently from what the component document assumes
- Two documents contradict each other
- A task depends on an unfinished earlier task that is itself blocked

**Not** blocked, keep going:

- You do not know how to do it yet. Read the component document again
- A test fails. That is the normal state before the code exists
- Something is tedious

---

## Definition of done

A task is `[x]` only when **all** of these hold:

1. The task's exit command exits zero.
2. `uv run pytest` is green **in full**, not just the new tests.
3. `uv run ruff check src tests` is clean.
4. No test was weakened, skipped or deleted.
5. No contract was changed.
6. `PROGRESS.md` is updated.
7. **The work is committed.**

If any of these is false, the task is not done. Do not mark it done and do not move on.

---

## Independence

Each task states its dependencies. If task A-07 is blocked and A-08 depends on A-07, skip A-08 too
and record why. If A-09 is independent, do A-09.

**Never fake a dependency to unblock yourself.** Do not stub out the blocked module and carry on, do
not write a placeholder that returns a plausible value. That produces a system that looks finished
and is not, which is far worse than an honest gap.

---

## Commits

**Commit after every task that reaches green, before starting the next one.** One task, one commit.

```bash
git add -A
git commit -m "Add nightly feature derivation and the coverage gate"
```

Imperative mood, one line, under 72 characters, no body unless something genuinely needs explaining.
**No attribution trailer, no co-author line, no tool name, no em-dash.**

Two reasons this matters more than it looks. A long unattended run needs **recovery points**: if
something goes wrong at task 40, a human can see exactly which task introduced it. And it gives a
**reviewable history** instead of one enormous undifferentiated diff.

**Do not commit a task that is not green.** Do not commit a blocked task; record it and move on.

**Never push. Never force. Never rewrite history.**

---

## If you finish everything

Run the full suite, run `uv run wha doctor`, run every scenario in `tests/fixtures/scenarios/`
through `uv run wha demo run`, and write a short summary at the end of `PROGRESS.md`: what is green,
what is blocked, and anything you noticed that a human should look at.

Then stop. Do not start improving things nobody asked for.
