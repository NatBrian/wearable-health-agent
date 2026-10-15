"""The corpus the agent retrieves from, and the wiring that lets it reach the corpus."""

from wha.constants import (
    BASELINE_MIN_NIGHTS_PERSONAL,
    DETECT_RED_BPM,
    DETECT_YELLOW_BPM,
    POP_PRIOR_RHR_MEAN_BPM,
)
from wha.retrieve.knowledge_docs import (
    build_default_corpus,
    build_index,
    generate_layer_2_method_docs,
    generate_layer_3_escalation_docs,
    generate_probe_evidence_docs,
)


def test_corpus_covers_every_cause_probe_and_urgent_sign() -> None:
    """Anything the agent can conclude about must be something it can cite a source for."""
    from wha.belief.causes import load_causes

    docs = {d.doc_id for d in build_default_corpus()}

    for cause in load_causes():
        assert f"confounder_{cause.cause.value}" in docs

    # probe_cycle was here and is retired: the fact it asked for is a standing one and is
    # collected once in Settings, so it costs no interruption at all. probe_medication
    # replaces it as the third case, being the only remaining one-time probe.
    for probe_id in ("probe_symptoms", "probe_alcohol", "probe_medication"):
        assert f"evidence_{probe_id}" in docs

    # And it is genuinely gone, rather than merely unlisted above.
    assert "evidence_probe_cycle" not in docs

    for rule_id in ("rf_chest_pain", "rf_breathless_at_rest", "rf_syncope"):
        assert f"escalation_{rule_id}" in docs


def test_method_passages_carry_the_constants_they_describe() -> None:
    """A passage that quotes a threshold must quote the one the detector actually uses.

    The numbers are interpolated from constants.py rather than retyped, so this asserts
    the wiring rather than the arithmetic. A passage saying 3 bpm while the detector used
    4 would be a citation that misleads about the system's own behaviour.
    """
    text = "\n".join(d.text for d in generate_layer_2_method_docs())

    assert f"{DETECT_YELLOW_BPM:.0f} bpm" in text
    assert f"{DETECT_RED_BPM:.0f} bpm" in text
    assert str(BASELINE_MIN_NIGHTS_PERSONAL) in text
    assert str(POP_PRIOR_RHR_MEAN_BPM) in text


def test_escalation_passages_carry_the_guidance_a_human_wrote() -> None:
    """Care advice is quoted from red_flags.yaml, never composed."""
    import yaml

    from wha.retrieve.knowledge_docs import RED_FLAGS_PATH

    rules = yaml.safe_load(RED_FLAGS_PATH.read_text(encoding="utf-8"))["tier_a"]
    docs = {d.doc_id: d.text for d in generate_layer_3_escalation_docs()}

    for rule in rules:
        assert rule["guidance"].strip() in docs[f"escalation_{rule['id']}"]


def test_probe_passages_say_their_numbers_are_assumed() -> None:
    """Every likelihood in probes.yaml is ASSUMED, and a citable passage must say so.

    A retrieved passage carrying a bare number reads as measured. These are not measured,
    and the disclosure rule for this project requires an unevidenced figure to be labelled
    wherever it is shown.
    """
    for doc in generate_probe_evidence_docs():
        assert "not measured" in doc.text
        assert "ASSUMED" in doc.text


def test_the_index_finds_the_right_passage_for_a_symptom_and_for_a_red_flag() -> None:
    """Retrieval is only useful if the passage it returns is the relevant one."""
    index = build_index()

    # Probe evidence contains assumed internal likelihoods. It stays findable through its
    # own question and fixed answer labels, but semantic similarity alone must not surface
    # it for a general symptom report. This remains true when the optional MedlinePlus
    # snapshot is absent and there are no consumer-health passages to outrank it.
    assert any("probe_symptoms" in r.chunk_id for r in index.query("How are you feeling?", top_k=3))
    assert any("probe_symptoms" in r.chunk_id for r in index.query("feverish or chills", top_k=3))

    # And a symptom query returns health information, not the system's own internals.
    for query in ("I have a fever and chills", "No fever", "yes, I feel unwell"):
        results = index.query(query, top_k=6)
        assert not any("probe_" in r.chunk_id for r in results), [
            query,
            [r.chunk_id for r in results],
        ]

    # The conversation compacts a natural-language message before retrieval. This is
    # especially important on the supported BM25-only fallback, where filler words in
    # "I feel a bit fever today, what should I do" displaced the actual topic page.
    from wha.agent.conversation import _retrieval_query_for_turn

    fever_query = _retrieval_query_for_turn(
        "I feel a bit fever today, what should I do?", prior_turns=[]
    )
    assert fever_query == "fever"
    fever_results = index.query(fever_query, top_k=6)
    assert any(r.title == "Fever" for r in fever_results), [r.title for r in fever_results]

    # Present in the results, not necessarily first.
    #
    # This asserted rank 1 until the MedlinePlus layer was added, at which point "chest
    # pain" reasonably returns the MedlinePlus chest pain topic first and our escalation
    # rule second. Demanding rank 1 would mean the corpus could never grow a consumer
    # health layer at all, which is the thing it most needed. The property that matters,
    # that the authored safety rules stay findable among a thousand fetched topics, is
    # asserted directly in test_medlineplus.py.
    chest = index.query("chest pain", top_k=6)
    assert any(r.chunk_id.startswith("escalation_rf_chest_pain") for r in chest)


def test_the_repository_supplies_an_index_to_the_retrieval_tool() -> None:
    """EpisodeRepository.retrieval_index was set to None and assigned by nothing.

    The tool reads it through getattr, so retrieve_clinical_evidence ran without error and
    could never return a passage. It was called zero times in 145 tool calls in the last
    production simulation, and citations were empty for the same reason.
    """
    from wha.agent.repository import EpisodeRepository
    from wha.agent.tools.impl import tool_retrieve_clinical_evidence
    from wha.agent.tools.registry import ToolContext

    db = EpisodeRepository()
    context = ToolContext(subject_id="sub_001", episode_id="ep_001", step_index=0)

    result = tool_retrieve_clinical_evidence({"query": "chest pain"}, context, db=db)

    assert result.ok
    assert result.value, "the retrieval tool returned no passages"
    assert result.freshness == "fresh"
    assert result.source_ids != ["local_corpus"]


def test_no_layer_three_passage_reads_like_a_configuration_file() -> None:
    """Item 31's own check, applied to every generated passage rather than to three of them.

    Two survived the original pass. The tier B bullets read "People describe this as people
    describe this as fever, feverish, ...", because `_describe_phrases` returns the whole
    sentence and the caller prepended the same words again. And the vitals document used
    the raw rule id as a section heading: "## rf_rhr_extreme_high", shown to a lay reader as
    clinical evidence, which is the plainest possible failure of "reads like health
    information, not a configuration file".

    The ids stay in metadata, which is where the audit trail reads them.
    """
    from wha.retrieve.knowledge_docs import generate_layer_3_escalation_docs

    docs = generate_layer_3_escalation_docs()
    assert docs, "no layer 3 documents generated"

    for doc in docs:
        lowered = doc.text.lower()
        assert "rf_" not in lowered, f"{doc.doc_id} prints a rule id: {doc.text[:120]}"
        assert "people describe this as people describe" not in lowered, (
            f"{doc.doc_id} doubles the phrase-list opener"
        )
        assert "any of:" not in lowered, f"{doc.doc_id} still prints a raw match list"
        assert "tier_b:" not in lowered and "tier_a:" not in lowered, doc.doc_id
        assert doc.title and not doc.title.startswith("rf_"), (
            f"{doc.doc_id} has an identifier as its title: {doc.title!r}"
        )

    # And the id really is still reachable for the audit trail.
    assert any(d.metadata.get("rule_id") for d in docs), (
        "no document carries its rule id in metadata, so the audit trail cannot link back"
    )
