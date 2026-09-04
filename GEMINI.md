# GEMINI.md

**This file exists so the instructions load whichever filename convention your version uses.**
Claude Code reads `CLAUDE.md`, Gemini reads this one, and both point at `AGENTS.md`, which holds
the full rules.

## Read these two files, in this order, before doing anything

1. **`STATUS.md`** at the repository root. **Where the project actually stands**, which is the only
   thing guaranteed to be current. Then `BLOCKERS.md` for what is open and why.
2. **`AGENTS.md`** at the repository root. The hard rules, always in context.

**You do not work from `history/`.** It holds the old build brief, the old proposal and the
67-task plan: all finished, all describing nothing about the present. Read `history/HANDOFF.md`
for the traps it records, never as a list of things to do. Schemas, models and constants are in
`docs/CONTRACTS.md`, which the source code cites by name and which is never edited.

## The four rules that matter most, in case nothing else loads

1. **Never modify, weaken, delete or skip a test to make something pass.** If a test genuinely
   encoded a defect you may correct it, but only after measuring the real behaviour first, and the
   reason goes in the commit. Measure, then assert.
2. **Never invent a number, and never write clinical content from your own knowledge.** Thresholds
   come from `src/wha/constants.py`, clinical figures from `data/knowledge/`, and health information
   from the cited corpus. A missing value is a blocker, not a gap to fill.
3. **A green test suite proves almost nothing here.** Every serious defect in this project was found
   by using the dashboard as an ordinary person. Finish by driving the real interface, not by
   reading code.
4. **Never `git push`.** Commit locally. No co-author line, no em-dash.

## Start

Read `STATUS.md`, pick up the open item you were asked about, research before deciding, do the work,
run the suite and ruff once at the end, then use the product and check the screen says what you
think it says.
