"""Night chart component with maturing baseline band and non-interpolated gaps."""

import altair as alt
import pandas as pd
import streamlit as st

from wha.models import BaselineRung, DetectionLevel, NightRow
from wha.ui.components.api import config

# Two things are plotted, not three. The band's edges were separate legend entries with
# the same colour and the same dash, so they were indistinguishable from each other and
# read as two unrelated measurements rather than the top and bottom of one range. They now
# share a series and are kept apart as lines by a `detail` encoding, which splits a mark
# without adding a legend entry.
SERIES_NIGHT = "Your sleeping heart rate"
SERIES_RANGE = "Your usual range"
SERIES_ORDER = [SERIES_NIGHT, SERIES_RANGE]

# Distinguishable in a small swatch: a dark solid navy against a mid amber dashed line.
# Two shades of the same blue are not tellable apart at legend size.
COLOUR_NIGHT = "#1f4e79"
COLOUR_RANGE = "#d08c26"

# Below this rung the band is still mostly the population estimate, so a night sitting
# outside it says more about how little the system knows than about the person.
_PERSONAL_RUNGS = {BaselineRung.SHRINKING, BaselineRung.PERSONAL, BaselineRung.MATURE}


def build_night_chart_data(nights: list[NightRow]) -> pd.DataFrame:
    """Prepare structured DataFrame for nocturnal RHR time-series and band visualization.

    Non-usable nights carry NaN for rhr_bpm so gaps are never interpolated.
    """
    records = []
    for n in sorted(nights, key=lambda x: x.night_date):
        lo_band = n.band_lo
        hi_band = n.band_hi
        band_width = (hi_band - lo_band) if (hi_band is not None and lo_band is not None) else None

        # For non-usable nights, rhr_bpm must be None/NaN
        val_rhr = float(n.rhr_bpm) if (n.usable and n.rhr_bpm is not None) else None

        records.append(
            {
                "date": n.night_date.isoformat(),
                "night_date": n.night_date,
                "rhr_bpm": val_rhr,
                "centre_bpm": n.centre_bpm,
                "deviation_bpm": n.deviation_bpm,
                "lo_band": lo_band,
                "hi_band": hi_band,
                "band_width": band_width,
                "level": n.level.value if n.level != DetectionLevel.NA else "NA",
                "usable": n.usable,
                "episode_id": n.episode_id,
            }
        )

    return pd.DataFrame(records)


def render_night_chart(nights: list[NightRow], rung: BaselineRung | None = None) -> None:
    """Plot overnight heart rate against the person's own usual range."""
    if not nights:
        st.info("No nights recorded yet. Wear the watch overnight and this will fill in.")
        return

    df = build_night_chart_data(nights)

    st.subheader("Your overnight heart rate")
    st.caption(
        "Your resting heart rate while asleep, measured over the sleep your watch actually "
        "recorded. Waking spells during the night are excluded, and daytime or exercise "
        "heart rate is never used."
    )

    # Trim to the span that actually has readings. The query looks back a fixed number of
    # days, so a new subject would otherwise get a chart that is mostly empty space.
    measured = df.dropna(subset=["rhr_bpm"])
    if measured.empty:
        st.info("No usable nights in this period yet.")
        return
    df = df.loc[measured.index.min() : measured.index.max()]

    long_df = df.melt(
        id_vars=["date"],
        value_vars=[c for c in ["rhr_bpm", "lo_band", "hi_band"] if c in df.columns],
        var_name="series",
        value_name="bpm",
    ).dropna(subset=["bpm"])

    # `edge` keeps the two band edges as separate lines; `series` is what the legend shows.
    long_df["edge"] = long_df["series"]
    long_df["series"] = long_df["series"].map(
        {
            "rhr_bpm": SERIES_NIGHT,
            "lo_band": SERIES_RANGE,
            "hi_band": SERIES_RANGE,
        }
    )

    # The y-axis deliberately does not start at zero. Nobody's resting heart rate goes
    # near zero, and anchoring there squashes the whole series into a thin band where the
    # three or four bpm that decide everything are invisible.
    low = float(long_df["bpm"].min()) - 3.0
    high = float(long_df["bpm"].max()) + 3.0

    chart = (
        alt.Chart(long_df)
        .mark_line()
        .encode(
            # One point per night, so the axis is days. Left to choose its own units,
            # Vega picked hours for a short series and labelled three nights with ticks
            # like "09 AM" and "03 PM", which reads as intra-day data the watch never
            # produced.
            x=alt.X(
                "date:T",
                title=None,
                axis=alt.Axis(format="%d %b", tickCount={"interval": "day", "step": 1}),
            ),
            y=alt.Y(
                "bpm:Q",
                title="beats per minute",
                scale=alt.Scale(domain=[low, high], zero=False, nice=False),
            ),
            color=alt.Color(
                "series:N",
                title="What each line means",
                sort=SERIES_ORDER,
                scale=alt.Scale(
                    domain=SERIES_ORDER,
                    range=[COLOUR_NIGHT, COLOUR_RANGE],
                ),
            ),
            # Set explicitly. Left to Altair these are assigned alphabetically, which made
            # the person's own nights dotted and a band line solid, inverting the emphasis.
            #
            # These carried legend=None. Vega-Lite merges the legends of every channel
            # encoding the same field, and a None on any of them suppresses the merged
            # legend, so the chart rendered with no legend at all whatever the colour
            # channel asked for. Sharing one title across the three channels gives a single
            # legend whose swatches show each series' real dash pattern and thickness.
            strokeDash=alt.StrokeDash(
                "series:N",
                title="What each line means",
                scale=alt.Scale(
                    domain=SERIES_ORDER,
                    range=[[1, 0], [5, 4]],
                ),
            ),
            size=alt.Size(
                "series:N",
                title="What each line means",
                scale=alt.Scale(
                    domain=SERIES_ORDER,
                    range=[2.5, 1.5],
                ),
            ),
            # Splits the upper and lower edges into two lines without giving each its own
            # legend entry. Without it they share a series name and are drawn as one
            # zigzag joining top to bottom.
            detail=alt.Detail("edge:N"),
            tooltip=[
                alt.Tooltip("date:T", title="Night", format="%d %b %Y"),
                alt.Tooltip("series:N", title=None),
                alt.Tooltip("bpm:Q", format=".1f"),
            ],
        )
        .properties(height=320)
    )

    st.altair_chart(chart, use_container_width=True)

    # A legend names the lines; it does not say what they mean or why the rule is
    # one-sided, and a reader whose nights sit below the band had no way to tell whether
    # that was a finding. Every figure quoted here carries the source it came from.
    st.markdown(
        f"""
**Reading this chart**

- **{SERIES_NIGHT}** — the solid dark blue line. One point per night.
- **{SERIES_RANGE}** — the two dashed amber lines above and below it. They are the top and
  bottom of the range expected for you on that night. The gap between them is wider when
  the system has less to go on, and narrows as your own nights accumulate.

{config()["DETECT_DIRECTION_NOTE"]}

**What this measures, and what it does not**

- Your nights are compared against **your own median**, not against an average adult, once
  {config()["BASELINE_MIN_NIGHTS_PERSONAL"]} nights of your sleep exist. Before that the comparison is
  to a typical adult and nothing is flagged.
- **Only sleep is measured, never your waking heart rate.** Daytime readings mostly record
  what you were doing: standing up or climbing stairs moves your heart rate by tens of
  beats, while an illness moves it by a few. Asleep you are in one posture and still, which
  is the only time a wrist sensor can see a change that small.
- The reading comes from your **main overnight sleep**, taken from your watch rather than
  from a fixed clock window, so it works whatever hours you keep. Where your watch recorded
  no sleep for a night, midnight to 7am is used instead and that night is labelled.
- **Naps are not included.** Heart rate during a daytime nap is measurably higher than
  during overnight sleep at the same sleep stage, so pooling them would move your reading
  by however much you happened to nap. A second sleep block is therefore ignored.
- **Sleep apnoea is not detected.** A condition that raises your heart rate every night
  becomes part of what this system learns as your normal, so it will not be flagged.
  Detecting it needs signals this watch does not provide.
"""
    )

    if rung is not None and rung not in _PERSONAL_RUNGS:
        st.info(
            "**This band is not yet yours, and nothing can be flagged.** With fewer than "
            f"{config()['BASELINE_MIN_NIGHTS_PERSONAL']} nights recorded it is still a typical-adult "
            f"estimate, centred on {config()['POP_PRIOR_RHR_MEAN_BPM']:.1f} bpm, which is the "
            "average of 525 adults, and about "
            f"{config()['WITHIN_PERSON_SCALE_PRIOR_BPM']:.1f} bpm wide, which is how much a "
            "typical person's nights move around their own average. Your nights may sit well "
            "outside it. That "
            "reflects how little is known about you, not anything about your health. At "
            f"{config()['BASELINE_MIN_NIGHTS_PERSONAL']} nights the band switches to your own median "
            "and closes around you, which is a visible step on this chart, and only then "
            "can a raised night be acted on."
        )

    st.caption(
        f"The starting range comes from {config()['POP_PRIOR_CITATION_PLAIN']}, and moves toward your "
        f"own nights as they accumulate. The thresholds that decide when a raised night is "
        f"worth investigating come from {config()['DETECT_CITATION_PLAIN']}. Measuring over your "
        f"recorded sleep follows {config()['SLEEP_WINDOW_CITATION_PLAIN']}, and leaving naps out "
        f"follows {config()['NAP_EXCLUSION_CITATION_PLAIN']}. Measuring asleep rather than across the day "
        f"follows {config()['DAYTIME_EXCLUSION_CITATION_PLAIN']}."
    )
    with st.expander("Full references"):
        st.markdown(
            f"""
- Where the band starts, {config()["POP_PRIOR_RHR_MEAN_BPM"]:.2f} bpm —
  {config()["POP_PRIOR_CITATION"]}
- How wide it starts, {config()["WITHIN_PERSON_SCALE_PRIOR_BPM"]:.2f} bpm —
  {config()["WITHIN_PERSON_SCALE_CITATION"]}. This is how much one person's nights move
  around their own average, which is a different quantity from the
  {config()["POP_PRIOR_RHR_SD_BPM"]:.2f} bpm by which different adults differ from each other.
- Thresholds for a raised night — {config()["DETECT_CITATION"]}
- Comparing against your own median, and the {config()["BASELINE_MIN_NIGHTS_PERSONAL"]}-night figure —
  {config()["BASELINE_PERSONAL_CITATION"]}
- Measuring over the device's reported sleep period — {config()["SLEEP_WINDOW_CITATION"]}
- Excluding naps from the reading — {config()["NAP_EXCLUSION_CITATION"]}
- Measuring asleep rather than across the day — {config()["DAYTIME_EXCLUSION_CITATION"]}
"""
        )
