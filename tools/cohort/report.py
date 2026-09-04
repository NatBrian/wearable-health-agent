"""Turn the per-participant cohort results into the numbers EVALUATION.md publishes.

Two things this does that a flattering evaluation would not:

1. It scores detection at several window widths, because a wide window makes any
   detector look good.
2. It compares against a RANDOM detector matched to the same alert rate, which is the
   only way to tell a real detection from a lucky one. This system's own evaluation
   module already demanded that comparator; it had never been run on real data.
"""

from __future__ import annotations

import json
import random
import statistics
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "data" / "cohort" / "cohort_results.json"

if not RESULTS.exists():
    raise SystemExit(f"{RESULTS} is missing. Run tools/cohort/evaluate.py first.")

rows = json.loads(RESULTS.read_text(encoding="utf-8"))

covid = [r for r in rows if r["category"] == "COVID-19" and r["symptom"]]
other = [r for r in rows if r["category"].startswith("Other Illness")]
unlab = [r for r in rows if r["category"] == "unlabelled"]

RNG_SEED = 20260904
TRIALS = 2000


def nights_of(r: dict) -> list[date]:
    return sorted(date.fromisoformat(d) for d in r["rhr_clock"])


def detected(alerts: list[date], onset: date, before: int, after: int) -> tuple[bool, int | None]:
    hits = [a for a in alerts if -before <= (a - onset).days <= after]
    if not hits:
        return False, None
    return True, (onset - min(hits)).days


def runs_of(alerts: list[date]) -> list[date]:
    """First night of each consecutive run of alerts."""
    out: list[date] = []
    prev: date | None = None
    for a in sorted(alerts):
        if prev is None or (a - prev).days > 1:
            out.append(a)
        prev = a
    return out


def sensitivity(key: str, before: int, after: int) -> tuple[int, int, list[int]]:
    hit = 0
    leads: list[int] = []
    for c in covid:
        alerts = [date.fromisoformat(d) for d in c[key]["alert_dates"]]
        d, lead = detected(alerts, date.fromisoformat(c["symptom"]), before, after)
        if d:
            hit += 1
            if lead is not None:
                leads.append(lead)
    return hit, len(covid), leads


def random_sensitivity(key: str, before: int, after: int) -> float:
    """A detector that alerts on the same NUMBER of runs, placed at random.

    Matched on alert rate per person, which is what makes it a fair floor: if a real
    detector cannot beat its own alert rate scattered at random, it has found nothing.
    """
    rng = random.Random(RNG_SEED)
    hits = 0
    for _ in range(TRIALS):
        got = 0
        for c in covid:
            nights = nights_of(c)
            if not nights:
                continue
            n_runs = len(runs_of([date.fromisoformat(d) for d in c[key]["alert_dates"]]))
            if n_runs == 0:
                continue
            picks = rng.sample(nights, min(n_runs, len(nights)))
            d, _ = detected(picks, date.fromisoformat(c["symptom"]), before, after)
            if d:
                got += 1
        hits += got
    return hits / (TRIALS * len(covid))


print(f"participants analysed: {len(rows)}")
print(f"  COVID-19 with a symptom onset date: {len(covid)}")
print(f"  other illness: {len(other)}")
print(f"  unlabelled (no illness label at all): {len(unlab)}")
print()

print("=" * 78)
print("DATA QUALITY GATE: nights surviving the 180 minute coverage floor")
print("=" * 78)
tot_n = sum(r["nights"] for r in rows)
tot_u = sum(r["usable_nights"] for r in rows)
frac = sorted(r["usable_nights"] / r["nights"] for r in rows if r["nights"])
print(f"  nights with any overnight heart rate : {tot_n}")
print(f"  nights usable                        : {tot_u}  ({tot_u / tot_n:.1%})")
print(f"  per person, median usable fraction   : {statistics.median(frac):.1%}")
print(f"  people losing more than half         : {sum(1 for f in frac if f < 0.5)} of {len(frac)}")
print()

print("=" * 78)
print("SENSITIVITY at several window widths, against a rate-matched random detector")
print("=" * 78)
print(f"{'window':<28} {'this system':>14} {'NightSignal':>14} {'random, matched':>17}")
for before, after in ((3, 1), (7, 3), (14, 7), (21, 7)):
    label = f"{before}d before, {after}d after"
    hw, nw, lw = sensitivity("wha_clock", before, after)
    hn, _, ln = sensitivity("nightsignal", before, after)
    rw = random_sensitivity("wha_clock", before, after)
    print(f"{label:<28} {hw}/{nw} = {hw / nw:>6.1%} {hn}/{nw} = {hn / nw:>6.1%} {rw:>16.1%}")
print()
for before, after in ((7, 3), (21, 7)):
    hw, nw, lw = sensitivity("wha_clock", before, after)
    hn, _, ln = sensitivity("nightsignal", before, after)
    if lw:
        print(
            f"  lead time at {before}d/{after}d, this system: median {statistics.median(lw):.1f} d,"
            f" range {min(lw)} to {max(lw)}"
        )
    if ln:
        print(
            f"  lead time at {before}d/{after}d, NightSignal: median {statistics.median(ln):.1f} d,"
            f" range {min(ln)} to {max(ln)}"
        )
print()

print("=" * 78)
print("ALERT BURDEN on people with no illness label at all")
print("=" * 78)
for key, name in (("wha_clock", "this system"), ("nightsignal", "published NightSignal")):
    runs = sum(len(runs_of([date.fromisoformat(d) for d in c[key]["alert_dates"]])) for c in unlab)
    nights = sum(c["nights"] for c in unlab)
    weeks = nights / 7.0
    per = [
        len(runs_of([date.fromisoformat(d) for d in c[key]["alert_dates"]]))
        / max(1.0, c["nights"] / 7.0)
        for c in unlab
    ]
    zero = sum(1 for p in per if p == 0)
    print(f"--- {name} ---")
    print(f"  people                       : {len(unlab)}")
    print(f"  person-weeks of data         : {weeks:.0f}")
    print(f"  investigations opened        : {runs}")
    print(f"  per person-week              : {runs / weeks:.3f}")
    print(f"  one investigation every      : {weeks / max(1, runs):.1f} weeks per person")
    print(f"  median per person, per week  : {statistics.median(per):.3f}")
    print(f"  people never alerted at all  : {zero} of {len(unlab)}")
    print()

print("=" * 78)
print("SLEEP WINDOW versus CLOCK WINDOW, on people with real sleep staging")
print("=" * 78)


def mad(v: list[float]) -> float:
    m = statistics.median(v)
    return 1.4826 * statistics.median([abs(x - m) for x in v])


pairs = []
for r in rows:
    if not r["rhr_sleep"]:
        continue
    common = sorted(set(r["rhr_clock"]) & set(r["rhr_sleep"]))
    if len(common) < 15:
        continue
    c = [r["rhr_clock"][d] for d in common]
    s = [r["rhr_sleep"][d] for d in common]
    pairs.append(
        (r["pid"], len(common), mad(c), mad(s), statistics.median(c) - statistics.median(s))
    )

print(f"  people with >=15 shared nights: {len(pairs)}")
if pairs:
    sc = [p[2] for p in pairs]
    ss = [p[3] for p in pairs]
    lvl = [p[4] for p in pairs]
    smaller = sum(1 for a, b in zip(sc, ss) if b < a)
    larger = sum(1 for a, b in zip(sc, ss) if b > a)
    same = sum(1 for a, b in zip(sc, ss) if b == a)
    print(f"  night-to-night spread, clock window : median {statistics.median(sc):.2f} bpm")
    print(f"  night-to-night spread, sleep window : median {statistics.median(ss):.2f} bpm")
    print(f"  spread SMALLER on the sleep window  : {smaller} of {len(pairs)}")
    print(f"  spread LARGER on the sleep window   : {larger} of {len(pairs)}")
    print(f"  spread identical                    : {same} of {len(pairs)}")
    print(f"  median level difference (clock - sleep): {statistics.median(lvl):+.2f} bpm")
    print()
    header = f"  {'participant':<12} {'nights':>7} {'spread clock':>13}"
    print(f"{header} {'spread sleep':>13} {'level diff':>11}")
    for pid, n, a, b, d in sorted(pairs, key=lambda p: p[3] - p[2]):
        print(f"  {pid:<12} {n:>7} {a:>13.2f} {b:>13.2f} {d:>+11.2f}")
print()

print("=" * 78)
print("PER CASE DETAIL, COVID-19, at a 7 day before / 3 day after window")
print("=" * 78)
print(
    f"{'participant':<12} {'nights':>6} {'usable':>6} {'wha':>5} {'lead':>5} "
    f"{'ns':>4} {'lead':>5} {'wha runs':>9} {'ns runs':>8}"
)
for c in sorted(covid, key=lambda x: x["pid"]):
    onset = date.fromisoformat(c["symptom"])
    aw = [date.fromisoformat(d) for d in c["wha_clock"]["alert_dates"]]
    an = [date.fromisoformat(d) for d in c["nightsignal"]["alert_dates"]]
    dw, lw2 = detected(aw, onset, 7, 3)
    dn, ln2 = detected(an, onset, 7, 3)
    print(
        f"{c['pid']:<12} {c['nights']:>6} {c['usable_nights']:>6} "
        f"{('yes' if dw else 'no'):>5} {lw2!s:>5} {('yes' if dn else 'no'):>4} {ln2!s:>5} "
        f"{len(runs_of(aw)):>9} {len(runs_of(an)):>8}"
    )
