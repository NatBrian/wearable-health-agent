# CLAUDE.md

**Read `STATUS.md` before doing anything.** It is the only file guaranteed to describe the
present. Then `BLOCKERS.md` for what is open, and `AGENTS.md` for the full rules.

Three files at the repository root are live: **`STATUS.md`**, **`BLOCKERS.md`**, **`AGENTS.md`**.

**Everything in `history/` is finished work and describes nothing about the present.** That is
the old build brief, the old proposal, and the 67-task plan, all superseded. Read
`history/HANDOFF.md` for the traps it records if you like, never as a list of things to do. If
anything in `history/` disagrees with `STATUS.md`, `STATUS.md` is right.

Schemas, models, constants and service signatures are in **`docs/CONTRACTS.md`**, which the source
code cites by name. It is still binding and it is never edited.

---

## What this is

A single-user wearable health early-warning agent. An overnight resting heart rate deviation
opens an **episode**. A Bayesian belief over twelve causes is updated from sensor data, and an
**EVSI policy** decides whether asking the person a question is worth the interruption. A
**deterministic safety floor** runs first and can only raise urgency, never lower it. Everything
the agent asserts must be **grounded in a cited passage** or it is stripped or labelled on
screen. The dashboard is a client of the HTTP API and holds no data logic.

---

## The rules that must survive even if nothing else loads

1. **This is a medical system. Never write clinical content from your own knowledge.** Every
   clinical design choice is backed by a cited study, or stated plainly as unevidenced in **both**
   the docs and the dashboard. A missing number is a blocker, not a gap to fill. The agent may
   cite the corpus and nothing else.
2. **Never weaken a test to make it pass.** If a test genuinely encoded a defect you may correct
   it, but only after **measuring** the real behaviour first, and the reason goes in the commit.
   Measure, then assert. Never the reverse.
3. **A green suite proves almost nothing here.** Every serious defect in this project was found by
   using the dashboard as an ordinary person, not by reading code. **Finish by driving the real
   interface with Playwright.** Full suites have passed while a page crashed on load, while the
   safety floor was unreachable, while four subsystems had never once executed, and while an
   import error made the Today page unopenable.
4. **The recurring defect here is code that exists, is referenced, and is never reached.** Assume
   that shape before assuming a logic error.
5. **Always `uv run`.** Bare `python` resolves to an unrelated project's virtual environment.
6. **Never `git push`.** Commit locally. No co-author line, no em-dash, anywhere.
7. **Single user.** One person, one phone. Do not build for multi-user.
8. **Subject `me` holds the user's four real nights. Never overwrite or delete it.** `sim` is
   disposable. `.env` is deliberately pointed at `sim`; restoring `.env.phase4-backup` points the
   system at a real person's watch, so do not, unless asked.
9. **Read-only:** `data/knowledge/`, `history/plan/`, `research/`, `archive/`, `history/PROPOSAL.md`,
   `history/HANDOFF.md`. One narrow exception, granted 4 September 2026: a clinical figure may be
   corrected **only** where the published source it cites can be quoted saying something
   different, and every such change goes in `docs/KNOWLEDGE-CHANGELOG.md` with the quoted
   sentence. If the source does not settle it, it is a blocker.
10. **Research first, then plan, then build.** Do not reason a clinical or agentic design choice
    from first principles when a study exists. Cite what you find, next to what it justifies.

---

## Working commands

```bash
uv run pytest                  # whole suite, about 5 minutes. Run ONCE at the end
uv run ruff check src tests    # lint
uv run wha doctor              # dependency and knowledge-table check
uv run wha serve               # API on 8500, dashboard on 8501, scheduler
uv run wha demo run <scenario> --live   # one frozen scenario against the real model
```

The eleven frozen scenarios take over ten minutes live; run them in two batches. A killed run
leaves an orphaned `python.exe` holding `data/demo.sqlite` open, and the next run fails with
`WinError 32`.

**`AGENTS.md` has the rest**: the traps table, the blocker format, the layout, and the style
rules. Read it once at the start of a session.
