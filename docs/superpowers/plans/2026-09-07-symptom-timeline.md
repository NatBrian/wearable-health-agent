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
- [ ] 6. Close honestly: block benign close while a symptom is outstanding; make the
      timeout close speak.
- [ ] 7. Recurrence linking at 7 days.
- [ ] 8. Regression tests for the DEFECT SHAPE, not just behaviour: fail if any
      `persist_nights` rule can never fire end to end; fail if a newly opened episode is
      never advanced.
- [ ] 9. Measure the yellow arm with `tools/cohort/sweep.py`, report the number.
- [ ] 10. Dashboard: the record tab, the step list, and the pipeline must show the symptom
      timeline and say why it escalated or did not.
- [ ] 11. Docs: `ARCHITECTURE.md`, `CONTRACTS.md`, `DISCLOSURES.md`,
      `KNOWLEDGE-CHANGELOG.md`, new `DESIGN-SYMPTOM-TIMELINE.md`, `BLOCKERS.md`
      (the dizziness item dissolves: it needs tracking, not a red flag).
- [ ] 12. Live dengue scenario with the real model, as the acceptance test.
