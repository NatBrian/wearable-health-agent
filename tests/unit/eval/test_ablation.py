"""Unit tests for ablation evaluation suite."""

import pytest

from wha.eval.ablation import (
    paired_bootstrap_difference,
    run_ablation_eval,
)


def test_the_ablation_suite_refuses_rather_than_inventing_effect_sizes() -> None:
    """This asserted six rows from an experiment that was never run.

    Measured before changing it: the suite's participants were `p_01` to `p_32`, made up.
    Their baseline scores were `random.Random(42).uniform(0.75, 0.95)`. The effect of
    removing each component was a hardcoded dict, so `wha eval ablation` printed
    "diff_persistence_rule: -0.1182" with a paired bootstrap interval around a constant,
    and went on reporting a contribution for the Chronos forecast three days after the
    forecast was deleted from the codebase.

    This is the identical defect `run_policy_eval` had, which STATUS records as one of the
    original catastrophic findings: hardcoded accuracy constants no policy had produced.
    That one was fixed by running the real policies through the real belief model. This one
    is disabled until somebody writes the real experiment, because a suite that reports
    invented effect sizes is worse than no suite: a reader cannot tell.

    The old expectation is not weakened here, it is inverted, because the behaviour it
    asserted should never have existed.
    """
    from wha.errors import ConfigError

    with pytest.raises(ConfigError) as excinfo:
        run_ablation_eval()

    message = str(excinfo.value)
    assert "No ablation has ever been run" in message
    assert "random.Random(42)" in message, "the message must say why, not just refuse"
    assert "wha eval policy" in message, "it must point at the measurements that are real"


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


def test_the_paired_bootstrap_itself_is_kept_and_still_correct() -> None:
    """The statistics were never the problem; the data fed to them was.

    `paired_bootstrap_difference` is a real implementation over participant clusters and is
    exercised on known inputs by the test above. It stays, so whoever writes the real
    ablation has it. What was removed is the fabricated input: 32 invented participants,
    scores from a seeded uniform, and a hardcoded dict of effect sizes reported as
    measurements.
    """
    from wha.errors import ConfigError
    from wha.eval import ablation

    assert callable(ablation.paired_bootstrap_difference)

    # The property is that the suite cannot return a result at all. Anything narrower is a
    # search for a string, and those strings appear legitimately in the docstring and the
    # refusal message that explain what was removed.
    with pytest.raises(ConfigError):
        ablation.run_ablation_eval()
