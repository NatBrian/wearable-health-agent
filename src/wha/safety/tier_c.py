"""Tier C safety layer: LLM second opinion combined strictly by set union."""

from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from wha.constants import TEMP_DETERMINISTIC
from wha.errors import LLMUnavailable
from wha.llm import LLMClient, get_llm_client
from wha.llm.prompts import RED_FLAG_CHECK_PROMPT
from wha.safety.models import RedFlagsConfig, SafetyCheckResult
from wha.safety.rules import check_red_flags_deterministic, load_red_flags


class LLMRedFlagOutput(BaseModel):
    """Schema expected from red_flag_check prompt.

    The aliases exist because this layer fails silently when they are absent: with
    ``extra="ignore"`` and empty defaults, a correct model response under a different
    field name parses to zero flags and raises nothing, disabling the Tier C backstop
    without any signal. Accepting the common alternatives is cheap insurance.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    suspected_flag_ids: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("suspected_flag_ids", "flag_ids", "flags"),
    )
    reason: str = Field(default="", validation_alias=AliasChoices("reason", "rationale"))


def check_red_flags_with_tier_c(
    user_text: str | None = None,
    robust_z: float | None = None,
    rhr_bpm: float | None = None,
    rung: Any = None,
    symptom_history: dict[str, int] | None = None,
    recent_tier_b: list[str] | None = None,
    llm_client: LLMClient | None = None,
    config: RedFlagsConfig | None = None,
) -> SafetyCheckResult:
    """Evaluate safety floor with deterministic rules and Tier C LLM union.

    The model contribution is strictly additive:
    - An empty model result never clears a deterministic rule hit.
    - An LLM failure (LLMUnavailable) falls back safely to deterministic rules without blocking.
    - Union of triggered flags ensures model can only add escalations, never suppress them.
    """
    cfg = config or load_red_flags()
    det_result = check_red_flags_deterministic(
        user_text=user_text,
        robust_z=robust_z,
        rhr_bpm=rhr_bpm,
        rung=rung,
        symptom_history=symptom_history,
        recent_tier_b=recent_tier_b,
        config=cfg,
    )

    text = (user_text or "").strip()
    if not text:
        return det_result

    client = llm_client or get_llm_client()

    tier_a_ids = {r.id for r in cfg.tier_a}
    tier_b_ids = {r.id for r in cfg.tier_b}

    llm_flags: set[str] = set()
    llm_reason: str | None = None

    try:
        prompt = RED_FLAG_CHECK_PROMPT.render(
            {
                "user_text": text,
                # Sorted, because a set's repr order varies between runs and would make
                # the rendered prompt, and therefore the cassette key, nondeterministic.
                "criteria_list": str(sorted(tier_a_ids | tier_b_ids)),
            }
        )
        output, _usage = client.complete(
            prompt,
            LLMRedFlagOutput,
            temperature=TEMP_DETERMINISTIC,
        )
        llm_flags = set(output.suspected_flag_ids)
        llm_reason = output.reason
    except (LLMUnavailable, ValueError, TypeError, KeyError, AttributeError):
        # LLM failure must never block a deterministic escalation
        return det_result

    # SET UNION: rules and model combined
    combined_flags = sorted(set(det_result.triggered_flags) | llm_flags)

    # Determine if any added LLM flags are Tier A or Tier B
    has_tier_a = any(f in tier_a_ids for f in combined_flags)
    # Union with the window before counting. A symptom the MODEL spotted tonight must be
    # able to combine with one the RULES recorded on another night; counting only tonight's
    # flags here would have reintroduced the same-message restriction on the Tier C path
    # after it had been removed from the deterministic one.
    tier_b_seen = {f for f in combined_flags if f in tier_b_ids} | {
        f for f in (recent_tier_b or []) if f in tier_b_ids
    }
    tier_b_count = len(tier_b_seen)

    escalate_urgent = det_result.level == "urgent" or has_tier_a
    escalate_same_day = det_result.level == "same_day" or (
        tier_b_count >= 2 and not escalate_urgent
    )

    new_guidance = list(det_result.guidance)
    for flag_id in llm_flags:
        for r in cfg.tier_a:
            if r.id == flag_id and r.guidance not in new_guidance:
                new_guidance.append(r.guidance)

    if (
        escalate_same_day
        and not escalate_urgent
        and cfg.tier_b_guidance
        and cfg.tier_b_guidance not in new_guidance
    ):
        new_guidance.append(cfg.tier_b_guidance)

    level = "urgent" if escalate_urgent else ("same_day" if escalate_same_day else None)
    escalate = escalate_urgent or escalate_same_day

    reasons: list[str] = []
    if det_result.reason:
        reasons.append(det_result.reason)
    if llm_flags and llm_reason:
        reasons.append(f"Tier C model identified: {sorted(llm_flags)} ({llm_reason})")

    return SafetyCheckResult(
        escalate=escalate,
        level=level,
        triggered_flags=combined_flags,
        model_flags=sorted(llm_flags),
        guidance=new_guidance,
        reason="; ".join(reasons) if reasons else None,
    )
