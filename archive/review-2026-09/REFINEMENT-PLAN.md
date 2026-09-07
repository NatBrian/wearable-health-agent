# Refinement plan

What to do, in the order that buys the most, with the reason and the steps for each one.

**Second revision, 4 September 2026.** The first revision assumed `data/knowledge/` was
written by a person, because every file in it says so. It was written by a language model.
That changes the reasoning behind several items, and one item reverses completely: see
item 6, where a measurement showed my own first review was wrong.

The papers are in `docs/EVIDENCE-LOG.md`. **You can read this file on its own.** Every part
of the system that needs work has an item here, and the coverage table proves it.

---

## What changed in this revision, and why

Four things were measured after the first draft, on 120 real people and 8,508 real nights.
Three of them changed a recommendation.

| Question | What I assumed | What the measurement says |
|---|---|---|
| Is the infection effect of 1.60 bpm far too small? | Yes, badly. | **No. It is about right.** Measured at 1.0 to 1.5 bpm above matched healthy controls. **I was wrong.** See item 6. |
| Would adding the published algorithm's step filter help? | Probably, it removes movement. | **No difference at all.** 2.97 bpm wobble either way. See item 20 for why. |
| Would a personal threshold beat a fixed one? | Likely, people differ. | **No.** Fixed beats personal at every matched alert rate. See item 8. |
| Does the Chronos forecast add detection signal? | Argued no, from a paper. | **Measured no.** It separates illness worse than the plain residual. See item 22. |

The first of those is the important one. My first review said the most important number in
the project was badly wrong. It is not. The citation attached to it is wrong, and the
number itself survives measurement.

---

## How to read an item

| Word | What it means |
|---|---|
| **FIX** | The idea is right. The number or the wiring is wrong. Repair it. |
| **SIMPLIFY** | It works, and it is more complicated than the job needs. Cut it down. |
| **DROP** | It does not earn its place. Delete it, and write down why. |
| **UNEVIDENCED** | It is a guess. Nothing is broken. Label it as a guess on screen. |
| **KEEP** | It is right and it is evidenced. Leave it alone. Listed at the end. |

Every item answers: **the problem**, **why it matters**, **how to do it**, and **how you
will know it worked**. Where an item used to offer two routes, I have chosen one and left
the other as a footnote, so this is a list of jobs and not a list of decisions.

**Effort** is focused work: **S** under an hour, **M** a few hours, **L** a day, **XL** more
than a day.

---

## Coverage: every part of the system, and where it lands

| Part of the system | Verdict | Item |
|---|---|---|
| `data/knowledge/` says a human wrote it, and a model did | **FIX, top priority** | **1** |
| Escalation criteria are checked by nothing | FIX, by deletion | **2** |
| Human review checkpoint approves itself | FIX | **3** |
| Blood oxygen rule has never run | FIX | **4** |
| The two extreme heart rate rules have never run | FIX | **4** |
| Marburg age gate never gets an age | FIX | **5** |
| infection effect of 1.60 bpm | **KEEP the number, FIX the citation** | **6** |
| exertion effect of 4.14 bpm in `causes.yaml` | FIX | **7** |
| Baseline band width still borrowed from strangers | FIX | **7** |
| Alert rule looser than the published one | FIX | **8** |
| Cycle answer never reaches the belief model | FIX | **9** |
| `get_data_quality` invents its numbers | FIX | **10** |
| Execution trace says every stage was skipped | FIX | **11** |
| Telegram does not name the source | FIX | **12** |
| Today page says three things that are not true | FIX | **13** |
| "Probably nothing to worry about" headline | FIX | **13** |
| Question record always says "fallback" | FIX | **14** |
| Baseline nights and rung hard-coded in the outcome | FIX | **14** |
| An escalated episode recommends "monitor" | FIX | **14** |
| "Stripped claims" panel is always empty | FIX | **14** |
| Offers a temperature reading the watch cannot take | FIX | **15** |
| Alcohol amount collected and thrown away | FIX | **16** |
| 64 answer likelihoods, machine generated | UNEVIDENCED | **17** |
| 45 temporal profile weights, no source | UNEVIDENCED | **17** |
| Travel, short sleep and unexplained effect sizes | UNEVIDENCED | **17** |
| The amber "not from a cited source" label | UNEVIDENCED | **17** |
| Population figure described as "525 adults" | FIX | **18** |
| Blood oxygen thresholds credited to WHO | FIX | **18** |
| Downie 2013 used outside its population | FIX | **18** |
| Detection accuracy says "not evaluated" | FIX | **19** |
| Median instead of mean, and no step filter | **KEEP, now justified** | **20** |
| Two corpus layers described but never built | FIX | **21** |
| Reranking described but absent | DROP the claim | **21** |
| Sleep window justified more widely than measured | FIX | **21** |
| Chronos forecast | **DROP** | **22** |
| `get_local_disease_activity` | **DROP** | **23** |
| The MEASURE limb | **DROP** | **24** |
| Two copies of the same belief maths | SIMPLIFY | **25** |
| `CONVERSATION_MAX_TURNS` does nothing | FIX | **26** |
| Two different escalation paths | SIMPLIFY | **27** |
| `one_time` on a probe does nothing | FIX | **28** |
| Weekly interruption budget that never binds | SIMPLIFY | **29** |
| Retrieval brings back the wrong passages | FIX | **30** |
| Corpus leaks the internal keyword lists | FIX | **31** |
| Urgency never expires | FIX | **32** |
| The differential chart misleads | FIX | **33** |
| Audit log padded, and no timings | FIX | **34** |

---

## Two rules to hold while doing any of this

1. **Do not make a test pass by changing the test.** Every problem here was invisible to 546
   passing tests. A test that proves a fix must exercise the whole path, not one function.
2. **Finish by using the product.** Open the page. Send the message. Every problem here was
   found by running the system, not by reading it.

---

# Tier 0. Safety and truthfulness. Do these first.

## 1. The knowledge files say a human wrote them, and a language model did

`FIX` · Effort **L** · Risk **low to do, high to leave**

**The problem.** Every file in `data/knowledge/` carries a line like:

> `# READ ONLY. Authored by a human. The coding agent loads this and never edits it.`

They were generated by a language model. `data/knowledge/README.md` states the reason those
files exist:

> "A language model asked to produce hundreds of cited conditional probabilities will
> produce hundreds of plausible fabrications... That is why these files are authored and
> frozen rather than generated."

That is exactly what happened, and the file describing the danger is itself one of the
generated files.

**Why it matters.** The whole safety story of this project is one sentence: *clinical content
comes from a human-curated, cited table, never from a model.* If a model produced the table,
that sentence is not true, and every downstream claim built on it inherits the problem. It
also means the reassuring commentary inside those files ("set deliberately conservatively",
"this is the honest encoding") is a model explaining why its own invented numbers should be
trusted.

**How much is affected.** Counted, not estimated:

| What | How many | Source given |
|---|---|---|
| Temporal profile weights, across 10 of the 12 causes | **45** | none. Only infection and alcohol carry a `profile_source` |
| Between-person spread (`effect_sd_bpm`) | **12** | reasoning for 2 of them, none for the other 10 |
| Answer likelihoods in `probes.yaml` | **64** | declared ASSUMED; no measurement exists |
| Interruption costs | **9** | none |
| Tier B persistence thresholds | **6** | none, though they match mainstream advice |
| Extreme heart rate thresholds | **4** | none |

That is roughly **140 numbers**. Several are load-bearing: `causes.yaml` says in its own
header "THE PROFILE IS WHAT DISCRIMINATES", and 45 of the 57 profile weights have no source.

**What is not affected.** The figures that carry a real citation still check out. I opened
the papers: the menstrual cycle, alcohol, vaccination, illness recovery, short sleep base
rate, the detection thresholds, the seven-night baseline rule, the population figures, all 28
exercise contrasts, and every Marburg item and performance number. Those are fine. The
problem is the numbers that were never cited, not the ones that were.

**The claim is not only in `data/knowledge/`.** I searched the whole repository. Fourteen more
places say a human wrote this material, and two of them are the ones that matter:

| Where | What it says | Why it matters |
|---|---|---|
| **`src/wha/ui/audit.py:108`** | "plain pattern matching against **a human-written list**" | **This is rendered on screen**, on the Audit page, whose entire purpose is to be trustworthy |
| **`README.md:320`** | "**Written by a human, in this repository:**" heading the knowledge section | The first thing anyone opening the repository reads about the clinical content |
| `AGENTS.md:105` | "Cited medical tables, authored by a human" | The rule that forbids editing them rests on this |
| `.agents/rules/20-prohibitions.md:49` | "Authored by a human, with sources" | Same |
| `src/wha/retrieve/knowledge_docs.py:1, :14` | "rendered out of the knowledge a human authored"; "it was written by a human" | In the code that builds the corpus the agent cites |
| `src/wha/retrieve/corpus.py:17` | "The human-written prose in causes.yaml" | Same |
| `src/wha/service/corpus.py:14` | "rendered from knowledge a human authored" | Same |
| `docs/CORPUS-VERIFICATION.md:5, :136` | "three files a human authored"; "the human-authored safety floor" | The document written to prove the citations were checked |
| `docs/RESEARCH-AGENTIC-TRIAGE.md:312` | "human-authored routing decisions" | The research note behind the triage redesign |
| `BLOCKERS.md:717` | "a human-authored safety list, so I have not added it" | A decision was deferred **because** of this belief |
| `history/HANDOFF.md:85` and four `history/plan/` files | the same claim | Frozen finished work, lowest priority, but still in the repository |

**How to do it.**

**Delete the claim. Do not replace it with "written by an AI".** That would be a different
blanket claim and no more accurate: some numbers in these files are correctly cited to real
papers and some have no source at all, and one header line cannot say both. The truthful
statement already exists at the level where it belongs, which is the `provenance` field on
each individual number. Remove the file-level claim and let that field carry the weight.

**Step 1, the exact edits. About twenty minutes.** Precise, because most of these are two
words inside a sentence that is otherwise true and should survive.

| File and line | Change | The sentence still works because |
|---|---|---|
| **`src/wha/ui/audit.py:108`** | "against a human-written list" becomes "against a fixed list" | The point of the sentence is that the list is not the model's, and "fixed" says that |
| **`README.md:320`** | "Written by a human, in this repository:" becomes "In this repository:" | It is a section heading for a file list |
| `AGENTS.md:105` | "Cited medical tables, authored by a human" becomes "The clinical tables. Every number carries its own provenance" | |
| `.agents/rules/20-prohibitions.md:49` | "the cited medical tables. Authored by a human, with sources" becomes "the clinical tables" | |
| `src/wha/retrieve/knowledge_docs.py:1` | "rendered out of the knowledge a human authored" becomes "rendered out of the knowledge tables in this repository" | |
| `src/wha/retrieve/knowledge_docs.py:14` | delete ", and it was written by a human" | The clause before it, that this is the only care-pathway guidance here, is true |
| `src/wha/retrieve/corpus.py:17` | "The human-written prose in causes.yaml" becomes "The prose in causes.yaml" | |
| `src/wha/service/corpus.py:14` | "rendered from knowledge a human authored" becomes "rendered from the knowledge tables" | |
| `docs/CORPUS-VERIFICATION.md:5` | "three files a human authored" becomes "three files in this repository" | |
| `docs/CORPUS-VERIFICATION.md:136` | delete "human-authored" | "the safety floor" is enough |
| `docs/RESEARCH-AGENTIC-TRIAGE.md:312` | delete "human-authored" | |
| `data/knowledge/*.yaml` headers | delete "Authored by a human." Keep "READ ONLY." | The read-only rule still applies, for the reason in step 4 |
| `data/knowledge/triage_rules.yaml:30` | delete ", Reviewed by a human before use" | |
| `data/knowledge/README.md:3` | delete "Authored by a human." | |
| `data/knowledge/README.md:11` | delete only the last sentence, "That is why these files are authored and frozen rather than generated." | **Keep the paragraph before it.** The warning that a model asked for hundreds of cited probabilities will produce hundreds of plausible fabrications is true, and is now the most relevant sentence in the repository. It simply no longer supports the conclusion that was drawn from it |

**Two that are not text edits.**

- **`data/knowledge/triage_rules.yaml:4` is true. Leave it.** "TRANSCRIBED FROM PUBLISHED
  RULES. Not authored, not invented, not tuned. Every item, weight and threshold below is
  copied from the cited paper." I checked every Marburg item and every performance figure
  against Bösner et al. 2010. It holds.
- **`BLOCKERS.md:717` deferred a decision on this basis**, so removing the words is not
  enough. It says adding "that's reassuring" to the never-say list is "a wording judgement
  about a human-authored safety list, so I have not added it". **Decision: do not add it.**
  The phrase is not an absolute reassurance like the others on that list, and in the real
  transcript it was attached to a genuine clinical observation. Banning it only makes the
  model write "that's a good sign" instead. The failure was that the sentence went unlabelled,
  which is item 17, not the vocabulary. Close the blocker with that reasoning.
- **`data/knowledge/sources.yaml:84`, "HAND-CURATED, NOT SCRAPED"**, describes a corpus layer
  that was never built. That belongs with item 21, not here.

**`history/` is a record of what was believed at the time. Leave it.** Six files there carry
the claim, and `history/README.md` already states that nothing in it describes the present.
Editing a frozen record to remove something that was genuinely believed when it was written
is its own kind of rewriting.

**Step 2. Strip the self-vouching prose from numbers that have no source.** Deleting the
header is not enough on its own, because the commentary beside individual numbers does the
same job in miniature: "set deliberately conservatively", "this is the honest encoding", "set
deliberately SMALL, which UNDERSTATES how much short sleep explains". Those read as a
person's reasoning and are a model's. Delete the vouching, keep the fact. `ASSUMED` already
means "no published value exists", which is the useful thing to say and needs no new label.

**Step 3. Triage by consequence, not by count.** Three groups:
   - **Measured.** The infection effect, spread and shape are now measured on real labelled
     data (item 6). Do the same for anything else you can measure.
   - **Findable.** Some have a real source that simply was not cited. The infection base rate
     is one: `causes.yaml` uses 0.025, and the standard figure is 2 to 4 colds a year lasting
     7 to 11 days, which is nearer 7 percent of days. Either cite a source or record the gap.
   - **Unmeasurable.** The 64 answer likelihoods are genuinely unmeasurable, and `probes.yaml`
     is right about why. They keep `ASSUMED`, which already means no published value
     exists, and it is shown on screen (item 17).
**Step 4. Change the rule in `AGENTS.md` and `CLAUDE.md`.** They forbid editing these files
because a human authored them. That justification is void, but the rule is still right for a
different reason: a clinical number should not change without a source and a record. Keep the
files under change control, and keep recording every change in
`docs/KNOWLEDGE-CHANGELOG.md` with the quoted source sentence, which is what that file is for.

**How you will know it worked.** Two checks.

First, `grep -rniE "authored by a human|written by a human|human-authored|human-written" .`
over everything except `history/`, `research/` and `.venv/` returns nothing.

Second, pick three numbers at random from `causes.yaml` or `probes.yaml` and try to find
where each came from. You should reach either a paper or an `ASSUMED` label. You should never
reach a sentence that tells you the number is trustworthy without saying why.

**What could go wrong.** Nothing technical. The risk is to the report: this weakens the
"never write clinical content from your own knowledge" claim. Say it plainly and it becomes a
strength, because finding it is exactly the kind of audit the discussion section should
describe.

## 2. Stop generating the "when to seek care" text

`FIX, by deletion` · Effort **S** · Risk **low**

**Why FIX and not DROP.** The text stays. Every outcome still tells you when to seek care,
and you lose nothing on screen. What is deleted is the model's freedom to write it, which is
how the fix is done rather than what it costs you. A DROP would mean the guidance itself does
not earn its place, and it does.

**The problem.** The outcome has a field that tells you when to seek care. The AI writes it
freely, and it is the only text in the system that goes through no check at all. In a real
run it produced:

> "Seek care if fever persists beyond 72 hours or exceeds 103°F (39.4°C)"

Those thresholds came out of the model.

**Why it matters.** This is the sentence most likely to make you act on something, and it is
the least checked thing on the page. A study that red-teamed four chatbots over 222 patient
questions found 5 to 13 percent of answers were outright unsafe.

**How to do it. Decided: do not build a guard. Remove the thing that needs guarding.**

An earlier draft of this item said to point the existing number filter at this field. That
was wrong, for three reasons, and the third is the one that matters.

**One, the filter is too permissive.** `collect_allowed_numbers` blanket-permits 0 through
10, plus 14, 21, 28, 30 and 995. So a model writing "over 5 nights" about a two night episode
sails through, and that exact sentence appeared in a real outcome. It only catches numbers
that happen to be large or unusual.

**Two, it is too blunt.** It deletes the **whole sentence** on any unrecognised number. So
"seek help if your temperature goes above 38 degrees" is deleted in full, because 38 is not
on the list, and the person is left with less guidance than before. You cannot tell 103 from
39.4 inside "103°F (39.4°C)" with a number heuristic, and you should not try: both are
fabricated here, but in another sentence one of them would be the right answer.

**Three, extending it adds a crash path.** `validate_and_sanitize_outcome` raises
`ValidationFailed` when `escalation_criteria` is empty and the disposition is not
LIKELY_BENIGN. In `node_critique` that call sits **outside** the `try` block. So a run where
the filter strips every criterion does not fall back gracefully. It raises, the node fails,
and the episode dies. A safety guard that breaks the episode is worse than no guard.

**The better answer is that these should never have been generated.** The system already
holds a complete set of reviewed care-pathway sentences, and it uses them everywhere else:

- `red_flags.yaml` tier A `guidance`, one per urgent sign, for example "Chest pain or
  pressure needs assessment now. Call 995 or go to an A&E."
- `red_flags.yaml` `tier_b_guidance`, the same-day wording.
- `triage_rules.yaml` band `meaning`, the published interpretation of a Marburg score.
- `DEFAULT_ESCALATION_CRITERIA`, the two general lines.

So:

1. **Remove `escalation_criteria` from the model's output schema** in
   `src/wha/agent/nodes.py`. `WriteOutcomeResponse` should return prose and claims only.
2. **Select the criteria deterministically** from the disposition, the triggered flags and
   the top of the differential. Infection leading with a reported fever selects the tier B
   fever wording; an escalation selects the matching tier A wording; everything else gets the
   two defaults. This is the same "model elicits, rules decide" split the Marburg triage
   already uses and that works well.
3. **Move `DEFAULT_ESCALATION_CRITERIA` and the two hard-coded lines in `node_conclude` into
   `red_flags.yaml`**, so all care wording lives in one place and the corpus can cite it.

This is less code than the guard, has no regex, cannot invent a threshold, cannot delete
guidance, and cannot crash the episode. It also makes the wording consistent between runs,
which for safety text is a feature and not a limitation.

**What you give up.** Tailoring. The invented sentence was specific to the fever the person
reported, and a selected one is more general. But specificity is exactly where the invention
happened, and selection still tailors by *choosing* the relevant rule rather than writing a
new one.

**Separately, fix the number filter where it does still run**, on `observation`. Replace the
blanket 0-to-10 allowance with the episode's real numbers, which the system already has:
the night count, the residual, the thresholds, the baseline centre and its night count. That
makes it both safer and less blunt, because the true numbers become allowed and the invented
small integers stop being waved through.

**Worth recording.** The model's invented "fever beyond 72 hours" happens to match mainstream
advice: NHS and Mayo both say seek advice after about three days. Matching by luck is not
sourcing, and it is the reason this kind of error is hard to spot by reading.

**How you will know it worked.** Run three live episodes with different dispositions. Every
line in the "when to seek care" text appears verbatim in `red_flags.yaml` or
`triage_rules.yaml`. `grep` the outcome text against those files and expect an exact match.

## 3. Let a human do the human review

`FIX` · Effort **S** · Risk **medium, episodes stop closing on their own**

**The problem.** The system drafts a conclusion and pauses for you to approve it. A
background job answers "approve" on your behalf fifteen minutes later, and the record says a
human approved it.

**Why it matters.** This is the one place a person can say "no, that is wrong" before the
system commits to a conclusion about their health. It has never been possible. A record
showing a human decision that never happened is worse than no checkpoint.

**The evidence.** A live run: episode `ep_3637eaf58033` went from waiting-for-you to closed
in one tick, with nobody involved.

**How to do it.**

1. `src/wha/service/scheduler.py`, `_resume_value`: it handles a question and a measurement,
   then falls through to `return {"decision": "approve"}`. Return `None` instead, which means
   "leave it parked".
2. `src/wha/agent/nodes.py`, `node_review`: before the `interrupt()`, call
   `db.set_episode_state(episode_id, "AWAITING_HUMAN_REVIEW")`. Without it the review cannot
   appear on screen. `node_ask` already does this one state along.
3. Add a timeout. If nobody reviews inside `ANSWER_TIMEOUT_HOURS`, close the episode and
   **record that it closed unreviewed**. Do not record an approval.

**How you will know it worked.** Take an episode to the end. The dashboard shows a draft with
approve, edit, reject and escalate. Click reject. The episode closes UNRESOLVED.

## 4. Connect the three safety rules that have never run

`FIX` · Effort **M** · Risk **medium, this can newly wake you at night**

**The problem.** Three rules are written, tested on their own, and connected to nothing.

- The blood oxygen rule (`check_overnight_oxygen` in `src/wha/safety/rules.py`) is called by
  no code and no test.
- The two extreme heart rate rules need `robust_z`. All three places that run the safety
  check pass only the text you typed, so the number is always missing and the branch is
  skipped.

**Why it matters.** A night far outside your own range currently raises nothing unless you
independently type a warning phrase. A safety floor that only fires on what you say is not a
floor on your data.

**The evidence.** Line coverage over a full production run: `src/wha/safety/rules.py` lines
162 to 178 and 253 to 266 never execute.

**How to do it.**

1. Do item 7 first. `robust_z` is currently divided by a band width one fifth borrowed from
   other people, so the threshold does not mean what it says.
2. `src/wha/service/nightly.py`, `run_nightly`, after `detect_range` returns: for each
   detection call `check_red_flags_deterministic` with `robust_z`, `rhr_bpm` and the baseline
   rung, all of which are already there.
3. Same place: call `check_overnight_oxygen` with the connection, subject and sleep window.
4. Route any escalation through `_notify_escalation` in
   `src/wha/service/symptom_report.py` rather than writing a second notification path.

**How you will know it worked.** Before shipping, run the rules over the cohort with
`scratch/cohort_eval.py` and count how often `robust_z` exceeds 6 across 8,508 real nights.
If that number is large, the threshold is wrong, not the wiring.

**What could go wrong.** This is the only item that can newly wake you at 3am. Measure first.

## 5. Give the chest pain rule the age it already knows

`FIX` · Effort **S** · Risk **low, it means more escalations not fewer**

**The problem.** The Marburg Heart Score was tested only on people aged 35 and over. The code
checks for that. The age is never filled in, so the check never fires and the rule runs on
everybody.

**Why it matters.** In a real run the person typed "I am 24 and male". The system pulled that
out and stored it, then applied a rule never tested on 24 year olds, scored 3 of 5 on three
things common in a young adult with a pulled muscle, said urgent, and cited "a 2010 study of
1,199 people with chest pain".

**The evidence.** Bösner et al. 2010 built the rule on "1,199 unselected and consecutive
patients aged >= 35 years".

**How to do it. Decided: a small profile in Settings, not a mid-conversation guess.**

Parsing the age out of what someone typed during a chest pain conversation is fragile and it
is the wrong moment to ask. Collect it once, in advance.

**What to collect, and nothing more.** The rule for deciding is: **does something in this
system actually consume it?** Five fields pass that test.

| Field | What consumes it | Why in Settings and not a question |
|---|---|---|
| **Age** | The Marburg age gate, `minimum_age_years: 35` | Asking during a chest pain episode wastes a turn at the worst moment |
| **Sex** | Marburg item 1, woman 65 or over or man 55 or over | Same |
| **Known coronary, cerebrovascular or peripheral vascular disease** | Marburg item 2 | This is the item most likely to be misremembered under stress, and it never changes |
| **Do you menstruate** | The luteal cause in `causes.yaml` | **This retires `probe_cycle` entirely.** It is already marked `one_time` and priced at 0.4 of an interruption. Moving it here removes an interruption from the budget and fixes item 9's plumbing at the same time |
| **Do you take a medicine that lowers your heart rate** | Nothing, deliberately. It becomes a **disclosure** | `causes.yaml` records that beta blockers blunt the heart rate response to infection, which is a false negative risk. The system should say "I am less able to see an infection in you" rather than silently being worse at its job |

Then: pass `age_years` into the existing parameter of `triage()`. The chain is already wired
end to end and simply never filled. Pre-fill the two Marburg items from the profile so the
conversation only has to ask the three that genuinely vary.

**What not to collect, and this matters more than the list above.**

- **Weight, height, BMI.** Nothing in this system reads them. There is no covariate model,
  and the baseline becomes personal after seven nights so it does not need them. A field
  nobody reads is worse than no field, because it tells the person their data is being used
  when it is not.
- **A free-text health history box.** This is the one to push back on hardest. Free text
  would go straight into the conversation prompt, where the model would reason from it with
  no grounding, no citation and no way to check it. That is precisely the "model reasons from
  unverified clinical text" path this whole project exists to prevent, and it would be opened
  by the person themselves, which makes it feel safe when it is not.

**The distinction worth holding: information for the doctor is not information for the
model.** If you want to record "I had pericarditis in 2019", it belongs in the SBAR handover
that `src/wha/service/handover.py` already builds, where a clinician reads it. It should
never enter a prompt. Add a free-text field if you like, label it "for your doctor", and
keep it out of the reasoning path entirely.

**How you will know it worked.** Say you have chest pain and set your age to 24. The reply
says the rule was not applied because it was only tested on people 35 and over, and routes
you conservatively rather than scoring you. Then check that answering the cycle question is
no longer possible, because Settings already knows.

---

# Tier 1. Things the documents say work, and do not.

## 6. The infection entry: keep the number, fix the citation

`KEEP the number` · `FIX the citation` · Effort **S** · Risk **low**

**This item reverses my first review. The correction matters more than anything else here.**

**The problem.** The infection row in `causes.yaml` carries a citation that points at the
wrong paper, a derivation that multiplies numbers from two different groups of people, and
one effect size doing the work of two very different situations. The number itself is fine.

**Why it matters.** This is the row the whole system turns on. If its provenance cannot be
checked, nothing built on it can be either, and this is the row a marker or a clinician would
look at first.

**What I said first.** That 1.60 bpm was far too small, incoherent with the 3 and 4 bpm
thresholds, and the reason the system cannot conclude illness. I recommended replacing it and
called it the highest priority in the document.

**What the measurement says.** I measured the infection effect directly, on the 30 labelled
COVID cases, using this system's own baseline code so the answer is in the same units the
detector works in. Against matched healthy controls, so the upward bias of taking a highest
night is removed:

| | Highest night above own baseline, 7 night window |
|---|---|
| Healthy people, random 7 night windows (46) | median **5.00 bpm** |
| The 7 nights before symptoms (23 cases) | median **6.00 bpm** |
| **The infection contribution** | **+1.0 bpm** |

Repeated using only minutes where the person was still, the difference is **+1.5 bpm**.

**`causes.yaml` says 1.60 bpm. The measured value is 1.0 to 1.5 bpm. It is right.** I was
wrong, and the reason I was wrong is worth recording: I reasoned that a cause smaller than
the detection threshold could not explain a flagged night, and concluded the cause must be
bigger. The real explanation is the other one. A flagged night is usually **noise**, not
infection, and the belief model is correct to say infection is unlikely.

**What is still wrong, and should be fixed.**

1. **The citation points at the wrong paper.** `docs/CORPUS-VERIFICATION.md` credits "1.8
   percent for females and 3.4 percent for males" to Mishra et al. 2020. I searched that
   paper. The figures are not in it. They are from Natarajan, Su and Heneghan 2022,
   *Frontiers in Physiology* 13:898251, which nothing here cites.
2. **The derivation multiplies numbers from two different groups of people**, a percentage
   from 7,200 Fitbit users by an average from 525 university students. It happens to land in
   the right place, which is luck, not method.
3. **One number is doing the work of two.** The measurement shows the effect has two very
   different sizes: about **1 to 1.5 bpm before symptoms**, and about **4 to 6 bpm at and
   just after symptom onset**. The median day-by-day curve peaks at **+6.00 bpm on the day
   after onset**. The model has one size with a shape on top, and the shape peaks at 1.0, so
   the model's maximum is 1.60 whichever night it is. It captures the pre-symptomatic regime
   and understates the symptomatic one by roughly four times.

**How to do it.**

1. **Keep `effect_mean_bpm: 1.60`.** Replace the derivation text with the measurement above
   and the sample it rests on.
2. Fix the citation to Natarajan, Su and Heneghan 2022, and record it in
   `docs/KNOWLEDGE-CHANGELOG.md`.
3. Replace `effect_sd_bpm: 1.00`, which has no source, with the measured between-person
   spread from the same data.
4. Consider letting the profile rise above 1.0 in its later nights, so the model can express
   the larger symptomatic effect. This changes behaviour, so measure the eleven scenarios
   before and after.
5. Record the infection base rate gap. `causes.yaml` uses 0.025, meaning about nine days of
   infection a year. Adults average two to four colds a year lasting seven to eleven days,
   which is nearer seven percent of days. Either cite a source for 0.025 or raise it.

**How you will know it worked.** Every number in the infection row traces to either a paper
or the measurement, and the changelog says which.

**What could go wrong.** Raising the base rate or the later profile weights will make the
system reach LIKELY_ILLNESS more often. Measure the eleven scenarios, decide whether the new
behaviour is right, then change the expectations and say why. Never the other way round.

## 7. Two corrections to the maths, both in the same direction

`FIX` · Effort **S** then **M** · Risk **low** then **medium**

**The problem, part one.** `causes.yaml` says unrecorded exercise raises heart rate by 4.14
bpm. That number was removed from `constants.py` on 4 September because it is not in the
paper. I checked the PDF: the paper's values either side are 2.91 and 5.59, and 4.14 is
neither. One file was corrected and its twin was missed.

**The problem, part two.** The baseline has a **centre** (your usual rate) and a **band
width** (how much you normally wobble). The centre was fixed to be your own after seven
nights. The band width was not: it is permanently `0.8 x yours + 0.2 x a stranger's`.

**Why it matters.** Exercise at 4.14 is the second biggest effect in the table and competes
with infection to explain a raised night. The band width sets `robust_z`, which is the unit
the extreme heart rate rules are written in, so item 4 depends on this being real. Measured
on a subject with 28 nights of perfectly steady data, their own wobble was exactly zero and
the band width came out at **1.728**, which is entirely the borrowed part.

**How to do it.**

1. Change exertion `effect_mean_bpm` from 4.14 to 2.91 in `data/knowledge/causes.yaml`, and
   fix the derivation text that claims 4.14 is the paper's figure.
2. Record it in `docs/KNOWLEDGE-CHANGELOG.md` with the quoted table.
3. `src/wha/detect/baseline.py`, `compute_baseline`: it already switches the centre to the
   personal median at `BASELINE_MIN_NIGHTS_PERSONAL`. Do the same for `scale_bpm`.
4. Keep `BASELINE_SCALE_FLOOR_BPM = 1.5`. Heart rates are whole numbers, so the wobble can be
   exactly zero, and dividing by zero makes every night look infinitely abnormal.

**How you will know it worked.** The History band narrows as a person's own nights accumulate
and stops moving once it is theirs. For reference, the measured median night-to-night wobble
across 101 real people is **2.97 bpm**, so a mature band width near 3 is right and one near
1.7 is too narrow.

## 8. Tighten the alert rule to the published one

`FIX` · Effort **S** · Risk **low, it trades a little sensitivity for a lot of quiet**

**The problem.** The published algorithm raises a red alert when the reading is at or above
baseline + 4 on **two consecutive nights**. This system flags when two consecutive nights are
raised and **at least one** is RED, so RED followed by YELLOW also fires. That is looser, and
nothing says so.

**Why it matters.** Measured on the cohort, sensitivity in the seven days before symptoms
against investigations opened per week on 76 healthy people:

| Yellow | Red | Rule | Sensitivity | Investigations per person-week | One every |
|---|---|---|---|---|---|
| 3 | 4 | at least one RED | **56.7%** | 0.293 | 3.4 weeks |
| 3 | 4 | **both RED** | 50.0% | **0.204** | **4.9 weeks** |
| 4 | 5 | at least one RED | 50.0% | 0.201 | 5.0 weeks |
| 5 | 6 | at least one RED | 46.7% | 0.147 | 6.8 weeks |
| 6 | 7 | at least one RED | 33.3% | 0.098 | 10.2 weeks |

Today's setting buys 6.7 points of sensitivity for **44 percent more investigations**. Two
other settings reach 50 percent at about 0.20 per week. Nothing reaches 56.7 percent cheaply.

**I also tested whether a personal threshold would do better**, using `robust_z` instead of
beats, since the system already computes it and never uses it to decide anything. It does
not. At every matched alert rate, the fixed threshold in beats is equal or better. The reason
is that dividing by a person's own wobble shrinks a noisy person's real signal along with
their noise.

**How to do it.**

1. `src/wha/detect/detector.py`, `compute_detection_for_features`: change the persistence
   condition from "any RED in the run" to "this night and the previous night are both RED".
2. Keep `DETECT_YELLOW_BPM` and `DETECT_RED_BPM` at 3.0 and 4.0. They are the published
   values and the sweep gives no reason to move them.
3. Record the sweep table in `EVALUATION.md` next to item 19's numbers.

**How you will know it worked.** Re-run `scratch/cohort_eval.py`. Sensitivity should land near
50 percent and the alert rate near 0.20 per person-week.

**What could go wrong.** You lose about one infection in fifteen. Given that the system also
opens fewer investigations, and that every investigation it opens on a healthy person is a
chance to interrupt them for nothing, this is the better trade. If you disagree, the table
above is the whole argument and you can pick a different row.

## 9. Let the cycle answer reach the belief model

`FIX` · Effort **S** · Risk **low**

**The problem.** One of the twelve causes, the menstrual cycle, is switched off and cannot be
switched on. The belief model takes a "does this apply" flag. No code passes it.

**Why it matters.** The system can ask the cycle question, spend part of your interruption
allowance on it, and your answer changes nothing. Confirmed live: the cause sat at exactly
0.0 throughout. The same missing wire means the "recently recovering from an illness" boost
never fires either.

**How to do it.**

1. **Take the fact from the Settings profile in item 5**, not from a probe answer. It is a
   standing fact about a person, not something to spend an interruption on, and item 5 moves
   it there. Fall back to `_cycle_applicability(answers)` if the profile is unset, so an
   already-answered probe is not wasted.
2. `src/wha/agent/nodes.py` already has `_cycle_applicability(answers)`, and `node_conclude`
   already calls it for the displayed text. Pass the resolved value into every
   `update_belief(...)` call as `luteal_applicable`. There are three: in `node_believe`,
   `node_decide` and `node_conclude`.
3. While there, build an `EpisodeContext` with `has_recent_illness` and pass it too. The
   belief model reads it and nothing supplies it. The system already knows this: it is
   whether a closed episode with disposition LIKELY_ILLNESS exists inside the published
   recovery window.
4. **Then retire `probe_cycle`.** With the fact in Settings it has nothing left to ask, and
   removing it frees an interruption. This also shrinks item 28, since `probe_medication`
   becomes the only remaining one-time probe.

**How you will know it worked.** Set "do you menstruate" to yes in Settings, then open an
episode. The luteal cause moves off 0.0 on the Trace tab's belief chart, and the cycle
question is never asked.

## 10. Make `get_data_quality` read the data

`FIX` · Effort **S** · Risk **low**

**The problem.** One of the seven tools the AI can call returns the same three invented
numbers every time, for every person, on every night: `coverage_ratio 0.95`,
`missing_hours 0.35`, `dropped_samples 0`. It never looks at the database.

**Why it matters.** A health system feeding invented numbers to its own reasoning, on the one
tool whose job is to say whether the watch might have misread the night. Confirmed from the
audit log of a live run, on nights whose real coverage was 341 to 362 minutes. The real
numbers are already used by the belief maths, so the AI and the arithmetic are told different
things about the same night.

**How to do it.** `src/wha/agent/tools/impl.py`, `tool_get_data_quality`. It receives `db` and
ignores it. Call `db.get_nightly_features(subject, start, end)`, which the tool directly above
it already uses, and return the real `coverage_minutes` and `implausible_dropped` plus the
count of unusable nights.

**How you will know it worked.** Run an episode, open Audit. The recorded tool result matches
the coverage on the History table.

## 11. Make the execution trace tell the truth

`FIX` · Effort **M** · Risk **low**

**The problem.** The Trace tab lists nine stages and marks **every one as skipped**, on every
episode, with an invented reason. It says "Ask probe not selected by EVSI optimizer" on an
episode whose own summary says a question was asked.

**Why it matters.** This is the screen whose whole job is to show what the system did, and it
shows the opposite. The belief chart directly below shows two real steps and the probability
moving 0.2954 to 0.7774, so the page contradicts itself.

**The cause.** `src/wha/service/episodes.py`, `get_episode` matches stage names against the
`operation` column of the audit log. That column holds ten fixed values and none is a stage
name, so no row can ever match.

**How to do it. Decided: build the trace from graph state, not from the audit log.**

1. `step_episode` already receives the graph result. It knows which nodes ran,
   `tool_call_count` and `depth_used`. Store a small trace record on the episode row.
2. Read it back in `get_episode` instead of scanning `audit_events`.
3. Fill `stage.detail_json` with the tool calls, so the expander in
   `src/wha/ui/components/pipeline_trace.py` finally renders. It is written and has never had
   data.

*The alternative was writing an audit row per node. The schema reserves `invoke_agent` and
`plan` for it, but it roughly triples the log and buries the tool calls, which are the entries
that matter.*

**How you will know it worked.** Open a closed episode, click Trace. Stages that ran say so,
with the tool calls listed under investigate.

## 12. Name the source on Telegram

`FIX` · Effort **S** · Risk **none**

**The problem.** On the dashboard a quoted passage is labelled "MedlinePlus, National Library
of Medicine". On Telegram the same passage is labelled `Sources: Fever`.

**Why it matters.** MedlinePlus is free to use on condition that you credit it. A topic title
is not a credit. Confirmed live by sending a real message and reading what came back. This
closes an open item in `BLOCKERS.md`.

**How to do it.**

1. `source_label()` in `src/wha/ui/components/citations.py` already does this job. It lives
   under `ui/`, which the Telegram code correctly refuses to import.
2. Move it to a shared module, for example `src/wha/retrieve/attribution.py`.
3. Use it in both the dashboard component and `format_for_telegram` in
   `src/wha/service/conversation.py`.
4. Fix the cut-off while there. Messages are trimmed at 900 characters mid-word; in one real
   message the cut fell inside the amber "not from a cited source" block. Trim at a sentence
   end and never inside that block.

**How you will know it worked.** Send yourself a general health question over Telegram. The
reply names MedlinePlus and the National Library of Medicine in words.

## 13. Fix four sentences on the Today page

`FIX` · Effort **S** · Risk **none**

**The problem.** Three statements on the screen you read daily are wrong, and one uses a
phrase the system forbids itself from saying.

| It says | The truth |
|---|---|
| "in contact for 362 minutes **between midnight and 7am**" | that night was measured over the sleep your watch recorded |
| "Your **lowest sustained rate** between midnight and 7am" | it is the **median** across the window |
| "subtracting what a recorded workout **or short sleep** would add" | only exercise is subtracted; `explained.py` says short sleep never is |
| "Probably nothing to worry about" | `red_flags.yaml` lists "nothing to worry about" among phrases the system must never say |

**Why it matters.** The first three misdescribe the design decision this project is proudest
of, on the main screen, while the History page describes them correctly. The fourth is the
system breaking its own safety rule, because the phrase filter runs on what the AI writes and
not on the interface's own words.

**How to do it.**

1. `src/wha/ui/today.py`, lines 199 to 207. The night carries `rhr_window_source`. Say "over
   the sleep your watch recorded" when it is `"sleep"`, and "between midnight and 7am, because
   no sleep was recorded" when it is `"clock"`.
2. Same file: "lowest sustained rate" becomes "the middle of your readings across that window".
3. Same file: delete "or short sleep".
4. `src/wha/ui/history.py` line 130 has the same clock wording.
5. `src/wha/ui/components/wording.py`, `DISPOSITION_PHRASES`: replace "Probably nothing to
   worry about". The explanation underneath it, "Nothing here points towards illness", is fine.
6. Add a test that no phrase in `wording.py` appears in `never_say`.

**How you will know it worked.** Open Today on a night measured over sleep. It says so.

## 14. Four small record defects

`FIX` · Effort **S each** · Risk **none**

**The problem.** Four places where the record states something untrue.

- Every question is filed as having used the canned sentence, even when the AI wrote it.
- Every outcome claims 28 baseline nights and a fully established baseline.
- An escalated episode records the recommended action as "monitor".
- The "stripped claims" panel always shows a green tick.

**Why it matters.** These are all small and all in the record. The record is what you would
show a doctor, and what is supposed to let you check the system rather than trust it. A record
that rounds four facts in the system's favour is worth less than no record.

**How to do it.**

1. `src/wha/agent/nodes.py`, `node_ask` calls `upsert_interaction` without `text_source`,
   whose default is `"fallback"`. Pass `text_source=updated_question.text_source`.
2. Same file, `node_conclude` hard-codes `baseline_nights=28, baseline_rung=MATURE`. It calls
   `db.get_baseline_rung` a few lines above for the disposition. Use the real values.
3. `action_val = "rest" if LIKELY_ILLNESS else "monitor"` sends ESCALATED to "monitor". Map
   ESCALATED to `seek_urgent_care`.
4. `src/wha/service/episodes.py`, `get_episode` sets `stripped_claims = []` and never fills
   it. Store stripped claim text on the outcome in `_enforce_claims` and read it back.

**How you will know it worked.** Open a closed episode from a subject with few nights. The
baseline number matches History, not 28.

## 15. Stop offering things the watch cannot do

`FIX` · Effort **S** · Risk **none**

**The problem.** In a real Telegram message sent during this review, the agent wrote:

> "Would you like me to check your current temperature readings from your watch?"

The watch does not measure temperature and never has. The message printed it twice.

**Why it matters.** An assistant offering a measurement it cannot take loses trust fast and it
is easy to prevent. The duplication happens because the model put the sentence in both the
reply and the question field, and the code appends the question on top.

**How to do it.**

1. `src/wha/llm/prompts/converse.py`: add the channels the watch really provides, which
   `docs/DESIGN-DATA-CHANNELS.md` already lists. State plainly that heart rate variability,
   breathing rate and temperature are not available.
2. `src/wha/agent/conversation.py`, `respond`: only append the question when it is not already
   contained in the reply.

**How you will know it worked.** Ask about your temperature over Telegram. It says the watch
does not measure that, once.

## 16. Stop asking for an amount you then ignore

`FIX` · Effort **S** · Risk **low**

**The problem.** The alcohol question offers "None", "1 to 2", "3 to 4", "5 or more". The
belief model has one on-off alcohol switch, so all three drinking answers do the same thing.

**Why it matters.** The system spends a whole interruption asking a more detailed question
than it can use. Underneath there is a citation problem too: the paper's 2.8 and 2.4 bpm are
the gap between **one drink above** the person's average and **one below**, a two-drink span,
not the effect of drinking at all.

**How to do it. Decided: reduce the question to two options.**

1. `data/knowledge/probes.yaml`: reduce `probe_alcohol` to "None" and "Yes", and update the two
   likelihood rows.
2. Keep recording the free text, so the detail is not lost, it simply does not pretend to feed
   the maths.
3. Correct the derivation text to say what the paper's contrast actually was.

*The alternative was scaling the effect by the reported amount. The paper supports dose
dependence, but no published figure maps "3 to 4 drinks" to a number of beats, so building it
would mean inventing exactly the kind of number item 1 is about.*

**How you will know it worked.** The question on screen has two options.

---

# Tier 2. Honesty. Say what is true.

## 17. Mark the generated numbers on screen

`UNEVIDENCED` · Effort **M** · Risk **none**

**The problem.** Nothing is broken. Some numbers here come from studies of tens of thousands
of people. About 140 were produced by a language model. On screen they look identical.

Four groups need a visible mark:

- **64 answer likelihoods** in `probes.yaml`. These convert what you say into a change in
  belief. No measurement of them exists, and `probes.yaml` explains why better than I can.
- **45 temporal profile weights**, across 10 of the 12 causes, with no source, in a file whose
  header says "THE PROFILE IS WHAT DISCRIMINATES".
- **Ten of the twelve between-person spread values**, and the travel, short sleep and
  "none of the above" effect sizes.
- **The amber "not from a cited source" label itself.** It relies on the AI sorting its own
  sentences. In a real transcript it wrote "that's reassuring" straight into the reply with no
  warning, then on the next turn correctly moved a similar sentence into the amber box. It is
  a floor, not a guarantee, and the screen implies otherwise.

**Why it matters.** The project's own rule is that a guess is stated in the documents **and**
on the dashboard. Right now most of these are in neither, because the documents described them
as human judgement.

**How to do it.**

1. `src/wha/agent/differential.py`, `_answer_reasons` already reads `provenance`. Return it as
   a field rather than folding it into a sentence.
2. In the episode panel, mark any line whose provenance is ASSUMED, with one line
   of explanation under the chart.
3. Under the amber panel in `src/wha/ui/today.py`, add: this labelling is done by the AI itself
   and may miss things, so treat anything without a source as a starting point.

**How you will know it worked.** Open a differential. You can tell at a glance which lines rest
on a study and which do not.

**While you are there.** "that's reassuring" is not on the `never_say` list and arguably should
be.

## 18. Correct three citations

`FIX` · Effort **S** · Risk **none**

**The problem.** Three sources credited with something they do not say.

1. **The infection percentages** are credited to Mishra et al. 2020. They come from Natarajan,
   Su and Heneghan 2022, *Frontiers in Physiology* 13:898251.
2. **The blood oxygen thresholds** are credited to WHO. WHO's January 2021 guidance recommends
   *using* home pulse oximetry. The 94 and 92 percent action levels are NHS England and British
   Thoracic Society guidance, and they are written for people **already known to have
   COVID-19**, not for screening someone healthy.
3. **Downie et al. 2013** is a review of red flags for **cancer and fracture in low back pain**.
   The quotation is accurate; the population is not the one it is used to justify. Sutaria et
   al. 2025 supports the same conclusion directly and should carry the argument.

**Why it matters.** A citation is the whole basis on which this project asks to be trusted with
a clinical number. A citation pointing at the wrong paper fails that as completely as no
citation, and it is harder to spot because it looks correct.

**How to do it.** Edit `docs/CORPUS-VERIFICATION.md`, the infection `citation` block in
`causes.yaml`, the `oxygen.citation` block in `triage_rules.yaml`, and the Downie quotation in
`triage_rules.yaml`. Record each in `docs/KNOWLEDGE-CHANGELOG.md`.

**Two smaller ones.** `POP_PRIOR_CITATION_PLAIN` says "a 2024 study of 525 adults"; they were
first-year university students aged 18 to 24. And the skin-tone caution about pulse oximeters
is stated more strongly than its source, whose own conclusion is that the difference "may not
be clinically relevant".

**How you will know it worked.** Every citation can be opened and the quoted sentence found.

## 19. Publish the detection accuracy

`FIX` · Effort **M** · Risk **none**

**The problem.** `EVALUATION.md` says detection accuracy is "not evaluated" because the labelled
data is missing. `BLOCKERS.md` A-25 and A-26 have been waiting for a human to supply it.

The data was never missing. It is a public 378 MB download, and the symptom dates are in the
same paper's supplementary spreadsheet, shifted the same way as the public files. It took about
forty minutes.

**Why it matters.** This is the project's central claim and it had no evidence.

**How to do it.**

1. Put these into `EVALUATION.md`:

   | Alert fired within | This system | Published NightSignal | Random, same rate |
   |---|---|---|---|
   | 3 days before onset, 1 after | 53.3% | 46.7% | 20.2% |
   | 7 days before, 3 after | 73.3% | 66.7% | 40.4% |
   | 21 days before, 7 after | 83.3% | 80.0% | 73.5% |

   Strictly before symptoms, 7 day window: **43.3%** against 33.3%. Alert burden on 76 healthy
   people over 738 person-weeks: **one investigation every 3.6 weeks** against 4.5.
2. **Always print the chance column.** 83 percent against a 73.5 percent chance floor is not a
   finding. 53 percent against 20 percent is.
3. Move `scratch/cohort_eval.py` into the repository, under `tools/`. A number nobody can
   reproduce is worth little.
4. Close A-25 and A-26 in `BLOCKERS.md` and record how the labels were obtained.

**How you will know it worked.** Someone else runs the script and gets the same numbers.

## 20. Write down how this differs from the published algorithm

`KEEP, now justified` · Effort **S** · Risk **none**

**The problem.** The thresholds and the 78 percent sensitivity come from NightSignal. Five
defining choices were changed here and nothing says so.

| | NightSignal, as its authors wrote it | This system | Verdict |
|---|---|---|---|
| window | midnight to 06:59 | the sleep the watch recorded | justified, see item 21 |
| which minutes | only minutes with zero steps | all minutes | **justified, see below** |
| the night's number | the **mean** | the **median** | **justified, see below** |
| baseline | every previous night including tonight | last 28 nights, excluding tonight | reasonable, untested |
| red alert | two nights in a row at +4 | two raised nights with at least one at +4 | **not justified, see item 8** |

**Why it matters.** The project quotes NightSignal's 78 percent sensitivity as support for
its own thresholds. That number was measured on NightSignal's algorithm, not this one. Until
someone writes down what changed and why, a reader cannot tell which parts of the evidence
transfer. Three of the five changes turn out to be justified, one is untested, and one should
be reverted, and that is a much better story than silence.

**The step filter, measured.** My first draft recommended adopting it, on the theory that it
removes movement. I tested it on 101 real people, scoring the same nights both ways.
Night-to-night wobble: **2.97 bpm with every minute, 2.97 bpm with still minutes only.** Only
15 of 101 people improved. Median change: zero.

**And the reason is the row above it.** NightSignal takes the **mean** of the night, which a
handful of moving minutes drags upward, so it must filter them out. This system takes the
**median**, which is already robust to a minority of high minutes. The step filter is
redundant here **because** of the median. Two deviations that look independent are actually one
choice and its consequence, and together they are sound.

**How to do it.** Add the table above, with these results, to `docs/DESIGN-BASELINE-CENTRE.md`
or a short new design note. Do **not** add the step filter. Do change the red alert rule, which
is item 8.

**How you will know it worked.** Someone reading the design note can say which parts of the
published algorithm were kept, which were changed, and what evidence supports each change.

## 21. Correct three things the documents say exist

`FIX` and `DROP the claim` · Effort **S** · Risk **none**

**The problem.**

1. **`sources.yaml` describes four corpus layers.** StatPearls has never been fetched. What the
   corpus calls layer 2 is three passages generated from `constants.py`. The Singapore care
   pathway layer is the nine passages already in `red_flags.yaml`.
2. **There is no reranking.** Searching the source tree finds none. Search is keyword matching
   plus meaning matching, combined by reciprocal rank fusion. Fusion is not reranking. Adding
   one is item 30; until then the claim should not be made.
3. **The sleep window is justified more widely than measured.** `docs/DESIGN-SLEEP-WINDOW.md`
   presents it as a general improvement. Measured on 21 real people with sleep staging,
   night-to-night wobble got **better for 6, worse for 5, and stayed the same for 10**, because
   only 3 of the 21 sleep much outside midnight to 7am. It is strongly justified for someone who
   sleeps 03:00 to 11:00, which is you, and roughly neutral for a conventional sleeper.

**Why it matters.** A document describing something that does not exist is what let four
subsystems in this project sit unnoticed for months.

**How to do it.** Edit `sources.yaml` to say what each layer is today with a note that two are
planned. Edit `docs/DESIGN-SLEEP-WINDOW.md` to say who the improvement is for. One paragraph
each.

**How you will know it worked.** `sources.yaml` and the output of `wha corpus build` agree.

---

# Tier 3. Delete and simplify.

Deleting is the cheapest way to improve this project. A deletion with a written reason is a
stronger result than a feature.

## 22. Delete the Chronos forecast

`DROP` · Effort **S** · Risk **low**

**The problem.** 182 MB of model weights, a deep learning framework as a dependency, a
prediction every night, and one advisory paragraph that changes nothing.

**Why it should go. This is now measured, not argued.** My first draft justified deletion using
a paper where a forecast was used *instead of* a detector, which is not what this does. That was
a stretch, so I tested the real question on 7,295 real nights:

| | Separates illness nights from ordinary nights |
|---|---|
| Plain baseline residual, what the detector already uses | **AUC 0.629** |
| Chronos forecast residual | **AUC 0.586** |

An AUC of 0.5 is no separation at all. **The forecast separates illness worse than the number
the system already has.** And asked whether it catches anything the detector misses: across 30
labelled infections, at the most generous setting it found **one** case the detector missed,
and at tighter settings **none**.

It is not a duplicate, the two numbers correlate at 0.73, so it is measuring something slightly
different. What it is measuring is just not more useful.

**How to do it.**

1. Remove `chronos-forecasting` and `torch` from `pyproject.toml`.
2. Delete `src/wha/detect/forecast.py` and its call in `detect_night`.
3. Keep the `forecast_status` column, set to `NOT_RUN`, so old rows still read.
4. Remove the forecast paragraph from `src/wha/ui/today.py` and the row from `wha doctor`.

**For your report, this is now a much better section than keeping it would have been.** You
tested whether a time-series foundation model added detection signal over a simple personal
baseline, on 7,295 nights of real data, found it did not, and removed it. That is a justified
model choice with evidence, which is what the rubric asks for. "We included a foundation model"
is not.

**How you will know it worked.** `wha doctor` no longer lists Chronos, `uv sync` installs far
less, and one full episode still runs.

## 23. Delete `get_local_disease_activity`

`DROP` · Effort **S** · Risk **none**

**The problem.** This tool calls a Singapore government address with no search terms and returns
`{"status": "active", "bytes": 12345}`, which is the length of the response. It never reads the
dengue clusters, never checks whether you are inside one, and never asks the air quality service
that is also allow-listed.

**Why it should go.** `sources.yaml` claims "A subject inside an active cluster materially raises
the dengue prior, and no shipped product does this." Nothing raises any prior, and there is no
dengue cause to raise. Making it real means adding a cause and a likelihood, which after item 1
is exactly the kind of number this project should stop generating.

**How to do it.**

1. Remove the name from `CLOSED_TOOL_REGISTRY` and `TOOL_SIGNATURES` in
   `src/wha/agent/tools/registry.py`.
2. Delete `tool_get_local_disease_activity` from `src/wha/agent/tools/impl.py`.
3. Remove the two live endpoints and the dengue claim from `sources.yaml`.
4. Put local outbreak context in the further work section of your report.

**How you will know it worked.** The Audit page lists six permitted tools, not seven.

## 24. Delete the MEASURE limb

`DROP` · Effort **S** · Risk **low**

**The problem.** The system can ask you to take your pulse by hand. That path is broken in three
places: nothing writes to the `measurements` table, the episode state that would show the request
is never set, and the resume logic always answers "declined" whatever you did.

**Why it should go rather than be repaired.** It fires only when a sensor problem leads the
differential at 0.5 or more, and that 0.5 is a generated number with no source. It then asks you
to count your pulse for 30 seconds and double it, which has considerable error of its own. The
honest behaviour is to say the night could not be judged.

**How to do it.**

1. Remove `ActionKind.MEASURE` from the router in `src/wha/agent/graph.py` and delete
   `node_measure`.
2. Remove the MEASURE branch in `src/wha/policy/select.py` and the
   `MEASURE_MIN_LEADING_PROBABILITY` constant.
3. Delete `compute_measurement_logfactor` and the measurement endpoints.
4. Keep the `measurements` table so old databases still open.
5. When sensor problems lead the differential, say so in the outcome instead.

**How you will know it worked.** Run the simulation with a poor coverage night. The outcome says
the night could not be judged.

## 25. Delete the duplicated belief maths

`SIMPLIFY` · Effort **S** · Risk **none**

**The problem.** `compute_residual_loglik` exists twice, in `src/wha/belief/likelihood.py` and
`src/wha/belief/inference.py`, and they differ: one guards an index at both ends, the other only
at the top.

**Why it matters.** This is the arithmetic the project says must be checkable by hand. Two
slightly different copies is the opposite. Coverage over a production run shows the
`likelihood.py` copy and the whole of `run_exact_inference` never execute.

**How to do it.** Delete the unused copy and `run_exact_inference`. Point the tests that call
them at the live path.

**How you will know it worked.** Searching for `compute_residual_loglik` finds one definition.

## 26. Make the conversation limit do something

`FIX` · Effort **S** · Risk **low**

**The problem.** A constant says a conversation may run to ten turns, cited to a Nature study.
The code works out whether you are at that limit, attaches it to the reply, and nothing reads it.

**Why it matters.** A stop condition that does not stop anything is worse than none, because it
appears in the report as a control that exists. The rubric asks explicitly for stop conditions.

**How to do it. Decided: enforce it rather than delete it.**

1. `src/wha/agent/conversation.py`: when `at_limit` is true, reply with a message that says the
   conversation has reached its length and offers the doctor summary. Do not silently refuse.
2. Keep the AMIE citation, which is accurate.

*The alternative was deleting the constant. Enforcing costs the same and keeps a control the
rubric asks for, so there is no reason to delete it.*

**How you will know it worked.** Have an eleven turn conversation. Something happens.

## 27. Have one escalation path, not two

`SIMPLIFY` · Effort **M** · Risk **low**

**The problem.** Two implementations of "check what the person said and escalate".
`report_symptoms` is one, the conversation engine is the other. The dashboard and Telegram use
the conversation engine; the command line uses `report_symptoms`. So "I have chest pain" behaves
differently depending on where you type it.

**Why it matters.** Only `report_symptoms` opens an episode, and it opens a new one every time.
The live database holds **five identical closed escalated episodes**, same dates, never
investigated, all shown separately on History, all from that path.

**How to do it.**

1. Give the conversation engine the ability to open an episode when the rules escalate, via
   `open_or_append_episode`.
2. Change `wha tell` in `src/wha/cli.py` to call `send_message`.
3. Delete `report_symptoms`, or keep it as a thin wrapper for the demo harness.
4. Repeat reports append to the open episode rather than opening a new one, which
   `open_or_append_episode` already does.

**How you will know it worked.** Type the same chest pain message twice. History shows one
investigation.

## 28. Make `one_time` work

`FIX` · Effort **S** · Risk **none**

**The problem.** Two probes are marked `one_time: true`, and their low interruption cost of 0.4
is justified by "asked once and then becomes a modelled covariate". `ProbeDefinition` forbids
extra fields and `load_probes` builds it field by field without reading `one_time`, so the field
is dropped silently.

**Why it matters.** Both probes are priced on a promise that is not kept, so the price is wrong,
and the system can spend part of your allowance asking the same setup question in every new
investigation.

**How to do it. Decided: honour it, and note that item 5 shrinks this job.**

Once item 5 moves the cycle fact into Settings and item 9 retires `probe_cycle`,
`probe_medication` is the only one-time probe left. Honouring the field is then eleven lines
for one probe, which is still worth doing because the probe is priced on that promise.

1. Add `one_time: bool = False` to `ProbeDefinition` and read it in `load_probes`.
2. In `select_action`, skip a one-time probe already answered in **any** past episode, not just
   this one. `db.get_answered_probe_ids` already exists and is per episode; add a subject-wide
   variant.
3. Consider whether `probe_medication` should follow the cycle question into Settings for the
   same reason. It asks whether you have started, stopped or missed a regular medicine, which
   is a **change**, not a standing fact, so it does not move cleanly. Leave it as a probe.

*The alternative was deleting the field and raising the two costs. Honouring it is the same
effort and keeps the design's intent.*

**How you will know it worked.** Answer the cycle question, close the episode, open a new one.
It is not asked again.

## 29. Simplify the story about the interruption budget

`SIMPLIFY` · Effort **S** · Risk **low**

**The problem.** Two counters: two unsolicited questions a week, and five questions inside one
investigation. The second binds. The first never has.

**Why it matters.** Measured on 76 healthy people over 738 person-weeks, the system opens an
investigation once every 3.6 weeks and asks at most one question per investigation. Two per week
is never approached. In a live run with plenty of budget left, the agent asked one question and
stopped, because every remaining question was worth less than the cost of asking. The EVSI
arithmetic did the work, not the counter.

The citation does not fit either. The counter is justified by a review finding that 72 to 99
percent of alarms are false or not worth acting on. That review is about **intensive care unit
bedside monitors**.

**How to do it. Decided: keep the code, fix the story.**

1. Keep `check_interruption_budget_gate`. It costs nothing and is a genuine safety net.
2. In the report and on the Audit page, present the **quiet band** as the thing that prevents
   over-interruption, because it is, and it is a better story than a counter.
3. Note in `constants.py` that the counter has never bound in measurement, and that the alarm
   fatigue citation comes from intensive care rather than consumer notifications.

*The alternative was deleting the counter. After item 6 and item 8 the alert rate changes, so
removing a safety net to save nothing is not worth it.*

**How you will know it worked.** Run the illness simulation. The agent asks one question and
stops, for the same reason it does today.

---

# Tier 4. Worth doing if there is time.

## 30. Add a reranker

`FIX` · Effort **M** · Risk **low**

**The problem.** Search brings back the wrong passages. For an episode about fever, four of the
five passages shown as evidence were about stiff neck, and the top one was the list of answer
options for the symptom question. In a chest pain conversation the one source cited under an
urgent escalation was "How to Prevent Heart Disease".

**Why it matters.** The grounding check proves a sentence came from a passage. It proves nothing
about whether the passage is relevant, and the Evidence tab calls them "Knowledge Citations and
Evidence".

**How to do it.** A reranker is a second, slower model that reads your question and each
candidate passage together and re-scores them.

1. Fetch the top 20 candidates from `HybridIndex.query` instead of the top 8.
2. Score each with a small cross-encoder such as `BAAI/bge-reranker-base`, which runs on a CPU.
3. Keep the best `RETRIEVE_TOP_K`, and cache the scores as the embeddings already are.

**How you will know it worked.** `wha corpus search fever` returns passages about fever.

**OUTCOME, 5 September 2026: MEASURED AND NOT ADOPTED.** The check above passes without a
reranker. Item 31, which rewrote the layer 3 passages, removed the cause: precision at 8
over twelve judged queries is **79.2%**, and `wha corpus search fever` returns eight
passages about fever. A cross-encoder was then tried anyway, in **16 configurations** across
two models, two pool depths, with and without the title in the scored text, and both
replacing the hybrid ranking and fused with it. **Not one beat 79.2%.** The best tied, and
only when fused with the ranking it was meant to improve. This item's exact prescription,
a pool of 20 reordered outright by `bge-reranker-base`, scored **72.9 percent**, and the
same prescription with the faster MiniLM scored **69.8 percent**, which is 9.4 points worse
than doing nothing. Deeper pools were consistently worse: more candidates give the cross-encoder more
off-topic material to promote, and BM25 exact-term matching on a small topical corpus beats
a model trained on MS MARCO web passages. A perfect reranker over the same pool would reach
94.8%, so the headroom exists and neither model captures any of it. The full table and the
reasoning are in the module docstring of `tools/retrieval_check.py`; reproduce the sweep
with `tools/rerank_sweep.py`. Adopting this would have cost 1.1 GB of weights and
seconds per query to make retrieval worse.

The 79.2 percent and all 16 runs were measured on the corpus as it stood that morning. Layer
4, the probe-evidence passages, was rewritten as prose afterwards, because `wha corpus search
fever` still returned the raw answer-option dump at rank 3, which is the failure this item's
problem statement actually described. On the same twelve queries the baseline is now **77.1
percent**, the 2.1 points spent on probe passages surfacing more often now that they are
written in a reader's words. The reranker comparison is unaffected: each model was scored
against the corpus it ran on.

## 31. Stop the corpus leaking the internal keyword lists

`FIX` · Effort **S** · Risk **none**

**The problem.** Two corpus layers are generated straight from YAML, so the passages you are
shown include raw phrase lists: "Any of: 'stiff neck', 'neck stiffness', 'can't touch chin to
chest'", and the whole tier B table with its trigger words.

**Why it matters.** That is an internal keyword list presented as clinical evidence, and it
publishes exactly which words cause an escalation.

**How to do it.** In `src/wha/retrieve/knowledge_docs.py`, the layer 3 generator writes the match
lists into the passage text. Write prose instead: what the sign is, why it matters, what to do.
Keep the rule id in metadata so the audit trail still links back.

**How you will know it worked.** The Evidence tab reads like health information, not a
configuration file.

## 32. Give urgency an expiry

`FIX` · Effort **M** · Risk **medium**

**The problem.** Urgency is the highest level any rule has ever reached in your whole
conversation history, with no time limit. A "see a doctor today" banner from days ago is still at
the top of Today, with no date and no way to clear it.

**Why it matters.** A red banner that never goes away is one you learn to ignore, which is the
alarm fatigue this project cites in its own constants.

**How to do it.**

1. `established_urgency` in `src/wha/agent/conversation.py`: only consider turns from the last N
   days.
2. Show the date the urgency was set next to the banner.
3. Add a button saying you have seen someone about it, which clears it and records that you did.

**What could go wrong.** Urgency must never fall because something reasoned it down. An expiry
is not reasoning, but it must be visible. Never drop it silently.

**How you will know it worked.** Reach "see a doctor today", come back the next day. The banner
carries its date and can be closed with a record.

## 33. Fix the differential chart

`FIX` · Effort **M** · Risk **low**

**The problem.** The chart is labelled "Cause Differential" and drawn as a ranked bar chart, so
it reads like a doctor's list of likely diagnoses. It is not. The twelve numbers are independent,
do not add to 1, and do not compete. A cause that is common and small scores high on any raised
night, because something has to explain the rise.

**Why it matters.** On a real closed episode the system concluded LIKELY_ILLNESS and the chart
underneath put **stress at 0.92** first, with the reason "Nothing gathered in this episode speaks
to this cause either way". The audit page repeats it: "most likely stress at 93%, chance of
illness 78%".

**And after the measurement in item 6, this is the chart that explains the whole system.** A
flagged night is usually noise, so the causes that are common and small will always rise to
explain it. Showing what the evidence *changed* rather than what is *largest* turns the most
misleading panel in the product into the most informative one.

**How to do it.**

1. `src/wha/agent/differential.py`: record each cause's probability **before** this episode's
   evidence and **after**.
2. Rank by how much this episode moved each cause, not by final size.
3. Retitle to something like "What this episode's evidence changed", with one line saying these
   are independent probabilities that do not add to 100 percent.

**How you will know it worked.** On an episode where you answered "feverish", infection is at the
top, because that is the cause the evidence moved.

## 34. Stop padding the audit log, and record the timings

`FIX` · Effort **S** · Risk **none**

**The problem.** Three small things.

1. **Padding.** The Audit page says "a check that found nothing new does not appear". The ingest
   recorder only stays quiet when zero rows were written, and re-pulling the same window rewrites
   the same rows. The live log holds five entries minutes apart, all reading "9785 heart rate
   samples arrived".
2. **No notifications.** `notify` is a permitted operation and nothing writes one, so the record
   does not show a question reached your phone.
3. **No timings.** `src/wha/agent/tools/registry.py` measures each call into `_latency_ms` and
   discards it.

**Why it matters.** The Audit page is the one screen whose purpose is to be trustworthy, and it
makes a claim about itself that is not true. Padding also buries the tool calls between dozens of
identical "data arrived" lines.

**How to do it.**

1. `record_ingest` in `src/wha/audit/monitor.py`: compare against the newest stored sample
   timestamp and stay quiet when nothing newer arrived.
2. Write a `notify` audit row where `record_notification` is called in `node_ask`.
3. Put `_latency_ms` into the `AuditEvent` instead of discarding it.

**How you will know it worked.** Run ingest three times. The Audit page shows one entry.

---

# What needs no work

These came out of the review as **KEEP**. Leave them alone. This list is as useful as the one
above: it is the part of your project that is already right and evidenced.

**The maths.** The sleep window as a design (see item 21 for the claim), the three hour coverage
floor, the personal baseline centre after seven nights, the 3.0 and 4.0 bpm thresholds (now
confirmed by a sweep against personal thresholds), the exercise subtraction table, the robust
z-score, **and the choice of the median over the mean, which measurement showed makes the step
filter unnecessary**.

**The knowledge tables that carry a citation.** The menstrual cycle, alcohol, vaccination,
illness recovery and short sleep base rate all matched their papers exactly, as did all 28
exercise contrasts and every Marburg item and performance figure. **And the infection effect of
1.60 bpm, which now has a measurement behind it as well** (item 6).

**The safety design.** The three-tier floor where fixed rules and the AI combine so the AI can
only add a flag. And the Marburg arrangement, where the AI asks and the published rule decides.
That is the best single idea in the system.

**The belief model.** All 4,096 combinations worked out exactly, in log space, and the time-shape
of each cause that does the real work of telling them apart.

**The policy.** The EVSI calculation, the decision threshold derived from the cost of each error
rather than picked, the swept interruption cost, and the per-episode, tool-call and step limits.

**The agent.** The tool loop, the edge back to investigate after you answer, pausing and resuming
across a restart, the closed list of tools, and the critique pass that may only remove.

**Retrieval and grounding.** Keyword plus meaning search combined by rank fusion, scanning
retrieved text for hidden instructions and marking rather than deleting it, and the word-for-word
claim check, which is the best safety idea in the system and was verified working live.

**The interfaces.** The HTTP boundary that makes the dashboard replaceable, the two-call
conversation design, and the tamper-evident audit log with its plain English nightly explanations.

**The evaluation.** The policy comparison against never-ask and always-ask, and the eleven frozen
scenarios run against the real model.

---

# If you only have one day

1. **Item 1**, correct the provenance lines in `data/knowledge/`. Ten minutes for step 1 alone,
   and it is the difference between a project with a known weakness and a project that lies about
   itself.
2. **Item 2**, check the "when to seek care" text. One hour, the biggest safety hole.
3. **Item 13**, four sentences on Today. One hour, the screen you read most.
4. **Item 12**, name the source on Telegram. Half an hour, closes a blocker and a licence
   obligation.
5. **Item 19**, publish the detection numbers, and **item 22**, delete Chronos with the
   measurement that justifies it. Two hours, and together they turn the project's weakest claim
   into its strongest.

---

# What I would not do

- **Do not add the step filter.** Measured: no difference, because the median already handles it.
  This was in the first draft and is withdrawn.
- **Do not switch to personal thresholds.** Measured: worse at every matched alert rate.
- **Do not add the two missing corpus layers yet.** Correct the description first (item 21). The
  measured problem is relevance, not volume.
- **Do not add more causes.** Twelve is already more than the evidence supports for several, and
  item 33 gets worse with each one.
- **Do not build multi-user support.** One person, one phone.
- **Do not weaken a scenario to accommodate item 6 or item 8.** Measure the new behaviour, decide
  whether it is right, then change the expectation and say why.
- **Do not try to source the 64 answer likelihoods.** I looked. The measurement has never been
  made. Mark them and move on (item 17).
