"""One set of sentences for both surfaces. The dashboard's module is a re-export."""


def test_dashboard_and_core_wording_are_the_same_object() -> None:
    from wha import wording
    from wha.ui import explain

    assert explain.TEXT is wording.TEXT
    assert explain.text is wording.text
    assert explain.level is wording.level


def test_facade_returns_every_key() -> None:
    import json

    from wha import wording
    from wha_android import facade

    out = json.loads(facade.wording())
    assert set(out) == set(wording.TEXT)


def test_core_wording_contains_no_digit() -> None:
    from wha import wording

    offenders = [k for k, v in wording.TEXT.items() if any(c.isdigit() for c in v)]
    assert not offenders, f"wording with a figure in it: {offenders}"
