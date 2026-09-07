"""Deterministic claim-to-source grounding enforcement."""

from collections.abc import Sequence

from wha.retrieve.models import Citation, GeneratedClaim, RetrievalResult


def normalize_whitespace_and_case(text: str) -> str:
    """Fold case and normalize all whitespace sequences to a single space."""
    return " ".join(text.lower().split())


def enforce_grounding(
    claims: Sequence[GeneratedClaim],
    passages: Sequence[Citation | RetrievalResult | str],
) -> tuple[list[GeneratedClaim], int]:
    """Deterministic claim-to-source enforcement via verbatim containment test.

    For each claim, evidence_span must appear verbatim in at least one retrieved passage
    after whitespace normalization and case folding.

    Returns:
        (grounded_claims, unsupported_claims_count)
    """
    normalized_passages: list[tuple[str, str]] = []
    for p in passages:
        if isinstance(p, Citation):
            source_id = p.source_id or p.title or "source"
            content = p.text or p.title
        elif isinstance(p, RetrievalResult):
            source_id = p.chunk_id or p.doc_id
            content = f"{p.text}\n{p.parent_text}"
        elif isinstance(p, str):
            source_id = "text_source"
            content = p
        else:
            source_id = "unknown"
            content = str(p)

        normalized_passages.append((source_id, normalize_whitespace_and_case(content)))

    grounded: list[GeneratedClaim] = []
    unsupported_count = 0

    for claim in claims:
        if not claim.evidence_span or not claim.evidence_span.strip():
            claim.citation = None
            unsupported_count += 1
            continue

        normalized_span = normalize_whitespace_and_case(claim.evidence_span)
        matched_source_id: str | None = None

        for source_id, norm_passage in normalized_passages:
            if normalized_span in norm_passage:
                matched_source_id = source_id
                break

        if matched_source_id is not None:
            # Attribution is decided here, not by the model. A claim whose span is found
            # in source A while the model cited source B previously kept B, and
            # output_checks then filtered the displayed sources down to B, dropping the
            # passage that actually supports the sentence. The reader would be shown a
            # citation that does not contain the claim.
            claim.citation = matched_source_id
            grounded.append(claim)
        else:
            claim.citation = None
            unsupported_count += 1

    return grounded, unsupported_count
