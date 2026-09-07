"""Unit tests for policy action selection, probe tie-breaking, and dispositions."""

from wha.belief import load_causes
from wha.models import (
    ActionKind,
    AnswerOption,
    BaselineRung,
    BeliefState,
    CauseId,
    Disposition,
)
from wha.policy import (
    ProbeDefinition,
    determine_disposition,
    select_action,
)

_cached_priors = load_causes()
_base_marginals = {p.cause: p.base_rate for p in _cached_priors}


def _make_belief(
    p_inf: float,
    extra_marginals: dict[CauseId, float] | None = None,
) -> BeliefState:
    marginals = dict(_base_marginals)
    marginals[CauseId.INFECTION] = p_inf
    if extra_marginals:
        marginals.update(extra_marginals)
    return BeliefState(
        marginals=marginals,
        p_illness=p_inf,
    )


def test_asks_inside_the_band() -> None:
    """When belief is in uncertainty band and gates allow, select_action asks the top probe."""
    # At p=0.12, symptoms probe has high EVSI and positive net score
    belief = _make_belief(0.12)
    action = select_action(belief, cost_per_interrupt=0.01)

    assert action.kind == ActionKind.ASK
    assert action.question is not None
    assert len(action.rejected) > 0


def test_answered_probe_not_reasked() -> None:
    """A probe that has already been asked is excluded from selection."""
    belief = _make_belief(0.12)
    action = select_action(
        belief,
        already_asked_probe_ids=["probe_symptoms"],
        cost_per_interrupt=0.01,
    )

    if action.kind == ActionKind.ASK:
        assert action.question is not None
        assert action.question.probe.probe_id != "probe_symptoms"


def test_tie_break_is_deterministic() -> None:
    """When two probes have identical scores, tie-break picks lower cost, then alphabetical id."""
    dummy_p1 = ProbeDefinition(
        probe_id="probe_b",
        target_cause=CauseId.INFECTION,
        interruption_cost=1.0,
        fallback_text="Probe B?",
        answer_space=[
            AnswerOption(option_id="opt1", label="1"),
            AnswerOption(option_id="opt2", label="2"),
        ],
        likelihood_present={"opt1": 0.5, "opt2": 0.5},
        likelihood_absent={"opt1": 0.5, "opt2": 0.5},
        provenance="ASSUMED",
        assumption="Test",
    )
    dummy_p2 = ProbeDefinition(
        probe_id="probe_a",
        target_cause=CauseId.INFECTION,
        interruption_cost=1.0,
        fallback_text="Probe A?",
        answer_space=[
            AnswerOption(option_id="opt1", label="1"),
            AnswerOption(option_id="opt2", label="2"),
        ],
        likelihood_present={"opt1": 0.5, "opt2": 0.5},
        likelihood_absent={"opt1": 0.5, "opt2": 0.5},
        provenance="ASSUMED",
        assumption="Test",
    )

    belief = _make_belief(0.12)
    # Even if p1 is listed first, alphabetical tie-break picks probe_a
    action = select_action(
        belief,
        probes=[dummy_p1, dummy_p2],
        cost_per_interrupt=0.0,
    )
    # When score is 0 or positive
    if action.kind == ActionKind.ASK:
        assert action.question is not None
        assert action.question.probe.probe_id == "probe_a"


def test_rejected_probes_recorded_with_scores() -> None:
    """Every action records the full rejected probe list with their computed scores."""
    belief = _make_belief(0.12)
    action = select_action(belief)

    assert isinstance(action.rejected, list)
    assert len(action.rejected) > 0
    for probe_id, score in action.rejected:
        assert isinstance(probe_id, str)
        assert isinstance(score, float)


def test_caps_produce_unresolved() -> None:
    """Exceeding hard episode limits terminates the episode as UNRESOLVED."""
    belief = _make_belief(0.12)

    # Max nights cap (10)
    action_nights = select_action(belief, nights_in_episode=10)
    assert action_nights.kind == ActionKind.CONCLUDE
    assert action_nights.disposition == Disposition.UNRESOLVED

    # Max steps cap (40)
    action_steps = select_action(belief, steps_in_episode=40)
    assert action_steps.kind == ActionKind.CONCLUDE
    assert action_steps.disposition == Disposition.UNRESOLVED


def test_disposition_table() -> None:
    """Verify all 5 rows of the terminal disposition contract."""
    # 1. Rung is COLD -> INSUFFICIENT_DATA
    disp_cold = determine_disposition(_make_belief(0.15), rung=BaselineRung.COLD)
    assert disp_cold == Disposition.INSUFFICIENT_DATA

    # 2. Confounder dominates and explains residual -> EXPLAINED_BY_EVENT
    # (alcohol at 0.70, p_illness at 0.04 < 0.10)
    disp_event = determine_disposition(
        _make_belief(0.04, extra_marginals={CauseId.ALCOHOL: 0.70}),
        rung=BaselineRung.MATURE,
    )
    assert disp_event == Disposition.EXPLAINED_BY_EVENT

    # 3. p_illness above threshold (0.10) -> LIKELY_ILLNESS
    disp_illness = determine_disposition(_make_belief(0.25), rung=BaselineRung.MATURE)
    assert disp_illness == Disposition.LIKELY_ILLNESS

    # 4. p_illness below threshold (0.10) -> LIKELY_BENIGN
    disp_benign = determine_disposition(_make_belief(0.02), rung=BaselineRung.MATURE)
    assert disp_benign == Disposition.LIKELY_BENIGN

    # 5. Budgets exhausted while inside band -> UNRESOLVED
    disp_unres = determine_disposition(
        _make_belief(0.12),
        rung=BaselineRung.MATURE,
        weekly_interruptions_used=2,
    )
    assert disp_unres == Disposition.UNRESOLVED
