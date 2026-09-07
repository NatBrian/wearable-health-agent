"""Retrieval, hybrid search, and claim-to-source enforcement."""

from wha.retrieve.chunking import (
    chunk_document,
    chunk_section_text,
    split_into_sections,
)
from wha.retrieve.corpus import (
    build_corpus_manifest,
    generate_layer_4_confounder_docs,
    load_corpus_from_directory,
)
from wha.retrieve.grounding import (
    enforce_grounding,
    normalize_whitespace_and_case,
)
from wha.retrieve.index import (
    DefaultSentenceTransformerEmbedder,
    Embedder,
    HybridIndex,
    Retriever,
)
from wha.retrieve.models import (
    Chunk,
    Citation,
    CorpusDocument,
    CorpusManifest,
    GeneratedClaim,
    RetrievalResult,
    SourceManifestEntry,
)

__all__ = [
    "Chunk",
    "Citation",
    "CorpusDocument",
    "CorpusManifest",
    "DefaultSentenceTransformerEmbedder",
    "Embedder",
    "GeneratedClaim",
    "HybridIndex",
    "RetrievalResult",
    "Retriever",
    "SourceManifestEntry",
    "build_corpus_manifest",
    "chunk_document",
    "chunk_section_text",
    "enforce_grounding",
    "generate_layer_4_confounder_docs",
    "load_corpus_from_directory",
    "normalize_whitespace_and_case",
    "split_into_sections",
]
