"""Prompt definition for episode outcome prose synthesis."""

from wha.constants import TEMP_NATURAL
from wha.llm.prompts.base import PromptDefinition

PROMPT = PromptDefinition(
    prompt_id="write_outcome",
    prompt_version="1",
    temperature=TEMP_NATURAL,
    instruction="Synthesize a calm, grounded, objective summary of the episode findings and recommended action.",
    context_template="Episode Summary: {summary}\nDisposition: {disposition}\nTop Causes: {top_causes}\nKnown Facts: {facts}",
    output_schema='{"observation": str, "claims": [str], "action_text": str, "escalation_criteria": [str]}',
    constraints=[
        "Every claim must be strictly grounded in cited physiological evidence or user reports.",
        "Include clear clinical escalation criteria (red flags).",
        "Never make definitive diagnostic declarations.",
    ],
    examples=[
        {
            "input": "Disposition: LIKELY_BENIGN, Top cause: alcohol",
            "output": {
                "observation": "Resting heart rate was elevated for 1 night following reported alcohol intake.",
                "claims": ["Heart rate elevation coincided with evening alcohol consumption."],
                "action_text": "No intervention required. Continue usual routine.",
                "escalation_criteria": [
                    "Seek care if elevated heart rate persists >3 nights without confounders."
                ],
            },
        }
    ],
    refusal_conditions=[
        "Refuse if data coverage is too sparse to form a coherent observation (INSUFFICIENT_DATA).",
        "Do not write outcome if red flag escalation is pending.",
    ],
)
