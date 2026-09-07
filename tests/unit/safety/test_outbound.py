"""Unit tests for outbound message validation and fallback safety enforcement."""

from wha.policy.probes import ProbeDefinition
from wha.safety import OutboundMessage, validate_outbound


def test_outbound_rejects_url() -> None:
    """Outbound questions with embedded external URLs are rejected and fallback to probe text."""
    msg = OutboundMessage(
        kind="QUESTION",
        text="Visit https://malicious-site.com/survey to log your symptoms.",
        probe_id="probe_alcohol",
        option_labels=["None", "Yes"],
    )

    res = validate_outbound(msg)
    assert res.valid is True
    assert res.text_source == "fallback"
    assert res.safety_event == "outbound_rejected"
    assert "https://" not in res.text_to_send


def test_outbound_rejects_slot_mismatch() -> None:
    """Option labels whose count does not match the probe's answer space trigger fallback.

    probe_alcohol has TWO options now, not four: the belief model has one on-off alcohol
    switch, so the four-way question collected a detail nothing could use. The mismatch is
    restated against that, because the test is about the count disagreeing and not about
    any particular count.
    """
    msg = OutboundMessage(
        kind="QUESTION",
        text="Did you have any drinks last night?",
        probe_id="probe_alcohol",
        option_labels=["None", "1 to 2", "3 or more"],  # Mismatch: 3 against 2
    )

    res = validate_outbound(msg)
    assert res.valid is True
    assert res.text_source == "fallback"
    assert res.safety_event == "outbound_rejected"


def test_outbound_rejects_oversize_callback_data() -> None:
    """callback_data exceeding 64 bytes is rejected and triggers fallback."""
    oversize_cb = "x" * 70  # 70 bytes > 64 bytes
    msg = OutboundMessage(
        kind="QUESTION",
        text="How was your sleep?",
        probe_id="probe_sleep_quality",
        option_labels=[
            "Normal",
            "Short, by choice",
            "Broken or restless",
            "Poor because I felt unwell",
        ],
        callback_data_list=[oversize_cb],
    )

    res = validate_outbound(msg)
    assert res.valid is True
    assert res.text_source == "fallback"
    assert res.safety_event == "outbound_rejected"


def test_outbound_rejects_over_length() -> None:
    """Message text exceeding OUTBOUND_MAX_CHARS (900 chars) is rejected."""
    huge_text = "A" * 950
    msg = OutboundMessage(
        kind="QUESTION",
        text=huge_text,
        probe_id="probe_alcohol",
        option_labels=["None", "1 to 2", "3 to 4", "5 or more"],
    )

    res = validate_outbound(msg)
    assert res.valid is True
    assert res.text_source == "fallback"
    assert res.safety_event == "outbound_rejected"


def test_unvalidatable_fallback_is_not_sent() -> None:
    """If a probe fallback itself is invalid (e.g. over length), message is not sent and episode parks."""
    corrupted_probe = ProbeDefinition(
        probe_id="corrupted_probe",
        target_cause="infection",
        interruption_cost=0.3,
        fallback_text="https://evil.com " + ("Bad " * 300),  # URL + overlength
        answer_space=[],
        likelihood_present={},
        likelihood_absent={},
        provenance="ASSUMED",
        assumption="Test corrupted probe",
    )

    msg = OutboundMessage(
        kind="QUESTION",
        text="https://evil.com initial text",
        probe_id="corrupted_probe",
    )

    cache = {"corrupted_probe": corrupted_probe}
    res = validate_outbound(msg, probes_cache=cache)

    assert res.valid is False
    assert res.park_episode is True
    assert res.text_to_send == ""
    assert res.text_source == "none"
