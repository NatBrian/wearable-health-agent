#!/usr/bin/env python
"""Serve the demo film's mock watch, on its own state file.

Identical to `tools/mock_watch.py serve` except that it reads
`data/demo_film_state.json`, so the parked simulation's cursor in
`data/sim_state.json` is never touched.

    uv run python tools/demo_film/serve_watch.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("WHA_MOCK_STATE", str(REPO_ROOT / "data" / "demo_film_state.json"))
sys.path.insert(0, str(REPO_ROOT / "tools"))

from http.server import HTTPServer

from mock_watch import STATE_PATH, MockWatchHandler

if __name__ == "__main__":
    host, port = "127.0.0.1", 8788
    print(f"Mock watch for the demo film on http://{host}:{port}")
    print(f"State: {STATE_PATH}")
    HTTPServer((host, port), MockWatchHandler).serve_forever()
