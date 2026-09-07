# Task workflow

> **THE 67-TASK LOOP BELOW IS FINISHED.** `history/plan/PROGRESS.md` is a frozen build log, not a
> queue: 63 rows are `[x]` and the four that are not are carried into `STATUS.md` and
> `BLOCKERS.md`. The work now is fixing, extending and verifying a system that exists:
> read **`STATUS.md`** for where it stands and **`BLOCKERS.md`** for what is open.
> **Do not update `PROGRESS.md`.** Keep `STATUS.md` and `BLOCKERS.md` current instead.
>
> What still applies, and is why this file is kept: the definition of done, the blocker format,
> commit discipline, and the rule that a recorded blocker beats a silent workaround. What has
> been **added** since: run the suite and ruff **once at the end**, not after every edit, and
> then **use the dashboard as an ordinary person**, because a green suite has repeatedly passed
> while the product was broken.

You will run unattended for a long time, possibly across several sessions, with nobody watching.
This file is what makes that recoverable.

---

## The loop

```
1. Open history/plan/PROGRESS.md
2. Find the first row not marked [x]
3. Open ONLY that task file: history/plan/tasks/<id>.md
4. Read docs/CONTRACTS.md and the ONE component document the task names
5. Write the tests the task specifies, then the code
6. Run the exit command
7. Green  -> mark [x] with the date, COMMIT, then next task
   Red    -> fix your code
   Stuck  -> append to BLOCKERS.md, mark [!], go to the next INDEPENDENT task
```

**One task at a time.** Do not read ahead, do not batch, do not start the next task before the
current one is green. Tasks are sized so that each is finished and verified before the next begins,
and that is the only thing keeping a long unattended run from drifting.

---

## Context discipline

For any task, load exactly:

- `AGENTS.md` (already in context)
- `docs/CONTRACTS.md`
- the **one** component document the task names
- the task file
- the source files the task names

**Not** the whole `history/plan/` folder, not every component, not `research/`. Loading more degrades your
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
## policy — a night the watch cannot vouch for still concludes LIKELY_ILLNESS

**What I tried:** item 24, whose check is "run the simulation with a poor coverage night, the
outcome says the night could not be judged".

**What happened:** it cannot pass. The gate required sensor_artifact as top cause at 0.50 or
more AND p_illness below 0.10. Measured over 20 combinations of coverage 30 to 239 minutes and
residual 3.2 to 10.0 bpm, it fired in none:

    coverage 30, residual 10.0 -> sensor 0.817, p_illness 0.138 -> LIKELY_ILLNESS

**What I think is wrong:** not the code. The same large residual that raises sensor_artifact
raises p_illness, so the two conditions are mutually exclusive under this belief model.

**What I need:** a decision I cannot make from evidence. Either a coverage figure below which a
night is unjudgeable regardless of belief, which needs a source or an explicit UNEVIDENCED
label, or a change to the outcome TEXT rather than the disposition so it cannot talk an
escalation down. Both the disposition set and the outcome model are frozen by the contract.
```

That is a real entry from `BLOCKERS.md`, 5 September 2026, chosen as the example because it
shows the two things that make a blocker useful: **the measurement that establishes the problem**,
and **the specific decision being asked for**. "It does not work" is not a blocker.

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
