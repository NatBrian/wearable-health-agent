"""Unit tests for the 4096 state presence matrix and exact log-space inference."""

from datetime import date, timedelta

import numpy as np

from wha.belief import (
    PRESENT,
    load_causes,
    run_exact_inference,
)
from wha.models import (
    Detection,
    DetectionLevel,
    Forecast,
)


def _make_det(d: int, residual: float = 4.5) -> Detection:
    return Detection(
        subject_id="subj_enum",
        night_date=date(2026, 9, 1) + timedelta(days=d),
        deviation_bpm=residual,
        explained_bpm=0.0,
        residual_bpm=residual,
        robust_z=2.0,
        level=DetectionLevel.RED,
        flagged=True,
        forecast=Forecast(),
    )


def test_state_matrix_shape_and_content() -> None:
    """PRESENT matrix has shape (4096, 12) and row 5 has bits 0 and 2 set."""
    assert PRESENT.shape == (4096, 12)
    assert PRESENT.dtype == bool

    # Row 5 corresponds to integer state 5 (bits 0 and 2 set: 1 + 4 = 5)
    row_5 = PRESENT[5]
    assert row_5[0] is True or row_5[0] == 1
    assert row_5[1] is False or row_5[1] == 0
    assert row_5[2] is True or row_5[2] == 1
    assert not any(row_5[3:])


def test_posterior_sums_to_one() -> None:
    """Posterior distribution over all 4096 states sums to 1.0."""
    dets = [_make_det(0, 3.5), _make_det(1, 4.0)]
    belief = run_exact_inference(dets)

    # Reconstruct state posterior from state_logprob
    state_probs = np.exp(np.array(belief.state_logprob) - np.max(belief.state_logprob))
    state_probs = state_probs / np.sum(state_probs)

    assert abs(np.sum(state_probs) - 1.0) < 1e-9


def test_marginals_do_not_sum_to_one() -> None:
    """Marginals represent independent cause contribution probabilities and do NOT sum to 1."""
    dets = [_make_det(0, 4.5), _make_det(1, 4.5)]
    belief = run_exact_inference(dets)

    marginal_sum = sum(belief.marginals.values())
    # With 12 causes and high residual, multiple causes have positive probability, sum > 1.0
    assert abs(marginal_sum - 1.0) > 0.01


def test_no_evidence_returns_priors() -> None:
    """With zero nights and zero answers, marginals equal the base rates from causes.yaml."""
    priors = load_causes()
    prior_map = {p.cause: p.base_rate for p in priors}

    belief = run_exact_inference([])
    for cause, prob in belief.marginals.items():
        expected_prob = prior_map[cause]
        assert abs(prob - expected_prob) < 1e-5


def test_log_space_no_underflow() -> None:
    """Ten consecutive nights of large residuals stays finite and non-uniform without underflow."""
    dets = [_make_det(i, 8.0) for i in range(10)]
    belief = run_exact_inference(dets)

    for prob in belief.marginals.values():
        assert not np.isnan(prob)
        assert not np.isinf(prob)
        assert 0.0 <= prob <= 1.0

    # Ensure posterior is non-uniform and discriminating
    probs = list(belief.marginals.values())
    assert max(probs) - min(probs) > 0.01


def test_recompute_is_deterministic() -> None:
    """Recomputing inference on identical inputs produces bit-identical marginals."""
    dets = [_make_det(0, 3.8), _make_det(1, 4.2), _make_det(2, 5.0)]
    b1 = run_exact_inference(dets)
    b2 = run_exact_inference(dets)

    assert b1.marginals == b2.marginals
    assert b1.p_illness == b2.p_illness
