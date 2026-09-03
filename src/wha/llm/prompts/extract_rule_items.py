"""Prompt definition for pulling decision-rule answers out of what the person said.

Split out from the conversation prompt deliberately. Asked to converse and to extract in
one call, the model conversed: it asked the Marburg questions correctly and returned an
empty ``rule_answers`` list every time, so the rule never completed and no urgency was ever
decided. A person describing chest pain was left in limbo, which is worse than the
over-escalation this redesign replaced.

This does one job, at temperature zero, over the outstanding items only. It mirrors the
first of AMIE's three per-turn steps, "analysing patient information", as its own call.
"""

from wha.constants import TEMP_DETERMINISTIC
from wha.llm.prompts.base import PromptDefinition

PROMPT = PromptDefinition(
    prompt_id="extract_rule_items",
    prompt_version="1",
    temperature=TEMP_DETERMINISTIC,
    instruction=(
        "Read what the person has said and decide, for each outstanding item only, "
        "whether they have answered it yes or no. Extract, do not infer."
    ),
    context_template=(
        "Everything They Have Said:\n{conversation}\n\n"
        "Outstanding Items:\n{items}\n\n"
        "Safety Gates:\n{gates}"
    ),
    output_schema=(
        '{"rule_answers": [{"item_id": str, "answer": bool, "quote": str}], '
        '"gates_confirmed": [str]}'
    ),
    constraints=[
        (
            "Only include an item when the person has actually addressed it. If they have "
            "not mentioned it, leave it out. An absent item is asked again; a wrong one "
            "changes a clinical score."
        ),
        "`quote` must be their own words, copied exactly, showing where the answer came from.",
        "Only use item ids from Outstanding Items. Invent nothing.",
        (
            "An item asking whether something is reproducible by pressing is answered true "
            "when pressing DOES reproduce the pain. Answer the question as asked, not the "
            "condition it scores."
        ),
        (
            "Confirm a safety gate only when the person has described it as happening to "
            "them, not when they have denied it or when you are asking about it."
        ),
    ],
    examples=[
        {
            "input": (
                "They said: I am 40, no heart problems ever, it does not change on stairs, "
                "pressing on it hurts exactly the same. Outstanding: mhs_age_sex, "
                "mhs_known_vascular, mhs_worse_with_exercise, mhs_reproducible_by_palpation"
            ),
            "output": {
                "rule_answers": [
                    {"item_id": "mhs_age_sex", "answer": False, "quote": "I am 40"},
                    {
                        "item_id": "mhs_known_vascular",
                        "answer": False,
                        "quote": "no heart problems ever",
                    },
                    {
                        "item_id": "mhs_worse_with_exercise",
                        "answer": False,
                        "quote": "it does not change on stairs",
                    },
                    {
                        "item_id": "mhs_reproducible_by_palpation",
                        "answer": True,
                        "quote": "pressing on it hurts exactly the same",
                    },
                ],
                "gates_confirmed": [],
            },
        }
    ],
    refusal_conditions=[
        "Return an empty list rather than guessing at an item they have not addressed.",
    ],
)
