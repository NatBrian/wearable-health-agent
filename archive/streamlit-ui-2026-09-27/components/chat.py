"""The conversation, and the sources behind every clinical sentence in it.

Two things this has to keep saying, because both are true and neither is obvious:

* The grounding check proves a quoted span exists in a passage. It does not prove the
  sentence around the quote describes the passage fairly. One reply cited two exactly
  correct passages while calling the baseline an average and naming a threshold that is
  not the threshold.
* The sorting of sentences into cited and uncited is done by the model itself, so an
  absence of warnings is not proof that everything above has a source.

The reply is not rendered from the response. It is read back from the stored transcript on
the rerun, so what the screen shows is what was actually recorded.
"""

import json
from datetime import date

import streamlit as st

from wha.ui import explain
from wha.ui.components.api import api
from wha.ui.components.citations import attribution_note, chip, drawer, is_external


def render(subject_id: str, night: date | None = None) -> str | None:
    """This conversation, the input box, and the urgency the safety rules established.

    Only the current consultation is drawn. The screen used to show the last forty turns
    whatever night they came from, so a question about Sunday sat under Monday's verdict
    and read as though it were about Monday. The agent already ended a consultation after
    a gap of several hours; the screen simply did not.

    Nothing is deleted. Earlier conversations are on the record screen in full.
    """
    st.subheader("Ask about any of this")
    st.caption(
        "Ask about your readings, or say how you feel. Anything you write is checked by "
        "fixed rules before any AI sees it. Those rules can raise how urgent this is, and "
        "the AI can never lower it."
    )

    # Scoped to the night on screen. A conversation about Sunday belongs to Sunday: once
    # Monday has been measured it moves to the record rather than sitting under Monday's
    # verdict, which is what "the chat was not cleared for the new night" meant.
    sessions = api().get_conversation_sessions(subject_id, since_night=night)
    turns = sessions[0]["turns"] if sessions else []
    earlier_here = sum(len(session["turns"]) for session in sessions[1:])
    all_sessions = api().get_conversation_sessions(subject_id)
    earlier = earlier_here + sum(len(session["turns"]) for session in all_sessions[len(sessions) :])

    if earlier and turns:
        st.caption(
            f"This is your conversation about this night. {earlier} earlier turns are kept "
            "on the record screen, under everything the system did."
        )
    elif earlier:
        st.caption(
            f"Nothing has been said about this night yet. {earlier} earlier turns are kept "
            "on the record screen, under everything the system did."
        )

    for index, turn in enumerate(turns):
        role = "user" if turn["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.write(turn["text"])
            _render_sources(turn, index)
            _render_uncited(turn)

    message = st.chat_input("Say anything, or ask a question")
    if message and message.strip():
        with st.spinner("Thinking, and checking every claim against a source..."):
            api().send_message(subject_id=subject_id, text=message.strip())
        st.rerun()

    # Urgency is read across every session, not just this one. It is monotone by design
    # and an escalation from a previous conversation is still in force.
    all_turns = [turn for session in all_sessions for turn in session["turns"]]
    with_urgency = [t for t in all_turns if t.get("urgency")]
    return str(with_urgency[-1]["urgency"]) if with_urgency else None


def _render_sources(turn: dict, index: int) -> None:
    citations = json.loads(turn.get("citations_json") or "[]")
    if not citations:
        return

    st.caption(f"Sources behind this reply: {len(citations)}. Open one to read it.")
    for position, citation in enumerate(citations):
        key = f"cite_{index}_{position}"
        if chip(citation, key=key):
            st.session_state["open_citation"] = key
        if st.session_state.get("open_citation") == key:
            with st.container(border=True):
                drawer(citation, quoted_span=citation.get("quoted_span"))
                if st.button("Close", key=f"{key}_close"):
                    st.session_state.pop("open_citation", None)
                    st.rerun()

    if any(is_external(c.get("source_id", "")) for c in citations):
        note = attribution_note()
        if note:
            st.caption(note)


def _render_uncited(turn: dict) -> None:
    uncited = json.loads(turn.get("uncited_json") or "[]")
    if not uncited:
        return

    st.warning(
        "**Not from a source.** The following came from the AI's general knowledge, not "
        "from anything held in this system. Treat it as a starting point to check.",
        icon="⚠️",
    )
    for note in uncited:
        st.caption(f"• {note}")
    st.caption(
        "This sorting is done by the AI itself and it can miss things, so a sentence "
        "above with no source shown is not proof that one exists."
    )
    st.caption(explain.text("citation.what_this_means"))
