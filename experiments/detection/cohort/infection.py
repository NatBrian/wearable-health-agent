"""How much does an infection actually raise your overnight resting heart rate?

`causes.yaml` says 1.60 bpm, and that is the single most consequential number in this
project: it is what the belief model weighs every competing explanation against. Its stated
derivation multiplies a percentage measured in 7,200 Fitbit users by an average measured in
525 university students, which lands in roughly the right place by luck rather than method.

This measures it directly, on 30 labelled COVID-19 cases, using the product's own
`compute_baseline` so the answer is in the units the detector works in.

**Everything here is measured against a matched control.** Taking the highest night in a
window is biased upward: do it on any window of noise and you get a positive number. So
the illness peak means nothing on its own. Healthy people are scored with the same
statistic, on windows of the same width, drawn from the same cohort. The difference between
the two is the honest estimate.

That control is the reason an earlier draft of this project's review was wrong. It argued
that 1.60 bpm could not be right because it is smaller than the 3 and 4 bpm thresholds, and
concluded the number must be bigger. The real explanation is the other one: a flagged night
is usually noise, and the belief model is correct to say infection is unlikely on any one
of them.

Three things are reported, because item 6 of the refinement plan needs all three:
the effect size, the between-person spread (`effect_sd_bpm`), and the day-by-day shape
(`profile`).

Run `evaluate.py` first.
"""

from __future__ import annotations

import json
import random
import statistics
import sys
import zipfile
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluate import ZIP, clock_nights, features_for, participants, read_hr

from wha.detect.baseline import compute_baseline

DATA = REPO / "data" / "cohort"
LABELS = json.loads((DATA / "labels.json").read_text(encoding="utf-8"))

ONSET = {
    r["pid"]: date.fromisoformat(r["symptom"])
    for r in LABELS
    if r["category"] == "COVID-19" and r.get("symptom")
}
ANY_ILL = {r["pid"] for r in LABELS}

# A window a healthy person's baseline is drawn from must not overlap the window being
# scored, or the elevation is partly subtracted from itself.
BASELINE_FROM, BASELINE_TO = 21, 60
MIN_BASELINE_NIGHTS = 7
MIN_SCORED_NIGHTS = 5
CONTROL_WINDOWS_PER_PERSON = 3

# Fixed so the control draw is the same on every run. Randomness that changes between runs
# would make this number unreproducible, which is the thing the whole file exists to fix.
RNG = random.Random(20260904)


def usable_series(pid: str, z: zipfile.ZipFile) -> list | None:
    hr = read_hr(z, pid)
    if len(hr) < 1000:
        return None
    feats = [f for f in features_for(pid, clock_nights(hr)) if f.usable and f.rhr_bpm is not None]
    return feats if len(feats) >= 40 else None


def peak_above(feats: list, centre: float, lo: date, hi: date) -> float | None:
    """Highest night in [lo, hi] relative to `centre`, or None if too few nights."""
    values = [f.rhr_bpm - centre for f in feats if lo <= f.night_date <= hi]
    return max(values) if len(values) >= MIN_SCORED_NIGHTS else None


def baseline_centre(feats: list, before: date) -> float | None:
    history = [f for f in feats if BASELINE_FROM <= (before - f.night_date).days <= BASELINE_TO]
    if len(history) < MIN_BASELINE_NIGHTS:
        return None
    return compute_baseline(history).centre_bpm


def describe(values: list[float]) -> dict:
    ordered = sorted(values)
    quarters = statistics.quantiles(ordered, n=4) if len(ordered) >= 4 else [ordered[0]] * 3
    return {
        "n": len(ordered),
        "median": statistics.median(ordered),
        "q1": quarters[0],
        "q3": quarters[2],
        "sd": statistics.pstdev(ordered) if len(ordered) > 1 else 0.0,
        "min": min(ordered),
        "max": max(ordered),
    }


def line(label: str, s: dict) -> str:
    return (
        f"  {label:<44} n={s['n']:>3}  median {s['median']:>5.2f}  "
        f"IQR {s['q1']:>5.2f} to {s['q3']:>5.2f}  SD {s['sd']:>4.2f}"
    )


def main() -> int:
    if not ZIP.exists():
        raise SystemExit("Run experiments/detection/cohort/fetch.py first.")

    z = zipfile.ZipFile(ZIP)
    available = set(participants(z))
    cache: dict[str, list] = {}

    def feats_for(pid: str) -> list | None:
        if pid not in cache:
            got = usable_series(pid, z)
            if got is None:
                return None
            cache[pid] = got
        return cache.get(pid)

    print("=" * 84)
    print("HIGHEST NIGHT ABOVE YOUR OWN BASELINE, illness against matched healthy windows")
    print("=" * 84)
    print("Both columns use the same statistic on windows of the same width, so the upward")
    print("bias of taking a maximum cancels. The difference is the infection effect.")
    print()

    summary: dict[int, tuple[dict, dict, dict]] = {}

    for width in (7, 15):
        pre_symptomatic: list[float] = []
        whole_episode: list[float] = []
        for pid, onset in sorted(ONSET.items()):
            if pid not in available:
                continue
            feats = feats_for(pid)
            if feats is None:
                continue
            centre = baseline_centre(feats, onset)
            if centre is None:
                continue
            # Strictly before symptoms: the window this system exists to act in.
            pre = peak_above(
                feats, centre, onset - timedelta(days=width), onset - timedelta(days=1)
            )
            if pre is not None:
                pre_symptomatic.append(pre)
            # Symptom onset included, which is the larger effect and a different regime.
            whole = peak_above(
                feats,
                centre,
                onset - timedelta(days=width // 2),
                onset + timedelta(days=width // 2),
            )
            if whole is not None:
                whole_episode.append(whole)

        controls: list[float] = []
        for pid in sorted(available - ANY_ILL):
            feats = feats_for(pid)
            if feats is None:
                continue
            nights = [f.night_date for f in feats]
            if len(nights) < BASELINE_TO:
                continue
            for _ in range(CONTROL_WINDOWS_PER_PERSON):
                end = nights[RNG.randrange(BASELINE_TO - 15, len(nights))]
                centre = baseline_centre(feats, end - timedelta(days=width - 1))
                if centre is None:
                    continue
                peak = peak_above(feats, centre, end - timedelta(days=width - 1), end)
                if peak is not None:
                    controls.append(peak)

        if not (pre_symptomatic and whole_episode and controls):
            continue

        pre_s, whole_s, ctrl_s = (
            describe(pre_symptomatic),
            describe(whole_episode),
            describe(controls),
        )
        summary[width] = (pre_s, whole_s, ctrl_s)

        print(f"--- {width} night windows ---")
        print(line("healthy, random windows (the control)", ctrl_s))
        print(line("COVID-19, strictly before symptoms", pre_s))
        print(line("COVID-19, spanning symptom onset", whole_s))
        print(
            f"  {'INFECTION EFFECT, pre-symptomatic':<44} "
            f"{pre_s['median'] - ctrl_s['median']:>+6.2f} bpm"
        )
        print(
            f"  {'INFECTION EFFECT, spanning onset':<44} "
            f"{whole_s['median'] - ctrl_s['median']:>+6.2f} bpm"
        )
        print()

    print("=" * 84)
    print("BETWEEN-PERSON SPREAD, which is what effect_sd_bpm encodes")
    print("=" * 84)
    print("  causes.yaml carries effect_sd_bpm: 1.00 with no source at all.")
    print()
    print("  The right statistic is NOT the spread of the peak. The belief model uses")
    print("  effect_sd as the spread of this cause's PER-NIGHT contribution, so the")
    print("  measurement has to be the mean nightly elevation per person, not a maximum")
    print("  over a window, which mixes in how noisy each person happens to be.")
    print()

    ill_means: list[float] = []
    for pid, onset in sorted(ONSET.items()):
        if pid not in available:
            continue
        feats = feats_for(pid)
        if feats is None:
            continue
        centre = baseline_centre(feats, onset)
        if centre is None:
            continue
        window = [f.rhr_bpm - centre for f in feats if -7 <= (f.night_date - onset).days <= -1]
        if len(window) >= MIN_SCORED_NIGHTS:
            ill_means.append(statistics.fmean(window))

    ctrl_means: list[float] = []
    rng = random.Random(20260905)
    for pid in sorted(available - ANY_ILL):
        feats = feats_for(pid)
        if feats is None:
            continue
        nights = [f.night_date for f in feats]
        if len(nights) < BASELINE_TO:
            continue
        for _ in range(CONTROL_WINDOWS_PER_PERSON):
            end = nights[rng.randrange(BASELINE_TO - 15, len(nights))]
            start = end - timedelta(days=6)
            centre = baseline_centre(feats, start)
            if centre is None:
                continue
            window = [f.rhr_bpm - centre for f in feats if start <= f.night_date <= end]
            if len(window) >= MIN_SCORED_NIGHTS:
                ctrl_means.append(statistics.fmean(window))

    if ill_means and ctrl_means:
        ill = describe(ill_means)
        ctrl = describe(ctrl_means)
        print(line("healthy, mean over a 7 night window", ctrl))
        print(line("COVID-19, mean over the 7 nights before", ill))
        print()
        print(f"  effect on the MEAN nightly elevation : {ill['median'] - ctrl['median']:+.2f} bpm")
        excess = max(0.0, ill["sd"] ** 2 - ctrl["sd"] ** 2) ** 0.5
        print(f"  between-person spread, excess of illness over control : {excess:.2f} bpm")
        print()
        print("  The subtraction assumes the two spreads are independent, which is an")
        print(f"  assumption. At n={ill['n']} cases it is also imprecise. Quote both numbers.")

    print()
    print("=" * 84)
    print("DAY BY DAY, relative to symptom onset. This is what `profile` encodes.")
    print("=" * 84)
    by_offset: dict[int, list[float]] = defaultdict(list)
    for pid, onset in sorted(ONSET.items()):
        if pid not in available:
            continue
        feats = feats_for(pid)
        if feats is None:
            continue
        centre = baseline_centre(feats, onset)
        if centre is None:
            continue
        for f in feats:
            offset = (f.night_date - onset).days
            if -10 <= offset <= 14:
                by_offset[offset].append(f.rhr_bpm - centre)

    control_median = summary[7][2]["median"] if 7 in summary else 0.0
    print(f"  {'day':>5} {'people':>7} {'median bpm above own baseline':>32}")
    for offset in range(-10, 15):
        values = by_offset.get(offset, [])
        if len(values) < 10:
            continue
        med = statistics.median(values)
        bar = "#" * max(0, round(med * 4))
        print(f"  {offset:>+5} {len(values):>7} {med:>+16.2f}   {bar}")
    print()
    print(f"  For scale, the healthy 7 night control peak sits at {control_median:.2f} bpm,")
    print("  but that is a MAXIMUM over 7 nights and these are per-night medians, so the")
    print("  two are not directly comparable. The shape is what this table is for.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
