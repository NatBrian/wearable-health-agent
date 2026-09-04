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
