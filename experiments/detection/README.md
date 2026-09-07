# Detection: our re-analysis of a public dataset

**Not a clinical trial. Not peer reviewed. Not validated against any clinical outcome.**

The data is real: the wearable release accompanying Mishra et al. 2020, Nature Biomedical
Engineering 4:1208-1220, with symptom onset dates from the same paper's supplementary data.
The analysis is ours, and it has been reviewed by nobody.

## What this can and cannot tell you

It can tell you how this detector behaves on that archive, against a chance floor, compared
against the published algorithm whose thresholds it borrows. That is a useful engineering
check and it is why the detector is built the way it is.

It cannot tell you that this system finds illness in real use. Specifically:

- **One cohort, one device, one illness.** Fitbit users enrolled in a COVID-19 study. Not a
  general population, and not any other infection.
- **Sensitivity is per PERSON, not per night**, and an alert anywhere in the window counts.
  That is the right question for an early-warning system and it is a looser one than
  per-night accuracy.
- **Retrospective.** Nobody was warned, nobody acted, and no outcome changed. There is no
  measurement here of whether an alert helps anyone.
- **The window is chosen by us.** A wide enough window makes any detector look good, which
  is why every result here is reported against a rate-matched random comparator, and why
  that comparator should be read first.

## Reproducing it

`fetch.py`, `labels.py`, `evaluate.py`, `report.py` and `sweep.py`, in that order. The
dataset is downloaded rather than committed.
