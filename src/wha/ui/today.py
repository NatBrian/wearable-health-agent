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
from wha.ui.components.citations import attribution_note, is_external, source_label
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

    # Say which window this night was actually measured over. It said "between midnight
    # and 7am" on every night, including the ones measured over the sleep the watch
    # recorded, which is the design decision this project is proudest of. The History page
    # described it correctly and the main screen did not.
    over_sleep = getattr(n, "rhr_window_source", "clock") == "sleep"
    window_words = (
        "over the sleep your watch recorded"
        if over_sleep
        else "between midnight and 7am, because no sleep was recorded"
    )
    st.caption(
        f"Night of {n.night_date}. Your watch was in contact for "
        f"{n.coverage_minutes} minutes {window_words}."
    )

    with st.expander("Show the numbers"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Resting heart rate", f"{n.rhr_bpm:.1f} bpm")
            # It is the MEDIAN across the window, not a minimum. A lowest sustained rate
            # is a different statistic and would move for different reasons.
            st.caption(f"The middle of your readings across that window, taken {window_words}.")
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
                "The same difference after subtracting what a recorded workout would be "
                "expected to add. This is what gets judged. Short sleep is NOT subtracted: "
                "it is weighed as one of the twelve explanations instead, because "
                "subtracting an uncertain quantity would manufacture confidence."
            )

        st.write(f"In words: {describe_bpm_difference(n.residual_bpm)}.")
        st.caption(f"Internal level for this night: {phrase.technical}")


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
                        st.caption(
                            f"**{c['title']}** — {source_label(c['source_id'])} "
                            f"(`{c['source_id']}`)"
                        )
                        st.caption(f'"{" ".join(str(c["passage"]).split())[:400]}"')
                    if any(is_external(c["source_id"]) for c in citations):
                        st.caption(attribution_note())
            if uncited:
                st.warning(
                    "**Not from a cited source.** The following came from the AI's own "
                    "general knowledge, not from anything in this system's references. "
                    "Treat it as a starting point to check, not as evidence.",
                    icon="⚠️",
                )
                for note in uncited:
                    st.caption(f"• {note}")
                # The label is a floor, not a guarantee, and the panel implied otherwise.
                #
                # Sorting its own sentences into cited and uncited is done by the AI. In a
                # real transcript it wrote "that's reassuring" straight into the reply with
                # no warning, then on the next turn correctly moved a similar sentence into
                # this box. A reader who trusts the box to be complete is trusting the
                # model to have caught itself.
                st.caption(
                    "This sorting is done by the AI itself and it can miss things. A "
                    "sentence in the reply above with no source shown is not proof that "
                    "one exists. Anything not quoted from a named source is a starting "
                    "point to check."
                )

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
    """What the rules concluded, when, and whether you have dealt with it.

    A "see a doctor today" banner from eleven days ago sat here with no date on it and no
    way to clear it. A red banner that never goes away is one you learn to ignore, which is
    the alarm fatigue this project cites in its own constants.

    Nothing here lowers an urgency. The ratchet is untouched and History keeps it. What
    changes is that the banner says how old it is, and that saying you have seen somebody
    stops it repeating an instruction with "today" in it for a fortnight.
    """
    state = api().get_urgency(subject_id)
    days_ago = state.get("days_ago")
    set_on = str(state.get("set_on") or "")[:10]

    if state.get("cleared"):
        st.info(
            f"**You said you have seen somebody about this.** The {urgency.replace('_', ' ')} "
            f"conclusion from {set_on} is still in your history and has not been removed. "
            "If anything changes, say so and the rules will read it again."
        )
        return

    if state.get("stale"):
        st.warning(
            f"**This was set {days_ago} days ago, on {set_on}, and said to seek care that "
            "day.** It has not been repeated since and this system has no way to know what "
            "happened. It is not saying you are fine now."
        )
    elif urgency == "urgent":
        st.error("**This needs medical attention today.**")
    else:
        st.warning("**You should see a doctor today.**")

    if days_ago is not None and not state.get("stale") and days_ago > 0:
        st.caption(f"Set on {set_on}, {days_ago} day{'s' if days_ago != 1 else ''} ago.")

    reason = api().latest_urgency_reason(subject_id)
    if reason:
        st.info(reason)
    st.caption(
        "Decided by a fixed rule from what you told it, not by the AI. The AI cannot "
        "lower this. Open **Summary for your doctor** below to take the detail with you."
    )

    if st.button("I have seen someone about this", key="urgency_seen"):
        api().acknowledge_urgency(subject_id)
        st.rerun()


def render_handover(subject_id: str) -> None:
    """Something to hand a clinician, so "seek care" is not the last useful thing said."""

    with st.expander("Summary for your doctor"):
        st.caption(
            "Everything here is either measured by your watch or something you said, with "
            "the time it was said. Nothing is invented and nothing here is a diagnosis. "
            "The structure is the one clinicians use for handovers."
        )
        if st.button("Build the summary", key="handover_build"):
            # The API returns the rendered SBAR text in "text". This called `.as_text()`
            # on the result, which worked while the dashboard held a service object and
            # crashed the WHOLE Today page with AttributeError once the HTTP boundary put
            # a dict there. Found by clicking the button, not by the suite. See
            # `ApiClient.localise` for the same mistake caught once before.
            payload = api().build_handover(subject_id)
            st.session_state["handover_text"] = payload.get("text", "")
            if not payload:
                st.error(
                    "The summary could not be built. The API did not answer. "
                    "Nothing about your readings has changed."
                )

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
