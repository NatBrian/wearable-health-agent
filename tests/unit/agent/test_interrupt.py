"""Unit tests for ask and measure interrupt discipline, idempotency, and timeout resumption."""

from unittest.mock import MagicMock, patch

from wha.agent import (
    EpisodeState,
    node_ask,
)
from wha.belief import load_causes
from wha.errors import LLMUnavailable
from wha.models import (
    Action,
    ActionKind,
    AnswerOption,
    BaselineRung,
    BeliefState,
    CauseId,
    Disposition,
    Probe,
    Question,
)
from wha.notify import MessageKind, Notifier
from wha.policy import determine_disposition

_cached_priors = load_causes()
_base_marginals = {p.cause: p.base_rate for p in _cached_priors}


def _make_belief(p_inf: float) -> BeliefState:
    marginals = dict(_base_marginals)
    marginals[CauseId.INFECTION] = p_inf
    return BeliefState(
        marginals=marginals,
        p_illness=p_inf,
    )


def _make_dummy_ask_action() -> Action:
    probe = Probe(
        probe_id="probe_alcohol",
        target_cause=CauseId.ALCOHOL,
        answer_space=[
            AnswerOption(option_id="none", label="None"),
            AnswerOption(option_id="1_2", label="1-2 drinks"),
            AnswerOption(option_id="3plus", label="3+ drinks"),
        ],
        evsi=0.45,
        interruption_cost=0.30,
        fallback_text="Did you have alcoholic drinks last night?",
    )
    question = Question(
        probe=probe,
        text="Did you have alcoholic drinks last night?",
        text_source="fallback",
        options=probe.answer_space,
        allows_free_text=True,
    )
    return Action(
        kind=ActionKind.ASK,
        question=question,
        rationale="EVSI positive for alcohol probe",
        rejected=[],
    )


def test_interrupt_resume_does_not_double_send() -> None:
    """When an interrupt is resumed, the re-executed node checks notifications and does not send twice."""
    action = _make_dummy_ask_action()
    state: EpisodeState = {
        "episode_id": "ep_double_send_test",
        "subject_id": "sub_001",
        "action": action,
        "step": 1,
    }

    # Specced against the real protocol. An unspecced MagicMock answers to any attribute,
    # so asserting on a misspelled method name passes while nothing is ever sent.
    mock_notifier = MagicMock(spec=Notifier)
    mock_notifier.send.return_value = True
    mock_db = MagicMock()

    # First pass: no prior notification recorded
    mock_db.has_notification_for.return_value = False

    def fake_interrupt(payload):
        # When interrupt returns, simulate resumption where db now reports already sent
        mock_db.has_notification_for.return_value = True
        return {"probe_id": "probe_alcohol", "option_id": "none"}

    with patch("wha.agent.nodes.ask.interrupt", side_effect=fake_interrupt):
        res1 = node_ask(state, notifier=mock_notifier, db=mock_db)
        assert len(res1["answers"]) == 1
        assert mock_notifier.send.call_count == 1

        # Simulate second resume pass
        res2 = node_ask(state, notifier=mock_notifier, db=mock_db)
        assert len(res2["answers"]) == 1
        # Notifier was NOT called again on second pass!
        assert mock_notifier.send.call_count == 1


def test_ask_node_calls_the_real_notifier_protocol_method() -> None:
    """The ask node must call Notifier.send. Calling a name the protocol does not define
    meant nothing was ever delivered while the question was recorded as sent."""
    action = _make_dummy_ask_action()
    state: EpisodeState = {
        "episode_id": "ep_protocol_check",
        "subject_id": "sub_001",
        "action": action,
        "step": 1,
    }

    notifier = MagicMock(spec=Notifier)
    notifier.send.return_value = True
    db = MagicMock()
    db.has_notification_for.return_value = False

    with patch(
        "wha.agent.nodes.ask.interrupt", return_value={"probe_id": "probe_alcohol", "option_id": "none"}
    ):
        node_ask(state, notifier=notifier, db=db)

    assert notifier.send.call_count == 1
    assert notifier.send.call_args.kwargs["kind"] == MessageKind.QUESTION
    # Delivery is only recorded once the transport confirms it.
    assert db.record_notification.call_count == 1


def test_failed_delivery_is_not_recorded_as_sent() -> None:
    """A transport that reports failure must not leave a delivery record behind.

    Recording it anyway parks the episode forever on an answer to a question the person
    was never actually asked.
    """
    action = _make_dummy_ask_action()
    state: EpisodeState = {
        "episode_id": "ep_failed_delivery",
        "subject_id": "sub_001",
        "action": action,
        "step": 1,
    }

    notifier = MagicMock(spec=Notifier)
    notifier.send.return_value = False
    db = MagicMock()
    db.has_notification_for.return_value = False

    with patch(
        "wha.agent.nodes.ask.interrupt", return_value={"probe_id": "probe_alcohol", "option_id": "none"}
    ):
        node_ask(state, notifier=notifier, db=db)

    assert notifier.send.call_count == 1
    assert db.record_notification.call_count == 0


def test_interrupt_resume_is_idempotent_on_writes() -> None:
    """Interaction rows are upserted with deterministic ids, ensuring exactly one logical record."""
    action = _make_dummy_ask_action()
    state: EpisodeState = {
        "episode_id": "ep_write_test",
        "subject_id": "sub_001",
        "action": action,
        "step": 1,
    }

    mock_db = MagicMock()
    mock_db.has_notification_for.return_value = True

    with patch(
        "wha.agent.nodes.ask.interrupt", return_value={"probe_id": "probe_alcohol", "option_id": "none"}
    ):
        node_ask(state, db=mock_db)
        node_ask(state, db=mock_db)

    # Both passes called upsert_interaction with the exact same interaction_id
    assert mock_db.upsert_interaction.call_count == 2
    id1 = mock_db.upsert_interaction.call_args_list[0].kwargs.get("interaction_id")
    id2 = mock_db.upsert_interaction.call_args_list[1].kwargs.get("interaction_id")
    assert id1 == id2
    assert id1 == "int_ep_write_test_probe_alcohol"


def test_timeout_resumes_with_timed_out_answer() -> None:
    """When a human wait times out, resumption produces an Answer with declined=True."""
    action = _make_dummy_ask_action()
    state: EpisodeState = {
        "episode_id": "ep_timeout_test",
        "subject_id": "sub_001",
        "action": action,
        "step": 1,
    }

    with patch("wha.agent.nodes.ask.interrupt", return_value={"timed_out": True}):
        res = node_ask(state)

    assert len(res["answers"]) == 1
    ans = res["answers"][0]
    assert ans.declined is True
    assert ans.option_id is None


def test_non_response_reaches_a_disposition() -> None:
    """Non-response is a designed path: policy reaches a valid terminal disposition without answers."""
    belief = _make_belief(0.12)

    # When question timeouts or budget exhausted, disposition is determined cleanly
    disp = determine_disposition(
        belief,
        rung=BaselineRung.MATURE,
        weekly_interruptions_used=2,
    )
    assert isinstance(disp, Disposition)
    assert disp == Disposition.UNRESOLVED


def test_llm_unavailable_in_ask_uses_fallback_text() -> None:
    """When LLM is unavailable during ask drafting, probe.fallback_text is used with text_source='fallback'."""
    orig_action = _make_dummy_ask_action()
    assert orig_action.question is not None

    # Construct question with text_source='llm'
    llm_question = Question(
        probe=orig_action.question.probe,
        text="Drafting...",
        text_source="llm",
        options=orig_action.question.options,
        allows_free_text=True,
    )
    action = orig_action.model_copy(update={"question": llm_question})

    state: EpisodeState = {
        "episode_id": "ep_fallback_test",
        "subject_id": "sub_001",
        "action": action,
        "step": 1,
    }

    mock_client = MagicMock()
    mock_client.complete.side_effect = LLMUnavailable("Ollama offline")

    captured_payload = {}

    def fake_interrupt(payload):
        captured_payload.update(payload)
        return {"probe_id": "probe_alcohol", "option_id": "none"}

    with patch("wha.agent.nodes.ask.interrupt", side_effect=fake_interrupt):
        res = node_ask(state, llm_client=mock_client)

    assert len(res["answers"]) == 1
    # Fallback text was delivered to the interrupt payload without raising
    assert captured_payload["text"] == "Did you have alcoholic drinks last night?"
