"""Symptoms as things that persist, rather than keywords in a single message.

`red_flags.yaml` has always described Tier B as "two or more co-occurring, OR one
persisting beyond a stated duration". The persistence half had never once fired.
`check_red_flags_deterministic` takes a `symptom_history` argument and no production
caller passed it, so `history.get(rule_id, 1)` was always 1 and `1 > persist_nights` was
never true for any of the six symptoms that carry one. Verified by running five nights of
a worsening fever through the floor: five refusals to escalate.

It was not merely unwired. It was uncomputable, because nothing recorded that a symptom
had been present on a given night. This module is that missing record, and everything it
needs was already in `conversation_turns`, so nothing new is collected from anybody.

Three definitions live here, and each one is a decision rather than an implementation
detail:

**When does a symptom stop counting?** On an explicit retraction, or after
SYMPTOM_RUN_GAP_DAYS with no mention. Strict night-by-night consecutiveness was rejected:
somebody who says nothing on Tuesday has not recovered on Tuesday, and resetting their
fever to zero for going quiet punishes exactly the silence this work exists to fix.

**How long has it been going?** First mention to most recent mention within the current
run, inclusive. So a fever mentioned on the 1st and the 3rd has lasted three nights, not
two mentions.

**What counts as a symptom being gone?** The person saying so. A negated mention writes
`present = 0` rather than no row at all, because "I said my fever went" and "I did not
mention my fever" are different facts and only one of them is reassuring.
"""

import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta

from wha.clock import local_date_of, local_today, now_utc
from wha.constants import SYMPTOM_COOCCURRENCE_WINDOW_NIGHTS, SYMPTOM_RUN_GAP_DAYS
from wha.db.iso import from_iso, to_iso
from wha.safety.models import RedFlagsConfig, SafetyCheckResult
from wha.safety.rules import is_phrase_negated, load_red_flags, matches_symptom


@dataclass(frozen=True)
class SymptomRun:
    """One symptom, and how long the person has been reporting it."""

    flag_id: str
    tier: str
    first_night: date
    last_night: date
    nights: int
    resolved: bool
    last_text: str

    @property
    def outstanding(self) -> bool:
        """Still going, as far as anything here knows."""
        return not self.resolved


def _tier_of(flag_id: str, cfg: RedFlagsConfig) -> str:
    if any(r.id == flag_id for r in cfg.tier_a):
        return "A"
    if any(r.id == flag_id for r in cfg.tier_b):
        return "B"
    return "TRACKED"


def detect_symptoms(text: str, config: RedFlagsConfig | None = None) -> dict[str, bool]:
    """Which known symptoms this message mentions, and whether it asserts or denies each.

    Returns flag id to `present`. A phrase that appears only under a negation yields
    False, which is a retraction, not an absence of information.
    """
    cfg = config or load_red_flags()
    neg = cfg.negation_guards.phrases
    window = cfg.negation_guards.window_words
    lowered = (text or "").lower()

    found: dict[str, bool] = {}
    for rule in [*cfg.tier_a, *cfg.tier_b, *cfg.tracked]:
        if matches_symptom(lowered, rule.match, neg, window):
            found[rule.id] = True
            continue
        # Present in the text but negated every time it appears: the person is telling us
        # it has gone. Recorded, because a resolution is the only thing that should let an
        # investigation close as benign, and it has to be distinguishable from silence.
        for phrase in rule.match:
            if phrase.lower() in lowered and is_phrase_negated(
                lowered, phrase.lower(), neg, window
            ):
                found[rule.id] = False
                break
    return found


def record_symptoms(
    conn: sqlite3.Connection,
    subject_id: str,
    text: str,
    night_date: date,
    source_turn_id: str | None = None,
    config: RedFlagsConfig | None = None,
    force_flag_id: str | None = None,
) -> dict[str, bool]:
    """Write what one message says about the person's symptoms, against one night.

    Idempotent per night: saying "still feverish" twice in an evening is one fact about
    that night, not two. A later retraction on the same night wins, because it is the more
    recent thing the person said.
    """
    cfg = config or load_red_flags()
    # `force_flag_id` records a symptom the phrase lists did not match, which is how a
    # tier C finding reaches the timeline. Never used to record an ABSENCE: the model may
    # only add.
    found = {force_flag_id: True} if force_flag_id else detect_symptoms(text, cfg)
    if not found:
        return {}

    now = to_iso(now_utc())
    for flag_id, present in found.items():
        conn.execute(
            """INSERT INTO symptom_observations
                 (subject_id, night_date, flag_id, tier, present, source_turn_id,
                  source_text, recorded_at_utc)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(subject_id, night_date, flag_id) DO UPDATE SET
                 present = excluded.present,
                 source_turn_id = excluded.source_turn_id,
                 source_text = excluded.source_text,
                 recorded_at_utc = excluded.recorded_at_utc""",
            (
                subject_id,
                night_date.isoformat(),
                flag_id,
                _tier_of(flag_id, cfg),
                1 if present else 0,
                source_turn_id,
                text[:2000],
                now,
            ),
        )
    conn.commit()
    return found


def symptom_as_of(conn: sqlite3.Connection, subject_id: str) -> date:
    """The date to judge "still going" against: the latest thing the system knows about.

    NOT the wall clock. A simulation runs nights ahead of today on purpose, and a first
    sync can carry readings whose local date is ahead of the server's. Keyed on
    `local_today()` alone, a symptom recorded against a later night is invisible to every
    rule that reads the timeline, so an outstanding symptom silently stops being
    outstanding. The API's `_record_end` already solves the same problem for the same
    reason: the window ends at the newest night on record, not at the calendar.

    Never earlier than today, so a stale database cannot freeze the clock either.
    """
    row = conn.execute(
        "SELECT MAX(night_date) AS n FROM symptom_observations WHERE subject_id = ?",
        (subject_id,),
    ).fetchone()
    today = local_today()
    if row is None or not row["n"]:
        return today
    try:
        return max(today, date.fromisoformat(str(row["n"])))
    except ValueError:
        return today


def symptom_runs(
    conn: sqlite3.Connection,
    subject_id: str,
    as_of: date,
    config: RedFlagsConfig | None = None,
) -> list[SymptomRun]:
    """Every symptom's current run, most recently mentioned first.

    A run ends when the person retracts the symptom, or when SYMPTOM_RUN_GAP_DAYS pass
    with no mention of it. Both endings are recorded, and neither is inferred from the
    heart rate having settled: a reading returning to normal is evidence about the
    reading. Dengue's critical phase begins as the fever breaks, relative bradycardia
    means an infection can run with an ordinary pulse, and resting heart rate takes weeks
    to months to return to baseline after an infection. Green is not recovered.
    """
    cfg = config or load_red_flags()
    rows = conn.execute(
        """SELECT night_date, flag_id, tier, present, source_text
             FROM symptom_observations
            WHERE subject_id = ? AND night_date <= ?
            ORDER BY flag_id ASC, night_date ASC""",
        (subject_id, as_of.isoformat()),
    ).fetchall()

    by_flag: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        by_flag.setdefault(str(row["flag_id"]), []).append(row)

    runs: list[SymptomRun] = []
    for flag_id, entries in by_flag.items():
        first: date | None = None
        last: date | None = None
        last_text = ""
        resolved = False
        for entry in entries:
            night = date.fromisoformat(str(entry["night_date"]))
            if not entry["present"]:
                # An explicit retraction ends the run outright.
                first = None
                last = None
                resolved = True
                continue
            if first is None or (last is not None and (night - last).days > SYMPTOM_RUN_GAP_DAYS):
                first = night
            last = night
            last_text = str(entry["source_text"] or "")
            resolved = False

        if first is None or last is None:
            continue
        # Gone quiet for longer than the episode-separation window: treat the run as over
        # rather than carrying it forward indefinitely. Not a retraction, so it is not
        # recorded as resolved; it simply stops being outstanding.
        stale = (as_of - last).days > SYMPTOM_RUN_GAP_DAYS
        runs.append(
            SymptomRun(
                flag_id=flag_id,
                tier=_tier_of(flag_id, cfg),
                first_night=first,
                last_night=last,
                nights=(last - first).days + 1,
                resolved=resolved or stale,
                last_text=last_text,
            )
        )

    return sorted(runs, key=lambda r: r.last_night, reverse=True)


def symptom_history(
    conn: sqlite3.Connection,
    subject_id: str,
    as_of: date,
    config: RedFlagsConfig | None = None,
) -> dict[str, int]:
    """How many nights each still-running symptom has been going, for the safety floor.

    This is the argument `check_red_flags_deterministic` has always accepted and never
    once been given. Resolved runs are excluded: a fever the person says has gone must not
    keep accumulating nights towards an escalation.
    """
    return {
        run.flag_id: run.nights
        for run in symptom_runs(conn, subject_id, as_of, config)
        if run.outstanding
    }


def outstanding_symptoms(
    conn: sqlite3.Connection,
    subject_id: str,
    as_of: date,
    config: RedFlagsConfig | None = None,
) -> list[SymptomRun]:
    """Symptoms the person has reported and never said were better."""
    return [run for run in symptom_runs(conn, subject_id, as_of, config) if run.outstanding]


def cooccurring_tier_b(
    conn: sqlite3.Connection,
    subject_id: str,
    as_of: date,
    config: RedFlagsConfig | None = None,
) -> list[str]:
    """Distinct Tier B symptoms reported within the co-occurrence window.

    "Two or more co-occurring" was implemented as "two or more in the same sentence",
    which is not what the word means. A fever on Monday and vomiting on Tuesday co-occur
    in any ordinary reading, and the system scored them as two unrelated singletons and
    did nothing. A person whose symptoms EVOLVE across nights, dizziness then fever then
    stomach pain, is the case this matters most for, and it was the case that produced the
    least response.

    The window is SYMPTOM_COOCCURRENCE_WINDOW_NIGHTS, derived from this file's own
    shortest persist_nights rather than invented.
    """
    cfg = config or load_red_flags()
    tier_b_ids = {r.id for r in cfg.tier_b}
    start = as_of - timedelta(days=SYMPTOM_COOCCURRENCE_WINDOW_NIGHTS - 1)
    rows = conn.execute(
        """SELECT DISTINCT flag_id FROM symptom_observations
            WHERE subject_id = ? AND present = 1
              AND night_date >= ? AND night_date <= ?""",
        (subject_id, start.isoformat(), as_of.isoformat()),
    ).fetchall()
    return sorted(str(r["flag_id"]) for r in rows if str(r["flag_id"]) in tier_b_ids)


def backfill_symptoms(
    conn: sqlite3.Connection,
    subject_id: str,
    config: RedFlagsConfig | None = None,
) -> int:
    """Rebuild the timeline from everything the person has already typed.

    The text was always there; only the reading of it was missing.

    TWO SOURCES, because there are two ways to say something to this system and using
    only one of them loses the more important half. `conversation_turns` holds what was
    typed into the chat. `interactions.free_text` holds what was typed in ANSWER to a
    question the agent asked, which is where a symptom report is most likely to appear:
    the live simulation's only symptom report, "I feel a bit dizzy", was a probe answer
    and appears in no conversation turn at all.

    The person's own words only. What the agent said is not evidence about how they feel.
    """
    cfg = config or load_red_flags()
    rows = conn.execute(
        """SELECT id, text, created_at_utc FROM conversation_turns
            WHERE subject_id = ? AND role = 'user' ORDER BY seq ASC""",
        (subject_id,),
    ).fetchall()

    # The night a message belongs to is a LOCAL date. Taking the UTC date instead put a
    # message typed at 01:41 in Singapore on the previous night, which is the same
    # off-by-one that once made `monitoring_since` treat a night before installation as
    # one the system had been watching.
    tz_row = conn.execute(
        "SELECT timezone FROM subjects WHERE subject_id = ?", (subject_id,)
    ).fetchone()
    tz_name = str(tz_row["timezone"]) if tz_row and tz_row["timezone"] else "Asia/Singapore"

    written = 0
    for row in rows:
        try:
            stamp = from_iso(str(row["created_at_utc"]))
        except (TypeError, ValueError):
            continue
        found = record_symptoms(
            conn,
            subject_id,
            str(row["text"] or ""),
            local_date_of(stamp, tz_name),
            source_turn_id=str(row["id"]),
            config=cfg,
        )
        written += len(found)

    # Answers to questions the agent asked. Dated by when they were ANSWERED, not asked:
    # the night a symptom belongs to is the night the person described, and somebody can
    # answer a question a day after it arrives.
    answers = conn.execute(
        """SELECT i.id AS id, i.free_text AS free_text,
                  COALESCE(i.answered_at_utc, i.asked_at_utc) AS at_utc
             FROM interactions i
             JOIN episodes e ON e.episode_id = i.episode_id
            WHERE e.subject_id = ? AND i.free_text IS NOT NULL AND i.free_text != ''
            ORDER BY at_utc ASC""",
        (subject_id,),
    ).fetchall()
    for row in answers:
        try:
            stamp = from_iso(str(row["at_utc"]))
        except (TypeError, ValueError):
            continue
        found = record_symptoms(
            conn,
            subject_id,
            str(row["free_text"]),
            local_date_of(stamp, tz_name),
            source_turn_id=str(row["id"]),
            config=cfg,
        )
        written += len(found)

    return written


def observe_and_check(
    conn: sqlite3.Connection,
    subject_id: str,
    text: str,
    night_date: date | None = None,
    config: RedFlagsConfig | None = None,
) -> SafetyCheckResult:
    """Record what the person said, then run the floor with their history in hand.

    One function because the ORDER matters and would otherwise be re-derived at every
    call site. Tonight's mention has to be written before the history is read, or a
    symptom's final night is missing from its own count and a run of exactly
    persist_nights + 1 escalates a night late.

    This is the only supported way to run the floor over something a person typed.
    Calling `check_red_flags_with_tier_c` directly with no history is what produced the
    original defect, and it still type-checks, so the guard is this function existing and
    being used rather than a signature that forbids it.
    """
    from wha.safety.tier_c import check_red_flags_with_tier_c

    cfg = config or load_red_flags()
    night = night_date or local_today()
    record_symptoms(conn, subject_id, text, night, config=cfg)
    result = check_red_flags_with_tier_c(
        user_text=text,
        symptom_history=symptom_history(conn, subject_id, night, cfg),
        recent_tier_b=cooccurring_tier_b(conn, subject_id, night, cfg),
        config=cfg,
    )

    # Anything TIER C spotted that the phrase lists missed goes on the timeline too.
    #
    # Found by running the live dengue scenario. "I cannot keep any water down" is not an
    # exact match for "can't keep fluids down", so the deterministic matcher missed it and
    # the model caught it. The escalation was correct, and the symptom was then FORGOTTEN:
    # it counted for tonight and would have counted for nothing tomorrow, because only the
    # matcher wrote to the timeline. That is the same silence-over-time defect this module
    # exists to remove, reintroduced one layer up.
    #
    # Safe in the one direction that matters: tier C is additive only and may never clear a
    # rule, so recording what it found can raise urgency later and can never lower it.
    # `model_flags`, NOT `triggered_flags`. The latter includes flags carried from earlier
    # nights, because that is what the escalation was built on, and writing those back as
    # tonight's report meant a symptom could never expire: every message renewed every
    # symptom still inside the window. In the demo film build, "I feel a lot better today,
    # the fever has gone" was recorded as fever, vomiting and poor intake all PRESENT.
    # Telling the system you had recovered increased your recorded symptom burden.
    known = set(detect_symptoms(text, cfg))
    for flag_id in result.model_flags:
        if flag_id in known:
            continue
        record_symptoms(conn, subject_id, text, night, config=cfg, force_flag_id=flag_id)

    return result
