"""Prompt definition for extracting structured facts from free text."""

from wha.constants import TEMP_DETERMINISTIC
from wha.llm.prompts.base import PromptDefinition

PROMPT = PromptDefinition(
    prompt_id="extract_facts",
    prompt_version="1",
    temperature=TEMP_DETERMINISTIC,
    instruction="Extract structured medical and confounder facts from user free text responses.",
    context_template="User Response: {user_response}\nRelevant Probes: {relevant_probes}",
    output_schema='{"facts": [{"cause_id": str, "present": bool, "confidence": float, "temporal_offset_days": int, "quote": str}]}',
    constraints=[
        "Extract only facts directly supported by user text.",
        "Never invent unmentioned symptoms or activities.",
        "Include exact substring quotes for verification.",
    ],
    examples=[
        {
            "input": "I had three beers yesterday evening and felt dehydrated.",
            "output": {
                "facts": [
                    {
                        "cause_id": "alcohol",
                        "present": True,
                        "confidence": 0.95,
                        "temporal_offset_days": 0,
                        "quote": "three beers yesterday evening",
                    }
                ]
            },
        }
    ],
    refusal_conditions=[
        "Refuse if user text is completely unrelated to health or physiological state.",
        "Return empty facts if no evidence of confounders or illness is present.",
    ],
)
