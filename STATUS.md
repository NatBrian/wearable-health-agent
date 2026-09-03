# STATUS — read this first

**Last updated:** 3 September 2026
**Branch:** `feat/agentic-early-warning-system` (14 commits ahead of the implementation work, nothing pushed)

`HANDOFF.md` describes the job of writing this system from nothing. That job is done. This
file describes where things actually stand.

---

## Verify in one minute

```bash
uv run pytest                     # 378 passed, 1 skipped
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
| Tests | **378 passed, 1 skipped**, no ignore list |
| Lint and format | clean |
| `wha doctor` | no fail rows |
| Frozen scenarios | **10 of 11** |
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

## Open items for a human

Nine entries in `plan/BLOCKERS.md`. The ones that matter:

1. **`no-response-timeout` fixture amplitude** — needs roughly 4.8 bpm to produce the RED
   night it assumes, or re-authoring. Read-only to the agent.
2. **Blood oxygen has no likelihood** in `causes.yaml`, so it is captured and shown but
   cannot move the belief. Adding one is a clinical judgement. Note the readings are sparse
   (five across seven days) and noisy (an 80 percent sixty-six seconds before a 92).
3. **Cohort datasets absent.** `data/datasets/stanford` and `pmdata` are empty and
   `cohort_labels.yaml` was never authored, so detection accuracy is honestly reported as
   "not evaluated" rather than given a number.
4. **`git stash@{0}`** holds the reverted SpO2/respiratory/skin-temperature work. Now
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
| The original rules and constraints | `HANDOFF.md` |
| The frozen contract | `plan/02-contracts.md` |
