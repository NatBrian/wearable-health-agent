"""Today view rendering inbox, active clinical interview, last night summary, and open episodes."""

from datetime import UTC, datetime, timedelta

import streamlit as st

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


def render_inbox(
    subject_id: str, pending: PendingInteraction | None, status: SystemStatus | None = None
) -> None:
    """Render the single active pending interaction or the reassuring nothing-pending state."""
    st.subheader("📬 Inbox & AI Clinical Interview")

    if pending is None:
        # Reassuring nothing-pending state
        stat = status or get_system_status(subject_id)
        now_str = datetime.now(UTC).strftime("%H:%M UTC")
        st.success(
            f"✨ **Nothing needs your attention.** Last checked {now_str}. "
            f"**{stat.quiet_nights_streak} quiet nights** in a row."
        )
        return

    if pending.kind == "question" and pending.question:
        q = pending.question
        st.markdown("### 💬 Active AI Clinical Investigation")
        st.info(f"**Question for you:** {q.text}")
        st.caption(
            "Our algorithm detected a physiological deviation. The AI agent is asking a targeted clinical probe to evaluate your symptoms and update the Bayesian diagnostic differential."
        )

        free_text = st.text_input("Additional notes or symptoms (optional)", key="q_free_text")

        cols = st.columns(len(q.probe.answer_space) + 1)
        for idx, opt in enumerate(q.probe.answer_space):
            with cols[idx]:
                if st.button(opt.label, key=f"opt_{opt.option_id}", use_container_width=True):
                    ans = Answer(
                        probe_id=q.probe.probe_id,
                        option_id=opt.option_id,
                        free_text=free_text or None,
                        declined=False,
                    )
                    submit_answer(pending.episode_id, ans)
                    st.rerun()

        with cols[-1]:
            if st.button("Not now", key="btn_decline", use_container_width=True):
                ans = Answer(
                    probe_id=q.probe.probe_id,
                    option_id=q.probe.answer_space[0].option_id,
                    free_text=None,
                    declined=True,
                )
                submit_answer(pending.episode_id, ans)
                st.rerun()

    elif pending.kind == "measurement" and pending.measurement:
        m = pending.measurement
        st.warning(f"**Measurement requested:** {m.instruction}")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Done", key=f"m_done_{m.measurement_id}", type="primary"):
                submit_measurement_done(m.measurement_id)
                st.rerun()
        with col2:
            if st.button("Can't right now", key=f"m_cant_{m.measurement_id}"):
                st.info("Measurement skipped for today.")

    elif pending.kind == "review" and pending.draft_outcome:
        draft = pending.draft_outcome
        st.warning(f"**Review requested for Episode {pending.episode_id}**")
        st.write(f"**Draft Disposition:** `{draft.disposition.value}`")
        st.write(f"**Observation:** {draft.observation}")
        edit_prose = st.text_area("Edit outcome observation (optional)", value=draft.observation)
        rationale = st.text_input("Reviewer rationale (optional)")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Approve", key="rev_approve", type="primary"):
                submit_human_decision(
                    episode_id=pending.episode_id,
                    decision="approve",
                    edited_prose=edit_prose if edit_prose != draft.observation else None,
                    rationale=rationale or None,
                )
                st.rerun()
        with col2:
            if st.button("Reject", key="rev_reject"):
                submit_human_decision(
                    episode_id=pending.episode_id,
                    decision="reject",
                    rationale=rationale or "Rejected by human reviewer",
                )
                st.rerun()
        with col3:
            if st.button("Escalate", key="rev_escalate"):
                submit_human_decision(
                    episode_id=pending.episode_id,
                    decision="escalate",
                    rationale=rationale or "Escalated by human reviewer",
                )
                st.rerun()


def render_last_night_summary(subject_id: str) -> None:
    """Render last night status in a clean card."""
    st.subheader("🌙 Last Night Vitals & Clinical Assessment")
    end_d = datetime.now(UTC).date()
    start_d = end_d - timedelta(days=14)
    nights = list_nights(subject_id, start=start_d, end=end_d)
    usable_nights = [n for n in reversed(nights) if n.usable and n.rhr_bpm is not None]
    if not usable_nights:
        st.info("No night vitals recorded yet.")
        return

    n = usable_nights[0]
    rhr = f"{n.rhr_bpm:.1f} bpm" if n.rhr_bpm is not None else "N/A"
    dev = f"{n.deviation_bpm:+.1f} bpm" if n.deviation_bpm is not None else "N/A"
    res = f"{n.residual_bpm:+.1f} bpm" if n.residual_bpm is not None else "N/A"

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Resting Heart Rate", rhr)
    with col2:
        st.metric("Baseline Deviation", dev)
    with col3:
        st.metric("Unexplained Residual", res)
    with col4:
        st.metric("Detection Level", n.level.value)

    st.caption(
        f"Recorded for night of **{n.night_date}** with {n.coverage_minutes} minutes of valid nocturnal watch contact."
    )


def render_open_episodes(subject_id: str) -> None:
    """Render one-line summaries of open episodes."""
    st.subheader("📋 Active Clinical Episodes")
    episodes = list_episodes(subject_id)
    open_eps = [e for e in episodes if e.state.value not in ("CLOSED", "RESOLVED")]

    if not open_eps:
        st.caption("No open episodes. All physiological signals within normal bounds.")
        return

    for ep in open_eps:
        disp = ep.disposition.value if ep.disposition else "IN_PROGRESS"
        disp_icon = "🩺" if "ILLNESS" in disp else "🚨" if "ESCALATE" in disp else "🔍"
        st.write(
            f"{disp_icon} **Episode `{ep.episode_id}`** (opened {ep.opened_on}) — State: `{ep.state.value}`, Disposition: `{disp}`"
        )


def render_today_page(subject_id: str) -> None:
    """Render complete Today surface."""
    render_status_strip(subject_id)
    st.write("---")

    pending = get_pending_interaction(subject_id)
    status = get_system_status(subject_id)

    render_inbox(subject_id, pending, status)
    st.write("---")
    render_last_night_summary(subject_id)
    st.write("---")
    render_open_episodes(subject_id)
