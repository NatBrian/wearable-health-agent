"""Prompt definition for investigation tool selection."""

from wha.constants import TEMP_DETERMINISTIC
from wha.llm.prompts.base import PromptDefinition

PROMPT = PromptDefinition(
    prompt_id="investigate",
    prompt_version="1",
    temperature=TEMP_DETERMINISTIC,
    instruction="Select the next diagnostic tool call to gather required episode evidence, or conclude investigation.",
    context_template=(
        "Tools You May Call:\n{tool_catalogue}\n\n"
        "Episode ID: {episode_id}\n"
        "History Summary: {history_summary}\n"
        "Previous Tool Calls: {previous_calls}\n"
        "Answers The Person Has Given: {answers_so_far}"
    ),
    output_schema='{"tool_call": {"tool_name": str, "args": dict, "called_at_utc": str} | null, "done": {"reason": str} | null}',
    constraints=[
        "Never call tools outside permitted Tier 1 registry.",
        "Stop investigation when sufficient evidence is accumulated or tool budget reached.",
        "Deterministic output with no conversational commentary.",
        (
            "When the person has answered a question, look up what that answer means "
            "before concluding: call retrieve_clinical_evidence with the symptom or "
            "cause they named."
        ),
        (
            "Do not repeat a tool call that already appears in Previous Tool Calls with "
            "the same arguments. Yield done instead."
        ),
    ],
    examples=[
        {
            "input": "Episode active with elevated nocturnal heart rate for 2 days.",
            "output": {
                "tool_call": {
                    "tool_name": "get_nightly_features",
                    "args": {"start": "-10d", "end": "today"},
                    "called_at_utc": "2026-09-01T02:00:00Z",
                },
                "done": None,
            },
        }
    ],
    refusal_conditions=[
        "Refuse if subject ID is invalid or missing.",
        "Yield done immediately if tool execution limit is exceeded.",
    ],
)
