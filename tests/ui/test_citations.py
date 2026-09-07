"""A citation you can open, which is the difference between evidence and a badge."""


def test_the_drawer_shows_the_whole_passage_not_only_the_quote(fake_api) -> None:
    """Grounding that cannot be inspected is a badge, not evidence."""
    from unittest.mock import patch

    from wha.ui.components.citations import drawer

    passage = "Resting heart rate rises in the days before symptoms appear in some infections."
    with patch("streamlit.markdown") as markdown, patch("streamlit.caption"):
        drawer({"title": "Viral prodrome", "source_id": "confounder_infection", "passage": passage})

    rendered = " ".join(str(call.args[0]) for call in markdown.call_args_list)
    assert passage in rendered


def test_the_quoted_span_is_highlighted_inside_the_passage(fake_api) -> None:
    """The reader has to see which words the sentence took, and what surrounded them."""
    from unittest.mock import patch

    from wha.ui.components.citations import drawer

    passage = "Resting heart rate rises in the days before symptoms appear."
    with patch("streamlit.markdown") as markdown, patch("streamlit.caption"):
        drawer(
            {"title": "Viral prodrome", "source_id": "confounder_infection", "passage": passage},
            quoted_span="rises in the days before symptoms",
        )

    rendered = " ".join(str(call.args[0]) for call in markdown.call_args_list)
    assert "<mark>rises in the days before symptoms</mark>" in rendered


def test_a_quote_absent_from_its_passage_is_reported_rather_than_highlighted(fake_api) -> None:
    """The grounding check proves the span exists. Where it does not, say so loudly."""
    from unittest.mock import patch

    from wha.ui.components.citations import drawer

    with (
        patch("streamlit.markdown"),
        patch("streamlit.caption"),
        patch("streamlit.warning") as warning,
    ):
        drawer(
            {
                "title": "Viral prodrome",
                "source_id": "confounder_infection",
                "passage": "A short passage.",
            },
            quoted_span="words that are not in it",
        )

    assert warning.called
    assert "could not be found" in warning.call_args[0][0]
