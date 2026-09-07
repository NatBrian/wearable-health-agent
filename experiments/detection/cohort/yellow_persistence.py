"""Does a long run of merely YELLOW nights deserve an investigation?

The detector flags two consecutive RED nights and nothing else, which is the published
NightSignal rule and is measured. What has never been measured is the gap that rule leaves:
somebody who sits at three and a half beats above their own normal for ten nights running,
never once reaching four, and has no investigation opened, ever.

That is not obviously wrong. It might be exactly right. But `sweep.py` compared "at least
one RED" against "both RED" and never scored a yellow-persistence arm at all, so the
current behaviour on this case is an assumption wearing a measurement's clothes.

Scored on the same nights, the same window and the same alert-rate denominator as
`sweep.py`, so the numbers here sit beside that table rather than beneath it.

Run `evaluate.py` first.
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from wha.constants import (  # noqa: E402
    BASELINE_MIN_NIGHTS_PERSONAL,
    DETECT_RED_BPM,
    DETECT_YELLOW_BPM,
)

RESULTS = REPO / "data" / "cohort" / "cohort_results.json"
if not RESULTS.exists():
    raise SystemExit(f"{RESULTS} is missing. Run experiments/detection/cohort/evaluate.py first.")

rows = json.loads(RESULTS.read_text(encoding="utf-8"))
if "per_night" not in rows[0]:
    raise SystemExit("cohort_results.json predates the per-night record. Re-run evaluate.py.")

PRE_FROM, PRE_TO = 7, 1

series: dict[str, list[dict]] = {
    r["pid"]: [
        {"night": date.fromisoformat(n["night"]), "residual": n["residual"]}
        for n in r["per_night"]
        if n["usable"]
        and n["residual"] is not None
        and n["baseline_nights"] >= BASELINE_MIN_NIGHTS_PERSONAL
    ]
    for r in rows
}

onsets = {
    r["pid"]: date.fromisoformat(r["symptom"])
    for r in rows
    if r["category"] == "COVID-19" and r["symptom"]
}
healthy = [r["pid"] for r in rows if r["category"] == "unlabelled"]
weeks_by_pid = {r["pid"]: r["nights"] / 7.0 for r in rows}


def levels(nights: list[dict]) -> dict[date, str]:
    out = {}
    for n in nights:
        v = n["residual"]
        out[n["night"]] = (
            "RED" if v >= DETECT_RED_BPM else ("YELLOW" if v >= DETECT_YELLOW_BPM else "GREEN")
        )
    return out


def alerts_both_red(nights: list[dict]) -> list[date]:
    """The rule in production today: two consecutive RED nights."""
    level = levels(nights)
    return sorted(
        d
        for d, lvl in level.items()
        if lvl == "RED" and level.get(d - timedelta(days=1)) == "RED"
    )


def alerts_raised_run(nights: list[dict], length: int) -> list[date]:
    """`length` consecutive nights at or above YELLOW, whether or not any is RED."""
    level = levels(nights)
    out = []
    for d, lvl in level.items():
        if lvl == "GREEN":
            continue
        run = 1
        cursor = d
        while run < length:
            cursor = cursor - timedelta(days=1)
            if level.get(cursor) in ("YELLOW", "RED"):
                run += 1
            else:
                break
        if run >= length:
            out.append(d)
    return sorted(out)


def runs(days: list[date]) -> int:
    total, prev = 0, None
    for d in days:
        if prev is None or (d - prev).days > 1:
            total += 1
        prev = d
    return total


def evaluate(alert_fn) -> tuple[float, float, int]:
    hit = 0
    for pid, onset in onsets.items():
        if any(-PRE_FROM <= (d - onset).days <= PRE_TO for d in alert_fn(series[pid])):
            hit += 1
    total_runs = sum(runs(alert_fn(series[p])) for p in healthy)
    total_weeks = sum(weeks_by_pid[p] for p in healthy)
    return hit / len(onsets), (total_runs / total_weeks if total_weeks else 0.0), hit


print(f"labelled COVID cases: {len(onsets)}   healthy controls: {len(healthy)}")
print(f"person-weeks of healthy data: {sum(weeks_by_pid[p] for p in healthy):.0f}")
print(f"YELLOW at +{DETECT_YELLOW_BPM} bpm, RED at +{DETECT_RED_BPM} bpm.")
print(f"Detection window: {PRE_FROM} days before symptom onset to {PRE_TO} day after.")
print()
print(f"{'rule':<44}{'sensitivity':>13}{'cases':>8}{'alerts/person-week':>21}")
print("-" * 86)

base_sens, base_rate, base_hit = evaluate(alerts_both_red)
print(f"{'two consecutive RED (in production today)':<44}{base_sens:>12.1%}{base_hit:>8}{base_rate:>21.3f}")

for length in (2, 3, 4, 5, 6, 7):
    sens, rate, hit = evaluate(lambda n, k=length: alerts_raised_run(n, k))
    print(f"{f'{length} consecutive nights at or above YELLOW':<44}{sens:>12.1%}{hit:>8}{rate:>21.3f}")

print()
print("Additive: the rule in production today, OR a run of yellow-or-above nights.")
for length in (3, 4, 5, 6, 7):

    def combined(n, k=length):
        return sorted(set(alerts_both_red(n)) | set(alerts_raised_run(n, k)))

    sens, rate, hit = evaluate(combined)
    print(
        f"{f'both RED or {length} raised nights':<44}{sens:>12.1%}{hit:>8}{rate:>21.3f}"
        f"   ({sens - base_sens:+.1%} sensitivity, {rate / base_rate if base_rate else 0:.2f}x alerts)"
    )
