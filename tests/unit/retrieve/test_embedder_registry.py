"""The phone cannot run sentence-transformers, so it must be able to hand the index an
embedder of its own before the index is built. The registry is that hand-off."""

import numpy as np

from wha.retrieve import embedder_registry
from wha.retrieve.knowledge_docs import _INDEX_CACHE, build_index
from wha.retrieve.models import CorpusDocument


class CountingEmbedder:
    def __init__(self) -> None:
        self.calls = 0

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        self.calls += 1
        vectors = np.zeros((len(texts), 384), dtype=np.float32)
        vectors[:, 0] = 1.0
        return vectors


def _tiny_corpus() -> list[CorpusDocument]:
    return [
        CorpusDocument(
            doc_id="t1", title="Fever", text="A fever is a body temperature above normal.",
            layer=1, source_url="test", metadata={},
        )
    ]


def test_build_index_uses_the_registered_embedder(monkeypatch) -> None:
    embedder = CountingEmbedder()
    embedder_registry.set_default_embedder(embedder)
    try:
        monkeypatch.setattr("wha.retrieve.knowledge_docs._load_cached_embeddings", lambda chunks: None)
        monkeypatch.setattr("wha.retrieve.knowledge_docs._save_cached_embeddings", lambda c, e: None)
        index = build_index(_tiny_corpus())
        assert embedder.calls == 1
        assert index.embedder is embedder
    finally:
        embedder_registry.set_default_embedder(None)


def test_explicit_argument_beats_the_registry(monkeypatch) -> None:
    registered, explicit = CountingEmbedder(), CountingEmbedder()
    embedder_registry.set_default_embedder(registered)
    try:
        monkeypatch.setattr("wha.retrieve.knowledge_docs._load_cached_embeddings", lambda chunks: None)
        monkeypatch.setattr("wha.retrieve.knowledge_docs._save_cached_embeddings", lambda c, e: None)
        index = build_index(_tiny_corpus(), embedder=explicit)
        assert explicit.calls == 1 and registered.calls == 0
        assert index.embedder is explicit
    finally:
        embedder_registry.set_default_embedder(None)


def test_registry_starts_empty_and_clears() -> None:
    _INDEX_CACHE.clear()
    assert embedder_registry.get_default_embedder() is None
    embedder_registry.set_default_embedder(CountingEmbedder())
    embedder_registry.set_default_embedder(None)
    assert embedder_registry.get_default_embedder() is None
