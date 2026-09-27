"""Naming a passage's source on screen, from the labels the API serves.

The labels are constants, so `/config` carries them and this module never imports below
the API. They are not duplicated here: a second copy would drift, and the phone and the
dashboard disagreeing about who wrote a passage is the defect this replaced.
"""

from wha.ui.components.api import config


def source_label(source_id: str) -> str:
    """A human name for where a passage came from. Falls back to the repository."""
    prefixes: dict[str, str] = config().get("SOURCE_LABEL_PREFIXES", {})
    for prefix, label in prefixes.items():
        if source_id.startswith(prefix):
            return label
    return str(config().get("SOURCE_LABEL_FALLBACK", "this repository's own knowledge"))


def is_external(source_id: str) -> bool:
    """True when the passage is fetched text rather than something rendered here."""
    return source_id.startswith(str(config().get("EXTERNAL_SOURCE_PREFIX", "medlineplus")))


def medlineplus_label() -> str:
    """The credit the licence requires, in the words the constant carries."""
    return str(config().get("MEDLINEPLUS_LABEL", "MedlinePlus, National Library of Medicine"))


def attribution_note() -> str:
    """Why an external passage carries a credit, shown wherever one is."""
    return str(config().get("ATTRIBUTION_NOTE", ""))


def chip(citation: dict | object, key: str) -> bool:
    """A clickable marker naming the source. True when the reader opened it.

    A citation the reader cannot open is a badge, not evidence. This is the control that
    turns one into the other.
    """
    import streamlit as st

    title = _field(citation, "title") or "source"
    source_id = _field(citation, "source_id") or ""
    return bool(
        st.button(
            f"{title} - {source_label(source_id)}",
            key=key,
            help="Open the passage this sentence quotes",
        )
    )


def drawer(citation: dict | object, quoted_span: str | None = None) -> None:
    """The whole passage, with the quoted words marked inside it.

    The grounding check proves the quoted span really appears in the passage. It does not
    prove the sentence built around that span describes the passage fairly, and on
    5 September 2026 one did not: two passages were exactly right while the reply called
    the baseline an "average" and said a night is flagged at a threshold it is not. So the
    whole passage is here to read, and where the quote cannot be located in it, the screen
    says so instead of quietly rendering the passage as if it supported the sentence.
    """
    import streamlit as st

    from wha.ui import design, explain

    passage = str(_field(citation, "passage") or "")
    source_id = str(_field(citation, "source_id") or "")
    title = str(_field(citation, "title") or source_id)

    st.markdown(f"**{title}**")
    st.caption(f"{source_label(source_id)}  ·  `{source_id}`")

    if quoted_span and quoted_span not in passage:
        st.warning(explain.text("citation.quote_missing"))
        st.markdown(design.quote(passage), unsafe_allow_html=True)
    else:
        st.markdown(design.quote(passage, quoted_span), unsafe_allow_html=True)

    st.caption(explain.text("citation.what_this_means"))
    if is_external(source_id):
        note = attribution_note()
        if note:
            st.caption(note)


def _field(citation: dict | object, name: str) -> object:
    """Citations arrive as models from the client and as dicts from the transcript."""
    if isinstance(citation, dict):
        return citation.get(name)
    return getattr(citation, name, None)
