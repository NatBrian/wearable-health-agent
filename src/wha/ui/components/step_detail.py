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
    if step.step_id == "decide" and out.get("action"):
        value = out.get("value_of_asking")
        cost = out.get("interruption_cost")
        if out.get("action") == "ASK" and value is not None and cost is not None:
            return (
                f"Asking you was worth {value:.3f} against a cost of interrupting you of "
                f"{cost:.3f}. A question is only asked when the first is larger, and it "
                "was."
            )
        considered = out.get("questions_considered") or []
        if considered:
            best = max(considered, key=lambda c: c.get("value_of_asking", 0))
            return (
                f"Every question it could have asked was scored. The best of them, "
                f"{_question_name(best.get('probe_id'))}, was worth "
                f"{best.get('value_of_asking'):.3f}. A negative number means the answer "
                "would be worth less than the cost of interrupting you, so it asked "
                "nothing."
            )
        return "No question scored high enough to be worth interrupting you."
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

    render_questions_considered(step)

    if step.outputs:
        st.markdown("**What it produced**")
        for key, value in step.outputs.items():
            if isinstance(value, list | dict) and len(str(value)) > 120:
                continue
            # A field with no value is not a finding. Printing "chosen question: None"
            # under a decision not to ask one reads as a gap in the record rather than as
            # the absence it is.
            if value is None:
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


# What each question is about, for a reader who did not name the probes.
_QUESTION_NAMES: dict[str, str] = {
    "probe_symptoms": "whether you have any symptoms",
    "probe_alcohol": "whether you drank",
    "probe_exertion": "whether you exercised hard",
    "probe_sleep_quality": "how you slept",
    "probe_stress": "whether you were stressed",
    "probe_travel": "whether you travelled",
    "probe_vaccination": "whether you were vaccinated",
    "probe_medication": "whether you changed medication",
    "probe_cycle": "where you are in your cycle",
}


def _question_name(probe_id: Any) -> str:
    return _QUESTION_NAMES.get(str(probe_id), str(probe_id))


def render_questions_considered(step: PipelineStepView) -> None:
    """Every question the policy weighed, and what each was worth.

    The decision to stay quiet is the one a person is most likely to want explained: it is
    the difference between being interrupted and not. Showing only the question it asked,
    and nothing about the ones it decided against, leaves that decision unexplainable.
    """
    considered = step.outputs.get("questions_considered") or []
    if not considered:
        return

    st.markdown("**Every question it weighed**")
    rows = [
        {
            "Question": _question_name(entry.get("probe_id")),
            "Worth asking": f"{entry.get('value_of_asking', 0):.3f}",
        }
        for entry in sorted(considered, key=lambda c: c.get("value_of_asking", 0), reverse=True)
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption(
        "Higher is worth more. A negative number means the answer would change what the "
        "system concludes by less than the cost of interrupting you, so it is not asked."
    )


def _value(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.3g}"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) or "none"
    return str(value)
