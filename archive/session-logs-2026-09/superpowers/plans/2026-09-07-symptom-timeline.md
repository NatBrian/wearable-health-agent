# Symptom timeline and the silences it fixes

**Status:** IN PROGRESS, started 7 September 2026.

**Why this exists.** The user asked what happens to a person whose symptom gets worse while
the system stays quiet. Five verified defects answer that, and three of them are the same
shape this project keeps producing: code that exists, is referenced, and is never reached.

## Verified findings

1. **Tier B persistence has never fired, for any symptom, ever.** `symptom_history` is a
   parameter of `check_red_flags_deterministic` that no production caller passes. Grep
   finds three references: the parameter, the pass-through in `tier_c.py`, one unit test.
   So `duration = history.get(rule.id, 1)` is always 1 and `1 > persist_nights` is never
   true. Verified by running five nights of worsening fever: five Falses. Six symptoms
   carry a `persist_nights` value and none of them can escalate alone. Tier C cannot
   rescue it; it is passed only the current message and its own tier B path also requires
   two co-occurring.
2. **No symptom timeline exists in the schema.** `triage_answers` upserts, keeping only
   the latest. Persistence is uncomputable as the data stands. `conversation_turns` keeps
   the raw text, so a timeline can be rebuilt without new data collection.
3. **EVSI structurally cannot notice deterioration.** Every probe targets a cause. Once a
   cause is settled, asking again scores near zero, so the more certain the system is that
   you are ill, the less reason it has to speak to you. `probe_symptoms` has no severity
   and no trajectory in its answer space, so there is no question in the system meaning
   "are you worse than yesterday".
4. **An episode closes benign with a symptom outstanding, and closes silently.**
   `check_close_conditions` blocks on a PENDING interaction but not on a reported symptom,
   and `close_episode` notifies nobody. The 10-night timeout close reaches the person as
   nothing at all.
5. **Sustained YELLOW never flags.** Unmeasured rather than wrong; the sweep compared
   "at least one RED" against "both RED" and never measured a yellow-persistence arm.

Downgraded: the exact-phrase gap in `BLOCKERS.md` is real but tier C rescues it live
("cannot keep fluids down" escalated). Noted: the `budgets` table has no reader or writer
in the service layer. Fails safe, but it is the same dead-code shape a fourth time.

## Decisions, and where they came from

- **Co-occurrence window: 2 nights, DERIVED.** From the shortest `persist_nights` already
  in `red_flags.yaml` (`rf_poor_intake`, `rf_persistent_vomiting`). Not invented; derived
  from numbers already reviewed. User chose this.
- **Outstanding-symptom follow-up overrides EVSI.** A deterministic rule beside the safety
  floor, not a term inside the belief model, because adding trajectory to the belief table
  would mean inventing likelihood rows that no literature supplies. User chose this.
- **Recurrence threshold: 7 days.** Respiratory illness surveillance conventionally
  separates episodes by at least 7 symptom-free days. Contains the dengue saddleback gap
  of 1 to 2 days, so a biphasic fever stays one illness. Shorter than EPISODE_MAX_NIGHTS.
  The clock runs on SYMPTOMS, not green nights, because the source says symptom-free and
  because RHR recovery lags symptom resolution by weeks (Radin: 79 days).
- **GREEN does not mean recovered.** Dengue's critical phase begins at defervescence;
  Faget's sign means heart rate can be normal or low during active infection; RHR takes
  ~79 days to return to baseline after COVID. Two GREEN nights is evidence about the
  READING, not about the PERSON. Green may close the detection; it must not close the
  symptom.
- **Abdominal pain deliberately NOT added to any tier.** The user reserved it as a live
  end-to-end test of whether the agent can recognise a dengue warning sign unaided.
  Pre-registered prediction: it will fail. `corpus.yaml` contains "dengue" zero times, so
  `enforce_grounding` makes a grounded dengue claim impossible, and tier C can only return
  ids from the red_flags list. Only an uncited note can survive.

## Tasks

- [x] 1. `symptom_observations` table + migration to v9.
- [x] 2. Recorder: re-run the matcher over conversation turns, one row per symptom
      per night. Backfill from existing `conversation_turns`.
- [x] 3. Wire `symptom_history` into both production call sites so `persist_nights` fires.
- [x] 4. Co-occurrence over a 2-night rolling window.
- [x] 5. Outstanding-symptom follow-up that overrides EVSI.
- [x] 6. Close honestly: block benign close while a symptom is outstanding; make the
      timeout close speak.
- [x] 7. Recurrence linking at 7 days.
- [x] 8. Regression tests for the DEFECT SHAPE, not just behaviour. 19 tests in
      `tests/unit/safety/test_symptom_persistence.py`, including an AST check that every
      free-text call site passes the history, verified by reintroducing the original bug.
      The episode-advance guard already existed as
      `test_episode_tick_advances_an_open_episode_that_never_timed_out`.
- [x] 9. Yellow arm MEASURED and CLOSED BY MEASUREMENT, like the reranker was.
      `tools/cohort/yellow_persistence.py`, 30 labelled cases, 76 controls, 738
      person-weeks. Adding a yellow-persistence arm to the current rule catches
      **zero additional cases** at every run length from 3 to 7 nights, while costing
      up to 5 percent more investigations on healthy people. Finding 5 is answered: the
      gap is real, and closing it helps nobody. Do not re-litigate from theory.
- [x] 10. Dashboard: step 8 "Check what you told us" added to the pipeline, with the
      symptom table, the arithmetic in words, and the "How this works" topic. Verified in
      a real browser with Playwright.
- [x] 11. Docs all updated, plus `STATUS.md` and `CLAUDE.md`, whose banner still said the
      work was finished.
- [x] 12. Live dengue scenario RUN against the real model. Result in the section below.


## The dengue test, run 7 September 2026 against the real model

**Message sent, as a person would type it:** "I have had a fever for the last three days
and now I have really bad stomach pain and I keep throwing up. I feel restless and I cannot
keep any water down."

**What the system did:**

```
URGENCY : same_day
FLAGS   : ['rf_fever', 'rf_persistent_vomiting', 'rf_poor_intake']
GUIDANCE: Two or more of these together ... is worth a same-day appointment. A
          polyclinic or a GP is appropriate. Go to an A&E if you develop any of the
          urgent signs listed above.
CITED   : ['Diarrhea']   (MedlinePlus)
```

**What the agent said:** *"...Having a fever for three days with severe stomach pain,
vomiting, and inability to keep water down is concerning. This could be due to an infection
or other serious condition. It's important to seek medical attention today, as you may need
fluids or treatment to prevent dehydration. **Have you noticed any blood in your vomit or
stools?**"*

**The prediction held.** It never said dengue, and it could not: `corpus.yaml` has no dengue
passage, so `enforce_grounding` cannot pass a dengue claim, and Tier C can only return ids
from the red-flag list.

**But it did better than the prediction, in one specific way worth recording.** Unprompted,
it asked about **mucosal bleeding**, which is a WHO dengue warning sign and a tier A rule it
was not told to seek. It reasoned to a red flag rather than pattern-matching a word. That is
the behaviour the design is supposed to produce.

**Three things it got wrong, and they are the finding.**

1. **Severe abdominal pain was invisible to every rule.** It is in no tier and not tracked,
   so it reached the belief model and nothing else. The agent read it in the transcript and
   the floor never saw it.
2. **Same-day is arguably UNDER-triaged for this picture.** Three days of fever with severe
   abdominal pain and persistent vomiting is a WHO dengue warning-sign presentation, which
   warrants referral for observation, not a polyclinic appointment "today". The system has
   no way to know that, because it has no dengue content.
3. **Nothing warned about defervescence.** The single most important thing to tell a person
   in this position is that the danger rises as the fever breaks. The system does not know
   it.

**The decision this forces is the user's:** whether this system should carry
Singapore-specific clinical content in its corpus. `sources.yaml` already names national
dengue guidance as material that should be there. Recorded in `BLOCKERS.md`.
