"""History: sixty nights a person can actually read."""

from datetime import date

import pandas as pd
from streamlit.testing.v1 import AppTest

from tests.ui.conftest import page
from wha.models import DetectionLevel, EpisodeState, EpisodeSummary, NightRow

PAGE = page("pages/2_History.py")


def _rows() -> list[NightRow]:
    return [
        NightRow(
            night_date=date(2026, 9, 1),
            rhr_bpm=46.0,
            centre_bpm=45.0,
            band_lo=39.0,
            band_hi=51.0,
            deviation_bpm=1.0,
            coverage_minutes=340,
            usable=True,
            level=DetectionLevel.GREEN,
        ),
        NightRow(
            night_date=date(2026, 9, 2),
            coverage_minutes=0,
            usable=False,
            level=DetectionLevel.NA,
        ),
        NightRow(
            night_date=date(2026, 9, 3),
            rhr_bpm=52.0,
            centre_bpm=45.0,
            band_lo=39.0,
            band_hi=51.0,
            deviation_bpm=7.0,
            coverage_minutes=331,
            usable=True,
            level=DetectionLevel.RED,
            episode_id="ep_1",
        ),
    ]


def _episodes() -> list[EpisodeSummary]:
    return [
        EpisodeSummary(
            episode_id="ep_1",
            opened_on=date(2026, 9, 3),
            state=EpisodeState.AWAITING_USER,
            night_span=(date(2026, 9, 2), date(2026, 9, 3)),
        )
    ]


def _ready(fake_api) -> None:
    fake_api.list_nights.return_value = _rows()
    fake_api.list_episodes.return_value = _episodes()


def test_the_page_renders_without_an_exception(fake_api) -> None:
    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert not app.exception


def test_the_chart_has_a_caption_naming_every_element_on_it(fake_api) -> None:
    """A chart nobody can read is decoration."""
    from wha.ui import explain

    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    captions = " ".join(c.value for c in app.caption)
    assert explain.text("chart.how_to_read") in captions


def test_a_night_with_no_reading_is_a_gap_not_a_zero() -> None:
    """A missing night drawn at zero reads as a heart rate of zero."""
    from wha.ui.components.night_chart import chart_frame

    frame = chart_frame(_rows())
    missing = frame[frame["night_date"] == date(2026, 9, 2)].iloc[0]

    assert missing["rhr_bpm"] != 0
    assert pd.isna(missing["rhr_bpm"])


def test_the_table_says_what_came_of_an_investigation_in_words(fake_api) -> None:
    """The point of the column is the result, not that a row exists."""
    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert app.dataframe, "the night table did not render"
    table = app.dataframe[0].value
    assert "Investigated" in list(table.columns)
    assert "waiting for your answer" in list(table["Investigated"])


def test_the_default_table_is_six_columns(fake_api) -> None:
    """Eleven columns of database vocabulary is what this page is being rescued from."""
    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert len(app.dataframe[0].value.columns) == 6


def test_the_full_field_view_is_off_by_default_and_adds_columns_when_asked(fake_api) -> None:
    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    toggle = next(t for t in app.toggle if "every recorded field" in t.label)
    assert toggle.value is False

    toggle.set_value(True).run()
    assert len(app.dataframe[0].value.columns) > 6


def test_filtering_to_investigated_nights_drops_the_others(fake_api) -> None:
    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    toggle = next(t for t in app.toggle if "looked into" in t.label)
    toggle.set_value(True).run()

    table = app.dataframe[0].value
    assert list(table["Night"]) == ["2026-09-03"]


def test_the_two_colour_scales_do_not_merge_into_one_legend() -> None:
    """A RED night was drawn in the same blue as the line labelled with your heart rate.

    The chart has two colour scales: one naming the lines, one colouring each night's dot
    by what the system concluded. Vega-Lite merges the legends of channels encoding the
    same channel, so a second `color` collapsed into the line legend and took the line
    palette with it. The dots use `fill`, which has its own legend and its own scale.
    """
    from wha.ui.components.night_chart import DOT_COLOURS, render_spec

    spec = render_spec(_rows())
    dots = spec["layer"][1]["encoding"]

    assert "fill" in dots, "the dot colours share the line channel again"
    assert "color" not in dots
    assert dots["fill"]["scale"]["range"] == [DOT_COLOURS[k] for k in DOT_COLOURS]
    assert dots["fill"]["title"] != spec["layer"][0]["encoding"]["color"]["title"]


def test_the_level_legend_does_not_run_three_verdicts_into_one_sentence(fake_api) -> None:
    """It read as one paragraph saying the night was in range, somewhat above and clearly
    above at once, because every level explanation opens "Your sleeping heart rate was".
    """
    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    captions = " ".join(c.value for c in app.caption)
    assert "**GREEN** in your usual range" in captions
    assert captions.count("Your sleeping heart rate was") == 0
