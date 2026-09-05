# AGENTS.md

Instructions for any coding agent working in this repository. Detailed rules live in
`.agents/rules/`.

**This file is not loaded automatically by every tool.** Claude Code auto-loads `CLAUDE.md`, which
is short and points here; Gemini reads `GEMINI.md`, which does the same. Whichever one you were
given, read this file once at the start of a session. If it and `CLAUDE.md` ever disagree, this
file wins and `CLAUDE.md` needs correcting.

> **The build is finished.** This file used to say "open `plan/PROGRESS.md`, find the first task
> not marked done, do that task". That loop is over: 63 of the 67 tasks are `[x]`, and the four
> that are not are carried into `STATUS.md` and `BLOCKERS.md` rather than waiting in a
> queue. The work now is fixing, extending and verifying a system that exists.
>
> **Read `STATUS.md` first, every time.** The three files you work from are all at the
> repository root: **`STATUS.md`** (where things stand), **`BLOCKERS.md`** (what is open), and
> this file (the rules).
>
> **You do not work from `history/`.** It holds the old build brief, the old proposal and the
> 67-task plan, all finished and all describing nothing about the present. See
> `history/README.md`. Schemas, models and constants are in `docs/CONTRACTS.md`, which the
> source code cites by name and which is never edited.

---

## The five rules that override everything

1. **Never modify, weaken, delete or skip a test to make something pass.** Not a loosened
   assertion, not a widened tolerance, not an `xfail`, not a changed expected value. If a test
   looks wrong, that is a **blocker**: write it to `BLOCKERS.md`.

   If a test genuinely encoded a defect, you may correct it to assert the intended behaviour, but
   only after **measuring** the real behaviour first, and the reason goes in the commit message.
   Measure, then assert. Never assert, then measure.

2. **Never invent a number.** Every threshold comes from `src/wha/constants.py`. Every clinical
   figure comes from `data/knowledge/`. If a value you need does not exist, that is a blocker.
   **Never write clinical content from your own knowledge.** That is the one line this project
   must not cross. The agent may cite the corpus and nothing else.

3. **`history/`, `docs/CONTRACTS.md`, `research/` and `archive/` are read-only inputs.** The two
   files you keep current are `STATUS.md` and `BLOCKERS.md`, both at the repository root.

   **`data/knowledge/` is under change control, not read-only.** It used to be sealed because a
   person had written it. That was not true, and the header lines saying so have been removed.
   The reason that survives is the one that matters: a clinical number must not move without
   evidence. A figure there, or in `src/wha/constants.py`, may change when either the published
   source it cites can be quoted saying something different, or a measurement made here on real
   data, with the script committed, says something different. Not a hunch, not a better number
   from elsewhere, never your own knowledge. Every change goes in `docs/KNOWLEDGE-CHANGELOG.md`
   with the old value, the new value, and either the quoted sentence or the command that
   reproduces the measurement. If neither settles it, it is still a blocker.

4. **Always `uv run`.** Never bare `python`, never bare `pip`. On this machine `python` resolves to
   an unrelated project's virtual environment and your imports fail in confusing ways.

5. **Commit locally when work is done and verified. Never `git push`.** Never force, never rewrite
   history. No co-author line, no tool name, no em-dash.

---

## How to work now

```
1. Read STATUS.md. It is the only file guaranteed to describe the present.
2. Read BLOCKERS.md for what is open and why.
3. Research before deciding. Every clinical or agentic design choice needs a citation,
   or an explicit written statement that nothing settles it.
4. Do the work.
5. Run the suite and ruff ONCE, at the end, not after every edit.
6. Then USE THE PRODUCT. See below. This is not optional.
7. Commit, with the reasoning in the message. Never push.
```

**A green suite proves almost nothing here.** Every serious defect in this project was found by
using the dashboard, not by reading code and not by running tests. A full suite has passed while a
page crashed on load, while the safety floor was unreachable, while four subsystems had never once
executed, and while an import error made the Today page unopenable. **Finish by driving the real
interface with Playwright as an ordinary person**, on the real pages, and read what the screen
actually says.

**This is a single-user application.** One person, one phone. Do not build for multi-user.

---

## What this system is, in five lines

An overnight resting heart rate deviation opens an **episode**. A Bayesian belief over twelve
causes is updated from the sensor data, and an **EVSI policy** decides whether asking the person a
question is worth the interruption. A **deterministic safety floor** runs first and can only ever
raise urgency, never lower it, and an LLM can never overrule it. Every clinical sentence the agent produces must
**quote a span that is verbatim in a retrieved passage**, or it is stripped or labelled on
screen. That check proves the quoted span exists, **not** that the sentence around it says
what the source says; see `docs/ARCHITECTURE.md` Part 14. The dashboard is a
**client of the HTTP API** and holds no data logic, so it can be replaced by React.

---

## Where things are

| Path | What it is | Writable? |
|---|---|---|
| `STATUS.md` | **Where the project actually stands. Read first** | Yes, keep current |
| `BLOCKERS.md` | What is open, and why. **Live, at the root** | Yes, keep current |
| `docs/CONTRACTS.md` | Schemas, models, constants, service signatures. **Still binding**, cited from the source code, and never edited | No |
| `history/` | **Finished work. Describes nothing about the present.** The old build brief and proposal, the 67-task plan, the frozen build log, and `review-2026-09/`: the September review, its completed 34 item queue, and the audit that found seventeen of those items were not actually done. See `history/README.md` | No |
| `docs/` | The living design and disclosure documents | Yes, keep true |
| `data/knowledge/` | The clinical tables. Every number carries its own provenance | **See rule 3** |
| `data/corpus/` | Fetched external text, gitignored. Not authored here | Fetch only |
| `docs/KNOWLEDGE-CHANGELOG.md` | Every clinical figure changed, with the source quoted | Yes |
| `docs/DISCLOSURES.md` | What is unevidenced, and where the user is told | Yes, keep true |
| `src/wha/` | The code | Yes |
| `tests/` | Tests. You may add, never weaken | Add freely |
| `research/`, `archive/` | Evidence and an earlier weaker generation | No |

**`research/` is evidence, not design.** Read it to find a citation or a measured figure. Never
take an architectural conclusion from it: several documents are superseded and say the opposite of
the current design.

---

## Rules specific to this system

- **The medical content is cited or it is disclosed.** A clinical design choice must be backed by a
  study cited next to it, or stated plainly as unevidenced in **both** the docs and the dashboard.
  Never let an unevidenced choice look like an evidenced one.
- **The safety floor is deterministic and additive.** An LLM may raise urgency. Nothing an LLM says
  may lower it. Where a validated rule exists the model ELICITS the items and the rule DECIDES:
  today that is chest pain and the Marburg Heart Score, the only entry in `flag_presentations`.
  Everything else, every tier B rule and both vitals rules, still escalates on a phrase match,
  because no validated history-only rule covers it. "Never by keyword matching" was written here
  and was not true.
- **No data logic in `ui/`.** The dashboard calls the HTTP API through `wha.api.client`. If a page
  needs a number, add an endpoint. This is what makes Streamlit replaceable.
- **Retrieved external text is untrusted.** Scan it for injection before the model sees it, and
  name its source wherever it is shown. MedlinePlus is attribution-only.
- **Two subjects exist.** `me` holds the user's four real nights: **never overwrite or delete it**.
  `sim` is disposable. `.env` is deliberately pointed at `sim`; the original is `.env.phase4-backup`
  and restoring it points the system at a real person's watch. Do not, unless asked.

---

## Commands

```bash
uv sync                        # install
uv run pytest                  # the whole suite, about 5 minutes
uv run pytest tests/unit -q    # fast loop
uv run ruff check src tests    # lint
uv run ruff format src tests   # format
uv run wha doctor              # check every dependency, print pass/fail
uv run wha serve               # API on 8500, dashboard on 8501, scheduler
uv run wha demo run <scenario> --live   # one frozen scenario against the real model
uv run wha corpus build        # regenerate data/knowledge/corpus.yaml
uv run wha data fetch corpus   # fetch the MedlinePlus release
```

Tests run **offline** with `WHA_LLM_PROVIDER=cassette`, forced by an autouse fixture in
`tests/conftest.py` that overrides `.env`. If a test needs the network, it is wrong.

The eleven frozen scenarios take longer than ten minutes to run live back to back. Run them in two
batches. If a batch is killed part-way it leaves an orphaned `python.exe` holding `data/demo.sqlite`
open, and the next run fails with `WinError 32`.

---

## Traps that fail silently

| | |
|---|---|
| **Code that is never reached** | **The defect this codebase produces over and over.** Something defined, referenced by other code, and never executed: a `db` adapter behind twelve `hasattr` guards, a poller nobody registered, `retrieval_index` assigned `None`, a fetch function that returned "verified" and fetched nothing. **Assume this shape before assuming a logic error** |
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

---

## When you are stuck

Append to `BLOCKERS.md`:

```markdown
## <task-id> or <area> - <one line>
**What I tried:** ...
**What happened:** exact error text
**What I think is wrong:** ...
**What I need:** a decision, a missing constant, a corrected test
```

Then move on. **Do not** invent a workaround, relax a type, swallow an exception, add a
`# type: ignore`, or change a contract. A recorded blocker is a good outcome. A silent workaround
is the worst one. If a blocker is later resolved, say so **in place** and write what replaced it.

---

## Style, in one paragraph

Python 3.12. Full type hints. Pydantic v2 for every boundary. Small functions with one job. No
business logic in `ui/`. No database access outside `db/` and `service/`. Docstrings and comments
say *why*, not *what*, and a test's docstring should say what breaking it would mean for the
person using this. Match the surrounding code. **No em-dashes in any output, comment or commit
message.**

Commit messages: imperative, one line under 72 characters, then a body explaining **why** and what
was measured. **No attribution trailer, no co-author line, no tool name, no em-dash. Never push.**
