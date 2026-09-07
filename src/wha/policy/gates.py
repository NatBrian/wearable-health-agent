"""Decision gates evaluated before information seeking."""

from dataclasses import dataclass

from wha.constants import (
    DEPTH_BUDGET_PER_EPISODE,
    EPISODE_MAX_NIGHTS,
    EPISODE_MAX_STEPS,
    INTERRUPTION_BUDGET_PER_WEEK,
    SYMPTOM_FOLLOWUP_MAX_PER_EPISODE,
    SYMPTOM_FOLLOWUP_MIN_NIGHTS_APART,
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


def check_symptom_followup_gates(
    has_pending_interaction: bool,
    episode_followups_sent: int,
    followup_sent_tonight: bool = False,
) -> GateResult:
    """The gates a symptom follow-up must clear, which are fewer than a probe's.

    A follow-up is not an information-seeking question and must not be scored like one.
    EVSI measures how much an answer moves the belief across twelve CAUSES, so once a
    cause is settled, asking again is worth nothing by construction: the more certain the
    system becomes that somebody is ill, the less reason it has to speak to them. That is
    the arithmetic working exactly as designed, and it is the wrong arithmetic for the
    question "are you getting worse".

    WHICH GATES STILL APPLY, and why each survives:

    * PENDING INTERACTION always. Two open questions at once is how a person ends up
      answering one and having the other silently time out.
    * A per-episode cap on follow-ups, so this cannot become a nightly alarm. Alarm
      fatigue is a real harm and this project cites it in its own constants.
    * ONE PER NIGHT, whatever else happens. Added 7 September 2026 after the rule fired
      ten times in three minutes. `SYMPTOM_FOLLOWUP_MIN_NIGHTS_APART` had been declared
      in constants.py, documented as exactly this, and read by nothing. The per-episode
      cap could not cover for it: follow-up interactions are keyed by night, so every
      repeat inside one night upserts into a single row and the number the cap reads
      stays at one. The cap was never wrong. Its input could not reach the value that
      trips it.

    WHICH DO NOT, and why:

    * The weekly interruption budget. A budget exists to stop the system pestering a well
      person, and letting it silence somebody who has told us they feel unwell and is
      getting worse inverts its purpose. The budget is still SPENT and still shown; it
      simply cannot gag this particular question.
    * The EVSI score, which is the whole point.
    * The rung gates. Not knowing somebody's baseline well is a reason to be careful about
      interpreting their heart rate. It is not a reason to stop asking them how they feel.
    """
    if has_pending_interaction:
        return GateResult(
            allowed=False,
            reason="Another interaction is already pending with user",
        )
    if followup_sent_tonight:
        return GateResult(
            allowed=False,
            reason=(
                f"A symptom follow-up has already been sent tonight "
                f"(at most {SYMPTOM_FOLLOWUP_MIN_NIGHTS_APART} per night)"
            ),
        )
    if episode_followups_sent >= SYMPTOM_FOLLOWUP_MAX_PER_EPISODE:
        return GateResult(
            allowed=False,
            reason=(
                f"Symptom follow-up cap reached "
                f"({episode_followups_sent}/{SYMPTOM_FOLLOWUP_MAX_PER_EPISODE})"
            ),
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
