"""The night pipeline: every step of the journey, for every night, or an honest gap."""

from wha.models import (
    CANONICAL_PIPELINE_STEPS,
    PipelineStepView,
    StepLayer,
    StepStatus,
)


def test_the_canonical_steps_are_ordered_and_unique() -> None:
    """The order on screen is the order the system ran, and no id appears twice."""
    ordinals = [s.ordinal for s in CANONICAL_PIPELINE_STEPS]
    ids = [s.step_id for s in CANONICAL_PIPELINE_STEPS]
    assert ordinals == sorted(ordinals)
    assert len(set(ids)) == len(ids)


def test_the_agentic_ids_match_the_stage_names_the_agent_already_uses() -> None:
    """Two vocabularies for one pipeline is how a screen comes to contradict the record.

    The agent's own stage names are the ones written into `episode_traces`. If the screen
    invented a second set, a step could be drawn as skipped while the record it was built
    from said it ran.
    """
    from wha.service.episodes import CANONICAL_STAGES

    step_ids = {s.step_id for s in CANONICAL_PIPELINE_STEPS}
    for name, _description in CANONICAL_STAGES:
        assert name in step_ids, f"agent stage {name} has no pipeline step"


def test_a_step_view_needs_nothing_it_cannot_know() -> None:
    """A step with no recorded time and no headline figure is a legal step.

    Making either mandatory would force a caller to invent one, which is the failure this
    whole module exists to avoid.
    """
    step = PipelineStepView(
        step_id="detect",
        ordinal=7,
        layer=StepLayer.DETERMINISTIC,
        status=StepStatus.RAN,
        reason="Compared the reading against your own band.",
    )
    assert step.occurred_utc is None
    assert step.headline_figure is None
