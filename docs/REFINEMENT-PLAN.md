# Refinement plan

What to do, in the order that buys the most, with the reason and the steps for each one.

Written 4 September 2026 from `docs/DESIGN-REVIEW.md`. The papers are in
`docs/EVIDENCE-LOG.md`. **You can read this file on its own.** Every part of the system that
needs work has an item here, and the coverage table below proves it.

---

## How to read an item

Each item starts with a word that says what kind of change it is.

| Word | What it means |
|---|---|
| **FIX** | The idea is right. The number or the wiring is wrong. Repair it. |
| **SIMPLIFY** | It works, and it is more complicated than the job needs. Cut it down. |
| **DROP** | It does not earn its place. Delete it, and write down why. |
| **UNEVIDENCED** | It is a guess. Nothing is broken. Label it as a guess on screen. |
| **KEEP** | It is right and it is evidenced. Leave it alone. These are listed at the end. |

Then each item answers four questions:

- **The problem** is what is actually wrong, in one or two sentences.
- **Why it matters** is what happens to you if it stays as it is.
- **How to do it** is the concrete steps, with the file names.
- **How you will know it worked** is the check. Not a test passing. A thing you look at.

**Effort** is focused work: **S** under an hour, **M** a few hours, **L** a day, **XL** a
day plus a decision only you can make.

---

## Coverage: every part of the system, and where it lands

66 parts were reviewed. 26 are fine and need nothing. The other 40 are all below.

| Part of the system | Verdict | Item |
|---|---|---|
| Escalation criteria are checked by nothing | FIX | **1** |
| Human review checkpoint approves itself | FIX | **2** |
| Blood oxygen rule has never run | FIX | **3** |
| The two extreme heart rate rules have never run | FIX | **3** |
| Marburg age gate never gets an age | FIX | **4** |
| infection effect of 1.60 bpm | FIX | **5** |
| exertion effect of 4.14 bpm in `causes.yaml` | FIX | **6** |
| Baseline band width still borrowed from strangers | FIX | **6** |
| Cycle answer never reaches the belief model | FIX | **7** |
| `get_data_quality` invents its numbers | FIX | **8** |
| Execution trace says every stage was skipped | FIX | **9** |
| Telegram does not name the source | FIX | **10** |
| Today page says three things that are not true | FIX | **11** |
| "Probably nothing to worry about" headline | FIX | **11** |
| Question record always says "fallback" | FIX | **12** |
| Baseline nights and rung hard-coded in the outcome | FIX | **12** |
| An escalated episode recommends "monitor" | FIX | **12** |
| "Stripped claims" panel is always empty | FIX | **12** |
| Offers a temperature reading the watch cannot take | FIX | **13** |
| Alcohol amount collected and thrown away | FIX | **14** |
| Thirty answer likelihoods are guesses | UNEVIDENCED | **15** |
| Travel, short sleep and unexplained effect sizes | UNEVIDENCED | **15** |
| The amber "not from a cited source" label | UNEVIDENCED | **15** |
| Population figure described as "525 adults" | FIX | **16** |
| Blood oxygen thresholds credited to WHO | FIX | **16** |
| Downie 2013 used outside its population | FIX | **16** |
| Detection accuracy says "not evaluated" | FIX | **17** |
| Alert rule looser than the published one | FIX | **18** |
| Median instead of mean, and no step filter | FIX | **18** |
| Two corpus layers described but never built | FIX | **19** |
| Reranking described but absent | DROP the claim | **19** |
| Sleep window justified more widely than measured | FIX | **19** |
| Chronos forecast | **DROP** | **20** |
| `get_local_disease_activity` | **DROP** | **21** |
| The MEASURE limb | **DROP** | **22** |
| Two copies of the same belief maths | SIMPLIFY | **23** |
| `CONVERSATION_MAX_TURNS` does nothing | FIX or DROP | **24** |
| Two different escalation paths | SIMPLIFY | **25** |
| `one_time` on a probe does nothing | FIX | **26** |
| Weekly interruption budget that never binds | SIMPLIFY | **27** |
| Retrieval brings back the wrong passages | FIX | **28** |
| Corpus leaks the internal keyword lists | FIX | **29** |
| Urgency never expires | FIX | **30** |
| The differential chart misleads | FIX | **31** |
| Audit log padded, and no timings | FIX | **32** |

---

## Two rules to hold while doing any of this

1. **Do not make a test pass by changing the test.** Every problem on this list was
   invisible to 546 passing tests. A test that proves a fix must exercise the whole path,
   not the one function.
2. **Finish by using the product.** Open the page. Send the message. Every problem here was
   found by running the system, not by reading it. Reading the fix is not checking the fix.

---

# Tier 0. Safety. Do these first.

## 1. Check the "when to seek care" text

`FIX` · Effort **S** · Risk **low**

**The problem.** The outcome has a field that tells you when to seek care. The AI writes it.
It is the only text in the system that goes through no check at all.

**Why it matters.** In a real run the AI wrote:

> "Seek care if fever persists beyond 72 hours or exceeds 103°F (39.4°C)"

Those numbers came out of the model's head. This is the sentence most likely to make you
act, and it is the least checked thing on the page. A study that red-teamed four chatbots
with 222 patient questions found 5 to 13 percent of answers were outright unsafe.

The odd part is that the guard already exists. `sanitize_fabricated_numbers_in_prose` in
`src/wha/safety/output_checks.py` would have deleted 72, 103 and 39.4. It is just pointed at
a different field.

**How to do it.**

1. Open `src/wha/safety/output_checks.py`, function `validate_and_sanitize_outcome`.
2. It already runs the number filter on `outcome.observation`. Run it on each string in
   `escalation_criteria` too.
3. In `src/wha/agent/nodes.py`, function `node_conclude`, the model's claims already go
   through `_enforce_claims`. Send the escalation criteria through the same containment
   check, so a sentence only survives if its supporting text was really retrieved.
4. If everything the model wrote is stripped, fall back to the human-written default. That
   is the correct failure, not a bug.
5. Those defaults are clinical sentences living in Python, in `node_conclude` and in
   `DEFAULT_ESCALATION_CRITERIA`. They are the only clinical text in the codebase not in
   `data/knowledge/`. Move them into `red_flags.yaml` with the rest of the care wording.

**How you will know it worked.** Run one live episode. Open the outcome. Every number in the
"when to seek care" text should be a number the system actually holds, or the text should be
the human-written fallback. No invented temperature, ever.

**What could go wrong.** The fallback text may be so general it becomes wallpaper you stop
reading. Write it once, properly, and keep it short.

## 2. Let a human do the human review

`FIX` · Effort **S** · Risk **medium, episodes will stop closing on their own**

**The problem.** The system drafts a conclusion and pauses for you to approve it. A
background job then answers "approve" on your behalf fifteen minutes later, and the record
says a human approved it.

**Why it matters.** This is the one place a person is supposed to be able to say "no, that
is wrong" before the system commits to a conclusion about their health. It has never been
possible. The record showing a human decision that never happened is worse than having no
checkpoint at all.

**The evidence.** A live run: episode `ep_3637eaf58033` went from waiting-for-you to closed
in a single tick, with nobody involved.

**How to do it.**

1. In `src/wha/service/scheduler.py`, function `_resume_value`: it handles a question and a
   measurement, then falls through to `return {"decision": "approve"}` for anything else.
   Return `None` instead. `None` means "leave it parked".
2. In `src/wha/agent/nodes.py`, function `node_review`: before the `interrupt()` call, do
   `db.set_episode_state(episode_id, "AWAITING_HUMAN_REVIEW")`. Without this the review can
   never appear on screen. `node_ask` already does the same thing one state along.
3. Add a timeout so nothing waits forever. If nobody reviews inside
   `ANSWER_TIMEOUT_HOURS`, close the episode and **record that it closed unreviewed**. Do
   not record an approval.

**How you will know it worked.** Open an episode to the end. The dashboard should show a
draft waiting for you with approve, edit, reject and escalate buttons. Click reject. The
episode should close as UNRESOLVED.

**What could go wrong.** You may not open the dashboard for days, and outcomes will pile up.
That is why step 3 exists. Do not skip it.

## 3. Connect the three safety rules that have never run

`FIX` · Effort **M** · Risk **medium, this can newly wake you at night**

**The problem.** Three rules are written, tested on their own, and connected to nothing.

- The blood oxygen rule (`check_overnight_oxygen` in `src/wha/safety/rules.py`) is called by
  no code and by no test.
- The two extreme heart rate rules need a number called `robust_z`. All three places that
  run the safety check pass only the text you typed, so that number is always missing and
  the rules are skipped.

**Why it matters.** A night six times further from your normal than usual currently raises
nothing, unless you happen to type a warning phrase yourself. A safety floor that only fires
on what you say is not a floor on your data.

**The evidence.** Line coverage over a whole production run: `src/wha/safety/rules.py` lines
162 to 178 and 253 to 266 never execute.

**How to do it.**

1. Do item 6 first. `robust_z` is currently divided by a band width that is one fifth
   borrowed from other people, so the threshold does not yet mean what it says.
2. In `src/wha/service/nightly.py`, function `run_nightly`, after `detect_range` returns:
   for each detection, call `check_red_flags_deterministic` passing `robust_z`, `rhr_bpm`
   and the baseline `rung`, which are all already there.
3. In the same place, call `check_overnight_oxygen` with the connection, the subject, and
   the sleep window for that night.
4. If either raises an escalation, send it the same way a self-report does. Reuse
   `_notify_escalation` in `src/wha/service/symptom_report.py` rather than writing a second
   notification path.

**How you will know it worked.** Before shipping, run the rules over the cohort data using
`scratch/cohort_eval.py`. It will tell you how often `robust_z` goes above 6 across 8,508
real nights. If that number is large, the threshold is wrong, not the wiring.

**What could go wrong.** This is the only item that can send you a new alert in the middle
of the night. Measure the trigger rate first. Do not ship it blind.

## 4. Give the chest pain rule the age it already knows

`FIX` · Effort **S** · Risk **low, it means more escalations not fewer**

**The problem.** The Marburg Heart Score was tested only on people aged 35 and over. The
code checks for that. But the age is never filled in, so the check never fires and the rule
runs on everybody.

**Why it matters.** In a real run the person typed "I am 24 and male". The system correctly
pulled that out and stored it. Then it applied a rule that was never tested on 24 year olds,
scored 3 out of 5 on three things that are common in a young adult with a pulled muscle,
told them it was urgent, and cited "a 2010 study of 1,199 people with chest pain".

**The evidence.** Bösner et al. 2010 built the rule on "1,199 unselected and consecutive
patients aged >= 35 years".

**How to do it.** Pick one of these two.

- **Easier:** in `src/wha/agent/conversation.py`, function `respond`, read the age out of the
  stored answer for `mhs_age_sex`. The person's own words are already saved next to it.
- **More reliable:** add a one-off age question to the Settings screen, store it on the
  subject, and pass it through `send_message` into `triage()`. The parameter chain already
  exists end to end and is simply never filled.

**How you will know it worked.** Type a chest pain message and say you are 24. The reply
should say the rule was not applied because it was only tested on people 35 and over, and it
should route you conservatively rather than scoring you.

**What could go wrong.** Everyone under 35 now gets escalated instead of scored. That is
more caution, not less, and `triage_rules.yaml` already says that is the intended direction.

---

# Tier 1. Things the documents say work, and do not.

## 5. Correct the infection effect size

`FIX` · Effort **XL, it needs a decision only you can make** · Risk **high, it changes everything downstream**

**The problem.** `causes.yaml` says an infection raises your overnight heart rate by 1.60
bpm. Three things are wrong with that number.

1. **It is credited to the wrong paper.** `docs/CORPUS-VERIFICATION.md` says the figures
   "1.8% for females and 3.4% for males" come from Mishra et al. 2020. I fetched that paper
   and searched it. They are not in it. They come from Natarajan, Su and Heneghan 2022,
   *Frontiers in Physiology* 13:898251, which nothing here cites.
2. **The sum mixes two different groups of people.** A percentage measured on 7,200 Fitbit
   users is multiplied by 62.75 bpm, which is the average of 525 first-year university
   students from a different study. And because it is a percentage, it shrinks for people
   with slow hearts: on your own nights of 44 to 47 bpm, the same percentages give **0.8 to
   1.5 bpm**, not 1.1 to 2.1. The detection thresholds are fixed numbers, so the system is
   quietly less sensitive for you than for an average person.
3. **It contradicts the paper the thresholds come from.** Nothing is looked at below 3.0
   bpm. Alavi et al. 2022, which supplies that 3.0, reports that 67 of 84 infected people
   (80 percent) crossed a 4 bpm alert. An infection that only ever adds 1.60 bpm cannot do
   that.

**Why it matters.** This is the number the whole system turns on. In a live run with two
nights at +5.0 bpm, before any question was asked:

```
infection         0.0756
stress            0.8147
alcohol           0.5536
short sleep       0.4813
```

The one thing the system exists to find came fourth, behind three harmless explanations that
are modelled as bigger. `BLOCKERS.md` already records this as "LIKELY_ILLNESS is unreachable"
and asks which of three numbers is wrong. It is this one.

**How to do it.**

1. Decide the replacement number. **I am not choosing it for you.** Mishra reports a median
   rise of 7 bpm during detected abnormal periods, but that only counts people who were
   already detected, so it is biased upward. This is a clinical judgement.
2. Write the reasoning and the quoted source sentence into
   `docs/KNOWLEDGE-CHANGELOG.md`, which is what that file is for.
3. Change `effect_mean_bpm` for infection in `data/knowledge/causes.yaml`, and fix its
   `citation` block to name Natarajan et al. 2022.
4. Re-run `uv run wha eval-report` and all eleven frozen scenarios.
5. Expect several scenario expectations to move. **Measure what the system now does, decide
   whether it is right, then change the expectation and say why in the commit.** Never the
   other way round.

**How you will know it worked.** Run the illness simulation again. On two nights at +5.0
bpm, infection should be near the top of the list, not fourth. The agent should still ask
only one question.

**What could go wrong.** A bigger infection effect means more questions and more
LIKELY_ILLNESS conclusions. That is the intended direction, but it must be measured, not
assumed.

## 6. Two corrections to the maths, both in the same direction

`FIX` · Effort **S** then **M** · Risk **low** then **medium**

**The problem, part one.** `causes.yaml` says unrecorded exercise raises heart rate by 4.14
bpm. That number was already removed from `constants.py` on 4 September because it is not in
the paper. I checked the PDF in this repository: the paper's values either side are 2.91 and
5.59, and 4.14 is neither. One file was corrected and its twin was missed.

**The problem, part two.** The baseline has two parts: the **centre** (your usual heart
rate) and the **band width** (how much you normally wobble). The centre was fixed to be
your own after seven nights. The band width was not. It is permanently
`0.8 x yours + 0.2 x a stranger's`, so a fifth of it never becomes yours.

**Why it matters.** Exercise at 4.14 bpm is the second biggest effect in the table, and it
competes directly with infection to explain a raised night. Making it smaller makes
infection more visible, which is the same direction as item 5.

The band width sets `robust_z`, which is the unit the extreme heart rate rules are written
in. Measured on a subject with 28 nights of perfectly steady data, their own wobble was
exactly zero and the band width came out at **1.728**, which is entirely the borrowed part.
Item 3 cannot be trusted until this is real.

**How to do it.**

1. Change `effect_mean_bpm` for exertion in `data/knowledge/causes.yaml` from 4.14 to 2.91,
   and fix the derivation text, which currently claims 4.14 is the paper's figure.
2. Record it in `docs/KNOWLEDGE-CHANGELOG.md` with the quoted table values. The narrow
   exception granted on 4 September covers exactly this case.
3. In `src/wha/detect/baseline.py`, function `compute_baseline`: it already switches the
   centre to the personal median once there are `BASELINE_MIN_NIGHTS_PERSONAL` nights. Do
   the same for `scale_bpm`.
4. Keep `BASELINE_SCALE_FLOOR_BPM = 1.5`. It exists because heart rates are whole numbers,
   so the wobble can come out as exactly zero, and dividing by zero makes every night look
   infinitely abnormal.

**How you will know it worked.** Look at the History chart for a steady subject. The band
should get narrower as their own nights accumulate, and stop moving once it is theirs.

**What could go wrong.** A very steady person could end up with a very narrow band, so
ordinary nights start looking abnormal. The 1.5 floor is what prevents that. Check it on
your own data before and after.

## 7. Let the cycle answer reach the belief model

`FIX` · Effort **S** · Risk **low**

**The problem.** One of the twelve causes, the menstrual cycle, is switched off and cannot
be switched on. The belief model takes a "does this apply" flag. No code anywhere passes it.

**Why it matters.** The system can ask you the cycle question, spend part of your weekly
interruption allowance on it, and your answer changes nothing. Confirmed on a live run:
that cause sat at exactly 0.0 from start to finish. The same missing wire also means the
"recently recovering from an illness" boost never happens either.

**How to do it.**

1. `src/wha/agent/nodes.py` already has `_cycle_applicability(answers)`, and `node_conclude`
   already calls it for the text shown on screen.
2. Pass its result into every `update_belief(...)` call, as `luteal_applicable`. There are
   three: in `node_believe`, in `node_decide`, and in `node_conclude`.
3. While there, build the `EpisodeContext` with `has_recent_illness` and pass it too. The
   belief model already reads it and nothing supplies it.

**How you will know it worked.** Answer the cycle question with "started more than 2 weeks
ago". The cause should move off 0.0 in the belief chart on the Trace tab.

**What could go wrong.** For someone who menstruates, this becomes the biggest harmless
explanation on about 45 percent of nights, which pushes infection down. That is correct
behaviour, and it is exactly why the three-state design was chosen. It just needs the third
state to be reachable.

## 8. Make `get_data_quality` read the data

`FIX` · Effort **S** · Risk **low**

**The problem.** One of the seven tools the AI can call returns the same three made-up
numbers every single time, for every person, on every night: `coverage_ratio 0.95`,
`missing_hours 0.35`, `dropped_samples 0`. It never looks at the database.

**Why it matters.** This is a health system feeding invented numbers to its own reasoning.
It is also the one tool whose job is to tell the AI whether the watch might have misread the
night. Confirmed from the audit log of a live run, on nights whose real coverage was 341 to
362 minutes. The real numbers are already in the database and already used by the belief
maths, so the AI and the arithmetic are being told different things about the same night.

**How to do it.**

1. Open `src/wha/agent/tools/impl.py`, function `tool_get_data_quality`.
2. It receives `db` and ignores it. Call `db.get_nightly_features(subject, start, end)`,
   which already exists and is used by the tool directly above it.
3. Return the real `coverage_minutes` and `implausible_dropped`, plus how many nights in the
   range were unusable.

**How you will know it worked.** Run an episode and open the Audit page. The recorded result
for that tool should show the same coverage figures you can see on the History table.

**What could go wrong.** The AI will start seeing genuinely poor nights and reasoning about
sensor problems more often. That is the point.

## 9. Make the execution trace tell the truth

`FIX` · Effort **M** · Risk **low**

**The problem.** The Trace tab lists nine stages and marks **every one of them as skipped**,
on every episode, with a made-up reason. It says "Ask probe not selected by EVSI optimizer"
on an episode that its own summary says asked a question.

**Why it matters.** This is the screen whose whole job is to show you what the system did.
It currently shows the opposite. The belief chart directly underneath it shows two real
steps and the probability moving from 0.2954 to 0.7774, so the page contradicts itself.

**The cause.** In `src/wha/service/episodes.py`, `get_episode` matches stage names against
the `operation` column of the audit log. That column can only hold ten fixed values, and
none of them is a stage name. So no row can ever match and nothing can ever be marked as
having run.

**How to do it.** Pick one. The second is better.

- **Option A:** write an audit row per node. The schema already reserves `invoke_agent` and
  `plan` for this. Downside: it roughly triples the size of the audit log and buries the
  tool calls, which are the entries that matter.
- **Option B, preferred:** build the trace from the graph state that `step_episode` already
  has in hand. It knows which nodes ran, `tool_call_count`, and `depth_used`. Store a small
  trace record on the episode row and read it back in `get_episode`.

Either way, fill in `stage.detail_json` with the tool calls, so the expander in
`src/wha/ui/components/pipeline_trace.py` finally renders something. It is already written
and has never had data.

**How you will know it worked.** Open a closed episode, click Trace. The stages that ran
should say so, with the tool calls listed underneath investigate.

**What could go wrong.** Option A makes the Audit page much noisier. Prefer B.

## 10. Name the source on Telegram

`FIX` · Effort **S** · Risk **none**

**The problem.** On the dashboard, a quoted passage is labelled "MedlinePlus, National
Library of Medicine". On Telegram the same passage is labelled `Sources: Fever`.

**Why it matters.** MedlinePlus is free to use **on condition that you credit it**. A topic
title is not a credit. This also closes an open item in `BLOCKERS.md`. Confirmed live during
the review by sending a real message and reading what came back.

**How to do it.**

1. `source_label()` in `src/wha/ui/components/citations.py` already does exactly this job.
   It lives under `ui/`, which the Telegram code correctly refuses to import.
2. Move it to a shared module, for example `src/wha/retrieve/attribution.py`.
3. Use it in both places: the dashboard component, and `format_for_telegram` in
   `src/wha/service/conversation.py`.
4. While there, fix the cut-off. Messages are trimmed at 900 characters and it currently
   cuts mid-word. In one real message it cut inside the amber "not from a cited source"
   block, which is the worst place to cut. Trim at a sentence end, and never inside that
   block.

**How you will know it worked.** Send yourself a general health question over Telegram. The
reply should name MedlinePlus and the National Library of Medicine in words.

## 11. Fix four sentences on the Today page

`FIX` · Effort **S** · Risk **none**

**The problem.** Three statements on the screen you read every day are wrong, and one uses a
phrase the system forbids itself from saying.

| It says | The truth |
|---|---|
| "in contact for 362 minutes **between midnight and 7am**" | that night was measured over the sleep your watch recorded |
| "Your **lowest sustained rate** between midnight and 7am" | it is the **median** across the window, not the lowest |
| "subtracting what a recorded workout **or short sleep** would add" | only exercise is subtracted; the code says short sleep never is |
| "Probably nothing to worry about" | `red_flags.yaml` lists "nothing to worry about" among the phrases the system must never say |

**Why it matters.** The first three misdescribe the single design decision this project is
proudest of, on the main screen. The History page describes all three correctly, so the two
pages disagree with each other. The fourth is the system breaking its own safety rule,
because the phrase filter runs on what the AI writes and not on the interface's own words.

**How to do it.**

1. `src/wha/ui/today.py`, around lines 199 to 207. The night already carries
   `rhr_window_source`. Say "over the sleep your watch recorded" when it is `"sleep"`, and
   "between midnight and 7am, because no sleep was recorded" when it is `"clock"`.
2. Same file: change "lowest sustained rate" to "the middle of your readings across that
   window".
3. Same file: delete "or short sleep".
4. `src/wha/ui/history.py` line 130 has the same clock wording. Fix it too.
5. `src/wha/ui/components/wording.py`, `DISPOSITION_PHRASES`: replace "Probably nothing to
   worry about" with something not on the never-say list. "Nothing here points to illness"
   is already the explanation underneath it and is fine.
6. Add a test that no phrase in `wording.py` appears in `never_say` in `red_flags.yaml`.

**How you will know it worked.** Open Today on a night measured over sleep. It should say
so. Then open a benign closed episode on History and check the headline.

## 12. Four small record defects

`FIX` · Effort **S each** · Risk **none**

**The problem.** Four places where the record states something that is not true.

- Every question is filed as having used the canned sentence, even when the AI wrote it.
- Every outcome claims 28 baseline nights and a fully established baseline.
- An escalated episode records the recommended action as "monitor".
- The "stripped claims" panel always shows a green tick.

**Why it matters.** These are all small, and they are all in the record. The record is the
thing you would show a doctor, and the thing that is supposed to let you check the system
rather than trust it. A record that quietly rounds four facts in the system's favour is
worth less than no record.

**How to do it.**

1. **The question source.** In `src/wha/agent/nodes.py`, `node_ask` calls
   `upsert_interaction` without `text_source`, and the default is `"fallback"`. Pass
   `text_source=updated_question.text_source`.
2. **The baseline figures.** In the same file, `node_conclude` hard-codes
   `baseline_nights=28, baseline_rung=BaselineRung.MATURE`. A few lines above it already
   calls `db.get_baseline_rung` for the disposition. Use the real values.
3. **The escalated action.** The line reads `"rest" if LIKELY_ILLNESS else "monitor"`, so
   ESCALATED falls into "monitor". Map ESCALATED to `seek_urgent_care`.
4. **The stripped claims.** `get_episode` in `src/wha/service/episodes.py` sets
   `stripped_claims = []` and never fills it. Store the stripped claim text on the outcome
   in `_enforce_claims`, and read it back here.

**How you will know it worked.** Open a closed episode from a subject with only a few
nights. The baseline number should match what History shows for them, not 28. Then run an
episode where a claim gets stripped, and check the Evidence tab lists it.

## 13. Stop offering things the watch cannot do

`FIX` · Effort **S** · Risk **none**

**The problem.** In a real Telegram message sent during this review, the agent wrote:

> "Would you like me to check your current temperature readings from your watch?"

The watch does not measure temperature and never has. The same message printed that
sentence twice.

**Why it matters.** An assistant offering a measurement it cannot take loses trust fast, and
it is easy to prevent. The duplication happens because the model put the same sentence in
both the reply and the question field, and the code adds the question on top.

**How to do it.**

1. In `src/wha/llm/prompts/converse.py`, add the list of channels the watch really provides
   to the prompt. `docs/DESIGN-DATA-CHANNELS.md` already has it: heart rate, steps, sleep,
   exercise, blood oxygen, distance, calories. State plainly that heart rate variability,
   breathing rate and temperature are not available.
2. In `src/wha/agent/conversation.py`, function `respond`, the line
   `text = f"{text}\n\n{question}"` should only run when the question is not already in the
   text.

**How you will know it worked.** Ask it about your temperature over Telegram. It should say
the watch does not measure that, and the reply should not repeat itself.

## 14. Stop asking for an amount you then ignore

`FIX` · Effort **S** or **XL**, depending on which route · Risk **low**

**The problem.** The alcohol question offers "None", "1 to 2", "3 to 4", "5 or more". The
belief model has one on-off alcohol switch. All three drinking answers do exactly the same
thing.

**Why it matters.** The system spends a whole interruption asking a more detailed question
than it can use. There is a smaller citation problem underneath too: the paper's 2.8 and 2.4
bpm figures are the gap between **one drink above** your average and **one below**, which is
a two-drink span, not the effect of drinking at all.

**How to do it.** Pick one.

- **Route A, free.** In `data/knowledge/probes.yaml`, reduce `probe_alcohol` to "None" and
  "Yes", and update the two likelihood rows. Keep recording the free text so the detail is
  not lost, it just does not pretend to feed the maths.
- **Route B, a decision.** Scale the effect by the reported amount. The source paper
  supports it: "Increases in alcohol intake were associated with dose-dependent increases in
  RHR." But choosing what "3 to 4 drinks" is worth in bpm is a clinical judgement, so this
  becomes an XL item like item 5.

**How you will know it worked.** Route A: the question on screen has two options. Route B:
answering "5 or more" moves alcohol further than answering "1 to 2" on the belief chart.

---

# Tier 2. Honesty. Say what is true.

## 15. Mark the guesses on screen

`UNEVIDENCED` · Effort **M** · Risk **none**

**The problem.** Nothing is broken here. Some numbers in this system come from studies of
tens of thousands of people. Others were guessed because no study exists. On screen they
look identical.

Three groups need a visible mark.

- **About thirty answer likelihoods** in `probes.yaml`. These convert what you say into a
  change in belief. The file is admirably honest about it: "no published measurement exists
  of how accurately a person reports drinking, stress or sleep to an app". The differential
  panel already quotes them at you, with the word ASSUMED in small print at the end.
- **Three cause effect sizes**: travel, short sleep, and "none of the above". All declared
  guesses in `causes.yaml`, all indistinguishable on screen from figures backed by 14,689
  people.
- **The amber "not from a cited source" label itself.** It relies on the AI sorting its own
  sentences, which is the same judgement the AI is making. In a real transcript it wrote
  "that's reassuring" straight into the reply with no warning, and on the next turn
  correctly moved a similar sentence into the amber box. The label is a floor, not a
  guarantee, and the screen implies otherwise.

**Why it matters.** The project's own rule is that a guess is stated in the documents **and**
on the dashboard. Two of these three are only in the documents.

**How to do it.**

1. In `src/wha/agent/differential.py`, `_answer_reasons` already reads `provenance` from the
   probe. Return it as a field rather than folding it into the sentence.
2. In the episode panel, show a small marker such as "estimated, no study" next to any line
   whose provenance is ASSUMED. Add one line of explanation under the chart.
3. Under the amber panel in `src/wha/ui/today.py`, add a sentence: this labelling is done by
   the AI itself and may miss things, so treat anything without a source as a starting point.

**How you will know it worked.** Open a differential on a closed episode. You should be able
to tell at a glance which lines rest on a study and which do not.

**While you are there.** "that's reassuring" is not on the `never_say` list and arguably
should be. That is a wording judgement about a human-written safety list, so it is yours.

## 16. Correct three citations

`FIX` · Effort **S** · Risk **none**

**The problem.** Three places where a source is credited with something it does not say.

1. **The infection percentages** are credited to Mishra et al. 2020. They come from
   Natarajan, Su and Heneghan 2022, *Frontiers in Physiology* 13:898251.
2. **The blood oxygen thresholds** are credited to WHO. WHO's January 2021 guidance
   recommends *using* home pulse oximetry. The 94 and 92 percent action levels are NHS
   England and British Thoracic Society guidance. They are also written for people **already
   known to have COVID-19**, not for screening someone healthy, which changes what they mean.
3. **Downie et al. 2013** is a review of red flags for **cancer and fracture in low back
   pain**. The quotation used is accurate; the population is not the one it is used to
   justify. Sutaria et al. 2025 supports the same conclusion directly and should carry the
   argument instead.

**Why it matters.** A citation is the whole basis on which this project asks to be trusted
with a clinical number. The rule you set yourself is that every clinical choice is backed by
a cited study. A citation pointing at the wrong paper fails that rule as completely as having
no citation, and it is harder to spot, because it looks correct.

**How to do it.** Edit `docs/CORPUS-VERIFICATION.md`, the `citation` block for infection in
`causes.yaml`, the `oxygen.citation` block in `triage_rules.yaml`, and the header comment in
`triage_rules.yaml` that quotes Downie. Record each change in `docs/KNOWLEDGE-CHANGELOG.md`
with the quoted sentence, as that file requires.

**Two smaller ones.** `POP_PRIOR_CITATION_PLAIN` in `constants.py` says "a 2024 study of 525
adults". They were first-year university students aged 18 to 24, which is the thing a reader
would want to know. And the skin-tone caution about pulse oximeters is stated more strongly
than its source, whose own conclusion is that the difference "may not be clinically
relevant".

**How you will know it worked.** Every citation in the corpus can be opened and the quoted
sentence found in the paper. That is what `docs/EVIDENCE-LOG.md` is for.

## 17. Publish the detection accuracy

`FIX` · Effort **M** · Risk **none**

**The problem.** `EVALUATION.md` says detection accuracy is "not evaluated" because the
labelled data is missing. `BLOCKERS.md` items A-25 and A-26 have been waiting for a human to
supply it.

The data was never missing. It is a public 378 MB download, and the symptom dates are in the
same paper's supplementary spreadsheet, shifted by the same amount as the public files so
they line up. It took about forty minutes.

**Why it matters.** This is the project's central claim and it had no evidence. Now it does,
and the evidence is good.

**How to do it.**

1. Put these numbers into `EVALUATION.md`:

   | Alert fired within | This system | Published NightSignal | Random, same rate |
   |---|---|---|---|
   | 3 days before onset, 1 after | 53.3% | 46.7% | 20.2% |
   | 7 days before, 3 after | 73.3% | 66.7% | 40.4% |
   | 21 days before, 7 after | 83.3% | 80.0% | 73.5% |

   Strictly before symptoms, 7 day window: **43.3%**, against 33.3% for the published
   algorithm. Alert burden on 76 healthy people over 738 person-weeks: **one investigation
   every 3.6 weeks**, against 4.5 weeks for the published algorithm.

2. **Always print the chance column next to the result.** 83 percent against a 73.5 percent
   chance floor is not a finding. 53 percent against 20 percent is.
3. Move `scratch/cohort_eval.py` into the repository, for example under `tools/`. A number
   nobody can reproduce is worth very little.
4. Close A-25 and A-26 in `BLOCKERS.md` and record how the labels were obtained.

**How you will know it worked.** Someone else can run the script and get the same numbers.

**What could go wrong.** The honest headline (53 percent) is lower than the 80 percent
currently quoted from someone else's paper. It is also yours, and it is real.

## 18. Write down how this differs from the published algorithm

`FIX` · Effort **S** to write, **M** if you adopt the step filter · Risk **low**

**The problem.** The thresholds and the 78 percent sensitivity come from NightSignal. Five
of the choices that define that algorithm were changed here, and nothing says so.

| | NightSignal, as its authors wrote it | This system |
|---|---|---|
| window | midnight to 06:59 | the sleep the watch recorded |
| which minutes | only minutes with zero steps | all minutes in the window |
| the night's number | the **mean** | the **median** |
| baseline | every previous night, including tonight | the last 28 nights, excluding tonight |
| red alert | two nights in a row at +4 or more | two raised nights with **at least one** at +4 |

**Why it matters.** The last row is looser, which is part of why this system finds more
infections and also raises more false alarms than the published one. The cohort measurement
in item 17 shows the trade is worth it. That makes it a decision, and a decision should be
written down.

**How to do it.**

1. Add the table above to `docs/DESIGN-BASELINE-CENTRE.md` or a new short design note, with
   the measured trade from item 17 beside it.
2. **Worth testing:** adding the zero-step filter is nearly free. It removes exactly the
   movement artefact that the "sensor problem" cause exists to model. In
   `src/wha/features/rhr.py`, drop minutes where the step count for that minute is not zero.
3. Run it through `scratch/cohort_eval.py` before adopting. It changes both sensitivity and
   the false alarm rate, so you need both numbers.

**How you will know it worked.** The cohort script prints the before and after.

## 19. Correct three things the documents say exist

`FIX` and `DROP the claim` · Effort **S** · Risk **none**

**The problem.** Three descriptions of things that are not there.

1. **`sources.yaml` describes four corpus layers.** StatPearls, the real clinical reference
   layer, has never been fetched. What the corpus calls layer 2 is three passages generated
   from `constants.py`. The Singapore care pathway layer is the nine passages already in
   `red_flags.yaml`, not the curated national guidance described.
2. **There is no reranking.** Searching the whole source tree for it finds nothing. Search
   works by keyword matching plus meaning matching, combined by a method called reciprocal
   rank fusion. Fusion is not reranking. If any write-up describes a reranking step, correct
   it. Adding one is item 28.
3. **The sleep window is justified more widely than measured.**
   `docs/DESIGN-SLEEP-WINDOW.md` presents it as a general improvement. Measured on 21 real
   people with real sleep data, night-to-night wobble got **better for 6, worse for 5, and
   stayed the same for 10**, because only 3 of the 21 sleep much outside midnight to 7am. It
   is strongly justified for someone who sleeps 03:00 to 11:00, which is you, and roughly
   neutral for a conventional sleeper.

**Why it matters.** A document describing something that does not exist is the thing that
made four subsystems in this project sit unnoticed for months.

**How to do it.** Edit `sources.yaml` to say what each layer actually is today, with a note
that the other two are planned. Edit `docs/DESIGN-SLEEP-WINDOW.md` to state who the
improvement is for. Both are one paragraph each.

**How you will know it worked.** Read `sources.yaml` and `wha corpus build` output side by
side. They should agree.

---

# Tier 3. Delete and simplify.

Deleting is the cheapest way to improve this project. A deletion with a written reason is a
stronger result than a feature.

## 20. Delete the Chronos forecast

`DROP` · Effort **S** · Risk **low, and it costs you a talking point**

**The problem.** 182 MB of model weights, a whole deep learning framework as a dependency, a
prediction every night, and one advisory paragraph on one screen that changes nothing. By
design it never sets a level, never opens an investigation, and is not used as evidence.

**Why it should go.** The project's own cited evidence argues against ever giving it more to
do. Alavi et al. 2022 compared three detectors on exactly this problem: plain baseline
comparison scored 78 percent sensitivity, a forecast-style detector scored 44 percent, at the
same false alarm rate. The simple method won.

**How to do it.**

1. Remove `chronos-forecasting` and `torch` from `pyproject.toml`.
2. Delete `src/wha/detect/forecast.py` and its call in `detect_night`.
3. Keep the `forecast_status` column and set it to `NOT_RUN`, so old rows still read.
4. Remove the forecast paragraph from `src/wha/ui/today.py` and the forecast row from
   `wha doctor`.
5. Write the reason in the report: not because it failed, but because the cited evidence says
   the simpler method is better and this one changes no decision.

**How you will know it worked.** `uv run wha doctor` no longer lists Chronos, `uv sync`
installs a far smaller set of packages, and the Today page no longer carries a paragraph that
changes nothing. Run one full episode to confirm nothing else depended on it.

**If you keep it, keep it for the report and say so.** Demonstrating a time series foundation
model is a fair reason for a coursework project. It is not a clinical one, and the write-up
should not imply otherwise.

## 21. Delete `get_local_disease_activity`

`DROP` · Effort **S** · Risk **none**

**The problem.** This tool calls a Singapore government web address with no search terms and
returns `{"status": "active", "bytes": 12345}`. That is the length of the response. It never
reads the dengue clusters, never checks whether you are inside one, and never asks the air
quality service that is also on the allow list.

**Why it should go.** `sources.yaml` says "A subject inside an active cluster materially
raises the dengue prior, and no shipped product does this." Nothing raises any prior, and
there is no dengue cause in the model to raise. Making it real means adding a cause and a
likelihood, which is a clinical decision and a large piece of work.

**How to do it.**

1. Remove the name from `CLOSED_TOOL_REGISTRY` and `TOOL_SIGNATURES` in
   `src/wha/agent/tools/registry.py`.
2. Delete `tool_get_local_disease_activity` from `src/wha/agent/tools/impl.py` and its
   registration.
3. Remove the two live endpoints from `sources.yaml` and the claim about dengue.
4. Put "local outbreak context" in the further work section of your report, which is where it
   honestly belongs.

**How you will know it worked.** The Audit page's list of permitted tools shows six, not
seven, and the AI cannot call it.

## 22. Delete the MEASURE limb

`DROP` · Effort **S** to delete, **M** to repair · Risk **low**

**The problem.** The system can decide to ask you to take your pulse by hand. That path is
broken in three separate places, any one of which is fatal.

1. Nothing anywhere writes a row to the `measurements` table.
2. The episode state that would make the request appear on screen is never set.
3. The code that resumes the paused episode always answers "declined", whatever you did.

So a notification goes out and the answer can never come back.

**Why it should go rather than be repaired.** It only triggers when a sensor problem is the
leading explanation at 0.5 or more, and that 0.5 is a guess with no source. It then asks you
to count your pulse for 30 seconds and double it, which has considerable error of its own.
The simpler honest behaviour is to tell you the night could not be judged.

**How to do it.**

1. Remove `ActionKind.MEASURE` from the router in `src/wha/agent/graph.py` and delete
   `node_measure`.
2. Remove the MEASURE branch in `src/wha/policy/select.py` and the
   `MEASURE_MIN_LEADING_PROBABILITY` constant.
3. Delete `compute_measurement_logfactor` and the measurement endpoints.
4. Keep the `measurements` table so old databases still open.
5. When sensor problems lead the differential, say so plainly in the outcome instead.

**How you will know it worked.** Run the simulation with a poor coverage night. The outcome
should say the night could not be judged, rather than sending a request nothing can answer.

## 23. Delete the duplicated belief maths

`SIMPLIFY` · Effort **S** · Risk **none**

**The problem.** The same function, `compute_residual_loglik`, exists twice, in
`src/wha/belief/likelihood.py` and `src/wha/belief/inference.py`. They are not identical: one
guards an index at both ends and the other only at the top.

**Why it matters.** This is the arithmetic the project says must be checkable by hand. Two
slightly different copies is the opposite of checkable. Coverage over a production run shows
the copy in `likelihood.py`, and the whole of `run_exact_inference`, never execute.

**How to do it.** Delete the unused copy in `likelihood.py` and delete `run_exact_inference`
from `inference.py`. Update the tests that call them to call the live path instead.

**How you will know it worked.** `uv run pytest` still passes, and searching for
`compute_residual_loglik` finds one definition.

## 24. Make the conversation limit do something, or remove it

`FIX or DROP` · Effort **S** · Risk **low**

**The problem.** A constant says a conversation may run to ten turns, cited to a Nature
study. The code works out whether you are at that limit, attaches the answer to the reply,
and then nothing reads it. No refusal, no warning, no stop.

**Why it matters.** A stop condition that does not stop anything is worse than none, because
it appears in the report as a control that exists.

**How to do it.** Pick one.

- **Enforce it.** In `src/wha/agent/conversation.py`, when `at_limit` is true, reply with a
  message that says the conversation has reached its length and suggests taking the summary
  to a doctor. Do not silently refuse.
- **Delete it.** Remove `CONVERSATION_MAX_TURNS`, the `at_turn_limit` field, and the AMIE
  citation from `constants.py`.

**How you will know it worked.** Have an eleven turn conversation and see what happens. Right
now, nothing does.

## 25. Have one escalation path, not two

`SIMPLIFY` · Effort **M** · Risk **low**

**The problem.** There are two separate implementations of "check what the person said, and
escalate if needed". `report_symptoms` in `src/wha/service/symptom_report.py` is one. The
conversation engine is the other. The dashboard and Telegram use the conversation engine. The
command line uses `report_symptoms`. So "I have chest pain" behaves differently depending on
where you type it.

**Why it matters.** Only `report_symptoms` opens and closes an episode, and it opens a new
one every time. The live database holds **five identical closed escalated episodes**, same
dates, never investigated, all shown separately on History, all from that path.

**How to do it.**

1. Give the conversation engine the ability to open an episode when the rules escalate, by
   calling `open_or_append_episode`.
2. Change `wha tell` in `src/wha/cli.py` to call `send_message` instead of
   `report_symptoms`.
3. Delete `report_symptoms`, or keep it as a thin wrapper for the demo harness only.
4. Make sure repeat reports about the same problem append to the open episode rather than
   opening a new one. `open_or_append_episode` already does this.

**How you will know it worked.** Type the same chest pain message twice on the dashboard.
History should show one investigation, not two.

## 26. Make `one_time` work, or remove it

`FIX` · Effort **S** · Risk **none**

**The problem.** Two probes in `probes.yaml` are marked `one_time: true`, and their low
interruption cost of 0.4 is justified by "asked once and then becomes a modelled covariate".
The loader in `src/wha/policy/probes.py` builds its object field by field and never reads
`one_time`, so the field is dropped without a word. Nothing makes them once.

**Why it matters.** Both probes are priced cheaply on the promise that you are only asked
once. If the promise is not kept, the price is wrong, and the system can spend part of your
interruption allowance asking you the same setup question in every new investigation.

**How to do it.** Pick one.

- **Honour it.** Add `one_time: bool = False` to `ProbeDefinition`, read it in
  `load_probes`, and in `select_action` skip any one-time probe already answered in **any**
  past episode, not just this one.
- **Remove it.** Delete the field from `probes.yaml` and raise the two interruption costs,
  since the justification for the low price no longer holds.

**How you will know it worked.** Answer the cycle question, close the episode, open a new
one. It should not be asked again.

## 27. Simplify the interruption budget

`SIMPLIFY` · Effort **S** · Risk **low**

**The problem.** There are two counters. One limits unsolicited questions to two per week.
The other limits questions inside one investigation to five. Keep the second. The first has
never done anything.

**Why it matters.** Measured on 76 healthy people over 738 person-weeks, the system opens an
investigation **once every 3.6 weeks**, and asks at most one question per investigation. Two
per week is never approached. In a live run with plenty of budget left, the agent asked one
question and then stopped on its own, because every remaining question was worth less than
the cost of asking. The EVSI arithmetic did the work, not the counter.

**The evidence also does not fit.** The counter is justified by a review finding that "72% to
99%" of alarms are false or not worth acting on. That review is about **intensive care unit
bedside monitors**. A phone notification is not that, and the file does not acknowledge the
jump.

**How to do it.**

1. Keep the alarm fatigue reasoning. It is right and well sourced.
2. In your report, present the **quiet band** as the thing that prevents over-interruption,
   because it is, and it is a much better story than a counter.
3. Either remove `check_interruption_budget_gate` from `src/wha/policy/gates.py`, or keep it
   as a safety net and say plainly that it has never bound.

**How you will know it worked.** Run the illness simulation. The agent should still ask
exactly one question and then stop, for the same reason it does today: every remaining
question is worth less than the cost of asking. If removing the counter changes how many
questions get asked, the counter was binding after all and you should put it back.

**What could go wrong.** If item 5 raises the infection effect, the alert rate rises and the
counter may start to matter. Re-measure with `scratch/cohort_eval.py` after item 5 before
removing anything.

---

# Tier 4. Worth doing if there is time.

## 28. Add a reranker

`FIX` · Effort **M** · Risk **low**

**The problem.** Search brings back the wrong passages. For an episode about fever, four of
the five passages shown as evidence were about stiff neck, and the top one was the list of
answer options for the symptom question. In a chest pain conversation the one source cited
under an urgent escalation was "How to Prevent Heart Disease".

**Why it matters.** The grounding check proves a sentence came from a passage. It proves
nothing about whether that passage is relevant. The Evidence tab calls them "Knowledge
Citations and Evidence".

**How to do it.** A **reranker** is a second, slower model that reads your question and each
candidate passage together and re-scores them. It is the standard fix for exactly this.

1. Fetch the top 20 candidates from `HybridIndex.query` instead of the top 8.
2. Score each with a small cross-encoder, for example `BAAI/bge-reranker-base`, which runs on
   a CPU.
3. Keep the best `RETRIEVE_TOP_K`.
4. Cache the scores, the same way the embeddings are already cached.

**How you will know it worked.** Search the corpus for "fever" with `wha corpus search`. The
top results should be about fever.

## 29. Stop the corpus leaking the internal keyword lists

`FIX` · Effort **S** · Risk **none**

**The problem.** Two of the four corpus layers are generated straight out of YAML, so the
passages you are shown include raw phrase lists: "Any of: 'stiff neck', 'neck stiffness',
'can't touch chin to chest'", and the whole tier B table with its trigger words.

**Why it matters.** That is an internal keyword list presented to you as clinical evidence.
It also publishes exactly which words cause an escalation.

**How to do it.** In `src/wha/retrieve/knowledge_docs.py`, the layer 3 generator writes the
match lists into the passage text. Write prose instead: what the sign is, why it matters, and
what to do. Keep the rule id in the metadata so the audit trail still links back.

**How you will know it worked.** Open the Evidence tab on an escalated episode. It should
read like health information, not like a configuration file.

## 30. Give urgency an expiry

`FIX` · Effort **M** · Risk **medium**

**The problem.** Urgency is the highest level any rule has ever reached in your whole
conversation history, with no time limit. A "see a doctor today" banner from days ago is
still at the top of the Today page, with no date and no way to clear it.

**Why it matters.** A red banner that never goes away is a banner you learn to ignore. That
is the alarm fatigue this project cites in its own constants.

**How to do it.**

1. In `established_urgency` in `src/wha/agent/conversation.py`, only consider turns from the
   last N days.
2. Show the date the urgency was set, next to the banner.
3. Add a button saying you have seen someone about it, which clears the banner and records
   that you did.

**How you will know it worked.** Have a chest pain conversation that reaches "see a doctor
today". Come back to the Today page the next day. The banner should carry the date it was
set, and there should be a way to close it that leaves a record.

**What could go wrong.** Urgency must never fall because something reasoned it down. An
expiry is not reasoning, but it must be visible. Never drop it silently.

## 31. Fix the differential chart

`FIX` · Effort **M** · Risk **low**

**The problem.** The chart is labelled "Cause Differential" and drawn as a ranked bar chart,
so it reads like a doctor's list of most likely diagnoses. It is not. The twelve numbers are
independent, do not add up to 1, and do not compete. A cause that is common and small scores
high on any raised night, because something has to explain the rise.

**Why it matters.** On a real closed episode the system concluded **LIKELY_ILLNESS** and the
chart immediately underneath put **stress at 0.92** in first place, with the reason "Nothing
gathered in this episode speaks to this cause either way." The audit page repeats it in
words: "most likely stress at 93%, chance of illness 78%". You read "we think you are ill"
directly above "most likely cause: stress, on no evidence".

**How to do it.** The cheapest fix is also the best one.

1. In `src/wha/agent/differential.py`, record each cause's probability **before** this
   episode's evidence and **after**.
2. Rank the chart by how much this episode moved each cause, not by its final size.
3. Change the heading to something like "What this episode's evidence changed", and add one
   line saying these are independent probabilities that do not add to 100 percent.

**How you will know it worked.** On an episode where you answered "feverish", infection
should be at the top, because that is the cause the evidence moved.

## 32. Stop padding the audit log, and record the timings

`FIX` · Effort **S** · Risk **none**

**The problem.** Three small things in the record.

1. **Padding.** The Audit page says "a check that found nothing new does not appear". But
   the ingest recorder only stays quiet when zero rows were written, and re-pulling the same
   window rewrites the same rows. The live log holds five entries minutes apart, all reading
   "9785 heart rate samples arrived".
2. **No notifications.** `notify` is a permitted operation and nothing writes one, so the
   record does not show that a question reached your phone.
3. **No timings.** `src/wha/agent/tools/registry.py` measures how long each tool call took
   into `_latency_ms` and throws it away, so the audit's duration column is always empty.

**Why it matters.** The Audit page is the one screen whose entire purpose is to be
trustworthy, and it currently makes a claim about itself that is not true. Padding also
buries the entries that matter, because the agent's tool calls end up scattered between
dozens of identical "data arrived" lines.

**How to do it.**

1. In `record_ingest` in `src/wha/audit/monitor.py`, compare against the newest sample
   timestamp already stored, and stay quiet when nothing newer arrived.
2. Write a `notify` audit row where `record_notification` is called in `node_ask`.
3. In the tool registry, put `_latency_ms` into the `AuditEvent` instead of discarding it.

**How you will know it worked.** Run ingest three times. The Audit page should show one
entry, not three.

---

# What needs no work

These came out of the review as **KEEP**. Leave them alone. This list is as useful as the
one above, because it is the part of your project that is already right and evidenced.

**The maths.** The sleep window as a design, the three hour coverage floor, the personal
baseline centre after seven nights, the 3.0 and 4.0 bpm thresholds, the exercise subtraction
table, and the robust z-score.

**The knowledge tables.** The menstrual cycle, vaccination, illness recovery and short sleep
figures all matched their papers exactly, as did all 28 exercise numbers.

**The safety design.** The three-tier floor where fixed rules and the AI are combined so the
AI can only ever add a flag. And the Marburg Heart Score arrangement, where the AI asks the
questions and the published rule decides. That is the best single idea in the system.

**The belief model.** Working out all 4,096 combinations exactly, in log space, and the
time-shape of each cause that does the real work of telling them apart.

**The policy.** The EVSI calculation, the decision threshold worked out from the cost of
each kind of error rather than picked, the swept interruption cost, and the per-episode,
tool-call and step limits, which do bind.

**The agent.** The tool loop, the edge that sends the agent back to investigate after you
answer, pausing and resuming across a restart, the closed list of seven tools, and the
critique pass that may only remove.

**Retrieval and grounding.** Keyword plus meaning search combined by rank fusion, scanning
retrieved text for hidden instructions and marking rather than deleting it, and above all
the word-for-word claim check, which is the best safety idea in the system and was verified
working on a live message.

**The interfaces.** The HTTP boundary that makes the dashboard replaceable, the two-call
conversation design, and the tamper-evident audit log with its plain English nightly
explanations.

**The evaluation.** The policy comparison against never-ask and always-ask, and the eleven
frozen scenarios run against the real model.

---

# If you only have one day

1. **Item 1.** Check the "when to seek care" text. One hour, and it is the biggest safety
   hole in the system.
2. **Item 11.** Four sentences on Today. One hour, and it is the screen you read most.
3. **Item 10.** Name the source on Telegram. Half an hour, and it closes an open blocker and
   a licence obligation.
4. **Item 17.** Publish the detection numbers. Two hours, and it turns the project's weakest
   claim into its strongest.
5. **Items 20 and 21.** Delete Chronos and the disease activity tool. One hour, and the
   project gets smaller and more honest at the same time.

That is one day. It removes the worst safety gap, makes the main screen truthful, and gives
the project the evidence it has been missing since it started.

---

# What I would not do

- **Do not add the two missing corpus layers yet.** Correct the description first (item 19).
  The corpus is already fourteen times the size it was, and the measured problem is
  relevance, not volume.
- **Do not add more causes.** Twelve is already more than the evidence supports for several
  of them, and the chart problem in item 31 gets worse with each one.
- **Do not build multi-user support.** One person, one phone. The API has no login on
  purpose and the reasoning is written down.
- **Do not weaken a scenario to accommodate item 5.** If a bigger infection effect breaks a
  frozen scenario, measure what the system now does, decide whether it is right, then change
  the expectation and say why. Measure, then assert. Never the other way round.
- **Do not go looking for the missing evidence again.** I looked. The numbers for how
  honestly people report drinking or stress to an app do not exist, and `probes.yaml` is
  right that better data will not fix that, because nobody has made the measurement. Label
  them (item 15) and move on.
