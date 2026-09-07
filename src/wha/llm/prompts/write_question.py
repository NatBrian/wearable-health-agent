"""Prompt definition for natural probe question phrasing."""

from wha.constants import TEMP_NATURAL
from wha.llm.prompts.base import PromptDefinition

PROMPT = PromptDefinition(
    prompt_id="write_question",
    prompt_version="1",
    temperature=TEMP_NATURAL,
    instruction="Phrase an empathetic, clear, non-leading question asking the user about a specific confounder or symptom.",
    context_template="Selected Probe: {probe_id}\nTarget Cause: {target_cause}\nFallback Text: {fallback_text}\nAnswer Options: {options}",
    output_schema='{"text": str, "option_labels": [str], "rationale": str}',
    constraints=[
        "Keep tone empathetic, calm, and objective.",
        "Never use alarming, leading, or definitive diagnostic claims.",
        "Keep question length under 200 characters.",
    ],
    examples=[
        {
            "input": "Probe: probe_alcohol, Target: alcohol",
            "output": {
                "text": "Your resting heart rate was higher last night. Did you have any alcoholic drinks yesterday evening?",
                "option_labels": ["No alcohol", "1-2 drinks", "3+ drinks"],
                "rationale": "Objective non-judgmental wording.",
            },
        }
    ],
    refusal_conditions=[
        "Refuse if probe ID is unrecognized or missing fallback options.",
        "Use fallback text if context is corrupted.",
    ],
)
