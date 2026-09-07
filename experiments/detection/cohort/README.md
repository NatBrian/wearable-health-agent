# Detection accuracy on real labelled data

This is how the detection numbers in `RESULTS.md` were produced. Nothing here is part of
the product. It imports the product's own pure functions so that what is measured is what
the product would actually do on those nights.

The project's central claim is that an overnight resting heart rate deviation is worth
investigating. Until this was run, that claim had no evidence: `RESULTS.md` said
detection accuracy was "not evaluated" because labelled data was missing. It was never
missing. Both inputs are public downloads and together they take under an hour.

## The data

**Wearable data.** Mishra et al. 2020, *Nature Biomedical Engineering* 4:1208-1220,
"Pre-symptomatic detection of COVID-19 from smartwatch data". De-identified minute-level
Fitbit heart rate, step and sleep records for 120 participants. 378 MB, no registration.

**Labels.** The same paper's Supplementary Data 1, Supplementary Table 3, which lists each
participant's symptom onset, COVID-19 diagnosis and recovery dates.

Both files carry the **same date shift** ("Dates have been shifted to obscure PHI"), so
they join on participant id without any realignment. That is the fact that makes this work,
and it is why the labels looked unavailable for so long: the shifted dates in the
spreadsheet look like nonsense until you notice the wearable files are shifted to match.

Neither file is committed. `data/cohort/` is gitignored, like everything else under
`data/` that is not a knowledge table.

## Running it

```bash
uv run python experiments/detection/cohort/fetch.py        # about 380 MB, a few minutes
uv run python experiments/detection/cohort/labels.py       # writes data/cohort/labels.json
uv run python experiments/detection/cohort/evaluate.py     # about 20 minutes, writes cohort_results.json
uv run python experiments/detection/cohort/report.py       # prints the tables in RESULTS.md
```

`evaluate.py` is the slow one. It replays the product's baseline and detector night by
night for every participant, which is 8,508 nights of arithmetic plus the sleep window
resolution.

## What the comparison is

Three detectors are scored on the same nights.

| | What it is |
|---|---|
| **This system** | `compute_baseline` and `compute_detection_for_features`, imported from `src/wha`, replayed night by night with a 28 night trailing history |
| **Published NightSignal** | Alavi et al. 2022, transcribed from the authors' own implementation: nightly **mean** of zero-step minutes between 00:00 and 06:59, expanding streaming median baseline, red alert on two consecutive nights at baseline + 4 |
| **Random, rate matched** | alerts on the same **number** of runs as this system, placed uniformly at random across that person's nights, averaged over 2,000 draws |

The third one is the important one. A wide detection window makes any detector look good,
so a sensitivity figure means nothing without the chance floor beside it. 83 percent against
a 73.5 percent floor is not a finding. 53 percent against 20 percent is.

`report.py` prints the chance column on every row. Do not quote a sensitivity from this
tool without it.
