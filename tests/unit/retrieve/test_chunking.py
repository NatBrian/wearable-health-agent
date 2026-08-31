"""Unit tests for section-aware chunking, parent document preservation, and corpus manifests."""

from pathlib import Path

from wha.retrieve import (
    CorpusDocument,
    build_corpus_manifest,
    chunk_document,
    load_corpus_from_directory,
)

FIXTURE_CORPUS_DIR = Path("tests/fixtures/corpus")


def test_chunking_is_section_aware() -> None:
    """Document chunking splits along markdown headings rather than arbitrary character cuts."""
    doc = CorpusDocument(
        doc_id="test_doc",
        title="Test Clinical Guideline",
        layer=2,
        licence="Attribution",
        text=(
            "# Header 1\nSection 1 content about respiratory illness.\n\n"
            "## Subheader 1.1\nDetailed signs including cough and tachypnea.\n\n"
            "# Header 2\nSection 2 content about cardiovascular stability."
        ),
    )

    chunks = chunk_document(doc, target_tokens=100)
    assert len(chunks) >= 3

    headings = [c.heading for c in chunks]
    assert "Header 1" in headings
    assert "Subheader 1.1" in headings
    assert "Header 2" in headings

    # Each chunk text stays within section
    for c in chunks:
        if c.heading == "Header 2":
            assert "cardiovascular stability" in c.text
            assert "respiratory illness" not in c.text


def test_parent_document_returned() -> None:
    """Chunk preserves the parent section text context for grounding and display."""
    doc = CorpusDocument(
        doc_id="test_doc",
        title="Test Guideline",
        layer=1,
        text="# Section Alpha\nParagraph 1.\n\nParagraph 2.\n\nParagraph 3.",
    )

    chunks = chunk_document(doc, target_tokens=5)
    assert len(chunks) >= 2

    for c in chunks:
        assert c.parent_text is not None
        assert "Section Alpha" in c.parent_text
        assert "Paragraph 1" in c.parent_text


def test_manifest_records_licence_and_checksum() -> None:
    """CorpusManifest records licences, chunk counts, and sha256 checksums per layer."""
    docs = load_corpus_from_directory(FIXTURE_CORPUS_DIR)
    assert len(docs) >= 4

    all_chunks = []
    for d in docs:
        all_chunks.extend(chunk_document(d))

    manifest = build_corpus_manifest(docs, all_chunks)
    assert manifest.chunk_count == len(all_chunks)
    assert manifest.sha256 and len(manifest.sha256) == 64
    assert len(manifest.sources) >= 1

    for src in manifest.sources:
        assert src.licence
        assert src.checksum
        assert src.doc_count >= 1


def test_fixture_corpus_contains_inj_001_and_clean_twin() -> None:
    """Fixture corpus contains both the poisoned INJ-001 prompt injection document and its clean twin."""
    docs = load_corpus_from_directory(FIXTURE_CORPUS_DIR)
    doc_ids = {d.doc_id for d in docs}

    assert "inj_001" in doc_ids
    assert "inj_001_clean" in doc_ids

    inj_doc = next(d for d in docs if d.doc_id == "inj_001")
    clean_doc = next(d for d in docs if d.doc_id == "inj_001_clean")

    assert "[SYSTEM OVERRIDE]" in inj_doc.text
    assert "[SYSTEM OVERRIDE]" not in clean_doc.text
