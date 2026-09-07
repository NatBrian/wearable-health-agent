"""Prompt definition for episode outcome prose synthesis."""

from wha.constants import TEMP_NATURAL
from wha.llm.prompts.base import PromptDefinition

PROMPT = PromptDefinition(
    prompt_id="write_outcome",
    # v3 removed escalation_criteria from the output schema. That field was the
    # when-to-seek-care text, and it was the only thing this system showed a person that
    # went through no check at all. A live run produced "Seek care if fever persists
    # beyond 72 hours or exceeds 103 degrees F (39.4 C)", with both thresholds invented.
    # It is now selected from red_flags.yaml by wha.safety.select_escalation_criteria.
    prompt_version="3",
    temperature=TEMP_NATURAL,
    instruction=(
        "Synthesize a calm, grounded, objective summary of the episode findings and "
        "recommended action. Every clinical claim must quote, verbatim, the span of a "
        "retrieved passage that supports it."
    ),
    context_template=(
        "Episode Summary: {summary}\n"
        "Disposition: {disposition}\n"
        "Top Causes: {top_causes}\n"
        "Known Facts: {facts}\n"
        "What The Person Told Us: {answers}\n"
        "Retrieved Passages: {passages}"
    ),
    output_schema=(
        '{"observation": str, "claims": [{"text": str, "evidence_span": str}], "action_text": str}'
    ),
    constraints=[
        "Every claim must be strictly grounded in cited physiological evidence or user reports.",
        (
            "evidence_span must be copied character for character out of one of the "
            "Retrieved Passages. It is checked by exact containment in code, so a "
            "paraphrase fails and the claim is discarded."
        ),
        (
            "If no retrieved passage supports a sentence, do not write that sentence and "
            "do not list it as a claim."
        ),
        (
            "Do not write when-to-seek-care advice. It is selected from a fixed list "
            "and appended after you. Describe what was observed, nothing more."
        ),
        "Never make definitive diagnostic declarations.",
        (
            "Never state that no symptoms were reported when What The Person Told Us "
            "names one. What they said outranks any inference from the numbers."
        ),
    ],
    examples=[
        {
            "input": "Disposition: LIKELY_BENIGN, Top cause: alcohol",
            "output": {
                "observation": (
                    "Resting heart rate was elevated for 1 night following reported alcohol intake."
                ),
                "claims": [
                    {
                        "text": (
                            "Heart rate elevation coincided with evening alcohol consumption."
                        ),
                        "evidence_span": "Per-drink RHR +2.8 bpm",
                    }
                ],
                "action_text": "No intervention required. Continue usual routine.",
            },
        }
    ],
    refusal_conditions=[
        "Refuse if data coverage is too sparse to form a coherent observation (INSUFFICIENT_DATA).",
        "Do not write outcome if red flag escalation is pending.",
    ],
)
