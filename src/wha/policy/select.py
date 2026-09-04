"""Policy action selection, disposition mapping, and probe scoring."""

from collections.abc import Sequence

from wha.constants import (
    EPISODE_MAX_NIGHTS,
    EPISODE_MAX_STEPS,
    POLICY_COST_PER_INTERRUPT,
)
from wha.models import (
    Action,
    ActionKind,
    BaselineRung,
    BeliefState,
    CauseId,
    Disposition,
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
    unanswered_questions: int = 0,
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

    # 5. THE SPOT READING WAS REMOVED ON 5 SEPTEMBER 2026.
    #
    # When sensor artifact led the differential the policy asked the person to count their
    # own pulse for thirty seconds and double it. Three invented numbers held that up, none
    # of them from any paper:
    #
    #   MEASURE_MIN_LEADING_PROBABILITY = 0.5   when to ask
    #   -1.5 and 0.3                            what the answer was worth, hardcoded in
    #                                           wha/belief/likelihood.py, not even in the
    #                                           knowledge tables
    #
    # And it could not complete: `_resume_value` in the scheduler answered every
    # measurement interrupt with `declined`, whatever the person did.
    #
    # The idea is also weaker than it looks. Asking a hand count to adjudicate a wrist
    # sensor asks a noisier instrument to judge a less noisy one. The honest behaviour when
    # the sensor is the leading explanation is to say the night could not be judged, which
    # is what `determine_disposition` now does through INSUFFICIENT_DATA.
    #
    # The `measurements` table is kept so databases written before this still open.

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
        unanswered_questions=unanswered_questions,
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
    unanswered_questions: int = 0,
) -> Disposition:
    """Map final belief and episode context to a terminal disposition.

    ``unanswered_questions`` counts questions the system asked and never got an answer to,
    including ones that timed out. Concluding anything reassuring from silence is the
    error this parameter exists to prevent.
    """
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

    # When the watch itself is the leading explanation, say the night could not be judged.
    #
    # The system used to ask for a hand-taken pulse here instead. That limb was removed on
    # 5 September 2026: it rested on three numbers with no source, and it asked the
    # noisier instrument to adjudicate the less noisy one. This is what replaces it, and
    # it is the honest answer rather than a weaker one. INSUFFICIENT_DATA already means
    # "this night cannot be judged", it is already in the disposition set, and it is
    # already what a COLD baseline returns for the same reason.
    #
    # Placed after the illness check for the same reason silence is: a sensor doubt must
    # never be able to talk an escalation down, only to prevent a confident conclusion.
    if (
        top_cause is CauseId.SENSOR_ARTIFACT
        and top_prob >= 0.50
        and p_inf < DERIVED_TREATMENT_THRESHOLD
    ):
        return Disposition.INSUFFICIENT_DATA

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

    # A question that was asked and never answered cannot support a reassuring conclusion.
    #
    # This is premature closure, and it has a name and a measured rate. Handler, Bedi and
    # Shah, arXiv:2605.15000 (2026), define it as "inappropriate commitment under
    # uncertainty: providing an answer, recommendation, or clinical guidance when the safer
    # response would be clarification, abstention, escalation, or refusal", and measured
    # false-action rates of 55 to 81 percent in frontier models on medical questions whose
    # correct answer had been removed.
    #
    # That is exactly what happened here. A timed-out question became a declined answer,
    # a declined answer contributes no likelihood factor, so the belief never moved and the
    # episode fell through to LIKELY_BENIGN. The system asked the one question it judged
    # most informative, heard nothing, and reported that things were probably fine.
    #
    # UNRESOLVED is the honest reading, and the disposition set already contains it. Placed
    # after the illness check because urgency may always rise: silence must never be able
    # to talk an escalation down, only to prevent a reassurance.
    if unanswered_questions > 0:
        return Disposition.UNRESOLVED

    return Disposition.LIKELY_BENIGN
