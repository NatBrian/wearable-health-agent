# Removing claims this project cannot support

**Started 7 September 2026, at the user's instruction, after reviewing the demo film cards.**

## What was wrong

The repository presented three different kinds of number as though they were one kind of
evidence.

1. **Our own simulations, presented as measurements.** The card that opened the film said
   "The sensor alone cannot separate them. This was measured." The 40 cases behind it are
   synthetic, the ground truth is a label we injected ourselves, and an oracle answers every
   question truthfully. `EVALUATION.md` said all of that under "What these numbers do not
   show". The card kept the figures and dropped the caveats.

2. **Our own re-analysis of a public dataset, presented without that caveat.** The 46.7
   percent detection figure, the 37 percent, the 4.9 weeks. Real people's wearable data from
   Mishra et al. 2020, but our analysis of it: not peer reviewed, not a clinical trial, never
   validated against a clinical outcome.

3. **A real citation applied to a population it was not about.** The worst of the three, and
   the one nobody flagged. Film card 13 quoted "fourteen studies", "under three in a hundred"
   and "ninety in a hundred" from Downie et al. BMJ 2013. That review is about red flags for
   spinal fracture and malignancy in **low back pain**. It says nothing about fever, vomiting
   or infection. A number that looks properly sourced but describes a different condition is
   more misleading than an uncited one, because a reader has no reason to doubt it.

This is a health project. It has no clinical trial, no validation and no regulatory
standing, and nothing written in it may imply otherwise.

## The rule

Mechanical on purpose, so it can be checked rather than argued about. **Every number in
user-facing text must be one of:**

1. **From a published source**, with the citation adjacent, **and about a population the
   claim applies to**.
2. **An operating parameter of this system**: a threshold, a timeout, a count of steps. A
   fact about the code, not a claim about health.
3. **Removed**, and living in `experiments/`.

Anything from our own analysis is category 3 in user-facing text.

Category 1 keeps the Marburg Heart Score figures, the NHS England oxygen thresholds and
Bloomfield's population prior. Category 2 keeps `DETECT_RED_BPM = 4.0`, the coverage floor
and the twenty one pipeline steps. Category 3 is everything below.

## Inventory

Counted 7 September. Excludes `history/`, `research/`, `archive/` and `scratch/`, which are
finished work and describe nothing about the present.

| File | Hits | Action |
|---|---|---|
| `EVALUATION.md` | whole file | move to `experiments/detection/` |
| `docs/detection-results.json` | whole file | move to `experiments/detection/` |
| `docs/DESIGN-VS-NIGHTSIGNAL.md` | 6 | move to `experiments/detection/` |
| `tools/cohort/` | whole folder | move to `experiments/detection/` |
| `README.md` | 4 | strip, replace with what is not established |
| `STATUS.md` | 6 | strip |
| `BLOCKERS.md` | 7 | strip |
| `USER-GUIDE.md` | 1 | strip |
| `docs/ARCHITECTURE.md` | 9 | strip, keep the design reasoning |
| `docs/DESIGN-DATA-CHANNELS.md` | 1 | strip |
| `docs/DESIGN-SYMPTOM-TIMELINE.md` | 1 | strip |
| `docs/DISCLOSURES.md` | 1 | strip |
| `docs/KNOWLEDGE-CHANGELOG.md` | 2 | keep, it is a change log of provenance and the numbers are its subject |
| `src/wha/ui/components/how_it_works.py` | 1 | **dashboard copy, a real user reads this.** strip |
| `src/wha/constants.py` | 7 | comments only, point at `experiments/` |
| `src/wha/detect/detector.py` | 2 | comments only |
| `src/wha/retrieve/knowledge_docs.py` | 1 | comments only |
| `src/wha/eval/report.py` | 4 | generator: output must move under `experiments/` |
| `tools/demo_film/script.yaml` | 5 | rewrite the cards |
| `tools/demo_film/timeline.py` | 1 | comments only |

## The trap in this cleanup

`wha eval-report` **generates** `EVALUATION.md`. Moving the file alone means the next person
to run that command puts a performance claim back in the repository root, and the cleanup
silently undoes itself. The generator's output path moves too, and its output carries the
disclaimer in the file it writes. This is the defect shape this project keeps producing:
something exists, is referenced, and quietly reverts.

## What replaces the claims

Not silence, and not the opposite error of claiming nothing is known.

> How well this detects illness in real use **has not been established.** It has not been
> tested in a clinical setting, on patients, or against a clinical outcome.

Then the design reasons, stated without figures: a wrist sensor cannot tell an infection
from wine or a hard evening session, so the system asks rather than guesses; one symptom is
treated differently from several together; a heart rate that settles is not treated as
recovery.

## What was done

| # | Task | Outcome |
|---|---|---|
| 1 | Inventory | 20 live files carried a figure of ours. Table above |
| 2 | `experiments/` | Created, with a disclaimer at the top of the folder and of each sub-folder |
| 3 | Move the artefacts | `EVALUATION.md`, `detection-results.json`, the NightSignal comparison and `tools/cohort/` moved. **The generator's output path moved too**, or `wha eval-report` would have put the claim back at the root |
| 4 | Documents | README, STATUS, BLOCKERS, USER-GUIDE, ARCHITECTURE, DISCLOSURES, the design docs. Decisions kept, figures removed |
| 5 | The Downie transfer | The repository had **already** corrected this on 5 September: `safety/triage.py` says the review is about low back pain. The film card reintroduced it, and one code comment lacked the caveat |
| 6 | Screens and comments | The dashboard told a user the system interrupts once every 4.9 weeks "measured across 76 people". A **corpus passage** the agent can quote carried the same problem |
| 7 | The cards | Card 5 deleted. Cards 1, 7, 9, 12, 13, 19, 20, 21 rewritten. Cards 15 and 17 now name their sources on screen |
| 8 | Tests | Two: no card and no screen may quote a figure of ours, and the film must state that it has never been tested on a patient |
| 9 | Re-cut and verify | Cards re-rendered, film re-cut, suite run |

## What this cost, and what it bought

Act V of the film lost most of its content, and the detection headline that was the
project's most quotable result is gone from everything a viewer or reader meets.

What replaced it is a chapter that says the system has never been tested on a patient,
that nobody has been warned or treated or helped by it, and that how well it works is not
known. For a health project with no trial behind it, that is the stronger chapter, and it
is the only one that is true.

## The thing worth remembering

The repository had already made this exact mistake once and corrected it. On 5 September
somebody noticed that Downie et al. was being quoted without its population and fixed it in
`safety/triage.py` and the changelog. Two days later a film card quoted the same review's
odds as though they were about fever and vomiting.

A correction that lives only in the file where it was made does not survive contact with
somebody writing new prose elsewhere. That is why the rule is now a test rather than a
paragraph.
