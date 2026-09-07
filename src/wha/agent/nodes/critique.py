"""The pass that removes unsupported claims and never adds any."""

import json
import re
from typing import Any

from wha.agent.nodes.context import _episode_numbers, _record_stage_ran
from wha.agent.nodes.schemas import CritiqueResponse
from wha.agent.state import EpisodeState
from wha.errors import LLMUnavailable, ValidationFailed
from wha.llm.client import LLMClient, get_llm_client
from wha.llm.prompts import get_prompt_definition
from wha.safety.output_checks import (
    DIAGNOSIS_PHRASES,
    FALSE_REASSURANCE_PHRASES,
    validate_and_sanitize_outcome,
)


def node_critique(
    state: EpisodeState,
    llm_client: LLMClient | None = None,
    db: Any = None,
) -> dict[str, Any]:
    """Run deterministic grounding first, followed by subtractive LLM critique."""
    draft = state.get("draft")
    if draft is None:
        return {"step": state.get("step", 0) + 1}

    obs = draft.observation
    # Deterministic phrase cleaning for false reassurance & diagnosis language
    for phrase in FALSE_REASSURANCE_PHRASES:
        if phrase in obs.lower():
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            obs = pattern.sub("", obs).strip()

    for phrase in DIAGNOSIS_PHRASES:
        if phrase in obs.lower():
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            obs = pattern.sub("", obs).strip()

    cleaned_draft = draft.model_copy(update={"observation": obs})

    # Step A: Deterministic grounding & sanitization
    sanitized_draft = validate_and_sanitize_outcome(
        cleaned_draft,
        episode_numbers=_episode_numbers(state),
    )

    # Step B: LLM Critique Pass (Subtractive only)
    client = llm_client or get_llm_client()
    try:
        critique_def = get_prompt_definition("critique")
        critique_prompt = critique_def.render(
            {
                "draft_text": sanitized_draft.observation,
                "sources": json.dumps(sanitized_draft.evidence_used),
                "facts": json.dumps(
                    [e.model_dump() for e in state.get("evidence", [])], default=str
                ),
            }
        )
        critique_res, _ = client.complete(
            critique_prompt,
            schema=CritiqueResponse,
            temperature=critique_def.temperature,
        )
        current_text = sanitized_draft.observation
        # Strip any ungrounded claims identified by the model
        for stripped in critique_res.stripped_claims:
            if stripped and stripped in current_text:
                current_text = current_text.replace(stripped, "").strip()

        # If model proposed a shorter / sanitized modified_text, use it if it doesn't inflate length
        if critique_res.modified_text and len(critique_res.modified_text) <= len(
            sanitized_draft.observation
        ):
            current_text = critique_res.modified_text

        sanitized_draft = sanitized_draft.model_copy(update={"observation": current_text})
    except (
        LLMUnavailable,
        ValidationFailed,
        KeyError,
        TypeError,
        ValueError,
        AttributeError,
        StopIteration,
    ):
        pass

    _record_stage_ran(db, state, "critique")

    return {
        "draft": sanitized_draft,
        "step": state.get("step", 0) + 1,
    }
