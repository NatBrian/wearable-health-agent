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

    with st.expander(_title("Reading the watch"), expanded=False):
        st.markdown(
            f"""
- The reading is taken over the sleep your watch recorded, because daytime heart rate
  reflects whatever you were doing. When the watch reports no sleep for a night, the
  window falls back to midnight to 7am and the night says so.
- At least **{config()["MIN_NOCTURNAL_MINUTES"]} minutes** of contact are needed, or the night is
  marked unusable rather than guessed at.
- Readings below **{config()["HR_PLAUSIBLE_MIN_BPM"]} bpm** or above **{config()["HR_PLAUSIBLE_MAX_BPM"]} bpm**
  are treated as sensor error and dropped.
"""
        )

    with st.expander(_title("Learning your normal"), expanded=False):
        st.markdown(
            f"""
Your baseline is the middle of your recent nights, not an average, so one bad night
cannot drag it. How much it relies on you rather than on typical adults depends on how
many nights it has:

| Nights of your own | What it uses |
|---|---|
| 0 to {config()["RUNG_COLD_MAX_NIGHTS"]} | Nothing is judged yet |
| {config()["RUNG_COLD_MAX_NIGHTS"] + 1} to {config()["RUNG_PRIOR_MAX_NIGHTS"]} | Mostly typical adults |
| {config()["RUNG_PRIOR_MAX_NIGHTS"] + 1} to {config()["RUNG_SHRINKING_MAX_NIGHTS"]} | A blend |
| {config()["RUNG_SHRINKING_MAX_NIGHTS"] + 1} to {config()["RUNG_PERSONAL_MAX_NIGHTS"]} | Mostly you |
| {config()["RUNG_PERSONAL_MAX_NIGHTS"] + 1} and up | You alone |

The measure of your night-to-night spread never goes below **{config()["BASELINE_SCALE_FLOOR_BPM"]} bpm**.
Watches report whole numbers, so a run of identical nights would otherwise give a spread
of exactly zero and make every later night look infinitely unusual.
"""
        )

    with st.expander(_title("Deciding a night is worth looking at"), expanded=False):
        st.markdown(
            f"""
- Anything a recorded workout would be expected to add is subtracted first.
- What remains is compared with your usual: **{config()["DETECT_YELLOW_BPM"]} bpm** above is slightly
  raised, **{config()["DETECT_RED_BPM"]} bpm** above is clearly raised.
- A single raised night is not enough. It takes **{config()["DETECT_PERSISTENCE_NIGHTS"]} nights** in a
  row, **both clearly raised**, before anything opens. That is what keeps a late drink
  from starting an investigation, and it is exactly the rule the study these thresholds
  come from used.
"""
        )

    with st.expander(
        _title("Opening an investigation, and what the AI may do inside it"), expanded=True
    ):
        tool_names = api().get_permitted_tool_names()
        tools = "\n".join(f"- `{name}`" for name in tool_names)
        st.markdown(
            f"""
**When one opens.** Only after **{config()["DETECT_PERSISTENCE_NIGHTS"]} clearly raised nights in a
row**, both of them at that level. A clearly raised night next to a slightly raised one does
not open anything, in either order, and slightly raised nights never open anything however
many there are. Nothing opens at all until the system has at least
**{config()["BASELINE_MIN_NIGHTS_PERSONAL"]} of your own measured nights**, because before that
your normal is still mostly a general estimate.

**What it is.** A single piece of work about one run of raised nights. Only one runs at a
time, so a stretch of raised nights is looked at as one thing rather than as a series of
separate alarms. It ends by concluding, or by your nights going quiet again.

**What it does not mean.** It is not a finding, and not a statement that anything is wrong.
It means the system thinks the readings are worth explaining, and it is going to try.

Inside one, the model can only call these {len(tool_names)} read-only tools, and nothing
else. Any other request is refused and recorded:

{tools}

It cannot write to your record, send you anything, or decide whether to interrupt you.
"""
        )

    with st.expander(_title("Checking what you have told us, over time"), expanded=False):
        st.markdown(
            f"""
Anything you say about how you feel is checked against a fixed list of symptoms. This is
plain rules, not AI, and it can only ever make the system MORE cautious, never less.

Three things can happen, and the first two need a memory of what you have said before
rather than just tonight's message:

- **One symptom that keeps going.** Each symptom has its own number of nights, and the
  count runs from the first night you mentioned it. **A night you say nothing does not
  reset it**, because going quiet is not the same as getting better. It stops when you
  say the symptom has gone, or after **{config()["SYMPTOM_RUN_GAP_DAYS"]} days** with no
  mention.
- **Two symptoms close together.** Two of these within
  **{config()["SYMPTOM_COOCCURRENCE_WINDOW_NIGHTS"]} nights** of each other is enough, whether
  you mentioned them in one message or on different nights. Feeling dizzy on Monday and
  feverish on Tuesday counts as both.
- **A symptom that goes straight to urgent care**, on its own, with no waiting.

Symptoms with no good evidence behind a rule, such as dizziness, are still **written down**
so the system can ask you about them. Recording something is a much smaller claim than
deciding where you should be treated, and it is the honest place for a symptom nobody has
measured a threshold for.

While any symptom of yours is still going, an investigation **will not close as "nothing
points towards illness"**, however settled your heart rate looks. Your readings coming back
to normal is evidence about your readings.
"""
        )

    with st.expander(_title("Working out the likely cause"), expanded=False):
        st.markdown(
            f"""
The system tracks **{config()["N_CAUSES"]} possible causes** at once and considers every combination
of them being present or absent, which is {2 ** config()["N_CAUSES"]:,} possibilities. This is ordinary
arithmetic, not a model, so the same evidence always gives the same answer.
"""
        )

    with st.expander(_title("Deciding whether to interrupt you"), expanded=True):
        st.markdown(
            f"""
This is the one decision the AI does not make. Before asking anything, the system works
out how much the answer could actually change what it does. If that is worth less than
the cost of interrupting you, it stays quiet.

**That arithmetic is what keeps this quiet, not a cap.** There is also a hard limit of
**{config()["INTERRUPTION_BUDGET_PER_WEEK"]} unsolicited questions a week**, and it has
never been reached in anything this project has run. In a test run with the whole weekly
allowance unspent it asked one question and stopped, because after the answer every
remaining question was worth less than the cost of asking it.

The cap stays as a backstop. It is just not the reason you are rarely asked anything.

This is why most raised nights never produce a question.
"""
        )

    with st.expander(
        _title("Writing the conclusion, and checking it before you see it"), expanded=False
    ):
        st.markdown(
            """
- Every clinical sentence in a conclusion has to quote a span that really appears in a
  passage this system holds. A sentence that quotes nothing is removed before you see it.
- The model then reads its own draft back, and at that point it can only remove claims,
  never add them. This step can make a conclusion smaller and never larger.
- A person approves, edits, rejects or escalates the draft. Nothing reaches you as a
  settled conclusion without passing that checkpoint.
- What is kept is saved to your record, this dashboard and the tamper-evident log at the
  same time, so the copy you read is the copy that was kept.

**What this check does not do.** It proves the quoted words are really in the passage. It
does not prove the sentence built around them describes that passage fairly, so every
citation opens to the whole passage for you to read.
"""
        )

    with st.expander(_title("The safety rules, which run before anything else"), expanded=True):
        st.markdown(
            """
If you describe certain symptoms in your own words, the system stops and tells you to
seek care. That check is plain pattern matching against a fixed list, it runs
before any model is consulted, and no amount of model output can switch it off. A
language model can only **add** a flag to that list, never remove one.
"""
        )

        # THE NUMBERS IN THIS FLOOR, AND WHERE THEY CAME FROM.
        #
        # This project's standing rule is that an unevidenced clinical figure must be
        # labelled in the docs AND on the dashboard. causes.yaml had that on both sides.
        # red_flags.yaml had it on neither, while its own footer called its numbers "the
        # only place in this project where a wrong number has a real-world consequence".
        # Six of the ten are ASSUMED, which is a legitimate answer and now a visible one.
        rows = api().get_safety_rule_provenance()
        if rows:
            assumed = [r for r in rows if r["provenance"] == "ASSUMED"]
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
            if assumed:
                st.warning(
                    f"**{len(assumed)} of these {len(rows)} numbers have no published "
                    "source behind them,** and the table says which. No study was found "
                    "measuring how many nights a symptom should persist before it is "
                    "worth a same-day appointment, so those windows were chosen rather "
                    "than measured. They are set short, which means they err towards "
                    "sending you to a doctor sooner rather than later. This is disclosed "
                    "because a number nobody measured must not look the same as one "
                    "somebody did.",
                    icon="⚠️",
                )

    with st.expander(_title("Where your data goes"), expanded=False):
        st.markdown(
            """
Readings, nightly figures and the full record stay in a database file on this machine.

The one exception is the language model. Unless it is set to the offline recorded
provider, the text of a question or summary is sent to whichever model endpoint is
configured, which may be a remote service. The Settings page shows which is in use.
"""
        )
