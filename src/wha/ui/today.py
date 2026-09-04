"""Today view: what happened last night, and anything that needs the person."""

import json
from datetime import timedelta

import streamlit as st

from wha.models import (
    Answer,
    PendingInteraction,
    SystemStatus,
)
from wha.ui.components.api import api, config, today
from wha.ui.components.status_strip import render_status_strip
from wha.ui.components.wording import (
    describe_bpm_difference,
    disposition_phrase,
    episode_state_phrase,
    level_phrase,
)


def render_inbox(
    subject_id: str, pending: PendingInteraction | None, status: SystemStatus | None = None
) -> None:
    """Render the one thing that needs the person, or say that nothing does."""
    if pending is None:
        stat = status or api().get_system_status(subject_id)
        still_learning = stat.usable_nights < config()["BASELINE_MIN_NIGHTS_PERSONAL"]
        streak = stat.quiet_nights_streak

        # A "quiet night" only means something if the night could have been anything else.
        # Below the alerting floor nothing can be flagged, so counting a streak claims
        # reassurance the system is not in a position to give, directly above a notice
        # saying it is not watching yet.
        if streak <= 0 or still_learning:
            st.success("**Nothing needs you right now.**")
        else:
            nights_word = "night" if streak == 1 else "nights"
            st.success(f"**Nothing needs you right now.** {streak} quiet {nights_word} in a row.")

        # Before the baseline is the person's own, nothing can be flagged at all, so
        # "nothing needs you right now" would read as "we checked and you are fine" when
        # the truth is that the system is not yet in a position to check.
        if still_learning:
            remaining = config()["BASELINE_MIN_NIGHTS_PERSONAL"] - stat.usable_nights
            nights_word = "night" if remaining == 1 else "nights"
            st.warning(
                f"**Not watching yet.** {remaining} more {nights_word} of sleep are needed "
                "before this system knows your normal well enough to raise anything. Until "
                "then it is learning, and it will not alert you even if a night is high.",
                icon="⏳",
            )

        # Missing nights are stated rather than folded into the reassurance above. The
        # streak used to include them, so a watch that recorded three nights of seven
        # still reported seven quiet ones.
        #
        # Phrased as what the watch did record, over a named period, rather than "4 of the
        # last 7 nights". That reads as a quota, and the system has real night-count
        # thresholds elsewhere, so a bare 7 here is indistinguishable from one of those.
        missing = stat.unmeasured_recent_nights
        if missing:
            recorded = config()["RECENT_NIGHTS_WINDOW"] - missing
            nights_word = "night" if recorded == 1 else "nights"
            st.caption(
                f"In the past week your watch recorded {recorded} {nights_word}. A night "
                "without a reading is skipped rather than guessed at, so it does not count "
                "toward learning your normal."
            )
        return

    if pending.kind == "question" and pending.question:
        q = pending.question
        st.subheader("One question for you")
        st.info(q.text)
        st.caption(
            "Your overnight heart rate was higher than usual and several things could "
            "explain it. This is the single question whose answer would most change what "
            "we think, which is why it is the only one being asked."
        )

        free_text = st.text_input(
            "Anything else you want to add (optional)",
            key="q_free_text",
            placeholder="For example: sore throat since yesterday",
        )

        cols = st.columns(len(q.probe.answer_space) + 1)
        for idx, opt in enumerate(q.probe.answer_space):
            with cols[idx]:
                if st.button(opt.label, key=f"opt_{opt.option_id}", use_container_width=True):
                    api().submit_answer(
                        pending.episode_id,
                        Answer(
                            probe_id=q.probe.probe_id,
                            option_id=opt.option_id,
                            free_text=free_text or None,
                            declined=False,
                        ),
                    )
                    st.rerun()

        with cols[-1]:
            if st.button("Skip", key="btn_decline", use_container_width=True):
                api().submit_answer(
                    pending.episode_id,
                    Answer(
                        probe_id=q.probe.probe_id,
                        option_id=q.probe.answer_space[0].option_id,
                        free_text=None,
                        declined=True,
                    ),
                )
                st.rerun()

        st.caption("Skipping is fine. You will not be asked this again for this episode.")

    elif pending.kind == "measurement" and pending.measurement:
        m = pending.measurement
        st.subheader("A quick reading would help")
        st.warning(m.instruction)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("I've done it", key=f"m_done_{m.measurement_id}", type="primary"):
                api().submit_measurement_done(m.measurement_id)
                st.rerun()
        with col2:
            if st.button("Not right now", key=f"m_cant_{m.measurement_id}"):
                st.info("No problem. This will be skipped for today.")

    elif pending.kind == "review" and pending.draft_outcome:
        draft = pending.draft_outcome
        phrase = disposition_phrase(draft.disposition)
        st.subheader("A summary is ready to check")
        st.write(f"**Conclusion:** {phrase.label}")
        st.caption(phrase.explanation)
        st.write(draft.observation)

        edit_prose = st.text_area("Change the wording (optional)", value=draft.observation)
        rationale = st.text_input("Why (optional)")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Looks right", key="rev_approve", type="primary"):
                api().submit_human_decision(
                    episode_id=pending.episode_id,
                    decision="approve",
                    edited_prose=edit_prose if edit_prose != draft.observation else None,
                    rationale=rationale or None,
                )
                st.rerun()
        with col2:
            if st.button("Not right", key="rev_reject"):
                api().submit_human_decision(
                    episode_id=pending.episode_id,
                    decision="reject",
                    rationale=rationale or "Rejected on review",
                )
                st.rerun()
        with col3:
            if st.button("This needs a doctor", key="rev_escalate"):
                api().submit_human_decision(
                    episode_id=pending.episode_id,
                    decision="escalate",
                    rationale=rationale or "Escalated on review",
                )
                st.rerun()


def render_last_night_summary(subject_id: str, status: SystemStatus | None = None) -> None:
    """Say plainly how last night looked, with the numbers available underneath."""
    st.subheader("Last night")
    stat = status or api().get_system_status(subject_id)
    end_d = today()
    start_d = end_d - timedelta(days=14)
    nights = api().list_nights(subject_id, start=start_d, end=end_d)
    usable_nights = [n for n in reversed(nights) if n.usable and n.rhr_bpm is not None]

    if not usable_nights:
        st.info("No nights recorded yet. Wear the watch overnight and readings will appear here.")
        return

    n = usable_nights[0]
    # The rung decides whether "your usual range" is a claim this system has earned.
    phrase = level_phrase(n.level, rung=stat.rung)

    if n.level.value == "GREEN":
        st.success(f"**{phrase.label}.** {phrase.explanation}")
    elif n.level.value == "YELLOW":
        st.warning(f"**{phrase.label}.** {phrase.explanation}")
    elif n.level.value == "RED":
        st.error(f"**{phrase.label}.** {phrase.explanation}")
    else:
        st.info(f"**{phrase.label}.** {phrase.explanation}")

    st.caption(
        f"Night of {n.night_date}. Your watch was in contact for "
        f"{n.coverage_minutes} minutes between midnight and 7am."
    )

    with st.expander("Show the numbers"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Resting heart rate", f"{n.rhr_bpm:.1f} bpm")
            st.caption("Your lowest sustained rate between midnight and 7am.")
        with col2:
            st.metric(
                "Compared with your usual",
                f"{n.deviation_bpm:+.1f} bpm" if n.deviation_bpm is not None else "n/a",
            )
            st.caption("How far this night sat above or below your own baseline.")
        with col3:
            st.metric(
                "After known causes",
                f"{n.residual_bpm:+.1f} bpm" if n.residual_bpm is not None else "n/a",
            )
            st.caption(
                "The same difference after subtracting what a recorded workout or "
                "short sleep would be expected to add. This is what gets judged."
            )

        st.write(f"In words: {describe_bpm_difference(n.residual_bpm)}.")
        st.caption(f"Internal level for this night: {phrase.technical}")

        # The forecast. It ran for the first time on 4 September 2026: the model existed,
        # was tested, and was called by nothing, so every night read NOT_RUN. It is shown
        # here and nowhere near a decision, because it is advisory and is not evidence in
        # the belief model.
        if n.forecast_status == "OK" and n.forecast_bpm is not None:
            st.write("---")
            st.write(
                f"**A second opinion, for interest.** Before seeing last night, a "
                f"forecasting model trained on time series expected about "
                f"{n.forecast_bpm:.1f} bpm from the shape of your recent nights."
            )
            if n.rhr_bpm is not None:
                gap = n.rhr_bpm - n.forecast_bpm
                st.caption(
                    f"Your actual reading was {n.rhr_bpm:.1f} bpm, which is "
                    f"{abs(gap):.1f} bpm {'above' if gap >= 0 else 'below'} what it "
                    "expected. This changes nothing. It does not decide whether a night "
                    "is looked into and it is not used to work out why. It is here so you "
                    "can see whether the night was a surprise given the recent trend, "
                    "which is a different question from whether it was high for you."
                )
        elif n.forecast_status == "TOO_FEW_NIGHTS":
            st.caption(
                "The forecasting model needs a few more nights before it will say "
                "anything, and declines rather than guessing."
            )


def render_open_episodes(subject_id: str) -> None:
    """List anything currently being looked into."""
    st.subheader("Being looked into")
    episodes = api().list_episodes(subject_id)
    open_eps = [e for e in episodes if e.state.value not in ("CLOSED", "RESOLVED")]

    if not open_eps:
        st.caption("Nothing open. Quiet nights are not shown here.")
        return

    for ep in open_eps:
        state = episode_state_phrase(ep.state)
        st.write(f"**{state.label}** — started {ep.opened_on}")
        st.caption(state.explanation)
        if ep.disposition is not None:
            phrase = disposition_phrase(ep.disposition)
            st.caption(f"So far: {phrase.label}")
        with st.expander("Reference"):
            st.caption(f"Investigation id `{ep.episode_id}`, internal state `{ep.state.value}`.")


def render_conversation(subject_id: str) -> str | None:
    """A real conversation, with the transcript, the citations and what is uncited.

    This replaced a text box over word-overlap matching that made no model call at all.
    Returns the urgency the rules have established, so the caller can draw it above
    everything else rather than under a reassurance.
    """
    st.subheader("Talk to it")
    st.caption(
        "Ask anything about your readings, or tell it how you feel. It may ask you "
        "questions back, and it answers on Telegram too. Anything you write is checked by "
        "fixed rules before any AI sees it, and those rules can raise how urgent this is "
        "but the AI can never lower it. Anything it says without a source should be "
        "flagged amber below, though that labelling depends on the AI and is not perfect."
    )

    turns = api().get_transcript(subject_id)
    for turn in turns:
        with st.chat_message("user" if turn["role"] == "user" else "assistant"):
            st.write(turn["text"])
            citations = json.loads(turn.get("citations_json") or "[]")
            uncited = json.loads(turn.get("uncited_json") or "[]")
            if citations:
                with st.expander(f"Where this comes from ({len(citations)})"):
                    for c in citations:
                        st.caption(f"**{c['title']}** (`{c['source_id']}`)")
                        st.caption(f'"{" ".join(str(c["passage"]).split())[:400]}"')
            if uncited:
                st.warning(
                    "**Not from a cited source.** The following came from the AI's own "
                    "general knowledge, not from anything in this system's references. "
                    "Treat it as a starting point to check, not as evidence.",
                    icon="⚠️",
                )
                for note in uncited:
                    st.caption(f"• {note}")

    message = st.chat_input("Say anything, or ask a question")
    if message and message.strip():
        with st.spinner("Thinking, and checking every claim against a source..."):
            # The reply is read back from the transcript on the rerun below rather than
            # rendered here, so the whole exchange is drawn from the stored record and a
            # refresh cannot show a different conversation from the one that was saved.
            api().send_message(subject_id=subject_id, text=message.strip())
        st.rerun()

    latest = [t for t in turns if t.get("urgency")]
    return str(latest[-1]["urgency"]) if latest else None


def render_urgency_banner(urgency: str, subject_id: str) -> None:
    """What the rules concluded, drawn above everything else on the page."""

    if urgency == "urgent":
        st.error("**This needs medical attention today.**")
    else:
        st.warning("**You should see a doctor today.**")

    reason = api().latest_urgency_reason(subject_id)
    if reason:
        st.info(reason)
    st.caption(
        "Decided by a fixed rule from what you told it, not by the AI. The AI cannot "
        "lower this. Open **Summary for your doctor** below to take the detail with you."
    )


def render_handover(subject_id: str) -> None:
    """Something to hand a clinician, so "seek care" is not the last useful thing said."""

    with st.expander("Summary for your doctor"):
        st.caption(
            "Everything here is either measured by your watch or something you said, with "
            "the time it was said. Nothing is invented and nothing here is a diagnosis. "
            "The structure is the one clinicians use for handovers."
        )
        if st.button("Build the summary", key="handover_build"):
            st.session_state["handover_text"] = api().build_handover(subject_id).as_text()

        text = st.session_state.get("handover_text")
        if text:
            st.code(text, language=None)
            st.download_button(
                "Download as a text file",
                data=text,
                file_name=f"summary-for-doctor-{subject_id}.txt",
                mime="text/plain",
            )


def render_today_page(subject_id: str) -> None:
    """Render the Today surface."""
    render_status_strip(subject_id)
    st.write("---")

    pending = api().get_pending_interaction(subject_id)
    status = api().get_system_status(subject_id)

    # A slot held open above everything else. What the rules have concluded is only known
    # after the conversation below has been handled, and an escalation must never be drawn
    # underneath a message saying nothing needs the person.
    inbox_slot = st.container()

    urgency = render_conversation(subject_id)
    render_handover(subject_id)

    with inbox_slot:
        if urgency:
            render_urgency_banner(urgency, subject_id)
        else:
            render_inbox(subject_id, pending, status)
    st.write("---")
    render_last_night_summary(subject_id, status)
    st.write("---")
    render_open_episodes(subject_id)
