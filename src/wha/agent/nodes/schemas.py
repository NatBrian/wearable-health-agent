"""Structured response models the nodes ask the language model to fill in."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from wha.models import (
    ExtractedFact,
)


class ToolCallArgs(BaseModel):
    """Tool invocation payload from model."""

    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)
    called_at_utc: datetime | None = None


class DoneSignal(BaseModel):
    """Completion signal with rationale."""

    reason: str


class InvestigateStep(BaseModel):
    """Single turn of the investigation loop."""

    tool_call: ToolCallArgs | None = None
    done: DoneSignal | None = None


class FactExtractionResponse(BaseModel):
    """Typed structured facts extracted by LLM from investigation artifacts."""

    facts: list[ExtractedFact] = Field(default_factory=list)


class VetoCheckResponse(BaseModel):
    """Unidirectional redundant question veto decision from model."""

    veto: bool = False
    reason: str = ""
    suggested_alternative: str | None = None


class QuestionDraftResponse(BaseModel):
    """Drafted question text and option labels from LLM."""

    text: str
    option_labels: list[str] = Field(default_factory=list)
    rationale: str | None = None


class OutcomeClaim(BaseModel):
    """One clinical assertion, with the passage span the model says supports it.

    ``claims`` was a bare ``list[str]``, so there was nothing to check a claim against and
    the claim-to-source enforcement in ``docs/CONTRACTS.md`` section 11.3 could not run
    even in principle. The span is what makes the check a deterministic containment test
    rather than a second opinion.
    """

    text: str
    evidence_span: str = ""


class WriteOutcomeResponse(BaseModel):
    """Synthesized outcome prose from the model.

    `escalation_criteria` was here and has been removed. It was the when-to-seek-care
    text, the sentence a person is most likely to act on, and the only field in the
    system that went through no check at all. A live run produced "Seek care if fever
    persists beyond 72 hours or exceeds 103 degrees F (39.4 C)", invented. It is now
    selected from `red_flags.yaml` by `select_escalation_criteria`, so there is nothing
    left to guard.
    """

    observation: str
    claims: list[OutcomeClaim] = Field(default_factory=list)
    action_text: str = ""


class CritiqueResponse(BaseModel):
    """Subtractive output critique response from LLM."""

    approved: bool = True
    stripped_claims: list[str] = Field(default_factory=list)
    modified_text: str = ""
    critique_notes: str = ""
