"""One night's journey, assembled from what was stored rather than re-run.

The deterministic half of this system leaves its working behind in four tables:
`heart_rate_samples`, `nightly_features`, `baselines` and `detections`. Nothing before this
module put those together and told the story of a single night, so an interface could
explain an investigation and could not explain the sixty-eight nights out of seventy-two
where no investigation happened. Those are the nights a person actually looks at.

Nothing here recalculates a result. Every figure is read from the row the deterministic
half wrote, so this module cannot disagree with the detector. Where a row records when it
was computed, that time is reported; where none was recorded, none is reported. A
plausible clock time is exactly the kind of invented figure this project refuses to add,
and `StepStatus.UNRECORDED` exists so that "we did not write it down" never has to be
dressed up as "it did not run".

The one thing this module does compute is the sleep window, through the same resolver the
features step used. That is a read of the same stored sleep stages rather than a second
opinion, and where its answer disagrees with the `rhr_window_source` stored on the night,
the stored value wins and the disagreement is reported.
"""

import json
import sqlite3
from datetime import UTC, date, datetime, timedelta

from wha.agent.steps import PRELOAD_TOOLS, pipeline_steps_that_ran
from wha.clock import local_today
from wha.db import connect
from wha.db.migrations import apply_schema
from wha.models import (
    CANONICAL_PIPELINE_STEPS,
    BaselineRung,
    CauseId,
    DetectionLevel,
    NightPipeline,
    PipelineHeadline,
    PipelineNightRef,
    PipelineStepView,
    StepLayer,
    StepStatus,
)
from wha.service.nights import get_night_detail, list_nights

# How long after a night a data pull can still be the one that carried it. Watch data is
# pulled every thirty minutes, so the pull covering a night lands within hours of it; a
# day of slack covers a phone that was off overnight without reaching into next week.
_INGEST_GRACE = timedelta(days=1)


def _subject_timezone(conn: sqlite3.Connection, subject_id: str) -> str:
    row = conn.execute(
        "SELECT timezone FROM subjects WHERE subject_id = ?", (subject_id,)
    ).fetchone()
    if row is not None and row["timezone"]:
        return str(row["timezone"])

    from wha.config import get_settings

    return get_settings().timezone


def _moment(value: object) -> datetime | None:
    """A stored timestamp, or nothing. Never a substitute for a missing one."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _step(
    step_id: str,
    status: StepStatus,
    reason: str,
    **kwargs: object,
) -> PipelineStepView:
    """Build one step, taking its ordinal and layer from the canonical list.

    Position and layer are properties of the pipeline, not of a night, so a caller cannot
    place a step out of order or colour it as the wrong kind of machine.
    """
    definition = next(s for s in CANONICAL_PIPELINE_STEPS if s.step_id == step_id)
    return PipelineStepView(
        step_id=definition.step_id,
        ordinal=definition.ordinal,
        layer=definition.layer,
        status=status,
        reason=reason,
        **kwargs,  # type: ignore[arg-type]
    )


def _collect_step(
    conn: sqlite3.Connection,
    subject_id: str,
    window_start: datetime,
    window_end: datetime,
) -> PipelineStepView:
    """Did the phone hand over data covering this night, and when.

    Ingest records itself only when something newer than last time arrived, because a poll
    every thirty minutes that re-fetches the same window would otherwise fill the record
    with cron ticks. So a night with no ingest event is not a night with no data: it is a
    night whose data arrived inside a pull recorded against another night, or before the
    system started writing these events at all. The step says that rather than implying
    the watch was silent.
    """
    horizon = (window_end + _INGEST_GRACE).isoformat()
    event = conn.execute(
        """SELECT timestamp_utc FROM audit_events
           WHERE subject_id = ? AND operation = 'ingest'
             AND timestamp_utc >= ? AND timestamp_utc <= ?
           ORDER BY timestamp_utc ASC LIMIT 1""",
        (subject_id, window_start.isoformat(), horizon),
    ).fetchone()

    payload = conn.execute(
        """SELECT fetched_at_utc, source_kind FROM raw_payloads
           WHERE subject_id = ? AND fetched_at_utc >= ? AND fetched_at_utc <= ?
           ORDER BY fetched_at_utc ASC LIMIT 1""",
        (subject_id, window_start.isoformat(), horizon),
    ).fetchone()

    if event is None and payload is None:
        return _step(
            "collect",
            StepStatus.UNRECORDED,
            "No data pull covering this night was written down. That does not mean none "
            "happened: a pull that finds nothing new is not recorded.",
        )

    occurred = _moment(event["timestamp_utc"] if event is not None else None) or _moment(
        payload["fetched_at_utc"] if payload is not None else None
    )
    outputs: dict[str, object] = {}
    if payload is not None:
        outputs["source"] = payload["source_kind"]

    return _step(
        "collect",
        StepStatus.RAN,
        "Your phone was asked for the readings your watch had recorded, and it sent them.",
        occurred_utc=occurred,
        outputs=outputs,
    )


def _store_step(
    conn: sqlite3.Connection,
    subject_id: str,
    window_start: datetime,
    window_end: datetime,
) -> PipelineStepView:
    """How much the watch actually recorded across the window this night was measured over."""
    samples = conn.execute(
        """SELECT COUNT(*) AS n FROM heart_rate_samples
           WHERE subject_id = ? AND ts_utc >= ? AND ts_utc < ?""",
        (subject_id, window_start.isoformat(), window_end.isoformat()),
    ).fetchone()["n"]

    stages = conn.execute(
        """SELECT COUNT(*) AS n FROM sleep_stages
           WHERE subject_id = ? AND end_utc > ? AND start_utc < ?""",
        (subject_id, window_start.isoformat(), window_end.isoformat()),
    ).fetchone()["n"]

    if samples == 0:
        return _step(
            "store",
            StepStatus.SKIPPED,
            "Your watch recorded no heart rate across this night, so there was nothing to store.",
            outputs={"heart_rate_samples": 0, "sleep_stage_rows": stages},
        )

    return _step(
        "store",
        StepStatus.RAN,
        "The readings were stored exactly as they arrived. Nothing is edited or "
        "smoothed at this point.",
        headline_figure=f"{samples} readings",
        outputs={"heart_rate_samples": samples, "sleep_stage_rows": stages},
    )


def _sleep_window_step(
    conn: sqlite3.Connection,
    subject_id: str,
    night_date: date,
    tz_name: str,
    stored_source: str | None,
) -> PipelineStepView:
    """Which stretch of time the night's reading was taken over, and where that came from.

    The window is resolved through the same code the features step used, but the authority
    on what actually happened is `nightly_features.rhr_window_source`. Where the two
    disagree, the stored value is reported and the disagreement is stated: sleep stages
    can arrive after a night was scored, and a screen that quietly re-derives would show a
    window the reading was never taken over.
    """
    from wha.features.sleep_window import resolve_sleep_window

    window = resolve_sleep_window(conn, subject_id, night_date, tz_name)
    source = stored_source or window.source

    outputs: dict[str, object] = {
        "window_source": source,
        "start_utc": window.start_utc.isoformat(),
        "end_utc": window.end_utc.isoformat(),
        "asleep_minutes": round(window.asleep_minutes, 1),
    }
    if stored_source is not None and stored_source != window.source:
        outputs["disagreement"] = (
            f"This night was measured over the {stored_source} window. Re-reading the "
            f"stored sleep now gives {window.source}, which means sleep data arrived "
            "after the night was scored."
        )

    if source == "sleep":
        reason = (
            "Your watch recorded when you slept, so the reading was taken over your "
            "actual sleep, with the waking spells inside it left out."
        )
    else:
        reason = (
            "Your watch recorded no sleep for this night, so the reading was taken over "
            "midnight to 7am local time instead."
        )

    if stored_source is None:
        return _step(
            "sleep_window",
            StepStatus.SKIPPED,
            "No reading was taken for this night, so no window was needed.",
            outputs=outputs,
        )

    return _step(
        "sleep_window",
        StepStatus.RAN,
        reason,
        headline_figure=f"{window.asleep_minutes / 60:.1f} h measured",
        outputs=outputs,
    )


def _features_step(conn: sqlite3.Connection, subject_id: str, night_date: date) -> PipelineStepView:
    """The one number a whole night is reduced to, and when it was worked out."""
    row = conn.execute(
        "SELECT * FROM nightly_features WHERE subject_id = ? AND night_date = ?",
        (subject_id, night_date.isoformat()),
    ).fetchone()

    if row is None:
        return _step(
            "features",
            StepStatus.SKIPPED,
            "There was no reading for this night, so nothing was worked out from it.",
        )

    outputs = {
        "rhr_bpm": row["rhr_bpm"],
        "coverage_minutes": row["coverage_minutes"],
        "sleep_hours": row["sleep_hours"],
        "usable": bool(row["usable"]),
        "implausible_dropped": row["implausible_dropped"],
    }
    occurred = _moment(row["computed_at_utc"])

    if row["rhr_bpm"] is None:
        return _step(
            "features",
            StepStatus.RAN,
            "Too little of the night was measured to take a resting heart rate from it.",
            occurred_utc=occurred,
            outputs=outputs,
        )

    return _step(
        "features",
        StepStatus.RAN,
        "The middle value of your heart rate across the window was taken as your "
        "resting heart rate for the night. The middle value is used rather than the "
        "average so that a few odd readings cannot drag it.",
        headline_figure=f"{row['rhr_bpm']:.0f} bpm",
        occurred_utc=occurred,
        outputs=outputs,
    )


def _baseline_step(conn: sqlite3.Connection, subject_id: str, night_date: date) -> PipelineStepView:
    """What normal means for this person, on this night."""
    row = conn.execute(
        "SELECT * FROM baselines WHERE subject_id = ? AND night_date = ?",
        (subject_id, night_date.isoformat()),
    ).fetchone()

    if row is None:
        return _step(
            "baseline",
            StepStatus.SKIPPED,
            "Your normal was not worked out for this night, which happens when the night "
            "had no reading of its own.",
        )

    return _step(
        "baseline",
        StepStatus.RAN,
        "Your own middle value over the previous nights, with a band around it for how "
        "much you vary from night to night. This is your normal, not anybody else's.",
        headline_figure=f"{row['centre_bpm']:.0f} bpm",
        outputs={
            "centre_bpm": row["centre_bpm"],
            "scale_bpm": row["scale_bpm"],
            "usable_nights": row["usable_nights"],
            "rung": row["rung"],
            "shrink_weight": row["shrink_weight"],
        },
    )


def _detection_row(
    conn: sqlite3.Connection, subject_id: str, night_date: date
) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM detections WHERE subject_id = ? AND night_date = ?",
        (subject_id, night_date.isoformat()),
    ).fetchone()


def _subtract_step(detection: sqlite3.Row | None) -> PipelineStepView:
    """Anything about the night that already has an explanation is taken off first."""
    if detection is None:
        return _step(
            "subtract_explained",
            StepStatus.SKIPPED,
            "Nothing was compared for this night, so there was nothing to subtract from.",
        )

    explained = detection["explained_bpm"] or 0.0
    if not explained:
        return _step(
            "subtract_explained",
            StepStatus.NOT_APPLICABLE,
            "Nothing to subtract: no evening workout was recorded for this night.",
            outputs={"explained_bpm": 0.0},
        )

    return _step(
        "subtract_explained",
        StepStatus.RAN,
        "A recorded evening workout raises resting heart rate for a while afterwards. "
        "That much was taken off before anything was judged, so exercise is not mistaken "
        "for illness.",
        headline_figure=f"-{explained:.1f} bpm",
        outputs={"explained_bpm": explained, "residual_bpm": detection["residual_bpm"]},
    )


def _detect_step(detection: sqlite3.Row | None) -> PipelineStepView:
    """Green, yellow or red, and whether that was enough to look into."""
    if detection is None:
        return _step(
            "detect",
            StepStatus.SKIPPED,
            "This night was never compared against your normal, which happens when it "
            "had no usable reading.",
        )

    reasons = json.loads(detection["reasons_json"]) if detection["reasons_json"] else []
    level = detection["level"]
    flagged = bool(detection["flagged"])

    if level == "NA":
        reason = "There was not enough of this night measured to judge it either way."
    elif flagged:
        reason = (
            "This night was clearly above your own normal, and so was the night before it. "
            "Two clearly raised nights in a row is the bar for looking into something, so "
            "an investigation was opened. Opening one is the only thing this step decides."
        )
    elif level == "RED":
        # Saying only "did not meet the bar" here is what made a red night read as an
        # unexplained warning: it WAS far enough above, and the reader could not tell why
        # nothing happened.
        reason = (
            "This night was clearly above your own normal. On its own that opens nothing: "
            "it takes two clearly raised nights in a row, and the night before this one "
            "was not at that level. Single raised nights are common and mostly have "
            "ordinary causes."
        )
    elif level == "YELLOW":
        reason = (
            "This night was somewhat above your own normal, which is below the level that "
            "can open anything. A night at this level never opens an investigation, "
            "however many of them there are."
        )
    else:
        reason = "This night sat inside your own usual range, so there was nothing to look into."

    return _step(
        "detect",
        StepStatus.RAN,
        reason,
        headline_figure=level,
        outputs={
            "level": level,
            "flagged": flagged,
            "deviation_bpm": detection["deviation_bpm"],
            "residual_bpm": detection["residual_bpm"],
            "robust_z": detection["robust_z"],
            "reasons": reasons,
        },
    )


# ------------------------------------------------------------------ the agentic half


# What each agent node did, said for somebody who has never seen this system. The node
# names are the graph's own, and the descriptions live here rather than in a screen so the
# API carries them and a second interface cannot describe the same node differently.
_AGENT_STEP_REASONS: dict[str, str] = {
    "preload": (
        "Five fixed readings were fetched before the model was allowed to do anything: "
        "your night, your normal, your recent nights, how complete the data was, and what "
        "was already known about this run."
    ),
    "investigate": (
        "The model chose which of its permitted tools to call, and called them in a loop, "
        "to gather what it needed. It can only call tools on this list, and it cannot "
        "reach anything else."
    ),
    "believe": (
        "Twelve possible causes were weighed against each other by exact arithmetic over "
        "every combination of them. This is not the model guessing: it is Bayes' rule, and "
        "it gives the same answer every time for the same evidence."
    ),
    "decide": (
        "Worked out whether asking you a question would change what happens next by "
        "enough to be worth interrupting you. If not, it stays quiet."
    ),
    "ask": (
        "The model put the chosen question into words and the investigation paused there "
        "until you replied."
    ),
    "conclude": (
        "A draft conclusion was written, and any sentence that did not quote a real "
        "passage was removed before you could see it."
    ),
    "critique": (
        "The model read its own draft and could only remove claims from it, never add them."
    ),
    "review": ("The draft waited for a person to approve, edit, reject or escalate it."),
    "deliver": (
        "The conclusion was saved to your record, this dashboard and the tamper-evident log."
    ),
}

_AGENT_SKIPPED_REASONS: dict[str, str] = {
    "ask": "No question was worth its interruption, so none was asked.",
    "review": "This investigation has not reached the review checkpoint.",
    "critique": "The draft has not been written yet, so there was nothing to critique.",
    "conclude": "This investigation has not drafted a conclusion yet.",
}


def _safety_floor_step(
    conn: sqlite3.Connection,
    subject_id: str,
    night_date: date,
) -> PipelineStepView:
    """What the person said, how long they have been saying it, and what the rules made of it.

    This layer ran before the agent from the beginning and was on no list, so the one
    screen that claims to show every step showed everything except the layer that can
    override every other layer.

    It is also where the two rules live that a person most needs to see, because they are
    the ones that decide whether anybody is told anything: a symptom that persists beyond
    its own window, and two symptoms that turn up within a few nights of each other. Both
    were unreachable until 7 September 2026, and both are stated here in nights and names
    rather than as a verdict.
    """
    from wha.constants import SYMPTOM_COOCCURRENCE_WINDOW_NIGHTS
    from wha.safety.rules import load_red_flags
    from wha.service.phrasing import symptom_label
    from wha.service.symptoms import cooccurring_tier_b, symptom_runs

    try:
        runs = symptom_runs(conn, subject_id, night_date)
        cooccurring = cooccurring_tier_b(conn, subject_id, night_date)
        windows = {rule.id: rule.persist_nights for rule in load_red_flags().tier_b}
    except Exception:  # noqa: BLE001
        return _step(
            "safety_floor",
            StepStatus.UNRECORDED,
            "The symptom record could not be read for this night.",
        )

    if not runs:
        return _step(
            "safety_floor",
            StepStatus.NOT_APPLICABLE,
            (
                "You had not told the system about any symptoms by this night, so there "
                "was nothing here for the rules to read. The rules that judge your "
                "readings still ran."
            ),
        )

    # The human words come from HERE, not from the screen. The dashboard is a client of
    # this API and holds no content of its own, so a symptom added to red_flags.yaml must
    # reach a page without anybody editing the page.
    reported = [
        {
            "symptom": symptom_label(run.flag_id),
            "symptom_id": run.flag_id,
            "nights_so_far": run.nights,
            "first_reported": run.first_night.isoformat(),
            "last_reported": run.last_night.isoformat(),
            "still_going": run.outstanding,
            "escalates_after_nights": windows.get(run.flag_id),
            "your_words": run.last_text[:200],
        }
        for run in runs
    ]

    persisted = [
        entry["symptom"]
        for entry in reported
        if entry["escalates_after_nights"] is not None
        and entry["still_going"]
        and entry["nights_so_far"] > entry["escalates_after_nights"]
    ]

    if persisted:
        reason = (
            f"{_join_words(persisted)} had been going on longer than the number of "
            "nights this system waits before saying something, so it raised it."
        )
    elif len(cooccurring) >= 2:
        reason = (
            f"{_join_words([symptom_label(f) for f in cooccurring])} were both reported within "
            f"{SYMPTOM_COOCCURRENCE_WINDOW_NIGHTS} nights of each other, and two of these "
            "together is enough to raise it."
        )
    else:
        reason = (
            f"{len(reported)} symptom{'s' if len(reported) != 1 else ''} on record. None "
            "had gone on long enough on its own, and no two of them fell close enough "
            "together, so nothing was raised by this step on this night."
        )

    return _step(
        "safety_floor",
        StepStatus.RAN,
        reason,
        inputs={
            "cooccurrence_window_nights": SYMPTOM_COOCCURRENCE_WINDOW_NIGHTS,
            "persistence_windows": windows,
        },
        outputs={
            "reported_symptoms": reported,
            "persisted_beyond_window": persisted,
            "co_occurring_within_window": [symptom_label(f) for f in cooccurring],
            "raised_something": bool(persisted or len(cooccurring) >= 2),
        },
    )


def _join_words(names: list[str]) -> str:
    """Names joined into a phrase a person would read aloud."""
    if len(names) == 1:
        return names[0].capitalize()
    return (", ".join(names[:-1]) + " and " + names[-1]).capitalize()


def _episode_row(conn: sqlite3.Connection, episode_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM episodes WHERE episode_id = ?", (episode_id,)).fetchone()


def _episode_open_step(
    conn: sqlite3.Connection,
    episode_id: str | None,
    detection: sqlite3.Row | None,
) -> PipelineStepView:
    """Whether this night opened an investigation, and why it did not when it did not."""
    flagged = bool(detection["flagged"]) if detection is not None else False

    if episode_id is None and not flagged:
        level = str(detection["level"]) if detection is not None else "NA"
        if level == "RED":
            why = (
                "This night was clearly raised, but a second clearly raised night in a row "
                "is what opens an investigation, and there was not one."
            )
        elif level == "YELLOW":
            why = (
                "This night was only somewhat raised, which is below the level that can "
                "open an investigation at all."
            )
        elif level == "NA":
            why = "This night could not be judged, so there was nothing to look into."
        else:
            why = "This night sat inside your usual range."
        return _step(
            "episode_open",
            StepStatus.NOT_APPLICABLE,
            f"{why} No investigation was opened, so nothing below this point ran.",
        )

    if episode_id is None and flagged:
        # The detector flagged and no episode exists. That is a real fault rather than a
        # quiet night, and smoothing it over would hide the one case worth seeing.
        return _step(
            "episode_open",
            StepStatus.UNRECORDED,
            "This night was flagged, and no investigation is recorded against it. That "
            "is a gap in the record rather than a decision the system made.",
        )

    row = _episode_row(conn, episode_id or "")
    if row is None:
        return _step(
            "episode_open",
            StepStatus.UNRECORDED,
            "An investigation is referenced for this night and its record cannot be found.",
        )

    return _step(
        "episode_open",
        StepStatus.RAN,
        "An investigation was opened. Only one is ever open at a time, so a run of raised "
        "nights is looked at as one thing rather than as several.",
        headline_figure=str(row["episode_id"]),
        outputs={
            "episode_id": row["episode_id"],
            "state": row["state"],
            "opened_on": row["opened_on"],
            "disposition": row["disposition"],
            "tool_call_count": row["tool_call_count"],
        },
    )


def _agent_steps(
    conn: sqlite3.Connection,
    episode_id: str | None,
    detection: sqlite3.Row | None,
) -> list[PipelineStepView]:
    """Steps 9 to 18, from the trace the graph wrote, or an honest gap where it did not."""
    ids = [
        s.step_id
        for s in CANONICAL_PIPELINE_STEPS
        if s.layer in {StepLayer.AGENTIC, StepLayer.USER} and s.step_id != "episode_open"
    ]

    if episode_id is None:
        flagged = bool(detection["flagged"]) if detection is not None else False
        status = StepStatus.UNRECORDED if flagged else StepStatus.NOT_APPLICABLE
        reason = (
            "No investigation is recorded for this night, so what the agent did cannot be shown."
            if flagged
            else "This runs only when a night is worth looking into, and this one was not."
        )
        return [_step(step_id, status, reason) for step_id in ids]

    trace = _episode_trace(conn, episode_id)
    closed = bool(
        conn.execute(
            "SELECT 1 FROM episodes WHERE episode_id = ? AND state = 'CLOSED'", (episode_id,)
        ).fetchone()
    )
    if not trace:
        # The agent writes its trace when it concludes, so an investigation still running
        # has none. Reporting every step as unrecorded then said "this ran before the
        # system recorded which steps it took" about work that was happening at that
        # moment, with the beliefs, tool calls and questions behind it sitting in the same
        # database. The trace is a convenience, not the only evidence: where it is absent,
        # the steps are read from what each one leaves behind, exactly as the deterministic
        # half already is.
        ran = pipeline_steps_that_ran(_agent_steps_from_evidence(conn, episode_id))
    else:
        ran = pipeline_steps_that_ran(trace.get("nodes_ran", []))
    interactions = conn.execute(
        "SELECT * FROM interactions WHERE episode_id = ? ORDER BY asked_at_utc",
        (episode_id,),
    ).fetchall()
    belief = conn.execute(
        """SELECT marginals_json, p_illness, ts_utc FROM beliefs
           WHERE episode_id = ? ORDER BY seq DESC LIMIT 1""",
        (episode_id,),
    ).fetchone()

    steps: list[PipelineStepView] = []
    for step_id in ids:
        if step_id == "answer":
            steps.append(_answer_step(interactions))
            continue
        if step_id == "deliver":
            steps.append(_deliver_step(conn, episode_id))
            continue
        if step_id not in ran:
            # An investigation that is still going has not reached its later steps yet.
            # Saying it "did not run" reads as a decision the system made, when the truth
            # is that it has not got there.
            if not trace and not closed:
                steps.append(
                    _step(
                        step_id,
                        StepStatus.SKIPPED,
                        "This investigation is still going and has not reached this step yet.",
                    )
                )
            elif not trace:
                # Finished, wrote no trace, and left nothing else behind either. This is
                # the one case where the honest answer is that we do not know.
                steps.append(
                    _step(
                        step_id,
                        StepStatus.UNRECORDED,
                        "This investigation finished without recording what this step did, "
                        "and it left nothing else to read. That is a gap in the record, not "
                        "a claim that the step was skipped.",
                    )
                )
            else:
                steps.append(
                    _step(
                        step_id,
                        StepStatus.SKIPPED,
                        _AGENT_SKIPPED_REASONS.get(
                            step_id, "This step was not needed for this investigation."
                        ),
                    )
                )
            continue

        outputs: dict[str, object] = {}
        headline: str | None = None
        occurred: datetime | None = None

        if step_id == "investigate":
            calls = trace.get("tool_calls", []) or []
            outputs = {"tool_calls": calls, "tool_call_count": trace.get("tool_call_count", 0)}
            headline = f"{len(calls)} tool calls"
        elif step_id == "believe" and belief is not None:
            marginals = json.loads(belief["marginals_json"])
            top = max(marginals.items(), key=lambda item: item[1]) if marginals else None
            outputs = {
                "marginals": marginals,
                "p_illness": belief["p_illness"],
                "top_cause": top[0] if top else None,
                "top_probability": top[1] if top else None,
            }
            headline = f"{top[0].replace('_', ' ')} {top[1]:.0%}" if top else None
            occurred = _moment(belief["ts_utc"])
        elif step_id == "decide":
            outputs = _decision_outputs(conn, episode_id, interactions)
            action = outputs.get("action")
            if action == "ASK" and outputs.get("value_of_asking") is not None:
                headline = f"asked, worth {outputs['value_of_asking']:.3f}"
            elif action:
                headline = str(action).lower()
        elif step_id == "ask" and interactions:
            outputs = {
                "questions": [row["question_text"] for row in interactions],
                "channel": interactions[0]["channel"],
            }
            headline = f"{len(interactions)} asked"
            occurred = _moment(interactions[0]["asked_at_utc"])
        elif step_id == "critique":
            stripped = trace.get("stripped_claims", []) or []
            outputs = {"stripped_claims": stripped}
            headline = f"{len(stripped)} removed"

        steps.append(
            _step(
                step_id,
                StepStatus.RAN,
                _AGENT_STEP_REASONS.get(step_id, "This step ran."),
                headline_figure=headline,
                occurred_utc=occurred,
                outputs=outputs,
            )
        )

    return steps


def _agent_steps_from_evidence(conn: sqlite3.Connection, episode_id: str) -> set[str]:
    """Which agent steps ran, read from what each one leaves behind.

    Used when no trace has been written yet, which is the normal state of an investigation
    that is still going. Every source here is a row the step itself wrote.
    """
    ran: set[str] = set()

    tools = [
        row["tool_name"]
        for row in conn.execute(
            """SELECT tool_name FROM audit_events
                WHERE episode_id = ? AND operation = 'execute_tool' AND tool_name IS NOT NULL""",
            (episode_id,),
        ).fetchall()
    ]
    if tools:
        # The five fixed reads are the preload set. Anything else was chosen by the model
        # inside the investigation loop. The set is read from `wha.agent.steps` so that a
        # tool added to preload is not counted here as evidence that the model chose it.
        ran.add("preload")
        if set(tools) - PRELOAD_TOOLS:
            ran.add("investigate")

    if conn.execute("SELECT 1 FROM beliefs WHERE episode_id = ? LIMIT 1", (episode_id,)).fetchone():
        # `believe` and `decide` are joined by an unconditional edge in the graph, so a
        # stored belief means the decision that follows it was reached too.
        ran.add("believe")
        ran.add("decide")

    if conn.execute(
        "SELECT 1 FROM interactions WHERE episode_id = ? LIMIT 1", (episode_id,)
    ).fetchone():
        ran.add("ask")

    if conn.execute(
        "SELECT 1 FROM outcomes WHERE episode_id = ? LIMIT 1", (episode_id,)
    ).fetchone():
        ran.add("conclude")

    return ran


def _decision_outputs(
    conn: sqlite3.Connection, episode_id: str, interactions: list[sqlite3.Row]
) -> dict[str, object]:
    """What the policy decided, and every question it scored to decide it.

    Read from the decision the agent wrote down. Recomputing it here would be a second
    opinion rather than the record: the inputs move as the week goes on, so a recomputation
    days later can disagree with what actually happened.
    """
    row = None
    for candidate in conn.execute(
        """SELECT output_json FROM audit_events
            WHERE episode_id = ? AND operation = 'plan' AND output_json IS NOT NULL
            ORDER BY timestamp_utc DESC""",
        (episode_id,),
    ):
        try:
            if "action" in json.loads(candidate["output_json"]):
                row = candidate
                break
        except (TypeError, ValueError):
            continue

    if row is None or not row["output_json"]:
        # Older investigations decided before the decision was written down. What survives
        # is whatever an asked question recorded about the probes it beat.
        if interactions:
            rejected = json.loads(interactions[0]["rejected_json"] or "[]")
            return {
                "action": "ASK",
                "value_of_asking": interactions[0]["evsi"],
                "interruption_cost": interactions[0]["interruption_cost"],
                "questions_considered": [
                    {"probe_id": probe, "value_of_asking": value} for probe, value in rejected
                ],
            }
        return {}

    payload = json.loads(row["output_json"])
    return {
        "action": str(payload.get("action") or "").upper(),
        "why": payload.get("rationale"),
        "chosen_question": payload.get("chosen_probe"),
        "value_of_asking": payload.get("value_of_asking"),
        "interruption_cost": payload.get("interruption_cost"),
        "questions_considered": payload.get("candidates") or [],
    }


def _episode_trace(conn: sqlite3.Connection, episode_id: str) -> dict:
    row = conn.execute(
        "SELECT payload_json FROM episode_traces WHERE episode_id = ?", (episode_id,)
    ).fetchone()
    if row is None or not row["payload_json"]:
        return {}
    try:
        loaded = json.loads(row["payload_json"])
    except (TypeError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _answer_step(interactions: list[sqlite3.Row]) -> PipelineStepView:
    """What you said back. The only step in the pipeline that is yours."""
    if not interactions:
        return _step(
            "answer",
            StepStatus.NOT_APPLICABLE,
            "You were not asked anything about this night, so there was nothing to answer.",
        )

    answered = [row for row in interactions if row["status"] == "ANSWERED"]
    if not answered:
        pending = interactions[0]["status"].lower()
        return _step(
            "answer",
            StepStatus.SKIPPED,
            f"A question was asked and is {pending}. The investigation waits rather than "
            "guessing what you would have said.",
        )

    replies = [row["answer_option_id"] or row["free_text"] or "" for row in answered]
    return _step(
        "answer",
        StepStatus.RAN,
        "You replied, and your answer changed what the system believed. Nothing about "
        "your symptoms is assumed: it is either something you said or it is unknown.",
        headline_figure=f"{len(answered)} answered",
        occurred_utc=_moment(answered[0]["answered_at_utc"]),
        outputs={"replies": replies},
    )


def _deliver_step(conn: sqlite3.Connection, episode_id: str) -> PipelineStepView:
    """Whether anything actually reached the person, and where it went."""
    rows = conn.execute(
        """SELECT kind, channel, status, sent_at_utc FROM notifications
           WHERE episode_id = ? ORDER BY queued_at_utc""",
        (episode_id,),
    ).fetchall()

    if not rows:
        return _step(
            "deliver",
            StepStatus.SKIPPED,
            "Nothing has been sent to you about this investigation yet.",
        )

    sent = [row for row in rows if row["status"] == "SENT"]
    return _step(
        "deliver",
        StepStatus.RAN,
        _AGENT_STEP_REASONS["deliver"],
        headline_figure=f"{len(sent)} sent",
        occurred_utc=_moment(sent[0]["sent_at_utc"]) if sent else None,
        outputs={
            "messages": [
                {"kind": row["kind"], "channel": row["channel"], "status": row["status"]}
                for row in rows
            ]
        },
    )


# ------------------------------------------------------------------- the safety floor


def _safety_steps(
    conn: sqlite3.Connection,
    subject_id: str,
    night_date: date,
    episode_id: str | None,
    tz_name: str,
) -> list[PipelineStepView]:
    """The floor that runs on your words, shown whether or not it triggered.

    Always present. A screen that hides the safety floor on the nights it stayed quiet
    teaches the person that it only exists during an investigation, and it is the one part
    of this system that runs on everything they type.
    """
    day_start, day_end = _local_day_bounds(night_date, tz_name)

    events = conn.execute(
        """SELECT safety_event, timestamp_utc FROM audit_events
           WHERE subject_id = ? AND operation IN ('chat', 'red_flag_check')
             AND timestamp_utc >= ? AND timestamp_utc < ?
           ORDER BY timestamp_utc""",
        (subject_id, day_start.isoformat(), day_end.isoformat()),
    ).fetchall()
    triggered = [row for row in events if (row["safety_event"] or "none") != "none"]

    if not events:
        phrase_step = _step(
            "safety_phrase_rules",
            StepStatus.NOT_APPLICABLE,
            "These rules read what you write. You did not write to the system around this "
            "night, so there was nothing for them to read. They are always on.",
        )
    elif triggered:
        phrase_step = _step(
            "safety_phrase_rules",
            StepStatus.RAN,
            "Something you wrote matched a fixed phrase rule, which raised the urgency. "
            "These rules are a plain list, not a model, and nothing the AI says can lower "
            "what they set.",
            headline_figure="triggered",
            occurred_utc=_moment(triggered[0]["timestamp_utc"]),
            outputs={"events": [row["safety_event"] for row in triggered]},
        )
    else:
        phrase_step = _step(
            "safety_phrase_rules",
            StepStatus.RAN,
            "Everything you wrote was checked against the fixed phrase rules, and none of "
            "them matched.",
            headline_figure="not triggered",
            occurred_utc=_moment(events[0]["timestamp_utc"]),
            outputs={"messages_checked": len(events)},
        )

    answers = conn.execute(
        """SELECT presentation, item_id, answer FROM triage_answers
           WHERE subject_id = ? AND (episode_id = ? OR (recorded_at_utc >= ? AND
                 recorded_at_utc < ?))""",
        (subject_id, episode_id or "", day_start.isoformat(), day_end.isoformat()),
    ).fetchall()

    if not answers:
        triage_step = _step(
            "safety_triage",
            StepStatus.NOT_APPLICABLE,
            "The five published questions only run when what you write suggests the "
            "presentation they were validated for. Nothing you wrote did.",
        )
    else:
        scored = sum(1 for row in answers if row["answer"] is not None)
        triage_step = _step(
            "safety_triage",
            StepStatus.RAN,
            "A short published checklist was worked through, using a cut-off from the "
            "study that produced it rather than a threshold chosen here.",
            headline_figure=f"{scored} of {len(answers)} answered",
            outputs={
                "presentation": answers[0]["presentation"],
                "items": [{"item_id": row["item_id"], "answer": row["answer"]} for row in answers],
            },
        )

    return [phrase_step, triage_step]


def _local_day_bounds(night_date: date, tz_name: str) -> tuple[datetime, datetime]:
    """The person's own day around a night, so a UTC hour cannot pick the wrong one."""
    from zoneinfo import ZoneInfo

    zone = ZoneInfo(tz_name)
    start = datetime(night_date.year, night_date.month, night_date.day, 0, 0, tzinfo=zone)
    return start.astimezone(UTC), (start + timedelta(days=1)).astimezone(UTC)


def _headline(
    detail: object,
    detection: sqlite3.Row | None,
    steps: list[PipelineStepView],
) -> PipelineHeadline:
    """The tiles, assembled from steps that already read stored rows."""
    believe = next((s for s in steps if s.step_id == "believe"), None)
    ask = next((s for s in steps if s.step_id == "ask"), None)
    baseline = next((s for s in steps if s.step_id == "baseline"), None)
    rung = baseline.outputs.get("rung") if baseline else None

    top_cause = believe.outputs.get("top_cause") if believe else None
    top_probability = believe.outputs.get("top_probability") if believe else None
    questions = len(ask.outputs.get("questions", [])) if ask and ask.outputs else 0
    sources = {citation.source_id for step in steps for citation in step.sources}

    return PipelineHeadline(
        level=detail.row.level,  # type: ignore[attr-defined]
        flagged=bool(detection["flagged"]) if detection is not None else False,
        rung=BaselineRung(rung) if rung else None,
        primary_cause=CauseId(top_cause) if top_cause else None,
        primary_probability=float(top_probability) if top_probability is not None else None,
        sleep_hours=detail.features.sleep_hours,  # type: ignore[attr-defined]
        coverage_minutes=detail.features.coverage_minutes,  # type: ignore[attr-defined]
        questions_asked=questions,
        sources_read=len(sources),
    )


def get_night_pipeline(
    subject_id: str,
    night_date: date,
    conn: sqlite3.Connection | None = None,
) -> NightPipeline:
    """Every step of one night, in the order it happened.

    Returns a pipeline for any night in range, including nights with no reading and
    nights nothing looked at, because those are the nights a screen currently cannot
    explain at all.
    """
    close_conn = False
    if conn is None:
        conn = connect()
        apply_schema(conn)
        close_conn = True

    try:
        tz_name = _subject_timezone(conn, subject_id)
        detail = get_night_detail(subject_id, night_date, conn=conn)
        detection = _detection_row(conn, subject_id, night_date)

        from wha.features.sleep_window import resolve_sleep_window

        window = resolve_sleep_window(conn, subject_id, night_date, tz_name)

        features_row = conn.execute(
            "SELECT rhr_window_source FROM nightly_features "
            "WHERE subject_id = ? AND night_date = ?",
            (subject_id, night_date.isoformat()),
        ).fetchone()
        stored_source = features_row["rhr_window_source"] if features_row is not None else None

        steps = [
            _collect_step(conn, subject_id, window.start_utc, window.end_utc),
            _store_step(conn, subject_id, window.start_utc, window.end_utc),
            _sleep_window_step(conn, subject_id, night_date, tz_name, stored_source),
            _features_step(conn, subject_id, night_date),
            _baseline_step(conn, subject_id, night_date),
            _subtract_step(detection),
            _detect_step(detection),
            _safety_floor_step(conn, subject_id, night_date),
            _episode_open_step(conn, detail.row.episode_id, detection),
            *_agent_steps(conn, detail.row.episode_id, detection),
            *_safety_steps(conn, subject_id, night_date, detail.row.episode_id, tz_name),
        ]
        steps.sort(key=lambda step: step.ordinal)

        headline = _headline(detail, detection, steps)

        return NightPipeline(
            subject_id=subject_id,
            night_date=night_date,
            episode_id=detail.row.episode_id,
            headline=headline,
            steps=steps,
        )
    finally:
        if close_conn:
            conn.close()


def list_pipeline_nights(
    subject_id: str,
    days: int = 60,
    conn: sqlite3.Connection | None = None,
    end: date | None = None,
) -> list[PipelineNightRef]:
    """Just enough about each night to draw the stepper.

    Built from `list_nights` rather than from its own query, so the stepper and the
    History table can never disagree about which nights exist.
    """
    end = end or local_today()
    start = end - timedelta(days=days)
    rows = list_nights(subject_id, start=start, end=end, conn=conn)
    return [
        PipelineNightRef(
            night_date=row.night_date,
            level=row.level or DetectionLevel.NA,
            has_episode=row.episode_id is not None,
            usable=row.usable,
        )
        for row in rows
    ]
