"""Live bridge client connecting to Health Connect HTTP server."""

import hashlib
import json
import os
from datetime import UTC, datetime

import httpx

from wha.errors import SourceUnavailable
from wha.models import RawPayload


class LiveBridge:
    """DataSource connecting to the Android Health Connect bridge over HTTP."""

    source_kind = "live"

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        token: str | None = None,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.host = host or os.environ.get("WHA_BRIDGE_HOST", "127.0.0.1")
        port_env = os.environ.get("WHA_BRIDGE_PORT")
        self.port = int(port if port is not None else (port_env if port_env else 8787))
        self.token = token if token is not None else os.environ.get("WHA_BRIDGE_TOKEN")
        self.timeout = timeout
        self.transport = transport

    def fetch(self, subject_id: str, days: int = 30) -> RawPayload:
        """Fetch payload attempting fallback paths in order: /?days=N, /, /latest."""
        attempts = [
            f"http://{self.host}:{self.port}/?days={days}",
            f"http://{self.host}:{self.port}/",
            f"http://{self.host}:{self.port}/latest",
        ]

        headers: dict[str, str] = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        last_error_detail: str = "all fallback paths failed"
        with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
            for url in attempts:
                try:
                    resp = client.get(url, headers=headers)
                    if resp.status_code == 200:
                        try:
                            body = resp.json()
                        except Exception as e:
                            raise SourceUnavailable(
                                f"Bridge at {self.host}:{self.port} returned malformed JSON"
                            ) from e

                        if not isinstance(body, dict):
                            raise SourceUnavailable(
                                f"Bridge at {self.host}:{self.port} returned non-object JSON"
                            )

                        canonical_text = json.dumps(body, sort_keys=True, separators=(",", ":"))
                        sha256 = hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()
                        now = datetime.now(UTC)

                        return RawPayload(
                            subject_id=subject_id,
                            source_kind="live",
                            fetched_at_utc=now,
                            sha256=sha256,
                            body=body,
                        )
                    else:
                        last_error_detail = f"status code {resp.status_code}"
                except httpx.TimeoutException as e:
                    raise SourceUnavailable(
                        f"Bridge at {self.host}:{self.port} timed out after {self.timeout}s"
                    ) from e
                except httpx.RequestError as e:
                    last_error_detail = f"connection error ({type(e).__name__})"

        raise SourceUnavailable(f"Bridge at {self.host}:{self.port} failed: {last_error_detail}")
