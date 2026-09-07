# Handover, 5 September 2026, amended 7 September

**For somebody, or something, opening this repository with no prior context.**

Read this, then `STATUS.md`. Together they take five minutes and will save you from the two
mistakes everyone makes here.

> **Amendment, 7 September 2026.** Section 1 below said there was nothing to do. That was
> true when it was written and is not true now. The dashboard was rewritten on 6 September,
> a production-mimic simulation is running against subject `sim`, an investigation is open,
> and three clinical decisions are waiting on the user. **`STATUS.md` is the current
> picture; read it first.** Everything else in this file still holds: the traps, the rules,
> and the reason `history/` must not be mined for tasks.

---

## 1. There is nothing to do

**Superseded, 7 September 2026. See the amendment above.** The rest of this section is still
correct about `history/`, which is what it was written to warn you about.

The work was finished on 5 September. The repository is full of documents that look like
open work and are not.

- `history/review-2026-09/REFINEMENT-PLAN.md` is a 34 item queue. **All 34 are done.**
- `history/plan/` is a 67 task build plan with a progress log. **Finished.**
- `history/HANDOFF.md` and `HANDOFF-AGENTIC-FLOW.md` are briefs for jobs that ended.
- `history/PROPOSAL.md` is a design document superseded in fourteen documented ways.

If you are told to "continue", **ask what is wanted.** Do not pick a task out of `history/`.

State on the day this was written, every line re-run rather than remembered:

```
uv run pytest                     628 passed, 1 skipped
uv run ruff check src tests       clean
uv run ruff format --check ...    clean
uv run wha doctor                 no fail rows
uv run wha demo run <each>        11 of 11 live, 30 expectations, no failures
dashboard, all five pages         driven with Playwright, no errors
```

Nothing has ever been pushed. The branch is `feat/agentic-early-warning-system`.

---

## 2. What this system is, in one paragraph

A single-user wearable health early-warning agent. It watches overnight resting heart rate.
When a night is high **for that person**, it opens an *episode*, works out how likely each of
twelve causes is with an exact Bayesian enumeration over 4,096 states, and uses expected value
of sample information to decide whether asking the person one question is worth interrupting
them for. A deterministic safety floor runs first on the person's own words and can only ever
raise urgency; no language model can lower it. Every clinical sentence must quote a span that
is verbatim in a retrieved passage or it is stripped or labelled amber on screen. The dashboard
is an HTTP client of the API and holds no data logic.

`docs/ARCHITECTURE.md` explains the whole thing for someone who has never seen it, in plain
English, and is the right second read if you need depth.

---

## 3. The two rules that matter more than the rest

**A green test suite proves almost nothing here.** Every serious defect in this project's
history was found by opening the dashboard and clicking, not by reading code and not by running
tests. With the suite green, at various times: the Today page crashed on a button; "Delete
everything" deleted nothing while reporting success; the human review screen was invisible to
anyone who had ever escalated; and an evaluation suite printed invented effect sizes generated
by `random.Random(42)`. **If you change anything, finish by using the product.**

**The recurring defect is code that exists, is referenced, and is never reached.** Assume that
shape before you assume a logic error. It has turned up in every review pass: a database
adapter missing behind twelve `hasattr` guards, a poller nobody registered, a graph node with no
caller, a chart reading three field names nothing ever wrote.

---

## 4. If you touch anything

- **Always `uv run`.** Bare `python` resolves to an unrelated project's virtual environment and
  the resulting import errors look like code bugs.
- **Never invent a number.** Thresholds live in `src/wha/constants.py`, clinical figures in
  `data/knowledge/`, and every one carries a provenance of `CITED`, `DERIVED` or `ASSUMED`. If
  a value you need does not exist, that is a blocker, not a gap to fill. This is a health
  system; a plausible-looking invented figure is the worst thing you can add to it.
- **Measure before you change a test.** A test may genuinely encode a defect, and you may
  correct it, but only after running the real behaviour and putting the measurement in the
  commit. Measure, then assert.
- **Subject `me` holds four real nights of a real person's data. Never overwrite it.** Subject
  `sim` is disposable and `.env` is deliberately pointed at it.
- **Never `git push`.** Commit locally. No co-author line, no em-dash anywhere.
- Stop `wha serve` before `uv sync`; it holds the virtual environment open.

---

## 5. What is genuinely open

Two items, both in `BLOCKERS.md`, both needing a human decision rather than code, both already
disclosed to the user on screen:

1. **A night the watch cannot vouch for still concludes LIKELY_ILLNESS.** When sensor artifact
   is the leading explanation at 0.817, the headline still reads as possible illness. The gate
   meant to catch this fired in 0 of 20 measured cases and was deleted rather than retuned,
   because moving a clinical threshold to make a feature fire is exactly what this project must
   not do.
2. **A cited sentence can still misdescribe its source.** The grounding check proves the quoted
   span exists in a passage; it does not prove the sentence built around it is a fair reading.
   Fixing it properly means one model grading another, which every other check here avoids.

Everything else in `BLOCKERS.md` is either resolved by a later entry or is a recorded
limitation rather than a task.

---

## 6. The thing worth reading if you read one more file

`history/review-2026-09/AUDIT-2026-09-05.md`.

A 34 item plan was executed and reported complete, with a passing test suite offered as
evidence. Fifteen independent agents then read the code instead of the account of it and found
**seventeen of the items were not done**. Two were production-breaking and both had been
introduced by that same work: the agent's decision node raised `OperationalError` on every
episode, and "Delete everything" rolled back entirely so 58,730 heart rate samples survived a
delete request.

It is kept unedited on purpose. A verdict quietly revised afterwards is not a verdict, and its
value is precisely that it disagreed with the person who wrote the work.

The same pattern showed up again in `docs/CONTRACTS.md`, which turned out to be **24
disagreements** behind the code with only 4 recorded. That one had a real consequence: the
delete function's table list had been checked against the contract, the contract did not know
two tables existed, so the delete missed them. A stale document was the direct cause of a
data-rights failure.

Both now have tests that fail if they drift again.
