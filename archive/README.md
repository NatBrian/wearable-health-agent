# archive/ is FINISHED WORK. Nothing here describes the present.

Everything in this directory records how this system was designed and built. It is kept
because the reasoning is worth having, and because several of its warnings turned out to
describe real defects. **None of it is a task list, a specification, or a description of
what the code does now.** If anything here disagrees with `README.md`, `README.md` is right.

**This folder was called `history/` until 7 September 2026.** Documents inside it still
refer to each other by that name. Read `history/x` as `archive/x`.

| You want | Read |
|---|---|
| What this project is, and where everything lives | **`README.md`** at the repository root |
| The rules you work under | **`AGENTS.md`** at the repository root |
| What the system cannot do | **`docs/DISCLOSURES.md`** |
| Schemas, models, constants, service signatures | **`docs/CONTRACTS.md`** |

## What is in here

| Path | What it was |
|---|---|
| `HANDOFF.md` | The brief for writing this system from an empty `src/`, 1 September 2026. Its traps section is still worth reading; its status is three generations out of date |
| `HANDOFF-AGENTIC-FLOW.md` | The follow-up brief for the agentic work, 3 September 2026. All five of its items are done |
| `PROPOSAL.md` | The narrative design document written before the plan. **Superseded in fourteen documented ways** and never a thing to build from. Kept because it is the written artefact for the course |
| `plan/` | The 67-task build plan, its component designs, and the frozen build log `PROGRESS.md` |
| `review-2026-09/` | The end-to-end review of 4 and 5 September 2026, its work queue, and the audit of that queue. All four described a job that is now finished; see the table below |
| `screenshots-2026-09-06/` | The four dashboard screenshots that `README.md` used until 7 September 2026, superseded when the record screen went from 20 steps to 21. The current ones are in `docs/screenshots/` |

## `review-2026-09/`, and why an audit is in here too

| File | What it was |
|---|---|
| `REFINEMENT-PLAN.md` | The 34 item work queue the review produced. **All 34 are done.** Read it for why a change was made, never as a list of things to do |
| `DESIGN-REVIEW.md` | The verdict on every component, 5 September 2026. Its detection figures are **superseded**: they were measured while the detector ran a looser alert rule than the one it cited, and the block carries a note saying so |
| `EVIDENCE-LOG.md` | Every citation the review fetched, with the load-bearing sentence quoted. Still the best record of what was checked against which paper, but its headline figures are superseded the same way |
| `AUDIT-2026-09-05.md` | Fifteen independent agents checking whether the 34 items were really done. **Seventeen came back partial**, two of them production-breaking, in work that had been reported as complete with a green suite behind it. Kept unedited on purpose: a verdict quietly revised afterwards is not a verdict |

The audit is the one to read if you only read one. It is the clearest evidence in this
repository for the rule at the top of `AGENTS.md`: a passing test suite is not evidence that
the code runs.

`plan/02-contracts.md` used to live here and is now `docs/CONTRACTS.md`, because the source code
cites it by name and it is still binding.

## One warning about `prior-generation/`

`prior-generation/` holds an **earlier, weaker attempt** at this project, including figures
that an audit found to be fabricated. Never read it as fact. The rest of this directory is
different: it is the real design history of the current system, accurate for the moment each
document was written.

**All of this directory is read-only.**

---

## Added 7 September 2026, when the project finished

The repository was reorganised so that somebody arriving with no context reads `README.md`
and nothing else to start. These files were live during the build and describe work that has
ended. **Nothing here describes the present.**

| Moved here | What it was | Why it is not live |
|---|---|---|
| `session-logs-2026-09/STATUS.md` | The running "what is true right now" file, updated every session | The project is finished. `README.md` carries the current state now, and two files claiming to describe the present is how they drift apart |
| `session-logs-2026-09/BLOCKERS.md` | Open problems and what was measured about each | Every entry is closed. The live record of what this system cannot do is `docs/DISCLOSURES.md`, which is enforced by tests |
| `session-logs-2026-09/HANDOVER.md` | Notes for somebody taking the project over cold | Superseded by `README.md`, which is now written for exactly that reader |
| `session-logs-2026-09/superpowers/` | Specs and implementation plans for the September work: the dashboard overhaul, the symptom timeline, the demo film, the claims cleanup, and the modularity work of 8 September | Each plan describes a job that is done. They are worth reading for WHY a thing was built, never as a queue of work. The modularity plan is the one still referenced from `README.md`, because it records why the current module boundaries are where they are |
| `prior-research/` | The research done before any code was written: problem formulation, unknowns, landscape, decision gates | The decisions it fed are made and are recorded where they apply |
| `prior-generation/` | An earlier attempt at this project, from 30 August 2026, and its research | A different project that this one replaced |

**The reading rule for this whole folder has not changed.** It is a record, not a queue. If
anything here disagrees with `README.md`, `README.md` is right. If you are asked to
"continue" with no further detail, ask what is wanted rather than mining these files for
work that was finished months ago.
