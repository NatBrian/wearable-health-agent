"""Prompts registry and discovery."""

from wha.llm.prompts.answer_about_episode import PROMPT as ANSWER_ABOUT_EPISODE_PROMPT
from wha.llm.prompts.base import PromptDefinition
from wha.llm.prompts.converse import PROMPT as CONVERSE_PROMPT
from wha.llm.prompts.critique import PROMPT as CRITIQUE_PROMPT
from wha.llm.prompts.extract_facts import PROMPT as EXTRACT_FACTS_PROMPT
from wha.llm.prompts.extract_rule_items import PROMPT as EXTRACT_RULE_ITEMS_PROMPT
from wha.llm.prompts.interview_followup import PROMPT as INTERVIEW_FOLLOWUP_PROMPT
from wha.llm.prompts.investigate import PROMPT as INVESTIGATE_PROMPT
from wha.llm.prompts.red_flag_check import PROMPT as RED_FLAG_CHECK_PROMPT
from wha.llm.prompts.veto_check import PROMPT as VETO_CHECK_PROMPT
from wha.llm.prompts.write_outcome import PROMPT as WRITE_OUTCOME_PROMPT
from wha.llm.prompts.write_question import PROMPT as WRITE_QUESTION_PROMPT

ALL_PROMPTS: list[PromptDefinition] = [
    INVESTIGATE_PROMPT,
    EXTRACT_FACTS_PROMPT,
    RED_FLAG_CHECK_PROMPT,
    VETO_CHECK_PROMPT,
    WRITE_QUESTION_PROMPT,
    INTERVIEW_FOLLOWUP_PROMPT,
    WRITE_OUTCOME_PROMPT,
    CRITIQUE_PROMPT,
    ANSWER_ABOUT_EPISODE_PROMPT,
    CONVERSE_PROMPT,
    EXTRACT_RULE_ITEMS_PROMPT,
]

PROMPTS_BY_ID: dict[str, PromptDefinition] = {p.prompt_id: p for p in ALL_PROMPTS}


def get_prompt_definition(prompt_id: str) -> PromptDefinition:
    """Look up PromptDefinition by prompt_id."""
    if prompt_id not in PROMPTS_BY_ID:
        raise KeyError(f"Unknown prompt_id '{prompt_id}'. Registered: {list(PROMPTS_BY_ID.keys())}")
    return PROMPTS_BY_ID[prompt_id]
