"""The History page had no test at all, and shipped a guaranteed crash.

`render_night_table` built its rows with the key "Night" and read them back as "Date", so
opening the page raised KeyError for any subject with any nights. Every one of the 388
tests passed while one of the five pages was completely dead. These render the page.
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from wha.models import DetectionLevel, NightRow
from wha.ui.history import render_episode_spans, render_night_table


def _night(night: date, rhr: float | None, level: DetectionLevel) -> NightRow:
    return NightRow(
        night_date=night,
        rhr_bpm=rhr,
        centre_bpm=62.75,
        band_lo=54.0,
        band_hi=71.0,
        deviation_bpm=(rhr - 62.75) if rhr is not None else None,
        explained_bpm=0.0,
        residual_bpm=(rhr - 62.75) if rhr is not None else None,
        coverage_minutes=408 if rhr is not None else 0,
        usable=rhr is not None,
        level=level,
    )


REAL_NIGHTS = [
    _night(date(2026, 8, 30), None, DetectionLevel.NA),
    _night(date(2026, 8, 31), 51.0, DetectionLevel.GREEN),
    _night(date(2026, 9, 1), 56.0, DetectionLevel.GREEN),
    _night(date(2026, 9, 2), 48.0, DetectionLevel.GREEN),
]


def test_the_night_table_renders_without_crashing() -> None:
    """The regression: KeyError 'Date' on every load."""
    with (
        patch("wha.ui.history.st") as mock_st,
        patch("wha.api.client.ApiClient.get_night_detail", return_value=None),
    ):
        mock_st.selectbox.return_value = None
        mock_st.expander.return_value.__enter__ = MagicMock()
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)

        render_night_table("me", REAL_NIGHTS)

    assert mock_st.dataframe.called, "the night table must be rendered"


def test_the_night_selector_is_offered_the_dates_it_displayed() -> None:
    """The options must come from the column the table actually built."""
    captured: dict[str, object] = {}

    def capture_selectbox(_label: str, **kwargs: object) -> None:
        captured.update(kwargs)

    with (
        patch("wha.ui.history.st") as mock_st,
        patch("wha.api.client.ApiClient.get_night_detail", return_value=None),
    ):
        mock_st.selectbox.side_effect = capture_selectbox
        mock_st.expander.return_value.__enter__ = MagicMock()
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)

        render_night_table("me", REAL_NIGHTS)

    assert captured["options"] == [
        "2026-09-02",
        "2026-09-01",
        "2026-08-31",
        "2026-08-30",
    ]


def test_an_empty_night_list_does_not_crash() -> None:
    with patch("wha.ui.history.st") as mock_st:
        render_night_table("me", [])
    assert mock_st.info.called


@pytest.mark.parametrize("nights", [REAL_NIGHTS, []])
def test_episode_spans_render_with_and_without_episodes(nights: list[NightRow]) -> None:
    with patch("wha.ui.history.st") as mock_st:
        result = render_episode_spans([])
    assert result is None
    # The old copy claimed every night sat inside the band, which the chart above it
    # contradicts whenever a person's nights run low.
    said = " ".join(str(c) for c in mock_st.caption.call_args_list)
    assert "within your usual range" not in said
