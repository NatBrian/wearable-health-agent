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
    "persisted_beyond_window": "symptoms that had gone on too long",
    "co_occurring_within_window": "symptoms close together in time",
    "raised_something": "this step raised something",
    "cooccurrence_window_nights": "how close together two symptoms must be, in nights",
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
            "Twelve possible causes, and every combination of them being present or "
            "absent, were weighed against how far your reading sat from your normal and "
            "against anything you have told it. That is four thousand and ninety six "
            "combinations, worked out exactly rather than sampled, so the same evidence "
            "always gives the same answer. The leading cause is "
            f"{_cause_name(out.get('top_cause'))} at "
            f"{format.probability(out.get('top_probability'))}."
        )
    if step.step_id == "safety_floor":
        reported = out.get("reported_symptoms") or []
        if not reported:
            return None
        persisted = out.get("persisted_beyond_window") or []
        together = out.get("co_occurring_within_window") or []
        if persisted:
            names = ", ".join(str(p) for p in persisted)
            return (
                f"You had been reporting {names} for longer than the number of nights this "
                "system waits before it says something, so it said something. Counting is "
                "from the first night you mentioned it to the most recent, and a night you "
                "said nothing does not reset it."
            )
        if len(together) >= 2:
            names = ", ".join(str(t) for t in together)
            return (
                f"You reported {names} within "
                f"{step.inputs.get('cooccurrence_window_nights')} nights of each other. Two "
                "of these together is enough on its own, whether you mentioned them in the "
                "same message or on different nights."
            )
        return (
            f"{len(reported)} symptom{'s' if len(reported) != 1 else ''} on record. No "
            "single one had gone on past its own limit, and no two fell close enough "
            "together, so this step raised nothing. It is still watching them."
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

    render_symptom_timeline(step)
    render_causes_weighed(step)
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


# The twelve causes, named for a reader rather than by their internal ids.
_CAUSE_NAMES: dict[str, str] = {
    "infection": "an infection coming on",
    "alcohol": "alcohol",
    "exertion": "hard exercise",
    "sleep_restriction": "too little sleep",
    "stress": "stress",
    "luteal": "the second half of your cycle",
    "vaccination": "a recent vaccination",
    "travel": "travel",
    "medication": "medication",
    "recovery_tail": "still recovering from something earlier",
    "sensor_artifact": "the watch misreading",
    "unexplained": "something not on this list",
}


def render_symptom_timeline(step: PipelineStepView) -> None:
    """Every symptom on record, how long it has run, and what would raise it.

    Showing only the outcome would repeat the mistake this step was added to fix. A
    person who is told "nothing was raised" cannot tell whether that is because the rules
    looked and were unmoved, or because nothing was ever recorded. The row for each
    symptom carries the count and the limit side by side, so the decision is checkable
    rather than announced.
    """
    reported = step.outputs.get("reported_symptoms")
    if not isinstance(reported, list) or not reported:
        return

    st.markdown("**What you have told the system, and for how long**")
    rows = []
    for entry in reported:
        if not isinstance(entry, dict):
            continue
        limit = entry.get("escalates_after_nights")
        rows.append(
            {
                # Already in ordinary words when it arrives. This screen holds no
                # content of its own, so the label travels with the data.
                "Symptom": entry.get("symptom"),
                "Nights so far": entry.get("nights_so_far"),
                "Raises it after": (
                    f"{limit} nights" if limit is not None else "does not raise on its own"
                ),
                "Still going": "yes" if entry.get("still_going") else "you said it had gone",
                "First said": entry.get("first_reported"),
                "Last said": entry.get("last_reported"),
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption(
        "Counted from the first night you mentioned something to the most recent. A night "
        "you said nothing does not reset the count, because saying nothing is not the same "
        "as being better. A symptom stops counting when you say it has gone, or after a "
        "week with no mention. Symptoms marked as not raising anything on their own are "
        "recorded so they can be asked about, not to route your care."
    )


def _cause_name(cause_id: Any) -> str:
    return _CAUSE_NAMES.get(str(cause_id), str(cause_id).replace("_", " "))


def render_causes_weighed(step: PipelineStepView) -> None:
    """All twelve causes and what the arithmetic makes of each.

    Showing only the leading one turns an explicit calculation over twelve possibilities
    into a single unexplained verdict. The whole point of doing it this way is that every
    candidate has a number attached and a person can see the ones that were ruled down as
    well as the one that came top.
    """
    marginals = step.outputs.get("marginals")
    if not isinstance(marginals, dict) or not marginals:
        return

    st.markdown("**All twelve causes it weighed**")
    rows = [
        {"Possible cause": _cause_name(cause), "How likely": format.probability(value)}
        for cause, value in sorted(marginals.items(), key=lambda kv: kv[1], reverse=True)
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption(
        "These do not add up to a hundred, and that is deliberate: more than one of them "
        "can be true on the same night, so each carries its own probability. They are "
        "probabilities on the evidence so far, not a diagnosis."
    )

    p_illness = step.outputs.get("p_illness")
    if p_illness is not None:
        st.caption(
            f"Chance an infection is contributing: {format.probability(p_illness)}. This "
            "is the single number the decision after this step is based on."
        )


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
