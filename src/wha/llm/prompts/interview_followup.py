"""Prompt definition for conversation follow-up questions."""

from wha.constants import TEMP_NATURAL
from wha.llm.prompts.base import PromptDefinition

PROMPT = PromptDefinition(
    prompt_id="interview_followup",
    prompt_version="1",
    temperature=TEMP_NATURAL,
    instruction="Generate a relevant follow-up question in an ongoing interview to clarify ambiguity.",
    context_template="Previous User Message: {last_message}\nEpisode Context: {episode_context}\nRemaining Uncertainty: {uncertainty_cause}",
    output_schema='{"text": str, "option_labels": [str], "rationale": str}',
    constraints=[
        "Ask only one focused question at a time.",
        "Acknowledge user input briefly before asking.",
        "Never offer definitive medical diagnoses.",
    ],
    examples=[
        {
            "input": "User says: 'I felt sick yesterday'.",
            "output": {
                "text": "I see. Could you share what specific symptoms you noticed yesterday?",
                "option_labels": [
                    "Fever/chills",
                    "Cough/throat",
                    "Fatigue/aches",
                    "Stomach upset",
                    "Other",
                ],
                "rationale": "Clarify symptom cluster.",
            },
        }
    ],
    refusal_conditions=[
        "Refuse if conversation depth budget is exhausted.",
        "Do not ask follow-up if user requested to stop.",
    ],
)
