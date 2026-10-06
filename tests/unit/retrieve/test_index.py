"""Unit tests for HybridIndex: BM25, dense search, RRF fusion, filters, and deduplication."""

from pathlib import Path

import numpy as np

from wha.retrieve import (
    Chunk,
    HybridIndex,
    chunk_document,
    load_corpus_from_directory,
)

FIXTURE_CORPUS_DIR = Path("tests/fixtures/corpus")


class StubDeterministicEmbedder:
    """Deterministic offline embedder without network access or model downloads."""

    def __init__(self, dim: int = 64) -> None:
        self.dim = dim

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dim), dtype=np.float32)

        vecs = []
        for text in texts:
            vec = np.zeros(self.dim, dtype=np.float32)
            lower = text.lower()
            if "pharyngitis" in lower or "sore throat" in lower or "centor" in lower:
                vec[0] += 5.0
            if "dengue" in lower or "platelet" in lower or "defervescence" in lower:
                vec[1] += 5.0
            if "fever" in lower or "temperature" in lower or "chills" in lower:
                vec[2] += 5.0
            if "alcohol" in lower or "drinking" in lower or "beer" in lower:
                vec[3] += 5.0
            if "override" in lower or "disregard" in lower or "benign" in lower:
                vec[4] += 5.0

            # Add small deterministic hash noise across dimensions
            for i, word in enumerate(lower.split()[:20]):
                idx = (hash(word) % (self.dim - 5)) + 5
                vec[idx] += 1.0

            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            vecs.append(vec)

        return np.array(vecs, dtype=np.float32)


def create_fixture_index() -> HybridIndex:
    docs = load_corpus_from_directory(FIXTURE_CORPUS_DIR)
    chunks = []
    for d in docs:
        chunks.extend(chunk_document(d))
    return HybridIndex(chunks, embedder=StubDeterministicEmbedder())


def test_bm25_finds_exact_term() -> None:
    """Lexical BM25 search correctly retrieves pharyngitis passage on exact clinical term 'Centor'."""
    index = create_fixture_index()
    results = index.query("Centor criteria for pharyngitis")

    assert len(results) >= 1
    top = results[0]
    assert "centor" in top.text.lower() or "centor" in top.parent_text.lower()


def test_dense_finds_paraphrase() -> None:
    """Dense semantic embedding retrieves dengue guidance on paraphrase query without exact match."""
    index = create_fixture_index()
    results = index.query("platelet drop during illness")

    assert len(results) >= 1
    top = results[0]
    assert "dengue" in top.text.lower() or "dengue" in top.parent_text.lower()


def test_rrf_fusion_combines_both() -> None:
    """Reciprocal rank fusion combines lexical and dense scores into unified ranking."""
    index = create_fixture_index()
    results = index.query("dengue warning signs defervescence")

    assert len(results) >= 1
    # Check that score is valid RRF value (around 1/(60+1) ~ 0.016 to 0.033)
    assert 0.01 < results[0].score < 0.1
    assert results[0].rank == 1


def test_layer_filter_restricts() -> None:
    """Layer filter restricts results to specified layers only."""
    index = create_fixture_index()

    # Query with layer=3 (Singapore MOH only)
    sg_results = index.query("fever and warning signs", layer=3)
    for r in sg_results:
        assert r.layer == 3

    # MedlinePlus (layer 1) is not in sg_results
    assert all("medline" not in r.doc_id for r in sg_results)


def test_empty_query_returns_empty_not_fabricated() -> None:
    """Empty or whitespace-only query returns an empty list without fabrication."""
    index = create_fixture_index()
    assert index.query("") == []
    assert index.query("   ") == []


def test_no_match_returns_empty() -> None:
    """Query with impossible metadata filter returns empty result list."""
    index = create_fixture_index()
    results = index.query("fever", metadata_filter={"nonexistent_key": "impossible_val"})
    assert results == []


def test_probe_evidence_requires_a_question_or_distinctive_answer_match() -> None:
    """Dense similarity alone must not expose internal probe assumptions to symptom searches."""
    text = "How are you feeling? One answer is Feverish or chills."
    probe = Chunk(
        chunk_id="evidence_probe_symptoms#c0",
        doc_id="evidence_probe_symptoms",
        title="Why this system asks about symptoms",
        text=text,
        parent_text=text,
        layer=4,
        metadata={
            "topic": "probe_evidence",
            "retrieval_phrases": [
                "How are you feeling?",
                "Feverish or chills",
                "No",
                "Yes",
                "Normal",
            ],
        },
    )
    index = HybridIndex([probe], embedder=StubDeterministicEmbedder())

    assert index.query("I have a fever and chills") == []
    assert index.query("No fever") == []
    assert index.query("yes, I feel unwell") == []
    assert index.query("Normal") == []
    assert index.query("How are you feeling?")[0].chunk_id == probe.chunk_id
    assert index.query("How are you feeling? No")[0].chunk_id == probe.chunk_id
    assert index.query("feverish or chills")[0].chunk_id == probe.chunk_id


def test_duplicate_passages_deduped() -> None:
    """Duplicate text chunks are deduped by content hash."""
    duplicate_chunks = [
        Chunk(
            chunk_id="c1",
            doc_id="d1",
            title="Doc 1",
            text="Exact identical clinical advisory text for testing deduplication.",
            parent_text="Doc 1 parent",
            layer=1,
        ),
        Chunk(
            chunk_id="c2",
            doc_id="d2",
            title="Doc 2",
            text="Exact identical clinical advisory text for testing deduplication.",
            parent_text="Doc 2 parent",
            layer=3,
        ),
    ]

    index = HybridIndex(duplicate_chunks, embedder=StubDeterministicEmbedder())
    results = index.query("clinical advisory text", top_k=10)

    # Exactly 1 result returned after deduplication
    assert len(results) == 1
