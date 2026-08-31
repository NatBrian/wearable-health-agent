"""Prompt definition for output critique and claim verification pass."""

from wha.constants import TEMP_DETERMINISTIC
from wha.llm.prompts.base import PromptDefinition

PROMPT = PromptDefinition(
    prompt_id="critique",
    prompt_version="1",
    temperature=TEMP_DETERMINISTIC,
    instruction="Critique proposed outcome draft against retrieved medical literature and evidence facts. May only strip ungrounded claims.",
    context_template="Proposed Draft: {draft_text}\nGrounding Sources: {sources}\nEpisode Facts: {facts}",
    output_schema='{"approved": bool, "stripped_claims": [str], "modified_text": str, "critique_notes": str}',
    constraints=[
        "Strictly subtractive: may remove or soften claims, never inject new unverified claims.",
        "Check that no ungrounded causal assertions remain.",
    ],
    examples=[
        {
            "input": "Draft claimed 'Your heart rate indicates a bacterial infection.' with no lab evidence.",
            "output": {
                "approved": False,
                "stripped_claims": ["indicates a bacterial infection"],
                "modified_text": "Your resting heart rate was elevated above your normal baseline.",
                "critique_notes": "Removed ungrounded bacterial diagnosis claim.",
            },
        }
    ],
    refusal_conditions=[
        "Refuse if proposed draft is completely devoid of content.",
        "Reject draft if safety escalation guidelines are violated.",
    ],
)
