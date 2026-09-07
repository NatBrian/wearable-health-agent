# Contributing

This file holds no rules of its own. It exists because GitHub links it from every pull
request and issue, so it is the first thing a new contributor is shown, and it should point
somewhere useful rather than repeat what is written better elsewhere.

**Read these two, in this order, before writing any code:**

1. **[README.md](README.md)**, what this project is and where everything lives. Three
   sections matter most before you start:
   - **"I want to do X. What do I read?"**, which routes you by goal.
   - **"Working on this at the same time as somebody else"**, the four files where parallel
     work collides, and where to start for each of the big workstreams.
   - **"Rules enforced by tests, not by convention"**, the things that will fail on you.
2. **[AGENTS.md](AGENTS.md)**, the rules. All of them, for every contributor, human or
   otherwise, in one file. If this file ever disagrees with it, `AGENTS.md` is right and
   this one needs correcting.

**This is a health project with no clinical validation.** Nothing you write may imply
otherwise. Every number in user-facing text must be a published figure with its citation, an
operating parameter of the code, or absent. See [DISCLAIMER.md](DISCLAIMER.md) and
`docs/DISCLOSURES.md`.

**Two habits this repository has learned the hard way**, both from `AGENTS.md`:

- **A green suite proves less than you would expect.** Every serious defect here was found
  by opening the dashboard and using it. Finish by driving the real interface.
- **If a rule matters, it is a test.** A correction that lives only in prose does not
  survive contact with the next person. Do not add a convention to a document without
  adding the check that holds it.
