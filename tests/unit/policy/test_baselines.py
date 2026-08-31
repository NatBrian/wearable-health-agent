"""Unit tests for the four comparator baseline policies."""

from wha.belief import load_causes
from wha.models import (
    ActionKind,
    BaselineRung,
    BeliefState,
    CauseId,
)
from wha.policy import (
    policy_always_ask,
    policy_never_ask,
    policy_random,
    policy_threshold,
    select_action,
)

_cached_priors = load_causes()
_base_marginals = {p.cause: p.base_rate for p in _cached_priors}


def _make_belief(p_inf: float) -> BeliefState:
    marginals = dict(_base_marginals)
    marginals[CauseId.INFECTION] = p_inf
    return BeliefState(
        marginals=marginals,
        p_illness=p_inf,
    )


def test_four_baselines_share_the_interface() -> None:
    """All 4 baselines and select_action share the same signature and return an Action."""
    belief = _make_belief(0.15)
    baselines = [
        policy_never_ask,
        policy_always_ask,
        policy_threshold,
        policy_random,
        select_action,
    ]
    for fn in baselines:
        act = fn(
            belief=belief,
            weekly_interruptions_used=0,
            episode_questions_asked=0,
            rung=BaselineRung.MATURE,
            nights_in_episode=1,
        )
        assert hasattr(act, "kind")
        assert hasattr(act, "rejected")
        assert act.kind in {ActionKind.ASK, ActionKind.OBSERVE, ActionKind.CONCLUDE}


def test_never_ask_never_asks() -> None:
    """Never-ask baseline never produces an ASK action across any belief state."""
    for p in [0.01, 0.05, 0.12, 0.25, 0.50, 0.90]:
        act = policy_never_ask(_make_belief(p))
        assert act.kind != ActionKind.ASK


def test_always_ask_asks_more_than_policy() -> None:
    """Always-ask requests a probe even when EVSI net value is negligible/negative for standard policy."""
    # At p=0.01, EVSI is 0 so standard policy will NOT ask, but always_ask will ask whenever unasked probe exists
    belief = _make_belief(0.01)
    act_real = select_action(belief, cost_per_interrupt=0.30)
    act_always = policy_always_ask(belief)

    assert act_real.kind != ActionKind.ASK
    assert act_always.kind == ActionKind.ASK


def test_threshold_policy_ignores_evsi() -> None:
    """Threshold policy asks strictly based on p_illness in [0.10, 0.75] regardless of EVSI."""
    belief_inside = _make_belief(0.50)
    act_inside = policy_threshold(belief_inside)
    assert act_inside.kind == ActionKind.ASK

    belief_outside = _make_belief(0.05)
    act_outside = policy_threshold(belief_outside)
    assert act_outside.kind != ActionKind.ASK
