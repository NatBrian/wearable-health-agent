"""Corpus loading, manifest creation, and Layer 4 generator from causes.yaml."""

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import yaml

from wha.belief.causes import load_causes
from wha.constants import CHUNK_TARGET_TOKENS
from wha.retrieve.models import Chunk, CorpusDocument, CorpusManifest, SourceManifestEntry


def generate_layer_4_confounder_docs() -> list[CorpusDocument]:
    """Generate Layer 4 citable confounder evidence documents from causes.yaml."""
    causes = load_causes()
    docs: list[CorpusDocument] = []

    for cause in causes:
        lines = [
            f"# Confounder Evidence: {cause.cause.value}",
            f"**Cause ID:** {cause.cause.value}",
            f"**Base Rate:** {cause.base_rate}",
            f"**Typical RHR Effect:** {cause.effect_mean_bpm:+.1f} bpm (SD {cause.effect_sd_bpm:.1f})",
            f"**Evidence Grade:** {cause.evidence_grade}",
            f"**Citation:** {cause.citation}",
            "",
            "## Clinical Mechanism and Effect Profile",
            f"Effect mean: {cause.effect_mean_bpm} bpm, SD: {cause.effect_sd_bpm} bpm.",
            "",
            "## Temporal Progression",
            f"Day-by-day multiplier profile across episode nights: {cause.profile}",
        ]
        doc_text = "\n".join(lines)
        docs.append(
            CorpusDocument(
                doc_id=f"confounder_{cause.cause.value}",
                title=f"Confounder Evidence: {cause.cause.value}",
                layer=4,
                source_url="data/knowledge/causes.yaml",
                licence="Ours",
                text=doc_text,
                metadata={"cause_id": cause.cause.value, "layer": 4},
            )
        )

    return docs


def load_corpus_from_directory(corpus_dir: Path | str) -> list[CorpusDocument]:
    """Load documents from JSON, Markdown or YAML files in a directory."""
    path = Path(corpus_dir)
    docs: list[CorpusDocument] = []
    if not path.is_dir():
        return docs

    for file in sorted(path.glob("*.*")):
        if file.suffix in [".md", ".txt"]:
            content = file.read_text(encoding="utf-8")
            doc_id = file.stem
            docs.append(
                CorpusDocument(
                    doc_id=doc_id,
                    title=doc_id.replace("_", " ").title(),
                    layer=1 if "medline" in doc_id else (3 if "sg" in doc_id else 2),
                    source_url=str(file),
                    licence="Attribution",
                    text=content,
                    metadata={"filename": file.name},
                )
            )
        elif file.suffix in [".yaml", ".yml"]:
            data = yaml.safe_load(file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for item in data:
                    docs.append(CorpusDocument(**item))
            elif isinstance(data, dict) and "documents" in data:
                for item in data["documents"]:
                    docs.append(CorpusDocument(**item))
            elif isinstance(data, dict):
                docs.append(CorpusDocument(**data))
    return docs


def build_corpus_manifest(
    docs: list[CorpusDocument],
    chunks: list[Chunk],
    chunk_target_tokens: int = CHUNK_TARGET_TOKENS,
) -> CorpusManifest:
    """Build manifest with licence, doc counts, and checksums."""
    now_utc = datetime.now(UTC).isoformat()

    layers_dict: dict[int, list[CorpusDocument]] = {}
    for d in docs:
        layers_dict.setdefault(d.layer, []).append(d)

    entries: list[SourceManifestEntry] = []
    combined_content = ""

    for layer, layer_docs in sorted(layers_dict.items()):
        layer_text = "".join(d.text for d in layer_docs)
        layer_hash = hashlib.sha256(layer_text.encode("utf-8")).hexdigest()
        combined_content += layer_hash
        licence = layer_docs[0].licence if layer_docs else "Attribution"
        entries.append(
            SourceManifestEntry(
                source_id=f"layer_{layer}",
                layer=layer,
                licence=licence,
                doc_count=len(layer_docs),
                checksum=layer_hash,
            )
        )

    overall_hash = hashlib.sha256(combined_content.encode("utf-8")).hexdigest()

    return CorpusManifest(
        manifest_version="1.0",
        created_at_utc=now_utc,
        chunk_count=len(chunks),
        chunk_target_tokens=chunk_target_tokens,
        sources=entries,
        sha256=overall_hash,
    )
