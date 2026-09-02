"""Unit tests for Tier C LLM second opinion safety checks and set union asymmetry."""

from wha.errors import LLMUnavailable
from wha.llm.client import LLMUsage
from wha.llm.prompts import RED_FLAG_CHECK_PROMPT
from wha.safety import (
    check_red_flags_with_tier_c,
    load_red_flags,
)
from wha.safety.tier_c import LLMRedFlagOutput


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


def test_prompt_output_schema_names_the_fields_the_parser_reads() -> None:
    """The declared schema must name the fields LLMRedFlagOutput actually reads.

    When these drift apart the layer fails silently: a correct model response parses to
    zero flags, raises nothing, and the Tier C backstop is gone with no signal at all.
    """
    schema_text = RED_FLAG_CHECK_PROMPT.output_schema
    for field_name in LLMRedFlagOutput.model_fields:
        assert field_name in schema_text, (
            f"Prompt output_schema does not mention '{field_name}', which the parser reads"
        )

    for example in RED_FLAG_CHECK_PROMPT.examples:
        assert set(example["output"]) == set(LLMRedFlagOutput.model_fields)


def test_prompt_example_uses_real_flag_ids() -> None:
    """Example flag ids must exist in red_flags.yaml, or they teach the model to invent ids."""
    cfg = load_red_flags()
    valid_ids = {r.id for r in cfg.tier_a} | {r.id for r in cfg.tier_b}

    for example in RED_FLAG_CHECK_PROMPT.examples:
        for flag_id in example["output"]["suspected_flag_ids"]:
            assert flag_id in valid_ids, f"Example teaches invented flag id '{flag_id}'"


def test_alternative_field_names_still_parse() -> None:
    """A model replying flag_ids/rationale reaches the union rather than silently emptying it."""
    parsed = LLMRedFlagOutput.model_validate(
        {"flag_ids": ["rf_chest_pain"], "rationale": "Describes crushing chest pressure."}
    )
    assert parsed.suspected_flag_ids == ["rf_chest_pain"]
    assert parsed.reason == "Describes crushing chest pressure."
