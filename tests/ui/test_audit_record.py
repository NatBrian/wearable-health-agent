"""The record tab: what the system did, and whether the record can still be trusted."""

from datetime import UTC, date, datetime

from streamlit.testing.v1 import AppTest

from tests.ui.conftest import page
from tests.ui.test_audit_pipeline import _pipeline
from wha.models import AuditEventView, DetectionLevel, PipelineNightRef

PAGE = page("pages/3_The_record.py")


def _event(operation: str = "ingest", actor: str = "system") -> AuditEventView:
    return AuditEventView(
        event_id="evt_1",
        timestamp_utc=datetime(2026, 9, 4, 7, 12, tzinfo=UTC),
        actor=actor,
        operation=operation,
        hash_ok=True,
    )


def _ready(fake_api) -> None:
    fake_api.list_pipeline_nights.return_value = [
        PipelineNightRef(
            night_date=date(2026, 9, 4),
            level=DetectionLevel.GREEN,
            has_episode=False,
            usable=True,
        )
    ]
    # The three tabs share one script run, so an exception in the pipeline tab takes the
    # record tab down with it. Every tab's data has to be present for any tab to be tested.
    fake_api.get_night_pipeline.return_value = _pipeline()
    fake_api.list_plain_records.return_value = []
    fake_api.query_audit.return_value = [_event()]
    fake_api.count_audit_events.return_value = 1
    fake_api.verify_hash_chain.return_value = (True, None)


def _tab_text(app: AppTest) -> str:
    parts = [m.value for m in app.markdown]
    parts += [c.value for c in app.caption]
    parts += [i.value for i in app.info]
    parts += [s.value for s in app.success]
    return " ".join(parts)


def test_an_empty_record_is_distinguished_from_a_broken_one(fake_api) -> None:
    """An empty page and a failed query must never look the same in a health system.

    An empty hash chain verifies. Reporting "the record is intact" over zero entries is a
    green tick for something that was never checked.
    """
    _ready(fake_api)
    fake_api.query_audit.return_value = []
    fake_api.count_audit_events.return_value = 0
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    body = _tab_text(app).lower()
    assert "nothing has been recorded yet" in body
    assert "the record is intact" not in body


def test_an_intact_record_says_so_only_when_there_is_something_to_verify(fake_api) -> None:
    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert any("record is intact" in s.value.lower() for s in app.success)


def test_a_broken_chain_is_stated_with_the_entry_it_breaks_at(fake_api) -> None:
    """If the record may have been altered, that outranks everything else on the page."""
    _ready(fake_api)
    fake_api.verify_hash_chain.return_value = (False, "evt_1")
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert app.error
    assert "evt_1" in app.error[0].value


def test_the_filter_reaches_the_application_rather_than_trimming_a_page(fake_api) -> None:
    """Filtering client-side would silently filter only the first hundred rows."""
    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    operation = next(s for s in app.selectbox if "kind of action" in s.label)
    operation.set_value("nightly").run()

    sent = fake_api.query_audit.call_args.args[0]
    assert sent.operation == "nightly"


def test_no_matching_events_does_not_claim_the_record_is_empty(fake_api) -> None:
    _ready(fake_api)
    fake_api.query_audit.return_value = []
    fake_api.count_audit_events.return_value = 42
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert "The record itself is not empty" in _tab_text(app)


def test_the_explainer_reads_its_figures_from_the_running_system(fake_api) -> None:
    """The version before it hardcoded them and drifted away from the code."""
    _ready(fake_api)
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert not app.exception
    fake_api.config.assert_called()


def test_the_two_tabs_describe_one_system_not_two() -> None:
    """Both tabs shipped a numbered list starting at 1, with different names and lengths.

    A reader could reasonably conclude the system does two different things. The topics
    are not a second pipeline: each one covers a range of the same twenty steps, and every
    step has to be covered by at least one topic, so a step added to the pipeline cannot
    go unexplained here and this page cannot claim a step the pipeline does not have.
    """
    from wha.models import CANONICAL_PIPELINE_STEPS
    from wha.ui.components.how_it_works import TOPIC_STEPS

    covered = {ordinal for steps in TOPIC_STEPS.values() for ordinal in steps}
    real = {definition.ordinal for definition in CANONICAL_PIPELINE_STEPS}

    assert covered <= real, f"topics claim steps that do not exist: {sorted(covered - real)}"
    assert real <= covered, f"steps no topic explains: {sorted(real - covered)}"


def test_the_topics_run_in_the_same_order_as_the_steps(fake_api) -> None:
    """Reported by the user: the ranges jumped about and skipped numbers.

    Steps 19 and 20 sat fourth in the list, one topic claimed 8 to 10 and 15 to 18 with
    three other topics in between, step 18 appeared twice, and nothing named 15 to 17. A
    reader following the numbers could not follow them.
    """
    from wha.ui.components.how_it_works import TOPIC_STEPS

    ranges = [steps for steps in TOPIC_STEPS.values() if steps]

    for steps in ranges:
        assert list(steps) == list(range(steps[0], steps[-1] + 1)), f"{steps} has a hole in it"

    firsts = [steps[0] for steps in ranges]
    assert firsts == sorted(firsts), "the topics are not in the order the steps run"

    flat = [ordinal for steps in ranges for ordinal in steps]
    assert flat == sorted(flat), "the topics overlap or double back"
    assert len(flat) == len(set(flat)), "a step is explained under two topics"


def test_no_topic_carries_a_number_of_its_own(fake_api) -> None:
    """A topic numbered 1 beside a step numbered 1 is the confusion being removed."""
    from wha.ui.components.how_it_works import TOPIC_STEPS, _title

    for topic in TOPIC_STEPS:
        rendered = _title(topic)
        assert not rendered.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8."))
        assert "step" in rendered
