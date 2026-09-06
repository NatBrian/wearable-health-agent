"""Last night, said once and then shown working.

The level chip uses the system's own word, GREEN, YELLOW or RED, because the screen and
the tamper-evident record have to call the same night the same thing. The plain sentence
under it is what that word means for a person who has never seen this system.

Three numbers follow, and every one of them carries what it is and where it came from.
That is the whole point of the rewrite: a number with no explanation on a health screen is
either ignored or over-read, and both are worse than not showing it.
"""

from typing import Any

import streamlit as st

from wha.models import NightDetail
from wha.ui import design, explain, format


def render(subject_id: str, detail: NightDetail, on_trace: Any = None) -> None:
    """The verdict card. `on_trace` is called with the night when the reader asks why."""
    row = detail.row
    level = str(row.level)

    st.subheader("Last night")
    st.markdown(
        design.chip(level, level) + f"  &nbsp; <strong>{format.night(row.night_date)}</strong>",
        unsafe_allow_html=True,
    )
    # The rung is passed, not omitted. Without it this says "in your usual range" to
    # somebody whose band is still the population estimate.
    st.write(explain.level(level, str(detail.baseline.rung)))

    left, middle, right = st.columns(3)
    with left:
        st.markdown(
            design.tile("Your reading", format.bpm(row.rhr_bpm), explain.text("metric.rhr")),
            unsafe_allow_html=True,
        )
    with middle:
        st.markdown(
            design.tile(
                "Your normal",
                format.bpm(row.centre_bpm),
                f"{explain.text('metric.baseline')} Usual range {format.band(row.band_lo, row.band_hi)}.",
            ),
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            design.tile(
                "The difference",
                format.gap(row.deviation_bpm),
                explain.text("metric.gap"),
            ),
            unsafe_allow_html=True,
        )

    # Which window this night was measured over, from the night itself. This read a
    # default of "clock" for both pages, so both asserted "because no sleep was recorded"
    # on every night, including the 44 of 72 where sleep WAS recorded and the reading was
    # taken over it. A dead branch that makes a false statement about somebody's own watch
    # is worse than the vaguer wording it replaced.
    st.caption(explain.text(f"metric.window_source.{row.rhr_window_source}"))
    st.caption(
        f"{explain.text('metric.coverage')} Your watch measured "
        f"{format.minutes(row.coverage_minutes)} of this night."
    )

    if row.explained_bpm:
        st.caption(
            f"A recorded evening workout explained {format.bpm(row.explained_bpm)} of the "
            f"rise, and that was subtracted before this night was judged."
        )

    if on_trace is not None and st.button(
        "Show me how this was worked out",
        key="verdict_trace",
        help="Opens every step of this night, from your watch to this result",
    ):
        on_trace(row.night_date)
