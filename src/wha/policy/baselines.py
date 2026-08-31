"""Benchmark comparison policies for evaluation."""

import random
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
    Disposition,
    Probe,
    Question,
)
from wha.policy.evsi import evsi, score_probe
from wha.policy.gates import check_all_ask_gates
from wha.policy.probes import ProbeDefinition, load_probes
from wha.policy.select import determine_disposition


def _build_ask_action(
    probe: ProbeDefinition,
    belief: BeliefState,
    rationale: str,
    rejected: list[tuple[str, float]],
) -> Action:
    probe_model = Probe(
        probe_id=probe.probe_id,
        target_cause=probe.target_cause,
        answer_space=probe.answer_space,
        evsi=evsi(belief, probe),
        interruption_cost=probe.interruption_cost,
        fallback_text=probe.fallback_text,
    )
    question_model = Question(
        probe=probe_model,
        text=probe.fallback_text,
        text_source="fallback",
        options=probe.answer_space,
        allows_free_text=True,
    )
    return Action(
        kind=ActionKind.ASK,
        question=question_model,
        rationale=rationale,
        rejected=rejected,
    )


def policy_never_ask(
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
    """Baseline: Never asks any questions. Concludes or observes solely on sensor evidence."""
    all_probes = probes if probes is not None else load_probes()
    rejected = [(p.probe_id, 0.0) for p in all_probes]

    if nights_in_episode >= EPISODE_MAX_NIGHTS or steps_in_episode >= EPISODE_MAX_STEPS:
        return Action(
            kind=ActionKind.CONCLUDE,
            disposition=Disposition.UNRESOLVED,
            rationale="Episode maximum duration or steps cap exceeded",
            rejected=rejected,
        )

    if (
        0.05 <= belief.p_illness <= 0.40
        and nights_in_episode < EPISODE_MAX_NIGHTS
        and not has_pending_interaction
    ):
        return Action(
            kind=ActionKind.OBSERVE,
            rationale="Never-ask policy observing next night data",
            rejected=rejected,
        )

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
        rationale=f"Never-ask policy concluding with disposition {disposition}",
        rejected=rejected,
    )


def policy_always_ask(
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
    """Baseline: Asks the highest-EVSI probe whenever any unasked probe exists and gates allow."""
    all_probes = probes if probes is not None else load_probes()
    asked_set = set(already_asked_probe_ids)

    candidate_scores: list[tuple[ProbeDefinition, float]] = [
        (p, evsi(belief, p)) for p in all_probes if p.probe_id not in asked_set
    ]
    candidate_scores.sort(key=lambda item: (-item[1], item[0].interruption_cost, item[0].probe_id))
    rejected = [(p.probe_id, sc) for p, sc in candidate_scores]

    if nights_in_episode >= EPISODE_MAX_NIGHTS or steps_in_episode >= EPISODE_MAX_STEPS:
        return Action(
            kind=ActionKind.CONCLUDE,
            disposition=Disposition.UNRESOLVED,
            rationale="Episode maximum duration or steps cap exceeded",
            rejected=rejected,
        )

    ask_gate = check_all_ask_gates(
        rung=rung,
        weekly_interruptions=weekly_interruptions_used,
        episode_questions=episode_questions_asked,
        has_pending_interaction=has_pending_interaction,
    )

    if ask_gate.allowed and candidate_scores:
        best_probe, best_evsi = candidate_scores[0]
        rejected_for_ask = [
            (p.probe_id, sc) for p, sc in candidate_scores if p.probe_id != best_probe.probe_id
        ]
        return _build_ask_action(
            best_probe,
            belief,
            f"Always-ask policy selected probe '{best_probe.probe_id}' with EVSI {best_evsi}",
            rejected_for_ask,
        )

    if (
        0.05 <= belief.p_illness <= 0.40
        and nights_in_episode < EPISODE_MAX_NIGHTS
        and not has_pending_interaction
    ):
        return Action(
            kind=ActionKind.OBSERVE,
            rationale="Always-ask policy observing next night data",
            rejected=rejected,
        )

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
        rationale=f"Always-ask policy concluding with disposition {disposition}",
        rejected=rejected,
    )


def policy_threshold(
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
    """Baseline: Asks if p_illness is within [0.10, 0.75], completely ignoring EVSI."""
    all_probes = probes if probes is not None else load_probes()
    asked_set = set(already_asked_probe_ids)

    candidate_probes = [p for p in all_probes if p.probe_id not in asked_set]
    candidate_probes.sort(key=lambda p: (p.interruption_cost, p.probe_id))
    rejected = [(p.probe_id, score_probe(belief, p, cost_per_interrupt)) for p in candidate_probes]

    if nights_in_episode >= EPISODE_MAX_NIGHTS or steps_in_episode >= EPISODE_MAX_STEPS:
        return Action(
            kind=ActionKind.CONCLUDE,
            disposition=Disposition.UNRESOLVED,
            rationale="Episode maximum duration or steps cap exceeded",
            rejected=rejected,
        )

    ask_gate = check_all_ask_gates(
        rung=rung,
        weekly_interruptions=weekly_interruptions_used,
        episode_questions=episode_questions_asked,
        has_pending_interaction=has_pending_interaction,
    )

    # Ask iff p_illness in [0.10, 0.75]
    if ask_gate.allowed and candidate_probes and (0.10 <= belief.p_illness <= 0.75):
        best_probe = candidate_probes[0]
        rejected_for_ask = [
            (p.probe_id, 0.0) for p in candidate_probes if p.probe_id != best_probe.probe_id
        ]
        return _build_ask_action(
            best_probe,
            belief,
            f"Threshold policy asking probe '{best_probe.probe_id}' based on p_illness={belief.p_illness}",
            rejected_for_ask,
        )

    if (
        0.05 <= belief.p_illness <= 0.40
        and nights_in_episode < EPISODE_MAX_NIGHTS
        and not has_pending_interaction
    ):
        return Action(
            kind=ActionKind.OBSERVE,
            rationale="Threshold policy observing next night data",
            rejected=rejected,
        )

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
        rationale=f"Threshold policy concluding with disposition {disposition}",
        rejected=rejected,
    )


def policy_random(
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
    ask_probability: float = 0.35,
    rng: random.Random | None = None,
) -> Action:
    """Baseline: Asks randomly matched to the average interrogation rate."""
    all_probes = probes if probes is not None else load_probes()
    asked_set = set(already_asked_probe_ids)

    candidate_probes = [p for p in all_probes if p.probe_id not in asked_set]
    rejected = [(p.probe_id, 0.0) for p in candidate_probes]

    if nights_in_episode >= EPISODE_MAX_NIGHTS or steps_in_episode >= EPISODE_MAX_STEPS:
        return Action(
            kind=ActionKind.CONCLUDE,
            disposition=Disposition.UNRESOLVED,
            rationale="Episode maximum duration or steps cap exceeded",
            rejected=rejected,
        )

    ask_gate = check_all_ask_gates(
        rung=rung,
        weekly_interruptions=weekly_interruptions_used,
        episode_questions=episode_questions_asked,
        has_pending_interaction=has_pending_interaction,
    )

    r = rng if rng is not None else random.Random()
    if ask_gate.allowed and candidate_probes and r.random() < ask_probability:
        chosen_probe = r.choice(candidate_probes)
        rejected_for_ask = [
            (p.probe_id, 0.0) for p in candidate_probes if p.probe_id != chosen_probe.probe_id
        ]
        return _build_ask_action(
            chosen_probe,
            belief,
            f"Random policy asked probe '{chosen_probe.probe_id}' at random",
            rejected_for_ask,
        )

    if (
        0.05 <= belief.p_illness <= 0.40
        and nights_in_episode < EPISODE_MAX_NIGHTS
        and not has_pending_interaction
    ):
        return Action(
            kind=ActionKind.OBSERVE,
            rationale="Random policy observing next night data",
            rejected=rejected,
        )

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
        rationale=f"Random policy concluding with disposition {disposition}",
        rejected=rejected,
    )
