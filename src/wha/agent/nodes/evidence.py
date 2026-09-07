"""Turning retrieved passages into citations, and stripping claims without one."""

from typing import Any

from wha.agent.nodes.context import _INVESTIGATE_CALLS_CHARS, _compact_json
from wha.agent.nodes.schemas import OutcomeClaim
from wha.models import (
    Citation,
)
from wha.retrieve.grounding import enforce_grounding
from wha.retrieve.models import Citation as RetrievedPassage
from wha.retrieve.models import GeneratedClaim


def _retrieved_passages(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every passage `retrieve_clinical_evidence` returned in this episode, deduped."""
    passages: list[dict[str, Any]] = []
    seen: set[str] = set()
    for call in tool_calls:
        if call.get("tool_name") != "retrieve_clinical_evidence" or not call.get("ok"):
            continue
        for passage in call.get("value") or []:
            if not isinstance(passage, dict):
                continue
            chunk_id = str(passage.get("chunk_id", ""))
            if not chunk_id or chunk_id in seen:
                continue
            seen.add(chunk_id)
            passages.append(passage)
    return passages


def _passages_for_prompt(passages: list[dict[str, Any]]) -> str:
    """The retrieved passages, laid out so the model can quote a span out of one."""
    if not passages:
        return (
            "No passages were retrieved in this episode. Return an empty claims list: "
            "there is nothing to ground a claim against."
        )
    blocks = [f"[{p.get('chunk_id')}] {p.get('title', '')}\n{p.get('text', '')}" for p in passages]
    return _compact_json(blocks, _INVESTIGATE_CALLS_CHARS)


def _citations_for(passages: list[dict[str, Any]]) -> list[Citation]:
    """The retrieved passages, in the shape an EpisodeOutcome records."""
    return [
        Citation(
            source_id=str(p.get("chunk_id", "")),
            title=str(p.get("title", "")),
            uri=str(p.get("source_url") or p.get("doc_id") or "") or None,
            passage=str(p.get("text", "")),
            retrieval_score=float(p.get("score") or 0.0),
        )
        for p in passages
    ]


def _enforce_claims(
    claims: list[OutcomeClaim],
    passages: list[dict[str, Any]],
    observation: str,
) -> tuple[str, list[Citation], int, list[str]]:
    """Check each claim against the retrieved text, and strip the ones that fail.

    Returns the observation with unsupported claims removed, the citations that actually
    support what remains, the count of claims that failed, and their text. Attribution is
    decided by :func:`enforce_grounding` from where the span was found, not by what the
    model said.
    """
    if not claims:
        return observation, [], 0, []

    # Two Citation models exist. wha.retrieve.models.Citation is what the grounding check
    # searches; wha.models.Citation is what an EpisodeOutcome records. Conflating them
    # raises at the model boundary, which is the only reason this distinction is visible.
    searchable = [
        RetrievedPassage(
            source_id=str(p.get("chunk_id", "")),
            title=str(p.get("title", "")),
            uri=str(p.get("source_url") or p.get("doc_id") or ""),
            text=str(p.get("text", "")),
        )
        for p in passages
    ]

    generated = [GeneratedClaim(text=c.text, evidence_span=c.evidence_span or None) for c in claims]
    grounded, unsupported = enforce_grounding(generated, searchable)

    grounded_texts = {c.text for c in grounded}
    cleaned = observation
    stripped: list[str] = []
    for claim in claims:
        if claim.text and claim.text not in grounded_texts:
            # Stripped before display, per the contract. A claim whose span is not in any
            # retrieved passage does not get to appear in the prose a person reads.
            #
            # Recorded as well as removed. The episode view assigned `stripped_claims` an
            # empty list and never filled it, so the panel whose whole job is to show what
            # was taken out showed a green tick even on episodes where something was.
            stripped.append(claim.text)
            if claim.text in cleaned:
                cleaned = cleaned.replace(claim.text, "").strip()

    cited_ids = {c.citation for c in grounded if c.citation}
    supporting = _citations_for([p for p in passages if str(p.get("chunk_id", "")) in cited_ids])
    return cleaned or observation, supporting, unsupported, stripped
