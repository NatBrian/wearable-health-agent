"""The deterministic half of the system writes down what it did, and what it declined to do.

Audit events were written only by the agent's tool calls and by settings changes, so on a
healthy night the record was empty. A person who had just had a night of sleep measured,
scored and judged opened the page that exists to show them what happened and found nothing
at all, with no way to tell that from the system having done nothing.

The schema always anticipated this: `actor` permits `system` and `monitor`, `operation`
permits `ingest` and `nightly`, and the audit page's own caption already told the reader
that "who" could be the scheduled nightly job. Only the writing was missing.

Two rules keep the record worth reading:

* **Only changes are recorded.** Ingest runs every 30 minutes and night scoring every 3
  hours, mostly redoing identical work. A job that ran and found nothing new writes nothing,
  so the record is a history of what happened to the person rather than a list of cron ticks.
* **Refusals are recorded too.** A stage that declined made a decision about the person.
  Chronos needing five nights and having four, or an elevation that cannot be flagged
  because the baseline is not yet theirs, are the reasons the system looked silent.
"""

import sqlite3
import uuid
from datetime import datetime
from typing import Any

from wha.clock import now_utc
from wha.constants import (
    BASELINE_MIN_NIGHTS_PERSONAL,
    DETECT_PERSISTENCE_NIGHTS,
    DETECT_RED_BPM,
    DETECT_YELLOW_BPM,
    MIN_NOCTURNAL_MINUTES,
)
from wha.db.audit_chain import append_audit
from wha.models import AuditEvent, Baseline, Detection, NightlyFeatures


def _event(subject_id: str, actor: str, operation: str, **kwargs: Any) -> AuditEvent:
    return AuditEvent(
        event_id=f"evt_{uuid.uuid4().hex[:12]}",
        subject_id=subject_id,
        timestamp_utc=now_utc(),
        actor=actor,  # type: ignore[arg-type]
        operation=operation,  # type: ignore[arg-type]
        **kwargs,
    )


def record_ingest(
    conn: sqlite3.Connection,
    subject_id: str,
    stored: int,
    source_kind: str,
    newest_sample_utc: str | None = None,
) -> None:
    """Note that data arrived. Silent unless something NEWER than last time arrived.

    "A check that found nothing new does not appear" is what The record screen tells the
    reader, and it was not true. This stayed quiet only when zero rows were written, and
    re-pulling the same window rewrites the same rows, so a poll every thirty minutes
    produced an entry every thirty minutes. The live log held five entries minutes apart
    all reading "9785 heart rate samples arrived", which buries the tool calls between
    dozens of identical lines.

    Comparing against the newest sample already recorded is what makes the claim true: a
    poll that re-fetched the same window has nothing newer in it and writes nothing.
    """
    if stored <= 0:
        return

    if newest_sample_utc is not None:
        previous = conn.execute(
            """SELECT MAX(json_extract(output_json, '$.newest_sample_utc')) AS latest
                 FROM audit_events
                WHERE subject_id = ? AND operation = 'ingest'""",
            (subject_id,),
        ).fetchone()
        if previous is not None and previous["latest"] and previous["latest"] >= newest_sample_utc:
            return
    append_audit(
        conn,
        _event(
            subject_id,
            "system",
            "ingest",
            input={"source": source_kind},
            output={
                "stored_samples": stored,
                "newest_sample_utc": newest_sample_utc,
                # Callers pass a phrase a person can read ("your watch", "simulated
                # data"), not an identifier. Wrapping it in "the ... source" produced
                # "arrived from the your watch source" on every ingest line of the record.
                "summary": f"{stored} heart rate samples arrived from {source_kind}.",
            },
        ),
    )
    conn.commit()


def _not_flagged_reason(baseline: Baseline, detection: Detection) -> str | None:
    """Why an elevated night did not raise an alert, in the reader's terms."""
    if detection.flagged:
        return None
    if baseline.usable_nights < BASELINE_MIN_NIGHTS_PERSONAL:
        return (
            f"Nothing can be flagged yet: {baseline.usable_nights} of the "
            f"{BASELINE_MIN_NIGHTS_PERSONAL} nights needed before the baseline is yours "
            "rather than a typical adult's."
        )
    if detection.level.value in ("YELLOW", "RED"):
        return (
            f"Raised, but a run of {DETECT_PERSISTENCE_NIGHTS} consecutive RED nights is "
            "required before an investigation opens."
        )
    return "Not raised, so there was nothing to investigate."


def night_reasoning(
    features: NightlyFeatures,
    baseline: Baseline,
    detection: Detection,
) -> dict[str, Any]:
    """The whole chain from what was measured to what was decided, and what was refused.

    Written so the arithmetic can be redone by hand and reach the same answer.
    """
    threshold = (
        f"below {DETECT_YELLOW_BPM} bpm is normal, {DETECT_YELLOW_BPM} to {DETECT_RED_BPM} "
        f"is slightly raised, {DETECT_RED_BPM} or more is clearly raised"
    )
    return {
        "night": features.night_date.isoformat(),
        "measured_over": (
            "the sleep your watch recorded"
            if getattr(features, "rhr_window_source", "clock") == "sleep"
            else "midnight to 7am, because no sleep was recorded"
        ),
        "minutes_measured": features.coverage_minutes,
        "minimum_minutes_required": MIN_NOCTURNAL_MINUTES,
        "usable": features.usable,
        "resting_heart_rate_bpm": features.rhr_bpm,
        "compared_against_bpm": baseline.centre_bpm,
        "baseline_built_from_nights": baseline.usable_nights,
        "baseline_maturity": baseline.rung.value,
        "difference_bpm": detection.deviation_bpm,
        "explained_by_activity_bpm": detection.explained_bpm,
        "explained_by": detection.reasons,
        "left_unexplained_bpm": detection.residual_bpm,
        "thresholds": threshold,
        "level": detection.level.value,
        "flagged": detection.flagged,
        "why_not_flagged": _not_flagged_reason(baseline, detection),
    }


def record_night_scored(
    conn: sqlite3.Connection,
    features: NightlyFeatures,
    baseline: Baseline,
    detection: Detection,
    previous: dict[str, Any] | None,
) -> None:
    """Record a night's reasoning, the first time it is scored and whenever it changes.

    `previous` is the stored detection row as it was before this run, or None if the night
    had never been scored. Re-scoring a night whose result is identical writes nothing:
    night scoring runs every few hours so that a night settles once its sleep has synced,
    and most of those passes reach the same answer.
    """
    reasoning = night_reasoning(features, baseline, detection)

    # "Only on change" exists to stop a job that runs every few hours filling the record
    # with identical entries. It must not stop the FIRST entry for a night: a night that has
    # been scored and has no record at all is exactly the silence this is here to end.
    already_recorded = conn.execute(
        """SELECT 1 FROM audit_events
            WHERE subject_id = ? AND operation = 'nightly'
              AND json_extract(output_json, '$.night') = ?
            LIMIT 1""",
        (features.subject_id, features.night_date.isoformat()),
    ).fetchone()

    if previous is None or already_recorded is None:
        operation_summary = "First scoring of this night."
    else:
        changed = [
            name
            for name, before, after in (
                ("level", previous.get("level"), detection.level.value),
                ("flagged", bool(previous.get("flagged")), detection.flagged),
                ("residual_bpm", previous.get("residual_bpm"), detection.residual_bpm),
            )
            if before != after
        ]
        if not changed:
            return
        operation_summary = (
            "Re-scored after more data arrived. Changed: " + ", ".join(changed) + "."
        )

    reasoning["why_this_entry_exists"] = operation_summary
    reasoning["plain"] = night_narrative(features, baseline, detection, operation_summary)
    append_audit(
        conn,
        _event(
            features.subject_id,
            "monitor",
            "nightly",
            input={
                "night": features.night_date.isoformat(),
                "previous": previous,
            },
            output=reasoning,
        ),
    )
    conn.commit()


def night_narrative(
    features: NightlyFeatures,
    baseline: Baseline,
    detection: Detection,
    why_entry: str,
) -> list[str]:
    """The same reasoning as sentences a person with no medical or technical background reads.

    The structured figures above are what makes the record checkable. This is what makes it
    readable. Both are stored, because a record nobody can understand is not transparency.
    """
    # "%-d" is a platform extension that raises on Windows, so the day is trimmed by hand.
    night = features.night_date.strftime("%d %B %Y").lstrip("0")
    lines: list[str] = []

    if not features.usable or features.rhr_bpm is None:
        lines.append(
            f"On the night of {night} your watch recorded {features.coverage_minutes} minutes "
            f"of sleep. At least {MIN_NOCTURNAL_MINUTES} are needed to measure anything, so "
            "this night was left out rather than guessed at."
        )
        lines.append(why_entry)
        return lines

    source = getattr(features, "rhr_window_source", "clock")
    if source == "sleep":
        lines.append(
            f"On the night of {night} your watch recorded {features.coverage_minutes} minutes "
            "of sleep, and your heart rate was measured over that sleep."
        )
    else:
        lines.append(
            f"On the night of {night} your watch recorded no sleep, so the hours between "
            f"midnight and 7am were used instead, giving {features.coverage_minutes} minutes."
        )

    lines.append(f"Your resting heart rate was {features.rhr_bpm:.0f} beats per minute.")

    if baseline.usable_nights < BASELINE_MIN_NIGHTS_PERSONAL:
        comparison = (
            f"It was compared against {baseline.centre_bpm:.1f}, which is still mostly a "
            f"typical adult rather than you: only {baseline.usable_nights} of your own "
            f"nights have been recorded so far, and {BASELINE_MIN_NIGHTS_PERSONAL} are needed."
        )
    else:
        comparison = (
            f"It was compared against {baseline.centre_bpm:.1f}, which is your own usual, "
            f"worked out from {baseline.usable_nights} of your nights."
        )
    lines.append(comparison)

    if detection.deviation_bpm is not None:
        direction = "above" if detection.deviation_bpm > 0 else "below"
        lines.append(f"That is {abs(detection.deviation_bpm):.1f} beats per minute {direction} it.")

    if detection.explained_bpm:
        lines.append(
            f"Of that, {detection.explained_bpm:.1f} is explained by activity the watch "
            "recorded, such as a workout before bed, so it was subtracted before judging."
        )

    if detection.residual_bpm is not None:
        # A signed number reads badly to someone who is simply below their usual, which is
        # most nights for most people. Only a rise is measured against the thresholds.
        if detection.residual_bpm > 0:
            lines.append(
                f"That leaves {detection.residual_bpm:.1f} above your usual once activity is "
                f"accounted for. Under {DETECT_YELLOW_BPM:.0f} is normal, "
                f"{DETECT_YELLOW_BPM:.0f} to {DETECT_RED_BPM:.0f} is slightly raised, and "
                f"{DETECT_RED_BPM:.0f} or more is clearly raised."
            )
        else:
            lines.append(
                f"Your heart rate was below your usual, not above it, so none of the "
                f"thresholds for a raised night applied. A rise of {DETECT_YELLOW_BPM:.0f} "
                f"or more is what this system looks for."
            )

    verdict = {
        "GREEN": "This night was normal.",
        "YELLOW": "This night was slightly raised.",
        "RED": "This night was clearly raised.",
        "NA": "This night could not be judged.",
    }.get(detection.level.value, "This night could not be judged.")
    lines.append(verdict)

    reason = _not_flagged_reason(baseline, detection)
    if detection.flagged:
        lines.append("An investigation was opened, because a raised run has now persisted.")
    elif reason:
        lines.append(reason)

    lines.append(why_entry)
    return lines


def record_conversation_turn(
    conn: sqlite3.Connection,
    subject_id: str,
    user_text: str,
    reply_text: str,
    urgency: str | None,
    triggered_flags: list[str],
    citations: int,
    uncited: int,
    rule_id: str | None = None,
    score: int | None = None,
    gate_triggered: str | None = None,
) -> None:
    """Put the conversation in the tamper-evident record.

    The record screen says "everything this system does is written down as it happens". After
    the conversation was added it recorded ingest, night scoring and the agent's tool calls
    and nothing else, so the exchange in which a person described chest pain and was routed
    to a doctor left no trace on the page whose entire purpose is to be checkable.

    The person's own words are recorded, because a rule fired on them and the record has to
    show what it fired on. Retrieved passages are not: they are in the episode's citations
    and would bury the entries that matter.
    """
    if urgency:
        narrative = (
            f"You wrote to the system, and a fixed rule set the urgency to {urgency}. "
            "That decision was made by the rule, not by the AI, and the AI cannot lower it."
        )
    elif triggered_flags:
        narrative = (
            "You wrote to the system. A safety rule matched what you said and the system "
            "started asking the questions a published decision rule needs before it can "
            "say how urgent this is."
        )
    else:
        narrative = "You wrote to the system and it answered."

    if uncited:
        narrative += (
            f" {uncited} sentence(s) in the reply came from the AI's own knowledge with no "
            "source behind them, and were labelled as such."
        )

    append_audit(
        conn,
        _event(
            subject_id,
            "human",
            "chat",
            input={"message": user_text},
            output={
                "reply": reply_text,
                "urgency": urgency,
                "triggered_flags": triggered_flags,
                "decision_rule": rule_id,
                "rule_score": score,
                "unconditional_gate": gate_triggered,
                "cited_claims": citations,
                "uncited_statements": uncited,
                "summary": narrative,
            },
            safety_event="red_flag_conversation" if triggered_flags else "none",
        ),
    )
    conn.commit()


def review_requested_at(conn: sqlite3.Connection, episode_id: str) -> datetime | None:
    """When this episode first asked a person to review its draft, if it ever did.

    Read from the audit log rather than a column on the episode, because the log already
    reserves the `human_decision` operation for exactly this and nothing had ever written
    one. It is also the honest place for it: whether a person reviewed a conclusion about
    their own health belongs in the record they can check, not only in a status field.
    """
    row = conn.execute(
        """SELECT MIN(timestamp_utc) AS first_asked FROM audit_events
            WHERE episode_id = ? AND operation = 'human_decision'
              AND human_decision IS NULL""",
        (episode_id,),
    ).fetchone()
    if row is None or not row["first_asked"]:
        return None
    return datetime.fromisoformat(row["first_asked"])


def record_review_requested(
    conn: sqlite3.Connection,
    subject_id: str,
    episode_id: str,
    disposition: str,
) -> None:
    """Record that the system paused and asked a person to check its conclusion.

    Written once per episode. `node_review` re-runs in full whenever the interrupt it
    parks on is resumed, so writing unconditionally would add an identical row on every
    tick and bury the decision that follows it.
    """
    if review_requested_at(conn, episode_id) is not None:
        return

    append_audit(
        conn,
        _event(
            subject_id,
            "agent",
            "human_decision",
            episode_id=episode_id,
            permission_decision="required_approval",
            output={
                "draft_disposition": disposition,
                "summary": (
                    "The system drafted a conclusion and stopped, because a person is "
                    "meant to check it before it is recorded. Nothing is closed until "
                    "you approve, edit, reject or escalate it."
                ),
            },
        ),
    )
    conn.commit()


def record_review_decision(
    conn: sqlite3.Connection,
    subject_id: str,
    episode_id: str,
    decision: str,
    rationale: str | None = None,
    reviewed_by_person: bool = True,
) -> None:
    """Record how the review ended, and whether a person was actually involved.

    A background job used to answer "approve" fifteen minutes later and the record then
    showed a human decision that never happened. That is worse than having no checkpoint,
    so an unreviewed close is recorded as `closed_unreviewed` by the `system` actor and is
    never called an approval.
    """
    append_audit(
        conn,
        _event(
            subject_id,
            "human" if reviewed_by_person else "system",
            "human_decision",
            episode_id=episode_id,
            human_decision=decision,
            human_decision_rationale=rationale,
            permission_decision="allowed" if reviewed_by_person else "required_approval",
            output={
                "summary": (
                    f"You reviewed the draft and chose to {decision} it."
                    if reviewed_by_person
                    else (
                        "Nobody reviewed this draft within the time allowed, so it was "
                        "closed unreviewed. It was not approved."
                    )
                ),
            },
        ),
    )
    conn.commit()


def record_policy_decision(
    conn: sqlite3.Connection,
    subject_id: str,
    episode_id: str,
    action_kind: str,
    rationale: str,
    chosen_probe: str | None,
    chosen_value: float | None,
    interruption_cost: float | None,
    candidates: list[tuple[str, float]] | None,
) -> None:
    """Write down what the policy decided, and what it scored to decide it.

    The decision to stay quiet left no trace anywhere. An episode that asked a question
    recorded it in `interactions`, along with the probes it rejected, but an episode that
    decided asking was not worth the interruption recorded nothing at all, so the screen
    could not say why the system had gone quiet and neither could anybody reading the
    record afterwards.

    That is the one decision in this system a person is most likely to want explained: it
    is the difference between being interrupted and not.
    """
    candidate_rows = [
        {"probe_id": probe_id, "value_of_asking": round(float(value), 4)}
        for probe_id, value in (candidates or [])
    ]
    append_audit(
        conn,
        _event(
            subject_id,
            "agent",
            # `operation` is a closed list. "plan" is the value the schema reserves for
            # deciding what to do next, which is exactly what this is.
            "plan",
            episode_id=episode_id,
            output={
                "action": action_kind,
                "rationale": rationale,
                "chosen_probe": chosen_probe,
                "value_of_asking": round(float(chosen_value), 4)
                if chosen_value is not None
                else None,
                "interruption_cost": round(float(interruption_cost), 4)
                if interruption_cost is not None
                else None,
                "candidates": candidate_rows,
                "summary": (
                    f"The policy chose {action_kind}. "
                    + (
                        f"Asking about {chosen_probe} was worth "
                        f"{chosen_value:.3f} against a cost of {interruption_cost:.3f}."
                        if chosen_probe
                        and chosen_value is not None
                        and interruption_cost is not None
                        else "No question scored above the cost of interrupting."
                    )
                ),
            },
        ),
    )
    conn.commit()


def record_data_safety_escalation(
    conn: sqlite3.Connection,
    subject_id: str,
    episode_id: str,
    detection: Detection,
    result: Any,
) -> None:
    """Record a safety rule that fired on the DATA rather than on what the person said.

    Every escalation this system had ever raised came from free text. These three rules
    read the night itself, and until they were connected the audit trail could never show a
    person a decision made about them that they had not triggered by typing something.
    """
    append_audit(
        conn,
        _event(
            subject_id,
            "system",
            "nightly",
            episode_id=episode_id,
            output={
                "night": detection.night_date.isoformat(),
                "level": detection.level.value,
                "robust_z": detection.robust_z,
                "residual_bpm": detection.residual_bpm,
                "triggered_flags": list(result.triggered_flags),
                "urgency": result.level,
                "guidance": list(result.guidance),
                "summary": (
                    "A fixed rule read the night itself and raised this, without you "
                    "having reported anything. " + (result.reason or "")
                ),
            },
            safety_event="red_flag_vitals",
        ),
    )
    conn.commit()


def record_notification_sent(
    conn: sqlite3.Connection,
    subject_id: str,
    episode_id: str | None,
    kind: str,
    channel: str,
    text: str,
) -> None:
    """Record that something was sent to the person's phone.

    `notify` is one of the ten operations the contract reserves and nothing had ever
    written one, so the record could not show that a question reached anybody. The
    `notifications` table knew, but the screen reads the audit chain, and that screen is
    the one that claims everything this system does is written down.

    The message text is recorded. It is what the person received, it is the system's own
    words rather than theirs, and a record of "a notification was sent" that does not say
    what it said is not much of a record.
    """
    append_audit(
        conn,
        _event(
            subject_id,
            "system",
            "notify",
            episode_id=episode_id,
            output={
                "kind": kind,
                "channel": channel,
                "text": text,
                "summary": f"A {kind.lower()} was sent to your {channel}.",
            },
        ),
    )
    conn.commit()


def record_urgency_acknowledged(
    conn: sqlite3.Connection,
    subject_id: str,
    urgency: str,
    set_on: str | None,
) -> None:
    """Record that the person says they have seen somebody about an urgency.

    This is the only thing that clears the banner, and clearing a red banner belongs on
    the record as much as raising one does. It does not lower the urgency: the ratchet in
    `established_urgency` is unchanged and History still shows it.
    """
    append_audit(
        conn,
        _event(
            subject_id,
            "human",
            "human_decision",
            human_decision="urgency_acknowledged",
            human_decision_rationale=f"Seen about a {urgency} urgency set on {set_on}.",
            permission_decision="allowed",
            output={
                "urgency": urgency,
                "set_on": set_on,
                "summary": (
                    "You said you have seen somebody about this, so the banner stops "
                    "showing. The urgency itself is not removed and it stays in your "
                    "history, because this system has no way to know what a clinician "
                    "found."
                ),
            },
        ),
    )
    conn.commit()
