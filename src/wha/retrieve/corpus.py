"""Corpus loading, manifest creation, and Layer 4 generator from causes.yaml."""

import hashlib
from pathlib import Path

import yaml

from wha.belief.causes import load_causes
from wha.clock import now_utc
from wha.constants import CHUNK_TARGET_TOKENS
from wha.retrieve.models import Chunk, CorpusDocument, CorpusManifest, SourceManifestEntry

CAUSES_PATH = Path("data/knowledge/causes.yaml")


def _load_cause_prose(path: Path | None = None) -> dict[str, dict[str, str]]:
    """The prose in causes.yaml that CausePrior does not carry.

    ``CausePrior`` keeps only what the belief model computes with. The label, the note,
    the derivation and the reasoning behind the temporal profile are the parts a person
    would actually want to read, and they are the reason a retrieved passage is worth
    citing rather than just restating a number.
    """
    target = path if path is not None else CAUSES_PATH
    if not target.exists():
        return {}
    data = yaml.safe_load(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    prose: dict[str, dict[str, str]] = {}
    for row in data.get("causes", []) or []:
        if isinstance(row, dict) and "cause" in row:
            prose[str(row["cause"])] = {
                key: str(row[key]).strip()
                for key in (
                    "label",
                    "note",
                    "derivation",
                    "assumption",
                    "profile_source",
                    "provenance",
                )
                if row.get(key)
            }
    return prose


def generate_layer_4_confounder_docs(path: Path | None = None) -> list[CorpusDocument]:
    """Generate Layer 4 citable confounder evidence documents from causes.yaml.

    One document per candidate cause, so that when the agent says an elevation is better
    explained by alcohol than by an infection it can cite the effect size, the base rate
    and the temporal shape that support the claim, rather than asserting it.
    """
    causes = load_causes() if path is None else load_causes(path)
    prose = _load_cause_prose(path)
    docs: list[CorpusDocument] = []

    for cause in causes:
        extra = prose.get(cause.cause.value, {})
        label = extra.get("label", cause.cause.value)
        lines = [
            f"# {label}",
            "",
            (
                "One of the candidate explanations for a raised sleeping heart rate. "
                f"Cause id: {cause.cause.value}."
            ),
            "",
            "## How large the effect is",
            "",
            (
                f"When present, this contributes about {cause.effect_mean_bpm:+.2f} bpm "
                "to the night's resting heart rate, with a between-person spread of "
                f"{cause.effect_sd_bpm:.2f} bpm. It is present on roughly "
                f"{cause.base_rate * 100:.1f} percent of nights."
            ),
            "",
            f"Evidence grade {cause.evidence_grade}."
            + (f" Provenance: {extra['provenance']}." if "provenance" in extra else ""),
            "",
            f"Source: {cause.citation}",
        ]
        if "derivation" in extra:
            lines += ["", "## How the number was derived", "", extra["derivation"]]
        if "assumption" in extra:
            lines += [
                "",
                "## This figure is assumed, not published",
                "",
                extra["assumption"],
            ]
        lines += [
            "",
            "## How it behaves over successive nights",
            "",
            (
                "Contribution weight by night since the elevation began: "
                f"{', '.join(f'{p:g}' for p in cause.profile)}. The last value repeats "
                "thereafter. The shape is what separates causes that look identical on "
                "any single night."
            ),
        ]
        if "profile_source" in extra:
            lines += ["", extra["profile_source"]]
        if "note" in extra:
            lines += ["", "## Why this one matters", "", extra["note"]]

        docs.append(
            CorpusDocument(
                doc_id=f"confounder_{cause.cause.value}",
                title=f"Confounder evidence: {label}",
                layer=4,
                source_url="data/knowledge/causes.yaml",
                licence="Ours",
                text="\n".join(lines),
                metadata={
                    "cause_id": cause.cause.value,
                    "layer": 4,
                    "citation": cause.citation,
                },
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
    fetched_at = now_utc().isoformat()

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
        created_at_utc=fetched_at,
        chunk_count=len(chunks),
        chunk_target_tokens=chunk_target_tokens,
        sources=entries,
        sha256=overall_hash,
    )
