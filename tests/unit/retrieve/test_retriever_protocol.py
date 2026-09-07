"""Retrieval is replaced by implementing an interface, not by matching a class name.

`Retriever` is a single method. These tests cover the two things a replacement can get
wrong: failing to satisfy the protocol, and returning a result shape that the grounding
check silently depends on.
"""

import sqlite3

from wha.agent.repository import EpisodeRepository
from wha.retrieve.index import HybridIndex, Retriever
from wha.retrieve.models import Chunk, RetrievalResult


class StubEmbedder:
    """Deterministic, so this file never loads a real embedding model."""

    def embed_texts(self, texts):
        import numpy as np

        return np.zeros((len(texts), 384), dtype=np.float32)


def test_the_real_index_satisfies_the_protocol() -> None:
    """If this fails, `tool_retrieve_clinical_evidence` silently retrieves nothing."""
    index = HybridIndex([], embedder=StubEmbedder())
    assert isinstance(index, Retriever)


def test_the_episode_database_does_not_satisfy_the_protocol() -> None:
    """The check that makes `isinstance` safe at the call site.

    `tool_retrieve_clinical_evidence` does `db if isinstance(db, Retriever) else
    getattr(db, "retrieval_index", None)`, because `db` is either an index or the episode
    database. A `runtime_checkable` protocol only tests that a `query` attribute exists, so
    an `EpisodeRepository` that ever grew a `query` method would be mistaken for a search
    index and the agent would retrieve from the wrong object without erroring.
    """
    repo = EpisodeRepository(conn=sqlite3.connect(":memory:"))
    assert not isinstance(repo, Retriever)


def test_anything_with_a_query_method_can_stand_in() -> None:
    """The point of the seam: no inheritance, no registration, no import of HybridIndex."""

    class KeywordOnlyIndex:
        def query(self, query_str, top_k=5, layer=None, metadata_filter=None):
            return [
                RetrievalResult(
                    chunk_id="c1",
                    doc_id="d1",
                    title="A document",
                    text="matched text",
                    parent_text="matched text",
                    layer=1,
                    score=1.0,
                )
            ]

    assert isinstance(KeywordOnlyIndex(), Retriever)


def test_the_return_shape_is_the_contract_that_matters() -> None:
    """A replacement returning a different shape disables the claim-to-source check.

    `enforce_grounding` reads `chunk_id`, `title`, `text` and `source_url` off these
    results to strip clinical sentences no passage supports. Losing a field does not
    degrade retrieval; it removes a safety mechanism, and it does so without an error.
    """
    required = {"chunk_id", "doc_id", "title", "text", "parent_text", "layer", "source_url"}
    missing = required - set(RetrievalResult.model_fields)
    assert not missing, f"RetrievalResult lost fields grounding depends on: {missing}"


def test_a_chunk_still_carries_what_a_citation_needs() -> None:
    """Chunks are what an index is built from, so the same argument applies to them."""
    assert {"chunk_id", "doc_id", "text", "layer"} <= set(Chunk.model_fields)
