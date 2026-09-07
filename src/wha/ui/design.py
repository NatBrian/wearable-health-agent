"""Every colour, every card, every chip. One module, so the screens look like one thing.

Streamlit gives you widgets, not a design. The previous dashboard styled things where it
needed them, so a status pill in one file and a level badge in another used different
greens for the same meaning, and nothing stopped a third from inventing a fourth.

Two rules hold this together:

* **Colour carries meaning, and the meaning is defined once.** A level colour means the
  level. A layer colour means which machine ran a step. Nothing is coloured for decoration.
* **No Streamlit internal class names.** Styling that reaches into `.st-emotion-cache-*`
  breaks silently on upgrade, and a health screen that silently loses its red is worse than
  one that never had it.

Everything here returns a string of HTML for a caller to pass to `st.markdown` with
`unsafe_allow_html=True`. Nothing here reads data.
"""

from typing import Literal

import streamlit as st

# Level colours. Text is dark on a pale ground rather than white on saturated colour: a
# health screen is read for minutes at a time, and saturated fills are tiring and print
# badly.
LEVEL_COLOURS: dict[str, tuple[str, str, str]] = {
    # level: (text, background, border)
    "GREEN": ("#0f5132", "#e6f4ea", "#a8d5b8"),
    "YELLOW": ("#664d03", "#fff6e0", "#f0d68a"),
    "RED": ("#842029", "#fdeaec", "#f0b3ba"),
    "NA": ("#41474e", "#eef0f2", "#ccd2d8"),
}

# Layer colours, matching the three halves of the system described in ARCHITECTURE.md:
# arithmetic, a language model in a fenced loop, the person, and the safety floor.
LAYER_COLOURS: dict[str, tuple[str, str, str]] = {
    "deterministic": ("#0f5132", "#e9f5ec", "#b7ddc4"),
    "agentic": ("#0a4a72", "#e8f2f9", "#aacce4"),
    "user": ("#553a7a", "#f1ecf9", "#cbb8e6"),
    "safety": ("#842029", "#fdeaec", "#f0b3ba"),
}

LAYER_NAMES: dict[str, str] = {
    "deterministic": "Arithmetic",
    "agentic": "AI",
    "user": "You",
    "safety": "Safety",
}

TONE_COLOURS: dict[str, tuple[str, str, str]] = {
    "ok": ("#0f5132", "#e6f4ea", "#a8d5b8"),
    "warn": ("#664d03", "#fff6e0", "#f0d68a"),
    "error": ("#842029", "#fdeaec", "#f0b3ba"),
    "info": ("#0a4a72", "#e8f2f9", "#aacce4"),
    "muted": ("#5b6169", "#f5f6f7", "#dfe3e7"),
}

Tone = Literal["ok", "warn", "error", "info", "muted"]

_CSS = """
<style>
  .wha-card {
    border: 1px solid #e3e6ea; border-radius: 10px; padding: 14px 16px;
    background: #ffffff; margin-bottom: 10px;
  }
  .wha-card h4 { margin: 0 0 6px 0; font-size: 0.95rem; }
  .wha-tile {
    border: 1px solid #e3e6ea; border-radius: 10px; padding: 10px 12px;
    background: #ffffff; height: 100%;
  }
  .wha-tile .label {
    font-size: 0.74rem; text-transform: uppercase; letter-spacing: .04em; color: #5b6169;
  }
  .wha-tile .value { font-size: 1.35rem; font-weight: 650; line-height: 1.25; }
  .wha-tile .note { font-size: 0.78rem; color: #5b6169; }
  .wha-chip {
    display: inline-block; padding: 2px 10px; border-radius: 999px;
    font-size: 0.76rem; font-weight: 600; border: 1px solid;
  }
  .wha-step {
    border: 1px solid; border-radius: 10px; padding: 8px 10px; min-height: 104px;
  }
  .wha-step .num { font-size: 0.72rem; font-weight: 700; opacity: .75; }
  .wha-step .name { font-size: 0.86rem; font-weight: 650; line-height: 1.2; }
  .wha-step .fig { font-size: 0.8rem; margin-top: 4px; }
  .wha-step .meta { font-size: 0.7rem; opacity: .7; margin-top: 4px; }
  .wha-step.dim { opacity: .55; }
  .wha-quote {
    border-left: 3px solid #aacce4; padding: 4px 10px; margin: 6px 0;
    background: #f7fafd; font-size: 0.86rem;
  }
  .wha-quote mark { background: #ffe9a8; padding: 0 2px; }
  .wha-sep { height: 1px; background: #e3e6ea; margin: 14px 0; }
  .wha-lede { font-size: 0.95rem; color: #333a41; }
</style>
"""


def inject() -> None:
    """Put the stylesheet on the page. Safe to call on every screen."""
    st.markdown(_CSS, unsafe_allow_html=True)


def chip(label: str, tone: str = "muted") -> str:
    """A small coloured label. `tone` is a tone name, a level, or a layer."""
    palette = TONE_COLOURS.get(tone) or LEVEL_COLOURS.get(tone) or LAYER_COLOURS.get(tone)
    fg, bg, border = palette or TONE_COLOURS["muted"]
    return (
        f'<span class="wha-chip" style="color:{fg};background:{bg};border-color:{border}">'
        f"{label}</span>"
    )


def tile(label: str, value: str, note: str = "", tone: str = "muted") -> str:
    """One headline figure with its name above and its explanation below."""
    fg, bg, border = TONE_COLOURS.get(tone) or LEVEL_COLOURS.get(tone, TONE_COLOURS["muted"])
    return (
        f'<div class="wha-tile" style="border-color:{border};background:{bg}">'
        f'<div class="label">{label}</div>'
        f'<div class="value" style="color:{fg}">{value}</div>'
        f'<div class="note">{note}</div>'
        f"</div>"
    )


def card(title: str, body_html: str) -> str:
    """A titled block. Used where a screen has several things to say at once."""
    return f'<div class="wha-card"><h4>{title}</h4>{body_html}</div>'


def step_card(
    ordinal: int,
    name: str,
    layer: str,
    figure: str | None,
    meta: str,
    dim: bool,
) -> str:
    """One numbered step in the pipeline grid, coloured by which machine ran it."""
    fg, bg, border = LAYER_COLOURS.get(layer, TONE_COLOURS["muted"])
    figure_html = f'<div class="fig">{figure}</div>' if figure else ""
    return (
        f'<div class="wha-step{" dim" if dim else ""}" '
        f'style="color:{fg};background:{bg};border-color:{border}">'
        f'<div class="num">STEP {ordinal}</div>'
        f'<div class="name">{name}</div>'
        f"{figure_html}"
        f'<div class="meta">{meta}</div>'
        f"</div>"
    )


def quote(passage: str, highlight: str | None = None) -> str:
    """A retrieved passage, with the quoted span marked inside it where it is present."""
    body = passage
    if highlight and highlight in passage:
        body = passage.replace(highlight, f"<mark>{highlight}</mark>", 1)
    return f'<div class="wha-quote">{body}</div>'


def separator() -> str:
    return '<div class="wha-sep"></div>'
