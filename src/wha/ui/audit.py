"""Audit: what the system did with your data, and proof the record has not been altered.

Every threshold quoted on this page is read from the constants and the knowledge tables
at render time rather than written into the prose. The previous version hardcoded its
figures and had drifted away from the code: it claimed a 120-minute coverage minimum
against an actual 180, a 1.0 bpm scale floor against an actual 1.5, baseline tiers that
did not match the ladder, and tool names that are not in the registry. It also promised
"zero cloud leakage" while the language model runs against a remote endpoint. Numbers
written by hand in an explanation drift; numbers read from the source cannot.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from wha.constants import (
    BASELINE_SCALE_FLOOR_BPM,
    DETECT_PERSISTENCE_NIGHTS,
    DETECT_RED_BPM,
    DETECT_YELLOW_BPM,
    HR_PLAUSIBLE_MAX_BPM,
    HR_PLAUSIBLE_MIN_BPM,
    INTERRUPTION_BUDGET_PER_WEEK,
    MIN_NOCTURNAL_MINUTES,
    N_CAUSES,
    RUNG_COLD_MAX_NIGHTS,
    RUNG_PERSONAL_MAX_NIGHTS,
    RUNG_PRIOR_MAX_NIGHTS,
    RUNG_SHRINKING_MAX_NIGHTS,
)
from wha.models import AuditFilter
from wha.service.audit import (
    count_audit_events,
    export_audit,
    get_permitted_tool_names,
    list_plain_records,
    query_audit,
    verify_hash_chain,
)
from wha.service.episodes import get_episode, list_episodes
from wha.ui.components.status_strip import render_status_strip
from wha.ui.components.wording import disposition_phrase, episode_state_phrase


def render_hash_chain_panel(subject_id: str) -> bool:
    """Say whether the record has been altered since it was written."""
    st.subheader("Has the record been changed?")
    intact, bad_id = verify_hash_chain(subject_id)

    # An empty chain verifies. Reporting "the record is intact" over zero entries is a
    # green tick for something never checked, on the one page whose whole purpose is to
    # be trustworthy. A new install has no entries until the agent runs for the first time.
    if intact and count_audit_events(subject_id) == 0:
        st.info(
            "**Nothing has been recorded yet.** The record fills in the first time the AI "
            "investigates a night. There is nothing here to verify."
        )
        return True

    if intact:
        st.success(
            "**No. The record is intact.** Every entry still matches the fingerprint "
            "taken when it was written, and each fingerprint includes the one before it. "
            "Changing or removing any entry after the fact would break the sequence from "
            "that point on."
        )
        return True

    st.error(
        f"**The record has been altered.** The sequence breaks at entry `{bad_id}`. "
        "Everything before that point is still intact; nothing after it can be trusted."
    )
    return False


def render_how_it_works(subject_id: str) -> None:
    """Explain the pipeline, with every figure read from the code."""
    st.subheader("How a night gets judged")
    st.caption("The numbers below are read from the running system, not written into this page.")

    with st.expander("1. Reading the watch", expanded=False):
        st.markdown(
            f"""
- Only the window from midnight to 7am is used, because daytime heart rate reflects
  whatever you were doing.
- At least **{MIN_NOCTURNAL_MINUTES} minutes** of contact are needed, or the night is
  marked unusable rather than guessed at.
- Readings below **{HR_PLAUSIBLE_MIN_BPM} bpm** or above **{HR_PLAUSIBLE_MAX_BPM} bpm**
  are treated as sensor error and dropped.
"""
        )

    with st.expander("2. Learning your normal", expanded=False):
        st.markdown(
            f"""
Your baseline is the middle of your recent nights, not an average, so one bad night
cannot drag it. How much it relies on you rather than on typical adults depends on how
many nights it has:

| Nights of your own | What it uses |
|---|---|
| 0 to {RUNG_COLD_MAX_NIGHTS} | Nothing is judged yet |
| {RUNG_COLD_MAX_NIGHTS + 1} to {RUNG_PRIOR_MAX_NIGHTS} | Mostly typical adults |
| {RUNG_PRIOR_MAX_NIGHTS + 1} to {RUNG_SHRINKING_MAX_NIGHTS} | A blend |
| {RUNG_SHRINKING_MAX_NIGHTS + 1} to {RUNG_PERSONAL_MAX_NIGHTS} | Mostly you |
| {RUNG_PERSONAL_MAX_NIGHTS + 1} and up | You alone |

The measure of your night-to-night spread never goes below **{BASELINE_SCALE_FLOOR_BPM} bpm**.
Watches report whole numbers, so a run of identical nights would otherwise give a spread
of exactly zero and make every later night look infinitely unusual.
"""
        )

    with st.expander("3. Deciding a night is worth looking at", expanded=False):
        st.markdown(
            f"""
- Anything a recorded workout would be expected to add is subtracted first.
- What remains is compared with your usual: **{DETECT_YELLOW_BPM} bpm** above is slightly
  raised, **{DETECT_RED_BPM} bpm** above is clearly raised.
- A single raised night is not enough. It takes **{DETECT_PERSISTENCE_NIGHTS} nights** in a
  row, including at least one clearly raised, before anything opens. That is what keeps a
  late drink from starting an investigation.
"""
        )

    with st.expander("4. The safety rules, which run before anything else", expanded=True):
        st.markdown(
            """
If you describe certain symptoms in your own words, the system stops and tells you to
seek care. That check is plain pattern matching against a human-written list, it runs
before any model is consulted, and no amount of model output can switch it off. A
language model can only **add** a flag to that list, never remove one.
"""
        )

    with st.expander("5. What the AI is and is not allowed to do", expanded=True):
        tool_names = get_permitted_tool_names()
        tools = "\n".join(f"- `{name}`" for name in tool_names)
        st.markdown(
            f"""
The model can only call these {len(tool_names)} read-only tools, and nothing
else. Any other request is refused and recorded:

{tools}

It cannot write to your record, send you anything, or decide whether to interrupt you.
"""
        )

    with st.expander("6. Working out the likely cause", expanded=False):
        st.markdown(
            f"""
The system tracks **{N_CAUSES} possible causes** at once and considers every combination
of them being present or absent, which is {2**N_CAUSES:,} possibilities. This is ordinary
arithmetic, not a model, so the same evidence always gives the same answer.
"""
        )

    with st.expander("7. Deciding whether to interrupt you", expanded=True):
        st.markdown(
            f"""
This is the one decision the AI does not make. Before asking anything, the system works
out how much the answer could actually change what it does. If that is worth less than
the cost of interrupting you, it stays quiet. You are asked at most
**{INTERRUPTION_BUDGET_PER_WEEK} times a week**.

This is why most raised nights never produce a question.
"""
        )

    with st.expander("8. Where your data goes", expanded=False):
        st.markdown(
            """
Readings, nightly figures and the full record stay in a database file on this machine.

The one exception is the language model. Unless it is set to the offline recorded
provider, the text of a question or summary is sent to whichever model endpoint is
configured, which may be a remote service. The Settings page shows which is in use.
"""
        )


def render_episode_trace(subject_id: str) -> None:
    """Show what actually happened inside one investigation."""
    st.subheader("Step by step through one investigation")

    episodes = list_episodes(subject_id)
    if not episodes:
        st.caption("Nothing has been investigated yet, so there is no trace to show.")
        return

    def _describe(ep_id: str) -> str:
        ep = next((e for e in episodes if e.episode_id == ep_id), None)
        if ep is None:
            return ep_id
        phrase = (
            disposition_phrase(ep.disposition)
            if ep.disposition is not None
            else episode_state_phrase(ep.state)
        )
        return f"{ep.opened_on} - {phrase.label}"

    selected = st.selectbox(
        "Which investigation",
        options=[e.episode_id for e in episodes],
        format_func=_describe,
        key="audit_trace_selector",
    )
    detail = get_episode(selected) if selected else None
    if detail is None:
        return

    if detail.stages:
        st.markdown("**What ran, and what was skipped**")
        for stg in detail.stages:
            icon = "✅" if stg.status.value == "RAN" else "⏭️"
            duration = f" ({stg.duration_ms} ms)" if stg.duration_ms else ""
            st.write(f"{icon} **{stg.name}**{duration} — {stg.reason}")

    if detail.belief_history:
        st.markdown("**How the thinking changed as evidence arrived**")
        for seq, trigger, belief in detail.belief_history:
            if not belief.marginals:
                continue
            top_cause, top_prob = max(belief.marginals.items(), key=lambda x: x[1])
            st.write(
                f"Step {seq} (after {trigger}): most likely **{top_cause}** at "
                f"{top_prob:.0%}, chance of illness {belief.p_illness:.0%}"
            )

    if detail.outcome:
        phrase = disposition_phrase(detail.outcome.disposition)
        st.markdown("**What it concluded**")
        st.info(f"**{phrase.label}.** {detail.outcome.observation}")
        st.caption(
            f"Internal disposition `{phrase.technical}`, confidence {detail.outcome.confidence}."
        )


def render_audit_table(subject_id: str, f: AuditFilter, limit: int = 50, offset: int = 0) -> None:
    """Render the event log."""
    st.subheader("Every recorded action")
    events = query_audit(f, limit=limit, offset=offset)

    if not events:
        st.info("Nothing matches those filters.")
        return

    data = []
    for e in events:
        data.append(
            {
                "When (UTC)": e.timestamp_utc.strftime("%Y-%m-%d %H:%M:%S"),
                "Who": e.actor,
                "What": e.operation,
                "Tool used": e.tool_name or "-",
                "Allowed": e.permission_decision or "-",
                "Safety": e.safety_event or "-",
                "Unaltered": "yes" if e.hash_ok else "NO",
                "Investigation": e.episode_id or "-",
                "Entry id": e.event_id,
            }
        )

    st.dataframe(pd.DataFrame(data), use_container_width=True)
    st.caption(
        "'Who' is either you, the scheduled nightly job, or the AI agent. "
        "'Allowed' records whether a tool request was permitted or refused."
    )


def render_plain_record(subject_id: str) -> None:
    """What happened, in sentences, before any of the technical detail.

    The event table is precise and unreadable to anyone who did not build the system. This
    page exists so a person can understand what was done with their data, which means the
    first thing on it has to be readable.
    """
    st.subheader("What happened, night by night")
    records = list_plain_records(subject_id, limit=25)

    if not records:
        st.info(
            "Nothing has been recorded yet. Entries appear here once your watch sends data "
            "and a night has been measured."
        )
        return

    for rec in records:
        when = str(rec["timestamp_utc"])[:16].replace("T", " ")
        if rec["operation"] == "nightly" and rec["night"]:
            title = f"Night of {rec['night']}"
        elif rec["operation"] == "ingest":
            title = "Data arrived from your watch"
        else:
            title = rec["operation"]

        with st.container(border=True):
            st.markdown(f"**{title}**")
            st.caption(f"Recorded {when} UTC")
            for line in rec["sentences"]:
                st.write(line)
            with st.expander("The exact figures behind this"):
                st.json(rec["detail"])


def render_audit_page(subject_id: str) -> None:
    """Render the Audit page."""
    render_status_strip(subject_id)
    st.write("---")

    st.title("The record")
    st.caption(
        "Everything this system does is written down as it happens: each night it measured "
        "and how it judged it, every tool the AI used and every one it was refused, and "
        "every settings change. Entries are written when something actually happens, so a "
        "check that found nothing new does not appear."
    )

    render_hash_chain_panel(subject_id)
    st.write("---")
    render_plain_record(subject_id)
    st.write("---")
    render_how_it_works(subject_id)
    st.write("---")
    render_episode_trace(subject_id)
    st.write("---")

    st.subheader("Search the record")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        ep_filter = st.text_input("Investigation id", key="audit_ep_filter")
    with col2:
        actor_filter = st.text_input("Who (you, agent, scheduler)", key="audit_actor_filter")
    with col3:
        op_filter = st.text_input("What happened", key="audit_op_filter")
    with col4:
        safety_filter = st.text_input("Safety events only", key="audit_safety_filter")

    audit_f = AuditFilter(
        subject_id=subject_id,
        episode_id=ep_filter or None,
        actor=actor_filter or None,
        operation=op_filter or None,
        safety_event=safety_filter or None,
    )

    render_audit_table(subject_id, audit_f)

    st.write("---")
    st.subheader("Take a copy")
    st.caption("The exported file includes the fingerprints, so it can be checked elsewhere.")
    col_csv, col_json = st.columns(2)
    with col_csv:
        if st.button("Download as CSV", key="btn_export_csv"):
            export_path = Path("scratch") / f"audit_{subject_id}.csv"
            export_audit(audit_f, export_path)
            st.success(f"Saved to `{export_path}`")
    with col_json:
        if st.button("Download as JSON", key="btn_export_json"):
            export_path = Path("scratch") / f"audit_{subject_id}.json"
            export_audit(audit_f, export_path)
            st.success(f"Saved to `{export_path}`")
