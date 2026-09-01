"""Unit tests for tool registry, security injection, caching, clamping, provenance, and failure safety."""

from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

import pytest

from wha.agent.tools import (
    CLOSED_TOOL_REGISTRY,
    ToolContext,
    ToolRegistry,
    ToolResult,
    create_default_tool_registry,
)
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


def test_no_tool_can_write() -> None:
    """All seven registered tools are strictly read-only and cannot perform writes."""
    registry = create_default_tool_registry()
    context = ToolContext(subject_id="sub_001")

    # Read-only db mock with no write methods
    ro_db = MagicMock(
        spec=["get_nightly_features", "get_baseline", "get_known_events", "find_similar_episodes"]
    )

    for tool_name in CLOSED_TOOL_REGISTRY:
        res = registry.invoke(
            tool_name,
            {"start": "2026-08-01", "end": "2026-08-05", "query": "fever"},
            context,
            db=ro_db,
        )
        assert isinstance(res, ToolResult)


def test_every_result_carries_provenance() -> None:
    """Every tool return carries valid provenance source_ids, as_of_utc, and freshness."""
    registry = create_default_tool_registry()
    context = ToolContext(subject_id="sub_001")

    res = registry.invoke("get_data_quality", {"start": "2026-08-01", "end": "2026-08-05"}, context)
    assert isinstance(res.source_ids, list)
    assert len(res.source_ids) > 0
    assert isinstance(res.as_of_utc, datetime)
    assert res.freshness in ("fresh", "stale", "missing")


def test_stale_data_is_flagged_not_hidden() -> None:
    """Features older than INGEST_STALE_WARN_HOURS (36h) are explicitly flagged as stale."""
    registry = create_default_tool_registry()
    context = ToolContext(
        subject_id="sub_001",
        now_utc=datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
    )

    # 4 days old data
    old_feature = MagicMock()
    old_feature.night_date = date(2026, 8, 25)

    mock_db = MagicMock()
    mock_db.get_nightly_features.return_value = [old_feature]

    res = registry.invoke(
        "get_nightly_features",
        {"start": "2026-08-20", "end": "2026-08-25"},
        context,
        db=mock_db,
    )

    assert res.ok is True
    assert res.freshness == "stale"
    assert res.note is not None


def test_missing_data_returns_ok_false_not_raise() -> None:
    """When queried entity has no records, tool returns missing status without raising into the graph."""
    registry = create_default_tool_registry()
    context = ToolContext(subject_id="sub_001")

    mock_db = MagicMock()
    mock_db.get_baseline.return_value = None

    res = registry.invoke(
        "get_personal_baseline",
        {"night_date": "2026-08-01"},
        context,
        db=mock_db,
    )

    assert res.ok is True
    assert res.value is None
    assert res.freshness == "missing"
    assert res.note is not None


def test_disease_activity_refuses_unlisted_url() -> None:
    """Attempts to pass an unlisted URL to get_local_disease_activity are strictly refused."""
    registry = create_default_tool_registry()
    context = ToolContext(subject_id="sub_001")

    res = registry.invoke(
        "get_local_disease_activity",
        {"url": "https://malicious-site.com/data.json"},
        context,
    )

    assert res.ok is False
    assert res.freshness == "missing"
    assert "Refused" in res.note


def test_disease_activity_unreachable_does_not_raise() -> None:
    """When disease activity endpoint is unreachable, tool returns ok=False without raising."""
    registry = create_default_tool_registry()
    context = ToolContext(subject_id="sub_001")

    with patch("urllib.request.urlopen", side_effect=OSError("Network unreachable")):
        res = registry.invoke("get_local_disease_activity", {}, context)

    assert res.ok is False
    assert res.freshness == "missing"
    assert "unreachable" in res.note


def test_no_network_in_six_of_seven_tools() -> None:
    """Six out of seven tools never make any network requests."""
    registry = create_default_tool_registry()
    context = ToolContext(subject_id="sub_001")

    six_tools = [
        "get_nightly_features",
        "get_personal_baseline",
        "get_known_events",
        "get_data_quality",
        "find_similar_past_episodes",
        "retrieve_clinical_evidence",
    ]

    with patch(
        "urllib.request.urlopen", side_effect=AssertionError("Network called on offline tool")
    ):
        for name in six_tools:
            res = registry.invoke(
                name, {"start": "2026-08-01", "end": "2026-08-05", "query": "fever"}, context
            )
            assert isinstance(res, ToolResult)


def test_large_result_is_truncated_visibly() -> None:
    """Audit serialization visibly marks and truncates oversized tool result values."""
    registry = ToolRegistry()
    context = ToolContext(subject_id="sub_001", episode_id="ep_001")

    huge_payload = "X" * 1500

    def mock_large_handler(args, ctx, db):
        return ToolResult(
            tool_name="get_nightly_features",
            args=args,
            ok=True,
            value=huge_payload,
            as_of_utc=datetime.now(UTC),
            freshness="fresh",
        )

    registry.register("get_nightly_features", mock_large_handler)
    registry.invoke("get_nightly_features", {"start": "2026-08-01", "end": "2026-08-10"}, context)

    event = context.audit_events[-1]
    assert event.tool_result is not None
    assert event.tool_result["truncated"] is True
    assert "[TRUNCATED]" in event.tool_result["preview"]
