# research/

**Evidence, not design.**

Nine investigations, roughly 126,000 words and 2,100 citations, plus working notes 00 to 15. Every
document carries explicit `UNVERIFIED` flags where a claim could not be sourced.

---

## If you are a coding agent

**Read this directory only to find a number or a citation.** Never take a design decision from it.

Several of these notes are **superseded and state the opposite of the current design**:

| File | Stale claim | Reality |
|---|---|---|
| `08-confirmed-constraints.md` | A team of four, a second device, live real-time monitoring | Solo. One device. Nightly cadence |
| `13-galaxy-watch5-data-reality.md` | "We should build on the manual export" | The export is ruled out. See `plan/04-decisions.md` D-105 |
| `14-automatic-data-access-and-samsung-vitals.md` | Recommends an Android reader plus a Dockerised stack | Neither is used |

**The implementation contract is `plan/`.** Design comes from there and nowhere else.

---

## What is genuinely useful here

| File | Use it for |
|---|---|
| `findings/F8-confounders-and-active-sensing.md` | Every effect size, base rate and temporal profile behind `data/knowledge/causes.yaml`, with evidence grades |
| `findings/F6-detection-datasets-evaluation.md` | Metric definitions, the small-sample protocol, and the list of metrics that must never be reported |
| `findings/F7-agentic-governance-rag.md` | Audit schema provenance, injection defences ranked by evidence, medical corpora and their licences |
| `findings/F4-foundation-models.md` | Why Chronos and not the alternatives |
| `15-project-hermes-read.md` | The closest prior art, and what it costs the novelty claim |

Note the verification flags. `[verified]` means a primary source was opened. `[secondary]` means a
search summary was read and the number should be re-checked before it is relied on.
