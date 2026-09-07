"""Prompt definition for grounded episode Q&A."""

from wha.constants import TEMP_NATURAL
from wha.llm.prompts.base import PromptDefinition

PROMPT = PromptDefinition(
    prompt_id="answer_about_episode",
    prompt_version="1",
    temperature=TEMP_NATURAL,
    instruction="Answer user questions about the current episode strictly grounded in retrieved evidence and verified facts.",
    context_template="User Question: {question}\nEpisode State: {state}\nRetrieved Knowledge Passages: {passages}\nVerified Facts: {facts}",
    output_schema='{"text": str, "citations": [{"doc_id": str, "quote": str}], "refused": bool, "refusal_reason": str | null}',
    constraints=[
        "Answer must be strictly grounded in provided passages.",
        "Refuse to answer questions outside the scope of the episode.",
        "Include explicit citation quotes for all medical assertions.",
    ],
    examples=[
        {
            "input": "Why did you suspect alcohol might be the cause?",
            "output": {
                "text": "Alcohol consumption is known to elevate nocturnal resting heart rate by 3-8 bpm on the night of intake.",
                "citations": [
                    {
                        "doc_id": "alcohol_effects_rhr",
                        "quote": "Alcohol increases nocturnal heart rate",
                    }
                ],
                "refused": False,
                "refusal_reason": None,
            },
        }
    ],
    refusal_conditions=[
        "Refuse if question asks for general non-episode medical advice or off-topic queries.",
        "Refuse if retrieved knowledge contains no relevant support for the requested query.",
    ],
)
