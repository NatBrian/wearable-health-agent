#!/usr/bin/env python
"""A mock Health Connect bridge that speaks the same HTTP protocol as the phone.

The point of this tool is to let a full production run continue past the nights the
real watch actually recorded, without any part of `src/wha` behaving differently.

`LiveBridge` fetches by GET http://host:port/?days=N and expects a Health Connect JSON
object back. `Synthetic` already generates exactly that object. So this server sits at a
local address, `WHA_BRIDGE_URL` points at it, and every downstream stage -- normalise,
nightly features, baseline, Chronos, detection, belief, policy, the agent graph and
Telegram -- runs unmodified, storing rows with source_kind "live".

Three commands matter:

    python tools/mock_watch.py serve                  # terminal 1, leave running
    python tools/mock_watch.py init --cursor 2026-09-03
    python tools/mock_watch.py day --scenario illness # one simulated day

State lives in data/sim_state.json so the cursor survives between invocations.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from wha.ingest.synthetic import Synthetic  # noqa: E402
from wha.models import Scenario  # noqa: E402

# The cursor survives between invocations here. `WHA_MOCK_STATE` lets a second timeline
# run without trampling the first: the parked simulation owns data/sim_state.json, and the
# demo film owns its own file. Unset, this is exactly what it always was.
STATE_PATH = Path(
    os.environ.get("WHA_MOCK_STATE") or (REPO_ROOT / "data" / "sim_state.json")
)

# The synthetic generator anchors its window at a UTC instant and works backwards.
# 08:00 UTC is 16:00 in Singapore, safely after the night it labels, so the night of
# the cursor date is complete in the payload.
ANCHOR_HOUR_UTC = 8

# `day --scenario X` attaches one of these to the day it advances to.
#
# The illness amplitudes are MEASURED, not guessed. The generator rounds every minute to a
# whole bpm, so an amplitude does not arrive intact in the nightly RHR: against a mature
# 61.35 bpm baseline, 4.6 moves RHR 61 -> 65 for a 3.65 bpm residual, which is below
# DETECT_RED_BPM = 4.0. That is the same arithmetic plan/docs/DISCLOSURES.md records for the
# no-response-timeout fixture. `flagged` additionally needs DETECT_PERSISTENCE_NIGHTS = 2
# consecutive elevated nights with at least one RED among them, so an amplitude that only
# ever reaches YELLOW opens no episode and the agent never runs.
#
# Swept on a 39-day window at base_bpm 60.0, seed 7, reading the residual and level of the
# onset night and the four that follow:
#
#   4.6  Y  Y  Y  G  G      never flagged
#   5.0  R  R* Y* G  G      flags on night 2
#   5.4  R  R* R* Y* G      flags on night 2, three RED nights, then recovery
#   6.6  R  R* R* R* G      more severe
#
# alcohol, stress and exercise keep the generator's own defaults, which are derived from
# data/knowledge/causes.yaml. They are deliberately too small to flag on their own: a
# benign cause that raised an alert by itself would be a false positive.
SCENARIOS: dict[str, dict[str, Any] | None] = {
    "healthy": None,
    "illness": {"kind": "illness", "amplitude_bpm": 5.4},
    "severe-illness": {"kind": "illness", "amplitude_bpm": 6.6},
    "mild-illness": {"kind": "illness", "amplitude_bpm": 5.0},
    "subclinical": {"kind": "illness", "amplitude_bpm": 4.6},
    "alcohol": {"kind": "alcohol", "amplitude_bpm": 2.6},
    "stress": {"kind": "stress", "amplitude_bpm": 1.5},
    "exercise": {"kind": "exercise", "amplitude_bpm": 4.14, "end_offset_h": 1.5},
    "nonwear": {"kind": "nonwear", "nights": 1},
}


# ----------------------------------------------------------------------------- state


def default_state(cursor: date, subject: str) -> dict[str, Any]:
    return {
        "subject": subject,
        "cursor": cursor.isoformat(),
        "window_days": 35,
        "base_bpm": 60.0,
        "seed": 7,
        "timezone": "Asia/Singapore",
        "events": [],
    }


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        raise SystemExit(
            f"No simulation state at {STATE_PATH}.\n"
            "Run:  python tools/mock_watch.py init --cursor YYYY-MM-DD"
        )
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


# ------------------------------------------------------------------- payload building


def first_night(state: dict[str, Any], days: int) -> date:
    """The earliest night date present in a payload of `days` days."""
    return date.fromisoformat(state["cursor"]) - timedelta(days=days - 1)


def build_scenario(state: dict[str, Any], days: int) -> Scenario:
    """Translate calendar-dated events into the generator's day-index injections.

    A negative start_day is deliberate and correct: an event that began before the window
    still has a tail, and the generator's temporal profiles decay to zero on their own.
    """
    base = first_night(state, days)
    injections: list[dict[str, Any]] = []
    for ev in state["events"]:
        ev_date = date.fromisoformat(ev["date"])
        inj = {k: v for k, v in ev.items() if k != "date"}
        inj["start_day"] = (ev_date - base).days
        inj["day"] = inj["start_day"]  # the generator reads one or the other by kind
        injections.append(inj)

    return Scenario(
        name="mock-watch",
        description="Mock Health Connect bridge serving a moving window of synthetic days.",
        days=days,
        base_bpm=float(state["base_bpm"]),
        seed=int(state["seed"]),
        timezone=state["timezone"],
        injections=injections,
    )


def build_body(state: dict[str, Any], days: int) -> dict[str, Any]:
    cursor = date.fromisoformat(state["cursor"])
    anchor = datetime(cursor.year, cursor.month, cursor.day, ANCHOR_HOUR_UTC, tzinfo=UTC)
    scenario = build_scenario(state, days)
    payload = Synthetic(scenario=scenario, anchor=anchor).fetch(state["subject"])
    return payload.body


# ------------------------------------------------------------------------ http server


class MockWatchHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path not in ("/", "/latest"):
            self.send_error(404, "mock watch serves / and /latest only")
            return

        try:
            state = load_state()
        except SystemExit as e:
            self.send_error(503, str(e))
            return

        qs = parse_qs(parsed.query)
        days = int(qs.get("days", [state["window_days"]])[0])

        # Never serve more than the watch is holding, whatever the caller asks for. A real
        # phone can only hand over what Health Connect has; asking it for thirty days when
        # it holds one does not conjure the other twenty-nine.
        #
        # This mattered. The scheduler's catch-up ingest asks for thirty days regardless of
        # the mock's window, so a mock configured to serve a single night happily generated
        # a month of synthetic nights and overwrote real readings that had been carried
        # into the subject. Working around it by running the system with --no-scheduler
        # then disabled Telegram polling, so a message sent from the phone was never
        # collected and the person got no reply. Clamping here fixes both.
        days = max(1, min(days, int(state["window_days"]), 400))

        body = build_body(state, days)
        raw = json.dumps(body).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

        nights = f"{first_night(state, days)}..{state['cursor']}"
        auth = "with token" if self.headers.get("Authorization") else "no token"
        sys.stderr.write(
            f"[mock-watch] served {days} days ({nights}) "
            f"{len(body['heart_rate'])} hr samples, {len(raw) // 1024} KiB, {auth}\n"
        )

    def log_message(self, fmt: str, *args: Any) -> None:
        pass  # the do_GET line above is the log we want


def cmd_serve(args: argparse.Namespace) -> int:
    server = HTTPServer((args.host, args.port), MockWatchHandler)
    print(f"Mock watch bridge listening on http://{args.host}:{args.port}")
    print("Point WHA_BRIDGE_URL at that address, then run `wha ingest`.")
    if STATE_PATH.exists():
        state = load_state()
        print(f"Cursor {state['cursor']}, subject {state['subject']}, {len(state['events'])} events")
    else:
        print(f"No state yet at {STATE_PATH}; run `init` before ingesting.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMock watch stopped.")
    return 0


# --------------------------------------------------------------------------- commands


def cmd_init(args: argparse.Namespace) -> int:
    cursor = date.fromisoformat(args.cursor) if args.cursor else datetime.now().date()
    state = default_state(cursor, args.subject)
    state["window_days"] = args.window
    state["base_bpm"] = args.base_bpm
    state["seed"] = args.seed
    save_state(state)
    print(f"Initialised {STATE_PATH}")
    print_status(state)
    return 0


def print_status(state: dict[str, Any]) -> None:
    days = state["window_days"]
    print(f"  subject      {state['subject']}")
    print(f"  cursor       {state['cursor']}  (latest night the watch has recorded)")
    print(f"  window       {days} days -> {first_night(state, days)} .. {state['cursor']}")
    print(f"  base bpm     {state['base_bpm']}   seed {state['seed']}")
    if state["events"]:
        print("  events")
        for ev in sorted(state["events"], key=lambda e: e["date"]):
            extra = ", ".join(f"{k}={v}" for k, v in ev.items() if k not in ("date", "kind"))
            print(f"    {ev['date']}  {ev['kind']:<10} {extra}")
    else:
        print("  events       none (healthy throughout)")


def cmd_status(args: argparse.Namespace) -> int:
    print_status(load_state())
    return 0


def cmd_event(args: argparse.Namespace) -> int:
    state = load_state()
    ev: dict[str, Any] = {"date": date.fromisoformat(args.date).isoformat(), "kind": args.kind}
    if args.amplitude is not None:
        ev["amplitude_bpm"] = args.amplitude
    if args.nights is not None:
        ev["nights"] = args.nights
    state["events"].append(ev)
    save_state(state)
    print(f"Added {args.kind} on {ev['date']}")
    print_status(state)
    return 0


def cmd_day(args: argparse.Namespace) -> int:
    state = load_state()
    cursor = date.fromisoformat(state["cursor"])
    target = date.fromisoformat(args.to) if args.to else cursor + timedelta(days=1)
    if target <= cursor:
        raise SystemExit(f"Cursor is already at {cursor}; --to must be later.")

    if args.scenario:
        preset = SCENARIOS[args.scenario]
        if preset is not None:
            ev = dict(preset)
            ev["date"] = target.isoformat()
            state["events"].append(ev)

    state["cursor"] = target.isoformat()
    save_state(state)

    span = (target - cursor).days
    print(f"=== Simulated watch advanced {span} day(s): {cursor} -> {target} ===")
    if args.scenario:
        print(f"    scenario on {target}: {args.scenario}")
    print()

    if args.no_run:
        print("--no-run: cursor moved, pipeline not invoked.")
        return 0

    return run_pipeline(state, start=cursor + timedelta(days=1), end=target)


def run_pipeline(state: dict[str, Any], start: date, end: date) -> int:
    """Run exactly what the scheduler runs: ingest, nightly, then step open episodes."""
    from wha.service.ingest import run_ingest
    from wha.service.nightly import run_nightly
    from wha.service.scheduler import run_episode_tick

    subject = state["subject"]

    print("--- ingest (live path, via the mock bridge) ---")
    stored = run_ingest(subject_id=subject, days=state["window_days"])
    print(f"stored/normalised {stored} heart rate samples\n")

    print(f"--- nightly {start} .. {end} ---")
    dets = run_nightly(
        subject_id=subject,
        date_or_range=f"{start.isoformat()}:{end.isoformat()}",
        no_ingest=True,
    )
    for d in dets:
        residual = f"{d.residual_bpm:+.2f} bpm" if d.residual_bpm is not None else "n/a"
        print(f"{d.night_date} | {d.level:<6} | flagged {str(d.flagged):<5} | residual {residual}")
    print()

    print("--- episode tick ---")
    result = run_episode_tick()
    print(json.dumps(result, default=str, indent=2))
    return 0


def cmd_backfill(args: argparse.Namespace) -> int:
    """Process the whole on-device window at once, the way a first sync would.

    `day` only runs nightly for the days it advanced, which is right once history exists.
    On an empty database there is no history, so every night would be scored against the
    population prior instead of a personal baseline. This command builds that history.
    """
    state = load_state()
    days = state["window_days"]
    start = first_night(state, days)
    end = date.fromisoformat(state["cursor"])
    print(f"=== First sync: processing the full on-device window {start} .. {end} ===\n")
    return run_pipeline(state, start=start, end=end)


def cmd_reset(args: argparse.Namespace) -> int:
    if STATE_PATH.exists():
        STATE_PATH.unlink()
        print(f"Removed {STATE_PATH}")
    else:
        print("No state file to remove.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__ or "")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("serve", help="Run the mock Health Connect bridge")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=int(os.environ.get("WHA_MOCK_WATCH_PORT", 8788)))
    p.set_defaults(fn=cmd_serve)

    p = sub.add_parser("init", help="Create the simulation state file")
    p.add_argument("--subject", default=os.environ.get("WHA_SUBJECT", "me"))
    p.add_argument("--cursor", help="Latest night the watch has recorded (YYYY-MM-DD)")
    p.add_argument("--window", type=int, default=35, help="Days the watch keeps on device")
    p.add_argument("--base-bpm", type=float, default=60.0)
    p.add_argument("--seed", type=int, default=7)
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("status", help="Show the cursor and scheduled events")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("event", help="Schedule an event on a specific date")
    p.add_argument("--kind", required=True, choices=["illness", "alcohol", "stress", "exercise", "nonwear"])
    p.add_argument("--date", required=True)
    p.add_argument("--amplitude", type=float, default=None)
    p.add_argument("--nights", type=int, default=None)
    p.set_defaults(fn=cmd_event)

    p = sub.add_parser("day", help="Advance the watch and run the pipeline")
    p.add_argument("--scenario", choices=sorted(SCENARIOS), default=None)
    p.add_argument("--to", help="Advance straight to this date instead of one day")
    p.add_argument("--no-run", action="store_true", help="Move the cursor only")
    p.set_defaults(fn=cmd_day)

    p = sub.add_parser("backfill", help="Ingest and score the entire on-device window")
    p.set_defaults(fn=cmd_backfill)

    p = sub.add_parser("reset", help="Delete the simulation state file")
    p.set_defaults(fn=cmd_reset)

    args = parser.parse_args()
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
