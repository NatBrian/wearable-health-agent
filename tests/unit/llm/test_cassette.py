"""Unit tests for offline cassette provider."""

from unittest.mock import patch

import pytest
from pydantic import BaseModel

from wha.errors import LLMUnavailable
from wha.llm import CassetteClient, Prompt, get_llm_client


class SampleQuestionSchema(BaseModel):
    text: str
    option_labels: list[str]
    rationale: str


class SampleOutcomeSchema(BaseModel):
    observation: str
    claims: list[str]
    action_text: str
    escalation_criteria: list[str]


class ToolCallItem(BaseModel):
    tool_name: str
    args: dict[str, str]
    called_at_utc: str


class DoneItem(BaseModel):
    reason: str


class SampleInvestigateItem(BaseModel):
    tool_call: ToolCallItem | None = None
    done: DoneItem | None = None


def test_cassette_provider_is_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unset or default WHA_LLM_PROVIDER config returns CassetteClient instance."""
    monkeypatch.delenv("WHA_LLM_PROVIDER", raising=False)
    client = get_llm_client()
    assert isinstance(client, CassetteClient)


def test_cassette_miss_fails_loudly() -> None:
    """Cassette miss raises LLMUnavailable explicitly naming prompt_id, scenario and path."""
    client = CassetteClient()
    prompt = Prompt(prompt_id="non_existent_prompt", prompt_version="1", user="test")

    with pytest.raises(LLMUnavailable) as exc_info:
        client.complete(prompt, SampleQuestionSchema)

    msg = str(exc_info.value)
    assert "non_existent_prompt" in msg
    assert "default" in msg or "scenario" in msg


def test_scenario_cassette_preferred_over_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """When WHA_SCENARIO is set, scenario-specific cassette is loaded instead of default."""
    monkeypatch.setenv("WHA_SCENARIO", "illness-onset")
    client = CassetteClient()
    prompt = Prompt(prompt_id="write_question", prompt_version="1")

    res, _usage = client.complete(prompt, SampleQuestionSchema)
    assert isinstance(res, SampleQuestionSchema)
    assert len(res.option_labels) > 0


def test_default_used_when_no_scenario_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """When WHA_SCENARIO is set to a scenario without a specific cassette, default is used."""
    monkeypatch.setenv("WHA_SCENARIO", "unrecorded_scenario_xyz")
    client = CassetteClient()
    prompt = Prompt(prompt_id="write_question", prompt_version="1")

    res, _usage = client.complete(prompt, SampleQuestionSchema)
    assert isinstance(res, SampleQuestionSchema)
    assert "resting heart rate" in res.text.lower()


def test_investigate_list_consumed_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """Investigate cassette list is consumed in sequence across successive calls."""
    monkeypatch.setenv("WHA_SCENARIO", "default")
    client = CassetteClient()
    prompt = Prompt(prompt_id="investigate", prompt_version="1")

    # Step 1: get_nightly_features
    step1, _ = client.complete(prompt, SampleInvestigateItem)
    assert step1.tool_call is not None
    assert step1.tool_call.tool_name == "get_nightly_features"

    # Step 2: get_known_events
    step2, _ = client.complete(prompt, SampleInvestigateItem)
    assert step2.tool_call is not None
    assert step2.tool_call.tool_name == "get_known_events"

    # Step 3: done
    step3, _ = client.complete(prompt, SampleInvestigateItem)
    assert step3.done is not None
    assert step3.tool_call is None


def test_investigate_past_end_yields_done(monkeypatch: pytest.MonkeyPatch) -> None:
    """Calling complete past the end of an investigate list yields Done without raising."""
    monkeypatch.setenv("WHA_SCENARIO", "default")
    client = CassetteClient()
    prompt = Prompt(prompt_id="investigate", prompt_version="1")

    for _ in range(3):
        client.complete(prompt, SampleInvestigateItem)

    # 4th call past the list
    step4, _ = client.complete(prompt, SampleInvestigateItem)
    assert step4.done is not None
    assert step4.tool_call is None


def test_cassette_never_reaches_network() -> None:
    """Cassette complete executes purely from local disk without making socket connections."""
    with patch("socket.socket") as mock_socket:
        client = CassetteClient()
        prompt = Prompt(prompt_id="write_question", prompt_version="1")
        res, _usage = client.complete(prompt, SampleQuestionSchema)
        assert not mock_socket.called
        assert isinstance(res, SampleQuestionSchema)


def test_authored_origin_recorded_in_audit() -> None:
    """Authored fixture cassette exposes origin and model_id as authored-fixture."""
    client = CassetteClient()
    prompt = Prompt(prompt_id="write_outcome", prompt_version="1")
    _res, _usage = client.complete(prompt, SampleOutcomeSchema)

    assert client.last_model_id == "authored-fixture"
    assert client.last_origin == "AUTHORED_FIXTURE"
