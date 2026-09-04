"""Policy action selection, disposition mapping, and probe scoring."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from wha.constants import (
    DEPTH_BUDGET_PER_EPISODE,
    EPISODE_MAX_NIGHTS,
    EPISODE_MAX_STEPS,
    MEASURE_MIN_LEADING_PROBABILITY,
    MEASUREMENT_TIMEOUT_HOURS,
    POLICY_COST_PER_INTERRUPT,
)
from wha.models import (
    Action,
    ActionKind,
    BaselineRung,
    BeliefState,
    CauseId,
    Disposition,
    MeasurementRequest,
    Probe,
    Question,
)
from wha.policy.evsi import DERIVED_TREATMENT_THRESHOLD, evsi, score_probe
from wha.policy.gates import check_all_ask_gates
from wha.policy.probes import ProbeDefinition, load_probes


def select_action(
    belief: BeliefState,
    probes: Sequence[ProbeDefinition] | None = None,
    weekly_interruptions_used: int = 0,
    episode_questions_asked: int = 0,
    rung: BaselineRung = BaselineRung.MATURE,
    nights_in_episode: int = 1,
    steps_in_episode: int = 1,
    has_pending_interaction: bool = False,
    already_asked_probe_ids: Sequence[str] = (),
    has_symptoms_evidence: bool = False,
    cost_per_interrupt: float = POLICY_COST_PER_INTERRUPT,
    already_measured: bool = False,
) -> Action:
    """Select the next policy action following the deterministic 6-step contract."""
    all_probes = probes if probes is not None else load_probes()
    asked_set = set(already_asked_probe_ids)

    # 1. Evaluate and score all unasked probes
    candidate_scores: list[tuple[ProbeDefinition, float]] = []
    for p in all_probes:
        if p.probe_id not in asked_set:
            sc = score_probe(belief, p, cost_per_interrupt=cost_per_interrupt)
            candidate_scores.append((p, sc))

    # Deterministic sorting: highest score first, tie-break on lower interruption cost, then probe_id
    candidate_scores.sort(key=lambda item: (-item[1], item[0].interruption_cost, item[0].probe_id))

    all_rejected: list[tuple[str, float]] = [(p.probe_id, sc) for p, sc in candidate_scores]

    # 2. Hard caps check
    if nights_in_episode >= EPISODE_MAX_NIGHTS or steps_in_episode >= EPISODE_MAX_STEPS:
        return Action(
            kind=ActionKind.CONCLUDE,
            disposition=Disposition.UNRESOLVED,
            rationale="Episode maximum duration or steps cap exceeded",
            rejected=all_rejected,
        )

    # 3. Check gates for asking questions
    ask_gate = check_all_ask_gates(
        rung=rung,
        weekly_interruptions=weekly_interruptions_used,
        episode_questions=episode_questions_asked,
        has_pending_interaction=has_pending_interaction,
    )

    # 4. If asking is allowed and best probe scores > 0 -> ASK
    if ask_gate.allowed and candidate_scores and candidate_scores[0][1] > 0.0:
        best_probe, best_score = candidate_scores[0]
        rejected_for_ask = [
            (p.probe_id, sc) for p, sc in candidate_scores if p.probe_id != best_probe.probe_id
        ]

        probe_model = Probe(
            probe_id=best_probe.probe_id,
            target_cause=best_probe.target_cause,
            answer_space=best_probe.answer_space,
            evsi=evsi(belief, best_probe),
            interruption_cost=best_probe.interruption_cost,
            fallback_text=best_probe.fallback_text,
        )

        question_model = Question(
            probe=probe_model,
            text=best_probe.fallback_text,
            # Asks the ask node to have the model word this, falling back to the text above
            # if it is unavailable or returns something invalid.
            #
            # This said "fallback", and the ask node only calls the model when it reads
            # "llm". Since this is the only place a Question is constructed, that branch
            # was unreachable and every question the system ever asked was the canned
            # fallback sentence. The prompt, the node and the provider all worked; nothing
            # could ever reach them.
            text_source="llm",
            options=best_probe.answer_space,
            allows_free_text=True,
        )

        return Action(
            kind=ActionKind.ASK,
            question=question_model,
            rationale=f"Selected highest EVSI probe '{best_probe.probe_id}' with positive net value {best_score}",
            rejected=rejected_for_ask,
        )

    # 5. A spot reading, when the leading explanation is the sensor itself.
    #
    # ActionKind.MEASURE appeared only in the graph's router. The policy never selected it,
    # so node_measure, the "A quick reading would help" screen, submit_measurement_done and
    # compute_measurement_logfactor were all unreachable and the measurements table had
    # never held a row. A whole limb of a health system that had never executed.
    #
    # This is the case it was built for. When sensor artifact leads the differential, no
    # question can settle it: the person cannot tell you whether their watch misread them.
    # A resting heart rate taken by hand can, and compute_measurement_logfactor already
    # knows what to do with the answer, moving weight away from sensor artifact when a
    # manual reading agrees with the device.
    #
    # Gated on the same pending check as asking, so it cannot stack on an outstanding
    # question, and it consumes the episode depth budget rather than the weekly one
    # because it is a request rather than an interruption.
    leading_cause, leading_p = (belief.top(1) or [(None, 0.0)])[0]
    if (
        leading_cause is CauseId.SENSOR_ARTIFACT
        and leading_p >= MEASURE_MIN_LEADING_PROBABILITY
        and not has_pending_interaction
        and episode_questions_asked < DEPTH_BUDGET_PER_EPISODE
        and not already_measured
    ):
        return Action(
            kind=ActionKind.MEASURE,
            measurement=MeasurementRequest(
                measurement_id=f"m_{uuid.uuid4().hex[:12]}",
                kind="spot_resting_hr",
                instruction=(
                    "Sit still for two minutes, then take your resting heart rate by hand: "
                    "count the beats at your wrist for 30 seconds and double it. Your watch "
                    "may have misread last night, and a reading you took yourself is the "
                    "only way to tell."
                ),
                expires_at_utc=datetime.now(UTC) + timedelta(hours=MEASUREMENT_TIMEOUT_HOURS),
            ),
            rationale=(
                f"Sensor artifact leads the differential at {leading_p:.2f}. No question "
                "can resolve it; a hand-taken reading can."
            ),
            rejected=all_rejected,
        )

    # 6. Check if another night of observation could plausibly resolve decision
    # Inside active uncertainty band and budget allows more nights
    p_inf = belief.p_illness
    inside_uncertainty_band = 0.05 <= p_inf <= 0.40
    if (
        inside_uncertainty_band
        and nights_in_episode < EPISODE_MAX_NIGHTS
        and not has_pending_interaction
    ):
        return Action(
            kind=ActionKind.OBSERVE,
            rationale="Belief is inside uncertainty band; observing next night data",
            rejected=all_rejected,
        )

    # 7. Conclude and assign disposition from belief
    disposition = determine_disposition(
        belief=belief,
        rung=rung,
        nights_in_episode=nights_in_episode,
        weekly_interruptions_used=weekly_interruptions_used,
        episode_questions_asked=episode_questions_asked,
        has_symptoms_evidence=has_symptoms_evidence,
    )

    return Action(
        kind=ActionKind.CONCLUDE,
        disposition=disposition,
        rationale=f"Concluding episode with disposition {disposition}",
        rejected=all_rejected,
    )


# Causes that correspond to a discrete, datable occurrence rather than an ongoing state.
# Only these can justify EXPLAINED_BY_EVENT.
EVENT_CAUSES = frozenset(
    {
        CauseId.EXERTION,
        CauseId.ALCOHOL,
        CauseId.VACCINATION,
        CauseId.TRAVEL,
        CauseId.MEDICATION,
    }
)


def determine_disposition(
    belief: BeliefState,
    rung: BaselineRung,
    nights_in_episode: int = 1,
    weekly_interruptions_used: int = 0,
    episode_questions_asked: int = 0,
    has_symptoms_evidence: bool = False,
) -> Disposition:
    """Map final belief and episode context to a terminal disposition."""
    if rung == BaselineRung.COLD:
        return Disposition.INSUFFICIENT_DATA

    p_inf = belief.p_illness

    # Check if a discrete event explains the residual.
    #
    # Restricted to causes that correspond to something that actually happened and was
    # recorded or reported: a workout, a drink, a jab, a flight, a medication change.
    # Ongoing states such as stress, short sleep or cycle phase are not events, and
    # reporting "explained by event" for them overstates what the system knows. Those
    # resolve as LIKELY_BENIGN, which is the honest reading of a low illness probability
    # with no discrete cause behind it.
    top_cause, top_prob = belief.top(1)[0]
    if top_cause in EVENT_CAUSES and top_prob >= 0.50 and p_inf < DERIVED_TREATMENT_THRESHOLD:
        return Disposition.EXPLAINED_BY_EVENT

    # Check budget/caps exhaustion inside the band
    if (
        weekly_interruptions_used >= 2
        or episode_questions_asked >= 5
        or nights_in_episode >= EPISODE_MAX_NIGHTS
    ) and (0.08 <= p_inf <= 0.25):
        return Disposition.UNRESOLVED

    # Illness vs Benign thresholding (at derived threshold 0.10)
    if p_inf >= DERIVED_TREATMENT_THRESHOLD:
        return Disposition.LIKELY_ILLNESS

    return Disposition.LIKELY_BENIGN
