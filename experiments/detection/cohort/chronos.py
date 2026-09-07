"""Does the Chronos forecast tell you anything the baseline residual does not?

Three questions, on 120 real people:

  1. Are the two numbers actually different, or is forecast_z just re-deriving residual?
  2. Near a labelled symptom onset, does forecast_z separate illness from ordinary nights
     as well as, better than, or worse than the residual?
  3. Would a forecast alert catch a case the detector misses?
"""

from __future__ import annotations

import json
import statistics
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
rows = json.loads((REPO / "data" / "cohort" / "chronos_results.json").read_text(encoding="utf-8"))

pairs: list[tuple[float, float]] = []
ill_res, ill_fc, well_res, well_fc = [], [], [], []

for r in rows:
    onset = date.fromisoformat(r["onset"]) if r["onset"] else None
    for n in r["nights"]:
        if n["forecast_z"] is None:
            continue
        res, fz = n["residual"], n["forecast_z"]
        pairs.append((res, fz))
        if onset is None:
            well_res.append(res)
            well_fc.append(fz)
        else:
            d = (date.fromisoformat(n["night"]) - onset).days
            if -7 <= d <= 1:
                ill_res.append(res)
                ill_fc.append(fz)
            elif abs(d) > 21:
                well_res.append(res)
                well_fc.append(fz)

print(f"nights with a forecast: {len(pairs)}")
print()


def corr(a, b):
    ma, mb = statistics.mean(a), statistics.mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5
    return num / den if den else 0.0


ra = [p[0] for p in pairs]
fa = [p[1] for p in pairs]
print("=" * 78)
print("1. ARE THEY THE SAME NUMBER?")
print("=" * 78)
print(f"  correlation between residual and forecast_z : {corr(ra, fa):.3f}")
print(f"  residual   : median {statistics.median(ra):+.2f}, sd {statistics.pstdev(ra):.2f}")
print(f"  forecast_z : median {statistics.median(fa):+.2f}, sd {statistics.pstdev(fa):.2f}")
print()

print("=" * 78)
print("2. DOES IT SEPARATE ILLNESS FROM ORDINARY NIGHTS?")
print("=" * 78)


def auc(pos: list[float], neg: list[float]) -> float:
    """Probability a random illness night scores above a random ordinary night."""
    neg_sorted = sorted(neg)
    import bisect

    total = 0.0
    for p in pos:
        lo = bisect.bisect_left(neg_sorted, p)
        hi = bisect.bisect_right(neg_sorted, p)
        total += lo + 0.5 * (hi - lo)
    return total / (len(pos) * len(neg))


print(f"  illness nights (7 days before onset to 1 after) : {len(ill_res)}")
print(f"  ordinary nights                                 : {len(well_res)}")
print()
print(
    f"  residual   : illness median {statistics.median(ill_res):+.2f}, "
    f"ordinary median {statistics.median(well_res):+.2f}, AUC {auc(ill_res, well_res):.3f}"
)
print(
    f"  forecast_z : illness median {statistics.median(ill_fc):+.2f}, "
    f"ordinary median {statistics.median(well_fc):+.2f}, AUC {auc(ill_fc, well_fc):.3f}"
)
print()
print("  AUC 0.5 means no separation at all. 1.0 means perfect.")
print()

print("=" * 78)
print("3. DOES THE FORECAST CATCH ANYTHING THE DETECTOR MISSES?")
print("=" * 78)
covid = [r for r in rows if r["onset"]]
for res_thr, fz_thr in ((3.0, 1.0), (3.0, 1.5), (4.0, 2.0)):
    det_only = fc_only = both = neither = 0
    for r in covid:
        onset = date.fromisoformat(r["onset"])
        window = [
            n
            for n in r["nights"]
            if n["forecast_z"] is not None
            and -7 <= (date.fromisoformat(n["night"]) - onset).days <= 1
        ]
        d = any(n["residual"] >= res_thr for n in window)
        f = any(n["forecast_z"] >= fz_thr for n in window)
        if d and f:
            both += 1
        elif d:
            det_only += 1
        elif f:
            fc_only += 1
        else:
            neither += 1
    print(
        f"  residual >= {res_thr}, forecast_z >= {fz_thr}: "
        f"both {both}, detector only {det_only}, FORECAST ONLY {fc_only}, neither {neither}"
    )
print()
print("  'forecast only' is the number of infections the forecast would catch that the")
print("  detector misses. That is the whole case for keeping it.")
