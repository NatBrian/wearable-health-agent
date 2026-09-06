"""The HTTP client the dashboard talks to, so no screen touches the application directly.

Method names and arguments deliberately mirror the service functions the dashboard used to
import. That keeps the screens readable and makes the boundary the only thing that changed.

Responses are parsed back into the same Pydantic models the service returns, so a screen
gets a typed object either way and a field rename cannot pass silently through JSON.

If this class is replaced by a React app calling the same endpoints, nothing behind it
moves. That is the point of it existing.
"""

from datetime import date, datetime
from typing import Any

import httpx

from wha.models import (
    EpisodeDetail,
    EpisodeSummary,
    NightDetail,
    NightPipeline,
    NightRow,
    PendingInteraction,
    PipelineNightRef,
    Settings,
    Subject,
    SubjectProfile,
    SystemStatus,
)

DEFAULT_BASE_URL = "http://127.0.0.1:8500"
DEFAULT_TIMEOUT = 120.0


class ApiUnavailable(RuntimeError):
    """The interface could not reach the application.

    Raised rather than returning empty results. A dashboard that silently renders nothing
    when the backend is down looks identical to one reporting that a person has no data,
    and in a health system those two must never look the same.
    """


class ApiClient:
    """Typed access to the HTTP boundary."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = client

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.base_url}{path}"
        try:
            if self._client is not None:
                response = self._client.request(method, url, timeout=self.timeout, **kwargs)
            else:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            raise ApiUnavailable(f"Could not reach the application at {url}: {exc}") from exc

        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise ApiUnavailable(f"{method} {path} failed: {response.status_code} {response.text}")
        return response.json()

    # ------------------------------------------------------------------ config

    def config(self) -> dict[str, Any]:
        """Thresholds and today's date. A screen must not hardcode either."""
        return self._request("GET", "/config") or {}

    def localise(self, moment: Any) -> datetime:
        """A UTC timestamp as a datetime in the subject's timezone.

        Returns a datetime, not a string. It replaced wha.clock.to_local, whose callers
        format the result themselves, and handing back a string turned every one of those
        into an AttributeError at render time. No test caught it because none rendered the
        status strip with a timestamp actually present.
        """
        raw = moment.isoformat() if hasattr(moment, "isoformat") else str(moment)
        result = self._request("GET", "/localise", params={"utc": raw})
        if not result:
            return moment
        return datetime.fromisoformat(str(result["local"]))

    # ---------------------------------------------------------------- subjects

    def list_subjects(self) -> list[Subject]:
        return [Subject.model_validate(row) for row in self._request("GET", "/subjects") or []]

    def delete_all_subject_data(self, subject_id: str) -> None:
        self._request("DELETE", f"/subjects/{subject_id}")

    # ------------------------------------------------------------------ status

    def get_system_status(self, subject_id: str) -> SystemStatus:
        return SystemStatus.model_validate(self._request("GET", f"/subjects/{subject_id}/status"))

    # ------------------------------------------------------------------ nights

    def list_nights(
        self,
        subject_id: str,
        start: date | None = None,
        end: date | None = None,
        days: int | None = None,
    ) -> list[NightRow]:
        """Nights in a window. With no dates, the application decides where it ends.

        A screen that computes the end from today's date hides any night dated later, and
        those exist whenever the watch is being simulated forward.
        """
        params: dict[str, str | int] = {}
        if start is not None:
            params["start"] = start.isoformat()
        if end is not None:
            params["end"] = end.isoformat()
        if days is not None:
            params["days"] = days
        rows = self._request("GET", f"/subjects/{subject_id}/nights", params=params)
        return [NightRow.model_validate(r) for r in rows or []]

    def get_night_detail(self, subject_id: str, night_date: date) -> NightDetail | None:
        raw = self._request("GET", f"/subjects/{subject_id}/nights/{night_date.isoformat()}")
        return NightDetail.model_validate(raw) if raw else None

    def get_night_pipeline(self, subject_id: str, night_date: date) -> NightPipeline:
        """Every step of one night, in the order it happened."""
        raw = self._request(
            "GET", f"/subjects/{subject_id}/nights/{night_date.isoformat()}/pipeline"
        )
        return NightPipeline.model_validate(raw)

    def list_pipeline_nights(self, subject_id: str, days: int = 60) -> list[PipelineNightRef]:
        """The nights the stepper can move between, and what each one concluded."""
        rows = self._request(
            "GET", f"/subjects/{subject_id}/pipeline/nights", params={"days": days}
        )
        return [PipelineNightRef.model_validate(r) for r in rows or []]

    # ---------------------------------------------------------------- episodes

    def list_episodes(self, subject_id: str) -> list[EpisodeSummary]:
        rows = self._request("GET", f"/subjects/{subject_id}/episodes")
        return [EpisodeSummary.model_validate(r) for r in rows or []]

    def get_episode(self, episode_id: str) -> EpisodeDetail | None:
        raw = self._request("GET", f"/episodes/{episode_id}")
        return EpisodeDetail.model_validate(raw) if raw else None

    def get_pending_interaction(self, subject_id: str) -> PendingInteraction | None:
        raw = self._request("GET", f"/subjects/{subject_id}/pending")
        return PendingInteraction.model_validate(raw) if raw else None

    def submit_answer(self, episode_id: str, answer: Any) -> None:
        self._request(
            "POST",
            f"/episodes/{episode_id}/answer",
            json={
                "probe_id": answer.probe_id,
                "option_id": answer.option_id,
                "free_text": answer.free_text,
                "declined": answer.declined,
            },
        )

    def submit_human_decision(
        self,
        episode_id: str,
        decision: str,
        edited_prose: str | None = None,
        rationale: str | None = None,
    ) -> None:
        self._request(
            "POST",
            f"/episodes/{episode_id}/review",
            json={
                "decision": decision,
                "edited_prose": edited_prose,
                "rationale": rationale,
            },
        )

    # ------------------------------------------------------------ conversation

    def get_conversation_sessions(
        self,
        subject_id: str,
        limit_turns: int = 400,
        since_night: date | None = None,
    ) -> list[dict[str, Any]]:
        """The conversation grouped into consultations, newest first.

        With `since_night`, only conversations from that night onward, so a screen showing
        one night does not show a conversation about a different one.
        """
        params: dict[str, str | int] = {"limit_turns": limit_turns}
        if since_night is not None:
            params["since_night"] = since_night.isoformat()
        rows = self._request("GET", f"/subjects/{subject_id}/conversation/sessions", params=params)
        return list(rows or [])

    def get_transcript(self, subject_id: str, limit: int = 40) -> list[dict[str, Any]]:
        return (
            self._request("GET", f"/subjects/{subject_id}/conversation", params={"limit": limit})
            or []
        )

    def send_message(
        self,
        subject_id: str,
        text: str,
        episode_id: str | None = None,
        episode_summary: str = "",
        age_years: int | None = None,
    ) -> dict[str, Any]:
        return (
            self._request(
                "POST",
                f"/subjects/{subject_id}/conversation",
                json={
                    "text": text,
                    "episode_id": episode_id,
                    "episode_summary": episode_summary,
                    "age_years": age_years,
                },
            )
            or {}
        )

    def get_urgency(self, subject_id: str) -> dict[str, Any]:
        return self._request("GET", f"/subjects/{subject_id}/urgency") or {}

    # --------------------------------------------------------------- handover

    def build_handover(self, subject_id: str, episode_id: str | None = None) -> dict[str, Any]:
        params = {"episode_id": episode_id} if episode_id else None
        return self._request("GET", f"/subjects/{subject_id}/handover", params=params) or {}

    # ------------------------------------------------------------------ audit

    def get_audit(
        self,
        subject_id: str,
        limit: int = 100,
        offset: int = 0,
        audit_filter: Any = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if audit_filter is not None:
            for field in (
                "episode_id",
                "actor",
                "operation",
                "safety_event",
                "since_utc",
                "until_utc",
            ):
                value = getattr(audit_filter, field, None)
                if value is not None:
                    params[field] = value.isoformat() if hasattr(value, "isoformat") else value
        return self._request("GET", f"/subjects/{subject_id}/audit", params=params) or {}

    def export_audit(self, audit_filter: Any, path: Any) -> str:
        """Fetch the record and write it where the caller asked.

        Where the file lands is the client's business. The application returns content,
        because a browser client cannot be handed a path on the server's disk.
        """
        params = {
            field: getattr(audit_filter, field)
            for field in ("episode_id", "actor", "operation", "safety_event")
            if getattr(audit_filter, field, None) is not None
        }
        result = self._request(
            "GET", f"/subjects/{audit_filter.subject_id}/audit/export", params=params
        )
        content = str(result["content"]) if result else ""
        from pathlib import Path as _Path

        _Path(path).write_text(content, encoding="utf-8")
        return content

    # --------------------------------------------------------------- settings

    def get_service_settings(self) -> Settings:
        return Settings.model_validate(self._request("GET", "/settings"))

    def update_settings(self, **kwargs: Any) -> Any:
        return self._request("POST", "/settings", json=kwargs)

    def acknowledge_urgency(self, subject_id: str) -> dict[str, Any]:
        raw = self._request("POST", f"/subjects/{subject_id}/urgency/acknowledged")
        return raw if isinstance(raw, dict) else {}

    def get_knowledge_provenance(self) -> dict[str, dict[str, str]]:
        raw = self._request("GET", "/knowledge/provenance")
        return raw if isinstance(raw, dict) else {}

    def get_safety_rule_provenance(self) -> list[dict[str, str]]:
        """Where each number in the deterministic safety floor came from."""
        return self._request("GET", "/knowledge/safety-provenance") or []

    def get_subject_profile(self, subject_id: str) -> SubjectProfile:
        raw = self._request("GET", f"/subjects/{subject_id}/profile")
        return SubjectProfile.model_validate(raw)

    def update_subject_profile(self, subject_id: str, **fields: Any) -> SubjectProfile:
        raw = self._request("POST", f"/subjects/{subject_id}/profile", json=fields)
        return SubjectProfile.model_validate(raw)

    def check_component(self, component: str, **overrides: Any) -> Any:
        """Probe a subsystem, optionally against values not yet saved."""
        from wha.models import ConnectionCheck

        raw = self._request(
            "POST",
            f"/diagnostics/{component}",
            json={k: v for k, v in overrides.items() if v is not None},
        )
        return ConnectionCheck.model_validate(raw) if raw else None

    # The audit screen was written against individual service functions. Rather than
    # rewrite the screen, the client offers the same shapes over the one audit endpoint,
    # which fetches the record once instead of five times.

    def query_audit(self, audit_filter: Any, limit: int = 100, offset: int = 0) -> list[Any]:
        """Takes an AuditFilter, matching the shape the audit screen already used."""
        from wha.models import AuditEventView

        rows = self.get_audit(
            audit_filter.subject_id, limit=limit, offset=offset, audit_filter=audit_filter
        ).get("events", [])
        return [AuditEventView.model_validate(r) for r in rows]

    def list_plain_records(self, subject_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """Plain-language entries. Dicts, matching what the service returns."""
        return list(self.get_audit(subject_id, limit=limit).get("plain", []))

    def count_audit_events(self, subject_id: str) -> int:
        return int(self.get_audit(subject_id, limit=1).get("count", 0))

    def verify_hash_chain(self, subject_id: str) -> tuple[bool, str | None]:
        body = self.get_audit(subject_id, limit=1)
        return bool(body.get("intact", False)), body.get("first_bad_event")

    def get_permitted_tool_names(self) -> list[str]:
        subject = self.config().get("configured_subject", "me")
        return list(self.get_audit(subject, limit=1).get("permitted_tools", []))

    def latest_urgency_reason(self, subject_id: str) -> str:
        return str(self.get_urgency(subject_id).get("reason", ""))

    def test_bridge_connection(self, **overrides: Any) -> Any:
        return self.check_component("bridge", **overrides)

    def test_llm_connection(self, **overrides: Any) -> Any:
        return self.check_component("llm", **overrides)

    def test_telegram_connection(self, **overrides: Any) -> Any:
        return self.check_component("telegram", **overrides)


_client: ApiClient | None = None


def get_client(base_url: str | None = None) -> ApiClient:
    """The shared client, built once per process."""
    global _client
    if _client is None or base_url is not None:
        import os

        _client = ApiClient(base_url=base_url or os.environ.get("WHA_API_URL", DEFAULT_BASE_URL))
    return _client
