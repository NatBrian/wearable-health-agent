"""Unit tests verifying structural integrity, components, refusal conditions, and temperatures of all prompts."""

import pytest

from wha.constants import TEMP_DETERMINISTIC, TEMP_NATURAL
from wha.errors import LLMUnavailable
from wha.llm.prompts import ALL_PROMPTS, get_prompt_definition


def test_prompt_has_all_six_components() -> None:
    """Every prompt in the prompts registry has all six mandatory components."""
    # Eleven: `converse` for the multi-turn grounded conversation, and
    # `extract_rule_items` for the separate zero-temperature pass that pulls decision-rule
    # answers out of it. They are split because one call asked to do both only conversed.
    assert len(ALL_PROMPTS) == 11
    for p in ALL_PROMPTS:
        assert p.prompt_id, "Missing prompt_id"
        assert p.prompt_version, f"{p.prompt_id}: Missing prompt_version"
        # 1. instruction
        assert p.instruction and len(p.instruction) > 10, f"{p.prompt_id}: Missing instruction"
        # 2. context_template
        assert p.context_template and len(p.context_template) > 5, (
            f"{p.prompt_id}: Missing context_template"
        )
        # 3. output_schema
        assert p.output_schema and len(p.output_schema) > 5, f"{p.prompt_id}: Missing output_schema"
        # 4. constraints
        assert len(p.constraints) >= 1, f"{p.prompt_id}: Missing constraints"
        # 5. examples
        assert len(p.examples) >= 1, f"{p.prompt_id}: Missing examples"
        # 6. refusal_conditions
        assert len(p.refusal_conditions) >= 1, f"{p.prompt_id}: Missing refusal_conditions"


def test_every_prompt_has_refusal_conditions() -> None:
    """Every prompt explicitly specifies refusal conditions (critical for INSUFFICIENT_DATA)."""
    for p in ALL_PROMPTS:
        assert isinstance(p.refusal_conditions, list)
        assert len(p.refusal_conditions) >= 1, f"Prompt '{p.prompt_id}' lacks refusal conditions"
        for r in p.refusal_conditions:
            assert isinstance(r, str) and len(r.strip()) > 5


def test_temperature_zero_for_checked_jobs() -> None:
    """Checked jobs have temperature=0.0 (TEMP_DETERMINISTIC); read jobs have temperature=0.3 (TEMP_NATURAL)."""
    checked_jobs = {"investigate", "extract_facts", "red_flag_check", "veto_check", "critique"}
    natural_jobs = {"write_question", "interview_followup", "write_outcome", "answer_about_episode"}

    for job in checked_jobs:
        p = get_prompt_definition(job)
        assert p.temperature == TEMP_DETERMINISTIC, f"{job} must have deterministic temperature 0.0"

    for job in natural_jobs:
        p = get_prompt_definition(job)
        assert p.temperature == TEMP_NATURAL, f"{job} must have natural temperature 0.3"


def _placeholder_context(definition: object) -> dict[str, str]:
    """Every context variable a template names, filled with a marker."""
    from string import Formatter

    return {
        field: f"<{field}>"
        for _, field, _, _ in Formatter().parse(definition.context_template)
        if field
    }


def test_prompt_version_written_to_audit() -> None:
    """Rendered Prompt carries prompt_id and prompt_version for audit traceability."""
    for p in ALL_PROMPTS:
        rendered = p.render(_placeholder_context(p))
        assert rendered.prompt_id == p.prompt_id
        assert rendered.prompt_version == p.prompt_version


def test_conversation_prompt_keeps_prior_topic_advice_out_of_new_answers() -> None:
    """An old symptom should not be repeated in an unrelated wearable-data answer."""
    prompt = get_prompt_definition("converse")
    assert prompt.prompt_version == "7"
    assert any(
        "A prior urgency level is metadata, not a reason to repeat clinical advice from an earlier topic."
        in constraint
        for constraint in prompt.constraints
    )


def test_conversation_prompt_requires_verbatim_uncited_notes() -> None:
    prompt = get_prompt_definition("converse")
    assert any(
        "Copy each such complete sentence exactly from `reply` into `uncited_notes`"
        in constraint
        for constraint in prompt.constraints
    )


def test_conversation_prompt_answers_latest_request_before_follow_up() -> None:
    prompt = get_prompt_definition("converse")
    assert any(
        "always answer the latest message first" in constraint
        and "Put the follow-up only in `question`" in constraint
        for constraint in prompt.constraints
    )


def test_missing_context_variable_refuses_rather_than_shipping_a_placeholder() -> None:
    """A forgotten key must not reach the model as the literal text of its own name.

    render() used to catch the KeyError and send the unrendered template, so a prompt
    missing a variable produced a quietly worse answer and nothing else. It also disarmed
    the oversize guard, because an unrendered template is always short.
    """
    p = get_prompt_definition("investigate")

    with pytest.raises(LLMUnavailable) as exc_info:
        p.render({"episode_id": "ep1"})

    assert "missing a context variable" in str(exc_info.value)


def test_oversize_prompt_raises_not_truncates() -> None:
    """Context exceeding budget raises LLMUnavailable rather than silently truncating."""
    p = get_prompt_definition("investigate")
    huge_context = {
        "history_summary": "A" * 20000,
        "episode_id": "ep1",
        "previous_calls": "[]",
        "answers_so_far": "None yet.",
        "tool_catalogue": "- get_nightly_features(start, end)",
    }

    with pytest.raises(LLMUnavailable) as exc_info:
        p.render(huge_context)

    assert "exceeded character budget" in str(exc_info.value)
    assert "Refusing to truncate silently" in str(exc_info.value)
