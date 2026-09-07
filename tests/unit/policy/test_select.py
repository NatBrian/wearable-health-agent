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


def test_the_real_belief_model_cannot_produce_the_state_the_sensor_gate_needed() -> None:
    """This test used to assert the gate worked, from a state production never reaches.

    It called `_sensor_artifact_belief(p=0.9)`, a hand-built BeliefState with
    sensor_artifact at 0.9 and p_illness pinned at 0.05. `update_belief` does not produce
    that pair: the same large residual that pushes sensor_artifact up also pushes p_illness
    up, so by the time sensor_artifact clears 0.50 the illness probability has cleared the
    0.10 treatment threshold and the gate's second condition is false.

    Measured over 20 combinations of coverage 30 to 239 minutes and residual 3.2 to 10.0
    bpm, the gate fired in NONE of them, so it was deleted rather than retuned. Moving 0.50
    or 0.10 to make it fire would be choosing a clinical threshold to satisfy a feature.

    This is the seeded-fixture pattern that this repository keeps repeating: a test builds
    the state the code needs, the code passes, and production never gets there. So this
    test now drives the REAL belief model and asserts the property that actually holds.
    """
    from datetime import date

    from wha.belief import update_belief
    from wha.models import Detection, DetectionLevel, Forecast, NightlyFeatures

    def night(day: int, residual: float) -> Detection:
        return Detection(
            subject_id="s",
            night_date=date(2026, 9, day),
            level=DetectionLevel.RED,
            flagged=True,
            residual_bpm=residual,
            robust_z=residual / 3.7,
            forecast=Forecast(),
        )

    def feature(day: int, coverage: int) -> NightlyFeatures:
        return NightlyFeatures(
            subject_id="s",
            night_date=date(2026, 9, day),
            rhr_bpm=70.0,
            coverage_minutes=coverage,
            usable=coverage >= 180,
        )

    seen_both = []
    for coverage in (30, 60, 120, 200, 239):
        for residual in (3.2, 4.0, 6.0, 10.0):
            nights = [night(4, residual), night(5, residual)]
            features = [feature(4, coverage), feature(5, coverage)]
            belief = update_belief(episode_nights=nights, features=features, luteal_applicable=None)
            top_cause, top_prob = belief.top(1)[0]
            if (
                top_cause is CauseId.SENSOR_ARTIFACT
                and top_prob >= 0.50
                and belief.p_illness < 0.10
            ):
                seen_both.append((coverage, residual, top_prob, belief.p_illness))

    assert not seen_both, (
        "the belief model now reaches the state the deleted gate needed, so the decision "
        f"to delete it should be revisited: {seen_both}"
    )

    # And INSUFFICIENT_DATA is still reachable, from the one branch that does work.
    assert (
        determine_disposition(_sensor_artifact_belief(p=0.9), rung=BaselineRung.COLD)
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


def test_a_one_time_probe_answered_before_is_not_even_considered() -> None:
    """`one_time` was in probes.yaml and dropped silently on load.

    ProbeDefinition forbids extra fields and load_probes built it field by field without
    reading the flag, so probe_medication was priced at 0.4 of an interruption on a promise
    that was not kept: the same setup question could be asked again in every new
    investigation, spending part of a weekly allowance each time.

    Asserted on `rejected`, which lists every probe the policy scored, because that proves
    the probe left the candidate set whatever action ends up winning.
    """
    from wha.policy.probes import load_probes

    one_time = [p.probe_id for p in load_probes() if p.one_time]
    assert one_time, "the flag is being dropped on load again"

    belief = _sensor_artifact_belief(p=0.1)

    considered = {pid for pid, _ in select_action(belief=belief).rejected}
    assert set(one_time) <= considered, "a one-time probe was never a candidate to begin with"

    after = {
        pid for pid, _ in select_action(belief=belief, answered_probe_ids_ever=one_time).rejected
    }
    assert not (set(one_time) & after), (
        "a one-time probe answered in an earlier episode was scored again"
    )


def test_a_repeatable_probe_is_not_skipped_by_an_earlier_answer() -> None:
    """The skip applies to one_time probes only. Everything else may be asked again.

    Compared with and without, because the winning probe is excluded from `rejected` and
    a straight containment check would fail on that one alone.
    """
    from wha.policy.probes import load_probes

    repeatable = [p.probe_id for p in load_probes() if not p.one_time]
    belief = _sensor_artifact_belief(p=0.1)

    def considered(**kwargs) -> set[str]:
        return {pid for pid, _ in select_action(belief=belief, **kwargs).rejected}

    assert considered() == considered(answered_probe_ids_ever=repeatable)
