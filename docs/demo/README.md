# The demo film

A recorded walkthrough of the whole system, for a portfolio and for a course submission.
Chaptered, captioned, no narration.

| File | What it is |
|---|---|
| `wha-demo.mp4` | The film |
| `chapters.txt` | Chapter timestamps, for a video description |
| `captions.srt` | Every caption with its timing, readable before it is burned in |
| `cards/` | The full frame cards, rendered from `script.yaml` |
| `footage/` | The live segments, recorded from the running dashboard |
| `telegram/` | Real messages this build sent to a real phone |
| `preflight/` | Frames from the resolution check, kept so the next person can see what passed |

**Everything here is generated.** Nothing is hand edited, so a wording change is an edit to
one file and a re-run, not a re-shoot.

## Where the words live

`tools/demo_film/script.yaml` holds every caption and every card, and
`tests/unit/test_demo_film_script.py` enforces its rules: no em-dashes, captions short
enough to read at speed, and nothing that tells the viewer to discount what they are
watching. Limitations get three whole chapters of their own, with the measurements behind
them. Said once with evidence is disclosure; said constantly in passing is noise.

## Rebuilding it

```bash
uv run python tools/demo_film/serve_watch.py            # terminal 1, the mock watch
uv run python tools/demo_film/build.py --stage seed     # terminal 2
uv run python tools/demo_film/build.py --stage story    # hits the real model
uv run python tools/demo_film/preflight.py              # then LOOK at the frames
uv run python tools/demo_film/film.py                   # record the live scenes
uv run python tools/demo_film/cards.py
uv run python tools/demo_film/assemble.py
```

`build.py` is the part worth understanding. It states what each day is predicted to do
BEFORE running it, and halts on the first day that does something else. A simulation you
watch and then describe afterwards always looks like it worked, because the description
gets written to fit what happened. This one halted five times, and four of those were
defects in the product rather than in the timeline. They are listed in
`docs/superpowers/plans/2026-09-07-demo-film.md`.

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
