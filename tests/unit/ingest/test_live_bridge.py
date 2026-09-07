"""Unit tests for the LiveBridge client."""

import httpx
import pytest

from wha.errors import SourceUnavailable
from wha.ingest import LiveBridge


def test_live_bridge_timeout_raises_source_unavailable() -> None:
    """Timeout during HTTP fetch raises SourceUnavailable."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    transport = httpx.MockTransport(handler)
    bridge = LiveBridge(host="127.0.0.1", port=8787, transport=transport)

    with pytest.raises(SourceUnavailable, match="timed out"):
        bridge.fetch("subj_live")


def test_live_bridge_never_logs_token() -> None:
    """Secret bearer token is never leaked into exception messages."""
    secret_token = "SUPER_SECRET_TOKEN_XYZ123"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "internal"})

    transport = httpx.MockTransport(handler)
    bridge = LiveBridge(host="127.0.0.1", port=8787, token=secret_token, transport=transport)

    with pytest.raises(SourceUnavailable) as exc_info:
        bridge.fetch("subj_live")

    msg = str(exc_info.value)
    assert secret_token not in msg
    assert "127.0.0.1:8787" in msg


def test_live_bridge_falls_back_through_paths() -> None:
    """Failed /?days=N falls back to / and /latest in order."""
    called_paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        called_paths.append(request.url.raw_path.decode())
        if request.url.raw_path == b"/latest":
            return httpx.Response(
                200,
                json={"app_version": "1.9.17", "steps": [], "heart_rate": []},
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    bridge = LiveBridge(host="127.0.0.1", port=8787, transport=transport)
    payload = bridge.fetch("subj_live", days=7)

    assert payload.source_kind == "live"
    assert "/?days=7" in called_paths[0]
    assert called_paths[1] == "/"
    assert called_paths[2] == "/latest"


def test_malformed_body_is_source_unavailable_not_crash() -> None:
    """Malformed non-JSON HTTP response raises SourceUnavailable rather than crashing."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>502 Bad Gateway</html>")

    transport = httpx.MockTransport(handler)
    bridge = LiveBridge(host="127.0.0.1", port=8787, transport=transport)

    with pytest.raises(SourceUnavailable, match="malformed JSON"):
        bridge.fetch("subj_live")
