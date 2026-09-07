"""Replay this system's detector, and the published NightSignal, over the real cohort.

Not part of the product. It imports the real pure functions from `wha` so that what is
measured is what the product would do, and implements the published algorithm separately
so the two can be scored on the same nights.

Writes `data/cohort/cohort_results.json`, which `report.py` turns into the tables in
`RESULTS.md`. Takes roughly twenty minutes.
"""

from __future__ import annotations

import bisect
import csv
import io
import json
import statistics
import sys
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from wha.constants import DETECT_RED_BPM
from wha.detect.baseline import compute_baseline
from wha.detect.detector import compute_detection_for_features
from wha.features.rhr import compute_nocturnal_rhr
from wha.models import DetectionLevel, NightlyFeatures

DATA = REPO / "data" / "cohort"
ZIP = DATA / "COVID-19-Wearables.zip"
LABELS = DATA / "labels.json"
RESULTS = DATA / "cohort_results.json"

# The dataset's sleep vocabulary. The product recognises Health Connect's words and
# numeric codes; this cohort uses Fitbit's, so the mapping is stated rather than assumed.
AWAKE_WORDS = {"wake", "awake", "restless"}

# How wide a window around symptom onset still counts as a detection. Deliberately the
# widest of the four the report scores, so the per-participant record keeps every alert
# and the narrow windows can be scored later without re-running this.
DETECTION_WINDOW_BEFORE = 21
DETECTION_WINDOW_AFTER = 7


# ----------------------------------------------------------------- loading


def participants(z: zipfile.ZipFile) -> list[str]:
    names = [n for n in z.namelist() if n.endswith("_hr.csv") and "longterm" not in n]
    return sorted(n.split("/")[-1][: -len("_hr.csv")] for n in names)


def read_hr(z: zipfile.ZipFile, pid: str) -> list[tuple[datetime, float]]:
    with z.open(f"COVID-19-Wearables/{pid}_hr.csv") as f:
        reader = csv.reader(io.TextIOWrapper(f, "utf-8", errors="replace"))
        next(reader, None)
        out = []
        for row in reader:
            if len(row) < 3:
                continue
            try:
                out.append((datetime.fromisoformat(row[1]), float(row[2])))
            except ValueError:
                continue
    return out


def read_steps(z: zipfile.ZipFile, pid: str) -> dict[datetime, float]:
    name = f"COVID-19-Wearables/{pid}_steps.csv"
    if name not in z.namelist():
        return {}
    with z.open(name) as f:
        reader = csv.reader(io.TextIOWrapper(f, "utf-8", errors="replace"))
        next(reader, None)
        out: dict[datetime, float] = {}
        for row in reader:
            if len(row) < 3:
                continue
            try:
                key = datetime.fromisoformat(row[1]).replace(second=0, microsecond=0)
                out[key] = float(row[2])
            except ValueError:
                continue
    return out


def read_sleep(z: zipfile.ZipFile, pid: str) -> list[tuple[datetime, datetime, str]]:
    name = f"COVID-19-Wearables/{pid}_sleep.csv"
    if name not in z.namelist():
        return []
    with z.open(name) as f:
        reader = csv.reader(io.TextIOWrapper(f, "utf-8", errors="replace"))
        next(reader, None)
        out = []
        for row in reader:
            if len(row) < 4:
                continue
            try:
                start = datetime.fromisoformat(row[1])
                dur = float(row[2])
            except ValueError:
                continue
            out.append((start, start + timedelta(seconds=dur), row[3].strip().lower()))
    return sorted(out)


# ----------------------------------------------------------------- windows


def clock_nights(hr: list[tuple[datetime, float]]) -> dict[date, list[tuple[datetime, float]]]:
    """Local 00:00 to 07:00, the NightSignal window and this system's fallback."""
    nights: dict[date, list[tuple[datetime, float]]] = defaultdict(list)
    for ts, bpm in hr:
        if ts.hour < 7:
            nights[ts.date()].append((ts, bpm))
    return nights


def sleep_sessions(
    stages: list[tuple[datetime, datetime, str]], gap_minutes: int = 60
) -> list[list[tuple[datetime, datetime, str]]]:
    """Split stage rows into sessions on a gap, as wha.features.sleep_window does."""
    sessions: list[list[tuple[datetime, datetime, str]]] = []
    current: list[tuple[datetime, datetime, str]] = []
    gap = timedelta(minutes=gap_minutes)
    for row in stages:
        if current and (row[0] - current[-1][1]) > gap:
            sessions.append(current)
            current = []
        current.append(row)
    if current:
        sessions.append(current)
    return sessions


def sleep_nights(
    hr: list[tuple[datetime, float]],
    stages: list[tuple[datetime, datetime, str]],
) -> dict[date, list[tuple[datetime, float]]]:
    """Heart rate inside the main recorded sleep of each night, waking spells excluded.

    Mirrors wha.features.sleep_window.resolve_sleep_window: the session chosen for a night
    is the one whose asleep intervals END on that local date, and where more than one
    qualifies the one with the most sleep wins (naps are not pooled).
    """
    best_by_night: dict[date, tuple[float, list[tuple[datetime, datetime]]]] = {}
    for session in sleep_sessions(stages):
        spans = [(a, b) for a, b, st in session if st not in AWAKE_WORDS]
        if not spans:
            continue
        merged: list[list[datetime]] = [[spans[0][0], spans[0][1]]]
        for a, b in spans[1:]:
            if a <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], b)
            else:
                merged.append([a, b])
        intervals = [(a, b) for a, b in merged]
        end = max(b for _, b in intervals)
        night = end.date()
        asleep = sum((b - a).total_seconds() for a, b in intervals)
        if night not in best_by_night or asleep > best_by_night[night][0]:
            best_by_night[night] = (asleep, intervals)

    # Bisect over the sorted heart rate series rather than rescanning it per night. A
    # linear rescan is O(nights x samples x intervals) and does not finish on a
    # participant with 700,000 samples.
    hr_sorted = sorted(hr)
    times = [ts for ts, _ in hr_sorted]

    nights: dict[date, list[tuple[datetime, float]]] = {}
    for night, (_, intervals) in best_by_night.items():
        picked: list[tuple[datetime, float]] = []
        for a, b in intervals:
            lo = bisect.bisect_left(times, a)
            hi = bisect.bisect_left(times, b)
            picked.extend(hr_sorted[lo:hi])
        if picked:
            nights[night] = picked
    return nights


# ------------------------------------------------------- this system's detector


def features_for(
    pid: str, nights: dict[date, list[tuple[datetime, float]]]
) -> list[NightlyFeatures]:
    """Nightly features using the product's own compute_nocturnal_rhr."""
    out: list[NightlyFeatures] = []
    for night in sorted(nights):
        samples = [{"ts_utc": ts, "avg_bpm": bpm} for ts, bpm in nights[night]]
        rhr, coverage, dropped, usable = compute_nocturnal_rhr(samples)
        out.append(
            NightlyFeatures(
                subject_id=pid,
                night_date=night,
                rhr_bpm=rhr,
                coverage_minutes=coverage,
                implausible_dropped=dropped,
                usable=usable,
            )
        )
    return out


def run_wha_detector(features: list[NightlyFeatures]) -> list[dict]:
    """Replay the product's detector night by night.

    Emits the residual, the robust z and the baseline's night count as the product
    computed them, so `sweep.py` can vary the thresholds over the real numbers instead of
    re-deriving its own. An earlier sweep rebuilt residuals from a night list that had the
    first five nights and every unusable night already removed, which gave every
    participant a different baseline from the one the detector actually used, and a
    sensitivity table that was wrong by six points.

    `compute_baseline` filters `usable` itself, so unusable nights are appended to history
    and simply ignored there.
    """
    results: list[dict] = []
    history: list[NightlyFeatures] = []
    prior_levels: dict[date, str] = {}
    for feat in features:
        baseline = compute_baseline(history)
        preceding: list[DetectionLevel] = []
        d = feat.night_date - timedelta(days=1)
        while prior_levels.get(d) in ("YELLOW", "RED"):
            preceding.append(DetectionLevel(prior_levels[d]))
            d -= timedelta(days=1)
        det = compute_detection_for_features(feat, baseline, preceding)
        prior_levels[feat.night_date] = det.level.value
        results.append(
            {
                "night": feat.night_date.isoformat(),
                "level": det.level.value,
                "flagged": det.flagged,
                "residual": det.residual_bpm,
                "robust_z": det.robust_z,
                "rhr": feat.rhr_bpm,
                "usable": feat.usable,
                "baseline_nights": baseline.usable_nights,
                "baseline_centre": baseline.centre_bpm,
                "baseline_scale": baseline.scale_bpm,
            }
        )
        history.append(feat)
        history = history[-28:]
    return results


# ------------------------------------------------------- published NightSignal


def run_nightsignal(
    hr: list[tuple[datetime, float]],
    steps: dict[datetime, float],
) -> list[tuple[date, bool]]:
    """The published algorithm, transcribed from the authors' own nightsignal.py.

    Nightly value: MEAN of minute heart rates between 00:00 and 06:59 where that minute's
    step count is zero. Baseline: expanding streaming median of all nightly means up to
    and including tonight. Red alert: two consecutive nights at or above baseline + 4.
    """
    per_night: dict[date, list[float]] = defaultdict(list)
    for ts, bpm in hr:
        if ts.hour >= 7:
            continue
        minute = ts.replace(second=0, microsecond=0)
        if steps and steps.get(minute, 0.0) != 0.0:
            continue
        per_night[ts.date()].append(bpm)

    avgs = {d: int(sum(v) / len(v)) for d, v in per_night.items() if v}
    ordered = sorted(avgs)
    over_red: dict[date, bool] = {}
    seen: list[int] = []
    for d in ordered:
        seen.append(avgs[d])
        median = int(statistics.median(seen))
        over_red[d] = avgs[d] >= median + int(DETECT_RED_BPM)

    alerts: list[tuple[date, bool]] = []
    for i, d in enumerate(ordered):
        prev = ordered[i - 1] if i > 0 else None
        red = bool(over_red[d] and prev is not None and (d - prev).days == 1 and over_red[prev])
        alerts.append((d, red))
    return alerts


# ----------------------------------------------------------------- scoring


@dataclass
class Case:
    pid: str
    category: str
    symptom: date | None
    diagnosis: date | None


def load_labels() -> dict[str, Case]:
    raw = json.loads(LABELS.read_text(encoding="utf-8"))
    out = {}
    for r in raw:
        out[r["pid"]] = Case(
            pid=r["pid"],
            category=r["category"],
            symptom=date.fromisoformat(r["symptom"]) if r.get("symptom") else None,
            diagnosis=date.fromisoformat(r["diagnosis"]) if r.get("diagnosis") else None,
        )
    return out


def score(alerts: list[date], case: Case | None, all_nights: list[date]) -> dict:
    """Recall and lead time against the labelled onset, and alerts outside illness."""
    anchor = case.symptom if case is not None else None

    detected = False
    lead = None
    if anchor is not None:
        window = [
            a
            for a in alerts
            if -DETECTION_WINDOW_BEFORE <= (a - anchor).days <= DETECTION_WINDOW_AFTER
        ]
        if window:
            detected = True
            lead = (anchor - min(window)).days

    illness_days: set[date] = set()
    if anchor is not None:
        for k in range(-DETECTION_WINDOW_BEFORE, DETECTION_WINDOW_AFTER + 1):
            illness_days.add(anchor + timedelta(days=k))
    false_alerts = [a for a in alerts if a not in illness_days]
    clean_days = len([d for d in all_nights if d not in illness_days])

    # Distinct alert runs, not alert nights. An episode covers a consecutive run, so a
    # four night run is one interruption and not four.
    def count_runs(days: list[date]) -> int:
        total = 0
        prev: date | None = None
        for a in sorted(days):
            if prev is None or (a - prev).days > 1:
                total += 1
            prev = a
        return total

    return {
        "detected": detected,
        "lead_days": lead,
        "n_alerts": len(alerts),
        "n_alert_runs": count_runs(alerts),
        "n_false_alert_days": len(false_alerts),
        "n_false_alert_runs": count_runs(false_alerts),
        "clean_nights": clean_days,
        "alert_dates": [a.isoformat() for a in sorted(alerts)],
    }


def main() -> int:
    if not ZIP.exists() or not LABELS.exists():
        raise SystemExit(
            "Missing inputs. Run experiments/detection/cohort/fetch.py then experiments/detection/cohort/labels.py first."
        )

    labels = load_labels()
    z = zipfile.ZipFile(ZIP)
    pids = participants(z)
    print(f"participants with heart rate data: {len(pids)}")
    print(f"labelled cases: {len(labels)}")
    print()

    rows = []
    for i, pid in enumerate(pids, 1):
        hr = read_hr(z, pid)
        if len(hr) < 1000:
            continue
        steps = read_steps(z, pid)
        stages = read_sleep(z, pid)

        clock = clock_nights(hr)
        sleep = sleep_nights(hr, stages) if stages else {}

        feats_clock = features_for(pid, clock)
        wha_clock = run_wha_detector(feats_clock)
        wha_clock_alerts = [date.fromisoformat(n["night"]) for n in wha_clock if n["flagged"]]

        feats_sleep = features_for(pid, sleep) if sleep else []
        wha_sleep = run_wha_detector(feats_sleep) if feats_sleep else []
        wha_sleep_alerts = [date.fromisoformat(n["night"]) for n in wha_sleep if n["flagged"]]

        ns = run_nightsignal(hr, steps)
        ns_alerts = [d for d, red in ns if red]

        case = labels.get(pid)
        all_nights = sorted(clock)
        row = {
            "pid": pid,
            "category": case.category if case else "unlabelled",
            "nights": len(all_nights),
            "usable_nights": sum(1 for f in feats_clock if f.usable),
            "has_sleep": bool(sleep),
            "sleep_nights": len(sleep),
            "wha_clock": score(wha_clock_alerts, case, all_nights),
            # Exactly what the detector computed, so a threshold sweep can vary the cut
            # points over the real numbers rather than rebuilding its own baselines.
            "per_night": wha_clock,
            "wha_sleep": score(wha_sleep_alerts, case, sorted(sleep)) if sleep else None,
            "nightsignal": score(ns_alerts, case, all_nights),
            # Nightly readings, so the sleep window and the clock window can be compared
            # on the same nights for the participants that have sleep staging.
            "rhr_clock": {
                f.night_date.isoformat(): f.rhr_bpm for f in feats_clock if f.rhr_bpm is not None
            },
            "rhr_sleep": {
                f.night_date.isoformat(): f.rhr_bpm for f in feats_sleep if f.rhr_bpm is not None
            },
            "symptom": case.symptom.isoformat() if case and case.symptom else None,
        }
        rows.append(row)
        print(
            f"[{i:>3}/{len(pids)}] {pid} {row['category']:<14} "
            f"nights={row['nights']:>3} usable={row['usable_nights']:>3} "
            f"wha_alerts={row['wha_clock']['n_alerts']:>3} "
            f"ns_alerts={row['nightsignal']['n_alerts']:>3}",
            flush=True,
        )

    RESULTS.write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")
    print(f"\nwrote {RESULTS}")
    print("Next: uv run python experiments/detection/cohort/report.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
