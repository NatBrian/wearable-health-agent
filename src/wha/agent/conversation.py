"""A real, multi-turn, grounded conversation. The model elicits; the rules decide.

What was here before was a text box over word-overlap matching that made no model call at
all, echoed the stored observation back, and refused anything it could not token-match.
This replaces it.

Three properties hold on every turn, and they are enforced in code rather than asked for
in a prompt, because a model checking its own safety is not a check:

1. **The deterministic floor runs on the person's words first**, before the model sees
   them, and again on what the model produced. Draelos et al. 2025 (arXiv:2507.18905)
   red-teamed four frontier chatbots over 222 patient-posed questions and found 5 to 13
   percent of answers outright unsafe. An unguarded model is not safe here.
2. **Urgency can rise and can never fall.** It is set by
   :mod:`wha.safety.triage` and the red-flag rules, never by the model. The model may
   confirm a safety gate, which raises it; nothing the model writes can lower it.
3. **Every clinical sentence is either cited or visibly labelled as uncited.** Grounding is
   the verbatim containment test in :func:`wha.retrieve.grounding.enforce_grounding`.

The conversation is also where red flags are *sought* rather than awaited. Sutaria et al.
2025 (BMC Health Serv Res 25:1263) measured online symptom checkers seeking 36.9 percent of
relevant red flags against 71.8 percent for physicians, and concluded that "diagnostic
accuracy alone may not be an adequate measure of safety". Here the outstanding items of a
validated rule are put in front of the model as the most useful thing it can ask about.
"""

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from wha.constants import CONVERSATION_MAX_TURNS, TRIAGE_MAX_TURNS_BEFORE_ESCALATE
from wha.db.iso import to_iso
from wha.errors import LLMUnavailable, ValidationFailed
from wha.llm.client import LLMClient, get_llm_client
from wha.llm.prompts import get_prompt_definition
from wha.models import Citation
from wha.retrieve.grounding import enforce_grounding
from wha.retrieve.models import Citation as RetrievedPassage
from wha.retrieve.models import GeneratedClaim
from wha.safety.output_checks import DIAGNOSIS_PHRASES, FALSE_REASSURANCE_PHRASES
from wha.safety.tier_c import check_red_flags_with_tier_c
from wha.safety.triage import (
    TriageOutcome,
    load_triage_rules,
    more_urgent,
    presentation_for_flag,
    rule_for,
    triage,
)

PASSAGE_CHARS = 3500
TRANSCRIPT_TURNS = 12


class RuleAnswer(BaseModel):
    """One decision-rule item the person answered, with their own words."""

    item_id: str
    answer: bool
    quote: str = ""


class RuleExtraction(BaseModel):
    """What a focused, zero-temperature pass found in what the person has said."""

    rule_answers: list[RuleAnswer] = Field(default_factory=list)
    gates_confirmed: list[str] = Field(default_factory=list)


class ConverseResponse(BaseModel):
    """What the model returns for one turn."""

    reply: str
    grounded_claims: list[GeneratedClaim] = Field(default_factory=list)
    uncited_notes: list[str] = Field(default_factory=list)
    rule_answers: list[RuleAnswer] = Field(default_factory=list)
    gates_confirmed: list[str] = Field(default_factory=list)
    asked_item_id: str | None = None
    question: str | None = None


class ConversationReply(BaseModel):
    """One agent turn, after every deterministic check has run over it."""

    model_config = ConfigDict(frozen=True)

    text: str
    citations: list[Citation] = Field(default_factory=list)
    uncited: list[str] = Field(default_factory=list)
    urgency: str | None = None
    urgency_reason: str = ""
    triggered_flags: list[str] = Field(default_factory=list)
    guidance: list[str] = Field(default_factory=list)
    asked_item_id: str | None = None
    triage: TriageOutcome | None = None
    turn_index: int = 0
    at_turn_limit: bool = False
    refused: bool = False


# ---------------------------------------------------------------------------- storage


def _next_seq(conn: sqlite3.Connection, subject_id: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(seq), 0) AS s FROM conversation_turns WHERE subject_id = ?",
        (subject_id,),
    ).fetchone()
    return int(row["s"]) + 1


def record_turn(
    conn: sqlite3.Connection,
    subject_id: str,
    role: str,
    text: str,
    episode_id: str | None = None,
    citations: list[Citation] | None = None,
    uncited: list[str] | None = None,
    urgency: str | None = None,
    triggered_flags: list[str] | None = None,
    asked_item_id: str | None = None,
    presentation: str | None = None,
) -> int:
    """Append one turn. The transcript outlives the process so a session can be resumed."""
    seq = _next_seq(conn, subject_id)
    conn.execute(
        """INSERT INTO conversation_turns
             (id, episode_id, subject_id, seq, role, text, citations_json, uncited_json,
              urgency, triggered_flags_json, asked_item_id, presentation, created_at_utc)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            f"turn_{uuid.uuid4().hex[:12]}",
            episode_id,
            subject_id,
            seq,
            role,
            text,
            json.dumps([c.model_dump() for c in (citations or [])], default=str),
            json.dumps(uncited or []),
            urgency,
            json.dumps(triggered_flags or []),
            asked_item_id,
            presentation,
            to_iso(datetime.now(UTC)),
        ),
    )
    conn.commit()
    return seq


def load_transcript(
    conn: sqlite3.Connection, subject_id: str, limit: int = TRANSCRIPT_TURNS
) -> list[dict[str, Any]]:
    """The most recent turns, oldest first."""
    rows = conn.execute(
        """SELECT * FROM conversation_turns WHERE subject_id = ?
           ORDER BY seq DESC LIMIT ?""",
        (subject_id, limit),
    ).fetchall()
    return [dict(r) for r in reversed(rows)]


def established_urgency(conn: sqlite3.Connection, subject_id: str) -> str | None:
    """The most urgent level any rule has reached in this conversation.

    Read back from the transcript rather than held in memory, so a restart cannot lose an
    escalation and quietly start again from calm.
    """
    rows = conn.execute(
        "SELECT urgency FROM conversation_turns WHERE subject_id = ? AND urgency IS NOT NULL",
        (subject_id,),
    ).fetchall()
    level: str | None = None
    for row in rows:
        level = more_urgent(level, row["urgency"])
    return level


def save_rule_answers(
    conn: sqlite3.Connection,
    subject_id: str,
    presentation: str,
    answers: list[RuleAnswer],
    episode_id: str | None = None,
) -> None:
    """Store what the person said about each rule item, with their own words beside it."""
    for answer in answers:
        conn.execute(
            """INSERT INTO triage_answers
                 (subject_id, episode_id, presentation, item_id, answer, source_text,
                  recorded_at_utc)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(subject_id, presentation, item_id) DO UPDATE SET
                 answer = excluded.answer,
                 source_text = excluded.source_text,
                 recorded_at_utc = excluded.recorded_at_utc""",
            (
                subject_id,
                episode_id,
                presentation,
                answer.item_id,
                1 if answer.answer else 0,
                answer.quote,
                to_iso(datetime.now(UTC)),
            ),
        )
    conn.commit()


def load_rule_answers(
    conn: sqlite3.Connection, subject_id: str, presentation: str
) -> dict[str, bool | None]:
    """Everything already established for a rule, for scoring and for the handover."""
    rows = conn.execute(
        "SELECT item_id, answer FROM triage_answers WHERE subject_id = ? AND presentation = ?",
        (subject_id, presentation),
    ).fetchall()
    return {r["item_id"]: (None if r["answer"] is None else bool(r["answer"])) for r in rows}


# ---------------------------------------------------------------------------- the turn


def _active_presentation(
    conn: sqlite3.Connection, subject_id: str, triggered_flags: list[str]
) -> str | None:
    """Which discriminator conversation is open, from this turn or an earlier one."""
    for flag in triggered_flags:
        presentation = presentation_for_flag(flag)
        if presentation:
            return presentation

    # An open discriminator conversation is remembered on the turn, not inferred from the
    # answers gathered. Inferring it meant that if a turn extracted nothing, which happens
    # whenever the person answers vaguely, the presentation was forgotten and the next
    # message started again from scratch with no rule in progress.
    row = conn.execute(
        """SELECT presentation FROM conversation_turns
            WHERE subject_id = ? AND presentation IS NOT NULL
            ORDER BY seq DESC LIMIT 1""",
        (subject_id,),
    ).fetchone()
    if row is not None:
        return str(row["presentation"])

    fallback = conn.execute(
        "SELECT presentation FROM triage_answers WHERE subject_id = ? LIMIT 1",
        (subject_id,),
    ).fetchone()
    return fallback["presentation"] if fallback else None


def _passages_for(query: str, top_k: int = 6) -> list[dict[str, Any]]:
    """Retrieve from the authored corpus. Empty rather than raising if it cannot build."""
    try:
        from wha.retrieve.knowledge_docs import get_default_index

        return [
            {
                "chunk_id": r.chunk_id,
                "doc_id": r.doc_id,
                "title": r.title,
                "text": r.text,
                "source_url": r.source_url,
                "score": r.score,
            }
            for r in get_default_index().query(query, top_k=top_k)
        ]
    except Exception:  # noqa: BLE001
        return []


def _render_passages(passages: list[dict[str, Any]]) -> str:
    if not passages:
        return "None retrieved. You have nothing to cite, so grounded_claims must be empty."
    text = "\n\n".join(f"[{p['chunk_id']}] {p['title']}\n{p['text']}" for p in passages)
    return text[:PASSAGE_CHARS]


def _render_transcript(turns: list[dict[str, Any]]) -> str:
    if not turns:
        return "(nothing yet)"
    return "\n".join(f"{t['role']}: {t['text']}" for t in turns)


def _sanitise(text: str) -> str:
    """Strip the phrasings the safety rules forbid outright, wherever they appear.

    ``red_flags.yaml`` states it plainly: this system never says "you are fine". The same
    deterministic cleaning the outcome prose gets is applied to conversation, because the
    conversation is now where most words reach the person.
    """
    cleaned = text
    for phrase in list(FALSE_REASSURANCE_PHRASES) + list(DIAGNOSIS_PHRASES):
        if phrase in cleaned.lower():
            idx = cleaned.lower().find(phrase)
            while idx != -1:
                cleaned = cleaned[:idx] + cleaned[idx + len(phrase) :]
                idx = cleaned.lower().find(phrase)
    return " ".join(cleaned.split())


def extract_rule_items(
    conn: sqlite3.Connection,
    subject_id: str,
    user_message: str,
    rule: Any,
    outstanding: list[Any],
    config: Any,
    llm_client: LLMClient | None = None,
) -> RuleExtraction:
    """Pull decision-rule answers out of what has been said, as its own focused call.

    Asked to converse and to extract in one response, the model conversed. In a live run it
    asked the Marburg questions correctly and returned an empty answer list every time, so
    the rule never completed, no urgency was ever decided, and a person describing chest
    pain was left in limbo. This runs separately, at temperature zero, over the outstanding
    items only.
    """
    if not outstanding:
        return RuleExtraction()

    transcript = load_transcript(conn, subject_id)
    said = "\n".join(f"{t['role']}: {t['text']}" for t in transcript)
    try:
        definition = get_prompt_definition("extract_rule_items")
        prompt = definition.render(
            {
                "conversation": f"{said}\nuser: {user_message}",
                "items": "\n".join(f"- {i.id}: {i.question_intent.strip()}" for i in outstanding),
                "gates": "\n".join(f"- {g.id}: {g.label}" for g in config.unconditional),
            }
        )
        result, _ = (llm_client or get_llm_client()).complete(
            prompt, schema=RuleExtraction, temperature=definition.temperature
        )
        return result
    except (LLMUnavailable, ValidationFailed, KeyError, TypeError, ValueError):
        # Extraction failing is not a reason to invent an answer. The rule stays
        # incomplete, and the turn budget below resolves it conservatively.
        return RuleExtraction()


def _agent_turns_since_presentation(conn: sqlite3.Connection, subject_id: str) -> int:
    """Agent replies since a discriminator conversation opened, counting the one in progress.

    The turn being produced counts. Without it the budget is always one turn behind, and
    the escalation fires a turn later than the constant says it should.
    """
    row = conn.execute(
        """SELECT MIN(seq) AS s FROM conversation_turns
            WHERE subject_id = ? AND triggered_flags_json != '[]'""",
        (subject_id,),
    ).fetchone()
    if row is None or row["s"] is None:
        return 0
    count = conn.execute(
        """SELECT COUNT(*) AS n FROM conversation_turns
            WHERE subject_id = ? AND role = 'agent' AND seq >= ?""",
        (subject_id, row["s"]),
    ).fetchone()
    return (int(count["n"]) if count else 0) + 1


def respond(
    conn: sqlite3.Connection,
    subject_id: str,
    user_message: str,
    episode_id: str | None = None,
    episode_summary: str = "",
    llm_client: LLMClient | None = None,
    age_years: int | None = None,
) -> ConversationReply:
    """One conversational turn, with every deterministic check applied around the model."""
    record_turn(conn, subject_id, "user", user_message, episode_id=episode_id)

    # 1. The floor, on the person's own words, before the model is involved at all.
    safety = check_red_flags_with_tier_c(user_text=user_message)
    triggered = list(safety.triggered_flags)
    floor_urgency = safety.level if safety.escalate else None

    config = load_triage_rules()
    prior = established_urgency(conn, subject_id)
    presentation = _active_presentation(conn, subject_id, triggered)
    rule = rule_for(presentation, config) if presentation else None
    known = load_rule_answers(conn, subject_id, presentation) if presentation else {}

    # A matched flag that a validated rule covers opens a discriminator conversation
    # instead of an escalation. Downie et al. 2013 (BMJ 347:f7095) found single red flags
    # mostly uninformative and combinations informative; this is that finding in code.
    #
    # Flags with no validated rule still escalate on the spot. That includes every tier B
    # rule and both vitals rules, none of which map to a presentation, so narrowing this
    # to chest pain does not quietly disarm the rest of the floor.
    outstanding = [i for i in (rule.items if rule else []) if known.get(i.id) is None]
    flags_without_rule = [f for f in triggered if presentation_for_flag(f, config) is None]
    if safety.escalate and not flags_without_rule and rule is not None:
        floor_urgency = None

    turn_index = len(load_transcript(conn, subject_id, limit=1000))
    at_limit = turn_index >= CONVERSATION_MAX_TURNS * 2

    prompt_def = get_prompt_definition("converse")
    passages = _passages_for(user_message)
    try:
        prompt = prompt_def.render(
            {
                "episode_summary": episode_summary or "No investigation is open.",
                "transcript": _render_transcript(load_transcript(conn, subject_id)),
                "user_message": user_message,
                "passages": _render_passages(passages),
                "established_urgency": prior or "none",
                "triage_state": (
                    f"{rule.label}: {len(outstanding)} of {len(rule.items)} items outstanding"
                    if rule
                    else "none in progress"
                ),
                "outstanding_items": (
                    "; ".join(f"{i.id}: {i.question_intent.strip()}" for i in outstanding) or "none"
                ),
                "gates": "; ".join(f"{g.id}: {g.label}" for g in config.unconditional),
            }
        )
        result, _ = llm_client_complete(llm_client, prompt, prompt_def.temperature)
    except (LLMUnavailable, ValidationFailed, KeyError, TypeError, ValueError) as exc:
        # The model being unavailable must never look like reassurance.
        text = (
            "I cannot reach the language model right now, so I can only tell you what the "
            "fixed rules found. Nothing here is a judgement about you."
        )
        reply = ConversationReply(
            text=text,
            urgency=more_urgent(prior, floor_urgency),
            urgency_reason=f"Model unavailable: {exc}",
            triggered_flags=triggered,
            guidance=list(safety.guidance),
            turn_index=turn_index,
            refused=True,
        )
        record_turn(
            conn,
            subject_id,
            "agent",
            reply.text,
            episode_id=episode_id,
            urgency=reply.urgency,
            triggered_flags=triggered,
        )
        return reply

    # 2. What the person told us about the rule, stored with their own words. The
    #    conversation model may volunteer answers; a separate focused pass at temperature
    #    zero is what actually finds them, because asked to do both the model converses.
    gate_ids = {g.id for g in config.unconditional}
    extracted = RuleExtraction()
    if presentation and rule is not None:
        extracted = extract_rule_items(
            conn, subject_id, user_message, rule, outstanding, config, llm_client
        )

    valid_ids = {i.id for i in (rule.items if rule else [])}
    collected = [
        a
        for a in (list(result.rule_answers) + list(extracted.rule_answers))
        if a.item_id in valid_ids
    ]
    if presentation and collected:
        save_rule_answers(conn, subject_id, presentation, collected, episode_id=episode_id)
        known = load_rule_answers(conn, subject_id, presentation)

    # 3. The rule decides. Gates first, so a presentation that excludes the rule never
    #    gets a score computed for it.
    gates = {
        g: True
        for g in (list(result.gates_confirmed) + list(extracted.gates_confirmed))
        if g in gate_ids
    }
    outcome: TriageOutcome | None = None
    rule_urgency: str | None = None
    if presentation:
        outcome = triage(
            presentation, gates=gates, answers=known, age_years=age_years, config=config
        )
        rule_urgency = outcome.urgency

    # 4. Nobody is left in limbo. A presentation the rules have opened but not resolved
    #    means the system does not yet know how urgent this is, and not knowing must not
    #    look like nothing being wrong. After a bounded number of turns it resolves the
    #    conservative way. Measured need: in a live run the agent asked the right questions,
    #    recorded none of the answers, and left a person with chest pain with no urgency at
    #    all, which is worse than the over-escalation this design replaced.
    if (
        presentation
        and rule is not None
        and outcome is not None
        and not outcome.complete
        and _agent_turns_since_presentation(conn, subject_id) >= TRIAGE_MAX_TURNS_BEFORE_ESCALATE
    ):
        rule_urgency = "urgent"
        outcome = outcome.model_copy(
            update={
                "urgency": "urgent",
                "meaning": (
                    "Not enough was established to use the decision rule, so this is being "
                    "treated as urgent. That is the cautious direction, not a finding."
                ),
            }
        )

    # 5. Urgency is the most urgent thing anything has established, ever. Monotone by
    #    construction: nothing the model wrote can lower it.
    urgency = more_urgent(more_urgent(prior, floor_urgency), rule_urgency)

    # 6. Grounding: verbatim containment, in code.
    searchable = [
        RetrievedPassage(
            source_id=str(p["chunk_id"]),
            title=str(p["title"]),
            uri=str(p.get("source_url") or ""),
            text=str(p["text"]),
        )
        for p in passages
    ]
    grounded, unsupported = enforce_grounding(list(result.grounded_claims), searchable)
    cited_ids = {c.citation for c in grounded if c.citation}
    citations = [
        Citation(
            source_id=str(p["chunk_id"]),
            title=str(p["title"]),
            uri=str(p.get("source_url") or p.get("doc_id") or "") or None,
            passage=str(p["text"]),
            retrieval_score=float(p.get("score") or 0.0),
        )
        for p in passages
        if str(p["chunk_id"]) in cited_ids
    ]

    # A claim whose span was not found is not shown as if it were sourced. It joins the
    # uncited list, where the interface labels it, rather than disappearing silently.
    grounded_texts = {c.text for c in grounded}
    uncited = list(result.uncited_notes) + [
        c.text for c in result.grounded_claims if c.text not in grounded_texts
    ]

    text = _sanitise(result.reply)
    if result.question:
        text = f"{text}\n\n{_sanitise(result.question)}"

    reply = ConversationReply(
        text=text.strip(),
        citations=citations,
        uncited=[u for u in (_sanitise(u) for u in uncited) if u],
        urgency=urgency,
        urgency_reason=(outcome.meaning if outcome and outcome.complete else ""),
        triggered_flags=triggered,
        guidance=list(safety.guidance),
        asked_item_id=result.asked_item_id,
        triage=outcome,
        turn_index=turn_index + 1,
        at_turn_limit=at_limit,
    )

    record_turn(
        conn,
        subject_id,
        "agent",
        reply.text,
        episode_id=episode_id,
        citations=citations,
        uncited=reply.uncited,
        urgency=urgency,
        triggered_flags=triggered,
        asked_item_id=result.asked_item_id,
        presentation=presentation,
    )
    _ = unsupported
    return reply


def llm_client_complete(
    client: LLMClient | None, prompt: Any, temperature: float
) -> tuple[ConverseResponse, Any]:
    """Single seam for the model call, so tests can drive a turn without a network."""
    return (client or get_llm_client()).complete(
        prompt, schema=ConverseResponse, temperature=temperature
    )
