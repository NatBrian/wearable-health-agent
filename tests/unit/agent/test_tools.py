"""Unit tests for tool registry, security injection, caching, clamping, and audit trails."""

from datetime import UTC, date, datetime

import pytest

from wha.agent.tools import ToolContext, ToolRegistry, ToolResult
from wha.errors import PermissionDenied
from wha.models import ControlTier


def test_registry_is_closed() -> None:
    """Invoking an unregistered or arbitrary tool name raises PermissionDenied."""
    registry = ToolRegistry()
    context = ToolContext(subject_id="sub_001")

    with pytest.raises(PermissionDenied):
        registry.invoke("open_web_search", {"query": "symptoms"}, context)

    with pytest.raises(PermissionDenied):
        registry.invoke("execute_shell", {"command": "dir"}, context)

    # Audited as denied
    assert len(context.audit_events) == 2
    assert all(e.permission_decision == "denied" for e in context.audit_events)


def test_subject_id_is_injected_not_supplied() -> None:
    """Model cannot supply a different subject_id; runtime subject_id is strictly used."""
    registry = ToolRegistry()
    context = ToolContext(subject_id="sub_legit")

    captured_args = {}

    def mock_handler(args, ctx, db):
        captured_args.update(args)
        return ToolResult(
            tool_name="get_nightly_features",
            args=args,
            ok=True,
            value={},
            as_of_utc=datetime.now(UTC),
            freshness="fresh",
        )

    registry.register("get_nightly_features", mock_handler)
    res = registry.invoke(
        "get_nightly_features",
        {"subject_id": "sub_attacker", "start": "2026-08-01", "end": "2026-08-10"},
        context,
    )

    assert res.ok is True
    # subject_id was stripped from args passed to handler
    assert "subject_id" not in captured_args
    assert context.expansion_attempts == 1


def test_cross_subject_access_impossible() -> None:
    """Tool invocation is strictly locked to context.subject_id and logs any cross-subject attempts."""
    registry = ToolRegistry()
    context = ToolContext(subject_id="sub_target")

    registry.invoke(
        "get_personal_baseline",
        {"subject_id": "sub_victim", "night_date": "2026-08-01"},
        context,
    )

    assert context.expansion_attempts == 1
    assert context.audit_events[-1].subject_id == "sub_target"


def test_identical_call_is_cached() -> None:
    """Identical tool invocations within an episode reuse cached results without re-executing handler."""
    registry = ToolRegistry()
    context = ToolContext(subject_id="sub_001", episode_id="ep_001")

    call_count = 0

    def mock_handler(args, ctx, db):
        nonlocal call_count
        call_count += 1
        return ToolResult(
            tool_name="get_data_quality",
            args=args,
            ok=True,
            value={"call": call_count},
            as_of_utc=datetime.now(UTC),
            freshness="fresh",
        )

    registry.register("get_data_quality", mock_handler)

    res1 = registry.invoke(
        "get_data_quality", {"start": "2026-08-01", "end": "2026-08-05"}, context
    )
    res2 = registry.invoke(
        "get_data_quality", {"start": "2026-08-01", "end": "2026-08-05"}, context
    )

    assert call_count == 1
    assert res1.value == res2.value


def test_cached_call_still_increments_counter() -> None:
    """Even when cached, every tool invocation increments context.tool_call_count."""
    registry = ToolRegistry()
    context = ToolContext(subject_id="sub_001", episode_id="ep_001")

    registry.invoke("get_data_quality", {"start": "2026-08-01", "end": "2026-08-05"}, context)
    registry.invoke("get_data_quality", {"start": "2026-08-01", "end": "2026-08-05"}, context)
    registry.invoke("get_data_quality", {"start": "2026-08-01", "end": "2026-08-05"}, context)

    assert context.tool_call_count == 3


def test_range_clamped_to_90_days() -> None:
    """A date range exceeding 90 days is automatically clamped to 90 days with a note."""
    registry = ToolRegistry()
    context = ToolContext(
        subject_id="sub_001",
        now_utc=datetime(2026, 9, 1, tzinfo=UTC),
    )

    captured_args = {}

    def mock_handler(args, ctx, db):
        captured_args.update(args)
        return ToolResult(
            tool_name="get_nightly_features",
            args=args,
            ok=True,
            value={},
            as_of_utc=ctx.now_utc,
            freshness="fresh",
        )

    registry.register("get_nightly_features", mock_handler)

    # 180-day range
    res = registry.invoke(
        "get_nightly_features",
        {"start": "2026-01-01", "end": "2026-07-01"},
        context,
    )

    assert res.ok is True
    start_d = date.fromisoformat(captured_args["start"])
    end_d = date.fromisoformat(captured_args["end"])
    assert (end_d - start_d).days == 90
    assert res.note is not None
    assert "90 days" in res.note


def test_tool_call_writes_audit_row() -> None:
    """Every tool call produces an audit event with control_tier='T1'."""
    registry = ToolRegistry()
    context = ToolContext(subject_id="sub_001", episode_id="ep_001")

    registry.invoke("get_personal_baseline", {"night_date": "2026-08-15"}, context)

    assert len(context.audit_events) == 1
    event = context.audit_events[0]
    assert event.control_tier == ControlTier.T1
    assert event.operation == "execute_tool"
    assert event.tool_name == "get_personal_baseline"
    assert event.permission_decision == "allowed"
