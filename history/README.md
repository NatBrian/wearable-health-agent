# history/ is FINISHED WORK. Nothing here describes the present.

Everything in this directory records how this system was designed and built. It is kept because
the reasoning is worth having and because several of its warnings turned out to describe real
defects. **None of it is a task list, a specification, or a description of what the code does
now.** If it disagrees with `STATUS.md`, `STATUS.md` is right.

| You want | Read |
|---|---|
| Where the project stands | **`STATUS.md`** at the repository root |
| What is open right now | **`BLOCKERS.md`** at the repository root |
| The rules you work under | **`CLAUDE.md`** and **`AGENTS.md`** at the repository root |
| Schemas, models, constants, service signatures | **`docs/CONTRACTS.md`** |

## What is in here

| Path | What it was |
|---|---|
| `HANDOFF.md` | The brief for writing this system from an empty `src/`, 1 September 2026. Its traps section is still worth reading; its status is three generations out of date |
| `HANDOFF-AGENTIC-FLOW.md` | The follow-up brief for the agentic work, 3 September 2026. All five of its items are done |
| `PROPOSAL.md` | The narrative design document written before the plan. **Superseded in fourteen documented ways** and never a thing to build from. Kept because it is the written artefact for the course |
| `plan/` | The 67-task build plan, its component designs, and the frozen build log `PROGRESS.md` |
| `review-2026-09/` | The end-to-end review of 4 and 5 September 2026, its work queue, and the audit of that queue. All four described a job that is now finished; see the table below |

## `review-2026-09/`, and why an audit is in here too

| File | What it was |
|---|---|
| `REFINEMENT-PLAN.md` | The 34 item work queue the review produced. **All 34 are done.** Read it for why a change was made, never as a list of things to do |
| `DESIGN-REVIEW.md` | The verdict on every component, 5 September 2026. Its detection figures are **superseded**: they were measured while the detector ran a looser alert rule than the one it cited, and the block carries a note saying so |
| `EVIDENCE-LOG.md` | Every citation the review fetched, with the load-bearing sentence quoted. Still the best record of what was checked against which paper, but its headline figures are superseded the same way |
| `AUDIT-2026-09-05.md` | Fifteen independent agents checking whether the 34 items were really done. **Seventeen came back partial**, two of them production-breaking, in work that had been reported as complete with a green suite behind it. Kept unedited on purpose: a verdict quietly revised afterwards is not a verdict |

The audit is the one to read if you only read one. It is the clearest evidence in this
repository for the rule at the top of `CLAUDE.md`: a passing test suite is not evidence that
the code runs.

`plan/02-contracts.md` used to live here and is now `docs/CONTRACTS.md`, because the source code
cites it by name and it is still binding.

## This is not `archive/`

`archive/` holds an **earlier, weaker generation** of this project, including figures that were
found under audit to be fabricated. Never read it as fact. This directory is different: it is the
real design history of the current system, accurate for the moment it was written.

**All of this directory is read-only.**
