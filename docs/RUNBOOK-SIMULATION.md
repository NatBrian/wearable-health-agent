# Running the system for real, then simulating the days after

This is the operator's guide for taking the system from a clean checkout to a live watch,
and then past the nights the watch actually recorded using a mock Health Connect bridge.

The mock bridge is not a shortcut around the system. It speaks the same HTTP protocol the
phone speaks, so `run_ingest` takes the **live** path, rows land with `source_kind="live"`,
and normalisation, nightly features, the baseline, detection, the belief model,
the policy, the agent graph and Telegram all run exactly as they do with the real device.

---

## Phase 1. A fresh start

```bash
uv sync
cp .env.example .env               # then fill it in; see the table below
uv run wha data fetch corpus       # REQUIRED, about 32 MB. Retrieval cannot run without it
uv run wha doctor
```

`doctor` creates `data/wha.sqlite` if it is missing. Expect `cohort miss` until you run
`experiments/detection/cohort/fetch.py`; detection accuracy is measured from that cohort and the figures are
published in `experiments/detection/detection-results.json`. No row should say `fail`.

`wha doctor --live` is the same check plus the probes that need the network and the phone,
in one report with one verdict. `wha check-live` is an alias for it.

The `.env` values that matter:

| Key | Why |
|---|---|
| `WHA_DB_PATH` | `data/wha.sqlite` |
| `WHA_SUBJECT` | `me` |
| `WHA_TIMEZONE` | `Asia/Singapore` |
| `WHA_LLM_*` | the live provider; `wha demo run` defaults to cassettes, everything else uses this |
| `WHA_BRIDGE_URL` | **the phone in Phase 2, the mock in Phase 4** |
| `WHA_TELEGRAM_*` | bot token and chat id; without both, the system falls back to `NullNotifier` and asks nobody |

## Phase 2. The real watch

Turn the phone hotspot on. `WHA_BRIDGE_URL` must be the Wi-Fi gateway address.

```bash
uv run wha doctor --live      # mandatory subsystems must all pass
uv run wha ingest              # pulls 30 days by default; the watch holds about a month
uv run wha nightly --range 2026-08-28:2026-09-03
uv run wha data capability    # what the device actually sends
```

Readings are taken over the sleep your watch recorded, not over a fixed clock window. See
`docs/DESIGN-SLEEP-WINDOW.md` for the evidence and the stated limitations, including naps
and sleep apnoea.

With only three nights the baseline sits at `COLD` or `PRIOR_DOMINATED`, and NOTHING CAN
BE FLAGGED at all: seven usable nights are needed before a night is compared against the
person's own median. That refusal is right, and it is worth seeing once before there is
enough history to hide it. A neural forecaster used to decline here too; it was deleted on
5 September 2026 after it scored worse than the plain residual it was meant to improve on.

`nightly` marks each night `history` or `watched`. Nights recorded before your first sync
are history: they build your baseline and can never raise an alert, so a first sync cannot
open an investigation into a night from before you owned the system.

## Phase 3. Start the system

```bash
uv run wha serve
```

Five background jobs start: a first-run catch up that fires immediately, ingest every 30
minutes, night scoring every 3 hours, an episode tick every 15 minutes, and Telegram
polling every 45 seconds. The dashboard is on <http://localhost:8501>.

Night scoring runs on an interval rather than at a fixed hour, because a night is measured
over the sleep the watch recorded and that is not finished at any particular clock time. A
night settles as soon as its sleep has synced, whether the person wakes at 07:00 or 13:00.

## Phase 4. The mock watch

Point the bridge at the local mock instead of the phone:

```bash
# .env
WHA_BRIDGE_URL=http://127.0.0.1:8788
WHA_BRIDGE_HOST=127.0.0.1
WHA_BRIDGE_PORT=8788
```

Terminal 1, left running:

```bash
uv run python tools/mock_watch.py serve
```

Terminal 2:

```bash
uv run python tools/mock_watch.py init --cursor 2026-09-03 --window 35
uv run python tools/mock_watch.py backfill
```

`init` sets the last night the watch has recorded. `backfill` processes the whole
on-device window at once, the way a first sync would; without it every night would be
scored against the population prior rather than a personal baseline. After it, the subject
has 35 nights and the baseline is `MATURE`.

Then advance one day at a time:

```bash
uv run python tools/mock_watch.py day --scenario healthy
uv run python tools/mock_watch.py day --scenario illness
uv run python tools/mock_watch.py day
uv run python tools/mock_watch.py status
```

Each `day` advances the cursor, ingests through the bridge, runs nightly for the new
night, and steps any open episode. When the policy judges a question worth the
interruption, your phone buzzes; answer in Telegram and the next tick resumes the graph
with your answer.

### Scenarios

| Scenario | Effect |
|---|---|
| `healthy` | nothing injected |
| `subclinical` | +4.6 bpm: elevated, never reaches RED, never flags. The system stays quiet. |
| `mild-illness` | +5.0 bpm: RED, then flags on the second night |
| `illness` | +5.4 bpm: RED, flagged, three RED nights, then recovery |
| `severe-illness` | +6.6 bpm: four RED nights |
| `alcohol`, `stress`, `exercise` | benign causes, deliberately too small to flag alone |
| `nonwear` | a night with no nocturnal coverage |

The illness amplitudes are measured, not chosen for effect. The generator rounds every
minute to a whole bpm, so an amplitude does not survive intact into the nightly RHR:
against a mature 61.35 bpm baseline, 4.6 moves RHR 61 → 65 for a 3.65 bpm residual, under
the 4.0 RED threshold. `flagged` additionally needs **two consecutive RED nights**, the published NightSignal
rule. It was "two elevated nights with a RED among them" until item 8 on 5 September 2026. The sweep behind these numbers is in `tools/mock_watch.py`.

To combine causes on one night, an elevation the agent has to explain away, schedule
them by date:

```bash
uv run python tools/mock_watch.py event --kind alcohol --date 2026-09-06
uv run python tools/mock_watch.py event --kind illness --date 2026-09-06 --amplitude 5.4
```

### Red flag

Red-flag escalation is driven by what you *say*, not by the data. Let an episode open,
wait for the question, and reply in Telegram with a Tier A phrase such as "feels like an
elephant is sitting on my chest". Escalation is deterministic and bypasses the belief and
policy nodes entirely.

## Known limitations of the simulation

Recorded in full in `docs/DISCLOSURES.md`:

- An **OBSERVE decision is never revisited.** Once the policy chooses to wait, the belief
  does not move again on later nights; the episode exits through the deterministic
  quiet-run or elapsed-nights close instead.
- ~~**Episode dates come from the wall clock**, so `closed_on` will read as today's real
  date while night dates run ahead. The `EPISODE_MAX_NIGHTS` close arm cannot fire under
  forward simulation.~~ **FIXED 7 September 2026.** `WHA_CLOCK_OFFSET_DAYS` shifts the
  whole system's idea of today, not just the night labels, so episode dates, audit rows,
  the review timeout and the date handed to the model in its own prompt all move together.
  Every close arm can fire. Unset in production, and `wha doctor` reports it as a warning
  when it is not. See `src/wha/clock.py`.
- The generator emits **four of the seven channels** the real watch sends. Blood oxygen,
  distance and calories are absent, so the dashboard shows fewer tiles than in Phase 2.
  Blood oxygen has no likelihood in `causes.yaml` and could not move the belief anyway.

## A second timeline, without disturbing this one

`tools/mock_watch.py` honours `WHA_MOCK_STATE`, so a second simulation can keep its own
cursor file instead of overwriting `data/sim_state.json`. The demo film uses this:

```bash
uv run python tools/demo_film/serve_watch.py    # its own state, its own database
uv run python tools/demo_film/build.py --stage seed
uv run python tools/demo_film/build.py --stage story
```

That harness is worth reading even if you never make a film, because it does one thing this
runbook does not: **it writes down what each day is predicted to do before running it, and
halts on the first day that does something else.** It halted five times, and four of those
were defects in the product rather than in the timeline. See
`archive/session-logs-2026-09/superpowers/plans/2026-09-07-demo-film.md`.

## Resetting

```bash
uv run python tools/mock_watch.py reset   # drops the cursor
rm data/wha.sqlite                        # drops all data; wha doctor recreates it
```
