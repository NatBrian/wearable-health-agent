"""How the system works, by topic, beside the same system walked night by night.

**These are not a second set of steps.** The tab beside this one walks a single night
through the twenty numbered steps the system actually runs. This one groups the same
machinery by topic, because "what is the safety floor" is a question about the system
rather than about last night.

That distinction was invisible in the first version: both tabs presented a numbered list
starting at 1, with different names, different counts and a different order, so a reader
could reasonably conclude the system does two different things. The topics are no longer
numbered on their own; each one says which steps it covers, and `TOPIC_STEPS` below is
asserted to cover all twenty so the two tabs cannot drift apart.

Carried over from the previous Audit page and deliberately not rewritten, because of the
property it already has: every threshold quoted here is read from the running system at
render time rather than written into the prose. The version before it hardcoded its
figures and had drifted, claiming a coverage minimum it did not use, a scale floor it did
not use, baseline tiers that did not match the ladder, and tool names not in the registry.

The pipeline view answers "what happened on this night". This answers "how does any of
this work", which is a different question and still worth a page.
"""

import streamlit as st

from wha import wording
from wha.ui.components.api import api, config

# Which pipeline steps each topic explains. Checked by a test: every step
# must appear under exactly the topics that describe it, so a step added to the pipeline
# cannot go unexplained here, and this page cannot claim a step the pipeline does not have.
# In the order the steps run, each topic covering a contiguous block, nothing skipped and
# nothing overlapping. The first version grouped by subject matter instead, so the ranges
# jumped about: steps 19 and 20 sat fourth, one topic claimed 8 to 10 and 15 to 18 with
# other topics in between, and step 18 appeared twice while nothing named 15 to 17.
# Grouping that reads well and ordering that matches the pipeline are not in tension here;
# the first version simply kept the old explainer's order.
TOPIC_STEPS: dict[str, tuple[int, ...]] = {
    "Reading the watch": (1, 2, 3, 4),
    "Learning your normal": (5,),
    "Deciding a night is worth looking at": (6, 7),
    # Step 8 was added on 7 September 2026. The rules that read what you have TOLD the
    # system ran before the agent from the beginning and appeared on neither tab, so the
    # two screens that promise to show every step both left out the layer that can
    # override all the others.
    "Checking what you have told us, over time": (8,),
    "Opening an investigation, and what the AI may do inside it": (9, 10, 11),
    "Working out the likely cause": (12,),
    "Deciding whether to interrupt you": (13, 14, 15),
    "Writing the conclusion, and checking it before you see it": (16, 17, 18, 19),
    "The safety rules, which run before anything else": (20, 21),
    # Not a step. It is true of every step, and giving it a number would have put a ninth
    # entry in a list of things that happen in order.
    "Where your data goes": (),
}


def _title(topic: str) -> str:
    """A topic, and the steps on the other tab that it covers."""
    steps = TOPIC_STEPS[topic]
    if not steps:
        return f"{topic}  (not a step: this is true of all of them)"
    if len(steps) == 1:
        return f"{topic}  (step {steps[0]})"
    runs: list[str] = []
    start = previous = steps[0]
    for value in steps[1:] + (None,):
        if value == previous + 1:
            previous = value
            continue
        runs.append(str(start) if start == previous else f"{start} to {previous}")
        if value is not None:
            start = previous = value
    return f"{topic}  (steps {', '.join(runs)})"


def render(subject_id: str) -> None:
    """Explain the pipeline, with every figure read from the code."""
    st.subheader("How the system works, by topic")
    st.caption(
        "The tab beside this one walks one night through every step in the order they "
        "run. This is the same machinery grouped by topic, and each heading says which of "
        "those steps it covers. Every number below is read from the running system rather "
        "than written into this page."
    )

    tool_names = api().get_permitted_tool_names()
    rows = api().get_safety_rule_provenance() or []
    assumed = [r for r in rows if r["provenance"] == "ASSUMED"]
    titles = list(TOPIC_STEPS)

    with st.expander(_title(titles[0]), expanded=False):
        st.markdown(topic_body(1, config=config()))

    with st.expander(_title(titles[1]), expanded=False):
        st.markdown(topic_body(2, config=config()))

    with st.expander(_title(titles[2]), expanded=False):
        st.markdown(topic_body(3, config=config()))

    with st.expander(_title(titles[3]), expanded=False):
        st.markdown(topic_body(4, config=config()))

    with st.expander(_title(titles[4]), expanded=True):
        st.markdown(topic_body(5, config=config(), tool_names=tool_names))

    with st.expander(_title(titles[5]), expanded=False):
        st.markdown(topic_body(6, config=config()))

    with st.expander(_title(titles[6]), expanded=True):
        st.markdown(topic_body(7, config=config()))

    with st.expander(_title(titles[7]), expanded=False):
        st.markdown(topic_body(8, config=config()))

    with st.expander(_title(titles[8]), expanded=True):
        st.markdown(topic_body(9, config=config(), assumed=len(assumed), rows=len(rows)))
        if rows:
            st.dataframe(
                [
                    {
                        "Rule": r["rule"],
                        "When it fires": r["number"],
                        "Where the number came from": (
                            "no published source found"
                            if r["provenance"] == "ASSUMED"
                            else "worked out from other figures here"
                            if r["provenance"] == "DERIVED"
                            else "a published study"
                        ),
                    }
                    for r in rows
                ],
                use_container_width=True,
                hide_index=True,
            )

    with st.expander(_title(titles[9]), expanded=False):
        st.markdown(topic_body(10, config=config()))


def topic_body(
    n: int,
    *,
    config: dict,
    tool_names: list[str] | tuple[str, ...] = (),
    assumed: int = 0,
    rows: int = 0,
    device: str = "this machine",
    surface: str = "this dashboard",
) -> str:
    """The shared topic text with every figure filled from the running system.

    The phone renders the same keys with the same values (device "this phone",
    surface "this app"), so the two surfaces describe the machinery identically.
    """
    tools = "\n".join(f"- `{name}`" for name in tool_names)
    n_causes = config["N_CAUSES"]
    return wording.text(f"topic.{n}.body").format(
        MIN_NOCTURNAL_MINUTES=config["MIN_NOCTURNAL_MINUTES"],
        HR_PLAUSIBLE_MIN_BPM=config["HR_PLAUSIBLE_MIN_BPM"],
        HR_PLAUSIBLE_MAX_BPM=config["HR_PLAUSIBLE_MAX_BPM"],
        RUNG_COLD_MAX_NIGHTS=config["RUNG_COLD_MAX_NIGHTS"],
        COLD_MAX_PLUS_ONE=config["RUNG_COLD_MAX_NIGHTS"] + 1,
        RUNG_PRIOR_MAX_NIGHTS=config["RUNG_PRIOR_MAX_NIGHTS"],
        PRIOR_MAX_PLUS_ONE=config["RUNG_PRIOR_MAX_NIGHTS"] + 1,
        RUNG_SHRINKING_MAX_NIGHTS=config["RUNG_SHRINKING_MAX_NIGHTS"],
        SHRINKING_MAX_PLUS_ONE=config["RUNG_SHRINKING_MAX_NIGHTS"] + 1,
        RUNG_PERSONAL_MAX_NIGHTS=config["RUNG_PERSONAL_MAX_NIGHTS"],
        PERSONAL_MAX_PLUS_ONE=config["RUNG_PERSONAL_MAX_NIGHTS"] + 1,
        BASELINE_SCALE_FLOOR_BPM=config["BASELINE_SCALE_FLOOR_BPM"],
        DETECT_YELLOW_BPM=config["DETECT_YELLOW_BPM"],
        DETECT_RED_BPM=config["DETECT_RED_BPM"],
        DETECT_PERSISTENCE_NIGHTS=config["DETECT_PERSISTENCE_NIGHTS"],
        SYMPTOM_RUN_GAP_DAYS=config["SYMPTOM_RUN_GAP_DAYS"],
        SYMPTOM_COOCCURRENCE_WINDOW_NIGHTS=config["SYMPTOM_COOCCURRENCE_WINDOW_NIGHTS"],
        BASELINE_MIN_NIGHTS_PERSONAL=config["BASELINE_MIN_NIGHTS_PERSONAL"],
        TOOL_COUNT=len(tool_names),
        TOOLS=tools,
        N_CAUSES=n_causes,
        N_CAUSES_POWER=f"{2**n_causes:,}",
        INTERRUPTION_BUDGET_PER_WEEK=config["INTERRUPTION_BUDGET_PER_WEEK"],
        ASSUMED_COUNT=assumed,
        ROW_COUNT=rows,
        DEVICE=device,
        SURFACE=surface,
    )
