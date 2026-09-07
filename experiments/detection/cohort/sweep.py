"""Should the detector fire on a fixed number of beats, or on a number personal to you?

Two questions, on the same nights, scored the same way.

**The threshold family.** The system already computes `robust_z`, the rise divided by that
person's own night-to-night wobble, and has never used it to decide anything. Would a
personal threshold beat a fixed one? The comparison must be AT A MATCHED ALERT RATE, which
section C does, because any detector looks sensitive if you let it alert often enough.

**The persistence rule.** This is the one place the system is looser than the published
algorithm it takes its thresholds from. NightSignal raises a red alert on two consecutive
nights at or above baseline + 4. This system flags two consecutive raised nights where AT
LEAST ONE is red, so red followed by yellow also fires, and nothing says so.

This reads the residual and the robust z that `evaluate.py` recorded from the product's own
`compute_detection_for_features`, and varies only the cut points. An earlier version
rebuilt its own baselines from a night list that had already had unusable nights removed,
which gave every participant a baseline the detector never used and a sensitivity table
that was wrong by six points. Do not reintroduce that: score what the detector computed.

Run `evaluate.py` first.
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from wha.constants import BASELINE_MIN_NIGHTS_PERSONAL

RESULTS = REPO / "data" / "cohort" / "cohort_results.json"
if not RESULTS.exists():
    raise SystemExit(f"{RESULTS} is missing. Run experiments/detection/cohort/evaluate.py first.")

rows = json.loads(RESULTS.read_text(encoding="utf-8"))
if "per_night" not in rows[0]:
    raise SystemExit(
        "cohort_results.json predates the per-night record. Re-run experiments/detection/cohort/evaluate.py."
    )

# 7 days before onset to 1 day after. Narrower than the report's widest window, because a
# threshold that only wins on a 21 day window has not shown pre-symptomatic detection.
PRE_FROM, PRE_TO = 7, 1

series: dict[str, list[dict]] = {}
for r in rows:
    # Unusable nights are not scored by the product and must not be scored here. The
    # baseline gate is the product's own: nothing is flagged until the centre is the
    # person's own median.
    series[r["pid"]] = [
        {
            "night": date.fromisoformat(n["night"]),
            "residual": n["residual"],
            "z": n["robust_z"],
        }
        for n in r["per_night"]
        if n["usable"]
        and n["residual"] is not None
        and n["baseline_nights"] >= BASELINE_MIN_NIGHTS_PERSONAL
    ]

onsets = {
    r["pid"]: date.fromisoformat(r["symptom"])
    for r in rows
    if r["category"] == "COVID-19" and r["symptom"]
}
healthy = [r["pid"] for r in rows if r["category"] == "unlabelled"]

# Person-weeks are counted over every night the person wore the watch, not only the
# scorable ones, because a week is a week whether or not the detector could speak.
weeks_by_pid = {r["pid"]: r["nights"] / 7.0 for r in rows}


def alerts_for(nights: list[dict], key: str, yellow: float, red: float, both_red: bool):
    """Flagged nights under a candidate rule: two consecutive raised, one red or both."""
    level = {}
    for n in nights:
        v = n[key]
        level[n["night"]] = "RED" if v >= red else ("YELLOW" if v >= yellow else "GREEN")
    out = []
    for d, lvl in level.items():
        if lvl == "GREEN":
            continue
        prev = level.get(d - timedelta(days=1))
        if prev in (None, "GREEN"):
            continue
        if both_red:
            if lvl == "RED" and prev == "RED":
                out.append(d)
        elif lvl == "RED" or prev == "RED":
            out.append(d)
    return sorted(out)


def runs(days: list[date]) -> int:
    """Consecutive alert nights are one investigation, not four."""
    total, prev = 0, None
    for d in days:
        if prev is None or (d - prev).days > 1:
            total += 1
        prev = d
    return total


def evaluate(key: str, yellow: float, red: float, both_red: bool) -> tuple[float, float]:
    hit = 0
    for pid, onset in onsets.items():
        a = alerts_for(series[pid], key, yellow, red, both_red)
        if any(-PRE_FROM <= (d - onset).days <= PRE_TO for d in a):
            hit += 1

    total_runs = sum(runs(alerts_for(series[p], key, yellow, red, both_red)) for p in healthy)
    total_weeks = sum(weeks_by_pid[p] for p in healthy)
    return hit / len(onsets), (total_runs / total_weeks if total_weeks else 0.0)


ABSOLUTE = ((3, 4), (4, 5), (5, 6), (6, 7), (6, 8), (7, 9), (8, 10), (9, 11), (10, 12))
PERSONAL = (
    (1.0, 1.5),
    (1.5, 2.0),
    (2.0, 2.5),
    (2.0, 3.0),
    (2.5, 3.0),
    (3.0, 3.5),
    (3.0, 4.0),
    (3.5, 4.5),
    (4.0, 5.0),
)

print(f"labelled COVID cases: {len(onsets)}   healthy controls: {len(healthy)}")
print(f"person-weeks of healthy data: {sum(weeks_by_pid[p] for p in healthy):.0f}")
print()
print(f"Detection window: {PRE_FROM} days before symptom onset to {PRE_TO} day after.")
print("Alert rate: investigations opened per person-week, on people with no illness label.")
print()

HEADER = (
    f"{'yellow':>7} {'red':>6} {'rule':>10} {'sensitivity':>13} "
    f"{'alerts/person-week':>20} {'one every':>12}"
)


def table(title: str, key: str, grid) -> None:
    print("=" * 86)
    print(title)
    print("=" * 86)
    print(HEADER)
    for y, r in grid:
        for both in (False, True):
            s, a = evaluate(key, y, r, both)
            rule = "2 RED" if both else "1 RED"
            every = f"{1 / a:.1f} wk" if a > 0 else "never"
            # The rule the detector actually runs, as of 5 September 2026: two consecutive
            # nights BOTH at or above baseline + 4, which is the published NightSignal
            # rule. It used to be "at least one RED", the row above.
            today = "   <- today" if key == "residual" and (y, r, both) == (3, 4, True) else ""
            print(f"{y:>7} {r:>6} {rule:>10} {s:>12.1%} {a:>20.3f} {every:>12}{today}")
    print()


table("A. ABSOLUTE THRESHOLD, in beats per minute", "residual", ABSOLUTE)
table("B. PERSONAL THRESHOLD, in multiples of this person's own wobble", "z", PERSONAL)

print("=" * 86)
print("C. MATCHED ALERT RATE: which family finds more infections per interruption?")
print("=" * 86)
for target in (0.28, 0.20, 0.15, 0.10, 0.05):
    best = {}
    for label, key, grid in (
        ("absolute bpm", "residual", ABSOLUTE),
        ("personal   ", "z", PERSONAL),
    ):
        for y, r in grid:
            for both in (False, True):
                s, a = evaluate(key, y, r, both)
                if a <= target and (label not in best or s > best[label][0]):
                    best[label] = (s, a, y, r, both)
    if len(best) == 2:
        print(f"  at most {target:.2f} alerts per person-week (one every {1 / target:.1f} weeks):")
        for label, (s, a, y, r, both) in best.items():
            print(
                f"    {label} : {s:>6.1%} sensitivity  (yellow {y}, red {r}, "
                f"{'2 RED' if both else '1 RED'}, rate {a:.3f})"
            )
