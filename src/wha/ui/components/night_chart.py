"""Night chart component with maturing baseline band and non-interpolated gaps."""

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
    """Render Streamlit line chart with band for nocturnal RHR."""
    if not nights:
        st.info("No nightly records available to plot.")
        return

    df = build_night_chart_data(nights)

    st.subheader("📈 Nocturnal Resting Heart Rate & Personal Baseline")
    # Display line chart
    chart_cols = [c for c in ["rhr_bpm", "lo_band", "hi_band"] if c in df.columns]
    chart_df = df.set_index("date")[chart_cols]
    st.line_chart(chart_df)
