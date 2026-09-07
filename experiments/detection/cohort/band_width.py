"""How wide should the band around your usual heart rate be, and whose wobble sets it?

The baseline has a CENTRE, your usual rate, and a SCALE, how much you normally wobble from
night to night. The centre became your own median once seven usable nights exist, on
evidence: the detection thresholds come from NightSignal, which measures deviations above a
per-individual streaming median with no population blending.

The scale did not. It is permanently `w x yours + (1 - w) x a stranger's`, and because the
trailing window caps n at 28 the weight caps at 0.8, so a fifth of an 8.64 bpm population
spread never washes out however long you wear the watch.

That matters because `robust_z` is residual divided by this scale, and `robust_z` is the
unit the two extreme heart rate safety rules are written in. Those rules fire at |z| > 6.
If the divisor is a fifth someone else's, the threshold does not mean what it says.

The refinement plan proposed making the scale personal at the same seven nights as the
centre. Before doing that, this measures what it would actually change: how wide the band
becomes, and how often the safety rules would fire, across 8,508 real nights.

Reads `data/cohort/cohort_results.json`, so run `evaluate.py` first. Baselines are rebuilt
from the per-night record, which preserves the `usable` flag, so `compute_baseline` filters
exactly as it did in the original run.
"""

from __future__ import annotations

import json
import statistics
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from wha.constants import (
    BASELINE_MIN_NIGHTS_PERSONAL,
    BASELINE_SCALE_FLOOR_BPM,
    BASELINE_WINDOW_NIGHTS,
    MAD_TO_SD_FACTOR,
)
from wha.detect.baseline import compute_baseline
from wha.models import NightlyFeatures

RESULTS = REPO / "data" / "cohort" / "cohort_results.json"
if not RESULTS.exists():
    raise SystemExit(f"{RESULTS} is missing. Run experiments/detection/cohort/evaluate.py first.")

rows = json.loads(RESULTS.read_text(encoding="utf-8"))

# The rule the two vitals rules in red_flags.yaml fire at.
EXTREME_Z = 6.0


def personal_scale(history: list[NightlyFeatures]) -> float:
    """What the scale would be with no borrowing at all, floor still applied."""
    usable = [n for n in history if n.usable and n.rhr_bpm is not None][-BASELINE_WINDOW_NIGHTS:]
    if not usable:
        return BASELINE_SCALE_FLOOR_BPM
    values = [float(n.rhr_bpm) for n in usable]
    median = statistics.median(values)
    mad = statistics.median([abs(v - median) for v in values])
    return max(MAD_TO_SD_FACTOR * mad, BASELINE_SCALE_FLOOR_BPM)


# The third option, and the one this file exists to test. 8.64 is Bloomfield's
# BETWEEN-PERSON spread: how much people differ from each other. The scale is trying to
# estimate a WITHIN-PERSON night-to-night spread: how much you differ from yourself. They
# are different quantities, and borrowing one for the other is the same category error the
# centre had, in the other direction. This is the measured within-person figure, printed
# in the first block below, fed back in as the prior.
WITHIN_PERSON_PRIOR = 3.71

shrunk_scales: list[float] = []
personal_scales: list[float] = []
within_scales: list[float] = []
raw_personal: list[float] = []
z_shrunk: list[float] = []
z_personal: list[float] = []
z_within: list[float] = []
mature_pairs: list[tuple[float, float, float]] = []

for row in rows:
    history: list[NightlyFeatures] = []
    for night in row["per_night"]:
        feature = NightlyFeatures(
            subject_id=row["pid"],
            night_date=date.fromisoformat(night["night"]),
            rhr_bpm=night["rhr"],
            coverage_minutes=300 if night["usable"] else 10,
            implausible_dropped=0,
            usable=night["usable"],
        )
        baseline = compute_baseline(history)
        if (
            night["usable"]
            and night["residual"] is not None
            and baseline.usable_nights >= BASELINE_MIN_NIGHTS_PERSONAL
        ):
            own = personal_scale(history)
            weight = baseline.shrink_weight
            within = max(
                weight * (own if own > BASELINE_SCALE_FLOOR_BPM else 0.0)
                + (1.0 - weight) * WITHIN_PERSON_PRIOR,
                BASELINE_SCALE_FLOOR_BPM,
            )
            shrunk_scales.append(baseline.scale_bpm)
            personal_scales.append(own)
            within_scales.append(within)
            z_shrunk.append(night["residual"] / max(baseline.scale_bpm, BASELINE_SCALE_FLOOR_BPM))
            z_personal.append(night["residual"] / own)
            z_within.append(night["residual"] / within)
            if baseline.usable_nights >= BASELINE_WINDOW_NIGHTS:
                mature_pairs.append((baseline.scale_bpm, own, within))
        history.append(feature)
        history = history[-BASELINE_WINDOW_NIGHTS:]

# Night to night wobble per person, which is what the scale is trying to estimate.
for row in rows:
    values = [n["rhr"] for n in row["per_night"] if n["usable"] and n["rhr"] is not None]
    if len(values) < 15:
        continue
    median = statistics.median(values)
    raw_personal.append(MAD_TO_SD_FACTOR * statistics.median([abs(v - median) for v in values]))


def describe(name: str, values: list[float]) -> None:
    ordered = sorted(values)
    quarters = statistics.quantiles(ordered, n=4)
    print(
        f"  {name:<38} n={len(ordered):>5}  median {statistics.median(ordered):>5.2f}  "
        f"IQR {quarters[0]:>5.2f} to {quarters[2]:>5.2f}"
    )


print("=" * 84)
print("HOW MUCH DOES A REAL PERSON'S OVERNIGHT HEART RATE WOBBLE?")
print("=" * 84)
describe("their own scaled MAD, whole record", raw_personal)
print(f"  people measured                        {len(raw_personal)}")
print()

print("=" * 84)
print("THE BAND WIDTH, as it is today and as a personal scale would make it")
print("=" * 84)
describe("today, toward 8.64 between-person SD", shrunk_scales)
describe("personal only, floor still applied", personal_scales)
describe(f"toward a {WITHIN_PERSON_PRIOR} within-person prior", within_scales)
if mature_pairs:
    print()
    print(f"  at a full {BASELINE_WINDOW_NIGHTS} night window, where the weight caps at 0.8:")
    for label, index in (("today", 0), ("personal only", 1), ("within-person prior", 2)):
        values = [row[index] for row in mature_pairs]
        print(f"    {label:<22} median {statistics.median(values):.2f} bpm")
print()

print("=" * 84)
print(f"HOW OFTEN WOULD THE EXTREME HEART RATE RULES FIRE? (|robust z| > {EXTREME_Z})")
print("=" * 84)
print("Those two rules have never executed, because no caller passes robust_z. Before")
print("connecting them, this is what connecting them would do on 8,508 real nights.")
print()
for name, values in (
    ("today, toward the between-person SD", z_shrunk),
    ("a personal scale, no shrinkage", z_personal),
    (f"toward a {WITHIN_PERSON_PRIOR} within-person prior", z_within),
):
    high = [z for z in values if z > EXTREME_Z]
    low = [z for z in values if z < -EXTREME_Z]
    nights = len(values)
    weeks = nights / 7.0
    print(f"--- {name} ---")
    print(f"  scorable nights                  : {nights}")
    print(f"  above +{EXTREME_Z}                        : {len(high)}  ({len(high) / nights:.3%})")
    print(f"  below -{EXTREME_Z}                        : {len(low)}  ({len(low) / nights:.3%})")
    print(
        f"  one urgent escalation every      : "
        f"{weeks / max(1, len(high) + len(low)):.0f} person-weeks"
    )
    ordered = sorted(values)
    print(
        f"  z distribution                   : median {statistics.median(ordered):+.2f}, "
        f"99th pct {ordered[int(0.99 * len(ordered))]:+.2f}, max {ordered[-1]:+.2f}"
    )
    print()

print("=" * 84)
print("READ THIS BEFORE CHANGING THE SCALE")
print("=" * 84)
print("A narrower band makes robust_z LARGER for the same rise, so the extreme rules fire")
print("more often. The two numbers above are the whole argument. If the personal scale")
print("produces urgent escalations at a rate a person would not tolerate, the threshold is")
print("wrong, not the wiring, and that has to be settled before item 4 connects the rules.")
