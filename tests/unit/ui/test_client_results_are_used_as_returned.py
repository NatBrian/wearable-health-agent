"""A screen must use what the client actually hands back, not what it used to hand back.

This is the second time this exact defect shipped. `ApiClient.localise` carries a docstring
about the first one: it returned a string where callers formatted a datetime, and no test
caught it "because none rendered the status strip with a timestamp actually present".

The second was found on 5 September 2026 by clicking "Build the summary" on the Today page:

    st.session_state["handover_text"] = api().build_handover(subject_id).as_text()
    AttributeError: 'dict' object has no attribute 'as_text'

`.as_text()` belongs to the `Handover` dataclass the SERVICE returns. Once the HTTP boundary
went in, the dashboard held the JSON body instead, and the call site was never updated. It
crashed the whole Today page, not just the expander, and the full suite stayed green because
nothing between the client and a rendered button was ever exercised together.

Both tests below are about that seam, from two directions.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wha.api.app import app
from wha.api.client import ApiClient

UI_ROOT = Path(__file__).resolve().parents[3] / "src" / "wha" / "ui"


@pytest.fixture(name="api")
def api_fixture() -> ApiClient:
    """A real ApiClient speaking to the real app, so the JSON shape is the real one."""
    return ApiClient(base_url="http://testserver", client=TestClient(app))


def test_the_handover_arrives_as_text_the_screen_can_render(api: ApiClient) -> None:
    """The endpoint renders the SBAR text; the screen must read it, not re-render it."""
    payload = api.build_handover("sim")

    assert isinstance(payload, dict), "the boundary hands over JSON, not a service object"
    assert not hasattr(payload, "as_text"), (
        "if this ever passes, the client stopped returning JSON and the UI must be revisited"
    )
    assert payload["text"].strip(), "the screen renders payload['text'] and nothing else"

    # The four SBAR sections travel separately too, so a different interface can lay them
    # out itself rather than parsing the rendered block.
    for section in ("situation", "background", "assessment", "recommendation"):
        assert section in payload, section


def _dict_returning_client_methods() -> set[str]:
    """Client methods whose result is a plain mapping, so it has no methods of its own."""
    names: set[str] = set()
    for name in dir(ApiClient):
        if name.startswith("_"):
            continue
        attr = getattr(ApiClient, name)
        if not callable(attr):
            continue
        annotation = getattr(attr, "__annotations__", {}).get("return")
        text = str(annotation)
        if "dict" in text or "list" in text:
            names.add(name)
    return names


def test_no_screen_calls_a_method_on_a_plain_json_result() -> None:
    """`api().something(...).attribute` is only safe when `something` returns an object.

    A static check, because that is what this defect is: the runtime never reached the
    line. Clicking every button in the dashboard is the only other way to find it, and
    that is exactly how it WAS found. This test makes the third instance cheap to catch.
    """
    plain = _dict_returning_client_methods()
    assert plain, "introspection found no dict-returning methods, so this test proves nothing"

    offences: list[str] = []

    for path in sorted(UI_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            # Match `<something>.<attr>` where <something> is a call to `api().<method>()`.
            if not isinstance(node, ast.Attribute):
                continue
            inner = node.value
            if not isinstance(inner, ast.Call) or not isinstance(inner.func, ast.Attribute):
                continue
            receiver = inner.func.value
            is_api_call = (
                isinstance(receiver, ast.Call)
                and isinstance(receiver.func, ast.Name)
                and receiver.func.id == "api"
            )
            if not is_api_call:
                continue
            method = inner.func.attr
            if method in plain:
                offences.append(
                    f"{path.relative_to(UI_ROOT.parents[2])}:{node.lineno} "
                    f"api().{method}(...).{node.attr} -- {method} returns plain JSON"
                )

    assert not offences, "screens using a JSON result as an object:\n  " + "\n  ".join(offences)
