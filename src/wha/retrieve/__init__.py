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
from wha.retrieve.index import (
    DefaultSentenceTransformerEmbedder,
    Embedder,
    HybridIndex,
)
from wha.retrieve.models import (
    Chunk,
    CorpusDocument,
    CorpusManifest,
    RetrievalResult,
    SourceManifestEntry,
)

__all__ = [
    "Chunk",
    "CorpusDocument",
    "CorpusManifest",
    "DefaultSentenceTransformerEmbedder",
    "Embedder",
    "HybridIndex",
    "RetrievalResult",
    "SourceManifestEntry",
    "build_corpus_manifest",
    "chunk_document",
    "chunk_section_text",
    "generate_layer_4_confounder_docs",
    "load_corpus_from_directory",
    "split_into_sections",
]
