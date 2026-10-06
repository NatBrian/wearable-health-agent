"""Hybrid retrieval index combining BM25 and dense embeddings with Reciprocal Rank Fusion."""

import hashlib
import re
from typing import Any, Protocol, runtime_checkable

import numpy as np
from rank_bm25 import BM25Okapi

from wha.constants import RETRIEVE_TOP_K, RRF_K
from wha.retrieve.models import Chunk, RetrievalResult


class Embedder(Protocol):
    """Protocol for dense text embedding."""

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed a list of strings into a normalized 2D numpy array (N, D)."""
        ...


@runtime_checkable
class Retriever(Protocol):
    """What the agent requires of a search index, and nothing more.

    Implement this to replace retrieval. `HybridIndex` satisfies it structurally, so no
    change to the current implementation was needed to introduce it.

    **The binding contract is the return type, not the signature.** `enforce_grounding` in
    `retrieve/grounding.py` reads `chunk_id`, `doc_id`, `title`, `text` and `source_url`
    from `RetrievalResult` to strip clinical sentences that no retrieved passage supports.
    An index returning a different shape disables that check without raising, so keep the
    shape. `tests/unit/retrieve/test_retriever_protocol.py` pins the fields it depends on.

    `runtime_checkable` is required because `tool_retrieve_clinical_evidence` uses
    `isinstance` to distinguish an index from the episode database. That check only tests
    for a `query` attribute, which is safe because `EpisodeRepository` has none; a test
    holds that true.
    """

    def query(
        self,
        query_str: str,
        top_k: int = RETRIEVE_TOP_K,
        layer: int | list[int] | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        """Return passages matching the query, best first."""
        ...


class DefaultSentenceTransformerEmbedder:
    """Live dense embedder using sentence-transformers (bge-small-en-v1.5)."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        self.model_name = model_name
        self._model = None

    def _get_model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 384), dtype=np.float32)
        model = self._get_model()
        embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(embeddings, dtype=np.float32)


def tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase alphanumeric words for BM25."""
    return re.findall(r"\w+", text.lower())


def _query_contains_phrase(query_tokens: list[str], phrase: str) -> bool:
    """Whether query contains a distinctive multiword phrase, not a generic answer token."""
    phrase_tokens = tokenize(phrase)
    if len(phrase_tokens) < 2 or len(phrase_tokens) > len(query_tokens):
        return False
    return any(
        query_tokens[start : start + len(phrase_tokens)] == phrase_tokens
        for start in range(len(query_tokens) - len(phrase_tokens) + 1)
    )


class HybridIndex:
    """Hybrid search index over chunk corpus using BM25, dense embeddings, and RRF."""

    def __init__(
        self,
        chunks: list[Chunk],
        embedder: Embedder | None = None,
        embeddings: np.ndarray | None = None,
    ) -> None:
        self.chunks = list(chunks)
        self.embedder = embedder or DefaultSentenceTransformerEmbedder()

        # BM25 Index
        tokenized_corpus = [tokenize(c.text) for c in self.chunks]
        self.bm25 = BM25Okapi(tokenized_corpus) if tokenized_corpus else None

        # Dense Index
        if embeddings is not None:
            self.embeddings = embeddings
        elif self.chunks:
            texts = [c.text for c in self.chunks]
            self.embeddings = self.embedder.embed_texts(texts)
        else:
            self.embeddings = np.empty((0, 384), dtype=np.float32)

    def query(
        self,
        query_str: str,
        top_k: int = RETRIEVE_TOP_K,
        layer: int | list[int] | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        """Execute hybrid search combining BM25 and dense ranking via RRF."""
        if not query_str or not query_str.strip() or not self.chunks:
            return []

        cleaned_query = query_str.strip()
        query_tokens = tokenize(cleaned_query)
        allowed_layers = (
            {layer} if isinstance(layer, int) else (set(layer) if layer is not None else None)
        )

        # 1. Candidate Filtering indices
        valid_indices: list[int] = []
        for idx, chunk in enumerate(self.chunks):
            if allowed_layers is not None and chunk.layer not in allowed_layers:
                continue
            if chunk.metadata.get("topic") == "probe_evidence":
                phrases = chunk.metadata.get("retrieval_phrases", [])
                if not any(_query_contains_phrase(query_tokens, phrase) for phrase in phrases):
                    continue
            if metadata_filter:
                match = True
                for k, v in metadata_filter.items():
                    if chunk.metadata.get(k) != v:
                        match = False
                        break
                if not match:
                    continue
            valid_indices.append(idx)

        if not valid_indices:
            return []

        # 2. BM25 Scores
        bm25_ranks: dict[int, int] = {}
        if self.bm25 and query_tokens:
            bm25_scores = self.bm25.get_scores(query_tokens)
            # Rank only valid indices with non-zero scores
            scored_bm25 = [
                (idx, float(bm25_scores[idx]))
                for idx in valid_indices
                if float(bm25_scores[idx]) > 0.0
            ]
            scored_bm25.sort(key=lambda x: x[1], reverse=True)
            for rank, (idx, _) in enumerate(scored_bm25, start=1):
                bm25_ranks[idx] = rank

        # 3. Dense Cosine Scores
        dense_ranks: dict[int, int] = {}
        if len(self.embeddings) == len(self.chunks) and len(valid_indices) > 0:
            query_vec = self.embedder.embed_texts([cleaned_query])
            if query_vec.shape[0] > 0 and query_vec.shape[1] == self.embeddings.shape[1]:
                # Cosine similarity (both vectors are normalized)
                q = query_vec[0]
                valid_matrix = self.embeddings[valid_indices]
                sims = np.dot(valid_matrix, q)
                scored_dense = [
                    (valid_indices[i], float(sims[i]))
                    for i in range(len(valid_indices))
                    if float(sims[i]) > 0.0
                ]
                scored_dense.sort(key=lambda x: x[1], reverse=True)
                for rank, (idx, _) in enumerate(scored_dense, start=1):
                    dense_ranks[idx] = rank

        # 4. Reciprocal Rank Fusion
        all_candidate_indices = set(bm25_ranks.keys()) | set(dense_ranks.keys())
        if not all_candidate_indices:
            return []

        rrf_scores: dict[int, float] = {}
        for idx in all_candidate_indices:
            score = 0.0
            if idx in bm25_ranks:
                score += 1.0 / (RRF_K + bm25_ranks[idx])
            if idx in dense_ranks:
                score += 1.0 / (RRF_K + dense_ranks[idx])
            rrf_scores[idx] = score

        # Sort candidates by RRF score descending
        sorted_indices = sorted(rrf_scores.keys(), key=lambda i: rrf_scores[i], reverse=True)

        # 5. Deduplication by content hash
        results: list[RetrievalResult] = []
        seen_hashes: set[str] = set()

        for idx in sorted_indices:
            chunk = self.chunks[idx]
            content_hash = hashlib.sha256(chunk.text.strip().lower().encode("utf-8")).hexdigest()
            if content_hash in seen_hashes:
                continue
            seen_hashes.add(content_hash)

            res = RetrievalResult(
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                title=chunk.title,
                heading=chunk.heading,
                text=chunk.text,
                parent_text=chunk.parent_text,
                layer=chunk.layer,
                source_url=chunk.source_url,
                score=round(rrf_scores[idx], 6),
                rank=len(results) + 1,
                metadata=dict(chunk.metadata),
            )
            results.append(res)
            if len(results) >= top_k:
                break

        return results
