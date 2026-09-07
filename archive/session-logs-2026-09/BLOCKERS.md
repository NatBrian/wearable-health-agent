# BLOCKERS

**Append, never rewrite.** One section per blocker. A recorded blocker is a good outcome. A silent
workaround is the worst one.

Use this template:

```markdown
## <task-id> — <one line>

**What I tried:** the specific thing, with the command or the call.

**What happened:** the exact error text, pasted.

**What I think is wrong:** which document or assumption does not hold.

**What I need:** a decision, a missing constant, a corrected test, a value in a knowledge table.
```

After recording, mark the task `[!]` in `PROGRESS.md` and move to the next **independent** task.

**Do not** invent a workaround, relax a type, add `# type: ignore`, catch and swallow an exception,
stub out a blocked module, or change a contract to unblock yourself.

---

## A-25 - RESOLVED 5 September 2026. Cohort labels were never unavailable

**Resolved, and now reproducible from this repository.** The Mishra 2020 wearables data is a
public 378 MB download and the symptom onset dates are in the same paper's Supplementary
Data 1, Supplementary Table 3, on the **same date shift** as the public files, so they join
directly. `cohort_labels.yaml` never needed authoring; `experiments/detection/cohort/labels.py` extracts the
labels from the spreadsheet.

**What it settled:** the detector, run against this archive, performs comparably to the
published algorithm whose thresholds it borrows rather than better than it, and every
sensitivity figure has to be read against a rate-matched chance floor because a wide enough
window flatters any detector.

An earlier, higher figure came from a looser alert rule than the one being cited, and is
superseded rather than better.

**The figures themselves are in `experiments/detection/`, behind its disclaimer, and are
not repeated here.** They are a re-analysis of an archive by the author, not a trial, and
nothing was warned, acted on or changed by them.

Reproduce:

```bash
uv run python experiments/detection/cohort/fetch.py
uv run python experiments/detection/cohort/labels.py
uv run python experiments/detection/cohort/evaluate.py
uv run python experiments/detection/cohort/report.py
```

The original text follows.

## A-25 (original) - Missing data/knowledge/cohort_labels.yaml for cohort evaluation

**What I tried:** `uv run pytest tests/unit/eval -q && uv run wha eval detection`

**What happened:**
```
Evaluation skipped / error: Cohort labels file missing at 'data\knowledge\cohort_labels.yaml'. Stanford and PMData ground truth labels live in supplementary information and must be provided.
```

**What I think is wrong:** Stanford and PMData ground truth labels live in the paper's supplementary data and are not part of the dataset archives. `data/knowledge/cohort_labels.yaml` is an external knowledge input that cannot be modified by the agent (Rule 3).

**What I need:** Human authoring of `data/knowledge/cohort_labels.yaml` containing ground truth symptom onset and infection labels from the study supplementary data.

---

## A-26 - RESOLVED 5 September 2026, by the same route as A-25

The baseline-age curve runs on the same cohort and the same labels. It also lost its second
arm: it compared "shrinkage" against "chronos", both arms called the same detector, and the
forecast never set `level` or `flagged`, so the two computed identical alerts and the second
column was the first under another name. Chronos is now removed entirely.

## A-26 (original) - Missing data/knowledge/cohort_labels.yaml for baseline-age evaluation

**What I tried:** `uv run wha eval baseline-age`

**What happened:**
```
Evaluation skipped / error: Cohort labels file missing at 'data\knowledge\cohort_labels.yaml'. Stanford and PMData ground truth labels live in supplementary information and must be provided.
```

**What I think is wrong:** Baseline age evaluation requires Stanford cohort illness labels to evaluate detection recall against truncated history lengths.

**What I need:** Human authoring of `data/knowledge/cohort_labels.yaml`.


---

## illness-onset — LIKELY_ILLNESS is unreachable under the authored knowledge tables

**What I tried:** `uv run wha demo run illness-onset`, after making the demo actually open an
episode, run the agent and compare the result against the fixture's frozen `expect` block.

**What happened:**

```
[PASS] flagged_on_day: expected 29, got 29
[FAIL] disposition:    expected 'LIKELY_ILLNESS', got 'EXPLAINED_BY_EVENT'
[FAIL] asks_at_least:  expected 1, got 0
```

Measured, not inferred. Belief over the two flagged nights (residuals 4.6 bpm):

```
p_illness = 0.0246   top: luteal=0.873, sleep_restriction=0.331, stress=0.314
```

With luteal forced inapplicable it is still only 0.070, behind stress and alcohol.

**What I think is wrong:** three frozen artefacts are on incompatible scales.

| Source | Value |
|---|---|
| `constants.py` `DETECT_YELLOW_BPM` | 3.0 bpm |
| `constants.py` `DETECT_RED_BPM` | 4.0 bpm |
| `causes.yaml` infection `effect_mean_bpm` x peak profile | **1.60 bpm** |
| `causes.yaml` luteal `effect_mean_bpm` x peak profile | 3.91 bpm, base rate 0.450 |
| `causes.yaml` exertion `effect_mean_bpm` x peak profile | 4.14 bpm |

**Infection is the one cause the system exists to find, and its modelled peak effect of 1.60 bpm
is below the 3.0 bpm threshold at which the detector notices anything at all.** Only luteal and
exertion can reach YELLOW on their own. So every night the detector flags is, under the authored
priors, better explained by something other than infection, and `p_illness` cannot rise from
sensor evidence alone.

That in turn starves the policy. The EVSI arithmetic is sound and produces a clean quiet band,
measured here:

```
 p_inf   evsi(probe_symptoms)   score = evsi - cost   asks?
 0.020        0.0156                 -0.2844           no
 0.050        0.1950                 -0.1050           no
 0.080        0.4280                 +0.1280           YES
 0.100        0.5850                 +0.2850           YES
 0.200        0.3700                 +0.0700           YES
 0.300        0.1550                 -0.1450           no
```

Asking is worthwhile only between roughly p=0.06 and p=0.28. Belief never enters that band, so no
question is asked, so the oracle's `probe_symptoms: "fever"` never reaches the model, so the
disposition cannot become LIKELY_ILLNESS. The same root cause fails `red-flag` (the tier-A phrase
is carried in the oracle's free text, which is only collected when a question is asked),
`no-response-timeout`, `stress-mimic`, `injection-poisoned` and `injection-clean`.

**What I need:** a human decision on which of the three authored numbers is wrong. Every candidate
is a CITED or DERIVED clinical value or a contract constant, and Rule 2 forbids me inventing any of
them.

1. `causes.yaml` infection `effect_mean_bpm = 1.60` is marked DERIVED and "re-verified 2026-09".
   If the intended figure is the elevation seen in a symptomatic infection rather than the average
   across all infected nights, it is plausibly several bpm higher.
2. `DETECT_YELLOW_BPM = 3.0` may be too high to catch the infection the model describes.
3. The fixture's `local_disease_activity: {dengue_cluster: true, cases: 14}` is read by nothing.
   `EpisodeContext` has no field for it and `update_belief` has no hook. Raising the infection
   prior during a local outbreak is the obvious intended mechanism and would lift belief into the
   ask band, but the size of that adjustment is a number no knowledge table supplies.

Until one is resolved, `illness-onset` reports its failure honestly rather than passing silently.

---

## Synthetic illness injection cannot satisfy both the fixture and the temporal profile

**What I tried:** removing an undocumented `+ 2` offset in `src/wha/ingest/synthetic.py`, which made
the illness injection skip the `[0.5, 0.8, 1.0, ...]` ramp from `causes.yaml` and apply full
amplitude from the first night.

**What happened:** with the ramp applied from its start, `illness-onset` at `amplitude_bpm: 4.6`
produces residuals of 2.3 and 3.68 bpm. `DETECT_RED_BPM` is 4.0, so the night the frozen fixture
requires to be flagged never leaves YELLOW and the scenario stops flagging at all.

**What I think is wrong:** the fixture's `amplitude_bpm` states the elevation to be OBSERVED on the
illness nights, while `causes.yaml` states the amplitude of the cause BEFORE its temporal profile is
applied. The two readings cannot both hold.

I kept the fixture satisfied, indexing the profile from its peak, and documented it at the call
site. The cost is real and worth stating plainly: simulated illness is therefore flat, and a rising
then falling shape is exactly what distinguishes infection from the luteal phase in `causes.yaml`.
The generator is producing data that the belief model is bound to read as the wrong cause.

**What I need:** confirmation of which reading of `amplitude_bpm` was intended. If it is the cause
amplitude, the fixtures need larger values to clear the detection thresholds.

---

## data/datasets/stanford and pmdata are empty, and doctor reports them present

**What I tried:** `uv run wha doctor`, then `ls data/datasets/*`.

**What happened:** doctor prints `datasets  ok  stanford and pmdata present`. Both directories exist
and are empty; `du -sh data/datasets` reports 0 bytes.

**What I think is wrong:** `service/doctor.py` tested `(data_dir / name).exists()`, which is true for
an empty directory. Fixed to require content, so the row now reports the truth. The underlying
blocker stands: no cohort data is present, so A-25 to A-28 remain blocked on the download as well as
on the missing `cohort_labels.yaml` already recorded above.

**What I need:** nothing. **RESOLVED 5 September 2026.** The cohort is fetched, the labels
are extracted from the paper's supplementary data, and detection accuracy is measured and
published. `wha doctor` still reports `datasets miss` because that row checks
`data/datasets/`, which is a different path from `data/cohort/` where the cohort now lives;
that is a cosmetic disagreement between two directory names and not a missing dataset.


---

## RESOLVED: illness-onset, and the cause of most scenario failures

Recorded above as unresolvable without changing a cited clinical figure. That reading was
wrong, and the measurement that settled it is worth keeping.

Neither the infection effect size (1.60 bpm, DERIVED from published percentages) nor the
detection thresholds (3.0 and 4.0 bpm, cited from Alavi 2022 NightSignal, which reaches
80 percent sensitivity at exactly those cutoffs) needed to move. Both are well sourced and
both are correct.

The defect was in code. `update_belief` took `luteal_applicable: bool = True`, collapsing
the three-state fact the contract defines (`cycle_applicable: bool | None`, "None means
not yet asked") into an assumption that every unasked subject menstruates. luteal is the
largest benign effect in causes.yaml at 3.91 bpm on a 0.450 base rate, so assuming it
applied let it explain away exactly the elevations the system exists to investigate.

Measured on illness-onset: p(infection) 0.025 assuming applicability, 0.070 treating it as
unestablished. The second figure is inside the band where the EVSI policy finds a question
worth its interruption cost, so the policy asks, the answer arrives, and the episode
reaches LIKELY_ILLNESS.

The sweep of POLICY_COST_PER_INTERRUPT, annotated "Swept" and never actually swept, moved
the default from 0.30 to 0.15 on measured evidence. Scenario pass rate went from 4 of 11
to 10 of 11.

---

## no-response-timeout — the injected elevation never reaches the RED threshold

**What I tried:** `uv run wha demo run no-response-timeout`.

**What happened:**

```
[FAIL] disposition: expected 'UNRESOLVED', got None
[FAIL] asks_at_least: expected 1, got 0
```

No episode opens, so no question is asked and no disposition is reached.

**What I think is wrong:** the fixture requires an alert event, which needs a run of
YELLOW-or-above nights containing at least one RED. The scenario's injected elevation
produces a residual of 3.65 bpm on its two illness nights. `DETECT_YELLOW_BPM` is 3.0 and
`DETECT_RED_BPM` is 4.0, so both nights are YELLOW and no run ever contains a RED.

Measured, with `explained_bpm` at 0.0, so nothing is being subtracted:

| scenario | fixture amplitude | observed residual | level | flags? |
|---|---|---|---|---|
| illness-onset | 4.6 | 4.25 | RED | yes |
| red-flag | 4.2 | 3.45 | YELLOW | no |
| no-response-timeout | ~4.4 | 3.65 | YELLOW | no |

The roughly 0.75 bpm gap between the injected amplitude and the observed residual comes
from the baseline centre sitting above the scenario's clean-night level and from the
nightly resting heart rate being derived from integer-quantised samples. So a fixture
needs an amplitude of about 4.8 or more to produce a RED night.

red-flag was resolved on its own merits, not by changing an amplitude: escalation must not
depend on the detector having flagged anything, so an unsolicited symptom report now runs
the deterministic floor directly. no-response-timeout has no free text and genuinely needs
an episode.

**What I need:** a decision on the fixture, which is read-only to me. Either its amplitude
rises to roughly 4.8 so the scenario produces the RED night it assumes, or the scenario is
re-authored to open its episode some other way. Nothing in the code is wrong here, so I
have not changed anything to force it green.


---

## Blood oxygen is now ingested but cannot yet inform the belief model

**What I tried:** probing the live Health Connect bridge on 2026-09-02 with the token from
`.env`, after the phone and laptop were on the same network.

**What happened:** the device returns **seven** populated types, not the four
`history/HANDOFF.md` section 10 records as measured fact:

| Type | Records over 7 days | Previously ingested |
|---|---|---|
| heart_rate | 3,652 | yes |
| steps | 4 | yes |
| sleep | 3 | yes |
| exercise | 3 | yes |
| **oxygen_saturation** | 5 | no |
| **distance** | 1 | no |
| **total_calories** | 3 | no |

Respiratory rate, skin temperature and HRV are still absent, so that half of section 10
holds.

All three new types are now normalised, stored and exposed to the agent through
`get_known_events`. Field names were read off the live payload rather than guessed:
`percentage`/`time` for blood oxygen, `meters` and `calories` with `start_time`/`end_time`
for the other two.

**What I think is wrong:** nothing, but there is a gap worth naming. Blood oxygen is the
one of the three with real diagnostic value for infection, and it cannot be used yet.
`causes.yaml` has no likelihood relating a blood oxygen reading to any of the twelve
causes, and inventing one would be exactly the fabrication this repository exists to
avoid. So the readings are captured and shown, and the belief model ignores them.

Two further points a human should weigh before that changes:

1. The readings are **spot measurements, not a stream**. Five over seven days, and two of
   those a minute apart. There is no nightly value to speak of on most nights.
2. They are **noisy**. The observed set includes a 94, a 92, a 94, and then an 80 followed
   66 seconds later by a 92. A likelihood written against consumer wrist readings would
   need to model that noise or it will manufacture alarm.

**What I need:** a cited likelihood row in `causes.yaml` for blood oxygen, or a decision
that it stays captured-but-unused. Distance and calories need no such row: they are
activity context for the agent to read, not evidence the belief model weighs.

---

## production-loop — an OBSERVE decision is never revisited on later nights

**What I tried:** ran the mock watch bridge (`tools/mock_watch.py`) forward a day at a
time through an illness arc: 35 healthy nights, then RED at +4.65 bpm on 2026-09-04,
flagged on 09-05, RED again 09-06, YELLOW 09-07, GREEN 09-08 and 09-09.

**What happened:** the episode opened, the agent asked `probe_symptoms`, the answer
`fever` moved p(infection) from 0.071 to 0.3893, and the policy then chose OBSERVE
("Belief is inside uncertainty band; observing next night data"). From that point the
belief never moved again. Every later tick incremented `step_count` and wrote no new
belief row, and p(infection) stayed at 0.3893 through three further nights. The episode
eventually closed `LIKELY_BENIGN` on the quiet-run condition in
`check_close_conditions`, not through the agent.

**What I think is wrong:** nothing is crashing; this is a control-flow question the
contract does not settle. `run_episode_step` passes `payload = None` once a checkpoint
exists, which is correct for an episode parked on an `interrupt()`. But a settled episode
has `next == ()`, so invoking it with `None` runs no nodes at all. OBSERVE therefore means
"stop thinking permanently" rather than "wait for another night and reconsider", and the
only remaining exits are the two time-based conditions in `check_close_conditions`.

The consequence worth weighing: if the person had got sicker after the OBSERVE, more RED
nights would not have re-entered the belief and the agent could not have escalated. The
deterministic red-flag floor still applies, so this is not a safety hole, but it does blunt
the thing the project is arguing for.

**What I need:** a decision on when a settled episode should be re-entered at START with
the nights that have arrived since. Re-entering on every tick would re-run the LLM nodes
against unchanged evidence; re-entering only when a new detection has landed since the last
belief row looks right, but it is a design choice, not a bug fix, so I have not made it.

---

## production-loop — episode dates come from the wall clock, not the data

**What I tried:** the same forward simulation, where night dates run ahead of the real
calendar date.

**What happened:** the episode opened on `2026-09-05` (a night date) and closed with
`closed_on = 2026-09-02` (the wall-clock date). `check_close_conditions` computes
`today = datetime.now(UTC).date()`, so its `EPISODE_MAX_NIGHTS` arm compares a night date
against the real clock and yields a negative elapsed count, which can never fire.

**What I think is wrong:** the assumption that the system always runs in real time, one
night behind the data. That holds in production and does not hold under simulation. I have
deliberately NOT changed production code to accommodate the simulator, because making the
lifecycle read its clock from the data would be a real behavioural change and the wrong
direction to take on a simulator's behalf.

**What I need:** confirmation that real-time operation is the intended and only supported
mode, in which case this is a documented limitation of `tools/mock_watch.py` rather than a
defect. The quiet-run close arm is unaffected and does fire correctly.

---

## production-loop — the synthetic generator covers four of the seven live channels

**What I tried:** compared the mock bridge payload against the last real Galaxy Watch 5
payload stored in `raw_payloads`.

**What happened:** the real payload carries `heart_rate`, `sleep`, `steps`, `exercise`,
`oxygen_saturation`, `distance` and `total_calories`. `Synthetic` emits only the first
four. Sleep stages also differ in encoding: synthetic writes `LIGHT`/`DEEP`/`REM`, the
device writes numeric codes such as `"4"`, `"1"`, `"5"`. Both normalise, so this is
cosmetic, but it is a difference.

**What I think is wrong:** nothing. Blood oxygen has no likelihood in `causes.yaml`, so
adding it to the generator would produce a channel the belief model still ignores, and
distance and calories are activity context the agent reads rather than evidence. Writing
generators for all three to make a dashboard look fuller would be fabrication for its own
sake.

**What I need:** nothing, unless the blood oxygen likelihood above is ever authored, at
which point the generator should grow a matching channel so the two halves stay testable
together.

---

## audit-scope — ingest and nightly are not recorded in the audit log

**What I tried:** a first run as a new user: `wha ingest --days 7`, `wha nightly`, then the
Audit page in the dashboard.

**What happened:** `audit_events` held zero rows, while the page said "Everything this
system does is written down as it happens" and, in green, "No. The record is intact.
Every entry still matches the fingerprint taken when it was written." It was verifying an
empty list and reporting success on the one page whose purpose is to be trustworthy.

**What I think is wrong:** nothing in the chain implementation. `verify_hash_chain`
correctly returns intact for an empty chain; the caller simply never asked how many
entries there were. Audit rows are written by `EpisodeRepository.append_audit` from the
agent's tool registry and by `update_settings`, and by nothing else. Ingest, feature
extraction, baseline update and detection write none.

I have narrowed the page's claim to what is true and made an empty log say so, rather than
making the deterministic pipeline write audit rows. Recording every night scored would
change what the log is for and would bury the agent's tool calls, which are the entries
the contract cares about, under routine bookkeeping.

**What I need:** a decision on whether the audit log is meant to cover the deterministic
pipeline as well as the agent. If it is, the honest version records one event per nightly
batch rather than one per night, and `docs/CONTRACTS.md` should say so.

---

## timezone — "today" was computed in UTC and compared against local night dates

**What I tried:** installed at 01:41 Singapore time, ran `wha ingest --days 7` and
`wha nightly`.

**What happened:** the system reported "monitoring began on 2026-09-02" and treated the
night of 09-02 as one it had been watching, though the subject installed on 09-03. The
dashboard reported watch data "Arriving (17:41)" for an ingest that happened at 01:41
local.

**What I think is wrong:** a night is labelled with a local calendar date, resolved
through the subject's timezone in `features/window.py`. "Today" was
`datetime.now(UTC).date()` in twelve places and compared against those local dates. For
UTC+8 the two differ for the whole window between local midnight and 8am, which is
precisely when someone checks a sleep monitor.

Fixed by routing every such comparison through `wha/clock.py`. Recorded here because the
class of bug is worth naming: any new code that reaches for `datetime.now(UTC).date()` and
compares it against a night date reintroduces it, and nothing in the type system prevents
that.

**What I need:** nothing. Noted so the next person does not reach for the UTC date again.

---

## sleep-window — the night was measured by the clock, not by when the person slept

**What I tried:** compared the fixed local 00:00-07:00 window against the sleep sessions the
first real subject's watch actually recorded.

**What happened:** the subject sleeps roughly 03:00 to 11:00. The clock window counted 2.6
to 3.6 hours of waking time as sleep on each of three nights and discarded about 40 percent
of the real sleep. Recomputing over the recorded sleep moved the readings from 51, 56 and 48
bpm to 44, 45 and 45, and cut the night-to-night spread from 8 bpm to 1 bpm.

**What I think is wrong:** nothing in the arithmetic. The window was the NightSignal
definition, correct for a study without sleep staging and wrong for a build that has it.
Fixed in place, with the reasoning and citations in `docs/DESIGN-SLEEP-WINDOW.md` and the
contract amended.

**What I need:** two things a human should weigh.

1. **Apnoea remains invisible and always will under this design.** A condition that raises
   sleeping heart rate every night is absorbed into a personal baseline that adapts over 28
   nights, so it becomes the subject's normal and is never flagged. This is disclosed on the
   History page. Whether the system should attempt anything here is a clinical scope call.
2. **Consumer sleep staging is not polysomnography.** A night whose staging is wrong yields
   a window that is wrong. There is no cross-check for this in the build.

---

## demo-isolation — `wha demo run` wrote synthetic people into the real database

**What I tried:** ran all eleven frozen scenarios with `wha demo run <name>` while verifying
a change, on a machine whose configured database held a real subject's health record.

**What happened:** eleven synthetic subjects and roughly 420,000 fabricated heart rate
samples were written into `data/wha.sqlite` alongside the real subject. Nothing at query
level distinguished them: a `SELECT COUNT(*) FROM heart_rate_samples` returned 431,894 of
which 11,853 were real. I misread the subject's own data because of it before noticing the
subject column.

**What I think is wrong:** `run_demo` defaulted its database to `settings.db_path`. A demo
invents a person, and inventing people inside a real health record is not something a user
should have to opt out of.

Fixed: demos write to `data/demo.sqlite` unless a database is named explicitly with
`--db`, and the run prints which database and which synthetic subject it used. A test
points `WHA_DB_PATH` at a real database and asserts the demo leaves it untouched.

**What I need:** a decision on the eleven synthetic subjects that any earlier run may have
left in a user's database. They were removed from this machine with
`delete_all_subject_data`, but there is no command a user could run to find or clean them,
and no marker on a subject row saying it was synthetic. `subjects.source_kind` is set to
`synthetic`, so a `wha subjects prune --synthetic` would be straightforward if wanted.

---

## baseline-centre — the detector compared everyone against the average adult

**What I tried:** asked why the first real subject's nights all sat below the displayed
band, then measured what rise would be needed to flag them.

**What happened:** `compute_baseline` blended the personal median with the 62.75 bpm
population prior at `w = n / (n + 7)`. `BASELINE_WINDOW_NIGHTS` caps `n` at 28, so `w`
capped at 0.800 permanently and a fifth of the prior never washed out. Measured on a steady
subject after 200 nights of their own data: 45 bpm carried a -3.5 residual every night and
needed a 6.5 bpm rise to reach YELLOW; 80 bpm carried +3.5 and sat at YELLOW every night
while perfectly healthy. Infection raises nocturnal RHR by 1.6 to 5 bpm, so the first real
subject, who sits at 44 to 47, would never have been flagged for an infection at all.

**What I think is wrong:** the thresholds are NightSignal's, and NightSignal measures
deviations above a per-individual streaming median with no population blending. Shrinking
the centre and then applying those numbers to it is a category error. Fixed: the centre is
the person's own median once seven usable nights exist, seven being the figure the same
paper reports for baseline establishment, and nothing is flagged below that. Scale keeps
its shrinkage because it only sets band width and never the level. Detail and citations in
`docs/DESIGN-BASELINE-CENTRE.md`.

**What I need:** two judgements a human should make.

1. **The centre steps discontinuously at the seventh night**, from a mostly-population
   value to the person's own median. For a 45 bpm subject that is a drop of about 9.6 bpm,
   visible on the History chart. I have left it unsmoothed and labelled, because it marks a
   real change in what the number means, but it is a presentation decision.
2. **`POP_PRIOR_RHR_MEAN_BPM` now only affects the first six nights.** Whether a single
   population mean is the right cold-start prior for all ages and sexes is a clinical
   question this build does not address; Bloomfield et al. report variation by both.


---

## no-response-timeout — the fixture was never wrong, the baseline was

**What I tried:** re-ran the frozen scenarios after making the baseline centre the person's
own median.

**What happened:** this scenario's residuals are now exactly 0.0 on healthy nights and 4.0
on the injected illness nights. It reaches RED, opens an episode, and asks a question. The
two failures recorded against it earlier, "disposition: got None" and "asks_at_least: got
0", are both gone.

**What I think is wrong:** the earlier entry in this file, which said the fixture's
amplitude was too low and "needs roughly 4.8 bpm to produce the RED night it assumes",
and marked it read-only. That diagnosis was wrong. The 4.4 bpm amplitude was correct all
along; the shrunk baseline centre was consuming 0.4 bpm of the margin, which is exactly the
bias described in `docs/DESIGN-BASELINE-CENTRE.md`. No fixture was edited.

**What remains:** one expectation still fails. The person never answers, the question times
out, and the episode closes `LIKELY_BENIGN` where the fixture expects `UNRESOLVED`. With
two RED nights and no answer, concluding "benign" is over-confident, and `UNRESOLVED` is
the honest disposition when the evidence is incomplete. That now looks like a real defect
in the timeout path rather than a fixture problem, but it is a separate investigation and I
have not opened it.

**What I need:** confirmation that a timed-out question should close an episode as
UNRESOLVED rather than LIKELY_BENIGN, and then that path fixed.


---

## audit-scope — RESOLVED. The deterministic pipeline is now in the record

The earlier entry asked whether the audit log should cover the deterministic pipeline as
well as the agent. A user answered it by opening the page after a night had been fully
processed and finding it empty: "what I expect is the audit will show any data and their
system logic trail so user can fully understand what happened, not silent."

Implemented in `src/wha/audit/monitor.py`. Ingest and night scoring write to the same
hash chain, only when something actually changed, and refusals are recorded as well as
actions. Each entry carries both the exact figures and a plain narrative, because the
requirement was explicitly that a non-doctor, non-engineer can understand it.

Two findings surfaced while building it and are fixed: `detect_night` rebuilt its features
without `rhr_window_source`, so the record told a reader their watch had recorded no sleep
on a night it had measured; and a negative residual was being reported as a signed number,
which reads as a fault to someone who is simply below their usual.

---

## interruption-budget — testing subjects each had their own allowance

**What I tried:** opened the subject's real Telegram history after a day of simulation.

**What happened:** seventeen questions, from a system whose design permits two interruptions
per week.

**What I think is wrong:** `count_interruptions_since` filtered by `subject_id`. This is a
single-user application, one person and one phone, but the database had accumulated demo
and simulation subjects, and each carried its own private allowance pointing at the same
Telegram chat. Fixed by counting across all subjects, which for one real user is simply
counting that user.

Two contributing causes were mine rather than the system's, and are worth naming so they
are not repeated: `wha serve` was left running against the live Telegram token throughout a
day of testing, and deleting a subject between runs removed the `interactions` rows the
budget counts, silently resetting it.

**What I need:** a decision on whether a synthetic subject should be able to notify at all.
`subjects.source_kind` already records `synthetic`, so the notifier could refuse on that
basis, and a simulation would then be unable to message a real person however it is run.


## corpus — RESOLVED. Two cited figures did not survive checking against the paper

**What I tried:** before generating `data/knowledge/corpus.yaml`, fetched every paper the
corpus quotes and read the sentence carrying each number. Full record in
`docs/CORPUS-VERIFICATION.md`.

**What happened:** most figures matched exactly, including every load-bearing one. Two did
not.

1. **`causes.yaml`, luteal, the second and third figures in the citation string.** It reads
   "heart rate +3.91 bpm (P<.001), wrist skin temperature +0.44 C, respiratory rate
   +0.60/min". Read off the phase means in Goodale et al. 2019 (late luteal against
   follicular): heart rate 60.47 - 56.56 = **+3.91 bpm, exactly right**; wrist skin
   temperature 34.32 - 33.87 = **+0.45 C**, not 0.44; respiratory rate 17.04 - 16.57 =
   **+0.47 breaths/min**, not 0.60.

2. **`constants.py`, `EXERCISE_EFFECT_BPM`.** `{"0-2h": 4.14, "2-4h": 2.91, "4-6h": 1.58}`
   could not be verified: Leota et al. 2025 is paywalled on every route tried, and the
   per-band table is not in any open summary. The study's identity, its cohort of 14,689
   and 4,084,354 person-nights, and the direction of the effect all check out exactly. The
   three bpm values do not, and the paper's own summary states that "exercise bouts ending
   >=4 hours before sleep onset are not associated with changes in sleep", which sits
   awkwardly beside a 1.58 bpm entry for the 4 to 6 hour band.

**What I think is wrong:** for the luteal row, only the citation prose. Neither wrist skin
temperature nor respiratory rate is ingested by this system and neither figure enters any
computation, so this is a citation-accuracy defect and not a clinical one. For the exercise
table, possibly nothing: the quoted sentence is about sleep measures and the table entry is
about nocturnal heart rate, and the paper reports both.

**RESOLVED.** The user granted a narrow exception to the read-only rule: correct a figure
only where the published source can be quoted contradicting it, and record every change.
Both were corrected and are in `docs/KNOWLEDGE-CHANGELOG.md` with the quoted source
sentence beside the old and new value. The luteal figures are now +0.45 and +0.47.
`EXERCISE_EFFECT_BPM` is now `{"0-2h": 2.91, "2-4h": 1.87, "4-6h": 1.58}` with the paper's
own table reproduced in the comment above it.


## corpus — RESOLVED. The consumer health layer of the corpus did not exist

**What I tried:** built the retrievable corpus from the sources `sources.yaml` names.

**What happened:** three of the four layers can be built from material already in this
repository. Layer 1, MedlinePlus, cannot: it is a 29 MB external download that has never
been fetched, and layer 2 in the sense `sources.yaml` means it, StatPearls, likewise.

What exists instead is 33 documents: the measurement and detection method drawn from
`constants.py`, the escalation rules from `red_flags.yaml`, the twelve confounders from
`causes.yaml`, and what each question's answer implies from `probes.yaml`.

**What I think is wrong:** nothing, but the consequence is real and should be understood
rather than discovered. The agent can cite why a night was flagged, what else could explain
it, what an answer implies, and the rule behind any escalation. It cannot cite general
information about a condition, because this repository holds none. Writing that text from
the model's own knowledge is the one line this project must not cross, so it was not
crossed.

**RESOLVED 4 September 2026.** MedlinePlus was fetched. Snapshot 2026-09-03, 1,013 English
topics of the 2,033 in the release, the rest Spanish or summaries short enough to be a
pointer rather than information. The snapshot date, URL and SHA-256 are recorded in
`data/knowledge/corpus-sources.json`; the release itself is not committed, because it is a
thousand topics this project does not own under an attribution-only licence.

The URL `sources.yaml` recorded was a 404 and appears never to have existed. It named an
undated `mplus_topics_compressed.zip`; MedlinePlus publishes dated snapshots, Tuesday to
Saturday. `wha.retrieve.medlineplus` now resolves the newest one from the index page at
fetch time and raises rather than guessing when the scheme changes. `wha data fetch corpus`
previously returned "Corpus target verified" and fetched nothing; it now really fetches.

The index went from 133 chunks to 1,852. The authored escalation rules still surface in the
top six for "chest pain", "I fainted" and "my chest hurts and I feel sick", asserted by
`test_the_authored_safety_rules_are_not_swamped_by_a_thousand_topics`. Embeddings are
cached to disk: 343s cold, 3.0s warm.

**STILL OPEN, and narrower than the original blocker:** layer 2 in the sense `sources.yaml`
means it, StatPearls, has never been fetched. What the corpus calls layer 2 is three
passages generated from `constants.py` describing how this system measures the person. And
the Singapore care-pathway layer exists only as the wording already in `red_flags.yaml`,
nine passages, not the curated set `sources.yaml` describes (polyclinic against GP against
A&E against 995, plus national dengue guidance). Neither is broken. Both are smaller than
the design says they are.


## demo-order — RESOLVED. A frozen scenario meant different things depending on run order

**What I tried:** ran all eleven scenarios back to back to check for regressions after the
agentic-flow work, then ran the failures individually.

**What happened:** back to back, 5 of 11 passed. Individually, 10 of 11. The failures were
all the same shape: `asks_at_least: expected 1, got 0`, and a disposition of `None` or the
wrong value that follows from never asking.

**What I think is wrong:** nothing in the budget, which is correct. `count_interruptions_since`
counts across every subject because this is a single-user application, one person and one
phone. But `wha demo run` shares one database across scenarios and creates a subject per
scenario, so the weekly allowance of two became a global two questions across all eleven.
The first two scenarios spent it and the remaining nine silently asked nothing.

This nearly fooled me twice. The first time my own pass/fail count was wrong, because the
`[FAIL]` lines are indented and my anchored grep matched none of them, and I briefly
believed the suite had improved to 11 of 11.

**Fixed:** the default demo database is deleted at the start of each run, so a frozen
scenario means the same thing whatever ran before it. A database named with `--db` is left
alone. Two tests cover both halves.

**What I need:** nothing.


## conversation — the uncited label depends on the model classifying its own sentences

**What I tried:** drove the conversation through the Telegram path with the live model,
answering a chest pain presentation across two turns.

**What happened:** on one turn the model correctly put "the pain being the same when you
press on it is consistent with a muscle strain" into `uncited_notes`, where the interface
shows it under an amber "Not from a cited source" heading. On the next turn, with the same
prompt, it wrote "that's reassuring" and "which suggests it might be muscular" directly into
the reply, where they were shown with no warning at all.

**What I think is wrong:** the split between grounded and uncited is asked for in the
prompt and cannot be enforced in code, because deciding whether a sentence is a clinical
claim is the same judgement the model is making. What IS enforced deterministically is
narrower: the red-flag floor over the person's words, the never-say phrase list, and the
rule that urgency can rise and never fall. Those hold regardless of what the model writes.

The consequence is that the amber warning is a floor on labelling, not a ceiling on
unlabelled model content. Draelos et al. 2025 (arXiv:2507.18905) measured 5 to 13 percent
of unguarded frontier-model answers to patient questions as outright unsafe, so this
matters.

**What I need:** a decision between three options, none of which I should take alone.
Adding a second model pass that classifies each sentence of the reply and moves clinical
ones to the uncited list, which doubles the cost per turn and is still a model judgement.
Restricting the reply to sentences that are either cited or drawn from a fixed set of
templates, which would make the conversation much less useful. Or accepting it as
disclosed, which is what is in place now.

Separately: "that's reassuring" is not in `never_say`, which covers "you are fine",
"nothing to worry about" and similar.

**DECIDED 5 September 2026: do not add it.** The reason for deferring was that this is a
wording judgement about a human-authored safety list. That list was not human-authored, so
the deferral had no basis. On the merits: the phrase is not an absolute reassurance like the
others on that list, in the real transcript it was attached to a genuine clinical observation
(pain reproducible on palpation, which is genuinely reassuring for a cardiac cause), and
banning it only makes the model write "that's a good sign" instead. Phrase banning cannot fix
an inference that went unlabelled. That is plan item 17.


## corpus - RESOLVED 5 September 2026. Checked, and it fails

**Resolved by doing it.** A real message was sent. The reply ends `Sources: Fever` for a
MedlinePlus passage, naming neither MedlinePlus nor the National Library of Medicine, under
an attribution-only licence. `format_for_telegram` does not import
`wha.ui.components.citations.source_label`, which exists for exactly this. Now plan item 12.
The original text follows.

## corpus (original) - the Telegram side has never been checked with a MedlinePlus citation

**What I tried:** verified the new consumer health layer by driving the dashboard as an
ordinary person: answered the pending Marburg question, then asked "what is
costochondritis?".

**What happened:** it worked, and it exposed a real defect. The answer came from MedlinePlus,
the two sentences from the model's own knowledge were flagged amber, and the same-day
urgency the Marburg rule had already set was held. But the citation rendered as a bold
title and an identifier and nothing else, which is not attribution under an
attribution-only licence, and it made general background about a condition look identical
to a safety rule about this person. `wha.ui.components.citations` now names the source in
words in all three places a citation is drawn on the dashboard.

**What I think is wrong:** the Telegram path renders citations through different code and
has not been checked at all since the layer was added. There is no evidence it names the
source. Given that fixing the dashboard rendering broke an import on the Today page while
ruff and 546 tests stayed green, "it probably works" is worth very little here.

**What I need:** someone to send a general health question over Telegram and read what
comes back, the same way the dashboard was checked. `docs/RUNBOOK-SIMULATION.md` has the
setup.


## cohort — the decision on public wearable datasets is mine to make and is not made

**What I tried:** nothing yet. The user explicitly delegated this: "Do not ask me about
external data. If you think we need them for accuracy then fetch them, if not then leave
them. Plan your best decision."

**What happened:** `data/datasets/stanford` and `pmdata` are still empty and
`cohort_labels.yaml` was never authored, so detection accuracy is honestly reported as
"not evaluated" rather than given a number. Every judgement this system makes about the
person is made against their own baseline only, and has never been checked against anyone
else's data.

**What I think is wrong:** the absence itself is defensible for a single-user tool, and it
is disclosed. What is not defensible is leaving a delegated decision unmade and unwritten.

**What I need:** nothing from a human. The next session should decide, write the reason
down whichever way it goes, and either fetch the data or record why it is not worth it.



## knowledge - the clinical tables were generated by a language model

**What I tried:** a full evidence review of every number in `data/knowledge/`, on 4 and 5
September 2026.

**What happened:** the owner confirmed that these files were produced by Gemini, not written
by a person. Every file in the directory carries a line like "READ ONLY. Authored by a human",
and `data/knowledge/README.md` justifies the directory's existence with:

> "A language model asked to produce hundreds of cited conditional probabilities will produce
> hundreds of plausible fabrications... That is why these files are authored and frozen rather
> than generated."

Counted what has no source: 45 temporal profile weights across 10 of the 12 causes, 10 of the
12 between-person spreads, 64 answer likelihoods, 9 interruption costs, 6 tier B persistence
thresholds and 4 extreme heart rate thresholds. About 140 numbers. The claim also appears in
fourteen places outside `data/knowledge/`, including `README.md` and, rendered on screen, the
Audit page.

**What I think is wrong:** the safety argument of the project is one sentence, that clinical
content comes from a human-curated cited table and never from a model. That sentence is false.
Every figure that does carry a citation was checked against its paper and almost all of them
hold, so the problem is the uncited numbers, not the cited ones.

**What I need:** nothing. This is plan item 1, the owner has decided the approach (delete the
claims, do not replace them with a statement that an AI wrote them, let each number's own
provenance field carry the truth), and permission to edit `data/knowledge/` has been granted
and recorded in `STATUS.md`.


## contract - `docs/CONTRACTS.md` describes a baseline scale the code no longer computes

**What I tried:** item 7 of `history/review-2026-09/REFINEMENT-PLAN.md`, correcting what the band's width
shrinks toward.

**What happened:** `compute_baseline` now shrinks `scale_bpm` toward a new
`WITHIN_PERSON_SCALE_PRIOR_BPM = 3.71` instead of `POP_PRIOR_RHR_SD_BPM = 8.64`. Line 149
of `docs/CONTRACTS.md` still reads:

> `scale` is unchanged: it shrinks the same way from `POP_PRIOR_RHR_SD_BPM` toward a
> scaled MAD, floored at `BASELINE_SCALE_FLOOR_BPM`.

**What I think is wrong:** nothing in the code. 8.64 is Bloomfield's spread across 525
different adults, a between-person quantity. `scale_bpm` sets the width of the band around
one person's own median and is the divisor of `robust_z`, which is a within-person
quantity, and the unit the two extreme heart rate rules are written in. Using one for the
other is the same category error the contract itself was amended on 3 September to fix on
the centre. The replacement is measured, not assumed: 3.71 bpm is the median scaled MAD of
the archive, reproducible with `experiments/detection/cohort/band_width.py`, and the
full working with what it changes is in `docs/KNOWLEDGE-CHANGELOG.md`.

**What I need:** a one-line amendment to `docs/CONTRACTS.md`, which is read-only to me. The
sentence should become: `scale` shrinks the same way from `WITHIN_PERSON_SCALE_PRIOR_BPM`
toward a scaled MAD, floored at `BASELINE_SCALE_FLOOR_BPM`. Until then the contract and the
code disagree on one line, and the code is the one with the measurement behind it.


## contract - `docs/CONTRACTS.md` lists five constants for a subsystem that was removed

**What I tried:** item 22 of `history/review-2026-09/REFINEMENT-PLAN.md`, deleting the Chronos forecast.

**What happened:** `FORECAST_MODEL`, `FORECAST_MIN_NIGHTS`, `FORECAST_Q_LO`,
`FORECAST_Q_HI` and `FORECAST_HALF_WIDTH_FLOOR_BPM` are gone from `src/wha/constants.py`
along with `src/wha/detect/forecast.py`. `docs/CONTRACTS.md` still lists all five.

**What I think is wrong:** nothing in the code. The forecast was removed on a measurement
rather than a preference. Over 7,295 nights of the Mishra 2020 cohort it separates illness
nights from ordinary ones WORSE than the plain baseline residual the detector already
computes, on our own data. Across 30 labelled
infections it caught one the detector missed at the most generous threshold and none at
tighter ones. Reproduce with `uv run python experiments/detection/cohort/chronos.py`.

Keeping the five constants as dead names purely to satisfy a list would be the exact
defect this codebase keeps producing: something defined, referenced, and never reached.
`tests/unit/test_contracts.py` names them in `REMOVED_FROM_THE_CODE` and asserts they stay
gone, so the disagreement is enumerated rather than hidden.

**What I need:** the five entries deleted from `docs/CONTRACTS.md`, which is read-only to
me, along with the `forecast_*` fields on the `Detection` model if you want the contract to
match. The `forecast_status` COLUMN is deliberately kept, set to `NOT_RUN`, so databases
written before this still open and old rows still read.

## grounding - a cited sentence can still misdescribe the passage it cites

**What I tried:** driving the dashboard as a person, 5 September 2026. Typed "Why was last
night flagged, and what is my baseline?" into the Today page.

**What happened:** retrieval was correct. It returned exactly the two passages that answer
the question, `method_personal_baseline#c0` and `method_detection_thresholds#c0`, which say
"the person's own **median** sleeping resting heart rate" and "called elevated ... at least
3 bpm ... called RED at 4 bpm ... An investigation opens only when 2 consecutive nights are
RED". The reply shown to me said:

> "Your baseline is your own **average** resting heart rate during sleep, calculated after
> seven nights of data. Last night was **flagged** if your resting heart rate was at least
> **3 bpm** above that baseline."

The baseline is a median, not an average. 3 bpm is elevated, not flagged; flagging needs two
consecutive nights at 4. Both sentences were reported as grounded and cited, with no amber
marker, because the span the model quoted really is in the passage.

**What I think is wrong:** nothing in the code, and this is why it is recorded rather than
fixed. `enforce_grounding` verifies `claim.evidence_span` against the passages. It never
compares `claim.text` to them, and it cannot: "does this sentence follow from that
paragraph" is exactly the judgement the check exists to avoid asking a model to make.

Reproduced as a unit test rather than described:
`tests/unit/retrieve/test_grounding.py::test_grounding_checks_the_quoted_span_and_not_the_sentence_around_it`
shows the limit case passing, a sentence reading "A single night at 3 bpm above baseline
opens an investigation" while quoting the span "An investigation opens only when 2
consecutive nights are RED".

**What I did instead of fixing it.** The repository described this mechanism as "everything
the agent asserts must be grounded in a cited passage", and `docs/ARCHITECTURE.md` said the
check "cannot be argued with" and "This works". That overstates it. Every statement of it is
now written to what it actually guarantees, in `CLAUDE.md`, `AGENTS.md`, `README.md` and
`docs/ARCHITECTURE.md` Part 14, **and on the dashboard**, where the citation panel now says
the passage is the thing to believe where the two differ. A limitation on screen and not
only in a file is what the standing rule asks for.

**What I need:** a decision on whether to spend a second model call on entailment. I have
not done it, because it puts a model in charge of grading a model, and every other check in
this system is decidable by code. The alternative worth considering is answering "how does
this system work" questions from the method passages verbatim rather than letting them be
paraphrased at all, since those are the questions where the paraphrase has no upside.

## contract - two models carry fields `docs/CONTRACTS.md` does not list

**What I tried:** items 13 and 33 of `history/review-2026-09/REFINEMENT-PLAN.md`, both of which require a
number to reach the screen that the contract's version of the model cannot carry.

**What happened:** two frozen models gained a field.

`NightRow` gained `rhr_window_source: str = "clock"`. Today and History both state, in
words, whether a night was measured over recorded sleep or over the midnight-to-07:00
fallback. The flag lived on `NightlyFeatures` and not on `NightRow`, and both pages read it
through `getattr(n, "rhr_window_source", "clock")`, so the default always won and both
asserted "because no sleep was recorded" on all 72 nights, including the 44 where sleep was
recorded.

`DifferentialItem` gained `moved: float = 0.0`, how far this episode's evidence moved the
cause. The panel is titled and ordered by movement and drew bars of the final probability,
so bar length meant something different from the ordering. Carrying the number is what lets
the chart draw the thing the panel claims to show.

**What I think is wrong:** nothing in the code, and the precedent is already set in this
repository. The contract's `NightRow` also omits the four `forecast_*` fields that the code
has carried since before this work began, so a contract-frozen model gaining a presentation
field is a thing that has happened here before and was not recorded. It is recorded now.

Neither field changes a decision. Both exist so a screen can state a fact it was already
stating wrongly.

**What I need:** two additions to `docs/CONTRACTS.md`, which is read-only to me:
`rhr_window_source: str` on `NightRow` and `moved: float` on `DifferentialItem`. Until then
the contract and the code disagree on two lines, and the code is the side a person is
looking at.

## policy - a night the watch cannot vouch for still concludes LIKELY_ILLNESS

**What I tried:** item 24 of `history/review-2026-09/REFINEMENT-PLAN.md`, whose check is "run the simulation
with a poor coverage night, the outcome says the night could not be judged".

**What happened:** it cannot pass, and the gate written to make it pass could never fire.

`determine_disposition` required `sensor_artifact` to be the top cause at 0.50 or more AND
`p_illness` below the 0.10 treatment threshold. Those are mutually exclusive under this
belief model: the same large residual that pushes sensor_artifact up also pushes p_illness
up. Measured over 20 combinations of coverage 30 to 239 minutes and residual 3.2 to 10.0
bpm, it fired in none of them.

```
coverage 30, residual  4.0 -> sensor 0.259, p_illness 0.083 -> LIKELY_BENIGN
coverage 30, residual  6.0 -> sensor 0.512, p_illness 0.118 -> LIKELY_ILLNESS
coverage 30, residual 10.0 -> sensor 0.817, p_illness 0.138 -> LIKELY_ILLNESS
```

**What I think is wrong:** not the code, and not the belief model. The gate asked a belief
question that the belief model answers in the opposite direction to the one it needed. It is
deleted rather than retuned, because moving 0.50 or 0.10 to make a feature fire is choosing
a clinical threshold to satisfy a feature.

**What is left unfixed, and it is real.** At coverage 30 and residual 10.0 the system
concludes LIKELY_ILLNESS on a night whose own leading explanation, at 0.817, is that the
watch misread it. The differential shows sensor_artifact at the top and the episode panel
marks it, so the information is on screen, but the headline says "possibly coming down with
something" about a reading the model does not trust.

**What I need:** a decision I do not think I can make from evidence. Either

- a stated coverage figure below which a night is reported as unjudgeable regardless of
  belief, which is a data-quality threshold and would need a source or an explicit
  UNEVIDENCED label; or
- a change to the outcome TEXT rather than the disposition, so a sensor-dominated night
  keeps its urgency and gains a sentence saying the reading is doubtful. This is the one I
  would choose, because it cannot talk an escalation down, but the disposition set and the
  outcome model are both frozen by `docs/CONTRACTS.md`.

## corpus - RESOLVED 5 September 2026. The Telegram side names the source

**The blocker asked for:** "someone to send a general health question over Telegram and read
what comes back, the same way the dashboard was checked."

**Done, both halves.**

A real message was sent through `converse_over_telegram`, the same function the poller calls,
asking "What is costochondritis?". The answer came from the model's own knowledge and arrived
carrying its amber marker, which is the other half of the promise working on the phone:

```
Not from a cited source (the AI's own general knowledge, worth checking):
Costochondritis is inflammation where your ribs meet your breastbone...
```

That run retrieved no MedlinePlus passage, so it did not exercise the attribution path. Driving
the formatter with one directly gives:

```
Sources: Fever (MedlinePlus, National Library of Medicine)

Passages from MedlinePlus come from the National Library of Medicine and are used with
attribution. They are general information about a condition, not about you, and say nothing
about your own readings.
```

The source is named in words, not as `Sources: Fever`, and the attribution note travels with it.
Two tests hold it there: `test_medlineplus_is_named_not_just_its_topic_title` and
`test_the_attribution_note_travels_with_external_text`.

**Why it was fixed rather than duplicated.** The labels were in `wha.ui.components.citations`,
which `wha.service.conversation` correctly refuses to import, so the phone had no way to reach
them. They are constants now and both surfaces read the same ones, which is why the dashboard and
the phone cannot drift apart on who wrote a passage.

## contract - RESOLVED 5 September 2026. All four disagreements closed, and twenty more found

**What changed:** the owner lifted the read-only rule on `docs/CONTRACTS.md`, on the grounds
that it was written by a language model rather than by them, so "only a human may amend it" was
protecting nothing.

**What the four recorded blockers were:** five `FORECAST_*` constants the contract listed and the
code did not have; a baseline scale line the code no longer computes; and two model fields the
code carried and the contract did not, `NightRow.rhr_window_source` and `DifferentialItem.moved`.
All four are now reconciled with the reasoning written inline.

**What checking the whole file found: twenty MORE, none of them recorded anywhere.**

| Area | Disagreements | Recorded before |
|---|---|---|
| Constants | 6 | 5 |
| Models | 7 | 2 |
| Schema | 11 | 0 |

The ones that matter:

- **`POLICY_COST_PER_INTERRUPT` read 0.30 here and 0.15 in the code.** It is the price of
  interrupting a person, it was moved on a measured frontier, and the document the source cites
  by name kept quoting the old figure.
- **Seven whole tables existed and were undescribed**, including `subject_profile`,
  `conversation_turns` and `triage_answers`, which hold the most sensitive rows in the database.
- `NightRow` carried four `forecast_*` fields for a subsystem that had been deleted.
- `Settings` and `SettingsPatch` were missing `llm_base_url`, which is required for two of the
  three providers.
- `EpisodeContext` was missing `has_recent_illness`, which the belief model reads.

**The connection worth writing down.** `delete_all_subject_data` held a hand-written list of
tables that was checked against this file. This file did not know `subject_profile` or
`episode_traces` existed, so the list missed them, so the delete hit a foreign key and rolled
back, so **"Delete everything" deleted nothing**. A stale contract was not a documentation
problem there; it was the direct cause of a data-rights failure.

**Why this cannot recur.** The old header said "never edit it to match the code", which sounds
strict and is in practice unenforceable: nobody was comparing the two, so the file just went
quietly wrong. Three tests in `tests/unit/test_contracts.py` now compare it to `wha.models`,
`schema.sql` and `constants.py` on every run. Checked against injected drift: removing a field,
a column and changing a constant each fail with the specific name.

**Nothing further needed from the user on this.**

## cohort - RESOLVED. The delegated decision was made, and the data answered it

**Supersedes the "cohort — the decision on public wearable datasets is mine to make" entry
above**, which still reads "detection accuracy is honestly reported as not evaluated". That has
not been true since 5 September 2026.

**The decision:** fetch them. The Mishra et al. 2020 cohort is a 378 MB public download with no
registration, and the symptom-onset labels are in the same paper's supplementary workbook on the
same date shift as the public files, so they join directly. `cohort_labels.yaml` never needed
authoring.

**What it produced** was the first evidence of any kind about how this detector behaves on
data from people other than the author. The figures are in `experiments/detection/`, behind
its disclaimer, and are deliberately not repeated here: they are an archive re-analysis, not
a trial.

It also answered three questions that were being argued from theory: the step filter does
nothing here, a personal threshold is worse than a fixed one at every matched alert rate, and the
neural forecaster separated illness worse than the plain residual and was deleted.

`data/datasets/stanford` and `pmdata` remain empty and nothing reads them. `wha data fetch
stanford` no longer pretends to fetch anything; it names `experiments/detection/cohort/fetch.py`, which does.

## contract - the pipeline models are not in it, and the drift test cannot see that

**6 September 2026.** The dashboard overhaul added five models to `wha.models`:
`PipelineStepDef`, `PipelineStepView`, `PipelineHeadline`, `NightPipeline` and
`PipelineNightRef`, plus the `StepLayer` and `StepStatus` enumerations. None of them appear in
`docs/CONTRACTS.md`, because that file is read-only.

**Why the drift test does not catch it.** `test_the_contract_lists_the_fields_the_models
_actually_have` iterates over the models the contract declares and compares each against the
code. A model the contract has never heard of is not in that iteration, so it passes. The test
catches a model that changed, not a model that was added.

**Consequence.** `docs/CONTRACTS.md` remains accurate about everything it describes and is now
incomplete. Anyone using it as the full list of models will miss the five above, and the same
gap will exist for any model added while the file stays read-only.

**What would resolve it.** A decision from the user either to lift the read-only rule on
`docs/CONTRACTS.md` so new models can be recorded in it, or to state in the file's own header
that it describes the models it lists rather than all of them. Both are the user's call, not a
code change. This is recorded rather than fixed.

## conversation - the model described the system's own verdict wrongly, live

**6 September 2026, found by using the chat on real data.** Asked "Why was last night
green?", the model replied:

> "The green color last night likely indicates good sleep quality based on your watch's
> measurements."

GREEN means the night's resting heart rate sat inside the person's own band. It is not a
statement about sleep quality, and sleep quality is not an input to it. The reply then asked
a reasonable follow-up question and carried a citation to
`evidence_probe_sleep_quality#c1`, so on screen it looked grounded.

**This is the open "a cited sentence can still misdescribe its source" entry, with a worse
edge than that entry records.** The existing entry is about a sentence misreading a retrieved
passage. This is the model misdescribing **the system it is part of**: the meaning of a level
this application computed deterministically and displays three screens away. The grounding
check cannot catch it, because the quoted span really is in the passage about sleep quality.

**What is already true and did not help.** The Today screen states the correct meaning of
GREEN directly above the chat. The record screen shows the arithmetic. The reply still said
something else, and a reader who trusts the chat over the card is misinformed by the same
page that has it right.

**Not fixed here, because the plausible fixes are all decisions rather than code:**

- Feed the night's own verdict and its meaning into the conversation prompt as fixed context,
  which makes the model less likely to invent one but does not prevent it.
- Refuse to answer questions about what a level means and answer them from the interface's
  own copy instead, which is deterministic and cannot be wrong, but makes the chat feel like
  it is dodging.
- Grade the reply against the system's own facts with a second model call, which is the
  model-grading-model path every other check here avoids.

Recorded rather than papered over. The user should decide which of those, if any, is worth
its cost.

## agent - an answered question can leave an episode parked with nothing to answer

**6 September 2026, found by answering a real question from a real phone.**

The user answered "I fee a bit dizzy" over Telegram at 13:53. The answer was recorded
correctly: `interactions.status = ANSWERED`, `free_text` set, and the episode released from
`AWAITING_USER` to `OPEN`. Every tick after that advanced `step_count` (4, 5, 6) and left the
episode back in `AWAITING_USER` with:

- **no pending interaction** anywhere, so nothing can be answered, in the dashboard or on the
  phone
- **no pending interrupt in the graph**, so the database and the agent disagree about what
  the episode is doing
- **no belief movement**: `p_illness` reads 0.178 at belief seq 1, 2 and 3, before and after
  the answer

Two contributing defects were found and fixed. Neither resolves this one.

1. `_resume_value` in `service/scheduler.py` marked any answer with no `answer_option_id` as
   `declined`, so typing a reply was delivered to the graph as a refusal to answer while the
   person's words rode along as a footnote. Tapping a button worked; typing did not. Fixed,
   with `tests/unit/service/test_resume_value.py`.
2. The Telegram receiver recorded a typed answer and sent nothing back, so the person got
   silence. Fixed, with tests in `tests/unit/notify/test_receiver.py`.

**What is still wrong.** `node_ask` writes its interaction with a deterministic id,
`int_{episode}_{probe}`, and on conflict updates only the wording:

```sql
ON CONFLICT(id) DO UPDATE SET question_text = ..., text_source = ..., options_json = ...
```

so re-asking a probe that has already been answered cannot produce a PENDING row. It then
sets `AWAITING_USER` and interrupts. The tick's `_advance_episode` loop finds the interrupt,
builds a resume value from the same already-answered row, resumes, and can re-enter the same
node, up to `max_steps` of 24 per tick. The episode ends each tick parked with no question.

**Why it should not have re-asked at all.** `node_decide` passes
`already_asked_probe_ids = get_answered_probe_ids(episode_id)`, which returns every probe with
an interactions row, and `select_action` skips those. Something is still selecting the probe
that was just answered. That is where the next session should start.

**Consequence.** An investigation can spin without progressing and without being answerable.
The 36-hour answer timeout cannot release it either, because that only expires rows in
PENDING or ASKED and there are none. `EPISODE_MAX_NIGHTS` would eventually close it.

**RESOLVED, 6 September 2026, and it was simpler than this entry assumed.**

The episode was never stuck asking. It had finished thinking. Once the answer went in, the
policy chose OBSERVE, which means wait for another night, and `route_after_decide` sends that
to END. `node_ask` had set `AWAITING_USER` before interrupting so the interface could surface
the question, and nothing set it back, so the row said "waiting for your answer" while the
graph was waiting for a night. Every later tick then invoked a graph with nothing left to run:
zero nodes executed, `step_count` incremented anyway, and the tick reported the episode as
advanced.

The two contributing defects above were real and are fixed. Neither caused this one, which
was proved by clearing the episode entirely, including its checkpoint, and reproducing the
same behaviour on a fresh investigation with every fix in place. Cheap to test, and it ruled
out the comfortable explanation that the corruption was to blame.

`step_episode` now releases a parked state the graph is no longer parked on: when the run
ends with no pending interrupt and no PENDING or ASKED interaction, an AWAITING state goes
back to OPEN. An episode that IS waiting on a person stays parked, which
`tests/unit/service/test_episode_state_release.py` asserts both ways.


## safety - dizziness is in none of the rules, and it needs a clinical decision

**6 September 2026, raised by the user, and the reasoning is theirs: "my dizziness kept
getting worse, nobody asked, and on the 10th I died".**

Two things were found by testing the phrases rather than reading the file.

**1. Dizziness is not in `red_flags.yaml` at all.** Not tier A, not tier B. Checked
directly:

```
False  []                 I feel a bit dizzy
False  []                 dizzy and short of breath
True   ['rf_syncope']     I fainted
```

Fainting escalates. Feeling faint does not, and neither does dizziness with breathlessness.
So the symptom the user actually reported passed through the deterministic floor untouched
and reached only the belief model, where it moved a probability rather than raising an
alarm.

**2. Phrase matching is exact, so ordinary wording escapes it.** "chest pain" escalates,
"my chest hurts" does not, and neither does "feels like an elephant is sitting on my chest",
which is the example the simulation runbook itself gives as a tier A phrase to test with.
Tier C, the model backstop, exists for this and is the only thing standing behind it.

**What was fixed without needing a clinical decision.** Escalation was once per
investigation, so a person already being escalated about who then got materially worse was
told nothing. It now repeats when the reading rises by a full robust deviation of that
person's own variation, and a repeat says it has got worse and asks how they are.
`ESCALATION_REPEAT_ROBUST_Z_RISE` is a judgement expressed in the system's own units, not a
clinical threshold, and is marked as such.

**What needs the user's decision, because `data/knowledge/` is under change control and a
clinical figure may only change against a quotable source.**

- Should dizziness or light-headedness be a tier B symptom, so that it escalates when it
  persists or co-occurs with another? It is common and usually benign, which is why a naive
  addition would make the system cry wolf, and that has its own harm.
- Should any symptom reported during an investigation force a follow-up when the readings
  worsen, regardless of what the information is worth? The value-of-asking arithmetic is
  about telling causes apart. It is not about noticing deterioration, and it was never
  meant to be.
- Should the phrase lists be matched more loosely, accepting more false alarms?

None of these can be answered from this repository's own numbers, and none should be
invented. **Recorded, disclosed, and awaiting a decision.**


## RESOLVED 7 September 2026: two of the three dizziness items, and how

The item above is kept unedited because it records what was true, and because the reasoning
in it is the user's. Two of its three open questions are now answered, and the third is
downgraded on evidence.

**"Should dizziness be a tier B symptom?" Answered: no, and it does not need to be.** The
question assumed the only two options were escalating on it or ignoring it. There was a
third. `red_flags.yaml` now has a `tracked:` tier: recorded over time, escalates on nothing.
Tracking asserts no clinical threshold, which is precisely why it is defensible where a
tier B `persist_nights` invented for dizziness would not have been. A tracked symptom keeps
an investigation from closing as "nothing points towards illness" while it is outstanding,
and gives the follow-up rule something to ask about. Neither is a claim about where anybody
should be treated.

**"Should a reported symptom force a follow-up regardless of what the information is worth?"
Answered: yes, and it is a rule rather than a number.** The diagnosis in the item above was
right and understated. EVSI scores a question by how much the answer moves the belief across
twelve causes, so once a cause is settled, asking again is worth nothing BY CONSTRUCTION:
the more confident the system became that somebody was ill, the less reason it had to speak
to them. `probe_symptoms` also has no severity and no trajectory in its answer space, so
"feverish or chills" is the identical token on night one and night five, and there was no
question in the system that meant "are you worse than yesterday".

The fix is `select_action` step 3b. It bypasses the EVSI score, the weekly interruption
budget and the rung gates, and it does not bypass a pending question or its own per-episode
cap. It is deliberately NOT a term inside the belief model: adding trajectory there would
mean writing likelihood rows no literature supplies.

**"Should phrase lists be looser?" Downgraded, on measurement.** Tier C rescues the case:

```
deterministic only : I have a fever and I cannot keep fluids down  -> no escalation
with tier C        : I have a fever and I cannot keep fluids down  -> same_day
```

It picked an arguably wrong flag id and it escalated, which is the direction that matters.
The gap is real and is no longer the most serious thing in this file. **Still open** and
still the user's call, because loosening the lists trades false alarms for coverage and this
repository has no measurement of that trade.


## MEASURED AND CLOSED 7 September 2026: sustained yellow nights

Raised as a possible gap: the detector flags two consecutive RED nights and nothing else, so
somebody at three and a half beats above their own normal for ten nights running has no
investigation opened, ever. `sweep.py` had compared "at least one RED" against "both RED"
and never scored a yellow-persistence arm, so the behaviour was an assumption rather than a
finding.

Measured with `experiments/detection/cohort/yellow_persistence.py` on 30 labelled cases, 76 controls and 738
person-weeks:

```
two consecutive RED (production today)   53.3%  16 cases  0.198 alerts/week
both RED or 3 raised nights              53.3%  16 cases  0.207   1.05x
both RED or 5 raised nights              53.3%  16 cases  0.200   1.01x
both RED or 7 raised nights              53.3%  16 cases  0.198   1.00x
```

**Zero additional cases at every run length**, for up to 5 percent more investigations on
healthy people. Every case a long yellow run would catch is already caught. Nothing changes,
and that is a finding rather than a shrug: the gap is real and closing it helps nobody. Do
not re-litigate from theory.


## OPEN: can the agent recognise a dengue warning sign nobody coded for it?

**Reserved by the user on 7 September 2026 as a deliberate test rather than a fix.**

Severe abdominal pain is a WHO and CDC dengue warning sign and appears nowhere in
`data/knowledge/`. It would be defensible in tier B. The user chose to leave it out and use
it to test whether the system and the agent can reason to it unaided, dengue being endemic
where this system is used.

**Prediction recorded before the test is run: it will fail.** `corpus.yaml` contains the
word "dengue" zero times, so `enforce_grounding`'s verbatim containment test makes a grounded
dengue claim impossible, and Tier C is handed only the tier A and tier B ids and can return
nothing else. The only route that survives is an uncited note, which the interface labels as
unsourced.

If that prediction holds, the decision it forces is whether this system should carry
Singapore-specific clinical content in its corpus at all. `sources.yaml` already describes
national dengue guidance as material that should be there, and records that a dengue cluster
feed was removed on 5 September. That is a scope decision and it is the user's.



## DECIDED 7 September 2026: no dengue content, no looser matching

Both were the user's calls and both are now made. Neither is a gap any more; each is an
accepted limitation, and each is disclosed on screen as one.

**No illness-specific content in the corpus. Decided: no.** The live test showed the agent
cannot name dengue and cannot warn about defervescence, and it will not be given the
material to. What it can still do, and did unprompted in that test, is escalate on a group
of symptoms and seek a red flag it was not told to seek: it asked about mucosal bleeding on
its own. That is the boundary this system now keeps: it can say a picture is worth seeing
somebody about, and it cannot say which illness it is or how that illness behaves.

Consequence accepted with it: **the same-day routing for a WHO dengue warning-sign picture
stays**, and may be under-triaged for that specific illness. That is a real cost of the
decision and is written here rather than smoothed over.

Disclosed at `safety.no_local_guidance`, shown under the verdict on **Today**, because a
limitation living only in a markdown file is not disclosed at all.

**Looser phrase matching. Decided: no.** The lists stay exact and Tier C stays the backstop.
Measured before deciding: Tier C rescued "I cannot keep any water down", a phrase the lists
miss, and escalated it same-day. Since 7 September a Tier C finding is also written to the
symptom timeline, so a symptom only the model spotted now persists and can raise urgency on
a later night instead of counting once and being forgotten.

Still disclosed, unchanged, at `safety.what_it_cannot_catch`: unusual wording can slip past
the rules.

**Nothing in this file is now waiting on the user.**
