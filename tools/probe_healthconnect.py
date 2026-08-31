"""
Health Connect bridge probe.

Answers one question: what is actually available, and how far back does it go?

PRIVACY: this script prints STRUCTURE ONLY. Field names, record counts, date
spans and gap counts. It never prints a health value or an absolute date, and writes nothing
to disk. The output is safe to paste into a chat or an issue.

Usage:
    export HC_TOKEN=...                                  # bearer token from the app
    python probe_healthconnect.py 192.168.1.42          # phone IP, default port 8787
    python probe_healthconnect.py 192.168.1.42 8787 30  # explicit port and days

The token is read from the HC_TOKEN environment variable. It is never written
to disk or committed.

Requires only the standard library.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone

DEFAULT_PORT = 8787
DEFAULT_DAYS = 30
TIMEOUT_S = 30

# Any key whose name looks like one of these is treated as a timestamp.
TIME_HINTS = ("time", "date", "start", "end", "instant", "timestamp")


def fetch(host: str, port: int, days: int):
    """Try the on-demand endpoint with a days window, then fall back."""
    attempts = [
        f"http://{host}:{port}/?days={days}",
        f"http://{host}:{port}/",
        f"http://{host}:{port}/latest",
    ]
    token = os.environ.get("HC_TOKEN", "").strip()
    if not token:
        print("  note: HC_TOKEN not set. Newer app versions require a bearer token.")
    for url in attempts:
        try:
            req = urllib.request.Request(url)
            if token:
                req.add_header("Authorization", f"Bearer {token}")
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
                body = r.read().decode("utf-8", errors="replace")
            print(f"  fetched OK: {url}  ({len(body):,} bytes)")
            return json.loads(body), url
        except urllib.error.URLError as e:
            print(f"  failed: {url}  ({e.reason})")
        except json.JSONDecodeError as e:
            print(f"  fetched but not valid JSON: {url}  ({e})")
    return None, None


def parse_ts(value):
    """Best-effort timestamp parse. Returns a datetime or None."""
    if isinstance(value, (int, float)):
        # Heuristic: seconds vs milliseconds since epoch.
        seconds = value / 1000.0 if value > 1e11 else float(value)
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (ValueError, OSError, OverflowError):
            return None
    if isinstance(value, str):
        text = value.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None
    return None


def timestamps_in(record):
    """Yield every plausible timestamp found in a flat-ish record."""
    if not isinstance(record, dict):
        return
    for key, value in record.items():
        if any(hint in key.lower() for hint in TIME_HINTS):
            ts = parse_ts(value)
            if ts is not None:
                yield ts


def summarise_records(name, records):
    """Print structure for one data type. Never prints a value."""
    print(f"\n  {name}")
    print(f"    records        : {len(records):,}")

    if not records:
        print("    STATUS         : EMPTY (type granted but no data present)")
        return

    field_counts = Counter()
    field_types = {}
    for rec in records:
        if isinstance(rec, dict):
            for key, value in rec.items():
                field_counts[key] += 1
                field_types.setdefault(key, type(value).__name__)

    stamps = sorted(ts for rec in records for ts in timestamps_in(rec))
    if stamps:
        first, last = stamps[0], stamps[-1]
        now = datetime.now(timezone.utc)
        # Inclusive day span: a range touching two calendar days spans 2 days.
        span_days = (last.date() - first.date()).days + 1
        distinct_days = len({ts.date() for ts in stamps})
        # Relative only. Absolute dates are not printed.
        print(f"    oldest record  : {(now - first).days} days ago")
        print(f"    newest record  : {(now - last).days} days ago")
        print(f"    span           : {span_days} days")
        print(f"    days with data : {distinct_days}")
        missing = max(0, span_days - distinct_days)
        pct = 100.0 * distinct_days / span_days if span_days else 0.0
        print(f"    days missing   : {missing}  ({pct:.0f}% coverage)")
    else:
        print("    timestamps     : none recognised (field naming differs)")

    print("    fields         :")
    for key, count in field_counts.most_common():
        coverage = 100.0 * count / len(records)
        print(f"        {key:<34} {field_types.get(key, '?'):<8} present in {coverage:5.1f}% of records")


def walk(payload):
    """Normalise the payload into {data_type_name: [records]}."""
    if isinstance(payload, dict):
        # Common shapes: {"heartRate": [...]}, or {"data": {...}}, or {"records": {...}}
        for wrapper in ("data", "records", "result", "payload"):
            if wrapper in payload and isinstance(payload[wrapper], (dict, list)):
                return walk(payload[wrapper])
        out = {}
        for key, value in payload.items():
            if isinstance(value, list):
                out[key] = value
            elif isinstance(value, dict):
                nested = walk(value)
                for nk, nv in nested.items():
                    out[f"{key}.{nk}"] = nv
        return out
    if isinstance(payload, list):
        return {"(root list)": payload}
    return {}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PORT
    days = int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_DAYS

    print("=" * 72)
    print("HEALTH CONNECT BRIDGE PROBE")
    print("Structure only. No health values are printed or stored.")
    print("=" * 72)
    print(f"\nTarget: {host}:{port}, requesting {days} days\n")

    payload, url = fetch(host, port, days)
    if payload is None:
        print("\nNo response. Check that:")
        print("  - the phone and this machine are on the same Wi-Fi")
        print("  - the app's local HTTP server is switched ON")
        print("  - the IP and port are right (the app displays both)")
        print("  - the phone is awake; Android Doze can suspend the server")
        sys.exit(2)

    groups = walk(payload)
    if not groups:
        print("\nResponse parsed but contained no recognisable record lists.")
        print("Top-level keys:", list(payload)[:40] if isinstance(payload, dict) else type(payload).__name__)
        sys.exit(3)

    print(f"\nData types returned: {len(groups)}")

    populated, empty = [], []
    for name in sorted(groups):
        (populated if groups[name] else empty).append(name)

    for name in sorted(groups):
        summarise_records(name, groups[name])

    print("\n" + "=" * 72)
    print("SUMMARY")
    print("=" * 72)
    print(f"\nPopulated types ({len(populated)}):")
    for n in populated:
        print(f"    {n}  ({len(groups[n]):,} records)")
    if empty:
        print(f"\nEmpty types ({len(empty)}) - granted but nothing written:")
        for n in empty:
            print(f"    {n}")

    print("\nThe question this answers: how far back does Health Connect go?")
    print("If the spans above are ~2-4 weeks, no Samsung export is needed.")
    print("If they are ~2 days, Samsung Health only began syncing recently.")
    print("\nThis output contains no health values and is safe to share.")


if __name__ == "__main__":
    main()
