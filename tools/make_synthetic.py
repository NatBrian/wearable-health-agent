"""
Synthetic Health Connect bridge payload.

Produces JSON in the exact shape the real bridge returns, so code written
against this will work unchanged against the phone.

SCHEMA OBSERVED FROM THE REAL DEVICE (2026-08-31, app v1.9.17):

    {
      "app_version": "1.9.17",
      "timestamp":   "2026-08-31T08:57:07.430Z",
      "steps": [
        {"count": 2594,
         "start_time": "2026-08-29T16:00:00Z",
         "end_time":   "2026-08-30T16:00:00Z"}
      ],
      "heart_rate": [
        {"time": "2026-08-30T16:33:00Z",
         "avg": 90, "min": 90, "max": 90,
         "metadata": {"data_origin": "com.sec.android.app.shealth",
                      "recording_method": "unknown",
                      "device": {"type": 0}}}
      ]
    }

Notes on the real payload:
  - Timestamps are ISO 8601, UTC, with a trailing Z.
  - Step buckets are daily and align to local midnight. The device is on
    UTC+8, so buckets run 16:00Z to 16:00Z.
  - Heart rate arrives in 1-minute buckets with avg/min/max.
  - The live payload repeats the "app_version" key twice. That is an app
    quirk; JSON parsers keep the last one, so it is not reproduced here.

ONLY heart_rate AND steps ARE GENERATED. Those are the only two types the
real device has returned so far. Sleep, resting heart rate, HRV, respiratory
rate and SpO2 are not emitted, because their real shape has not been seen
yet and inventing it would defeat the point of this file.

Usage:
    python make_synthetic.py --days 30 > sample.json
    python make_synthetic.py --days 30 --elevate-last 3 --elevate-bpm 5
"""

import argparse
import json
import math
import random
from datetime import datetime, timedelta, timezone

DATA_ORIGIN = "com.sec.android.app.shealth"
APP_VERSION = "1.9.17"
UTC_OFFSET_HOURS = 8  # device local time, used to align daily step buckets


def iso(dt):
    """ISO 8601 in UTC with a trailing Z, matching the bridge."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resting_bpm(hour, base):
    """A plain circadian shape: lowest around 04:00, highest late afternoon."""
    return base + 12.0 * math.sin((hour - 10.0) / 24.0 * 2 * math.pi)


def make_heart_rate(start, days, base_bpm, elevate_from, elevate_bpm, rng):
    """One record per minute, 24h a day, with a few non-wear gaps."""
    out = []
    for minute in range(days * 24 * 60):
        t = start + timedelta(minutes=minute)

        # Non-wear: skip a two-hour charging window most evenings.
        if t.hour == 21 and rng.random() < 0.7:
            continue

        offset = elevate_bpm if elevate_from is not None and t >= elevate_from else 0.0
        centre = resting_bpm(t.hour + t.minute / 60.0, base_bpm) + offset
        avg = int(round(rng.gauss(centre, 3.0)))
        spread = rng.randint(0, 4)

        out.append({
            "time": iso(t),
            "avg": avg,
            "min": avg - spread,
            "max": avg + spread,
            "metadata": {
                "data_origin": DATA_ORIGIN,
                "recording_method": "unknown",
                "device": {"type": 0},
            },
        })
    return out


def make_steps(start, days, rng):
    """One record per local day, bucketed 16:00Z to 16:00Z for UTC+8."""
    out = []
    midnight = start.replace(hour=0, minute=0, second=0, microsecond=0)
    bucket_start = midnight - timedelta(hours=UTC_OFFSET_HOURS)
    for _ in range(days):
        out.append({
            "count": rng.randint(1500, 12000),
            "start_time": iso(bucket_start),
            "end_time": iso(bucket_start + timedelta(days=1)),
        })
        bucket_start += timedelta(days=1)
    return out


def build(days, base_bpm, elevate_last, elevate_bpm, seed):
    rng = random.Random(seed)
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    start = now - timedelta(days=days)
    elevate_from = now - timedelta(days=elevate_last) if elevate_last else None

    return {
        "app_version": APP_VERSION,
        "timestamp": iso(now),
        "steps": make_steps(start, days, rng),
        "heart_rate": make_heart_rate(start, days, base_bpm, elevate_from, elevate_bpm, rng),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--days", type=int, default=30, help="days of history (default 30)")
    p.add_argument("--base-bpm", type=float, default=62.0, help="personal baseline (default 62)")
    p.add_argument("--elevate-last", type=int, default=0,
                   help="raise heart rate over the final N days, to simulate a deviation")
    p.add_argument("--elevate-bpm", type=float, default=4.0,
                   help="size of that rise in bpm (default 4, the published detection threshold)")
    p.add_argument("--seed", type=int, default=1, help="random seed (default 1)")
    args = p.parse_args()

    payload = build(args.days, args.base_bpm, args.elevate_last, args.elevate_bpm, args.seed)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
