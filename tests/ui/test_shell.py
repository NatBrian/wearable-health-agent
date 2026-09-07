"""The first screen, and the rules the whole interface is built on."""

from streamlit.testing.v1 import AppTest

from tests.ui.conftest import page

PAGE = page("Home.py")


def _body(app: AppTest) -> str:
    parts = [m.value for m in app.markdown]
    parts += [c.value for c in app.caption]
    parts += [e.value for e in app.error]
    parts += [w.value for w in app.warning]
    parts += [t.value for t in app.title]
    parts += [h.value for h in app.subheader]
    return " ".join(parts)


def test_the_home_page_renders_without_an_exception(fake_api) -> None:
    """A page that raises on load is invisible to every test that does not render it."""
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert not app.exception


def test_home_says_what_the_system_cannot_do(fake_api) -> None:
    """The disclaimer is the point of this page, so its absence is a test failure."""
    app = AppTest.from_file(PAGE, default_timeout=30).run()
    body = _body(app).lower()

    assert "cannot diagnose" in body
    assert "not a medical device" in body


def test_what_to_do_if_unwell_comes_before_anything_else(fake_api) -> None:
    """A person who feels ill should not have to read past the features first."""
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert app.error, "the page renders no urgent block at all"
    assert "emergency services" in app.error[0].value.lower()


def test_the_honesty_note_is_counted_rather_than_typed(fake_api) -> None:
    """The count comes from the application. Typing it here is how a document goes stale."""
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert "Of the 3 causes and questions" in _body(app)
    fake_api.get_knowledge_provenance.assert_called()


def test_a_person_with_no_data_is_not_told_they_are_well(fake_api) -> None:
    """An empty database and a healthy person must never render the same way."""
    fake_api.list_subjects.return_value = []
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert app.warning
    assert "nobody to show" in app.warning[0].value.lower()


def test_every_explanation_has_words_in_it() -> None:
    """Copy nobody wrote is worse than copy nobody read."""
    from wha.ui import explain

    for key in explain.KEYS:
        assert explain.text(key).strip(), key


def test_no_explanation_carries_a_figure() -> None:
    """A number typed into a screen drifts away from the code that uses it.

    This page previously claimed a coverage minimum of one hundred and twenty minutes
    against an actual hundred and eighty, and baseline tiers that did not match the
    ladder. Every number now comes from the application; the copy carries none.
    """
    import re

    from wha.ui import explain

    offenders = [key for key in explain.KEYS if re.search(r"\d", explain.text(key))]
    assert not offenders, f"copy with figures in it: {offenders}"


def test_a_missing_explanation_raises_rather_than_rendering_nothing() -> None:
    """A blank space where an explanation belongs is the failure being prevented."""
    import pytest

    from wha.ui import explain

    with pytest.raises(KeyError):
        explain.text("step.nothing_like_this.what")


def test_every_page_defaults_to_the_configured_subject(fake_api) -> None:
    """Opening a page directly showed a different person than Home did.

    Home read the configured subject; the other four fell back to `subjects[0]`, whichever
    row the database returned first. So Home showed `sim` while Today showed `me`, which
    holds four nights of a real person's data, and the only clue was that the two screens
    quoted different night counts.
    """
    from wha.models import BaselineRung, Subject

    fake_api.list_subjects.return_value = [
        Subject(
            subject_id="me",
            label="Real person",
            source_kind="live",
            timezone="Asia/Singapore",
            usable_nights=4,
            rung=BaselineRung.PRIOR_DOMINATED,
        ),
        Subject(
            subject_id="sim",
            label="Simulated",
            source_kind="synthetic",
            timezone="Asia/Singapore",
            usable_nights=28,
            rung=BaselineRung.MATURE,
        ),
    ]

    import streamlit as st

    from wha.ui.components.subject import resolve

    st.session_state.clear()
    assert resolve() == "sim", "the first row won over the configured subject"


def test_a_remembered_subject_that_no_longer_exists_is_not_used(fake_api) -> None:
    """Deleting everything about a person must not leave their id selected."""
    import streamlit as st

    from wha.ui.components.subject import resolve

    st.session_state.clear()
    st.session_state["active_subject"] = "someone_deleted"
    assert resolve() == "sim"


def test_the_attention_line_only_names_lines_that_are_on_screen(fake_api) -> None:
    """It read "Watch data, Problems today", and there is no Problems today line."""
    status = fake_api.get_system_status.return_value
    fake_api.get_system_status.return_value = status.model_copy(update={"errors_24h": 3})

    app = AppTest.from_file(PAGE, default_timeout=30).run()

    tiles = " ".join(m.value for m in app.markdown if "wha-tile" in m.value)
    for warning in app.warning:
        if "need attention" not in warning.value:
            continue
        named = warning.value.split(":", 1)[1].split(".")[0]
        for part in named.split(","):
            assert part.strip() in tiles, f"{part.strip()!r} is named but is not on screen"


def test_recorded_problems_are_still_reported_somewhere(fake_api) -> None:
    """The counterpart: taking it out of the attention line must not lose it."""
    status = fake_api.get_system_status.return_value
    fake_api.get_system_status.return_value = status.model_copy(update={"errors_24h": 3})

    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert any("3 problems" in w.value for w in app.warning)


def test_the_honesty_note_counts_entries_that_rest_on_an_unevidenced_figure(fake_api) -> None:
    """It said "11 figures" over twenty entries, which was the wrong unit and an undercount.

    Eleven was the count whose provenance is ASSUMED. Entries marked DERIVED can still
    carry a figure with no source, and three of them do.
    """
    fake_api.get_knowledge_provenance.return_value = {
        "a": {"provenance": "CITED", "has_unevidenced_number": "no"},
        "b": {"provenance": "ASSUMED", "has_unevidenced_number": "no"},
        "c": {"provenance": "DERIVED", "has_unevidenced_number": "yes"},
    }

    app = AppTest.from_file(PAGE, default_timeout=30).run()
    body = _body(app)

    assert "Of the 3 causes and questions" in body
    assert "2 rest" in body


def test_the_record_screen_has_one_name(fake_api) -> None:
    """The sidebar said Audit, the page said The record, and Home's card said Record."""
    from pathlib import Path

    import wha.ui

    pages = {p.stem for p in (Path(wha.ui.__file__).parent / "pages").glob("*.py")}
    assert "3_The_record" in pages
    assert not any(name.endswith("Audit") for name in pages)

    app = AppTest.from_file(PAGE, default_timeout=30).run()
    assert "The record" in _body(app)
