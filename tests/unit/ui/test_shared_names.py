"""Cause and disposition names are shared with the phone, not reworded per surface."""

from wha import wording
from wha.models import CauseId, Disposition


def test_every_cause_has_a_person_facing_name() -> None:
    missing = [c.value for c in CauseId if f"cause.{c.value}" not in wording.TEXT]
    assert not missing, f"causes without a wording name: {missing}"


def test_every_disposition_has_a_label_and_a_meaning() -> None:
    for disposition in Disposition:
        assert f"disposition.{disposition.value}" in wording.TEXT
        assert f"disposition.{disposition.value}.why" in wording.TEXT


def test_phrasing_and_step_detail_read_the_shared_keys() -> None:
    from wha.service import phrasing
    from wha.ui.components import step_detail

    for disposition in Disposition:
        label, meaning = phrasing.disposition_phrase(disposition.value)
        assert label == wording.text(f"disposition.{disposition.value}")
        assert meaning == wording.text(f"disposition.{disposition.value}.why")
    for cause in CauseId:
        assert step_detail._cause_name(cause.value) == wording.text(f"cause.{cause.value}")
