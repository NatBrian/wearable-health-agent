# AGENTS.md

**The rules for any coding agent working in this repository.** This is the only file that
holds them. `CLAUDE.md` and `GEMINI.md` are three-line pointers here, so every agent gets
the same rules whichever tool loaded it.

**Read `README.md` first** for what this project is, where everything lives and what to
read for the goal you have been given. Then read this. Then start.

> **The project is finished.** There is no task queue. `archive/` is full of documents that
> look like plans and every one describes a job that has ended. If you are asked to
> "continue" with no further detail, **ask what is wanted** rather than inventing work.

---

## The six rules that override everything

**1. Never modify, weaken, delete, rename, skip or `xfail` a test to make it pass.** Not a
loosened assertion, not a widened tolerance, not a changed expected value.

The one narrow exception: a test can encode the defect rather than the behaviour. Then, and
only in this order:

1. **Measure the real behaviour first.** Run it, print it, write the number down. Never
   reason about what it probably does.
2. **Decide whether the new behaviour is correct**, on that measurement.
3. **Then** change the expectation, with the measurement and the reason in the commit.

Measure, then assert. Never assert, then measure.

**2. Never invent a number, and never write clinical content from your own knowledge.**
Every threshold comes from `src/wha/constants.py`. Every clinical figure comes from
`data/knowledge/`. The agent may cite the corpus and nothing else. If a value you need does
not exist, that is a blocker, not a gap to fill.

**3. Every number in user-facing text must be sourced, or it must go.** It has to be either
from a published source with the citation adjacent AND about a population the claim applies
to, or an operating parameter of this system, which is a fact about the code rather than a
claim about health. **Anything this project measured about itself is neither**, and belongs
in `experiments/` behind its disclaimer. Two tests enforce this. See `experiments/README.md`
for why, and `archive/session-logs-2026-09/superpowers/plans/2026-09-07-claims-cleanup.md`
for what went wrong when it was not enforced.

**4. `data/knowledge/` is under change control.** A clinical figure there, or in
`src/wha/constants.py`, may change only when one of two things holds:

1. The published source it cites can be quoted saying something different.
2. A measurement made in this repository, on real data, with the script committed, says
   something different.

Not a hunch, not a better number from elsewhere, never your own knowledge. **Every change
goes in `docs/KNOWLEDGE-CHANGELOG.md`** with the old value, the new value, and either the
quoted sentence or the command that reproduces it. If neither settles it, it is a blocker.

**5. Always `uv run`.** Never bare `python`, never bare `pip`. On this machine `python`
resolves to an unrelated project's virtual environment and imports fail confusingly.

**6. Commit when work is done and verified, and push.** Two things you may never do:
**force-push**, and **rewrite history that has already been pushed**. Somebody else may
have pulled it. If a rewrite looks necessary, that is a question for the person you are
working with, not a decision to make.

`main` is the default branch and holds everything. Work on a branch off it and open a pull
request; the ruleset on `main` restricts direct updates, so a merge needs the admin
override and is the repository owner's call rather than yours.

Commit messages say why, not what. No co-author line, no tool name, no em-dash anywhere.

---

## How to work

```
1. Read README.md, then this file.
2. RESEARCH before deciding. Every clinical or agentic design choice needs a citation,
   or an explicit written statement that nothing settles it. Never reason a medical
   choice from first principles when a study exists.
3. PLAN before building. Write down what you are going to do and why, and get it agreed
   before you write code. For anything larger than a one-line fix, write it to a file.
4. Do the work.
5. Run the suite and ruff ONCE, at the end, not after every edit.
6. Then USE THE PRODUCT. See below. This is not optional.
7. Commit with the reasoning in the message, and push. Never force, never rewrite.
```

**Steps 2 and 3 are not ceremony, and skipping them is how this project has gone wrong.**
This is a medical system: a design choice made from intuition rather than a source is a
clinical claim nobody checked, and it will end up on a screen somebody trusts. A plan
written down before the work can be argued with, which is the whole point; a plan
reconstructed afterwards is a description of whatever happened.

Every substantial change to this system went research, then a written spec, then a plan,
then the build. Those documents are in `archive/session-logs-2026-09/superpowers/`, and they
are worth reading as examples of the expected shape, never as a queue of work.

`uv run python tools/demo_film/serve_demo.py` opens a complete seventeen day timeline with
an illness, a relapse and a recovery already in it, so there is always something real to
look at.

---

## How this project fails

Every one of these happened here. They share a shape: **the failure reported success.** The
suite was green, the exit code was zero, the output looked right. Normal instincts do not
catch this, so it is written down.

**A green suite proves almost nothing.** Every serious defect in this project was found by
using the dashboard, never by reading code and never by running tests. Full suites have
passed while a page crashed on load, while the safety floor was unreachable, while four
subsystems had never once executed, and while an import error made the Today page
unopenable. **Finish by driving the real interface as an ordinary person would**, on the
real pages, and read what the screen actually says.

**Write down what should happen before you run it.** A run you watch and then describe
afterwards always looks like it worked, because the description gets written to fit what
happened. The demo build states each day's expected outcome first and halts on the first
mismatch, and that caught four defects no test could have. If you are about to run something
whose result you will have to judge, judge it in advance.

**Look at the artefact, not the exit code.** A scene was filmed against the wrong date and
looked entirely correct. A film was encoded twice with captions four times too large, both
times exiting zero. Open the file. Read the frame. Query the database.

**Verify the absence, not just the silence.** A defect was reported here that did not exist,
because the grep behind it searched two directories and not the third. Before concluding
something is missing, check that you looked where it would be.

**Make it a rule only a test can enforce.** A misapplied citation was found and corrected in
one file, then reintroduced two days later in another by somebody who had not read that
file. A correction that lives only where it was made does not survive contact with new
prose. If it matters, it is a test.

**Try the expensive thing on a cheap sample.** A half hour render was burned twice to find a
font size that a ten second slice would have shown immediately.

---

## What this system is, in five lines

An overnight resting heart rate deviation opens an **episode**. A Bayesian belief over
twelve causes is updated from the sensor data, and an **EVSI policy** decides whether asking
the person a question is worth the interruption. A **deterministic safety floor** runs first
and can only ever raise urgency, never lower it, and no model may overrule it. Every
clinical sentence the agent produces must **quote a span that is verbatim in a retrieved
passage**, or it is stripped or labelled on screen. That check proves the quoted span
exists, **not** that the sentence around it is fair to the source. The dashboard is a
**client of the HTTP API** and holds no data logic.

---

## Rules specific to this system

- **The medical content is cited or it is disclosed.** A clinical design choice must be
  backed by a study cited next to it, or stated plainly as unevidenced in **both** the docs
  and the dashboard. Never let an unevidenced choice look like an evidenced one.
- **A citation must be about the population you are applying it to.** A number that looks
  properly sourced but describes a different condition is worse than an uncited one, because
  a reader has no reason to doubt it. This repository has made that mistake twice.
- **The safety floor is deterministic and additive.** A model may raise urgency. Nothing a
  model says may lower it. Where a validated rule exists the model ELICITS the items and the
  rule DECIDES: today that is chest pain and the Marburg Heart Score. Everything else
  escalates on a phrase match, because no validated history-only rule covers it.
- **No data logic in `ui/`.** The dashboard calls the HTTP API through `wha.api.client`. If
  a page needs a number, add an endpoint. A test enforces this.
- **UI copy may contain no digits.** A test enforces that too. Numbers reach the screen from
  the API, so a figure typed into prose cannot drift away from the code.
- **Retrieved external text is untrusted.** Scan it for injection before the model sees it,
  and name its source wherever it is shown. MedlinePlus is attribution-only.
- **Subject `me` holds the user's real watch data. Never overwrite or delete it.** `sim` and
  `demo` are disposable.
- **Single user.** One person, one phone. Do not build for multi-user.

---

## Commands

```bash
uv sync                              # install
uv run wha data fetch corpus         # REQUIRED once, see README setup
uv run wha doctor                    # check every dependency, print pass/fail
uv run pytest -n auto                # the whole suite, about five minutes
uv run pytest tests/unit -q          # fast loop
uv run ruff check src tests          # lint
uv run ruff format src tests         # format
uv run wha serve                     # API on 8500 plus scheduler
cd frontend && npm run dev           # Vite dashboard on 8443, in a second terminal
uv run python tools/demo_film/serve_demo.py   # the finished demo timeline
```

Tests run **offline** with `WHA_LLM_PROVIDER=cassette`, forced by an autouse fixture in
`tests/conftest.py` that overrides `.env`. If a test needs the network, it is wrong.

---

## Traps that fail silently

| | |
|---|---|
| **Code that is never reached** | **The defect this codebase produces over and over.** Something defined, referenced by other code, and never executed: a `db` adapter behind twelve `hasattr` guards, a poller nobody registered, a safety argument no caller passed, a constant documented and read by nothing. **Assume this shape before assuming a logic error** |
| `python` on PATH | Points at another project's venv. Always `uv run` |
| LangGraph `interrupt()` | Re-runs the **whole node** on resume. Everything before it must be idempotent |
| Thinking models | `max_tokens` below `LLM_MAX_TOKENS_FLOOR` returns an **empty string**, not an error |
| Provider JSON mode | Not uniform. Always validate with Pydantic. One repair round, then raise |
| **MAD floor** | MAD is **exactly zero** on quantised data. Without `BASELINE_SCALE_FLOOR_BPM` every night becomes an infinite deviation |
| **Log-space inference** | Products of 4096 Gaussian densities underflow to zero within a few nights. You get a uniform posterior and never notice |
| **YAML booleans** | Bare `no`, `yes`, `on`, `off` parse as booleans. An `option_id: no` becomes `False` and the slot breaks **while still passing validation** |
| Telegram `callback_data` | Hard 64-byte limit |
| Windows paths | `pathlib.Path` only. Never a hard-coded separator |
| Shell heredocs | This repo has already lost file content to them. Use a file-writing tool. **Never insert an import by matching a prefix of an existing import line**: it silently truncates the rest and the page dies while the tests stay green |
| `docs/CONTRACTS.md` | Compared against the models, schema and constants on every test run. A schema change fails the suite until it is updated |

---

## When you are stuck

**Do not** invent a workaround, relax a type, swallow an exception, add a `# type: ignore`,
or change a contract. A recorded problem is a good outcome. A silent workaround is the worst
one.

Say plainly what you tried, the exact error, what you think is wrong and what you need: a
decision, a missing constant, a corrected test. Then move on to what is not blocked.

---

## Style

Python 3.12, full type hints, Pydantic v2 at every boundary, small functions with one job.
The details are in **`docs/CODE-CONVENTIONS.md`**.

Comments and docstrings say **why**, not what. A test's docstring should say what breaking
it would mean for the person using this. Prose in this repository is written for somebody
who has just arrived and knows nothing, in plain words, with no em-dashes.
