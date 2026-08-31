"""Data models for corpus documents, chunks, and index manifests."""

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
