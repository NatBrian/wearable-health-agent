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
3. **When a turn contains an uncited claim, only claims passing the evidence-span check are
   shown.** Grounding is the verbatim containment test in
   :func:`wha.retrieve.grounding.enforce_grounding`.

The conversation is also where red flags are *sought* rather than awaited. Sutaria et al.
2025 (BMC Health Serv Res 25:1263) measured online symptom checkers seeking 36.9 percent of
relevant red flags against 71.8 percent for physicians, and concluded that "diagnostic
accuracy alone may not be an adequate measure of safety". Here the outstanding items of a
validated rule are put in front of the model as the most useful thing it can ask about.
"""

import json
import re
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from wha.audit.monitor import record_conversation_turn
from wha.clock import local_today, now_utc
from wha.constants import (
    CONVERSATION_MAX_TURNS,
    CONVERSATION_SESSION_GAP_HOURS,
    TRIAGE_MAX_TURNS_BEFORE_ESCALATE,
)
from wha.db.iso import from_iso, to_iso
from wha.errors import LLMUnavailable, ValidationFailed
from wha.llm.client import LLMClient, get_llm_client
from wha.llm.prompts import get_prompt_definition
from wha.models import Citation, SubjectProfile
from wha.retrieve.grounding import enforce_grounding
from wha.retrieve.models import Citation as RetrievedPassage
from wha.retrieve.models import GeneratedClaim
from wha.safety.output_checks import DIAGNOSIS_PHRASES, FALSE_REASSURANCE_PHRASES
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
            to_iso(now_utc()),
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


def _rows_this_session(conn: sqlite3.Connection, subject_id: str) -> list[sqlite3.Row]:
    """Newest-first rows in the current consultation, bounded by the configured gap."""
    rows = conn.execute(
        """SELECT * FROM conversation_turns WHERE subject_id = ?
            ORDER BY seq DESC LIMIT 1000""",
        (subject_id,),
    ).fetchall()
    if not rows:
        return []

    gap = timedelta(hours=CONVERSATION_SESSION_GAP_HOURS)
    current: list[sqlite3.Row] = []
    previous: datetime | None = None
    for row in rows:
        try:
            stamp = from_iso(row["created_at_utc"])
        except (TypeError, ValueError):
            break
        if previous is not None and (previous - stamp) > gap:
            break
        current.append(row)
        previous = stamp
    return current


def _load_session_transcript(
    conn: sqlite3.Connection, subject_id: str, limit: int = TRANSCRIPT_TURNS
) -> list[dict[str, Any]]:
    """The current consultation only, oldest first, for the agent's working context."""
    rows = _rows_this_session(conn, subject_id)[:limit]
    return [dict(row) for row in reversed(rows)]


def _prior_session_turns(
    conn: sqlite3.Connection, subject_id: str, user_message: str
) -> list[dict[str, Any]]:
    """Current consultation turns before the user message being answered."""
    turns = _load_session_transcript(conn, subject_id)
    if turns and turns[-1]["role"] == "user" and turns[-1]["text"] == user_message:
        return turns[:-1]
    return turns


_CHAT_QUERY_STOP_WORDS = {
    "a",
    "about",
    "am",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "bit",
    "but",
    "can",
    "could",
    "did",
    "do",
    "does",
    "for",
    "from",
    "give",
    "have",
    "help",
    "hello",
    "hey",
    "how",
    "i",
    "in",
    "is",
    "it",
    "last",
    "me",
    "mean",
    "meaning",
    "means",
    "my",
    "of",
    "on",
    "or",
    "please",
    "recommend",
    "should",
    "so",
    "suggest",
    "tell",
    "thank",
    "thanks",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "to",
    "today",
    "was",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
    "would",
    "you",
    "your",
    "feel",
    "feeling",
    "night",
    "bpm",
}


def _topic_query(text: str) -> str:
    """Keep the health or measurement terms that matter to retrieval."""
    words = re.findall(r"[a-z]+|\d+", text.casefold())
    focused: list[str] = []
    for word in words:
        if word in _CHAT_QUERY_STOP_WORDS or word.isdecimal():
            continue
        focused.append("fever" if word == "feverish" else word)
    return " ".join(focused)


def _retrieval_query_for_turn(user_message: str, prior_turns: list[dict[str, Any]]) -> str:
    """Search the latest topic, borrowing current-session context for generic follow-ups."""
    focused = _topic_query(user_message)
    if focused:
        return focused
    for turn in reversed(prior_turns):
        if turn.get("role") == "user":
            focused = _topic_query(str(turn.get("text") or ""))
            if focused:
                return focused
    return ""


def _watch_record_passage(
    episode_summary: str,
    user_message: str,
    query: str,
    prior_turns: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Expose recorded watch facts as a source only when the person asks about them."""
    date_match = re.match(r"Latest recorded night: (\d{4}-\d{2}-\d{2})\.", episode_summary)
    watch_terms = {
        "alert",
        "coverage",
        "detection",
        "heart",
        "hr",
        "level",
        "measured",
        "measurement",
        "oxygen",
        "reading",
        "readings",
        "record",
        "rhr",
        "rate",
        "sleep",
        "spo2",
        "steps",
        "watch",
    }
    context_text = " ".join(
        [user_message, *(str(turn.get("text") or "") for turn in prior_turns)]
    ).casefold()
    message_words = set(re.findall(r"[a-z]+", context_text))
    personal_reference = bool(
        message_words.intersection({"my", "mine", "watch", "reading", "readings", "recorded"})
        or "last night" in context_text
        or "bpm" in message_words
    )
    if date_match is None or not personal_reference or not watch_terms.intersection(query.split()):
        return None
    return {
        "chunk_id": f"watch_record_{date_match.group(1)}",
        "doc_id": "",
        "title": "Your wearable record",
        "text": episode_summary,
        "source_url": "",
        "score": 1.0,
    }


def _turns_this_session(conn: sqlite3.Connection, subject_id: str) -> int:
    """How many turns are in the CONSULTATION the person is currently in.

    This was `len(load_transcript(conn, subject_id, limit=1000))`, every row the subject
    had ever produced, with no episode, session or date filter, and nothing anywhere resets
    or deletes conversation_turns. So after twenty stored rows the agent stopped conversing
    permanently and every future message got "we have been going back and forth for 10
    exchanges" forever.

    Tu et al. measured ten turns within one consultation. A limit derived from that paper
    and applied to a lifetime is not that paper's finding.

    A gap of CONVERSATION_SESSION_GAP_HOURS ends a session, so picking the phone up the
    next morning starts a new one. The rows are kept either way: nothing here deletes
    history, and `established_urgency` still reads the whole transcript, so an escalation
    from a previous session is still in force.
    """
    return len(_rows_this_session(conn, subject_id))


def _episode_for_escalation(
    conn: sqlite3.Connection,
    subject_id: str,
    urgency: str | None,
    episode_id: str | None,
) -> str | None:
    """Open or extend the investigation an escalation implies. Never raises.

    EVERY path that can return an urgent or same-day reply must call this. It used to be
    written inline on the main path only, so the two early returns above it, the turn-limit
    reply and the model-unavailable reply, could hand somebody "urgent" with no
    investigation opened at all. Measured: with the model raising LLMUnavailable and the
    message "I am coughing up blood", `respond` returned urgency 'urgent' and the episodes
    table stayed empty. That is the defect item 27 exists to remove, reintroduced on the
    offline branch, and it is worse there because the offline branch is the one that runs
    when nothing else is working.

    `open_or_append_episode` appends to an open episode rather than opening a second, so
    saying the same thing twice produces one investigation rather than two.
    """
    if urgency not in ("urgent", "same_day") or episode_id is not None:
        return episode_id

    from wha.service.episode_lifecycle import open_or_append_episode

    try:
        return open_or_append_episode(conn, subject_id, local_today())
    except Exception:  # noqa: BLE001
        # A failure to open the investigation must not cost the person the escalation
        # itself, which is already in the reply and in the conversation record.
        return None


def established_urgency(conn: sqlite3.Connection, subject_id: str) -> str | None:
    """The most urgent level any rule has reached in this conversation.

    Read back from the transcript rather than held in memory, so a restart cannot lose an
    escalation and quietly start again from calm.

    UNBOUNDED ON PURPOSE, and this is the one the model and the ratchet read. Urgency may
    never fall because something reasoned it down, and narrowing this would be exactly
    that. What ages is the BANNER, not the fact; see `urgency_state`.
    """
    rows = conn.execute(
        "SELECT urgency FROM conversation_turns WHERE subject_id = ? AND urgency IS NOT NULL",
        (subject_id,),
    ).fetchall()
    level: str | None = None
    for row in rows:
        level = more_urgent(level, row["urgency"])
    return level


def urgency_state(conn: sqlite3.Connection, subject_id: str) -> dict[str, Any]:
    """The urgency, when it was set, how old it is, and whether it has been dealt with.

    A "see a doctor today" banner from eleven days ago sat at the top of the page with no
    date on it and no way to clear it. A red banner that never goes away is one you learn
    to ignore, which is the alarm fatigue this project cites in its own constants.

    Nothing here lowers an urgency. `established_urgency` is unchanged and still monotone;
    this adds the two things the screen was missing, WHEN and WHETHER YOU DEALT WITH IT,
    and lets the interface say so instead of repeating an instruction with "today" in it
    for a fortnight.
    """
    from wha.constants import URGENCY_STALE_DAYS

    level = established_urgency(conn, subject_id)
    if level is None:
        return {"urgency": None, "set_on": None, "days_ago": None, "stale": False, "cleared": False}

    # MOST RECENT, not first. This was MIN(created_at_utc), and MIN made an old
    # acknowledgement clear a NEW urgency of the same level: raised on day 1, acknowledged
    # on day 2, raised again on day 30, and because `set_on` was still day 1 the day-2
    # acknowledgement compared as "after it" and the banner stayed cleared. A live red
    # banner silently suppressed by a fortnight-old acknowledgement is exactly the silent
    # drop item 32's own "what could go wrong" section forbids.
    #
    # MAX also makes the screen's "It has not been repeated since" true by construction:
    # if it had been repeated, this would be that later time.
    row = conn.execute(
        """SELECT MAX(created_at_utc) AS last_set FROM conversation_turns
            WHERE subject_id = ? AND urgency = ?""",
        (subject_id, level),
    ).fetchone()
    set_on = row["last_set"] if row is not None and row["last_set"] else None
    days_ago = None
    if set_on:
        try:
            days_ago = (now_utc() - from_iso(set_on)).days
        except (TypeError, ValueError):
            days_ago = None

    # Cleared only by the person saying they have seen somebody, and only if they said so
    # AFTER the urgency was set. Recorded in the audit chain under the `human_decision`
    # operation, so clearing a red banner is itself on the record.
    cleared = False
    if set_on:
        seen = conn.execute(
            """SELECT 1 FROM audit_events
                WHERE subject_id = ? AND operation = 'human_decision'
                  AND human_decision = 'urgency_acknowledged'
                  AND timestamp_utc >= ?
                LIMIT 1""",
            (subject_id, set_on),
        ).fetchone()
        cleared = seen is not None

    return {
        "urgency": level,
        "set_on": set_on,
        "days_ago": days_ago,
        "stale": bool(days_ago is not None and days_ago >= URGENCY_STALE_DAYS),
        "cleared": cleared,
    }


# The two Marburg items that are standing facts about a person rather than facts about
# this episode. Item 1 is "a woman 65 or over, or a man 55 or over", which age and sex
# settle between them. Item 2 is known coronary, cerebrovascular or peripheral vascular
# disease, which is the item most likely to be misremembered under stress and the one that
# never changes.
MARBURG_AGE_SEX_ITEM = "mhs_age_sex"
MARBURG_VASCULAR_ITEM = "mhs_known_vascular"
MARBURG_FEMALE_AGE = 65
MARBURG_MALE_AGE = 55


def profile_rule_answers(profile: SubjectProfile, valid_ids: set[str]) -> list[RuleAnswer]:
    """Rule items the Settings profile already answers, so nobody is asked them twice.

    Asking these during a chest pain conversation spends a turn at the worst possible
    moment, and the answers do not depend on what is happening today.

    A missing field yields no answer at all rather than a False. The rule then stays
    incomplete and resolves the conservative way, which is what the design requires: not
    knowing must never look like nothing being wrong.
    """
    answers: list[RuleAnswer] = []

    if MARBURG_AGE_SEX_ITEM in valid_ids and profile.age_years is not None and profile.sex:
        threshold = MARBURG_FEMALE_AGE if profile.sex == "female" else MARBURG_MALE_AGE
        answers.append(
            RuleAnswer(
                item_id=MARBURG_AGE_SEX_ITEM,
                answer=profile.age_years >= threshold,
                quote=f"From your profile: {profile.age_years}, {profile.sex}.",
            )
        )

    if MARBURG_VASCULAR_ITEM in valid_ids and profile.known_vascular_disease is not None:
        answers.append(
            RuleAnswer(
                item_id=MARBURG_VASCULAR_ITEM,
                answer=profile.known_vascular_disease,
                quote="From your profile.",
            )
        )

    return answers


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
                to_iso(now_utc()),
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


def _remove_inline_questions(text: str) -> str:
    """Keep a follow-up question in its structured field, so it appears only once."""
    fragments = re.split(r"(?<=[.!?])\s+|\n+", text)
    return " ".join(fragment.strip() for fragment in fragments if "?" not in fragment)


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

    transcript = _prior_session_turns(conn, subject_id, user_message)
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

    # The standing facts, read once. Everything that reads them treats a missing value as
    # unknown and behaves conservatively. Imported here rather than at module level:
    # wha.service imports this module, so a top-level import is a cycle.
    from wha.service.settings import get_subject_profile

    profile = get_subject_profile(subject_id, conn=conn)

    # 1. The floor, on the person's own words, before the model is involved at all.
    #
    # `observe_and_check` rather than the bare check, because the floor needs to know how
    # long each symptom has been going. It did not, and the persistence half of Tier B had
    # therefore never fired for anybody: five nights of a worsening fever produced five
    # refusals to escalate. Recording tonight's mention first is load-bearing, which is why
    # the ordering lives in one function instead of at each call site.
    from wha.service.symptoms import observe_and_check

    safety = observe_and_check(conn, subject_id, user_message)
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
    # READ WITH ITS POPULATION ATTACHED, as safety/triage.py already says: that review is
    # about red flags for cancer and fracture in LOW BACK PAIN, and its odds do not
    # transfer to anything this system routes. It is cited for the shape of the finding,
    # that one matched phrase is weak and a combination is not, and for nothing else.
    #
    # Flags with no validated rule still escalate on the spot. That includes every tier B
    # rule and both vitals rules, none of which map to a presentation, so narrowing this
    # to chest pain does not quietly disarm the rest of the floor.
    outstanding = [i for i in (rule.items if rule else []) if known.get(i.id) is None]
    flags_without_rule = [f for f in triggered if presentation_for_flag(f, config) is None]

    turn_index = _turns_this_session(conn, subject_id)
    at_limit = turn_index >= CONVERSATION_MAX_TURNS * 2

    # THE SUPPRESSION IS ONLY VALID IF THE DISCRIMINATOR IS ACTUALLY GOING TO RUN.
    #
    # Holding the floor's urgency back is a trade: no escalation now, in exchange for the
    # rule's questions being asked instead. `at_limit` is precisely the case where the
    # second half of that trade cannot be honoured, because the conversation stops here.
    #
    # Without `and not at_limit`, somebody typing "I have chest pain" on turn twenty-one
    # received urgency None and a message saying we had talked enough. Measured. The
    # comment in the branch below asserted the opposite, and asserting it did not make it
    # true. Refusing to converse must never be a way for urgency to come out lower than
    # the deterministic floor put it.
    if safety.escalate and not flags_without_rule and rule is not None and not at_limit:
        floor_urgency = None

    if at_limit:
        # THE LIMIT NOW STOPS SOMETHING.
        #
        # `CONVERSATION_MAX_TURNS` is cited to Tu et al. 2025, where AMIE had the
        # information it needed within the first ten turns. The code worked out whether
        # the person was at that limit, attached the answer to the reply as
        # `at_turn_limit`, and nothing read it. A stop condition that does not stop
        # anything is worse than none, because it appears in the report as a control.
        #
        # The safety floor above has already run on this message, and its urgency is NOT
        # suppressed here (see the `and not at_limit` above), so somebody typing "chest
        # pain" on turn twenty-one does escalate. What stops is the conversing, never the
        # floor. This used to be a claim in a comment rather than a property of the code.
        text = (
            f"We have been going back and forth for {CONVERSATION_MAX_TURNS} exchanges, "
            "which is as far as this is useful. A study of conversational diagnosis found "
            "the information needed was in hand within about that many turns, and past it "
            "I would be rephrasing rather than learning anything new.\n\n"
            "What is worth doing now is taking this to a person. The summary on the "
            "History page is written for a doctor: it has your nights, what you told me, "
            "which rules ran and what they concluded, with the dates on everything.\n\n"
            "If something changes or gets worse, say so and the safety rules will still "
            "read it. They have not stopped."
        )
        limit_urgency = more_urgent(prior, floor_urgency)
        episode_id = _episode_for_escalation(conn, subject_id, limit_urgency, episode_id)
        reply = ConversationReply(
            text=text,
            urgency=limit_urgency,
            urgency_reason=(
                "The conversation reached its length limit. The urgency here is whatever "
                "the rules had already established, unchanged."
            ),
            triggered_flags=triggered,
            guidance=list(safety.guidance),
            turn_index=turn_index + 1,
            at_turn_limit=True,
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

    prompt_def = get_prompt_definition("converse")
    prior_turns = _prior_session_turns(conn, subject_id, user_message)
    query = _retrieval_query_for_turn(user_message, prior_turns)
    passages = _passages_for(query)
    watch_passage = _watch_record_passage(episode_summary, user_message, query, prior_turns)
    if watch_passage is not None:
        passages.insert(0, watch_passage)
    try:
        prompt = prompt_def.render(
            {
                "episode_summary": episode_summary or "No investigation is open.",
                "transcript": _render_transcript(prior_turns),
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
        offline_urgency = more_urgent(prior, floor_urgency)
        episode_id = _episode_for_escalation(conn, subject_id, offline_urgency, episode_id)
        reply = ConversationReply(
            text=text,
            urgency=offline_urgency,
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
    # Two of the five Marburg items are standing facts, not things to ask somebody who is
    # frightened about their chest. Age, sex and known vascular disease are collected once
    # in Settings, so the conversation only has to ask the three that genuinely vary.
    collected.extend(
        a
        for a in profile_rule_answers(profile, valid_ids)
        if a.item_id not in {c.item_id for c in collected}
    )
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
        # The age gate. Marburg was built on "1,199 unselected and consecutive patients
        # aged >= 35 years", triage() has always taken an age_years to enforce that, and
        # nothing ever filled it in, so the rule ran on everybody. In a real run a 24 year
        # old scored 3 of 5 on three things common in a young adult with a pulled muscle
        # and was told it was urgent, citing a study of people twice their age.
        outcome = triage(
            presentation,
            gates=gates,
            answers=known,
            age_years=age_years if age_years is not None else profile.age_years,
            config=config,
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

    # An urgent conversation opens an investigation, so there is ONE escalation path.
    #
    # There were two. `report_symptoms` did this with its own SQL and the conversation
    # engine did not do it at all, so "I have chest pain" behaved differently depending on
    # where it was typed: the command line opened an episode, the dashboard and Telegram
    # did not. Worse, only `report_symptoms` opened one and it opened a NEW one every
    # time, so the live database holds five identical closed escalated episodes with the
    # same dates, never investigated, all shown separately on History.
    #
    # `open_or_append_episode` appends to an open episode rather than opening a second, so
    # saying the same thing twice produces one investigation. It is also where the
    # concurrency assertion lives.
    episode_id = _episode_for_escalation(conn, subject_id, urgency, episode_id)

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
    quoted_spans = {
        claim.citation: claim.evidence_span
        for claim in grounded
        if claim.citation and claim.evidence_span
    }
    citations = [
        Citation(
            source_id=str(p["chunk_id"]),
            title=str(p["title"]),
            uri=str(p.get("source_url") or p.get("doc_id") or "") or None,
            passage=str(p["text"]),
            retrieval_score=float(p.get("score") or 0.0),
            quoted_span=quoted_spans.get(str(p["chunk_id"])),
        )
        for p in passages
        if str(p["chunk_id"]) in cited_ids
    ]

    # A claim whose span was not found is not shown as if it were sourced. It joins the
    # uncited list for audit and storage. If any claim is uncited, construct the displayed
    # body only from claims whose evidence spans passed the deterministic check; do not
    # trust free-form prose to repeat an unsupported claim exactly enough to remove it.
    grounded_texts = {c.text for c in grounded}
    uncited = list(result.uncited_notes) + [
        c.text for c in result.grounded_claims if c.text not in grounded_texts
    ]

    # Append the question only when it is not already in the reply. The model routinely
    # puts the same sentence in both fields, and the result was a real message that asked
    # the person about their temperature twice in a row.
    if uncited:
        grounded_sentences = [_sanitise(claim.text).strip() for claim in grounded]
        text = " ".join(sentence for sentence in grounded_sentences if sentence)
        if not text:
            text = "I couldn't verify an answer from the available sources."
    else:
        text = _sanitise(result.reply)
    question = _sanitise(result.question) if result.question else ""
    if question:
        text = _remove_inline_questions(text)
    if question and question.strip().casefold() not in text.casefold():
        text = f"{text}\n\n{question}"

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

    record_conversation_turn(
        conn,
        subject_id=subject_id,
        user_text=user_message,
        reply_text=reply.text,
        urgency=urgency,
        triggered_flags=triggered,
        citations=len(citations),
        uncited=len(reply.uncited),
        rule_id=outcome.rule_id if outcome else None,
        score=outcome.score if outcome else None,
        gate_triggered=outcome.gate_triggered if outcome else None,
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
        prompt, schema=ConverseResponse, temperature=temperature, max_tokens=4096
    )
