"""Section-aware chunking preserving parent document and section context."""

import re

from wha.constants import CHUNK_TARGET_TOKENS
from wha.retrieve.models import Chunk, CorpusDocument


def split_into_sections(text: str) -> list[tuple[str | None, str]]:
    """Split markdown-style text into (heading, section_text) tuples."""
    lines = text.split("\n")
    sections: list[tuple[str | None, list[str]]] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    heading_re = re.compile(r"^(#{1,6})\s+(.+)$")

    for line in lines:
        match = heading_re.match(line)
        if match:
            if current_lines or current_heading is not None:
                sections.append((current_heading, current_lines))
            current_heading = match.group(2).strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading, current_lines))

    return [
        (heading, "\n".join(sec_lines).strip())
        for heading, sec_lines in sections
        if "\n".join(sec_lines).strip()
    ]


def chunk_section_text(text: str, target_tokens: int = CHUNK_TARGET_TOKENS) -> list[str]:
    """Break section text into chunks respecting paragraph boundaries."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return [text] if text.strip() else []

    chunks: list[str] = []
    current_chunk_paras: list[str] = []
    current_word_count = 0

    for para in paragraphs:
        para_words = len(para.split())
        if current_word_count + para_words > target_tokens and current_chunk_paras:
            chunks.append("\n\n".join(current_chunk_paras))
            current_chunk_paras = [para]
            current_word_count = para_words
        else:
            current_chunk_paras.append(para)
            current_word_count += para_words

    if current_chunk_paras:
        chunks.append("\n\n".join(current_chunk_paras))

    return chunks


def chunk_document(doc: CorpusDocument, target_tokens: int = CHUNK_TARGET_TOKENS) -> list[Chunk]:
    """Chunk a CorpusDocument with section-awareness and parent-document preservation."""
    sections = split_into_sections(doc.text)
    if not sections:
        sections = [(None, doc.text)]

    chunks: list[Chunk] = []
    chunk_idx = 0

    for heading, section_text in sections:
        parent_text = section_text if len(section_text) >= len(doc.text) * 0.2 else doc.text
        sub_chunks = chunk_section_text(section_text, target_tokens=target_tokens)
        for sc in sub_chunks:
            chunk = Chunk(
                chunk_id=f"{doc.doc_id}#c{chunk_idx}",
                doc_id=doc.doc_id,
                title=doc.title,
                heading=heading,
                text=sc,
                parent_text=parent_text,
                layer=doc.layer,
                source_url=doc.source_url,
                metadata=dict(doc.metadata),
            )
            chunks.append(chunk)
            chunk_idx += 1

    return chunks
