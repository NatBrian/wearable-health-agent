"""The MEASURE limb: when the sensor itself is the leading explanation."""

from wha.models import ActionKind, BeliefState, CauseId
from wha.policy.select import select_action


def _sensor_artifact_belief(p: float = 0.9) -> BeliefState:
    return BeliefState(
        marginals={c: (p if c is CauseId.SENSOR_ARTIFACT else 0.05) for c in CauseId},
        p_illness=0.05,
    )


_ALL_PROBES_ASKED = [
    "probe_symptoms",
    "probe_alcohol",
    "probe_exertion",
    "probe_sleep_quality",
    "probe_stress",
    "probe_vaccination",
    "probe_travel",
    "probe_cycle",
    "probe_medication",
]


def test_a_spot_reading_is_requested_when_the_sensor_itself_leads() -> None:
    """ActionKind.MEASURE was never selected by anything.

    It appeared only in the graph's router, so node_measure, the "A quick reading would
    help" screen, submit_measurement_done and compute_measurement_logfactor were all
    unreachable and the measurements table had never held a row. This is the case the limb
    was built for: no question can settle whether a watch misread you, and a hand-taken
    reading can.
    """
    action = select_action(
        belief=_sensor_artifact_belief(),
        already_asked_probe_ids=_ALL_PROBES_ASKED,
    )

    assert action.kind == ActionKind.MEASURE
    assert action.measurement is not None
    assert action.measurement.kind == "spot_resting_hr"
    assert "by hand" in action.measurement.instruction


def test_a_spot_reading_is_asked_for_once_per_episode() -> None:
    """Asking twice for the same reading is not more information, it is nagging."""
    action = select_action(
        belief=_sensor_artifact_belief(),
        already_asked_probe_ids=_ALL_PROBES_ASKED,
        already_measured=True,
    )

    assert action.kind != ActionKind.MEASURE


def test_no_spot_reading_when_the_sensor_is_merely_one_candidate() -> None:
    """It fires when the sensor leads, not whenever artifact is on the list at all."""
    action = select_action(
        belief=_sensor_artifact_belief(p=0.2),
        already_asked_probe_ids=_ALL_PROBES_ASKED,
    )

    assert action.kind != ActionKind.MEASURE


def test_a_spot_reading_never_stacks_on_an_outstanding_question() -> None:
    """The same gate that stops a second question stops this."""
    action = select_action(
        belief=_sensor_artifact_belief(),
        already_asked_probe_ids=_ALL_PROBES_ASKED,
        has_pending_interaction=True,
    )

    assert action.kind != ActionKind.MEASURE


def test_silence_never_produces_a_reassuring_conclusion() -> None:
    """Premature closure, with a name and a measured rate.

    Handler, Bedi and Shah, arXiv:2605.15000 (2026), define it as "inappropriate commitment
    under uncertainty: providing an answer, recommendation, or clinical guidance when the
    safer response would be clarification, abstention, escalation, or refusal", and measured
    false-action rates of 55 to 81 percent in frontier models on medical questions whose
    correct answer had been removed.

    This system did it deterministically: a timed-out question became a declined answer, a
    declined answer contributes no likelihood factor, so the belief never moved and the
    episode concluded LIKELY_BENIGN. It asked the most informative question it had, heard
    nothing, and reported that things were probably fine.
    """
    from wha.models import BaselineRung, Disposition
    from wha.policy.select import determine_disposition

    quiet = BeliefState(
        marginals={c: (0.30 if c is CauseId.STRESS else 0.05) for c in CauseId},
        p_illness=0.04,
    )

    answered = determine_disposition(quiet, rung=BaselineRung.MATURE, unanswered_questions=0)
    unanswered = determine_disposition(quiet, rung=BaselineRung.MATURE, unanswered_questions=1)

    assert answered == Disposition.LIKELY_BENIGN
    assert unanswered == Disposition.UNRESOLVED


def test_silence_cannot_talk_an_escalation_down() -> None:
    """Urgency may always rise. The unanswered check sits after the illness threshold."""
    from wha.models import BaselineRung, Disposition
    from wha.policy.select import determine_disposition

    concerning = BeliefState(
        marginals={c: (0.60 if c is CauseId.INFECTION else 0.05) for c in CauseId},
        p_illness=0.60,
    )

    assert (
        determine_disposition(concerning, rung=BaselineRung.MATURE, unanswered_questions=2)
        == Disposition.LIKELY_ILLNESS
    )


def test_a_recorded_event_still_explains_a_night_despite_an_unanswered_question() -> None:
    """An unanswered question is an absence of evidence, not evidence of absence.

    A workout the watch recorded is positive evidence from the device and does not depend
    on the person replying, so it is still allowed to explain the night.
    """
    from wha.models import BaselineRung, Disposition
    from wha.policy.select import determine_disposition

    explained = BeliefState(
        marginals={c: (0.70 if c is CauseId.EXERTION else 0.05) for c in CauseId},
        p_illness=0.03,
    )

    assert (
        determine_disposition(explained, rung=BaselineRung.MATURE, unanswered_questions=1)
        == Disposition.EXPLAINED_BY_EVENT
    )
