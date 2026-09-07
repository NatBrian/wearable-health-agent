#!/usr/bin/env python
"""Receive a screenshot from the browser and write it into the repository.

    uv run python tools/demo_film/catch_still.py

The Telegram stills come from the operator's own logged-in browser, driven through
BrowserOS, which can capture a page but cannot write a file. This listens on a local port
and writes whatever is posted to it, so a capture taken in that browser lands in
`docs/demo/telegram/` next to everything else.

Deliberately dumb and deliberately local: it binds 127.0.0.1, accepts one field, and
writes PNGs under one directory. It is a courier, not a service.
"""

from __future__ import annotations

import base64
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "docs" / "demo" / "telegram"
HOST, PORT = "127.0.0.1", 8790
SAFE = re.compile(r"[^a-z0-9-]")


class Catcher(BaseHTTPRequestHandler):
    # HTTP/1.1 with a Content-Length on every reply. The first version defaulted to
    # HTTP/1.0, so the client waited for a connection close that a keep-alive fetch never
    # got, and a single threaded server then wedged behind that open socket: the second
    # post never reached the handler at all.
    protocol_version = "HTTP/1.1"

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            name = SAFE.sub("-", str(payload.get("name", "still")).lower())[:60] or "still"
            data = base64.b64decode(payload["data"])
        except Exception as e:  # noqa: BLE001
            body = str(e).encode("utf-8")
            self.send_response(400)
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        OUT.mkdir(parents=True, exist_ok=True)
        path = OUT / f"{name}.png"
        path.write_bytes(data)
        print(f"wrote {path}  ({len(data) // 1024} KiB)")

        body = str(path).encode("utf-8")
        self.send_response(200)
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

    def log_message(self, fmt: str, *args: object) -> None:
        pass


if __name__ == "__main__":
    print(f"catching stills on http://{HOST}:{PORT} into {OUT}")
    ThreadingHTTPServer((HOST, PORT), Catcher).serve_forever()
