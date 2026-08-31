"""Prompt definition for redundant question veto checks."""

from wha.constants import TEMP_DETERMINISTIC
from wha.llm.prompts.base import PromptDefinition

PROMPT = PromptDefinition(
    prompt_id="veto_check",
    prompt_version="1",
    temperature=TEMP_DETERMINISTIC,
    instruction="Determine whether a proposed inquiry has already been answered by existing facts or is redundant.",
    context_template="Proposed Probe: {probe_id}\nCandidate Question: {question_text}\nKnown Facts: {known_facts}",
    output_schema='{"veto": bool, "reason": str, "suggested_alternative": str | null}',
    constraints=[
        "Veto only if the factual answer is already known with certainty.",
        "Do not veto when uncertainty remains high.",
    ],
    examples=[
        {
            "input": "Proposed asking about alcohol when user already logged 3 pints on the same evening.",
            "output": {
                "veto": True,
                "reason": "Alcohol consumption already logged in episode facts.",
                "suggested_alternative": None,
            },
        }
    ],
    refusal_conditions=[
        "Refuse veto if known facts are contradictory or unverified.",
        "Default to veto=False when in doubt.",
    ],
)
