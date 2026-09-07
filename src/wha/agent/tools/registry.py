"""Agent tool registry, execution harness, and common result shape."""

import json
import time
import uuid
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from wha.clock import local_date_of, local_today, now_utc
from wha.errors import PermissionDenied
from wha.models import AuditEvent, ControlTier

TOOL_MAX_RANGE_DAYS: int = 90
MAX_AUDIT_VALUE_CHARS: int = 500

CLOSED_TOOL_REGISTRY: set[str] = {
    "get_nightly_features",
    "get_personal_baseline",
    "get_known_events",
    "get_data_quality",
    "find_similar_past_episodes",
    "retrieve_clinical_evidence",
}


# What each tool is for and what it takes. The model was told the tool names and nothing
# else, so it guessed argument names: a production run recorded
# `retrieve_clinical_evidence({"symptom": "fever"})` against a handler that reads `query`,
# which returned an empty list, reported ok, and left the episode with no citations. A tool
# the model cannot call correctly is no more use than one that does not exist.
#
# subject_id is deliberately absent from every signature. The registry strips any
# model-supplied subject and uses the one the episode was opened for.
TOOL_SIGNATURES: dict[str, str] = {
    "get_nightly_features": (
        'get_nightly_features(start: "YYYY-MM-DD", end: "YYYY-MM-DD") '
        "-> the nightly readings, coverage and sleep hours in that range"
    ),
    "get_personal_baseline": (
        'get_personal_baseline(night_date: "YYYY-MM-DD") '
        "-> the person's own centre and band on that night, and how mature it is"
    ),
    "get_known_events": (
        'get_known_events(start: "YYYY-MM-DD", end: "YYYY-MM-DD") '
        "-> workouts, steps, blood oxygen and other recorded context in that range"
    ),
    "get_data_quality": (
        'get_data_quality(start: "YYYY-MM-DD", end: "YYYY-MM-DD") '
        "-> coverage minutes and implausible readings dropped, for judging sensor artifact"
    ),
    "find_similar_past_episodes": (
        "find_similar_past_episodes() -> this person's earlier investigations and how they ended"
    ),
    "retrieve_clinical_evidence": (
        'retrieve_clinical_evidence(query: "free text", layer: int optional) '
        "-> passages from the local clinical corpus. THE ARGUMENT IS `query`. "
        'Put the symptom or cause in it, for example {"query": "fever"}'
    ),
}


def describe_tools(names: list[str]) -> str:
    """The catalogue handed to the model: one line per tool, name and arguments."""
    return "\n".join(f"- {TOOL_SIGNATURES[n]}" for n in sorted(names) if n in TOOL_SIGNATURES)


class ToolResult(BaseModel):
    """Common result shape for all T1 tools."""

    model_config = ConfigDict(frozen=True)

    tool_name: str
    args: dict[str, Any]
    ok: bool
    value: Any  # a typed model, never a raw row
    source_ids: list[str] = Field(default_factory=list)
    as_of_utc: datetime
    freshness: Literal["fresh", "stale", "missing"]
    note: str | None = None


class ToolContext(BaseModel):
    """Execution context injected by the runtime for tool invocations."""

    model_config = ConfigDict(frozen=False)

    subject_id: str
    episode_id: str | None = None
    step_index: int | None = None
    now_utc: datetime = Field(default_factory=now_utc)
    tool_call_count: int = 0
    expansion_attempts: int = 0
    audit_events: list[AuditEvent] = Field(default_factory=list)


HandlerFunc = Callable[[dict[str, Any], ToolContext, Any], ToolResult]


def format_tool_result_for_audit(
    result: ToolResult, max_chars: int = MAX_AUDIT_VALUE_CHARS
) -> dict[str, Any]:
    """Serialize tool result for audit logging with visible truncation for large payloads."""
    raw_str = str(result.value)
    truncated = False
    if len(raw_str) > max_chars:
        raw_str = raw_str[:max_chars] + "... [TRUNCATED]"
        truncated = True

    return {
        "ok": result.ok,
        "source_ids": result.source_ids,
        "freshness": result.freshness,
        "truncated": truncated,
        "preview": raw_str,
    }


class ToolRegistry:
    """Closed registry of T1 read-only tools with runtime injection and per-episode cache."""

    def __init__(self) -> None:
        self._handlers: dict[str, HandlerFunc] = {}
        self._episode_caches: dict[str, dict[str, ToolResult]] = {}

    def register(self, name: str, handler: HandlerFunc) -> None:
        """Register a handler for a closed registry tool name."""
        if name not in CLOSED_TOOL_REGISTRY:
            raise PermissionDenied(
                f"Cannot register '{name}': outside closed T1 tool specification."
            )
        self._handlers[name] = handler

    def clear_episode_cache(self, episode_id: str) -> None:
        """Clear cache when an episode concludes."""
        self._episode_caches.pop(episode_id, None)

    def list_tools(self) -> list[str]:
        """Return list of registered tool names."""
        return list(self._handlers.keys())

    def invoke(
        self,
        tool_name: str,
        raw_args: dict[str, Any],
        context: ToolContext,
        db: Any = None,
    ) -> ToolResult:
        """Invoke a tool with subject_id injection, clamping, caching, and audit logging."""
        now = context.now_utc
        episode_id = context.episode_id or "default"

        # Every attempt costs budget, including a refused one. The investigate loop
        # terminates only when this counter reaches its ceiling, so charging solely for
        # successful calls let a model that keeps requesting an unregistered tool spin
        # forever, issuing unbounded LLM calls that the budget never bounded.
        context.tool_call_count += 1

        # 1. Closed Registry Enforcement
        if tool_name not in CLOSED_TOOL_REGISTRY:
            # Audit denied attempt
            event = AuditEvent(
                event_id=f"aud_{uuid.uuid4().hex[:12]}",
                subject_id=context.subject_id,
                episode_id=context.episode_id,
                step_index=context.step_index,
                timestamp_utc=now,
                actor="agent",
                operation="execute_tool",
                control_tier=ControlTier.T1,
                tool_name=tool_name,
                tool_args=raw_args,
                permission_decision="denied",
            )
            context.audit_events.append(event)
            if db is not None and hasattr(db, "append_audit"):
                db.append_audit(event)

            raise PermissionDenied(
                f"Tool '{tool_name}' is not permitted. Registry is closed to non-T1 tools."
            )

        # 2. Subject ID injection: Model-supplied subject_id is stripped and logged
        args = dict(raw_args)
        if "subject_id" in args:
            attempted_id = args.pop("subject_id")
            if attempted_id != context.subject_id:
                context.expansion_attempts += 1

        # 3. Date range clamping to at most 90 days and not in the future
        clamp_note: str | None = None
        today = local_date_of(now) if isinstance(now, datetime) else local_today()

        start_val = args.get("start") or args.get("start_date")
        end_val = args.get("end") or args.get("end_date")

        if start_val is not None and end_val is not None:
            try:
                start_d = (
                    date.fromisoformat(str(start_val)) if isinstance(start_val, str) else start_val
                )
                end_d = date.fromisoformat(str(end_val)) if isinstance(end_val, str) else end_val

                if end_d > today:
                    end_d = today
                    clamp_note = f"End date clamped to today ({today.isoformat()})."

                if (end_d - start_d).days > TOOL_MAX_RANGE_DAYS:
                    start_d = end_d - timedelta(days=TOOL_MAX_RANGE_DAYS)
                    clamp_note = (
                        f"Range exceeded {TOOL_MAX_RANGE_DAYS} days; "
                        f"clamped start to {start_d.isoformat()}."
                    )

                if "start" in args:
                    args["start"] = start_d.isoformat()
                if "start_date" in args:
                    args["start_date"] = start_d.isoformat()
                if "end" in args:
                    args["end"] = end_d.isoformat()
                if "end_date" in args:
                    args["end_date"] = end_d.isoformat()
            except (ValueError, TypeError):
                pass

        # 5. Caching within the same episode
        cache_key = f"{tool_name}:{json.dumps(args, sort_keys=True)}"
        episode_cache = self._episode_caches.setdefault(episode_id, {})

        if cache_key in episode_cache:
            cached_result = episode_cache[cache_key]
            # Write audit row for cached access
            event = AuditEvent(
                event_id=f"aud_{uuid.uuid4().hex[:12]}",
                subject_id=context.subject_id,
                episode_id=context.episode_id,
                step_index=context.step_index,
                timestamp_utc=now,
                actor="agent",
                operation="execute_tool",
                control_tier=ControlTier.T1,
                tool_name=tool_name,
                tool_args=args,
                tool_result={"cached": True, "source_ids": cached_result.source_ids},
                permission_decision="allowed",
            )
            context.audit_events.append(event)
            if db is not None and hasattr(db, "append_audit"):
                db.append_audit(event)
            return cached_result

        # 6. Handler Execution
        handler = self._handlers.get(tool_name)
        if handler is None:
            # Default stub result if handler not registered yet
            result = ToolResult(
                tool_name=tool_name,
                args=args,
                ok=True,
                value={},
                source_ids=[f"stub_{tool_name}"],
                as_of_utc=now,
                freshness="fresh",
                note=clamp_note,
            )
            latency_ms = None
        else:
            t0 = time.perf_counter()
            result = handler(args, context, db)
            # Measured here and then discarded into a name with a leading underscore, so
            # AuditEvent.latency_ms was always None and the record could not say how long
            # anything took. On the page whose purpose is to show what the system did.
            latency_ms = int((time.perf_counter() - t0) * 1000)
            if clamp_note:
                result = result.model_copy(
                    update={"note": f"{result.note}; {clamp_note}" if result.note else clamp_note}
                )

        # Store in cache
        episode_cache[cache_key] = result

        # 7. Write Audit Row
        event = AuditEvent(
            event_id=f"aud_{uuid.uuid4().hex[:12]}",
            subject_id=context.subject_id,
            episode_id=context.episode_id,
            step_index=context.step_index,
            timestamp_utc=now,
            actor="agent",
            operation="execute_tool",
            control_tier=ControlTier.T1,
            tool_name=tool_name,
            tool_args=args,
            tool_result=format_tool_result_for_audit(result),
            permission_decision="allowed",
            latency_ms=latency_ms,
        )
        context.audit_events.append(event)
        if db is not None and hasattr(db, "append_audit"):
            db.append_audit(event)

        return result
