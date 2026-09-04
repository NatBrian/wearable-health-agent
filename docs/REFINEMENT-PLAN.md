# Refinement plan

What to actually do, in the order that buys the most. Every item names the reason, the
evidence behind it, the effort, and the risk of doing it. Nothing here is a suggestion to
add a feature: this project does not need more parts.

Written 4 September 2026 from `docs/DESIGN-REVIEW.md`. The evidence is in
`docs/EVIDENCE-LOG.md`.

**Effort** is my estimate of focused work: **S** under an hour, **M** a few hours, **L** a
day or more, **XL** a clinical decision plus a day or more.

**A note on ordering.** The first four items are safety. Items 5 to 12 are things that are
documented as working and are not. Items 13 onward are honesty and deletion. If you only do
the first page, do the first page.

---

## Before anything: the two rules to hold

1. **Do not fix these by changing a test.** Every one of these was invisible to 546 passing
   tests. The test that proves a fix must exercise the wire, not the function.
2. **Finish each one by using the product.** Every defect in this list was found by running
   or driving, and none by reading. A fix verified by reading is not verified.

---

# Tier 0. Safety. Do these first.

## 1. Put the escalation criteria through the checks that already exist
**FIX · Effort S · Risk: low**

**What.** `EpisodeOutcome.escalation_criteria` is written by the model and passes through
neither the grounding check nor the fabricated-number filter. Route it through both. The
number filter is already written and already called two lines away; it is simply pointed at
`observation` only.

**Why.** This is the single most action-guiding text the system produces. From a live run:

> "Seek care if fever persists beyond 72 hours or exceeds 103°F (39.4°C)"

72, 103 and 39.4 are clinical thresholds invented by a language model. Every one of them
would have been stripped by the filter that already exists, because none appears in any
structured field.

**Evidence.** Draelos et al. 2025 (arXiv:2507.18905) measured 5 to 13 percent of unguarded
frontier-model answers to patient-posed questions as outright unsafe. This is the exact
surface that guard exists for.

**Risk of doing it.** If the check strips everything the model wrote, the field falls back
to `DEFAULT_ESCALATION_CRITERIA`, which is human-authored and safe. That is the correct
failure mode. Watch that the fallback is not so generic it becomes noise.

**While you are there.** Those fallbacks are hand-written clinical sentences living in
Python: `node_conclude` carries "Seek care if elevated heart rate persists >3 nights without
confounders" and `output_checks.py` carries `DEFAULT_ESCALATION_CRITERIA`. They are the only
clinical content in the codebase that is not in `data/knowledge/`, which is the project's own
rule. Move them into `red_flags.yaml`, where the rest of the care-pathway wording already
lives and where the corpus can cite them.

## 2. Connect the human review checkpoint, or remove the claim
**FIX · Effort S · Risk: medium, it will slow episodes down**

**What.** `_resume_value` in `service/scheduler.py` handles `question` and `measurement` and
falls through to `{"decision": "approve"}` for everything else, which includes the human
review interrupt. And `AWAITING_HUMAN_REVIEW` is never set by anything, so the review
cannot appear in the dashboard. Two changes: set the state in `node_review` before the
interrupt, and return `None` from `_resume_value` for an unhandled kind so the episode
stays parked until a person acts.

**Why.** As shipped, a background job approves the system's clinical output on your behalf
fifteen minutes later, and the record shows a human decision that never happened. This is
the rubric's mandatory human-in-the-loop checkpoint.

**Evidence.** Confirmed on a live run: episode `ep_3637eaf58033` went from `AWAITING_USER`
to `CLOSED` in a single tick with no human involved.

**Risk of doing it.** Episodes will stop closing on their own. For a single user who may not
open the dashboard for days, that means outcomes pile up unreviewed. Pair the fix with a
timeout: if nobody reviews within, say, `ANSWER_TIMEOUT_HOURS`, close it and **record that
it closed unreviewed**, which is honest, rather than recording an approval.

## 3. Give the vitals rules and the blood oxygen rule a caller
**FIX · Effort M · Risk: medium, it creates a new alerting path**

**What.** Three safety mechanisms have never executed:

- `check_overnight_oxygen` is called by nothing in `src/` and by no test.
- The two extreme heart rate rules need `robust_z`, and all three production callers of
  `check_red_flags_with_tier_c` pass only `user_text`.

The natural home for all three is the nightly detection path, where `robust_z`, the rung
and the sleep window are all already in hand: after `detect_night` computes a detection,
evaluate the vitals rules against it and the oxygen rule against the window, and raise an
escalation through the same route a self-report takes.

**Why.** A night six robust standard deviations above your own baseline currently raises
nothing at all unless you independently type a tier A phrase. That is the opposite of what a
safety floor is for.

**Evidence.** Line coverage over a full production run: `safety/rules.py` lines 162-178 and
253-266 never execute.

**Risk of doing it.** This is the one item that can newly wake someone at 3am. Do it after
item 6 (the scale fix), because `robust_z` is currently divided by a scale that is one fifth
borrowed from 18-24 year old university students, so the threshold does not mean what it
says. And measure the trigger rate on the cohort data before shipping it: the harness in
`scratch/cohort_eval.py` will tell you how often z > 6 occurs in 8,508 real nights.

## 4. Feed the Marburg age gate the age it already has
**FIX · Effort S · Risk: low**

**What.** `triage()` refuses to apply the rule below `minimum_age_years: 35`, and
`age_years` is populated by nothing. The dashboard does not collect it and the API field is
never filled. Either collect it once in Settings, or read it out of the `mhs_age_sex`
extraction, which already stores the person's own words.

**Why.** In a live run the person said "I am 24 and male", the extractor stored it
correctly, and the system applied a rule validated only in people aged 35 and over, scored
3 of 5 from three items common in a young adult with a muscular strain, routed to urgent,
and cited "a 2010 study of 1,199 people with chest pain".

**Evidence.** Bösner et al. 2010 derived the rule on "1,199 unselected and consecutive
patients aged >= 35 years". Below that it was never tested.

**Risk of doing it.** Under-35s will be escalated unconditionally instead of scored, which
is more escalations, not fewer. That is the conservative direction and the file already says
so.

---

# Tier 1. Documented as working, and not working.

## 5. Correct the infection effect size
**FIX · Effort XL, because it needs a clinical decision · Risk: high, it changes everything downstream**

**What.** `causes.yaml` infection `effect_mean_bpm: 1.60` is unsupported by its cited source
and is incoherent with the detection thresholds. Decide the replacement, record the
reasoning, and re-run the eleven frozen scenarios and the policy evaluation.

**Why.** Three independent problems:

1. **The citation is wrong.** `docs/CORPUS-VERIFICATION.md` attributes "average peak
   increases relative to baseline of 1.8% for females and 3.4% for males" to Mishra et al.
   2020. Those percentages are not in that paper. They are from Natarajan, Su and Heneghan
   2022, *Frontiers in Physiology* 13:898251, which nothing in the repository cites.
2. **The derivation mixes cohorts.** A percentage from a 7,200-person Fitbit COVID cohort is
   multiplied by 62.75 bpm from 525 first-year university students. And because the effect
   is proportional while the thresholds are absolute, the same percentages give **0.8 to 1.5
   bpm** on this project's own subject, whose nights sit at 44 to 47.
3. **It contradicts the threshold paper.** The detector notices nothing below 3.0 bpm.
   Alavi et al. 2022, the source of that threshold, reports 67 of 84 infected participants
   (80 percent) crossing a +4 bpm two-night alert. A 1.60 bpm peak effect cannot be
   reconciled with that.

Measured consequence, live run, two nights at +5.0 bpm before any question: infection
0.0756, behind stress 0.8147, alcohol 0.5536 and short sleep 0.4813. The cause the system
exists to find sat fourth.

**Evidence.** All three sources quoted in `docs/EVIDENCE-LOG.md`. `BLOCKERS.md` already
records this as "LIKELY_ILLNESS is unreachable under the authored knowledge tables" and asks
which of three numbers is wrong. It is this one.

**Risk of doing it.** Raising the infection effect raises p(infection) on every elevation,
which will make the system ask more questions and reach LIKELY_ILLNESS more often. That is
the intended direction, and it must be measured: re-run
`uv run wha eval-report` and all eleven scenarios, and expect several expectations to move.
Do not pick a number to make a scenario pass. Measure first, then assert.

**What I am not doing for you.** I am not proposing a replacement number. Mishra reports a
median 7 bpm increase during detected abnormal periods, but that sample is conditioned on
having been detected and is biased upward. This is a clinical judgement and it belongs to a
human, which is exactly what `BLOCKERS.md` said.

## 6. Correct `causes.yaml` exertion 4.14, and stop shrinking the scale
**FIX · Effort S for the first, M for the second · Risk: low for the first, medium for the second**

**What.** Two separate corrections that both move sensitivity in the same direction.

`causes.yaml` exertion `effect_mean_bpm: 4.14`. The identical number was corrected in
`constants.py` on 4 September with the reasoning "4.14 appears nowhere" in Leota et al.
2025. I confirmed that against the PDF in this repository: the paper's high-strain-versus-
none values are 2.91 at two hours before sleep and 5.59 at sleep onset, and 4.14 is neither.
One file was corrected and its twin was not. The narrow exception granted on 4 September
covers exactly this case.

Second: `compute_baseline` fixed the **centre** to be the person's own median after seven
nights, and left the **scale** as a permanent blend, `0.8 x personal + 0.2 x 8.64`. The
identical argument applies. Measured on a subject with 28 nights of steady data: personal
spread exactly 0, scale **1.728**, entirely the population contribution.

**Why.** Exertion at 4.14 is the second largest effect in the table and competes directly
with infection to explain a raised night; correcting it to 2.91 raises p(infection) on every
elevation. The scale sets `robust_z`, which is the unit the extreme-heart-rate rules are
written in, so item 3 depends on this being real.

**Risk of doing it.** Un-shrinking the scale narrows the displayed band for steady people
and widens it for variable ones. Keep `BASELINE_SCALE_FLOOR_BPM = 1.5`, which exists because
median absolute deviation is exactly zero on whole-number heart rates, and check that a very
steady person does not end up with every night at a large `robust_z`.

## 7. Pass cycle applicability into the belief model
**FIX · Effort S · Risk: low**

**What.** No production caller passes `luteal_applicable` or `context` to `update_belief`.
`_cycle_applicability(answers)` already exists and is already computed in `node_conclude`
for the displayed reason. Pass it in `node_believe`, `node_decide` and `node_conclude`. The
same change makes `has_recent_illness` reach `recovery_tail`.

**Why.** One of the twelve causes is inert by construction, and `probe_cycle` can be asked,
costs 0.4 of an interruption, and its answer cannot move anything. Confirmed live: luteal
0.0 throughout an episode.

**Risk of doing it.** For a menstruating user this makes luteal the largest benign
explanation on roughly 45 percent of nights, which will reduce p(infection). That is the
correct behaviour and it is why the three-state fix was made; it just needs the third state
to be reachable.

## 8. Make `get_data_quality` return the data
**FIX · Effort S · Risk: low**

**What.** It ignores `db` and `args` and returns `{"coverage_ratio": 0.95, "missing_hours":
0.35, "dropped_samples": 0}` on every call. Read `coverage_minutes` and
`implausible_dropped` from `nightly_features`, which the belief model already uses.

**Why.** A health system handing fabricated numbers to its own reasoning layer, on the one
tool whose job is to inform judgements about sensor artefact. Confirmed in the audit log of
a live run, on nights whose real coverage was 341 to 362 minutes.

**Risk of doing it.** The agent will start seeing genuinely poor nights and may reason about
sensor artefact more often, which is the point.

## 9. Make the execution trace tell the truth
**FIX · Effort M · Risk: low**

**What.** `get_episode` builds pipeline stages by matching `CANONICAL_STAGES` names against
`audit_events.operation`, and that column is a `Literal` of ten values containing no stage
name. No row can ever match, so every stage renders SKIPPED with an invented reason. Either
write an audit row per node (the schema already reserves `invoke_agent` and `plan`), or
derive the trace from the graph state that `step_episode` already has in hand.

**Why.** The panel currently says "Ask probe not selected by EVSI optimizer" on an episode
whose own summary reports one question asked, and "Human review checkpoint bypassed" as the
only accurate line. `stage.detail_json` is always empty so the tool-call expander never
renders. This is the rubric's "observable workflow: visible planning steps, state changes,
and tool calls" and it is the most visible defect in the product.

**Risk of doing it.** Writing one audit row per node will roughly triple the volume of the
audit log. Prefer deriving the trace from graph state, and keep the audit log for decisions.

## 10. Name the source on Telegram
**FIX · Effort S · Risk: none**

**What.** `format_for_telegram` renders `f"Sources: {titles}"` from chunk titles.
`wha.ui.components.citations.source_label` exists for exactly this and is not imported.
Move it out of `ui/` into a shared module and use it on both surfaces.

**Why.** Confirmed live during this review: a real Telegram message ended `Sources: Fever`
for a MedlinePlus passage, with no mention of MedlinePlus or the National Library of
Medicine. MedlinePlus is attribution-only licensed, and the passage text itself carries the
attribution line that is being dropped. This closes the open blocker in `BLOCKERS.md`.

Also fix the truncation: 900 characters cuts mid-sentence, and in one real message the cut
fell inside the amber "not from a cited source" block. Truncate at a sentence boundary and
never inside the uncited section.

## 11. Fix the four sentences on the Today page
**FIX · Effort S · Risk: none**

**What.** Three factual errors in one expander, plus one forbidden phrase:

| Says | Should say |
|---|---|
| "in contact for 362 minutes between midnight and 7am" | over the sleep your watch recorded, when `rhr_window_source == "sleep"` |
| "Your lowest sustained rate between midnight and 7am" | the median heart rate across that window |
| "subtracting what a recorded workout **or short sleep** would be expected to add" | only a recorded workout; `explained.py` says short sleep is never subtracted |
| "Probably nothing to worry about" (the LIKELY_BENIGN headline) | anything not on the never-say list |

**Why.** The first three misdescribe the project's own headline design decision on the
screen a person reads every day, and the History page describes them correctly, so the two
screens disagree. The fourth is a phrase `red_flags.yaml` lists among those the system must
never say, and the false-reassurance filter runs on model output but not on the interface's
own hard-coded strings.

**Risk of doing it.** None. Add a test that the interface's own wording table contains no
phrase from `never_say`.

## 12. Fix the four small record defects
**FIX · Effort S each · Risk: none**

- `node_ask` calls `upsert_interaction` without `text_source`, which defaults to
  `"fallback"`, so every question is recorded as having used the canned sentence. Confirmed
  live: the stored text was model-written and the record said otherwise.
- `EpisodeOutcome` hard-codes `baseline_nights=28` and `baseline_rung=MATURE` on every
  outcome regardless of the subject's real baseline. The correct values are one `db` call
  away and `node_conclude` already makes that call for the disposition.
- `action_val = "rest" if LIKELY_ILLNESS else "monitor"` means an **ESCALATED** episode
  records the recommended action as "monitor".
- `stripped_claims` is set to `[]` in `get_episode` and never filled, so the Evidence tab
  always shows "No claims were stripped" whatever happened.

---

# Tier 2. Honesty.

## 13. Say on screen which numbers are guesses
**UNEVIDENCED · Effort M · Risk: none**

**What.** The rule this project sets itself is that an unevidenced choice is stated in the
docs **and on the dashboard**. About thirty probe likelihood numbers, three cause effect
sizes, two policy thresholds and two vitals thresholds are declared unevidenced in the files
and are indistinguishable on screen from figures backed by a study of 14,689 people.

The differential panel already quotes them at you: "That answer is expected in 25% of cases
where this is contributing, against 3% where it is not (probes.yaml, probe_symptoms,
provenance ASSUMED)". The provenance is there and it is in small print at the end. Make it a
visible marker.

**Why.** It is the project's own rule, and `probes.yaml` is unusually honest about the
problem: "A model asked to cite these will search, find nothing, and produce a confident
number anyway."

## 14. Correct three citations that do not say what they are used to say
**FIX · Effort S · Risk: none**

- **The infection percentages** are from Natarajan, Su and Heneghan 2022, *Frontiers in
  Physiology* 13:898251, not Mishra et al. 2020. Correct
  `docs/CORPUS-VERIFICATION.md` and `causes.yaml`, and record it in
  `docs/KNOWLEDGE-CHANGELOG.md`.
- **The blood oxygen thresholds** are NHS England and British Thoracic Society guidance, not
  WHO. WHO's January 2021 guidance recommends *using* home pulse oximetry; the 94 and 92
  action thresholds are the UK ones. Also record that they are validated for people
  **already known to have COVID-19**, not for screening a healthy person.
- **Downie et al. 2013** is a systematic review of red flags for **malignancy and fracture in
  low back pain**. The quotation is accurate and the population is not the one it is used to
  justify. Sutaria et al. 2025 supports the same conclusion directly and should carry the
  argument.

Two smaller ones: `POP_PRIOR_CITATION_PLAIN` should say first-year university students aged
18 to 24 rather than "525 adults"; and the pulse oximetry caution is stated more strongly
than the review, whose own conclusion is that the overestimation "may not be clinically
relevant".

## 15. Publish the detection accuracy, and answer the delegated question
**Effort M · Risk: none**

**What.** `EVALUATION.md` says detection accuracy is "not evaluated" because the datasets are
absent. `BLOCKERS.md` A-25 and A-26 wait for a human to author `cohort_labels.yaml`. The data
is a public 378 MB download and the labels are in the paper's own Supplementary Data 1, on
the same date shift. It took about forty minutes.

Answer the delegated decision ("fetch them if accuracy needs them, leave them if not, but
decide") with: **fetch them**, and put the numbers in `EVALUATION.md`:

| Detection window | This system | NightSignal | Random, matched |
|---|---|---|---|
| 3d before, 1d after | 53.3% | 46.7% | 20.2% |
| 7d before, 3d after | 73.3% | 66.7% | 40.4% |
| 21d before, 7d after | 83.3% | 80.0% | 73.5% |

Strictly pre-symptomatic at the 7 day window: **43.3%** against 33.3% for the reference.
Alert burden on 76 people with no illness label, 738 person-weeks: **one investigation every
3.6 weeks** against 4.5 for the reference.

Report the wide-window number **with** the chance floor beside it or not at all. 83 percent
against a 73.5 percent chance floor is not a result.

**Risk of doing it.** The honest headline is lower than the 80 percent the project currently
quotes from NightSignal. It is also the first real evidence the project has, and it says the
detector works.

## 16. State the four deviations from the published algorithm
**Effort S · Risk: none**

The window, the step filter, mean versus median, the baseline window, and the looser
red-alert rule all differ from the algorithm whose thresholds and sensitivity this project
cites. The cohort measurement shows the trade is favourable. Write it down as a decision
rather than leaving it as an undocumented divergence.

While there: adding NightSignal's **zero-step filter** is nearly free and would remove
exactly the motion artefact that the sensor-artifact cause exists to model. Worth testing
on the cohort harness before adopting.

---

# Tier 3. Delete.

Deleting is the cheapest way to make this project better, and a deletion with a reason
written down is a stronger result than a feature.

## 17. Delete the Chronos forecast
**DROP · Effort S · Risk: low, and it costs you a talking point**

182 MB of model weights, a PyTorch dependency, a per-night inference, and one advisory
paragraph on one screen that changes no decision by design. The project's own cited evidence
argues against ever giving it more: Alavi et al. 2022 measured plain baseline deviation at
78 percent sensitivity against 44 percent for a forecast-style detector at the same false
signal rate.

**If you keep it, keep it for the report and say so.** Demonstrating a time series
foundation model is a legitimate reason for a coursework project. It is not a clinical one,
and the write-up should not imply otherwise.

## 18. Delete `get_local_disease_activity`
**DROP · Effort S · Risk: none**

It fetches a government endpoint with no query parameters and returns
`{"status": "active", "bytes": <length>}`. It never parses dengue clusters, never checks
whether you are inside one, and never queries the air quality endpoint that is also
allow-listed. `sources.yaml` claims "A subject inside an active cluster materially raises the
dengue prior, and no shipped product does this." Nothing raises any prior, and there is no
dengue cause to raise.

Implementing it properly means adding a cause and a likelihood, which is a clinical decision
and a large piece of work. Delete the tool and the claim, and put "local outbreak context"
in the further-work section where it belongs.

## 19. Delete the MEASURE limb, or fix all three breaks
**DROP · Effort S to delete, M to fix · Risk: low**

Three independent breaks: nothing writes to the `measurements` table,
`AWAITING_MEASUREMENT` is never set, and the resume logic hard-codes "declined". So the
policy can select it, a notification goes out, and the answer can never come back.

Before fixing, ask whether it earns three fixes. It fires only when sensor artefact leads
the differential at 0.5 or more, which is an unevidenced threshold, and it asks a person to
count their pulse for 30 seconds and double it, a measurement with considerable error of its
own. The simpler honest behaviour is to tell the person the night could not be judged.

## 20. Delete the unreachable belief code
**SIMPLIFY · Effort S · Risk: none**

`compute_residual_loglik` exists twice, in `belief/likelihood.py` and `belief/inference.py`,
with different index clamping. Coverage over a production run shows the `likelihood.py` copy
and the whole of `run_exact_inference` never execute. Delete the unreachable pair and keep
one implementation, in the module the project says the arithmetic must be checkable in.

## 21. Delete or enforce `CONVERSATION_MAX_TURNS`
**SIMPLIFY · Effort S · Risk: low**

The code computes whether you are at the limit, attaches it to the reply, and nothing reads
it. A stop condition that does not stop anything is worse than none, because it appears in
the report as a control that exists. Either refuse past the limit with a message that names
why, or delete the constant, the field and the AMIE citation.

## 22. Collapse the second escalation path
**SIMPLIFY · Effort M · Risk: low**

`report_symptoms` reimplements "check the floor, open an episode, close it ESCALATED,
notify", and is reachable only from the CLI and the demo harness. The dashboard and Telegram
both route free text to the conversation engine instead, which does not create episodes. So
"I have chest pain" behaves differently depending on the surface you type it into.

The live database holds **five identical closed ESCALATED episodes**, same dates, step count
zero, all displayed separately on History, all from this path. Pick one path. The
conversation engine is the better one; give it the ability to open and close an episode, and
make the CLI call it.

## 23. Drop `one_time`, or implement it
**Effort S · Risk: none**

`probes.yaml` marks two probes `one_time: true` and justifies their low interruption cost
with "asked once and then becomes a modelled covariate". The loader never reads the field
and drops it silently. Either honour it across episodes or delete it and re-price the two
probes.

---

# Tier 4. Worth doing if there is time.

## 24. Add a reranker
**Effort M · Risk: low**

There is none today; RRF is fusion, not reranking. The relevance problems are exactly what a
reranker fixes: for a fever episode four of five cited passages were about meningism, and
the top-ranked "evidence" was the list of answer options for the symptom question. A small
cross-encoder over the top 20 candidates is a well-understood addition and would be the
highest-value retrieval change available.

## 25. Stop the generated corpus layers leaking the internals
**Effort S · Risk: none**

Layers 2 and 3 are generated from YAML, so the passages shown to a lay reader include the
raw phrase-match lists and the whole tier B table with its trigger phrases. That is the
internal keyword list presented as clinical evidence, and it publishes exactly which words
cause an escalation. Generate prose from those files rather than rendering them.

## 26. Give urgency an expiry
**Effort M · Risk: medium**

Urgency is the maximum over the entire transcript with no time limit, so a "see a doctor
today" banner from days ago is still at the top of Today, undated, with no way to resolve
it. Training a person to ignore a persistent red banner is the alarm fatigue this project
cites in its own constants.

**Risk of doing it.** Urgency must never fall through reasoning. An expiry is not reasoning,
but it must be explicit: show the date it was set, and ask the person to confirm they sought
care rather than silently dropping it.

## 27. Rename the differential panel, or change what it shows
**Effort M · Risk: low**

The twelve numbers are independent marginal probabilities that do not sum to one and do not
compete. Labelled "Cause Differential" and drawn as a ranked bar chart, they read as a
differential diagnosis. Measured on a real closed episode: disposition LIKELY_ILLNESS, chart
underneath showing **stress at 0.9228** in first place, with the attached reason "Nothing
gathered in this episode speaks to this cause either way."

Cheapest fix: rank by **how much this episode's evidence moved each cause** rather than by
absolute probability, and say in the heading that these are independent probabilities. That
turns a misleading chart into the most informative one in the product.

## 28. Fix the audit padding and the empty latency column
**Effort S · Risk: none**

`record_ingest` skips only when zero rows were written, and re-pulling the same window
rewrites the same rows, so the live log holds five consecutive entries minutes apart all
reading "9785 heart rate samples arrived", under a caption that says a check finding nothing
new does not appear. Compare against the last recorded count, or record the newest sample
timestamp instead.

The tool registry measures each call's duration into `_latency_ms` and discards it, so the
audit's latency column is always null and the trace's duration is always None.

---

# What I would not do

- **Do not add StatPearls or the Singapore care-pathway layer yet.** Both are recorded as
  missing and `sources.yaml` describes them as present. Correct the description first. The
  corpus is already fourteen times the size it was and the measured problem is relevance,
  not volume.
- **Do not add more causes.** Twelve is already more than the evidence supports for several
  of them, and the ranked display problem gets worse with each one.
- **Do not build multi-user support.** One person, one phone. The API is unauthenticated on
  purpose and the reasoning is written down.
- **Do not weaken a scenario expectation to accommodate item 5.** If raising the infection
  effect breaks a frozen scenario, measure the new behaviour, decide whether it is correct,
  and change the expectation with the reason in the commit. Measure, then assert.
- **Do not chase the remaining unevidenced numbers with more searching.** I looked. The
  self-report likelihoods do not exist in the literature and `probes.yaml` is right that
  better data will not fix that, because the measurement has not been made. Label them and
  move on.

---

# If you only have one day

1. Item 1, escalation criteria through the checks. One hour, and it is the biggest safety
   hole in the system.
2. Item 11, the four sentences on Today. One hour, and it is the most-read screen.
3. Item 10, name the source on Telegram. Half an hour, and it closes an open blocker and a
   licence obligation.
4. Item 15, publish the detection numbers. Two hours, and it turns the project's weakest
   claim into its strongest one.
5. Item 17 and 18, delete Chronos and the disease activity tool. One hour, and the project
   gets smaller and more honest at the same time.

That is a day, it removes the worst safety gap, it makes the main screen truthful, and it
gives the project the evidence it has been missing since it started.
