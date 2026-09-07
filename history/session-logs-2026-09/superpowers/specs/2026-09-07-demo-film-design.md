# The demo film: design

**Written 7 September 2026.** A recorded walkthrough of the whole system, for a portfolio
and for a course submission. Around 22 to 25 minutes, chaptered, captioned, no narration.

The audience is **not an engineer and not a clinician**. Every caption has to be readable by
somebody who has never heard of a resting heart rate baseline, while still being specific
enough that an examiner can tick a rubric line against it.

---

## 1. What this is, and what it is not

This is a film of the **real product**, driven through its real interface, over a timeline
that runs across twelve simulated days. Nothing on screen is mocked up, redrawn or faked.
The agent's replies are generated live by the real model against the real corpus.

It is **not** a screencast of somebody clicking around. Every chapter exists to make one
claim, and every claim is either shown happening or backed by a number this repo can
reproduce.

### The provenance rule

**Corrected 7 September after reading the database rather than the handover note.** Subject
`me` holds 34 night rows but only **seven usable nights**, 31 August to 6 September. The
watch was not worn before that, so the other 27 rows have no nocturnal coverage and were
never scored. Seven usable nights puts the baseline on the SHRINKING rung, and 28 are needed
for MATURE.

So the baseline is built the way the previous simulation built it: **27 generated prologue
nights from 4 to 30 August, at the resting rate measured from the real ones, then the seven
real nights**. That is 34 usable and a MATURE baseline. The twelve story nights come from the
mock Health Connect bridge, which speaks the same HTTP protocol the phone speaks, so every
downstream stage runs unmodified.

The film therefore does **not** say "34 real nights" anywhere. It says a month of nights, and
the closing card carries the precise sentence: seven nights of real watch data, the rest
generated at the resting rate measured from them, and the illness simulated.

That fact is stated **once**, on the closing card, as a plain sentence. It is not repeated in
captions during the film. A demo that interrupts itself every ninety seconds to disclaim
what the viewer is watching teaches them to discount it, which is the opposite of the goal,
and the honesty is not improved by the repetition. It stays in this spec, in the runbook, in
`wha doctor`, and on the closing card.

### Caption rules

- No em-dashes and no en-dashes, anywhere, including chapter cards and the closing card.
- No digits-as-jargon without a plain-language gloss. "3.71 bpm" alone means nothing; "about
  four beats a minute, which is roughly what one glass of wine does" means something.
- No hedging asides, no "this is only a simulation", no apologising for the product
  mid-sentence. Limitations get their own chapter, stated once, with evidence.
- Short lines. Two lines maximum on screen at once.

---

## 2. The timeline

Subject `demo`, in a **separate database file** `data/demo_film.sqlite`. The live `data/wha.sqlite`
is opened read-only exactly once, to copy the real nights out of subject `me`. Subject `me`
is never written to, and the parked `sim` episode from 7 September is untouched.

| Date | Reading | What happens | What the chapter proves |
|---|---|---|---|
| Aug 4 to Aug 30 | green | 27 generated prologue nights at the real resting rate, so the baseline reaches MATURE | Nothing can be judged until it knows you |
| Aug 31 to Sept 6 | green | the seven real nights, copied in as raw readings and scored by the real nightly job | The person is real |
| Sept 7 | green | nothing | |
| Sept 8 | elevated | hard training at 9pm | An explained elevation is not an alert |
| Sept 9 | **yellow** | alcohol | Yellow does not flag |
| Sept 10 | green | nothing | |
| Sept 11 | green | nothing | |
| Sept 12 | **RED** | first red night, no alert. The person volunteers "I feel a bit dizzy" through `wha tell` | One red night is not an alert. Dizziness is tracked, not flagged |
| Sept 13 | **RED** | second consecutive red, investigation opens, agent runs, asks one question, answered "fever and chills" | Perceive, reason, act. The value of asking, computed |
| Sept 14 | **RED** | person reports vomiting. Fever on the 13th plus vomiting on the 14th are two Tier B flags across nights, so the floor escalates to same-day care | The 7 September fix. This used to be silent |
| Sept 15 | **green** | person says they feel better. The investigation does **not** close, and a follow-up is asked anyway | A settled reading is evidence about the reading |
| Sept 16 | **RED** | fever returns into the same investigation | Memory across waits, and recurrence linking |
| Sept 17 | green | symptoms resolve, investigation closes **and says so** | A close that speaks |
| Sept 18 | green | person types a chest pain presentation into the chat | Marburg elicited, scored in code |

### Two deliberate changes from the first sketch

**Dizziness moved to the first red night, and is volunteered rather than answered.** On one
red night nothing is flagged, so there is no question to answer. Volunteering it exercises
`wha tell`, and it leaves an outstanding tracked symptom that is what blocks the false close
on the 15th. The two scenarios the user asked for become one thread rather than two.

**Stomach ache became vomiting.** `rf_persistent_vomiting` is a Tier B flag and stomach ache
is not, so only vomiting produces the cross-night escalation the chapter exists to show.

### The chest pain scene, and why it is not a Tier A stop

The first sketch had chest pain firing Tier A immediately. That is not what the system does,
and the thing it actually does is better. Per `docs/RESEARCH-AGENTIC-TRIAGE.md` section 4,
the agent elicits the five Marburg Heart Score items in conversation and a deterministic
function scores them. At 3 or more, urgent evaluation. The model elicits, the rule decides,
and the model can raise urgency but can never lower it.

The film shows the scored path, and a card states the exclusion: when the presentation is one
Marburg was never validated for, such as pain happening now with sweating or collapse, the
rule is **not allowed to run at all** and it is an unconditional emergency with no questions.

---

## 3. The clock

Twelve nights have to pass in one afternoon. `wha/clock.py` already centralises "what day is
it", but **43 sites in `src/wha` read the wall clock directly** for timestamps, so a shifted
date would reach the night labels and not the audit rows, the LLM prompt context or the
episode ticks.

42 of them call `datetime.now(UTC)`. The forty-third, `service/nightly.py:104`, calls
`datetime.now(ZoneInfo(tz))` and never mentions UTC, so the grep that found the other 42
walked straight past it. It is the function that resolves a default date range, which is to
say the one place where being a day out is least likely to be noticed and most likely to
matter.

**Design.** `clock.now_utc()` becomes the single source of the current instant, honouring
`WHA_CLOCK_OFFSET_DAYS`. Default is unset, which is exactly today's behaviour. All 43 call
sites route through it. A test then forbids `datetime.now(`, `date.today()` and
`datetime.today()` anywhere in `src/wha` outside `clock.py`, in the same style as the
existing wiring tests, so it cannot rot back.

**Blast radius control.** The offset is read from a separate `demo.env` that the build script
loads. It never goes in `.env`. `wha doctor` grows a row that reports the offset and marks it
`warn` when non-zero, so a shifted clock can never be mistaken for production.

This is the largest edit in the plan and it touches production code for a film. The
alternatives are worse: running the build over twelve real days is not happening, and
shifting only the database writes leaves the model being told the wrong date in its own
prompt, which would show on camera the moment the agent mentions a day.

---

## 4. Two passes, and why

**Pass one, the build.** Runs the twelve days through the real CLI against the real model.
Snapshots `data/demo_film.sqlite` after each day into `data/demo-snapshots/day-NN.sqlite`.

**Pass two, the camera.** Restores a snapshot per scene and drives the browser. Re-shooting a
scene costs no API calls and cannot produce a weaker answer than the take before it.

Nothing is ever cassetted or replayed through a fixture. Every word the agent says was
generated live, once, by the real model. The ad-hoc chat scenes (chapter 12's grounding
questions, chapter 17's chest pain conversation) run **live on camera**, because streaming
text is worth filming and chat calls are cheap.

Rebuilding the whole arc re-pays for the agent calls. That only happens if the timeline
itself changes.

---

## 5. Filming

**Resolution is settled before a single frame is shot.** 1920x1080 at a 2x device scale
factor. Pre-flight: screenshot all five screens, then look at them and check that Streamlit
is in wide mode, that the 21-step pipeline graph fits without scrolling, and that body text
survives the downscale to 1080p. If it is cramped, fix the viewport or the layout first.

Live browser motion for anything the product does. Authored full-frame cards for anything it
cannot show: the architecture diagram, the measured tables, the citations, the chapter
titles. The cards are rendered from a script file so a wording change is an edit, not a
re-shoot.

Telegram is filmed as stills captured through BrowserOS from the real bot chat, cut in at
three beats: the first question arriving, the same-day escalation, and an answer typed from
the phone.

---

## 6. The chapters

Five acts, 24 chapters. The full list with its rubric mapping is in the plan document,
`docs/superpowers/plans/2026-09-07-demo-film.md`, because it is the working checklist.

The three chapters this film is really for:

- **Chapter 9, the quiet band.** Asking is only worth it in the middle. Silent at a 2 percent
  chance of illness, asks at 8 percent, silent again at 30 percent, because by then the
  answer would not change what to do. This is the most counterintuitive true thing in the
  project and no other demo of this kind shows it.
- **Chapter 15, the investigation that will not close.** Green reading, person says they feel
  better, and it stays open, for three cited reasons.
- **Chapter 18, taking the AI away.** Point the system at a dead endpoint and the
  deterministic detector still flags, the fallback question still goes out, and the badge
  reads FALLBACK. A health system that survives its own AI failing is a stronger claim than
  anything the AI does.

---

## 7. Defects found while writing this spec

**One real, one imagined.** Recorded together because the imagined one is the more useful
lesson.

1. **Real. `README.md` promised an Audit Journal at `/Audit`.** No such route exists; the
   journal is a tab on The record. `EVALUATION.md` carried the same stale name, and that file
   is generated, so the fix had to go into `src/wha/eval/report.py` too or the next report
   run would have restored it. Fixed.
2. **Not real. This spec first claimed nothing verifies the audit hash chain.** It does.
   `verify_chain` in `db/audit_chain.py`, wrapped by `service/audit.py`, called by
   `api/app.py` on every audit request, rendered by `ui/pages/3_The_record.py`, and unit
   tested, with a considered case for an empty chain where claiming "intact" over zero rows
   would be a small lie. The claim came from a grep that searched `src/wha/audit/` and
   `cli.py` and never `src/wha/db/`. Withdrawn.

The second is worth keeping in writing. This project's stated recurring defect is code that
exists, is referenced, and is never reached, and looking for that shape makes it easy to
report an absence that is really an incomplete search. Verify the absence, not just the
silence.

---

## 8. Non-goals

- No narration or synthesised speech. Captions only.
- Prompt injection, permission scoping and data deletion are **stated on a card, not filmed**.
  They are straightforward, they photograph badly, and screen time spent on them is taken
  from the chapters that show something a viewer could not have guessed.
- No new product features for the film's benefit. The audit verification in section 7 is a
  fix to an existing promise, not a feature.
