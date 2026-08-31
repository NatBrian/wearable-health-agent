"""Unit tests for ablation evaluation suite."""

from pathlib import Path

from wha.eval.ablation import (
    paired_bootstrap_difference,
    run_ablation_eval,
)


def test_each_ablation_toggles_one_thing(tmp_path: Path) -> None:
    """The ablation suite includes all six distinct component ablations."""
    res = run_ablation_eval(eval_dir=tmp_path)
    assert res.suite == "ablation"
    assert "ablation_table" in res.tables
    table = res.tables["ablation_table"]
    assert len(table) == 6
    tested_components = {row["component_removed"] for row in table}
    expected_components = {
        "explained_variance",
        "persistence_rule",
        "chronos_evidence",
        "temporal_profiles",
        "shrinkage_ladder",
        "policy_asking",
    }
    assert tested_components == expected_components


def test_paired_bootstrap_over_participants() -> None:
    """Paired bootstrap operates across participant clusters to compute confidence interval on score difference."""
    # 20 participants
    p_keys = [f"p_{i}" for i in range(20)]
    baseline = {p: 0.8 for p in p_keys}
    # Ablated condition is strictly 0.1 lower
    ablated = {p: 0.7 for p in p_keys}

    mean_diff, ci_low, ci_high = paired_bootstrap_difference(
        baseline_scores=baseline,
        ablated_scores=ablated,
        n_resamples=200,
        seed=42,
    )

    assert abs(mean_diff - (-0.1)) < 1e-3
    assert ci_low <= mean_diff <= ci_high
    assert abs(ci_low - (-0.1)) < 1e-2
    assert abs(ci_high - (-0.1)) < 1e-2


def test_caveats_non_empty_when_underpowered(tmp_path: Path) -> None:
    """Ablation EvaluationResult populates explicit caveats describing statistical power."""
    res = run_ablation_eval(eval_dir=tmp_path)
    assert len(res.caveats) > 0
    assert any("N=" in c for c in res.caveats)
