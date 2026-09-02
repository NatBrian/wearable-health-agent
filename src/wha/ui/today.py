"""Today view: what happened last night, and anything that needs the person."""

from datetime import timedelta

import streamlit as st

from wha.clock import local_today
from wha.constants import RECENT_NIGHTS_WINDOW
from wha.models import (
    Answer,
    PendingInteraction,
    SystemStatus,
)
from wha.service.episodes import (
    get_pending_interaction,
    list_episodes,
    submit_answer,
    submit_human_decision,
    submit_measurement_done,
)
from wha.service.nights import list_nights
from wha.service.status import get_system_status
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
        stat = status or get_system_status(subject_id)
        streak = stat.quiet_nights_streak
        if streak <= 0:
            st.success("**Nothing needs you right now.**")
        else:
            nights_word = "night" if streak == 1 else "nights"
            st.success(f"**Nothing needs you right now.** {streak} quiet {nights_word} in a row.")

        # Missing nights are stated rather than folded into the reassurance above. The
        # streak used to include them, so a watch that recorded three nights of seven
        # still reported seven quiet ones.
        #
        # Phrased as what the watch did record, over a named period, rather than "4 of the
        # last 7 nights". That reads as a quota, and the system has real night-count
        # thresholds elsewhere, so a bare 7 here is indistinguishable from one of those.
        missing = stat.unmeasured_recent_nights
        if missing:
            recorded = RECENT_NIGHTS_WINDOW - missing
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
                    submit_answer(
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
                submit_answer(
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
                submit_measurement_done(m.measurement_id)
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
                submit_human_decision(
                    episode_id=pending.episode_id,
                    decision="approve",
                    edited_prose=edit_prose if edit_prose != draft.observation else None,
                    rationale=rationale or None,
                )
                st.rerun()
        with col2:
            if st.button("Not right", key="rev_reject"):
                submit_human_decision(
                    episode_id=pending.episode_id,
                    decision="reject",
                    rationale=rationale or "Rejected on review",
                )
                st.rerun()
        with col3:
            if st.button("This needs a doctor", key="rev_escalate"):
                submit_human_decision(
                    episode_id=pending.episode_id,
                    decision="escalate",
                    rationale=rationale or "Escalated on review",
                )
                st.rerun()


def render_last_night_summary(subject_id: str, status: SystemStatus | None = None) -> None:
    """Say plainly how last night looked, with the numbers available underneath."""
    st.subheader("Last night")
    stat = status or get_system_status(subject_id)
    end_d = local_today()
    start_d = end_d - timedelta(days=14)
    nights = list_nights(subject_id, start=start_d, end=end_d)
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


def render_open_episodes(subject_id: str) -> None:
    """List anything currently being looked into."""
    st.subheader("Being looked into")
    episodes = list_episodes(subject_id)
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


def render_today_page(subject_id: str) -> None:
    """Render the Today surface."""
    render_status_strip(subject_id)
    st.write("---")

    pending = get_pending_interaction(subject_id)
    status = get_system_status(subject_id)

    render_inbox(subject_id, pending, status)
    st.write("---")
    render_last_night_summary(subject_id, status)
    st.write("---")
    render_open_episodes(subject_id)
