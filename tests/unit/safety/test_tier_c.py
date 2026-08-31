"""Unit tests for Tier C LLM second opinion safety checks and set union asymmetry."""

from wha.errors import LLMUnavailable
from wha.llm.client import LLMUsage
from wha.safety import (
    check_red_flags_with_tier_c,
)


class MockLLMClient:
    """Mock LLM client returning controlled flag ids."""

    def __init__(self, flag_ids: list[str] | None = None, raise_unavailable: bool = False) -> None:
        self.flag_ids = flag_ids or []
        self.raise_unavailable = raise_unavailable

    def complete(self, prompt, schema, temperature=0.0, max_tokens=1024):
        if self.raise_unavailable:
            raise LLMUnavailable("LLM endpoint is down.")
        return schema(suspected_flag_ids=self.flag_ids, reason="Mock reason"), LLMUsage()


def test_llm_can_add_but_not_remove() -> None:
    """An empty model output never clears a deterministic rule hit, but can add a new flag."""
    # Case 1: Deterministic hit (rf_chest_pain) + Empty LLM output -> Still escalates!
    empty_llm = MockLLMClient(flag_ids=[])
    res1 = check_red_flags_with_tier_c(
        user_text="I have severe crushing chest pain.",
        llm_client=empty_llm,
    )
    assert res1.escalate is True
    assert res1.level == "urgent"
    assert "rf_chest_pain" in res1.triggered_flags

    # Case 2: Deterministic miss (figurative phrasing) + LLM adds rf_chest_pain -> Escalates!
    additive_llm = MockLLMClient(flag_ids=["rf_chest_pain"])
    res2 = check_red_flags_with_tier_c(
        user_text="Feels like an elephant is sitting on my upper torso.",
        llm_client=additive_llm,
    )
    assert res2.escalate is True
    assert res2.level == "urgent"
    assert "rf_chest_pain" in res2.triggered_flags


def test_llm_unavailable_does_not_block_escalation() -> None:
    """When LLM endpoint raises LLMUnavailable, deterministic escalation still fires."""
    failing_llm = MockLLMClient(raise_unavailable=True)

    res = check_red_flags_with_tier_c(
        user_text="I fainted and passed out at work today.",
        llm_client=failing_llm,
    )

    assert res.escalate is True
    assert res.level == "urgent"
    assert "rf_syncope" in res.triggered_flags
