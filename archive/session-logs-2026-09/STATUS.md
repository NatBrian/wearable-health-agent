# STATUS: read this first

**Last updated:** 7 September 2026
**Branch:** `feat/agentic-early-warning-system` (nothing has ever been pushed)

---

## THERE IS WORK IN PROGRESS. READ THIS BEFORE ANYTHING ELSE.

**A demo film is being made, and building it has found six defects in the product.** The
plan and the running list of findings are in
`docs/superpowers/plans/2026-09-07-demo-film.md`, the design in
`docs/superpowers/specs/2026-09-07-demo-film-design.md`. Read the findings table before
touching the safety floor or the symptom timeline.

**A seventeen day timeline has been built and every day matched its prediction.** Subject
`demo`, in `data/demo_film.sqlite`, which is NOT `data/demo.sqlite` (that belongs to the
eleven frozen scenarios). 27 generated prologue nights, then the seven usable real nights
copied read-only out of `me`, then 7 to 23 September: an illness, a relapse, a recovery and
a chest pain conversation. Snapshots after every day are in `data/demo-snapshots/`.

**Rebuild or re-film it with:**

```bash
uv run python tools/demo_film/serve_watch.py            # terminal 1
uv run python tools/demo_film/build.py --stage seed     # terminal 2
uv run python tools/demo_film/build.py --stage story    # hits the real model
uv run python tools/demo_film/preflight.py              # look at the frames
uv run python tools/demo_film/film.py                   # record the live scenes
uv run python tools/demo_film/cards.py && uv run python tools/demo_film/assemble.py
```

`build.py` states each day's predicted outcome BEFORE running it and halts on the first
mismatch. That is the point of it: a simulation described afterwards always looks like it
worked. It halted five times, and four of those were real defects.

**Rules that hold while this runs:**

- Subject `me` holds the user's real watch data. The film opens it READ-ONLY, once.
- The parked `sim` simulation is untouched. `tools/mock_watch.py` now honours
  `WHA_MOCK_STATE`, so the film has its own cursor file and cannot trample it.
- `WHA_CLOCK_OFFSET_DAYS` shifts the whole system's idea of today. It is unset in
  production, `wha doctor` reports it as a warning when it is not, and `build.py` clears it
  when it exits.

## What building the film found, in the product

Six defects, none of which the test suite could have caught, and two of them in code
written on 7 September to fix a different silence.

1. **The symptom follow-up fired ten times in three minutes**, consumed the whole
   conversation depth budget in one tick and closed an investigation as UNRESOLVED on its
   second day. On a real phone that is ten notifications.
   `SYMPTOM_FOLLOWUP_MIN_NIGHTS_APART` was declared, documented and read by nothing, and
   the per-episode cap could not cover for it because follow-up rows are keyed by night, so
   the number it reads is pinned at one all day.
2. **Saying "I feel better" recorded MORE symptoms than saying nothing.**
   `observe_and_check` wrote every id in `triggered_flags`, which deliberately includes
   flags carried from earlier nights, so every message re-asserted every symptom still in
   the window and a symptom could never expire.
3. **"The fever has gone" was read as a report of fever.** The negation guard only looked
   backwards, so "no fever" worked and the commonest way of saying a symptom stopped did
   not.
4. **A quiet run closed an investigation while a person was reviewing its conclusion.**
   The human checkpoint was skipped and nothing recorded that it had been.
5. **The escalation that reaches the phone was not written down.** "You should see a
   doctor today" arrived on a real phone leaving no trace of delivery, in a system whose
   record screen says everything it does is written down as it happens.
6. **`README.md` promised an Audit Journal page that does not exist**, and `EVALUATION.md`
   carried the same stale name from its generator.

## 7 SEPTEMBER 2026: the symptom timeline landed. Two of those three decisions are closed.

The safety floor could not see time passing. `check_red_flags_deterministic` accepts a
`symptom_history` argument and **no production caller ever passed it**, so the persistence
half of Tier B had never fired for any symptom in the life of this project: five nights of
a worsening fever through the real path produced five refusals to escalate. "Two or more
co-occurring" separately meant "in the same message", so a fever on Monday and vomiting on
Tuesday counted as two unrelated singletons. Neither threshold in `red_flags.yaml` changed.
They simply began to be read.

Four silences fixed, each measured before and after:

- Tier B persistence now fires. Six symptoms could not escalate alone; now they can.
- Co-occurrence spans nights, so an illness whose symptoms evolve is seen.
- An outstanding symptom **overrides the value-of-asking arithmetic** and forces a
  follow-up. EVSI scores how much an answer moves the belief across twelve causes, so once
  a cause is settled asking is worth nothing by construction: the more certain the system
  became that somebody was ill, the less reason it had to speak to them.
- Green nights no longer close an investigation as benign while a symptom is outstanding,
  and a time-based close now says something instead of nothing.

Read `docs/DESIGN-SYMPTOM-TIMELINE.md` for the evidence, which is the part worth your time:
dengue's critical phase begins at defervescence, Faget's sign, and Radin's 79-day recovery
lag together mean **a green reading is evidence about the reading, not about the person**.

**Nothing is waiting on the user. All decisions are made.**

The dengue test was run live against the real model on 7 September. It escalated correctly
(same_day on fever, vomiting and poor intake) and, unprompted, asked about mucosal bleeding,
a WHO dengue warning sign and a tier A rule it was not told to seek. It never said dengue,
exactly as predicted before the run, because `corpus.yaml` has no dengue passage and
grounding requires verbatim containment.

Two decisions closed on the back of it, both the user's:

- **No illness-specific content in the corpus.** Accepted with its cost: the same-day
  routing for a dengue warning-sign picture may be under-triaged for that illness.
  Disclosed on **Today** under the verdict.
- **No looser phrase matching.** Tier C stays the backstop, and its findings now reach the
  symptom timeline, so a symptom only the model spotted persists instead of counting once.

**The simulation is stopped.** `sim` sits at 9 September with investigation
`ep_20445aee7610` still OPEN. Its timeline now carries dizziness, fever and vomiting: the
last two came from the dengue test, which wrote into the live database on purpose. Backup
before that write is `data/backups/wha-before-dengue-test-20260907-021427.sqlite`.

Closed since the last update: dizziness (it needed **tracking**, not a red flag, which
asserts no threshold), the forced follow-up (done, as a rule), and sustained yellow nights,
which were tried on an archive of past wearable data and found to add nothing. See
`experiments/detection/`.

## Documentation, rewritten 7 September 2026

`README.md` was rewritten for somebody arriving cold: a document map, a one-page version of
the architecture, a **"design decisions, and why"** section naming the six questions already
settled by measurement so they are not re-argued, and a **"working on this codebase"** section
listing the rules that are enforced by tests rather than by convention. Nothing was dropped;
every heading and paragraph from the old version was checked mechanically.

`USER-GUIDE.md` is **new**, for the person whose health this is, with seven screenshots taken
from the running system. It documents three things that were nowhere before: when the AI
actually fires, how Telegram works end to end, and how to tell a sourced reply from an
unsourced one.

The four screenshots `README.md` used until now are superseded (the record screen went from
20 steps to 21) and are in `history/screenshots-2026-09-06/`.

Verified on 7 September 2026, all re-run rather than remembered:

| Check | Result |
|---|---|
| `uv run pytest -n auto` | **782 collected, all passing, 1 skipped**, about five minutes |
| `uv run ruff check src tests` | clean |
| `uv run ruff format --check src tests` | clean |
| `uv run wha doctor` | no `fail` rows, and a new `clock` row that warns when the demo offset is set |
| Dashboard, all five screens | driven with Playwright through the whole demo timeline, and recorded |
| Seventeen day demo timeline | every day matched the outcome predicted before it ran |
| Eleven frozen scenarios | 11 of 11 live, 5 September, not re-run since |
| Telegram | real questions, a real same-day escalation and real outcomes, on a real phone |
| The film | `docs/demo/wha-demo.mp4`, 29 minutes 12 seconds, 24 chapters |

`pytest-xdist` is installed: run `-n auto`. The suite takes about five minutes in parallel
against nearly eight serial, and the interface tests forty-five seconds against ninety.

## What the simulation found, and what it cost to find

Fifteen defects, none of which the test suite could have caught, because every one of them
needed the product to be used. The full list is in
`docs/superpowers/plans/walkthrough-2026-09-06.md` and in the commits from 6 and 7
September. The ones worth knowing about before touching anything:

- **Typing an answer was recorded as refusing to answer.** Tapping a button worked. A reply
  typed on a phone reached the graph as `declined` with the person's words as a footnote, so
  the belief never moved.
- **An episode could sit at "waiting for your answer" with no question.** `node_ask` parks
  the row before interrupting; when the policy then chose to observe, nothing set it back.
- **Escalation was once per investigation, ever.** Somebody who got worse, or who stayed far
  outside their own range for days, heard nothing after the first message. Both now speak.
- **The record claimed steps had not run while they were running**, because the agent only
  writes its trace when it concludes.
- **Every screen but Home showed a different person**, and the History chart drew a RED
  night in the same colour as the line labelled with the person's own heart rate.

## The dashboard was rewritten on 6 September 2026

`src/wha/ui/` was deleted and rewritten for a reader with no engineering and no medical
background. Nothing in the deterministic half, the agentic half or the safety floor changed.

What is new behind it: `service/pipeline.py` assembles a whole night's journey from what the
nightly job already stored, so **every** night has a step-by-step account, including the
sixty-eight of seventy-two where no investigation opened. Two endpoints serve it. A step with
no recorded timestamp reports none, and a step nobody wrote down reports `unrecorded` rather
than `skipped`.

What is new in front: one place for styling, one for copy, one for formatting; a top bar that
says what a failure stops rather than naming a component; a Today screen where every number
carries what it is and a link to the step that produced it; citations that open to the whole
passage with the quoted span marked; a History table of six columns; and a record screen whose
first tab is the night drawn as twenty clickable steps.

The design is in `docs/superpowers/specs/2026-09-06-dashboard-overhaul-design.md`, the plan in
`docs/superpowers/plans/2026-09-06-dashboard-overhaul.md`, and **the nine defects that only
appeared when the interface was actually used** are in
`docs/superpowers/plans/walkthrough-2026-09-06.md`. Two of those nine were serious: every
screen but Home showed a different person, and the History chart drew a RED night in the same
colour as the line labelled with the person's own heart rate.

**If somebody asks you to "continue", ask them what they want.** There is no obvious next
task, and inventing one would be worse than asking.

**New here with no context? Read `HANDOVER.md` first.** It is five minutes and covers the
two mistakes everyone makes in this repository.

**Two known imperfections are open, and both need a human decision rather than code.** They
are the last two entries in `BLOCKERS.md`, they are disclosed to the user on screen, and
neither breaks anything: a night whose leading explanation is a bad sensor reading still
reports as possible illness, and a cited sentence can still misdescribe the passage it cites.

---

## There is no open work queue. Here is where to look for what.

The system was reviewed end to end on 4 and 5 September 2026, producing a 34 item plan. That
plan was executed, **audited, found to be seventeen items short of done, and finished.** All
of it is now finished work and lives in `history/review-2026-09/`.

**Live documents, which describe the present:**

| Document | What it is |
|---|---|
| `STATUS.md` | This file. Where things stand |
| `BLOCKERS.md` | What is open and why. Append, never rewrite |
| `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` | The rules you work under |
| `docs/ARCHITECTURE.md` | How the whole system works, for someone who has never seen it |
| `docs/CONTRACTS.md` | Schemas, models, constants. Binding, and never edited |
| `docs/DISCLOSURES.md` | Every limitation, its evidence, and the screen it appears on |
| `docs/KNOWLEDGE-CHANGELOG.md` | Every clinical figure changed, with the quoted source or the command |
| `docs/DESIGN-*.md` | Why four specific design choices are what they are, each with its measurement |
| `experiments/detection/detection-results.json`, `EVALUATION.md` | The published accuracy figures |
| `docs/RUNBOOK-SIMULATION.md` | Taking it from a clean checkout to a live watch |

**Finished work, in `history/review-2026-09/`:** the 34 item queue, the component-by-component
review, the citation log, and the audit. Read them for why a change was made, never as a list
of things to do. The review's detection figures are superseded and say so.

### READ THIS FIRST: the plan was reported done, and 17 items were not

On 5 September 2026, after all 34 items were marked complete and a green suite was offered
as evidence, the work was audited by fifteen independent agents reading the code rather than
the account of it. **Seventeen items came back partial.** Several were defects introduced by
the plan's own work and then reported as finished.

The four that mattered most, all confirmed by running the code rather than reading it:

1. **The agent was broken outright.** Item 28 added a query selecting `subject_id` from
   `interactions`, a table with no such column, called from `node_decide` behind a `hasattr`
   guard that is True. Every production episode raised `OperationalError` at the decision
   node. `wha demo run` could not complete. Every test of `node_decide` passes `db=None`,
   which makes the guard False, and the eleven scenario tests asserted the contents of the
   JSON fixtures they had just loaded, so nothing reached it.
2. **"Delete everything" deleted nothing.** `delete_all_subject_data` held a hand-written
   list of fifteen tables against a schema of twenty-seven, missing `subject_profile` and
   `episode_traces` from that same week and, for far longer, `conversation_turns` and
   `triage_answers`. The two new ones carry foreign keys, so the transaction rolled back
   entirely. Measured on a copy of the real database: 58,730 heart rate samples before,
   58,730 after.
3. **The human review checkpoint could not be reached.** No draft was stored while an
   episode waited, and `render_inbox` sat in the `else` of `if urgency`. Urgency is monotone,
   so once a person had escalated once they could never see a question or a review again.
4. **Two evaluation suites reported numbers nobody measured.** `wha eval detection` printed
   zeros as a benchmark; `wha eval ablation` was entirely synthetic, with 32 invented
   participants, scores from `random.Random(42)` and a hardcoded dict of effect sizes, and
   was still reporting a Chronos contribution days after Chronos was deleted.

All are fixed, each with a test checked against the defect by reintroducing it. The full
audit, item by item with file and line, is in `history/review-2026-09/AUDIT-2026-09-05.md`.

**The lesson is the one this file already stated and I did not follow.** A green suite is not
evidence. It was green for every one of these.

### The three findings from executing it that change how you read everything else

1. **The detector no longer beats the published algorithm, and the claim that it did was
   an artefact of running a looser rule than the one being cited.** Item 8 tightened the
   alert rule to NightSignal's own: two consecutive nights at baseline + 4. Re-scored on the
   same archive the two agree case for case. That correction is the finding; the figures on
   either side of it are ours, from an archive re-analysis rather than any trial, and they
   live in `experiments/detection/` behind its disclaimer.
2. **A between-person number was being used for a within-person quantity.** The baseline
   prior used Bloomfield's 8.64 bpm, which is how much adults differ *from each other*. The
   quantity needed is how much one person varies *night to night*, which is a different
   thing and a much smaller one. This is the correction with the widest reach: it moves
   every robust z in the system. Item 7.
3. **Fourteen figures carried a "Swept." annotation for a sensitivity analysis that does
   not exist anywhere.** Removed rather than fabricated. About 140 numbers in
   `data/knowledge/` still have no source and are now marked as such on screen, not only in
   the files. Items 1 and 17.

### What is still open

- **Item 30, the reranker, was tried and not adopted.** Several configurations across two
  cross-encoders, and not one beat plain hybrid retrieval on this corpus. That is an
  engineering comparison of our own search against itself, recorded in
  `experiments/retrieval/`. The table is in the module docstring of
  `tools/retrieval_check.py` and the outcome is written into the plan item itself.
- **A cited sentence can still misdescribe the passage it cites.** Found by using the
  dashboard. Not a bug and not fixable by a cheap check, so it is recorded in
  `BLOCKERS.md`, corrected in every file that overstated it, and said on the screen.
- Two contract disagreements are recorded in `BLOCKERS.md` rather than papered over.
  `docs/CONTRACTS.md` is read-only and names five constants the code no longer has;
  `tests/unit/test_contracts.py::REMOVED_FROM_THE_CODE` enumerates them.

### Permission granted for this work, 5 September 2026

`data/knowledge/` may be edited, and every change goes into `docs/KNOWLEDGE-CHANGELOG.md`
with the source sentence quoted or the measurement that replaced it. A number still may not
be invented. `README.md`, `AGENTS.md`, `CLAUDE.md` and `.agents/rules/` may be edited.
**`history/`, `research/`, `archive/` and `docs/CONTRACTS.md` remain read-only.**

### The evidence is in `experiments/detection/cohort/`, and it is committed

The cohort numbers used to live in a gitignored `scratch/`, so they would not have survived
a clean checkout. They are now committed and reproducible from two public downloads:

| File | What it does |
|---|---|
| `experiments/detection/cohort/fetch.py` | downloads both public inputs and asserts their byte counts |
| `experiments/detection/cohort/labels.py` | extracts the symptom-onset labels from the supplementary workbook |
| `experiments/detection/cohort/evaluate.py` | replays this system's own detector over the cohort |
| `experiments/detection/cohort/report.py` | sensitivity at four windows, chance floor, alert burden |
| `experiments/detection/cohort/sweep.py` | absolute against personal thresholds, at matched alert rates |
| `experiments/detection/cohort/infection.py` | the infection effect against matched controls |
| `experiments/detection/cohort/band_width.py` | night-to-night noise, three ways |
| `experiments/detection/cohort/chronos.py` | whether the forecast added anything. It did not, and it is gone |
| `tools/retrieval_check.py` | whether search returns passages about what was asked |

Start with `experiments/detection/cohort/README.md`. The published figures are in `experiments/detection/detection-results.json`.

---

## Verify in one minute

```bash
uv run pytest                       # 622 passed, 1 skipped, about 14 minutes
uv run ruff check src tests         # clean
uv run ruff format --check src tests
uv run wha doctor                   # no fail rows
uv run wha demo run illness-onset   # exits 0, opens an episode, reaches a disposition
uv run python tools/retrieval_check.py   # our own retrieval check, and every off-topic passage listed
uv run wha corpus search fever      # Fever first, and no internal configuration at all
```

Everything above runs offline. The phone bridge and the live model are not needed.

**None of it proves the thing that matters.** Every serious defect in this project, in every
session, was found by opening the dashboard and using it. In this session alone, with the
suite green throughout: "Summary for your doctor" crashed the whole Today page, the Trace
tab advertised a pipeline stage that had been deleted, and a reply misdescribed this
system's own detection rule while showing the two passages that state it correctly. Finish
by driving the real interface, not by reading this table.

---

## What happened

The implementation was completed by another agent, then reviewed adversarially. The review
found that **the agentic half of the system had never actually run**. It compiled,
executed, produced output and passed 331 tests while doing none of its work:

- No implementation existed of the twelve-method `db` interface every node and tool read
  through, so every `hasattr` guard was False and the tools returned empty results.
- Nothing was injected into the nodes, so `db` and `notifier` were always `None`.
- **No code path anywhere created an episode.** Only tests inserted episode rows.
- Questions were sent via `notifier.send_message`, which no notifier defines, and nothing
  ever constructed a notifier.
- The graph used a fresh in-memory checkpointer per tick, so no interrupt could resume.
- **Both layers of the red-flag safety floor were disconnected.** "No fever, but chest
  pain" did not escalate, and Tier C parsed every correct model response to zero flags.
- `run_policy_eval` returned hardcoded accuracy constants no policy had produced.

All of the above is fixed. The detail is in `history/plan/PROGRESS.md`.

---

## Current numbers

| Check | Result | When |
|---|---|---|
| Tests | **622 passed, 1 skipped**, no ignore list | 5 September |
| Lint and format | clean, `ruff check src tests` | 5 September |
| `wha doctor` | no fail rows | 5 September |
| Dashboard driven end to end with Playwright | all five pages, three defects found | 5 September |
| Telegram | a real message sent through `converse_over_telegram` | 5 September |
| Detection performance | **Not established.** There is no clinical trial and no validation. Our own re-analysis of a public archive is in `experiments/detection/`, behind its disclaimer | 7 September |
| Retrieval quality | Checked by us on twelve queries we judged ourselves. Not a benchmark, not validated. `tools/retrieval_check.py` | 5 September |
| Corpus | **1,849 chunks**, four layers, one of them fetched | 5 September |
| Frozen scenarios | **11 of 11** live against the real provider, 30 expectations, no failures | 5 September, re-run |

`tools/` now holds the scripts behind three of those rows, so the numbers survive a clean
checkout: `cohort/` for detection, `retrieval_check.py` for retrieval, and `rerank_sweep.py`
with `rerank-sweep-results.txt` for the reranker that was measured and not adopted.

The eleven scenarios take longer than ten minutes to run back to back live, so run them in
two batches. If a batch is killed part-way, check for an orphaned `python.exe`: a killed
run holds `data/demo.sqlite` open and the next run fails with WinError 32.

---

## The finding worth remembering

`LIKELY_ILLNESS` was unreachable, and the cause was **not** a clinical figure. Both the
infection effect size (1.60 bpm, since measured on the cohort) and the detection thresholds (3.0 and 4.0 bpm,
from Alavi 2022 NightSignal) are correctly sourced.

The defect was that `update_belief` collapsed the three-state cycle-applicability fact the
contract defines into an assumption that **every unasked subject menstruates**. The luteal
phase is the largest benign effect in `causes.yaml`, so it explained away exactly the
elevations the system exists to investigate, and was wrong for every male user.

Measured: p(infection) 0.025 assuming applicability, 0.070 treating it as unestablished.
The second is inside the band where the policy finds a question worth asking.

`POLICY_COST_PER_INTERRUPT` was annotated "Swept" and had never been swept. Now measured,
and moved from 0.30 to 0.15 on the frontier.

---

## Real device data

Ingested and working. **Four** usable nights at **44, 45, 45 and 47 bpm** with 303 to 399
minutes of wear, and the baseline correctly shrinking from the population prior toward the
subject as nights accumulate.

The figures in this paragraph were "three usable nights at 51, 56 and 48 bpm with 379 to 418
minutes"; none of the three matched the database, which has always been the source of truth
for them. Read it back with:

```bash
uv run python -c "import sqlite3; c=sqlite3.connect('data/wha.sqlite'); print([dict(zip(('date','bpm','mins'), r)) for r in c.execute(\"SELECT night_date, rhr_bpm, coverage_minutes FROM nightly_features WHERE subject_id='me' AND usable=1 ORDER BY night_date\")])"
```

**A resting heart rate in the mid forties matters for reading the rest of this file.** It sits
below the `rf_rhr_extreme_low` cold-rung bound of 40 by only a few beats, and that bound is
one of the numbers marked ASSUMED with no published source. `CLAUDE.md` and `AGENTS.md` both
say four nights; this section said three.

The watch provides **seven** channels, not the four `history/HANDOFF.md` section 10 originally
recorded. All seven are ingested. Heart rate variability, respiratory rate and skin
temperature are absent and cannot be computed from one-minute averages. The reasoning, and
why supporting the rest of Health Connect is not planned, is in
**`docs/DESIGN-DATA-CHANNELS.md`**.

**The bridge is only reachable when the phone hotspot is on.** Its address in `.env` is the
Wi-Fi gateway. Everything except `wha ingest` works without it.

---

## The production loop now closes

A production simulation, driven by a mock Health Connect bridge that speaks the real
protocol (`tools/mock_watch.py`, guide in `docs/RUNBOOK-SIMULATION.md`), found that
`wha serve` never completed a cycle. Five defects, all of the same shape as the ones the
earlier review caught, code that existed and never ran:

- `run_episode_tick` iterated only timed-out episodes, so a **newly opened episode was
  never stepped**. It sat at `step_count` 0 until a human ran `wha episode step`.
- `create_scheduler` registered three jobs while its docstring named four. The **Telegram
  polling job was absent**, and nothing anywhere constructed a `TelegramReceiver`.
- `EpisodeRepository` was **missing all five methods** the receiver reaches for through
  `hasattr`, so a tapped button was acknowledged to the user and then discarded.
- The ask node **dropped the answer space and the channel**, storing every question as
  having no options, asked over no transport.
- The ask node also **dropped `evsi`, `interruption_cost` and `rejected`**, so the one row
  that evidences the project's central claim recorded 0.0 against every question.

All fixed, with `tests/integration/test_production_loop.py` covering each. Measured end to
end against the mock watch: episode opens at `MATURE` baseline, agent asks
`probe_symptoms` with EVSI 0.357 against a 1.0 interruption cost having beaten eight
alternatives, the answer `fever` moves p(infection) from 0.071 to 0.3893, and the episode
closes `LIKELY_BENIGN` on the quiet-run condition once nights return to GREEN.

Three findings were recorded rather than fixed, because each is a design decision rather
than a defect. They are in `BLOCKERS.md`: an OBSERVE decision is never revisited on
later nights, episode dates come from the wall clock rather than the data, and the
synthetic generator covers four of the seven live channels.

---

## The night is measured over recorded sleep, not the clock

A production simulation with a real subject found the largest defect so far. The nocturnal
window was local 00:00 to 07:00 for everyone, the NightSignal definition, which that study
used because its data had no sleep staging. This build has staging and was ignoring it.

The subject sleeps roughly 03:00 to 11:00. The clock window counted 2.6 to 3.6 hours of
waking time as sleep on each of three nights and discarded about 40 percent of the real
sleep. Recomputed over the recorded sleep:

| Night | RHR, clock | RHR, sleep | Change |
|---|---|---|---|
| 31 Aug | 51.0 | 44.0 | -7.0 |
| 01 Sep | 56.0 | 45.0 | -11.0 |
| 02 Sep | 48.0 | 45.0 | -3.0 |

The spread matters more than the level: 8 bpm (48 to 56) became 1 bpm (44 to 45). Baseline
and observation share the window so a constant offset cancels, but variance does not, and
inflated variance widens the detection band and costs sensitivity. This subject's personal
scale fell from about 4.5 bpm to the 1.5 bpm floor.

Naps are excluded on evidence, not preference: Whitehurst, Naji and Mednick 2018,
Neurobiol Sleep Circadian Rhythms 5:52-57, found heart rate measurably higher during
daytime naps than overnight sleep at matched sleep stages. Reasoning, citations and stated
limitations, including that **sleep apnoea remains undetectable by design**, are in
`docs/DESIGN-SLEEP-WINDOW.md` and disclosed on the History page.

The nightly job no longer runs at 09:00. A clock trigger assumed the subject was awake and
synced by then; this one wakes around 11:00. Nights are re-scored on an interval and settle
when their sleep arrives.

`docs/CONTRACTS.md` is amended, and the column arrived in schema v4. The database is now at v8; `DB_VERSION` in `src/wha/db/migrations.py` is the only figure to trust for this.

---

## The detector compared everyone against the average adult

Asked why the first real subject's nights all sat below the displayed band, and found the
most serious defect of the simulation. `compute_baseline` blended the personal median with
a 62.75 bpm population prior at `w = n / (n + 7)`, and because the trailing window caps `n`
at 28 the weight capped at 0.800 permanently: a fifth of the prior never washed out.

Measured on a steady subject after 200 nights of their own data:

| True sleeping RHR | Centre | Residual every night |
|---|---|---|
| 45 | 48.5 | -3.5, needed a 6.5 bpm rise to reach YELLOW |
| 62.75 | 62.8 | 0.0 |
| 80 | 76.5 | +3.5, YELLOW every night while healthy |

Infection raises nocturnal RHR by 1.6 to 5 bpm, so the first real subject, who sits at 44
to 47, **would never have been flagged for an infection at all**.

The thresholds are NightSignal's, and NightSignal measures deviations above a
per-individual **streaming median with no population blending**. Applying its numbers to a
shrunk centre was a category error. The centre is now the person's own median once seven
usable nights exist, seven being the figure that paper reports for baseline establishment,
and nothing is flagged below that. Scale keeps its shrinkage: it sets band width and
`robust_z`, never the level. `docs/DESIGN-BASELINE-CENTRE.md`, contract amended.

This also corrected a diagnosis in `BLOCKERS.md`. `no-response-timeout` was recorded
as needing a higher injected amplitude; in fact its 4.4 bpm was always right and the shrunk
centre was eating the margin. Its residuals are now exactly 4.0, it reaches RED, opens an
episode and asks a question. One expectation still fails, for a different and real reason:
a timed-out question closes the episode `LIKELY_BENIGN` where `UNRESOLVED` is the honest
disposition. Recorded, not yet fixed.

---

## Limitations are on screen, not only in files

`DISCLAIMER.md` had been in this repository since the beginning and **nothing in the
interface ever showed it**, so a person using the dashboard was never told this is not a
medical device. It is now rendered where they land, with an expandable statement of what
the system can and cannot do.

`docs/DISCLOSURES.md` is the index: every clinical limitation, the evidence or the
explicit lack of it, and the screen it appears on. It exists so the rule can be checked
rather than assumed. The rule itself: a clinical choice is either backed by a citation next
to the number it justifies, or recorded as unevidenced in the docs **and** disclosed in the
dashboard.

Also removed a contradiction the disclosure exposed. Today said "4 quiet nights in a row"
directly above "Not watching yet": a night cannot be quiet if nothing could have flagged
it, so no streak is claimed below the alerting floor.

---

## A user ran the whole thing, and the agent was the next job

A seven-scenario production simulation was run end to end as an ordinary person: healthy
nights, exercise, an office party, feeling rough afterwards, a fever, a sore throat and
severe diarrhoea. What works is described in `history/HANDOFF-AGENTIC-FLOW.md`; the short
version is that the deterministic half is sound. Twenty healthy nights produced no
interruptions, a 4 bpm rise caused by a workout was correctly explained away rather than
raised, and the same physiological signal reached opposite conclusions depending on what
the person said about it.

Fifteen defects were found and fixed, nearly all the same shape this codebase keeps
producing: something defined, referenced elsewhere, and never reached. A person could not
report a symptom at all; an escalation notified nobody; nothing was ever written to the
outcomes table; an OBSERVE was never revisited; the model never worded a single question; a
pending question never appeared in the dashboard. See the commits from `Close eleven gaps a
simulated user walked into`.

That task is now **done**. The next section describes it.


---

## The agent can now look something up, and say where it got it

The five items in `history/HANDOFF-AGENTIC-FLOW.md` are complete. The detail is in
`history/plan/PROGRESS.md`; the short version is that the loop closes and the output is sourced.

**The graph returns to `investigate` after an answer.** That one edge is what makes the
cycle hypothesis-driven. Measured on a live run against the mock watch:
`retrieve_clinical_evidence` fired for the first time in this project's history, at the
step immediately after the answer, with the query `fever`. Belief moved 0.2954 to 0.7774 on
that answer, and the episode closed LIKELY_ILLNESS with five citations and no unsupported
claims.

**Three defects had to be fixed for that edge to do anything.** The investigate prompt was
rendered once before the loop, so the model was asked an identical question after every
call and asked for the same tool again, which is the 101 calls to `get_nightly_features`
the handover recorded. `tool_calls` reduces by concatenation and the node returned the
whole accumulated list, which would have doubled the record on every re-entry. Fact
extraction re-ran over the whole history, which would have duplicated every fact.

**The corpus is 33 documents, and every figure in it was checked against its paper.**
Generated from `causes.yaml`, `red_flags.yaml`, `probes.yaml` and `constants.py`, with the
numbers interpolated from the constants rather than retyped. `wha corpus build` writes it
out for review, `wha corpus search` queries it the way the agent does. Most citations
matched verbatim, including every load-bearing one; two did not and are in
`BLOCKERS.md`. The record is **`docs/CORPUS-VERIFICATION.md`**.

**No consumer health layer exists**, because writing one would be inventing clinical
content. The agent can cite why a night was flagged, what else could explain it, what an
answer implies, and the rule behind an escalation. It cannot cite general information about
a condition. Disclosed on the episode Evidence tab, not only in a file.

**`retrieval_index` was `None` and assigned by nothing**, so the retrieval tool was
allow-listed, offered to the model, ran without error and could never return a passage.
`citations` and `unsupported_claims` were hardcoded, and `claims` was a bare list of
strings, so the verbatim containment test the contract specifies had nothing to check
against and could not run even in principle.

### What driving the dashboard found that reading the code did not

Eight defects, all of the shape this codebase keeps producing.

The one worth remembering: **the model called `retrieve_clinical_evidence({"symptom": "fever"})`
against a handler that reads `query`.** It returned an empty list, reported ok, and the
episode concluded with no citations and nothing looking wrong. The model had been given the
tool names and nothing else, so it guessed. There is now a signature catalogue in the
prompt, a test that every registered tool appears in it, and an argument-less call is a
refusal that names the argument rather than a successful empty result.

The others: the outcome was written without the person's answer and stated "No specific
symptoms were reported" for an episode in which they had reported a fever; `tool_call_count`
and `depth_used` were columns nothing wrote to; `interruptions_used_this_week` was hardcoded
0; clicking an investigation on History did nothing, so the panel holding the differential
and the citations was unreachable by clicking; an urgent self-report was drawn underneath a
green "Nothing needs you right now"; and `PromptDefinition.render` swallowed a missing
context variable and sent the unrendered template, which also disarmed its own oversize
guard.

### The open decision, answered by measurement

The handover asked whether item 1 would make the agent nag. Across three live episodes it
asked **exactly one question each**, and in the episode with budget headroom it still asked
one and then concluded, because after the answer the EVSI for every remaining probe fell
below its interruption cost. The weekly budget was not the binding constraint there; the
policy's own quiet band was.

### One measurement discipline note

`wha demo run` results depended on the order the scenarios were run in, because the weekly
budget counts across subjects and the demo database is shared. Back to back the suite
reported 5 of 11; individually, 10 of 11. Fixed by resetting the demo database per run. I
believed the wrong number twice before checking, once because my own grep for `[FAIL]` was
anchored while the lines are indented. Recorded in `BLOCKERS.md`.

Frozen scenarios were **10 of 11** at the time of writing, with `no-response-timeout`
failing because a timed-out question closed `LIKELY_BENIGN` where `UNRESOLVED` is honest.
**That was fixed, and all eleven now pass live: 30 expectations, no failures, re-run
against the real provider on 5 September 2026.**


---

## A red flag is now something it asks about, not a word it waits for

The safety floor matched phrases. Someone typing "chest pain" was routed to an ambulance
with no confirming question, which is not what a clinician does and not what the evidence
supports. The research behind the replacement is in **`docs/RESEARCH-AGENTIC-TRIAGE.md`**.

**The evidence.** Downie et al., BMJ 2013;347:f7095, reviewed red flags systematically:
"many red flags in current guidelines provide virtually no change in probability ... or
have untested diagnostic accuracy". Individually most were uninformative; combinations
carried the information. Sutaria et al., BMC Health Serv Res 2025;25:1263, defines a red
flag as a symptom that would be **sought**, and measured online symptom checkers seeking
36.9 percent of the relevant ones against 71.8 percent for physicians.

**The one rule this system can actually run.** The Marburg Heart Score rules out coronary
disease in primary care from history and self-palpation alone: five items, cut-off 3,
sensitivity 87.1 percent, specificity 80.8 percent, NPV about 98 percent (Bösner et al.,
CMAJ 2010;182(12):1295-1300; external validation Haasenritter et al., Br J Gen Pract
2012;62(599):e415-21). Transcribed item by item into `data/knowledge/triage_rules.yaml`.

**The division of labour is the design.** The model elicits, in whatever words the person
uses. `wha/safety/triage.py` decides. The model may raise urgency at any time and can never
lower it; urgency falls only when a transcribed published rule returns a lower band from
items the person actually gave. Marburg's own contraindication, "do not use in an emergency
setting", is encoded as unconditional gates that are checked first and stop the score being
computed at all.

Measured live: "I have chest pain today" now asks about exertion instead of escalating.
Answering the five items scored 0 of 5 and routed to **see a doctor today** rather than an
ambulance, naming the rule and its source on screen. Every answer is stored with the
person's own words beside it.

## It is a conversation now

`ask_about_episode` was a text box over word-overlap matching that made **no model call at
all**. `wha/agent/conversation.py` replaces it: multi-turn, retrieval-grounded, persisted,
and wrapped in deterministic checks on every turn.

- **Cited or labelled, never silently asserted.** Draelos et al. 2025 (arXiv:2507.18905)
  red-teamed four frontier chatbots over 222 patient-posed questions: 5 to 13 percent of
  answers were outright unsafe. Anything the model writes from its own knowledge appears
  under an amber "Not from a cited source" heading.
- **Two calls per turn, not one.** Asked to converse and to extract rule answers together,
  the model conversed: it asked the Marburg questions correctly and recorded none of the
  answers, so the rule never completed and a person describing chest pain was left with no
  urgency at all. Extraction is now its own zero-temperature pass.
- **Nobody is left in limbo.** If a rule cannot be completed within three replies the
  presentation resolves as urgent, stated as the cautious direction rather than a finding.

## The budget was the wrong shape

Alarm fatigue evidence concerns unsolicited alarms: 72 to 99 percent of monitor alarms are
non-actionable (Front Digit Health 2022;4:843747). Counting a follow-up inside a live
conversation against the same allowance is why the agent could never ask more than two
questions a week. Now two resources: **2 unsolicited interruptions a week**, and **10 turns
inside a conversation**, the figure at which AMIE reached an accurate differential (Tu et
al., Nature 2025;642:442-450).

## Something to hand a doctor

`wha/service/handover.py` builds an SBAR summary with a question prompt list. SBAR is the
WHO, Joint Commission, AHRQ and IHI recognised handover structure; question prompt lists
increase the questions a patient asks without lengthening the consultation (2025
meta-analysis of RCTs). Everything in it is measured or quoted with a timestamp.

Building it found two defects it would otherwise have shipped to a clinician: nights
reporting **42.9 hours of sleep**, because overlapping sleep records were summed rather
than merged; and an inverted rule item printed as "pain not reproducible: yes" when the
person had said pressing *does* reproduce it, which asserts the reverse of what they said.


---

## Four subsystems had never executed, and the dashboard is now replaceable

A pipeline review, stage by stage, driven rather than read.

**Chronos had never run.** `forecast_night()` was called by nothing: `detect_night` took an
optional `Forecast` defaulting to `NOT_RUN` and every caller left it out. A subject with 41
usable nights against a five-night minimum recorded `NOT_RUN` on every night, while
`wha doctor` reported 182 MB of weights present and this file claimed Chronos was
forecasting. It was connected, which is what finally let it be compared, **and the
comparison deleted it.** On our own data the forecast residual separated illness less well
than the plain baseline residual the detector already computes, and it caught essentially
nothing the detector missed. `src/wha/detect/forecast.py`, the five `FORECAST_*` constants
and the `chronos-forecasting` dependency are gone. The comparison and its limits are in
`experiments/forecasting/`.

That agrees with the literature rather than contradicting it: Alavi et al. 2022, the source
of our thresholds, measured plain baseline deviation at 78 percent sensitivity against 54
for CuSum and 44 for a forecast-style detector.

**MEASURE had never fired.** `ActionKind.MEASURE` appeared only in the graph's router, so
`node_measure`, the "A quick reading would help" screen, `submit_measurement_done` and
`compute_measurement_logfactor` were unreachable and the `measurements` table had never
held a row. **The whole limb is deleted.** It was briefly replaced by a disposition gate
that turned out to be unreachable too, measured over 20 combinations of coverage and
residual and firing in none of them, so that went as well. The graph has eight nodes and
`measure` is not one of them. What remains unfixed is in `BLOCKERS.md`: a night whose
leading explanation is a sensor artifact still concludes LIKELY_ILLNESS.

**Injection scanning had never run in production.** `scan_untrusted` was called only by
`wha/eval/adversarial.py`, so the `injection-poisoned` scenario passed because the
evaluation invoked the scanner directly. Retrieved passages are now scanned before the
model sees them, and detection contains rather than drops.

**The conversation was not in the audit chain**, while the page said everything is written
down. It is now, under the `chat` operation the contract had reserved and nothing used.

### The dashboard is a client now

Screens called service functions as Python imports. Clean layering, with no SQL in any
view, but only Python could cross it. There is now a FastAPI boundary on `127.0.0.1:8500`
with 34 endpoints and generated OpenAPI docs at `/docs`, and Streamlit is one of its
clients. A React front end can replace it without a line of backend work.

`/config` enumerates every public constant from the module rather than listing them by
hand, so it cannot drift, and it carries the subject's local date because a browser cannot
compute it. A test asserts no screen imports `wha.service`, `wha.constants`, `wha.clock` or
anything below them.

Driving the five screens found two defects the suite did not: `localise` returned a string
where `to_local` had returned a datetime, so every caller that formatted it broke at render
time; and the audit endpoint took a subject id where the service wanted an `AuditFilter`.
Both were invisible to tests because no test rendered the status strip with a timestamp
present or opened the Audit page.


---

## Silence was being reported as reassurance

The scenario that had failed since before this work began, `no-response-timeout`, was not a
fixture problem. It was **premature closure**, and the behaviour has a name and a measured
rate in the literature.

Handler, Bedi and Shah, arXiv:2605.15000 (2026), define it as "inappropriate commitment
under uncertainty: providing an answer, recommendation, or clinical guidance when the safer
response would be clarification, abstention, escalation, or refusal", and measured **55 to
81 percent false-action rates** across five frontier models on medical questions whose
correct answer had been removed.

This build did it deterministically, with no model involved. A timed-out question became a
declined answer, a declined answer contributes no likelihood factor, so the belief never
moved and the episode fell through to `LIKELY_BENIGN`. The system asked the single most
informative question it had, heard nothing, and reported that things were probably fine.

An unanswered question now forces `UNRESOLVED`. The check sits after the illness threshold,
so silence can prevent a reassurance and can never talk an escalation down, and a workout
the watch itself recorded still explains a night because that is positive evidence rather
than an absence. **Frozen scenarios are 11 of 11 for the first time.**

## Two clinical figures corrected against their papers

A narrow exception to the read-only rule was granted: a figure may be corrected when the
published source can be quoted contradicting it. Every such edit is recorded in
**`docs/KNOWLEDGE-CHANGELOG.md`** with the source, the old value, the new value and what it
changed downstream.

**`EXERCISE_EFFECT_BPM` was two-thirds traceable and one-third invented.** With the paper
in hand at `research/papers/leota-2025-nat-commun-16-3297.pdf`, its table gives incremental
contrasts between strain levels; high strain against none is their sum: 1.58 bpm at -6h,
1.87 at -4h, 2.91 at -2h, 5.59 at sleep onset. Of the three stored values, **2.91 and 1.58
are exactly the paper's figures** at -2h and -6h, and **4.14 appears nowhere**. The two
real ones were also assigned to bands one step apart from each other. Corrected to
`{"0-2h": 2.91, "2-4h": 1.87, "4-6h": 1.58}` under one rule, the far edge of each band,
which is the smallest figure the paper supports. That direction is deliberate: this
quantity is subtracted from the elevation, so overstating it hides illness.

**The luteal citation** said wrist temperature +0.44 C and respiratory rate +0.60/min;
Goodale's own phase means give +0.45 and +0.47. Neither channel is ingested, so this was a
citation defect rather than a clinical one, but that string is rendered into the corpus as
a citable passage.

## Blood oxygen is used, as a threshold and not as a cause

The question was whether to give it a likelihood in `causes.yaml`. It does not get one: **no
published study relates a wearable oxygen reading to any of the twelve causes**, so that
number would be invented. What exists is WHO guidance on when a level warrants care rather
than home management, and documented **silent hypoxia** in COVID, where oxygen falls while
the person still feels well. That is exactly the pre-symptomatic window this system exists
for, and heart rate cannot see it.

So it sits in the deterministic floor as a cited threshold that can raise urgency. Three
constraints come straight from the evidence:

- **It needs a night, not a spot check.** Ten readings inside the sleep window, or it
  returns no opinion. The real device gave six readings across four days, including an 80
  percent followed by a 92 percent sixty-six seconds later. Overnight tracking has to be
  switched on in the phone app for this to do anything.
- **It uses the median, not the minimum**, because the minimum fires on every movement
  artefact this sensor produces.
- **A normal reading is explicitly not an all-clear.** Consumer pulse oximetry reads high
  on darker skin (pooled bias 1.27 percent for dark pigmentation against 0.70 for light,
  *J Med Internet Res* 2024;26:e62769), so a genuine fall can be missed. That caveat is
  shown every time, including on normal nights.

**The machine is left pointed at the simulation.** `.env` has `WHA_SUBJECT=sim` and the
bridge on `127.0.0.1:8788`; the original is `.env.phase4-backup`. Restore it before using
the real watch.

---

## The agent can cite general health information now, and says where it came from

`sources.yaml` has described four corpus layers since the design was written. Only three
existed. The agent could explain why a night was flagged, what else might explain it, and
the rule behind an escalation, and if asked what a fever is it had to refuse, because the
only alternative was writing clinical text from the model's own knowledge.

**The URL recorded for the missing layer was a 404 and appears never to have existed.** It
named an undated `mplus_topics_compressed.zip`; MedlinePlus publishes dated snapshots,
Tuesday to Saturday. `wha.retrieve.medlineplus` resolves the newest at fetch time and
raises rather than guessing if the scheme changes, so the entry cannot rot the same way
twice. `wha data fetch corpus` used to return "Corpus target verified" and fetch nothing.

Snapshot 2026-09-03: **1,013 English topics** of 2,033, the rest Spanish or summaries short
enough to be a pointer rather than information. Date, URL and SHA-256 are in
`data/knowledge/corpus-sources.json`. The release itself is not committed, because it is a
thousand topics this project does not own under an attribution-only licence.

**What it cost, measured rather than assumed.** The index went from 133 chunks to 1,849, a
fourteenfold increase. The authored escalation rules still surface in the top six for
"chest pain", "I fainted" and "my chest hurts and I feel sick", and a test asserts it,
because a thousand fetched topics burying this system's own safety rules is the plausible
failure here. The deterministic floor never consults retrieval, so what changed is what the
person reads and what the model reasons over, not whether an escalation fires. Embeddings
are cached to disk keyed by a digest of the chunk text: **343s cold, 3.0s warm**.

One older test asserted our chest-pain rule was rank 1 for "chest pain". With a consumer
layer present, MedlinePlus ranks first and our rule second. That assertion encoded the
absence of layer 1: holding it would have meant the corpus could never grow the layer it
most needed. Corrected to assert presence in the results, after measuring the top-6
behaviour rather than to make it go green.

### What driving the dashboard found, again

Answered the pending Marburg question, then asked "what is costochondritis?". It answered
from MedlinePlus, flagged its two ungrounded sentences amber, and held the same-day urgency
the rule had already set. **The citation underneath rendered as a bold title and an
identifier and nothing else.** That is traceable and it is not attribution, and the licence
is attribution-only. It also hid the distinction that matters more than the licence:
general background about a condition and a safety rule about this person looked identical
sitting under a piece of health advice.

`wha.ui.components.citations` now names the source in words everywhere a citation is drawn.
Fixing it broke an import on the Today page, and **ruff and 546 tests were entirely happy
while that page was dead.** Reloading the page as a user caught it in seconds. That is the
fourth time in this project that a passing suite has said nothing about whether the screen
renders.

**The Telegram path has not been checked since the layer was added.** It renders citations
through different code. There is no evidence it names the source.

---

### What driving the dashboard found, a third time, after all 34 items were done

Every one of these was found by opening a page and clicking something, with the suite green
before and after. None was found by a test, and the first two took the page down.

1. **"Summary for your doctor" crashed the whole Today page.** `AttributeError: 'dict'
   object has no attribute 'as_text'`. When the HTTP boundary went in, the dashboard started
   holding the JSON body where it used to hold a service object, and this one call site was
   never updated. The endpoint had been returning the rendered text in `"text"` the whole
   time. **Second instance of the shape**: `ApiClient.localise` carries a docstring about
   the first. A static guard now walks every screen for `api().method(...).attribute` where
   the client method returns plain JSON, and it was checked against the real defect before
   being kept.

2. **The Trace tab advertised a pipeline stage that had been deleted.** `CANONICAL_STAGES`
   still listed `measure` after `node_measure` was removed, so a person saw a stage of their
   own investigation described as "Request spot resting heart rate or overnight wear",
   permanently pending. The graph had eight nodes and the screen showed nine. A test now
   reads `add_node` calls out of `graph.py` and requires the two lists to match, in order.

3. **A reply misdescribed this system's own detection rule while citing the passages that
   state it correctly.** Asked why a night was flagged, it called the baseline an "average"
   (it is the median) and said a night is flagged at 3 bpm (3 is elevated; flagging needs
   two consecutive nights at 4). This one is **not a bug and is not fixed**: the grounding
   check verifies the span the model quoted, never the sentence around it. Recorded in
   `BLOCKERS.md`, corrected in every file that overstated it, and said on the screen.

Two smaller ones from the same pass: the record read "arrived from the your watch source" on
every ingest line, and `wha corpus search fever` still returned the raw answer-option dump at
rank 3, which is the failure item 30 was written about.

**`episode_traces` had zero rows.** Item 11 added the table and the writer, and the writer is
guarded by `hasattr(db, "record_episode_trace")`, the exact guard that once made every tool
in this system a silent no-op. It turned out to be sound, but nothing had ever proved it: the
Trace tab's tests insert rows directly, so they would pass with the writer deleted. A test
now drives the real node through a real repository, and it was checked by disabling the
writer to confirm it fails.

---

## Open items for a human

`BLOCKERS.md`. The ones that matter:

**Almost everything that used to be listed here is now an item in
`history/review-2026-09/REFINEMENT-PLAN.md`, and all 34 are done.** What remains below is only what the plan
does not cover.

1. **`.env` is pointed at the simulation.** Everything verified in the review ran on
   simulated or public cohort data. Restore `.env.phase4-backup` before real use, and not
   before being asked.
2. **The nightly scheduler, and the processes it leaves behind.** A `wha serve` with its
   scheduler active was found running during the review, polling Telegram every 45 seconds
   against `data/wha.sqlite`. On 5 September, **twelve orphaned Streamlit processes** from
   an earlier session's test runs were found still alive on ports 8599 to 8611, each burning
   a core. They were stopped, along with `wha serve`, so nothing from that session is left
   running. Stop `wha serve` before a `uv sync`: it holds the virtual environment open, and
   a `uv sync` against a running server fails with a file lock.
3. **`git stash@{0}`** holds the reverted SpO2, respiratory and skin-temperature work.
   Superseded and safe to drop.
4. **Blood oxygen still has no likelihood** in `causes.yaml`, so it cannot move the belief.
   That remains correct: no published study relates a wearable oxygen reading to any of the
   twelve causes, and inventing one is exactly what item 1 is about. What plan item 4 fixes
   is that the oxygen *threshold rule*, which is cited and does exist, has never been called.

**Closed by the review, with the evidence in `history/review-2026-09/EVIDENCE-LOG.md`:**

- **The cohort datasets, and the `cohort_labels.yaml` that was never needed.** The delegated
  decision is made: fetch
  them. They were never unavailable. The Stanford set is a public 378 MB download and the
  symptom onset dates are in the same paper's Supplementary Data 1, on the same date shift as
  the public files. Detection accuracy is measured. Blockers A-25 and A-26 are answered.
- **The Telegram citation.** Checked by sending a real message. It renders `Sources: Fever`
  for a MedlinePlus passage, naming neither MedlinePlus nor the National Library of Medicine,
  under an attribution-only licence. Now plan item 12.
- **The two narrow corpus layers.** Still narrower than `sources.yaml` claims. Now plan item
  21, which corrects the claim rather than building the layers.

---

## Standing constraints that still apply

- **Never weaken a test to make it pass.** Where a test encoded a defect, it was corrected
  to assert the intended behaviour and the reason recorded in the commit.
- **Never invent a number.** Thresholds live in `constants.py`, clinical figures in
  `data/knowledge/`. A value that is not there is a blocker.
- **Never push.** Commit locally only.
- `data/knowledge/`, `research/` and `archive/` are inputs, not outputs.
- Documentation figures are now asserted against the code by
  `tests/unit/test_documented_numbers.py`, because the README and the audit page had both
  drifted from `constants.py`.

---

## Where to look

| Question | File |
|---|---|
| How the build ran, task by task | `history/plan/PROGRESS.md` (frozen build log, stops partway through the agentic work) |
| What is open right now | `BLOCKERS.md` (root, live) |
| Why only seven data channels | `docs/DESIGN-DATA-CHANNELS.md` |
| Does the policy actually work | `EVALUATION.md` |
| What the agent may cite, and whether it checks out | `docs/CORPUS-VERIFICATION.md` |
| Which MedlinePlus release is in use | `data/knowledge/corpus-sources.json` |
| Every clinical figure changed, and the source quoted for it | `docs/KNOWLEDGE-CHANGELOG.md` |
| The original rules and constraints | `history/HANDOFF.md` |
| The frozen contract | `docs/CONTRACTS.md` |
