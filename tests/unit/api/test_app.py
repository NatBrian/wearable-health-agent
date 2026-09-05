"""The HTTP boundary, which is what makes the dashboard replaceable."""

import pytest
from fastapi.testclient import TestClient

from wha.api.app import app

client = TestClient(app)


def test_config_gives_a_client_the_numbers_it_must_not_hardcode() -> None:
    """The dashboard imported these from wha.constants, which a browser cannot do.

    It also meant a threshold could drift between a screen and the code that uses it.
    """
    from wha.constants import BASELINE_MIN_NIGHTS_PERSONAL, DETECT_RED_BPM

    body = client.get("/config").json()

    # Names match the source exactly, so a reader can find the constant and the reasoning
    # written above it without a mapping table.
    assert body["BASELINE_MIN_NIGHTS_PERSONAL"] == BASELINE_MIN_NIGHTS_PERSONAL
    assert body["DETECT_RED_BPM"] == DETECT_RED_BPM
    assert body["today"], "a client has no way to know the subject's local date"
    assert body["configured_subject"], "a client cannot read the environment"


def test_config_is_enumerated_so_it_cannot_drift_from_the_code() -> None:
    """Listing the constants by hand would let this endpoint fall behind the module.

    Every public constant is exported, so a threshold added tomorrow reaches an interface
    without anyone remembering to add it here.
    """
    from wha import constants

    body = client.get("/config").json()
    public = {n for n in dir(constants) if n.isupper()}
    serialisable = {
        n
        for n in public
        if isinstance(getattr(constants, n), str | int | float | bool | list | dict | type(None))
    }

    assert serialisable <= set(body), f"missing from /config: {sorted(serialisable - set(body))}"


def test_every_endpoint_a_screen_needs_is_present() -> None:
    """A missing endpoint means a screen that cannot be rebuilt in another framework."""
    paths = {r.path for r in app.routes if hasattr(r, "methods")}

    for required in (
        "/config",
        "/subjects",
        "/subjects/{subject_id}/status",
        "/subjects/{subject_id}/nights",
        "/subjects/{subject_id}/episodes",
        "/subjects/{subject_id}/pending",
        "/subjects/{subject_id}/conversation",
        "/subjects/{subject_id}/urgency",
        "/subjects/{subject_id}/handover",
        "/subjects/{subject_id}/audit",
        "/episodes/{episode_id}",
        "/episodes/{episode_id}/answer",
        "/settings",
    ):
        assert required in paths, required


def test_an_unknown_episode_is_a_404_not_an_empty_success() -> None:
    """A screen must be able to tell "no such thing" from "nothing to show"."""
    assert client.get("/episodes/does-not-exist").status_code == 404


def test_an_unknown_diagnostic_component_is_refused() -> None:
    """The component list is closed, like the tool registry."""
    assert client.post("/diagnostics/anything", json={}).status_code == 404


def test_the_openapi_schema_is_generated() -> None:
    """A React author needs the contract without reading Python."""
    schema = client.get("/openapi.json").json()
    assert schema["info"]["title"]
    assert "/config" in schema["paths"]


def test_localise_returns_a_datetime_callers_can_format() -> None:
    """It replaced wha.clock.to_local, whose callers call .strftime on the result.

    Returning a string turned every one of those into an AttributeError at render time,
    and no test caught it because none rendered the status strip with a timestamp actually
    present. Driving the dashboard did.
    """
    from datetime import UTC, datetime

    from wha.api.client import ApiClient

    api = ApiClient(base_url="http://testserver", client=client)
    result = api.localise(datetime(2026, 9, 4, 5, 0, tzinfo=UTC))

    assert isinstance(result, datetime)
    assert result.strftime("%H:%M")


def test_the_documented_endpoint_count_matches_the_app() -> None:
    """Four live documents published "28 endpoints" while the app served 31.

    A number repeated across four files with no single source drifts the moment anyone adds
    a route, and nothing notices. This reads the count from the app and from the documents,
    so adding an endpoint fails here rather than quietly making the docs wrong.
    """
    import re
    from pathlib import Path

    actual = len({(r.path, tuple(sorted(r.methods))) for r in app.routes if hasattr(r, "methods")})
    assert actual > 20, "route table looks wrong, this test would prove nothing"

    repo = Path(__file__).resolve().parents[3]
    documents = [
        repo / "STATUS.md",
        repo / "docs" / "ARCHITECTURE.md",
        repo / "docs" / "DESIGN-REVIEW.md",
    ]

    wrong: list[str] = []
    for path in documents:
        if not path.exists():
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in re.finditer(r"(\d+) endpoints", line):
                if int(match.group(1)) != actual:
                    wrong.append(
                        f"{path.relative_to(repo)}:{i}: says {match.group(1)}, app has {actual}"
                    )

    assert not wrong, "the documented endpoint count is stale:\n  " + "\n  ".join(wrong)


def test_no_document_quotes_a_policy_accuracy_the_eval_did_not_produce() -> None:
    """Three live documents published an "Always ask" accuracy of 0.925. It is 0.825.

    `run_policy_eval` was fixed in an earlier session to run the real policies through the
    real belief model, and it wrote 0.825 to data/eval/policy.json. The documents kept the
    old constant, which is the figure from when the suite returned hardcoded numbers no
    policy had produced.
    """
    import json
    from pathlib import Path

    repo = Path(__file__).resolve().parents[3]
    results = repo / "data" / "eval" / "policy.json"
    if not results.exists():
        pytest.skip("policy.json not generated on this machine")

    metrics = json.loads(results.read_text(encoding="utf-8")).get("metrics", {})
    always_ask = metrics.get("always_ask_mean_accuracy")
    assert always_ask is not None, "policy.json has no always-ask accuracy"

    superseded = "0.925"

    # Records that quote the wrong number ON PURPOSE are excluded by name.
    # docs/AUDIT-2026-09-05.md is the independent audit that FOUND this mismatch; it
    # quotes 0.925 as the finding, and rewriting it to say 0.825 would erase the thing it
    # exists to record. Its own header says it is kept unedited. The changelog and the
    # blocker file are the same shape: a correction has to be able to name what it
    # corrected.
    PRESERVED_RECORDS = {"AUDIT-2026-09-05.md", "KNOWLEDGE-CHANGELOG.md"}

    # The retracted figure must not appear at all, on any line, rather than only on lines
    # labelled "Always ask". The first version of this test required both on one line and
    # therefore missed docs/DESIGN-DATA-CHANNELS.md, which phrases it as "asks one
    # well-chosen question scores 0.925" with no label. Caught by reintroducing the number
    # and watching the test pass anyway.
    searched = list(repo.glob("docs/*.md")) + [
        repo / "README.md",
        repo / "STATUS.md",
        repo / "AGENTS.md",
        repo / "EVALUATION.md",
    ]
    wrong: list[str] = []
    for path in searched:
        if path.name in PRESERVED_RECORDS or not path.exists():
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if superseded in line:
                wrong.append(f"{path.relative_to(repo)}:{i}: {line.strip()[:80]}")

    assert not wrong, (
        f"the measured always-ask accuracy is {always_ask}, and these still say {superseded}:\n  "
        + "\n  ".join(wrong)
    )
