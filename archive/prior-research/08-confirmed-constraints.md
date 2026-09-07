# 08. Confirmed Constraints and What They Change

**Status:** Phase 1 output, updated with answers received 2026-08-30.
**Date:** 2026-08-30

---

## Confirmed

| # | Constraint | Source |
|---|---|---|
| C1 | This is **a healthcare AI course project**, and simultaneously wanted as a **personal tool** and a **portfolio piece**. Three audiences. | Answered |
| C2 | This is a **team project**, not solo. Team size and work split not yet confirmed. | Answered |
| C3 | The team owns wearables: **Samsung Galaxy Watch** (the author) and **WHOOP** (a teammate). Which, if either, is used is still open. | Answered |
| C4 | Effort budget: **6 to 8 hours per day, roughly 90 to 110 hours** over the two weeks (per person, assumed). | Answered |
| C5 | **Live real-time behaviour is expected** in the demonstration. Replay alone is not sufficient. | Answered |

---

## What each constraint changes

### C1: three audiences, one artifact

Coursework, personal tool, and portfolio pull in mostly compatible directions but not identically:

| Audience | Rewards | Punishes |
|---|---|---|
| the course marker | Clinical grounding, evaluation rigour, correct use of the course's concepts, honest limitations | Unsupported claims, decorative components, no evaluation |
| Personal use | Actually running on your own device, low friction, useful output | Anything that only works on a replayed public dataset |
| Portfolio | Legibility, a visible working demo, a crisp one-sentence claim | A notebook with no artifact, or a stack with no story |

The union is achievable: a system that runs live on the team's own devices (personal + portfolio) and is evaluated properly on public cohort data (course project). But note that this **splits the data strategy in two on purpose**, which is now a design requirement rather than an option. See gate G1 below.

**Still needed, and it is the highest-value single input to this project: the course requirements.** If it names required techniques, weightings, page limits, or a specific clinical framing, several decision gates close immediately and correctly. Please provide it before Phase 2 starts.

### C2: it is a team

Changes the plan structurally, not just in size:

- Work can be parallelised, which makes a broader system feasible than a solo build at the same hours.
- Parallel work needs **clean interfaces defined up front**, otherwise integration eats the second week. Component boundaries move from being a design nicety to a scheduling necessity.
- Two device ecosystems in the team is a data-access opportunity and a harmonization cost (see C3).
- 90 to 110 hours per person times the team size is a much larger envelope than the solo assumption in doc 04. The research phase does **not** scale with team size, though: it stays at two to three days, and it can be run in parallel across tracks.

**Still needed:** team size, and whether members have distinct strengths that should shape the split.

### C3: two real devices, two ecosystems

This is a genuine asset and it reopens something the archived work dismissed outright.

**What it enables:**
- Live ingestion from real hardware, which C5 now requires anyway.
- Retrospective confounder annotation on the team's own historical data, which is the only realistic route to confounder ground truth (doc 02, U2). Both members know when they drank, trained hard, slept badly, travelled or were ill.
- A cross-device angle: two different vendors computing nominally the same metrics with different proprietary definitions.

**What it does not enable, and this needs saying plainly:** with two people wearing devices for two weeks, N is 2 and the probability that either gets a well-timed acute infection is low. **The team's own data cannot serve as the evaluation set for detection performance.** It is a live demonstration substrate and, if the historical export goes back far enough, a small annotated case series. Detection metrics still need a public cohort. This is the two-track data strategy that C1 already implied.

**New unknowns raised (added to doc 02 as Tier 0 and Tier 1 items):**

- **U18. Samsung Galaxy Watch data access.** Which channels are actually exposed, through which path (Samsung Health app export, Health Connect on Android, Samsung Health SDK / Health Platform, or Privileged SDK), at what granularity, and with what gating? Specifically: does it expose HRV, skin temperature, respiratory rate, or only heart rate, sleep and activity? Watch model matters and needs to be recorded.
- **U19. WHOOP data access.** WHOOP is reported to have a self-serve developer API with OAuth. Which endpoints, which metrics (recovery, HRV, resting HR, respiratory rate, skin temperature delta, sleep stages), what history depth, what rate limits, what licence terms for a course project.
- **U20. True end-to-end latency, body to API.** This is now critical and is treated in C5 below.
- **U21. Cross-device metric harmonization.** Two vendors define resting HR, HRV and sleep stages differently, with proprietary and undocumented pipelines. Is this a liability to be managed (normalize per-person and never compare across devices) or a deliberate feature (a device-agnostic layer)? It cannot be ignored, because the team has both.

All four are device-access research, which is now **in scope** for Phase 2, where doc 03 had provisionally marked vendor API mechanics as over-weighted. That judgement is superseded: it was made on the assumption of no real devices and no live requirement. Both assumptions are now false.

### C4: 90 to 110 hours per person

Comfortable. It supports a real evaluation plus a working live demo plus ablations, which the tighter budgets would not have. It does not support building everything in the archived architecture, and the cut list in Track G.3 still gets written in advance.

Research phase allocation is unchanged at two to three days. With a team, run the tracks in parallel rather than extending the calendar.

### C5: live real-time is expected

The most consequential answer, and it creates a tension that must be resolved honestly rather than papered over.

**The tension.** The physiological evidence points toward the illness signal living in **nightly, sleep-window measurements**, where motion, meals, posture and stress noise are absent. But a nightly decision cadence produces one decision per day, which is not something an audience can watch happen. Meanwhile consumer wearables do not stream continuously to the cloud: they sync in batches, on their own schedule, with latency measured in minutes to hours.

So "real-time" has three possible honest meanings here, and which one is intended must be settled:

| Meaning | What it involves | Cost |
|---|---|---|
| **A. Live ingestion** | Data really arrives from a real device during the demo, whatever its latency. The system reacts when it arrives. | Real device integration; latency determined by the vendor, not by us |
| **B. Live intraday monitoring** | The system continuously processes intraday signal and can react within the day, with a separate nightly illness decision | Two cadences, more surface area, more false-alarm exposure intraday |
| **C. Live-looking demonstration** | Time-warped replay that visibly runs, updates and reacts on screen | Cheap, but it is a presentation device and should be labelled as one |

These are not mutually exclusive. A defensible combination is real live ingestion (A) for the personal-use and portfolio audiences, an intraday deterministic safety watcher plus a nightly illness decision (a constrained form of B), and time-warped replay (C) used to show multi-week illness episodes that cannot be demonstrated in a fifteen-minute presentation. But that is a design proposal, and design is Phase 3. For now it is recorded as the resolution space for gate G2.

**U20 becomes a Tier 0 unknown.** Before promising real-time anything, measure the actual body-to-API latency for the Samsung watch and for WHOOP. If the honest answer is "data appears 30 to 90 minutes after the fact, in batches," then that is what "real-time" means in this project and the claim must be worded accordingly. Overclaiming latency in a health-monitoring system is exactly the kind of thing a reviewer will probe.

---

## Consequences for the decision gates

| Gate | Change |
|---|---|
| **G1 Data foundation** | Narrowed toward **hybrid**: public cohort for evaluation, team's own devices for live demonstration and (if history is deep enough) an annotated case series. Still open on which public cohort and how deep the personal history goes. |
| **G2 Decision cadence** | Constrained by C5. Pure nightly rollup no longer satisfies the requirement on its own. Resolution space is now the A/B/C table above. Still open. |
| **G3 Detection engine** | Unchanged. |
| **G4 Where agency lives** | Unchanged, and still the contribution-bearing gate. |
| **G5 Agent-computer interface** | Unchanged. |
| **G6 Retrieval and grounding** | Likely to be settled by the course requirements. Waiting on it. |
| **G7 Evaluation strategy** | Strengthened toward option D: public-cohort detection metrics, plus a semi-synthetic policy benchmark with sensitivity analysis, plus a real annotated case series from the team's own data. |
| **G8 Output contract and safety** | Raised in importance. The system will run on real people (the team), not only on a dataset, which makes the safety envelope a live concern rather than a paper one. |
| **G9 Demonstration harness** | Constrained by C5. Notebook-plus-figures is ruled out. An interactive harness is now required, and its cost must be budgeted rather than minimized. |
| **G10 Target condition** | Unchanged, and still to be answered by the research. Note that C1's personal-use goal mildly favours a year-round framing over a purely infection-specific one, since infection episodes are rare and a tool that is silent 350 days a year is not a tool anyone keeps using. |

---

## Additions to the research checklist

New Track H, to run in parallel with Track A. This work did not exist before C3 and C5.

| # | Item | Type | Unblocks |
|---|---|---|---|
| H.1 | Record exact device models and firmware for the Samsung watch and the WHOOP unit | [ASK] | U18, U19 |
| H.2 | Enumerate every data-access path for the Samsung watch. For each: channels exposed, granularity, history depth, auth model, gating, and whether an Android app is required | [SPIKE] | U18, G1 |
| H.3 | Same for WHOOP: endpoints, metrics, history depth, rate limits, auth, and terms of use for an academic project | [SPIKE] | U19, G1 |
| H.4 | **Measure** end-to-end latency for both: wear the device, note wall-clock time, and record when the data actually becomes retrievable. Do not take a vendor's word for it | [SPIKE] | U20, G2, G9, and the honesty of the real-time claim |
| H.5 | Export the deepest available personal history from both devices and run doc 04 items A.2 through A.5 on it | [SPIKE] | U4, G1, G7 |
| H.6 | Compare the two devices' metric definitions where they overlap, and decide whether cross-device harmonization is a managed liability or a stated feature | [SPIKE] | U21 |
| H.7 | Both team members reconstruct a retrospective annotation timeline over their exported history: illness episodes, heavy drinking, hard training, poor sleep, travel, vaccination | [ASK] | U2, G7, the confounder ground-truth problem |

H.4 and H.7 are the two highest-value items in this track. H.4 determines whether the real-time claim is honest. H.7 is the cheapest available partial answer to the circularity problem that doc 00 identified as the sharpest objection to the whole project.

---

## Still outstanding

1. **The the course assignment brief and requirements.** Highest-value remaining input.
2. **Team size and how the work will be split.**
3. **Device models, and how far back each member's exportable history goes** (H.1, H.5).
4. Doc 07 questions Q6 (LLM provider and budget), Q7 (compute, GPU availability), Q10 (attachment to the infection framing), Q11 (anything already known to be wanted in the system).
