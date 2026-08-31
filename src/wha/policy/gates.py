"""Decision gates evaluated before information seeking."""

from dataclasses import dataclass

from wha.constants import (
    DEPTH_BUDGET_PER_EPISODE,
    EPISODE_MAX_NIGHTS,
    EPISODE_MAX_STEPS,
    INTERRUPTION_BUDGET_PER_WEEK,
)
from wha.models import BaselineRung


@dataclass(frozen=True)
class GateResult:
    allowed: bool
    reason: str | None = None


def check_rung_gate(rung: BaselineRung) -> GateResult:
    """Rung gate: COLD never opens an episode; PRIOR_DOMINATED may not ask questions."""
    if rung == BaselineRung.COLD:
        return GateResult(allowed=False, reason="Baseline is on COLD rung")
    if rung == BaselineRung.PRIOR_DOMINATED:
        return GateResult(
            allowed=False,
            reason="Baseline is on PRIOR_DOMINATED rung (cannot ask questions)",
        )
    return GateResult(allowed=True)


def check_interruption_budget_gate(weekly_interruptions_used: int) -> GateResult:
    """Rolling 7-day budget gate: max INTERRUPTION_BUDGET_PER_WEEK interruptions."""
    if weekly_interruptions_used >= INTERRUPTION_BUDGET_PER_WEEK:
        return GateResult(
            allowed=False,
            reason=f"Weekly interruption budget exhausted ({weekly_interruptions_used}/{INTERRUPTION_BUDGET_PER_WEEK})",
        )
    return GateResult(allowed=True)


def check_depth_budget_gate(episode_questions_asked: int) -> GateResult:
    """Episode depth gate: max DEPTH_BUDGET_PER_EPISODE questions per episode."""
    if episode_questions_asked >= DEPTH_BUDGET_PER_EPISODE:
        return GateResult(
            allowed=False,
            reason=f"Episode depth budget exhausted ({episode_questions_asked}/{DEPTH_BUDGET_PER_EPISODE})",
        )
    return GateResult(allowed=True)


def check_pending_interaction_gate(has_pending_interaction: bool) -> GateResult:
    """Concurrency gate: at most one active interaction awaiting user."""
    if has_pending_interaction:
        return GateResult(
            allowed=False,
            reason="Another interaction is already pending with user",
        )
    return GateResult(allowed=True)


def check_episode_caps_gate(nights_in_episode: int, steps_in_episode: int) -> GateResult:
    """Hard safety caps on episode duration and graph recursion."""
    if nights_in_episode >= EPISODE_MAX_NIGHTS:
        return GateResult(
            allowed=False,
            reason=f"Episode max nights cap reached ({nights_in_episode}/{EPISODE_MAX_NIGHTS})",
        )
    if steps_in_episode >= EPISODE_MAX_STEPS:
        return GateResult(
            allowed=False,
            reason=f"Episode max steps cap reached ({steps_in_episode}/{EPISODE_MAX_STEPS})",
        )
    return GateResult(allowed=True)


def check_all_ask_gates(
    rung: BaselineRung,
    weekly_interruptions: int,
    episode_questions: int,
    has_pending_interaction: bool = False,
) -> GateResult:
    """Evaluate all question-asking gates in contract order."""
    rung_res = check_rung_gate(rung)
    if not rung_res.allowed:
        return rung_res

    budget_res = check_interruption_budget_gate(weekly_interruptions)
    if not budget_res.allowed:
        return budget_res

    depth_res = check_depth_budget_gate(episode_questions)
    if not depth_res.allowed:
        return depth_res

    pending_res = check_pending_interaction_gate(has_pending_interaction)
    if not pending_res.allowed:
        return pending_res

    return GateResult(allowed=True)
