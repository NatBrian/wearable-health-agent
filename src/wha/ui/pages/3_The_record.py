"""The record: this night step by step, everything the system did, and how it all works.

Three tabs, in the order a person needs them. The first answers "why did it say that about
last night", which is the question people actually arrive with. The second is the
tamper-evident log. The third explains the machinery for anyone who wants it.

The empty case matters here more than anywhere else in the dashboard: an empty record and
a failed query must never look the same, because one of them means nothing happened and
the other means the page is lying by omission.
"""

import json
from datetime import date, datetime

import streamlit as st

from wha.api.client import ApiUnavailable
from wha.models import AuditFilter
from wha.ui import design, explain, format
from wha.ui.components import how_it_works, pipeline_graph, step_detail
from wha.ui.components.api import api, unavailable
from wha.ui.components.status_bar import render as render_status_bar
from wha.ui.components.subject import resolve as resolve_subject


def _night_options(subject: str) -> list:
    refs = api().list_pipeline_nights(subject, days=60)
    return sorted(refs, key=lambda r: r.night_date, reverse=True)


def render_pipeline_tab(subject: str) -> None:
    """One night, from watch to conclusion."""
    refs = _night_options(subject)
    if not refs:
        st.info(
            "No nights are recorded yet, so there is no pipeline to show. This is an empty "
            "record, not a failed check."
        )
        return

    remembered = st.session_state.get("pipeline_night")
    dates = [r.night_date for r in refs]
    default = date.fromisoformat(remembered) if remembered else None
    if default not in dates:
        # The most recent night is often one the watch did not measure, and opening on it
        # shows every step reading "did not run" to somebody who came here to find out
        # what happened. Open on the most recent night there is something to explain.
        measured = [r.night_date for r in refs if r.usable]
        default = measured[0] if measured else dates[0]
    index = dates.index(default)

    def _label(value: date) -> str:
        ref = next(r for r in refs if r.night_date == value)
        marker = str(ref.level) if ref.usable else "not measured"
        return f"{format.night(value)}  ({marker})"

    previous, picker, following = st.columns([1, 4, 1])
    with picker:
        selected = st.selectbox("Which night", dates, index=index, format_func=_label)
    with previous:
        if st.button("Earlier", use_container_width=True) and index + 1 < len(dates):
            selected = dates[index + 1]
            st.session_state["pipeline_night"] = selected.isoformat()
            st.rerun()
    with following:
        if st.button("Later", use_container_width=True) and index > 0:
            selected = dates[index - 1]
            st.session_state["pipeline_night"] = selected.isoformat()
            st.rerun()

    st.session_state["pipeline_night"] = selected.isoformat()

    try:
        pipeline = api().get_night_pipeline(subject, selected)
    except (ApiUnavailable, RuntimeError, ValueError) as exc:
        st.error(
            "**This night could not be loaded.** That is a failure to fetch it, not a "
            f"statement that nothing happened. ({exc})"
        )
        return

    pipeline_graph.render_headline(pipeline)
    st.markdown(design.separator(), unsafe_allow_html=True)

    graph, panel = st.columns([3, 2])
    with graph:
        st.subheader("From your watch to the conclusion")
        opened = pipeline_graph.render(pipeline)
    with panel:
        if opened:
            step_detail.render(pipeline, opened)
        else:
            st.info("Click any step on the left to see exactly what it did.")


def render_record_tab(subject: str) -> None:
    """Everything the system did, and whether the record can still be trusted."""
    st.subheader("Has the record been changed?")
    intact, bad_id = api().verify_hash_chain(subject)
    count = api().count_audit_events(subject)

    # An empty chain verifies. Reporting "the record is intact" over zero entries is a
    # green tick for something never checked, on the one page whose whole purpose is to be
    # trustworthy.
    if intact and count == 0:
        st.info(f"**Nothing has been recorded yet.** {explain.text('record.empty')}")
    elif intact:
        st.success(
            "**No. The record is intact.** Every entry still matches the fingerprint taken "
            "when it was written, and each fingerprint includes the one before it, so "
            "changing any entry after the fact would break the sequence from that point on."
        )
    else:
        st.error(
            f"**The record has been altered.** The sequence breaks at entry `{bad_id}`. "
            "Everything before that point is still intact; nothing after it can be trusted."
        )

    st.caption(explain.text("record.what_it_is"))
    st.markdown(design.separator(), unsafe_allow_html=True)

    st.subheader("What happened, in sentences")
    records = api().list_plain_records(subject, limit=25)
    if not records:
        st.info("Nothing has been recorded yet.")
    for record in records:
        when = str(record["timestamp_utc"])[:16].replace("T", " ")
        if record["operation"] == "nightly" and record.get("night"):
            title = f"Night of {record['night']}"
        elif record["operation"] == "ingest":
            title = "Data arrived from your watch"
        else:
            title = record["operation"]
        with st.container(border=True):
            st.markdown(f"**{title}**")
            st.caption(f"Recorded {when} UTC")
            for line in record["sentences"]:
                st.write(line)
            with st.expander("The exact figures behind this"):
                st.json(record["detail"])

    st.markdown(design.separator(), unsafe_allow_html=True)
    render_conversations(subject)

    st.markdown(design.separator(), unsafe_allow_html=True)
    st.subheader("Every recorded action")

    actor, operation, episode = st.columns(3)
    with actor:
        who = st.selectbox("Who did it", ["anyone", "system", "agent", "human", "monitor"])
    with operation:
        what = st.selectbox(
            "What kind of action",
            ["anything", "ingest", "nightly", "chat", "execute_tool", "human_decision", "settings"],
        )
    with episode:
        which = st.text_input("Investigation id (optional)")

    audit_filter = AuditFilter(
        subject_id=subject,
        actor=None if who == "anyone" else who,
        operation=None if what == "anything" else what,
        episode_id=which or None,
    )
    events = api().query_audit(audit_filter, limit=100)

    if not events:
        st.info("Nothing matches those filters. The record itself is not empty.")
    else:
        st.dataframe(
            [
                {
                    "When (UTC)": event.timestamp_utc.strftime("%Y-%m-%d %H:%M:%S"),
                    "Who": event.actor,
                    "What": event.operation,
                    "Tool used": event.tool_name or "-",
                    "Allowed": event.permission_decision or "-",
                    "Safety": event.safety_event or "-",
                    "Unaltered": "yes" if event.hash_ok else "NO",
                    "Investigation": event.episode_id or "-",
                    "Entry id": event.event_id,
                }
                for event in events
            ],
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            "'Who' is you, the scheduled nightly job, or the AI. 'Allowed' records whether "
            "a tool request was permitted or refused."
        )

    if st.button("Prepare a copy of the record"):
        content = api().export_audit(audit_filter, None)
        st.download_button(
            "Download it",
            data=content if isinstance(content, str) else str(content),
            file_name=f"record-{subject}.jsonl",
            mime="application/json",
        )


def render_conversations(subject: str) -> None:
    """Every conversation, kept and readable, not only the current one.

    Today shows the consultation you are in. Everything before it lives here, with the
    sources each reply quoted and whatever the safety rules made of it, because a
    conversation about your own health is part of your record rather than a scratchpad
    that scrolls away.
    """
    st.subheader("Conversations")
    sessions = api().get_conversation_sessions(subject)

    if not sessions:
        st.info(
            "You have not written to the system yet. This is an empty record, not a failed check."
        )
        return

    st.caption(
        f"{len(sessions)} conversation(s), newest first. A gap of several hours starts a "
        "new one, which is the same rule the system itself uses."
    )

    for position, session in enumerate(sessions):
        started = _moment(session.get("started_utc"))
        label = format.local_time(api(), started) if started else "time not recorded"
        turns = session["turns"]
        urgencies = [t["urgency"] for t in turns if t.get("urgency")]
        summary = f"{label} - {len(turns)} turns"
        if urgencies:
            summary += f" - safety rules reached {urgencies[-1]}"

        with st.expander(summary, expanded=position == 0):
            for turn in turns:
                who = "You" if turn["role"] == "user" else "The system"
                st.markdown(f"**{who}**")
                st.write(turn["text"])
                citations = json.loads(turn.get("citations_json") or "[]")
                if citations:
                    st.caption(
                        "Sources quoted: "
                        + ", ".join(str(c.get("title") or c.get("source_id")) for c in citations)
                    )
                uncited = json.loads(turn.get("uncited_json") or "[]")
                if uncited:
                    st.caption(
                        f"{len(uncited)} sentence(s) in this reply came from the AI's own "
                        "knowledge with no source behind them."
                    )


def _moment(value: object) -> datetime | None:
    """A stored timestamp, or nothing. Never a substitute for a missing one."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def main() -> None:
    st.set_page_config(page_title="The record", page_icon="🔍", layout="wide")
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
        st.title("The record")

        pipeline_tab, record_tab, how_tab = st.tabs(
            ["This night, step by step", "Everything the system did", "How this works"]
        )
        with pipeline_tab:
            render_pipeline_tab(subject)
        with record_tab:
            render_record_tab(subject)
        with how_tab:
            how_it_works.render(subject)
    except ApiUnavailable as exc:
        unavailable(exc)


if __name__ == "__main__":
    main()
