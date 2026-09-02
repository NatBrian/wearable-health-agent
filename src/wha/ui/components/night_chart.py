"""Night chart component with maturing baseline band and non-interpolated gaps."""

import altair as alt
import pandas as pd
import streamlit as st

from wha.models import DetectionLevel, NightRow


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


def render_night_chart(nights: list[NightRow]) -> None:
    """Plot overnight heart rate against the person's own usual range."""
    if not nights:
        st.info("No nights recorded yet. Wear the watch overnight and this will fill in.")
        return

    df = build_night_chart_data(nights)

    st.subheader("Your overnight heart rate")
    st.caption(
        "The dark line is each night. The shaded pair around it is your usual range for "
        "that period, which widens when there is less to go on. A night outside the band "
        "is what starts an investigation."
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

    long_df["series"] = long_df["series"].map(
        {
            "rhr_bpm": "Your night",
            "lo_band": "Usual range, low",
            "hi_band": "Usual range, high",
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
            x=alt.X("date:T", title=None),
            y=alt.Y(
                "bpm:Q",
                title="beats per minute",
                scale=alt.Scale(domain=[low, high], zero=False, nice=False),
            ),
            color=alt.Color(
                "series:N",
                title=None,
                scale=alt.Scale(
                    domain=["Your night", "Usual range, low", "Usual range, high"],
                    range=["#1f4e79", "#9ecae1", "#9ecae1"],
                ),
            ),
            # Set explicitly. Left to Altair these are assigned alphabetically, which made
            # the person's own nights dotted and a band line solid, inverting the emphasis.
            strokeDash=alt.StrokeDash(
                "series:N",
                legend=None,
                scale=alt.Scale(
                    domain=["Your night", "Usual range, low", "Usual range, high"],
                    range=[[1, 0], [4, 3], [4, 3]],
                ),
            ),
            size=alt.Size(
                "series:N",
                legend=None,
                scale=alt.Scale(
                    domain=["Your night", "Usual range, low", "Usual range, high"],
                    range=[2.5, 1.2, 1.2],
                ),
            ),
            tooltip=["date:T", "series:N", alt.Tooltip("bpm:Q", format=".1f")],
        )
        .properties(height=320)
    )

    st.altair_chart(chart, use_container_width=True)
