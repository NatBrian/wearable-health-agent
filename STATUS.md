# STATUS — read this first

**Last updated:** 4 September 2026 (premature closure, and two corrected figures)
**Branch:** `feat/agentic-early-warning-system` (14 commits ahead of the implementation work, nothing pushed)

`HANDOFF.md` describes the job of writing this system from nothing. That job is done. This
file describes where things actually stand.

---

## Verify in one minute

```bash
uv run pytest                     # 536 passed, 1 skipped
uv run ruff check src tests       # clean
uv run ruff format --check src tests
uv run wha doctor                 # no fail rows
uv run wha demo run illness-onset # exits 0, opens an episode, reaches a disposition
```

Everything above runs offline. The phone bridge and the live model are not needed.

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

All of the above is fixed. The detail is in `plan/PROGRESS.md`.

---

## Current numbers

| Check | Result |
|---|---|
| Tests | **536 passed, 1 skipped**, no ignore list |
| Lint and format | clean |
| `wha doctor` | no fail rows |
| Frozen scenarios | **11 of 11** |
| Evaluation | measured, in `EVALUATION.md` |

The scenario that fails is `no-response-timeout`, and it is a fixture defect rather than a
code defect: its injected amplitude yields a 3.65 bpm residual against a 4.0 bpm threshold,
so no alert event can form. Forcing it green would mean editing a frozen fixture or nudging
a constant. Recorded in `plan/BLOCKERS.md` with the measurements.

---

## The finding worth remembering

`LIKELY_ILLNESS` was unreachable, and the cause was **not** a clinical figure. Both the
infection effect size (1.60 bpm, derived) and the detection thresholds (3.0 and 4.0 bpm,
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

Ingested and working. Three usable nights at **51, 56 and 48 bpm** with 379 to 418 minutes
of wear out of a possible 420, and the baseline correctly shrinking from the population
prior toward the subject (62.75 → 61.28 → 60.69) as nights accumulate.

The watch provides **seven** channels, not the four `HANDOFF.md` section 10 originally
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
than a defect. They are in `plan/BLOCKERS.md`: an OBSERVE decision is never revisited on
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

`plan/02-contracts.md` is amended, schema is v4 (`nightly_features.rhr_window_source`).

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

This also corrected a diagnosis in `plan/BLOCKERS.md`. `no-response-timeout` was recorded
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
severe diarrhoea. What works is described in `docs/HANDOFF-AGENTIC-FLOW.md`; the short
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

The five items in `docs/HANDOFF-AGENTIC-FLOW.md` are complete. The detail is in
`plan/PROGRESS.md`; the short version is that the loop closes and the output is sourced.

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
`plan/BLOCKERS.md`. The record is **`docs/CORPUS-VERIFICATION.md`**.

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
anchored while the lines are indented. Recorded in `plan/BLOCKERS.md`.

Frozen scenarios remain **10 of 11**, with `no-response-timeout` failing for the reason
already recorded: a timed-out question closes `LIKELY_BENIGN` where `UNRESOLVED` is honest.


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
forecasting. It now runs, at 0.1 s per night once warm, and is shown as advisory context.

It stays out of the belief model on evidence. No study was found showing a forecast
residual identifies *which* cause is present, and Alavi et al. 2022, the source of our
thresholds, measured plain baseline deviation at 78 percent sensitivity against 54 for
CuSum and 44 for RHRAD. `FORECAST_AS_EVIDENCE` and `FORECAST_EVIDENCE_SD_BPM` are deleted
and `plan/02-contracts.md` amended.

**MEASURE had never fired.** `ActionKind.MEASURE` appeared only in the graph's router, so
`node_measure`, the "A quick reading would help" screen, `submit_measurement_done` and
`compute_measurement_logfactor` were unreachable and the `measurements` table had never
held a row. The policy now selects it when sensor artifact leads the differential.

**Injection scanning had never run in production.** `scan_untrusted` was called only by
`wha/eval/adversarial.py`, so the `injection-poisoned` scenario passed because the
evaluation invoked the scanner directly. Retrieved passages are now scanned before the
model sees them, and detection contains rather than drops.

**The conversation was not in the audit chain**, while the page said everything is written
down. It is now, under the `chat` operation the contract had reserved and nothing used.

### The dashboard is a client now

Screens called service functions as Python imports. Clean layering, with no SQL in any
view, but only Python could cross it. There is now a FastAPI boundary on `127.0.0.1:8500`
with 28 endpoints and generated OpenAPI docs at `/docs`, and Streamlit is one of its
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

## Open items for a human

`plan/BLOCKERS.md`. The ones that matter:

1. **Two cited figures did not survive checking.** In `causes.yaml` the luteal citation
   states wrist skin temperature +0.44 C and respiratory rate +0.60/min; read off Goodale
   et al. 2019 those are +0.45 and +0.47. Neither channel is used, so this is a citation
   defect rather than a clinical one. And `EXERCISE_EFFECT_BPM` could not be verified at
   all: Leota et al. 2025 is paywalled everywhere tried. Both files are read-only to me and
   were not touched. `docs/CORPUS-VERIFICATION.md` has the full record.
2. **Whether to fetch MedlinePlus.** It is free and attribution-only, and it is the only
   route to the agent being able to cite general health information about a condition.
3. **`no-response-timeout`** closes `LIKELY_BENIGN` where `UNRESOLVED` is the honest
   disposition for a question that was never answered.
4. **Blood oxygen has no likelihood** in `causes.yaml`, so it is captured and shown but
   cannot move the belief. Adding one is a clinical judgement. Note the readings are sparse
   (five across seven days) and noisy (an 80 percent sixty-six seconds before a 92).
5. **Cohort datasets absent.** `data/datasets/stanford` and `pmdata` are empty and
   `cohort_labels.yaml` was never authored, so detection accuracy is honestly reported as
   "not evaluated" rather than given a number.
6. **`git stash@{0}`** holds the reverted SpO2/respiratory/skin-temperature work. Now
   superseded by the proper implementation and safe to drop.

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
| What was broken and fixed, in detail | `plan/PROGRESS.md` (end) |
| What still needs a human | `plan/BLOCKERS.md` |
| Why only seven data channels | `docs/DESIGN-DATA-CHANNELS.md` |
| Does the policy actually work | `EVALUATION.md` |
| What the agent may cite, and whether it checks out | `docs/CORPUS-VERIFICATION.md` |
| The original rules and constraints | `HANDOFF.md` |
| The frozen contract | `plan/02-contracts.md` |
