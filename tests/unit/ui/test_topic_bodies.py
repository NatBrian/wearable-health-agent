"""The topic bodies interpolate at render time; a misspelled placeholder would reach
a screen as a KeyError (dashboard) or a raw {TOKEN} (phone). Formats every body
against the real config so a typo fails here instead."""

from wha import wording
from wha.service import config_export
from wha.ui.components.how_it_works import TOPIC_STEPS, topic_body


def test_every_topic_body_formats_with_no_tokens_left() -> None:
    config = config_export()
    titles = list(TOPIC_STEPS)
    assert len(titles) == 10
    for n, title in enumerate(titles, 1):
        assert wording.text(f"topic.{n}.title") == title
        body = topic_body(
            n, config=config, tool_names=["read_nights"], assumed=6, rows=10
        )
        assert "{" not in body, f"topic {n} left a placeholder unfilled"
        assert "read_nights" in topic_body(
            5, config=config, tool_names=["read_nights"]
        )
