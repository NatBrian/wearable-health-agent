"""Your nights, drawn so that the few beats per minute that decide everything are visible.

Ported rather than rewritten, because the encoding here is the product of several real
defects and each fix is worth keeping:

* The band's two edges were separate legend entries in the same colour and dash, so they
  read as two unrelated measurements rather than the top and bottom of one range. They
  share a series now and are split into two lines by a `detail` encoding, which does not
  add a legend entry.
* Every channel carried `legend=None`. Vega-Lite merges the legends of channels encoding
  the same field, and a None on any one of them suppresses the merged legend, so the chart
  rendered with no legend at all. One shared title across the three channels fixes it.
* The x axis, left to choose its own units, labelled three nights with ticks like "09 AM",
  which reads as intra-day data the watch never produced.
* The y axis deliberately does not start at zero. Nobody's resting heart rate approaches
  zero, and anchoring there squashes the series into a strip where nothing is readable.

Nights with no usable reading carry no value rather than a zero, so the line breaks. A gap
is missing data; a zero would be a heart rate of zero.
"""

import altair as alt
import pandas as pd
import streamlit as st

from wha.models import DetectionLevel, NightRow
from wha.ui import design, explain

SERIES_NIGHT = "Your sleeping heart rate"
SERIES_RANGE = "Your usual range"
SERIES_ORDER = [SERIES_NIGHT, SERIES_RANGE]

# Distinguishable in a small swatch: dark solid navy against a mid amber dashed line. Two
# shades of one blue are not tellable apart at legend size.
COLOUR_NIGHT = "#1f4e79"
COLOUR_RANGE = "#d08c26"

DOT_COLOURS = {
    "GREEN": design.LEVEL_COLOURS["GREEN"][0],
    "YELLOW": "#b8860b",
    "RED": design.LEVEL_COLOURS["RED"][0],
    "NA": design.LEVEL_COLOURS["NA"][0],
}


def chart_frame(nights: list[NightRow]) -> pd.DataFrame:
    """One row per night. A night with no usable reading carries no value."""
    records = []
    for night in sorted(nights, key=lambda n: n.night_date):
        records.append(
            {
                "date": night.night_date.isoformat(),
                "night_date": night.night_date,
                "rhr_bpm": float(night.rhr_bpm)
                if (night.usable and night.rhr_bpm is not None)
                else None,
                "lo_band": night.band_lo,
                "hi_band": night.band_hi,
                "level": str(night.level) if night.level else DetectionLevel.NA.value,
                "usable": night.usable,
                "episode_id": night.episode_id,
            }
        )
    return pd.DataFrame(records)


def render_spec(nights: list[NightRow]) -> dict:
    """The chart as a Vega-Lite spec, so its encodings can be asserted without a browser.

    Separate from `render` because the defect worth testing here is not whether a chart
    appears. It is which channel each scale is on, and that is only visible in the spec.
    """
    chart = _build(nights)
    assert chart is not None, "no measured night to build a spec from"
    return chart.to_dict()


def _build(nights: list[NightRow]) -> alt.LayerChart | None:
    """The layered chart, or nothing when there is no measured night to draw."""
    frame = chart_frame(nights)
    measured = frame.dropna(subset=["rhr_bpm"])
    if measured.empty:
        return None

    frame = frame.loc[measured.index.min() : measured.index.max()]

    lines = frame.melt(
        id_vars=["date"],
        value_vars=[c for c in ("rhr_bpm", "lo_band", "hi_band") if c in frame.columns],
        var_name="series",
        value_name="bpm",
    ).dropna(subset=["bpm"])
    lines["edge"] = lines["series"]
    lines["series"] = lines["series"].map(
        {"rhr_bpm": SERIES_NIGHT, "lo_band": SERIES_RANGE, "hi_band": SERIES_RANGE}
    )

    low = float(lines["bpm"].min()) - 3.0
    high = float(lines["bpm"].max()) + 3.0
    axis = alt.Axis(format="%d %b", tickCount={"interval": "day", "step": 1})
    scale = alt.Scale(domain=[low, high], zero=False, nice=False)

    line_layer = (
        alt.Chart(lines)
        .mark_line()
        .encode(
            x=alt.X("date:T", title=None, axis=axis),
            y=alt.Y("bpm:Q", title="beats per minute", scale=scale),
            color=alt.Color(
                "series:N",
                title="What each line means",
                sort=SERIES_ORDER,
                scale=alt.Scale(domain=SERIES_ORDER, range=[COLOUR_NIGHT, COLOUR_RANGE]),
            ),
            strokeDash=alt.StrokeDash(
                "series:N",
                title="What each line means",
                scale=alt.Scale(domain=SERIES_ORDER, range=[[1, 0], [5, 4]]),
            ),
            size=alt.Size(
                "series:N",
                title="What each line means",
                scale=alt.Scale(domain=SERIES_ORDER, range=[2.5, 1.5]),
            ),
            detail=alt.Detail("edge:N"),
            tooltip=[
                alt.Tooltip("date:T", title="Night", format="%d %b %Y"),
                alt.Tooltip("series:N", title=None),
                alt.Tooltip("bpm:Q", title="beats per minute", format=".1f"),
            ],
        )
    )

    dots = (
        alt.Chart(measured)
        .mark_point(filled=True, size=80, stroke=None)
        .encode(
            x=alt.X("date:T", title=None, axis=axis),
            y=alt.Y("rhr_bpm:Q", title="beats per minute", scale=scale),
            # `fill`, not `color`. Vega-Lite merges the legends of channels encoding the
            # same channel name, so a second `color` here collapsed into the line legend
            # and took the line palette with it: a RED night drew in the same blue as the
            # line labelled "your sleeping heart rate". A chart that colours a red night
            # blue is making a false statement about the data.
            fill=alt.Fill(
                "level:N",
                title="What the system concluded",
                scale=alt.Scale(
                    domain=list(DOT_COLOURS), range=[DOT_COLOURS[k] for k in DOT_COLOURS]
                ),
            ),
            tooltip=[
                alt.Tooltip("date:T", title="Night", format="%d %b %Y"),
                alt.Tooltip("rhr_bpm:Q", title="Your reading", format=".0f"),
                alt.Tooltip("level:N", title="Conclusion"),
            ],
        )
    )

    return (line_layer + dots).properties(height=340)


def render(nights: list[NightRow]) -> None:
    """The chart, and a caption naming every element on it."""
    if not nights:
        st.info("No nights recorded yet. This is an empty chart, not a finding about your health.")
        return

    chart = _build(nights)
    if chart is None:
        st.info(
            "No night in this period was measured well enough to plot. That is missing "
            "data, not a result."
        )
        return

    st.altair_chart(chart, use_container_width=True)
    st.caption(explain.text("chart.how_to_read"))
