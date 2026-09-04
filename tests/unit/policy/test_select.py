"""The MEASURE limb: when the sensor itself is the leading explanation."""

from wha.models import ActionKind, BaselineRung, BeliefState, CauseId, Disposition
from wha.policy.select import determine_disposition, select_action


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
    "probe_medication",
]


def test_no_spot_reading_is_ever_requested() -> None:
    """The MEASURE limb was removed on 5 September 2026, so nothing selects it.

    These three tests asserted that a hand-taken pulse was requested when sensor artifact
    led the differential. That limb is gone, and the reason is worth keeping here because
    it is the reason the tests changed.

    Three invented numbers held it up, none of them from any paper: the 0.5 leading
    probability that decided when to ask, and the -1.5 and 0.3 log-factor the answer
    contributed, hardcoded in wha/belief/likelihood.py rather than in a knowledge table.
    It also could not complete: `_resume_value` in the scheduler answered every
    measurement interrupt with `declined` whatever the person did.

    And the idea is weaker than it looks. Asking somebody to count their own pulse for
    thirty seconds in order to judge whether their wrist sensor misread them asks the
    noisier instrument to adjudicate the less noisy one.

    What replaces it is saying so: when the sensor leads, the night could not be judged.
    """
    for probability in (0.9, 0.6, 0.5, 0.2):
        action = select_action(
            belief=_sensor_artifact_belief(p=probability),
            already_asked_probe_ids=_ALL_PROBES_ASKED,
        )
        assert action.kind != ActionKind.MEASURE, f"a spot reading was requested at p={probability}"
        assert action.measurement is None


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


def test_a_sensor_doubt_means_the_night_could_not_be_judged() -> None:
    """What replaces the spot reading, and it is the honest answer rather than a weaker one.

    The system used to respond to a leading sensor artifact by asking the person to count
    their own pulse. INSUFFICIENT_DATA already means "this night cannot be judged", it is
    already in the disposition set, and a COLD baseline already returns it for the same
    reason.
    """
    assert (
        determine_disposition(_sensor_artifact_belief(p=0.9), rung=BaselineRung.MATURE)
        == Disposition.INSUFFICIENT_DATA
    )


def test_a_sensor_doubt_never_talks_an_escalation_down() -> None:
    """Urgency may always rise. A doubt about the watch must not lower it."""
    from wha.models import BeliefState, CauseId

    marginals = {c: 0.02 for c in CauseId}
    marginals[CauseId.SENSOR_ARTIFACT] = 0.90
    marginals[CauseId.INFECTION] = 0.80
    belief = BeliefState(marginals=marginals, p_illness=0.80)

    assert determine_disposition(belief, rung=BaselineRung.MATURE) == Disposition.LIKELY_ILLNESS
