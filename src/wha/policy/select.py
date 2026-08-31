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
            text_source="fallback",
            options=best_probe.answer_space,
            allows_free_text=True,
        )

        return Action(
            kind=ActionKind.ASK,
            question=question_model,
            rationale=f"Selected highest EVSI probe '{best_probe.probe_id}' with positive net value {best_score}",
            rejected=rejected_for_ask,
        )

    # 5. Check if another night of observation could plausibly resolve decision
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

    # 6. Conclude and assign disposition from belief
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

    # Check if a non-illness confounder dominates and explains the residual
    top_cause, top_prob = belief.top(1)[0]
    if (
        top_cause != CauseId.INFECTION
        and top_cause != CauseId.UNEXPLAINED
        and top_prob >= 0.50
        and p_inf < DERIVED_TREATMENT_THRESHOLD
    ):
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
