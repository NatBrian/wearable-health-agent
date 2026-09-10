"""The Record tab highlights where a result came from. The edges are declared in one
place and must describe steps that exist, in an order that is possible."""

from wha.models import CANONICAL_PIPELINE_STEPS, PIPELINE_LINEAGE

ORDINAL = {s.step_id: s.ordinal for s in CANONICAL_PIPELINE_STEPS}


def test_every_edge_names_real_steps() -> None:
    for edge in PIPELINE_LINEAGE:
        assert edge.from_step in ORDINAL, edge
        assert edge.to_step in ORDINAL, edge


def test_no_edge_runs_backwards_except_the_answer_loop() -> None:
    """Data flows forward through the numbered steps. The one declared exception is an
    answer (step 15) feeding investigate (step 11), which is the hypothesis loop."""
    allowed_backward = {("answer", "investigate"), ("answer", "believe")}
    for edge in PIPELINE_LINEAGE:
        if (edge.from_step, edge.to_step) in allowed_backward:
            continue
        assert ORDINAL[edge.from_step] < ORDINAL[edge.to_step], edge


def test_every_step_after_the_first_consumes_something() -> None:
    consumers = {e.to_step for e in PIPELINE_LINEAGE}
    orphans = [s.step_id for s in CANONICAL_PIPELINE_STEPS if s.ordinal > 1 and s.step_id not in consumers]
    assert not orphans, f"steps with no declared input: {orphans}"


def test_edges_are_unique() -> None:
    seen = [(e.from_step, e.output, e.to_step) for e in PIPELINE_LINEAGE]
    assert len(seen) == len(set(seen))


def test_every_output_named_is_one_the_pipeline_writes() -> None:
    """Read from the source rather than a fixture: the keys appear as string literals
    in the outputs= dicts of service/pipeline.py."""
    from pathlib import Path

    source = Path("src/wha/service/pipeline.py").read_text(encoding="utf-8")
    missing = [e for e in PIPELINE_LINEAGE if f'"{e.output}"' not in source]
    assert not missing, f"lineage names outputs the pipeline never writes: {missing}"
