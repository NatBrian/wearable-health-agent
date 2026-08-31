# GEMINI.md

**This file exists so the instructions load whichever filename convention your version uses.**

## Read these two files, in this order, before doing anything

1. **`HANDOFF.md`** at the repository root. It tells you what this project is, what state it is in,
   and exactly what to do. It assumes you have no prior knowledge.
2. **`AGENTS.md`** at the repository root. The hard rules, always in context.

Then the four files `HANDOFF.md` section 2 names under `.agents/rules/`.

## The three rules that matter most, in case nothing else loads

1. **Never modify, weaken, delete or skip a test to make something pass.** If a test looks wrong,
   that is a blocker: record it in `plan/BLOCKERS.md` and move to the next independent task.
2. **You are here to write code, not to plan.** The implementation plan is finished and frozen in
   `plan/`. **Do not build from `PROPOSAL.md`**, which predates it and is superseded in fourteen
   documented ways.
3. **Never invent a number.** Thresholds come from `src/wha/constants.py`, clinical figures from
   `data/knowledge/`. If a value is missing, that is a blocker.

## Start

Open `plan/PROGRESS.md`, find the first row not marked `[x]`, open only that task file under
`plan/tasks/`, and do it. There are 67 tasks. Commit after each one. Never push.
