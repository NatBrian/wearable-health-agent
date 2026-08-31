"""Data models for corpus documents, chunks, citations, claims, and index manifests."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CorpusDocument(BaseModel):
    """Raw or structured document in the retrieval corpus."""

    model_config = ConfigDict(frozen=True)

    doc_id: str
    title: str
    layer: int
    source_url: str | None = None
    licence: str = "Attribution"
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    """Section-aware chunk with parent section context for retrieval."""

    model_config = ConfigDict(frozen=True)

    chunk_id: str
    doc_id: str
    title: str
    heading: str | None = None
    text: str
    parent_text: str
    layer: int
    source_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    """Scored and ranked retrieved passage."""

    model_config = ConfigDict(frozen=True)

    chunk_id: str
    doc_id: str
    title: str
    heading: str | None = None
    text: str
    parent_text: str
    layer: int
    source_url: str | None = None
    score: float
    rank: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)


class Citation(BaseModel):
    """Retrieved passage cited as evidence."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    title: str = ""
    uri: str = ""
    text: str = ""


class GeneratedClaim(BaseModel):
    """Generated clinical assertion with explicit evidence span and citation link."""

    model_config = ConfigDict(frozen=False)

    text: str
    evidence_span: str | None = None
    citation: str | None = None


class SourceManifestEntry(BaseModel):
    """Manifest entry for a single corpus source layer."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    layer: int
    licence: str
    doc_count: int
    checksum: str


class CorpusManifest(BaseModel):
    """Manifest recording build provenance, licences, checksums, and chunking params."""

    model_config = ConfigDict(frozen=True)

    manifest_version: str = "1.0"
    created_at_utc: str
    chunk_count: int
    chunk_target_tokens: int
    sources: list[SourceManifestEntry]
    sha256: str
