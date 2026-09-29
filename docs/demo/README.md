# The demo film

A recorded walkthrough of the whole system, for a portfolio and for a course submission.
Chaptered, captioned, no narration.

| File | What it is |
|---|---|
| `wha-demo.mp4` | The film |
| `chapters.txt` | Chapter timestamps, for a video description |
| `captions.srt` | Every caption with its timing, readable before it is burned in |
| `cards/` | The full frame cards, rendered from `script.yaml` |
| `footage/` | The live segments, recorded from the Vite dashboard |
| `telegram/` | Real messages this build sent to a real phone |
| `preflight/` | Frames from the resolution check, kept so the next person can see what passed |

The finished database is committed too, at `data/demo_film.sqlite`. It is **not**
reproducible: rebuilding it costs model calls and the agent would word its replies
differently, so the timeline you see is the one the film was cut from and cannot be
recreated exactly. The per-day snapshots the build wrote to `data/demo-snapshots/` were about 300 MB, were
never committed, and were deleted on 7 September. They are only needed to re-film a single
day, and `build.py` writes them again if you do.

**Everything here is generated.** Nothing is hand edited, so a wording change is an edit to
one file and a re-run, not a re-shoot.

## Where the words live

`tools/demo_film/script.yaml` holds every caption and every card, and
`tests/unit/test_demo_film_script.py` enforces its rules: no em-dashes, captions short
enough to read at speed, and nothing that tells the viewer to discount what they are
watching. Limitations get three whole chapters of their own, with the measurements behind
them. Said once with evidence is disclosure; said constantly in passing is noise.

## Just looking at it

The finished timeline is committed, so a fresh checkout can open it without rebuilding
anything and without spending a single model call:

```bash
uv run python tools/demo_film/serve_demo.py
```

In a second terminal, run the Vite dashboard:

```bash
cd frontend
npm run dev
```

Then open <http://127.0.0.1:8443>. Every night from 4 August to 23 September 2026 is there: the
quiet nights, the illness, the relapse, the three linked investigations, every question
asked and answered, the escalation, the human review decisions and the audit trail behind
all of it.

Use **Dashboard** for the original metric overview and its Today and History sections,
**Pipeline** for the selected-night trace, audit, conversation archive and explanations, and
**Settings** for the four configuration sections. The chat rail is available from each
destination. The timeline runs on subject `demo`; the real subject `me` is not used.

That script does three things `wha serve` on its own would not:

- **Shifts the clock**, computed from today's real date at launch, so the newest night in
  the database reads as "last night" however long from now you run it. Without that, Today
  shows nothing.
- **Serves a working copy**, so browsing, chatting or answering something cannot alter the
  committed timeline. Delete `data/demo_film_live.sqlite` and run it again to get back to
  exactly the state the film was cut from.
- **Runs without the scheduler**, so nothing ingests, advances or expires while you look.

## Rebuilding it

The timeline is already committed, so this records the dashboard without rebuilding its
simulated history. The outage scene uses one existing demo prompt and records the fixed-rule
fallback on a disposable copy. Start the demo API as described above, then run the Vite
dashboard in `frontend/`.

```bash
uv run python tools/demo_film/film_vite.py --offline-base-url http://127.0.0.1:8445 --output-dir docs/demo/footage-vite
uv run python tools/demo_film/cards.py
uv run python tools/demo_film/assemble.py --footage-dir docs/demo/footage-vite --output-dir docs/demo/review-vite
```

The recorder uses the normal dashboard for every chapter except the model-outage scene. For
that scene, run a second Vite instance on the offline URL above with
`VITE_API_URL=http://127.0.0.1:8502`. Its API must use a disposable copy of the demo database,
subject `demo`, `--no-scheduler`, `WHA_LLM_PROVIDER=openai_compatible`, an empty model key,
`WHA_NOTIFY_CHANNEL=none`, no Telegram credentials, and a model base URL on a verified closed
localhost port. The recorder requires this separate frontend URL so its one existing demo
prompt cannot reach the normal API; only the cloned database receives the fallback turn.
Review the render in `docs/demo/review-vite/` before copying it over the published film.

The assembler's output and footage directories can be changed with `--output-dir` and
`--footage-dir`. Its persistent `work/` subdirectory reuses encoded segments on the next
run.

`build.py` is the part worth understanding. It states what each day is predicted to do
BEFORE running it, and halts on the first day that does something else. A simulation you
watch and then describe afterwards always looks like it worked, because the description
gets written to fit what happened. This one halted five times, and four of those were
defects in the product rather than in the timeline. They are listed in
`archive/session-logs-2026-09/superpowers/plans/2026-09-07-demo-film.md`.

## What is real and what is simulated

The baseline is seven nights of the author's own watch data, 31 August to 6 September,
copied read-only out of subject `me`. Twenty seven prologue nights before them are
generated at the resting rate measured from those seven, purely so the baseline reaches the
MATURE rung, which needs twenty eight usable nights. The illness, from 7 to 23 September,
is simulated through the mock Health Connect bridge, which speaks the same HTTP protocol
the phone speaks, so every downstream stage runs unmodified.

Every word the agent says was generated live by the real model against the real corpus.
Nothing is cassetted, replayed or written by hand.

That sentence appears once in the film, on the closing card. It is not repeated in the
captions, because a recording that interrupts itself every ninety seconds to disclaim what
is on screen teaches the viewer to discount all of it.

## The clock

Seventeen nights pass in an afternoon because `WHA_CLOCK_OFFSET_DAYS` moves the whole
system's idea of today: night labels, audit rows, episode ticks, the review timeout and the
date handed to the model in its own prompt. It is unset in production, it lives in
`tools/demo_film/demo.env` and never in `.env`, `wha doctor` reports it as a warning
whenever it is not zero, and `build.py` clears it when it exits.
