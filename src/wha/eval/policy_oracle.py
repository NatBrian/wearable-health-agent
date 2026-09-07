"""Policy evaluation benchmark against a hidden-self-report oracle.

Every figure this module reports is measured by running the real policies through the
real belief model. It previously returned hardcoded accuracy constants
(``evsi_mean_accuracy: 0.84``) and closed-form curves (``0.70 + 0.15 / cost_weight``)
that no policy had ever produced, wrote them to ``data/eval/policy.json``, and surfaced
them in the dashboard behind a button labelled "Run Policy Suite".
"""

from datetime import date, timedelta
from pathlib import Path
from typing import Any

from wha.clock import now_utc
from wha.constants import POLICY_COST_PER_INTERRUPT
from wha.models import (
    Action,
    ActionKind,
    Answer,
    BeliefState,
    Detection,
    DetectionLevel,
    EvaluationResult,
    Forecast,
    ForecastStatus,
)
from wha.policy.evsi import DERIVED_TREATMENT_THRESHOLD
from wha.policy.probes import load_probes

INJECTION_AMPLITUDES = [1.0, 2.0, 4.0, 6.0, 8.0]
INJECTION_DURATIONS = [1, 2, 4, 7]

# Cost weights swept for the frontier. POLICY_COST_PER_INTERRUPT is annotated "Swept" in
# both constants.py and docs/CONTRACTS.md, and is exposed to the user as
# policy_cost_weight, so it is a tuning parameter rather than a cited clinical figure.
COST_WEIGHT_SWEEP = [0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 1.00]

_EVAL_START = date(2026, 8, 1)


class PolicyOracleHarness:
    """Simulated oracle over confounder annotations, revealing self-reports strictly on query."""

    def __init__(self, ground_truth_answers: dict[str, str]) -> None:
        self._answers = ground_truth_answers
        self.revealed_answers: dict[str, str] = {}
        self.query_count = 0

    def query(self, probe_id: str) -> str | None:
        """Reveal ground-truth self report for probe_id if present in oracle."""
        self.query_count += 1
        ans = self._answers.get(probe_id)
        if ans is not None:
            self.revealed_answers[probe_id] = ans
        return ans


def evaluate_policy_on_oracle(
    policy_fn: Any,
    belief: BeliefState,
    detections: list[Detection],
    oracle: PolicyOracleHarness,
    probe_cost_weight: float = 1.0,
    depth_budget: int = 2,
) -> tuple[Action, int]:
    """Step a policy against the oracle until terminal action or budget exhaustion."""
    probes = load_probes()
    interruptions_spent = 0
    curr_belief = belief
    asked_probe_ids: list[str] = []
    action: Action | None = None

    for step in range(depth_budget + 1):
        action = policy_fn(
            belief=curr_belief,
            probes=probes,
            weekly_interruptions_used=interruptions_spent,
            episode_questions_asked=step,
            already_asked_probe_ids=asked_probe_ids,
            cost_per_interrupt=probe_cost_weight,
        )

        if action.kind == ActionKind.ASK:
            interruptions_spent += 1
            if action.question and action.question.probe:
                p_id = action.question.probe.probe_id
                asked_probe_ids.append(p_id)
                oracle.query(p_id)
        else:
            return action, interruptions_spent

    return action or Action(kind=ActionKind.OBSERVE), interruptions_spent


def _detections_for(amplitude_bpm: float, duration_days: int) -> list[Detection]:
    """Detections for one simulated case."""
    level = (
        DetectionLevel.RED
        if amplitude_bpm >= 4.0
        else DetectionLevel.YELLOW
        if amplitude_bpm >= 3.0
        else DetectionLevel.GREEN
    )
    return [
        Detection(
            subject_id="eval",
            night_date=_EVAL_START + timedelta(days=i),
            residual_bpm=amplitude_bpm,
            level=level,
            flagged=False,
            forecast=Forecast(status=ForecastStatus.NOT_RUN),
        )
        for i in range(duration_days)
    ]


def _truth_is_illness(oracle_answers: dict[str, str]) -> bool:
    """Ground truth for a simulated case: the person reports infection-like symptoms."""
    return oracle_answers.get("probe_symptoms") in {"fever", "throat", "aches"}


def _score_policy(
    policy_fn: Any,
    belief: BeliefState,
    detections: list[Detection],
    oracle_answers: dict[str, str],
    cost_weight: float,
) -> tuple[bool, int]:
    """Run one policy on one simulated case.

    Returns whether it decided correctly and how many times it interrupted. The decision
    is read from the belief the policy would hold given whatever it chose to ask, which
    is the point of the comparison: a policy that asks nothing must decide on sensors
    alone.
    """
    from wha.belief import update_belief

    oracle = PolicyOracleHarness(oracle_answers)
    _action, interruptions = evaluate_policy_on_oracle(
        policy_fn,
        belief,
        detections,
        oracle,
        probe_cost_weight=cost_weight,
    )

    answers = [Answer(probe_id=pid, option_id=opt) for pid, opt in oracle.revealed_answers.items()]
    final = update_belief(episode_nights=detections, answers=answers)
    said_illness = final.p_illness >= DERIVED_TREATMENT_THRESHOLD
    return said_illness == _truth_is_illness(oracle_answers), interruptions


def _simulated_cases() -> list[tuple[float, int, dict[str, str]]]:
    """Amplitude, duration and hidden self-report for each simulated case.

    Half the cases are genuine infections and half are benign mimics presenting with the
    same elevation. That is the discrimination the policy exists to make, and the reason
    asking can beat any sensor-only rule.
    """
    cases: list[tuple[float, int, dict[str, str]]] = []
    for amp in INJECTION_AMPLITUDES:
        for dur in INJECTION_DURATIONS:
            cases.append((amp, dur, {"probe_symptoms": "fever", "probe_stress": "none"}))
            cases.append((amp, dur, {"probe_symptoms": "none", "probe_stress": "lots"}))
    return cases


def run_policy_eval(
    labels: dict[str, Any] | None = None,
    eval_dir: Path | None = None,
) -> EvaluationResult:
    """Benchmark the EVSI policy against four comparators on simulated cases."""
    from wha.belief import update_belief
    from wha.policy.baselines import (
        policy_always_ask,
        policy_never_ask,
        policy_random,
        policy_threshold,
    )
    from wha.policy.select import select_action

    target_eval_dir = eval_dir if eval_dir is not None else Path("data/eval")
    target_eval_dir.mkdir(parents=True, exist_ok=True)

    policies: dict[str, Any] = {
        "evsi": select_action,
        "threshold": policy_threshold,
        "never_ask": policy_never_ask,
        "always_ask": policy_always_ask,
        "random": policy_random,
    }

    cases = _simulated_cases()
    detections_by_case = {(amp, dur): _detections_for(amp, dur) for amp, dur, _ in cases}
    beliefs_by_case = {
        key: update_belief(episode_nights=dets) for key, dets in detections_by_case.items()
    }

    heatmap_rows: list[dict[str, Any]] = []
    correct_by_policy: dict[str, list[bool]] = {name: [] for name in policies}
    interruptions_by_policy: dict[str, list[int]] = {name: [] for name in policies}

    for amp, dur, answers in cases:
        belief = beliefs_by_case[(amp, dur)]
        detections = detections_by_case[(amp, dur)]
        row: dict[str, Any] = {
            "amplitude_bpm": amp,
            "duration_days": dur,
            "truth": "illness" if _truth_is_illness(answers) else "benign",
        }
        for name, fn in policies.items():
            correct, interruptions = _score_policy(
                fn, belief, detections, answers, POLICY_COST_PER_INTERRUPT
            )
            correct_by_policy[name].append(correct)
            interruptions_by_policy[name].append(interruptions)
            row[f"{name}_correct"] = correct
        heatmap_rows.append(row)

    # How the EVSI policy trades interruptions against accuracy as the cost weight moves.
    frontier_rows: list[dict[str, Any]] = []
    for cost_w in COST_WEIGHT_SWEEP:
        correct: list[bool] = []
        interruptions: list[int] = []
        for amp, dur, answers in cases:
            ok, n = _score_policy(
                select_action,
                beliefs_by_case[(amp, dur)],
                detections_by_case[(amp, dur)],
                answers,
                cost_w,
            )
            correct.append(ok)
            interruptions.append(n)
        frontier_rows.append(
            {
                "interruption_cost_weight": cost_w,
                "evsi_accuracy": round(sum(correct) / len(correct), 4),
                "evsi_interruptions": round(sum(interruptions) / len(interruptions), 4),
            }
        )

    metrics: dict[str, float] = {}
    for name in policies:
        n = len(correct_by_policy[name]) or 1
        metrics[f"{name}_mean_accuracy"] = round(sum(correct_by_policy[name]) / n, 4)
        metrics[f"{name}_mean_interruptions"] = round(sum(interruptions_by_policy[name]) / n, 4)

    result = EvaluationResult(
        suite="policy",
        generated_at_utc=now_utc(),
        metrics=metrics,
        tables={
            "injection_heatmap": heatmap_rows,
            "accuracy_interruption_frontier": frontier_rows,
        },
        figures=[],
        sample_size=len(cases),
        caveats=[
            (
                "Simulated cases, not a clinical cohort. Ground truth is the injected label, "
                "so this measures whether a policy recovers a cause it was given, not whether "
                "the cause model itself is correct."
            ),
            (
                "The oracle answers every question truthfully and at once. Adherence, recall "
                "error and non-response are not modelled, so the interruption counts are a "
                "lower bound on what a person would actually experience."
            ),
            (
                "Half the cases are infections and half are benign mimics by construction. "
                "The real prevalence of infection among flagged nights is far lower, so "
                "accuracy here is not a deployment estimate."
            ),
        ],
    )

    out_file = target_eval_dir / "policy.json"
    out_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result
