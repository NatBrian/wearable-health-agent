"""Today: anything that needs you, then what happened last night, then the record of it.

The order is deliberate and was a real defect. Urgency established by the safety rules is
monotone: it can rise and never falls. The old page drew the inbox in the `else` of `if
urgency`, so once a person had escalated even once, no question and no review draft could
ever be shown to them again. A parked episode waiting for their approval was invisible on
the one screen that exists to surface it, and it timed out unreviewed.

What that `else` was protecting is real and is kept: the "nothing needs you" reassurance
must never be drawn under a live escalation. That is a condition on the reassurance, not
on the whole inbox.
"""

from datetime import date

import streamlit as st

from wha.api.client import ApiUnavailable
from wha.models import Answer
from wha.ui import design, explain, format
from wha.ui.components import chat, verdict
from wha.ui.components.api import api, config, unavailable
from wha.ui.components.status_bar import render as render_status_bar
from wha.ui.components.subject import resolve as resolve_subject


def _open_pipeline(night: date) -> None:
    """Hand the reader to the step-by-step view of this night."""
    st.session_state["pipeline_night"] = night.isoformat()
    st.switch_page("pages/3_The_record.py")


def render_pending(subject_id: str, pending) -> None:
    """The one thing that needs the person, drawn before anything that reports to them."""
    if pending is None:
        return

    if pending.kind == "question" and pending.question:
        question = pending.question
        st.subheader("One question for you")
        st.info(question.text)
        st.caption(
            "Several things could explain last night. This is the single question whose "
            "answer would most change what the system concludes, which is why it is the "
            "only one being asked."
        )
        free_text = st.text_input(
            "Anything else you want to add (optional)",
            key="q_free_text",
            placeholder="For example: sore throat since yesterday",
        )
        options = question.probe.answer_space
        columns = st.columns(len(options) + 1)
        for index, option in enumerate(options):
            with columns[index]:
                if st.button(option.label, key=f"opt_{option.option_id}", use_container_width=True):
                    api().submit_answer(
                        pending.episode_id,
                        Answer(
                            probe_id=question.probe.probe_id,
                            option_id=option.option_id,
                            free_text=free_text or None,
                            declined=False,
                        ),
                    )
                    st.rerun()
        with columns[-1]:
            if st.button("Skip", key="btn_decline", use_container_width=True):
                api().submit_answer(
                    pending.episode_id,
                    Answer(
                        probe_id=question.probe.probe_id,
                        option_id=options[0].option_id,
                        free_text=None,
                        declined=True,
                    ),
                )
                st.rerun()
        st.caption("Skipping is fine. You will not be asked this again for this investigation.")
        return

    if pending.kind == "review" and pending.draft_outcome:
        draft = pending.draft_outcome
        st.subheader("A summary is ready for you to check")
        st.write(f"**What it concluded:** {draft.disposition.value.replace('_', ' ').lower()}")
        st.write(draft.observation)
        st.caption(
            "Nothing here is settled until you decide. You can change the wording, say it "
            "is wrong, or send it on to a clinician."
        )

        prose = st.text_area("Change the wording (optional)", value=draft.observation)
        rationale = st.text_input("Why (optional)")
        approve, reject, escalate = st.columns(3)
        with approve:
            if st.button("Looks right", key="rev_approve", type="primary"):
                api().submit_human_decision(
                    episode_id=pending.episode_id,
                    decision="approve",
                    edited_prose=prose if prose != draft.observation else None,
                    rationale=rationale or None,
                )
                st.rerun()
        with reject:
            if st.button("Not right", key="rev_reject"):
                api().submit_human_decision(
                    episode_id=pending.episode_id,
                    decision="reject",
                    rationale=rationale or "Rejected on review",
                )
                st.rerun()
        with escalate:
            if st.button("This needs a doctor", key="rev_escalate"):
                api().submit_human_decision(
                    episode_id=pending.episode_id,
                    decision="escalate",
                    rationale=rationale or "Escalated on review",
                )
                st.rerun()
        return

    if pending.kind == "measurement" and pending.measurement:
        st.subheader("Something to measure")
        st.info(pending.measurement.instruction)
        st.caption("This is asked only where the reading would change what happens next.")


def render_reassurance(subject_id: str, status) -> None:
    """Said only when the system is actually in a position to say it."""
    rung = str(status.rung)
    if rung in {"COLD", "PRIOR_DOMINATED"}:
        # Before the baseline is the person's own, nothing can be flagged at all, so
        # "nothing needs you" would read as "we checked and you are fine" when the truth
        # is that the system is not yet in a position to check.
        st.info(f"**Still learning your normal.** {explain.rung(rung)}")
        return

    # Found on the second walkthrough: this sat directly above a night the system had
    # judged RED, with an investigation running underneath it. The sentence is about the
    # inbox and was read as being about the person's health, so it now says which.
    st.success("Nothing is waiting for you to answer right now.")
    quiet = status.quiet_nights_streak
    if quiet:
        st.caption(f"Your last {quiet} measured nights were in your usual range.")
    missing = status.unmeasured_recent_nights
    if missing:
        # A night the watch did not measure is not a quiet night. Counting it as one turns
        # missing data into reassurance.
        recorded = config()["RECENT_NIGHTS_WINDOW"] - missing
        st.caption(
            f"In the past week your watch recorded {recorded} nights. A night without a "
            "reading is skipped rather than guessed at."
        )


def render_investigation(subject_id: str) -> None:
    """What is being looked into, in the words of what it is waiting for."""
    episodes = [e for e in api().list_episodes(subject_id) if str(e.state) != "CLOSED"]
    if not episodes:
        return

    episode = episodes[0]
    st.subheader("Being looked into")
    waiting = {
        "OPEN": "The system is working through this now.",
        "AWAITING_USER": "Waiting for your answer to the question above.",
        "AWAITING_MEASUREMENT": "Waiting for a measurement from you.",
        "AWAITING_HUMAN_REVIEW": "Waiting for a person to check the draft conclusion.",
    }.get(str(episode.state), "In progress.")
    st.write(waiting)

    # What you last told it, on the screen as well as on the phone. Answering from
    # Telegram recorded the answer and showed nothing here, so somebody who replied on
    # their phone then opened the dashboard saw no sign that it had arrived.
    _render_last_answer(episode.episode_id)

    if episode.top_cause is not None:
        st.markdown(
            design.tile(
                "Most likely explanation so far",
                str(episode.top_cause).replace("_", " "),
                f"Currently {format.probability(episode.top_probability)} likely. This "
                "moves as evidence arrives and is not a diagnosis.",
            ),
            unsafe_allow_html=True,
        )

    # There is no second button here. This one and the one on the verdict card both
    # opened the same night's pipeline whenever the investigation covered last night,
    # which is the usual case, so the screen offered the same destination twice under two
    # different names. What the reader cannot get from the verdict card is which nights
    # this investigation covers, so that is what this says instead.
    first, last = episode.night_span
    if first == last:
        st.caption(
            f"This investigation is about the night of {format.night(first)}. Every step "
            "of it is on the record screen."
        )
    else:
        st.caption(
            f"This investigation covers the nights of {format.night(first)} to "
            f"{format.night(last)}. Every step of any of them is on the record screen, "
            "where you can move between them."
        )


def _render_last_answer(episode_id: str) -> None:
    """The most recent question you answered, and what you said."""
    try:
        detail = api().get_episode(episode_id)
    except (ApiUnavailable, RuntimeError, ValueError):
        return
    if detail is None:
        return

    answered = [i for i in detail.interactions if i.status == "ANSWERED"]
    if not answered:
        return

    latest = answered[-1]
    said = latest.free_text or latest.answer_option_id or ""
    when = format.local_time(api(), latest.answered_at_utc)
    st.markdown(f"**It asked:** {latest.question_text}")
    st.markdown(f"**You answered at {when}:** {said}")
    st.caption(
        "Recorded. Whatever you said is used as evidence and never overridden, and the "
        "system will only message you again if there is something worth telling you."
    )


def render_why_no_question(subject_id: str, night: date | None) -> None:
    """Why nothing was asked, when nothing was asked.

    Silence from a system that sometimes asks questions reads as a fault. It is usually a
    decision: every question it could have put was worth less than the cost of
    interrupting. That decision is recorded, so it can be said here rather than left to be
    guessed at.
    """
    if night is None:
        return
    try:
        pipeline = api().get_night_pipeline(subject_id, night)
    except (ApiUnavailable, RuntimeError, ValueError):
        return

    decide = next((s for s in pipeline.steps if s.step_id == "decide"), None)
    if decide is None or decide.outputs.get("action") in (None, "ASK"):
        return

    considered = decide.outputs.get("questions_considered") or []
    st.caption(
        "It did not ask you anything about this night, and that was a decision rather "
        f"than an oversight: it scored {len(considered)} possible questions and every one "
        "came out worth less than interrupting you for. The full scoring is on the record "
        "screen, under the step that made the decision."
        if considered
        else "It did not ask you anything about this night. No question it could have put "
        "was worth the interruption."
    )


def render_handover(subject_id: str) -> None:
    """One summary, visible before it is copied. It is your information to send."""
    st.subheader("Summary for your doctor")
    st.caption(explain.text("handover.what_it_is"))

    if st.button("Prepare the summary", key="handover_build"):
        # The API returns the rendered text in "text". This called `.as_text()` on the
        # result, which worked while the dashboard held a service object and crashed the
        # whole page with AttributeError once the HTTP boundary put a dict there. Found by
        # clicking the button, not by the suite.
        payload = api().build_handover(subject_id)
        st.session_state["handover_text"] = payload.get("text", "")

    text = st.session_state.get("handover_text")
    if text:
        st.caption("Read this before you send it. Use the copy control in the corner.")
        st.code(text, language=None)


def main() -> None:
    st.set_page_config(page_title="Today", page_icon="🌙", layout="wide")
    design.inject()

    try:
        # Resolved in one place. Reading `subjects[0]` here showed a different person on
        # this screen than on Home, with no indication that it had.
        subject = resolve_subject()
        if subject is None:
            st.warning("There is nobody to show yet.")
            return

        render_status_bar(subject)
        st.markdown(design.separator(), unsafe_allow_html=True)

        pending = api().get_pending_interaction(subject)
        status = api().get_system_status(subject)

        render_pending(subject, pending)
        if pending is None:
            render_reassurance(subject, status)

        # No end date: the application decides where the record ends. Computing it from
        # today hid the newest night whenever the watch ran ahead of the wall clock, so
        # Today showed a green night while a red one sat unshown in the record.
        nights = api().list_nights(subject, days=7)
        measured = [n for n in nights if n.usable]
        shown_night = measured[-1].night_date if measured else None
        if measured:
            detail = api().get_night_detail(subject, measured[-1].night_date)
            if detail is not None:
                verdict.render(subject, detail, on_trace=_open_pipeline)
        else:
            st.info(
                "**No night has been measured yet.** This is missing data, not a result. "
                "Nothing here says anything about your health."
            )

        render_investigation(subject)
        render_why_no_question(subject, shown_night)
        st.markdown(design.separator(), unsafe_allow_html=True)
        chat.render(subject, night=shown_night)
        st.markdown(design.separator(), unsafe_allow_html=True)
        render_handover(subject)
    except ApiUnavailable as exc:
        unavailable(exc)


if __name__ == "__main__":
    main()
