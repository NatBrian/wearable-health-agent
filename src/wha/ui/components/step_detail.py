"""What one step did, why it exists, and the arithmetic behind it in words.

Sections in a fixed order, because a reader learns the shape once and then knows where to
look: what happened, why this step exists at all, what went in, what came out, the sources
it read, and the raw record underneath.

"The numbers" states the arithmetic in words rather than showing a formula. A person who
cannot read a formula still deserves to know that the difference is their reading minus
their normal, and a person who can read one is not helped by seeing it in a screen when
the raw values are one expander away.
"""

from typing import Any

import streamlit as st

from wha.models import PipelineStepView, StepStatus
from wha.ui import design, explain, format
from wha.ui.components.citations import drawer
from wha.ui.components.pipeline_graph import step_name

# How each step's outputs read as a sentence. Keys are output field names; the value names
# the field for a person. Anything not named here is still shown, under its own key.
_FIELD_NAMES: dict[str, str] = {
    "heart_rate_samples": "readings stored",
    "sleep_stage_rows": "sleep records",
    "window_source": "window used",
    "asleep_minutes": "minutes of sleep measured",
    "start_utc": "window started",
    "end_utc": "window ended",
    "rhr_bpm": "your reading",
    "coverage_minutes": "minutes measured",
    "sleep_hours": "hours of sleep",
    "usable": "good enough to use",
    "implausible_dropped": "impossible readings dropped",
    "centre_bpm": "your normal",
    "scale_bpm": "how much you vary",
    "usable_nights": "nights it is built from",
    "rung": "how well your normal is known",
    "explained_bpm": "explained by exercise",
    "residual_bpm": "left after that",
    "deviation_bpm": "above your normal",
    "robust_z": "how unusual, in your own units",
    "level": "conclusion",
    "flagged": "opened an investigation",
    "reasons": "why",
    "top_cause": "leading explanation",
    "top_probability": "how likely",
    "p_illness": "chance this is illness",
    "evsi": "value of asking you",
    "interruption_cost": "cost of interrupting you",
    "questions": "questions asked",
    "replies": "what you said",
    "stripped_claims": "claims removed for having no source",
    "tool_call_count": "tool calls",
    "messages_checked": "messages checked",
    "episode_id": "investigation",
}


def _arithmetic(step: PipelineStepView) -> str | None:
    """The sum this step did, in a sentence, using its own stored values."""
    out = step.outputs
    if step.step_id == "detect" and out.get("deviation_bpm") is not None:
        return (
            f"Your reading minus your normal is {format.gap(out.get('deviation_bpm'))}. "
            f"After subtracting what a recorded workout explains, "
            f"{format.bpm(out.get('residual_bpm'))} was left, and that is what was judged."
        )
    if step.step_id == "baseline" and out.get("centre_bpm") is not None:
        return (
            f"The middle of your recent nights is {format.bpm(out.get('centre_bpm'))}, and "
            f"you vary by about {format.bpm(out.get('scale_bpm'))} from night to night. "
            f"That is built from {out.get('usable_nights')} of your own nights."
        )
    if step.step_id == "believe" and out.get("top_probability") is not None:
        return (
            f"Every combination of twelve causes was weighed. The leading one is "
            f"{str(out.get('top_cause')).replace('_', ' ')} at "
            f"{format.probability(out.get('top_probability'))}. These are probabilities on "
            "the evidence so far, not a diagnosis."
        )
    if step.step_id == "decide" and out.get("evsi") is not None:
        return (
            f"Asking you was worth {out.get('evsi'):.3f} against an interruption cost of "
            f"{out.get('interruption_cost'):.3f}. A question is only asked when the first "
            "is larger."
        )
    return None


def render(pipeline: Any, step_id: str) -> None:
    """The panel beside the grid, for whichever step the reader opened."""
    step = next((s for s in pipeline.steps if s.step_id == step_id), None)
    if step is None:
        st.info("Select a step to see what it did.")
        return

    st.markdown(
        design.chip(str(step.layer).replace("_", " "), str(step.layer))
        + f" &nbsp; <strong>Step {step.ordinal} of {len(pipeline.steps)}</strong>",
        unsafe_allow_html=True,
    )
    st.subheader(step_name(step.step_id))

    st.markdown("**What happened**")
    st.write(step.reason)
    if step.status is StepStatus.UNRECORDED:
        st.warning(explain.text("pipeline.unrecorded"))
    elif step.status is not StepStatus.RAN:
        st.caption(f"This step {format.status_word(str(step.status))} on this night.")

    st.markdown("**Why this step exists**")
    st.write(explain.step(step.step_id, "why"))

    sentence = _arithmetic(step)
    if sentence:
        st.markdown("**The numbers**")
        st.write(sentence)

    if step.outputs:
        st.markdown("**What it produced**")
        for key, value in step.outputs.items():
            if isinstance(value, list | dict) and len(str(value)) > 120:
                continue
            st.write(f"- {_FIELD_NAMES.get(key, key.replace('_', ' '))}: {_value(value)}")

    if step.sources:
        st.markdown(f"**Sources it read: {len(step.sources)}**")
        for index, citation in enumerate(step.sources):
            with st.expander(getattr(citation, "title", f"source {index + 1}")):
                drawer(citation)

    with st.expander("The raw record for this step"):
        st.json(
            {
                "step_id": step.step_id,
                "status": str(step.status),
                "occurred_utc": step.occurred_utc.isoformat() if step.occurred_utc else None,
                "inputs": step.inputs,
                "outputs": step.outputs,
                "detail": step.detail_json,
            }
        )


def _value(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.3g}"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) or "none"
    return str(value)
