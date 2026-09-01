"""Unit tests for History view, baseline band narrowing, gap handling, and episode spans."""

from datetime import date
from unittest.mock import MagicMock, patch

import numpy as np

from wha.models import (
    DetectionLevel,
    EpisodeState,
    EpisodeSummary,
    NightRow,
)
from wha.ui.components.night_chart import build_night_chart_data
from wha.ui.history import render_episode_spans


def test_history_gaps_not_interpolated() -> None:
    """Non-usable nights (coverage gaps) are assigned NaN/None in chart data so they are not interpolated."""
    nights = [
        NightRow(
            night_date=date(2026, 8, 1),
            rhr_bpm=60.0,
            centre_bpm=60.0,
            band_lo=56.0,
            band_hi=64.0,
            deviation_bpm=0.0,
            residual_bpm=0.0,
            explained_bpm=0.0,
            coverage_minutes=420,
            level=DetectionLevel.GREEN,
            usable=True,
            episode_id=None,
        ),
        NightRow(
            night_date=date(2026, 8, 2),
            rhr_bpm=None,
            centre_bpm=None,
            band_lo=None,
            band_hi=None,
            deviation_bpm=None,
            residual_bpm=None,
            explained_bpm=0.0,
            coverage_minutes=60,  # Below coverage threshold
            level=DetectionLevel.NA,
            usable=False,
            episode_id=None,
        ),
        NightRow(
            night_date=date(2026, 8, 3),
            rhr_bpm=62.0,
            centre_bpm=60.0,
            band_lo=56.0,
            band_hi=64.0,
            deviation_bpm=2.0,
            residual_bpm=2.0,
            explained_bpm=0.0,
            coverage_minutes=430,
            level=DetectionLevel.GREEN,
            usable=True,
            episode_id=None,
        ),
    ]

    df = build_night_chart_data(nights)
    assert len(df) == 3
    # Check that day 2 (non-usable) has NaN / None for rhr_bpm
    row_gap = df[df["night_date"] == date(2026, 8, 2)].iloc[0]
    assert np.isnan(row_gap["rhr_bpm"]) or row_gap["rhr_bpm"] is None
    assert bool(row_gap["usable"]) is False


def test_history_band_narrows_with_maturity() -> None:
    """Baseline band width at early/immature stage (5 usable nights) exceeds mature stage (28 usable nights)."""
    early_night = NightRow(
        night_date=date(2026, 8, 5),
        rhr_bpm=60.0,
        centre_bpm=60.0,
        band_lo=52.0,
        band_hi=68.0,  # width = 16.0 (early / shrinking ladder)
        deviation_bpm=0.0,
        residual_bpm=0.0,
        explained_bpm=0.0,
        coverage_minutes=420,
        level=DetectionLevel.GREEN,
        usable=True,
        episode_id=None,
    )
    mature_night = NightRow(
        night_date=date(2026, 8, 28),
        rhr_bpm=60.0,
        centre_bpm=60.0,
        band_lo=56.5,
        band_hi=63.5,  # width = 7.0 (mature baseline)
        deviation_bpm=0.0,
        residual_bpm=0.0,
        explained_bpm=0.0,
        coverage_minutes=420,
        level=DetectionLevel.GREEN,
        usable=True,
        episode_id=None,
    )

    df = build_night_chart_data([early_night, mature_night])
    early_row = df[df["night_date"] == date(2026, 8, 5)].iloc[0]
    mature_row = df[df["night_date"] == date(2026, 8, 28)].iloc[0]

    assert early_row["band_width"] > mature_row["band_width"]


def test_episode_spans_clickable() -> None:
    """Clicking an episode span button sets query param and returns episode id."""
    episodes = [
        EpisodeSummary(
            episode_id="ep_abc_123",
            opened_on=date(2026, 8, 10),
            closed_on=date(2026, 8, 12),
            state=EpisodeState.CLOSED,
            disposition=None,
            night_span=(date(2026, 8, 10), date(2026, 8, 12)),
        )
    ]

    with (
        patch("streamlit.columns", return_value=[MagicMock()]),
        patch("streamlit.button", return_value=True),
        patch("streamlit.query_params", {}) as mock_params,
    ):
        selected = render_episode_spans(episodes)
        assert selected == "ep_abc_123"
        assert mock_params.get("episode") == "ep_abc_123"
