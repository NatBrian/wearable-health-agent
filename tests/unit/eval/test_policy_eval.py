"""Unit tests for policy evaluation suite on hidden self-report oracle."""

from datetime import date
from pathlib import Path

from wha.eval.policy_oracle import (
    PolicyOracleHarness,
    evaluate_policy_on_oracle,
    run_policy_eval,
)
from wha.models import (
    ActionKind,
    BeliefState,
    CauseId,
    Detection,
    DetectionLevel,
    Forecast,
    ForecastStatus,
)
from wha.policy.baselines import (
    policy_always_ask,
    policy_never_ask,
    policy_threshold,
)
from wha.policy.select import select_action


def _make_det() -> Detection:
    d = date(2026, 8, 15)
    return Detection(
        subject_id="p01",
        night_date=d,
        level=DetectionLevel.RED,
        deviation_bpm=5.0,
        residual_bpm=5.0,
        flagged=True,
        forecast=Forecast(status=ForecastStatus.OK),
    )


def _make_belief(p_illness: float = 0.6) -> BeliefState:
    all_causes = list(CauseId)
    marginals = {c: 0.1 for c in all_causes}
    marginals[CauseId.INFECTION] = p_illness
    return BeliefState(
        marginals=marginals,
        p_illness=p_illness,
        state_logprob=[-1.0] * 4096,
    )


def test_oracle_only_reveals_on_ask() -> None:
    """Never-ask policy sees zero self-reports and oracle is never queried."""
    oracle = PolicyOracleHarness(
        ground_truth_answers={
            "probe_alcohol": "yes",
            "probe_workout": "late_evening",
        }
    )
    belief = _make_belief(p_illness=0.6)
    dets = [_make_det()]

    action, spent = evaluate_policy_on_oracle(
        policy_fn=policy_never_ask,
        belief=belief,
        detections=dets,
        oracle=oracle,
    )

    assert spent == 0
    assert oracle.query_count == 0
    assert len(oracle.revealed_answers) == 0
    assert action.kind != ActionKind.ASK


def test_four_policies_run_on_same_fixture() -> None:
    """All four policies execute on identical belief fixture and produce expected action patterns."""
    oracle_answers = {"probe_alcohol": "yes", "probe_workout": "none"}
    belief = _make_belief(p_illness=0.5)
    dets = [_make_det()]

    results = {}
    for name, fn in [
        ("never_ask", policy_never_ask),
        ("always_ask", policy_always_ask),
        ("threshold", policy_threshold),
        ("evsi", select_action),
    ]:
        oracle = PolicyOracleHarness(ground_truth_answers=oracle_answers)
        action, spent = evaluate_policy_on_oracle(
            policy_fn=fn,
            belief=belief,
            detections=dets,
            oracle=oracle,
            depth_budget=2,
        )
        results[name] = (action, spent)

    # never_ask must spend 0 interruptions
    assert results["never_ask"][1] == 0
    # always_ask must spend at least 1 interruption
    assert results["always_ask"][1] >= 1


def test_injection_sweep_produces_heatmap(tmp_path: Path) -> None:
    """Policy evaluation suite generates injection sweep heatmap over amplitude and duration."""
    res = run_policy_eval(eval_dir=tmp_path)
    assert res.suite == "policy"
    assert "injection_heatmap" in res.tables
    heatmap = res.tables["injection_heatmap"]
    # 5 amplitudes x 4 durations x 2 ground truths = 40 cells. Each elevation is presented
    # twice, once as a real infection and once as a benign mimic producing an identical
    # residual. Without the mimic, accuracy is unmeasurable: a policy that always answers
    # "illness" would score perfectly.
    assert len(heatmap) == 40
    assert {c["truth"] for c in heatmap} == {"illness", "benign"}
    for cell in heatmap:
        assert "amplitude_bpm" in cell
        assert "duration_days" in cell
        # Per-case correctness, measured by running the policy, not a formula.
        assert isinstance(cell["evsi_correct"], bool)
        assert isinstance(cell["threshold_correct"], bool)

    # The comparators must actually differ, or the benchmark is not measuring anything.
    assert res.metrics["always_ask_mean_interruptions"] > res.metrics["evsi_mean_interruptions"]
    assert res.metrics["never_ask_mean_interruptions"] == 0.0


def test_result_records_provenance(tmp_path: Path) -> None:
    """EvaluationResult contains suite name, metrics, timestamps, and caveats."""
    res = run_policy_eval(eval_dir=tmp_path)
    assert res.suite == "policy"
    assert res.generated_at_utc is not None
    assert "accuracy_interruption_frontier" in res.tables
    assert len(res.caveats) > 0
    assert res.sample_size > 0
