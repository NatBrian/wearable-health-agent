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


def test_the_honesty_note_counts_figures_rather_than_asserting_a_number(fake_api) -> None:
    """The count comes from the application. Typing it here is how a document goes stale."""
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert "2 figures" in _body(app)
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
