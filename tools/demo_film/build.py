#!/usr/bin/env python
"""Build the demo film's twelve day timeline through the real system.

This is pass one of two. It runs the production pipeline against the real model and leaves
a database snapshot after every day, so pass two can point a camera at any single day
without re-running the arc or paying for the model calls again.

    uv run python tools/demo_film/serve_watch.py          # terminal 1, leave running
    uv run python tools/demo_film/build.py --stage seed   # terminal 2
    uv run python tools/demo_film/build.py --stage story

Three things keep this away from production:

1. It writes to `data/demo_film.sqlite`, never `data/wha.sqlite`. The live database is
   opened read-only, once, to copy the seven real nights out of subject `me`.
2. It uses its own mock watch state file, so the parked simulation's cursor is untouched.
3. It sets `WHA_CLOCK_OFFSET_DAYS` per day, which nothing else in the repository sets.

The day loop asserts each day's prediction from `timeline.py` and STOPS on the first
mismatch. That is the point of the whole harness. Adjusting a prediction to match what
happened would turn this back into a demo that always works.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "tools"))

DEMO_DB = REPO_ROOT / "data" / "demo_film.sqlite"
DEMO_STATE = REPO_ROOT / "data" / "demo_film_state.json"
SNAPSHOT_DIR = REPO_ROOT / "data" / "demo-snapshots"
LIVE_DB = REPO_ROOT / "data" / "wha.sqlite"
SUBJECT = "demo"
REAL_SUBJECT = "me"
TZ = "Asia/Singapore"

# Set before anything from `wha` is imported, because settings are read at import time.
os.environ["WHA_DB_PATH"] = str(DEMO_DB)
os.environ["WHA_SUBJECT"] = SUBJECT
os.environ["WHA_TIMEZONE"] = TZ
os.environ["WHA_MOCK_STATE"] = str(DEMO_STATE)
os.environ.setdefault("WHA_BRIDGE_URL", "http://127.0.0.1:8788")

from timeline import (
    BASE_BPM,
    DAYS,
    PROLOGUE_END,
    PROLOGUE_START,
    REAL_END,
    REAL_START,
    SEED,
    Day,
)

# Raw sample tables carried over from the real subject. Derived tables are deliberately
# NOT copied: features, baselines and detections are recomputed by the real nightly job,
# so what the film shows was produced by the system rather than transplanted into it.
RAW_TABLES = (
    "heart_rate_samples",
    "sleep_stages",
    "step_buckets",
    "exercise_sessions",
    "oxygen_saturation_samples",
    "distance_buckets",
    "calorie_buckets",
)

# Without these two there is no night to score. The others are sparse in the real data.
REQUIRED_TABLES = ("heart_rate_samples", "sleep_stages")


class BuildError(RuntimeError):
    """A day did not do what it was predicted to do. Investigate, do not adjust."""


# ------------------------------------------------------------------------ the clock


def real_today() -> date:
    """Today, ignoring any offset. The offset is measured from here."""
    return datetime.now(UTC).astimezone(ZoneInfo(TZ)).date()


def set_clock_to(when: date) -> int:
    offset = (when - real_today()).days
    os.environ["WHA_CLOCK_OFFSET_DAYS"] = str(offset)
    from wha.clock import local_today

    reads = local_today()
    if reads != when:
        raise BuildError(f"clock offset {offset:+d} makes today {reads}, wanted {when}")
    return offset


def clear_clock() -> None:
    os.environ.pop("WHA_CLOCK_OFFSET_DAYS", None)


# ------------------------------------------------------------------------- plumbing


def connect_demo() -> sqlite3.Connection:
    conn = sqlite3.connect(DEMO_DB)
    conn.row_factory = sqlite3.Row
    return conn


def snapshot(label: str) -> Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    dest = SNAPSHOT_DIR / f"{label}.sqlite"
    with connect_demo() as src, sqlite3.connect(dest) as dst:
        src.backup(dst)
    return dest


def write_state(cursor: date, window_days: int) -> None:
    DEMO_STATE.parent.mkdir(parents=True, exist_ok=True)
    DEMO_STATE.write_text(
        json.dumps(
            {
                "subject": SUBJECT,
                "cursor": cursor.isoformat(),
                "window_days": window_days,
                "base_bpm": BASE_BPM,
                "seed": SEED,
                "timezone": TZ,
                "events": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def bridge_is_up() -> bool:
    import httpx

    try:
        httpx.get(os.environ["WHA_BRIDGE_URL"], params={"days": 1}, timeout=5.0)
    except Exception:  # noqa: BLE001
        return False
    return True


# ---------------------------------------------------------------------------- seeding


def seed() -> None:
    """A fresh database, a generated prologue, then the real nights on top."""
    if not bridge_is_up():
        raise BuildError(
            "the mock watch is not answering. Start it first:\n"
            "    uv run python tools/demo_film/serve_watch.py"
        )

    for path in (DEMO_DB, DEMO_STATE):
        if path.exists():
            path.unlink()
    if SNAPSHOT_DIR.exists():
        shutil.rmtree(SNAPSHOT_DIR)

    from wha.db import apply_schema, connect

    conn = connect(DEMO_DB)
    apply_schema(conn)
    conn.close()

    # 1. The prologue. Generated nights at the person's own measured resting rate, purely
    #    so the baseline reaches MATURE. Nothing in the film happens in this window.
    prologue_nights = (PROLOGUE_END - PROLOGUE_START).days + 1
    print(f"=== prologue: {prologue_nights} generated nights {PROLOGUE_START} .. {PROLOGUE_END}")
    write_state(PROLOGUE_END, prologue_nights)
    set_clock_to(PROLOGUE_END)
    run_pipeline_for(PROLOGUE_START, PROLOGUE_END, window_days=prologue_nights)

    # 2. The real nights, copied as RAW readings only.
    print(f"\n=== real nights: copying {REAL_START} .. {REAL_END} out of subject '{REAL_SUBJECT}'")
    copied = copy_real_nights()
    for table, n in copied.items():
        print(f"    {table:<28} {n:>7} rows")

    # 3. Scored by the real nightly job, not transplanted.
    print(f"\n=== nightly over the real nights {REAL_START} .. {REAL_END}")
    set_clock_to(REAL_END)
    from wha.service.nightly import run_nightly

    for d in run_nightly(
        subject_id=SUBJECT,
        date_or_range=f"{REAL_START.isoformat()}:{REAL_END.isoformat()}",
        no_ingest=True,
    ):
        residual = f"{d.residual_bpm:+.2f}" if d.residual_bpm is not None else "n/a"
        print(f"    {d.night_date} | {d.level:<6} | residual {residual}")

    # The story days are served one night at a time. The clamp in the mock watch is what
    # stops a catch-up ingest asking for thirty days and generating synthetic nights over
    # the real ones.
    write_state(REAL_END, 1)
    clear_clock()

    report_baseline()
    snapshot("00-seeded")
    print(f"\nsnapshot: {SNAPSHOT_DIR / '00-seeded.sqlite'}")


def copy_real_nights() -> dict[str, int]:
    """Copy raw readings for the real window out of the live database, read-only.

    The source is opened with `mode=ro` rather than by convention. Subject `me` holds a
    real person's watch data and this is the only thing in the film that touches it.
    """
    src = sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    dst = connect_demo()

    lo = datetime(REAL_START.year, REAL_START.month, REAL_START.day, tzinfo=ZoneInfo(TZ))
    # Nights are labelled by local date and run to 7am, so take a generous upper bound and
    # let the sleep window decide what belongs to which night.
    hi = datetime(REAL_END.year, REAL_END.month, REAL_END.day, tzinfo=ZoneInfo(TZ)) + timedelta(
        days=1
    )
    lo_iso, hi_iso = lo.astimezone(UTC).isoformat(), hi.astimezone(UTC).isoformat()

    counts: dict[str, int] = {}
    dst.execute(
        "INSERT OR REPLACE INTO subjects (subject_id, label, source_kind, timezone, "
        "created_at_utc) VALUES (?, ?, ?, ?, ?)",
        (SUBJECT, SUBJECT, "live", TZ, datetime.now(UTC).isoformat()),
    )

    for table in RAW_TABLES:
        cols = [r[1] for r in src.execute(f"PRAGMA table_info({table})")]
        if not cols:
            continue
        # `ts_utc` for point samples, `start_utc` for buckets and sessions. Getting this
        # list wrong once already cost a build: heart_rate_samples uses `ts_utc`, the
        # first version of this list did not have it, and the copy silently recorded zero
        # rows and carried on. Silently recording zero is how a demo ends up filming an
        # empty chart, so an unknown table is now an error.
        time_col = next((c for c in ("ts_utc", "start_utc") if c in cols), None)
        if time_col is None:
            raise BuildError(
                f"{table} has no recognised time column. Columns are {cols}. "
                "Add the right one rather than skipping the table."
            )
        rows = src.execute(
            f"SELECT * FROM {table} WHERE subject_id = ? AND {time_col} >= ? AND {time_col} < ?",
            (REAL_SUBJECT, lo_iso, hi_iso),
        ).fetchall()
        if not rows:
            # Only two channels are load bearing. A night is measured over the sleep the
            # watch recorded, so without heart rate or sleep there is nothing to score.
            # The rest are genuinely sparse in the real data: `me` holds a single distance
            # row in a month, and halting over that would be noise.
            if table in REQUIRED_TABLES:
                raise BuildError(
                    f"{table} returned no rows for subject {REAL_SUBJECT!r} between "
                    f"{lo_iso} and {hi_iso}. The real nights cannot be copied from nothing."
                )
            counts[table] = 0
            continue
        placeholders = ",".join("?" * len(cols))
        payload = []
        subject_idx = cols.index("subject_id")
        for row in rows:
            values = list(row)
            values[subject_idx] = SUBJECT
            payload.append(values)
        dst.executemany(
            f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({placeholders})",
            payload,
        )
        counts[table] = len(payload)

    dst.commit()
    dst.close()
    src.close()
    return counts


def report_baseline() -> None:
    from wha.detect.baseline import rung_for

    conn = connect_demo()
    usable = conn.execute(
        "SELECT COUNT(*) FROM nightly_features WHERE subject_id = ? AND usable = 1",
        (SUBJECT,),
    ).fetchone()[0]
    conn.close()
    print(f"\nbaseline: {usable} usable nights, rung {rung_for(usable).name}")
    if rung_for(usable).name != "MATURE":
        raise BuildError(
            f"{usable} usable nights gives the {rung_for(usable).name} rung. The story needs "
            "MATURE, which needs 28. Something in the seed did not land."
        )


# ------------------------------------------------------------------------- the story


def run_pipeline_for(start: date, end: date, window_days: int, agent: bool = True) -> None:
    from wha.service.ingest import run_ingest
    from wha.service.nightly import run_nightly
    from wha.service.scheduler import run_episode_tick

    run_ingest(subject_id=SUBJECT, days=window_days)
    run_nightly(
        subject_id=SUBJECT,
        date_or_range=f"{start.isoformat()}:{end.isoformat()}",
        no_ingest=True,
    )
    if agent:
        run_episode_tick()


def advance_to(day: Day, agent: bool = True) -> None:
    """Move the watch on one night and run exactly what the scheduler runs."""
    state = json.loads(DEMO_STATE.read_text(encoding="utf-8"))
    from mock_watch import SCENARIOS

    preset = SCENARIOS[day.scenario]
    events = list(state["events"])
    if preset is not None:
        events.append({**preset, "date": day.date.isoformat()})
    for extra in day.events:
        events.append({**extra, "date": day.date.isoformat()})
    state["events"] = events
    state["cursor"] = day.date.isoformat()
    DEMO_STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    run_pipeline_for(day.date, day.date, window_days=state["window_days"], agent=agent)


def review_draft(day: Day) -> bool:
    """The human checkpoint. Approve, edit, reject or escalate a drafted conclusion.

    Nothing exercised this in the first build, so every draft was released unreviewed
    once its window passed and the investigation closed on a day the timeline did not
    expect. That default is correct and it is recorded as "not approved", but a film
    about human oversight that never shows a human overseeing anything is not much of a
    film.
    """
    if day.review is None:
        return False
    conn = connect_demo()
    row = conn.execute(
        "SELECT episode_id FROM episodes WHERE subject_id = ? AND state = "
        "'AWAITING_HUMAN_REVIEW' ORDER BY opened_on DESC LIMIT 1",
        (SUBJECT,),
    ).fetchone()
    conn.close()
    if row is None:
        raise BuildError(
            f"{day.date} expected a drafted conclusion to review and there is none. "
            "Either the agent did not conclude, or it concluded on a different day."
        )

    decision, rationale = day.review
    from wha.service.episodes import submit_human_decision

    submit_human_decision(episode_id=row["episode_id"], decision=decision, rationale=rationale)
    print(f'    reviewed the draft: {decision.upper()}, "{rationale}"')
    return True


def speak(day: Day) -> None:
    """What the person says, through the same path the dashboard and Telegram use."""
    from wha.service.conversation import send_message

    for text in day.tell:
        reply = send_message(subject_id=SUBJECT, text=text)
        urgency = reply.urgency or "none"
        print(f'    said: "{text}"')
        print(f"    urgency {urgency}, flags {list(reply.triggered_flags or [])}")
        print(f"    reply: {reply.text[:160]}")


def answer_pending(day: Day) -> bool:
    if day.answer is None:
        return False
    conn = connect_demo()
    row = conn.execute(
        "SELECT i.id, i.episode_id, i.probe_id, i.question_text FROM interactions i "
        "JOIN episodes e ON e.episode_id = i.episode_id "
        "WHERE e.subject_id = ? AND i.status = 'PENDING' "
        "ORDER BY i.asked_at_utc DESC LIMIT 1",
        (SUBJECT,),
    ).fetchone()
    conn.close()
    if row is None:
        return False

    from wha.models import Answer
    from wha.service.episodes import submit_answer

    print(f'    question was: "{row["question_text"][:140]}"')
    submit_answer(
        row["episode_id"],
        Answer(probe_id=row["probe_id"], option_id=None, free_text=day.answer, declined=False),
    )
    print(f'    answered: "{day.answer}"')

    from wha.service.scheduler import run_episode_tick

    run_episode_tick()
    return True


# ---------------------------------------------------------------------- verification


def observe(day: Day) -> dict[str, object]:
    conn = connect_demo()
    iso = day.date.isoformat()

    det = conn.execute(
        "SELECT level, flagged FROM detections WHERE subject_id = ? AND night_date = ?",
        (SUBJECT, iso),
    ).fetchone()

    open_ep = conn.execute(
        "SELECT episode_id, opened_on, state, disposition, preceded_by_episode_id "
        "FROM episodes WHERE subject_id = ? AND state != 'CLOSED' "
        "ORDER BY opened_on DESC LIMIT 1",
        (SUBJECT,),
    ).fetchone()

    newest_ep = conn.execute(
        "SELECT episode_id, opened_on, state, disposition FROM episodes "
        "WHERE subject_id = ? ORDER BY opened_on DESC, rowid DESC LIMIT 1",
        (SUBJECT,),
    ).fetchone()

    asked = conn.execute(
        "SELECT COUNT(*) FROM interactions i JOIN episodes e ON e.episode_id = i.episode_id "
        "WHERE e.subject_id = ? AND substr(i.asked_at_utc, 1, 10) = ?",
        (SUBJECT, iso),
    ).fetchone()[0]

    urgencies = [
        r[0]
        for r in conn.execute(
            "SELECT urgency FROM conversation_turns WHERE subject_id = ? "
            "AND substr(created_at_utc, 1, 10) = ? AND urgency IS NOT NULL",
            (SUBJECT, iso),
        )
    ]

    symptoms = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT flag_id FROM symptom_observations WHERE subject_id = ? "
            "AND present = 1 AND night_date <= ?",
            (SUBJECT, iso),
        )
    ]
    conn.close()

    return {
        "level": det["level"] if det else None,
        "flagged": bool(det["flagged"]) if det else None,
        "episode_open": open_ep is not None,
        "episode_id": open_ep["episode_id"] if open_ep else None,
        "opened_on": open_ep["opened_on"] if open_ep else None,
        "newest_episode": dict(newest_ep) if newest_ep else None,
        "questions_today": asked,
        "urgencies": urgencies,
        "symptoms": sorted(symptoms),
    }


def check(day: Day, seen: dict[str, object]) -> list[str]:
    e = day.expect
    bad: list[str] = []

    if e.level is not None and seen["level"] != e.level:
        bad.append(f"level: predicted {e.level}, got {seen['level']}")

    if e.flagged is not None and seen["flagged"] != e.flagged:
        bad.append(f"flagged: predicted {e.flagged}, got {seen['flagged']}")

    if e.episode_open is not None and seen["episode_open"] != e.episode_open:
        bad.append(f"episode_open: predicted {e.episode_open}, got {seen['episode_open']}")

    if e.episode_is_new:
        if seen["opened_on"] != day.date.isoformat():
            bad.append(
                f"a new investigation should have opened today, opened_on={seen['opened_on']}"
            )
    elif e.episode_open and seen["opened_on"] == day.date.isoformat():
        bad.append("an investigation opened today, but this day should continue the previous one")

    if e.question_asked is not None:
        asked = bool(seen["questions_today"])
        if asked != e.question_asked:
            bad.append(f"question_asked: predicted {e.question_asked}, got {asked}")

    if e.escalation is not None and e.escalation not in (seen["urgencies"] or []):
        bad.append(f"escalation: predicted {e.escalation}, got {seen['urgencies'] or 'none'}")

    missing = [s for s in e.symptoms_on_timeline if s not in seen["symptoms"]]
    if missing:
        bad.append(f"symptoms missing from the timeline: {missing}, have {seen['symptoms']}")

    return bad


# ------------------------------------------------------------------------------ main


def resume_from(when: date) -> None:
    """Restore the snapshot taken the day before `when`, so a day can be re-run.

    Every day the model touches costs a real API call, so re-running the whole arc to
    reach day eleven is waste. The snapshots exist precisely so a day can be replayed
    from the state that preceded it.
    """
    index = next((i for i, d in enumerate(DAYS) if d.date == when), None)
    if index is None:
        raise BuildError(f"{when} is not in the timeline")
    if index == 0:
        source = SNAPSHOT_DIR / "00-seeded.sqlite"
        cursor = REAL_END
    else:
        previous = DAYS[index - 1]
        source = SNAPSHOT_DIR / f"{index:02d}-{previous.date.isoformat()}.sqlite"
        cursor = previous.date
    if not source.is_file():
        raise BuildError(f"no snapshot at {source}. Run the earlier days first.")

    shutil.copyfile(source, DEMO_DB)
    write_state(cursor, 1)
    # The events that produced the nights up to here have already been ingested and
    # scored, so the state file starts clean and each day re-adds its own.
    for earlier in DAYS[:index]:
        state = json.loads(DEMO_STATE.read_text(encoding="utf-8"))
        from mock_watch import SCENARIOS

        preset = SCENARIOS[earlier.scenario]
        events = list(state["events"])
        if preset is not None:
            events.append({**preset, "date": earlier.date.isoformat()})
        for extra in earlier.events:
            events.append({**extra, "date": earlier.date.isoformat()})
        state["events"] = events
        DEMO_STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(f"resumed from {source.name}, cursor {cursor}")


def run_story(only: date | None, stop_on_mismatch: bool, start: date | None = None) -> int:
    if not DEMO_DB.exists():
        raise BuildError("no demo database. Run --stage seed first.")
    if not bridge_is_up():
        raise BuildError("the mock watch is not answering. Start tools/demo_film/serve_watch.py")

    failures = 0
    if start is not None:
        resume_from(start)

    for index, day in enumerate(DAYS, 1):
        if only is not None and day.date != only:
            continue
        if start is not None and day.date < start:
            continue
        offset = set_clock_to(day.date)
        print(f"\n{'=' * 78}\n{day.date}  {day.chapter}   (clock {offset:+d} days)\n{'=' * 78}")
        if day.expect.note:
            print(f"predicted: {day.expect.note}\n")

        advance_to(day)
        answered = answer_pending(day)
        reviewed = review_draft(day)
        speak(day)
        if (day.tell or reviewed) and not answered:
            from wha.service.scheduler import run_episode_tick

            run_episode_tick()

        seen = observe(day)
        print(
            f"\n    level={seen['level']} flagged={seen['flagged']} "
            f"episode_open={seen['episode_open']} opened_on={seen['opened_on']} "
            f"questions_today={seen['questions_today']}"
        )
        print(f"    urgencies={seen['urgencies']}  symptoms={seen['symptoms']}")

        bad = check(day, seen)
        if bad:
            failures += 1
            print("\n  PREDICTION FAILED")
            for line in bad:
                print(f"    - {line}")
            if stop_on_mismatch:
                clear_clock()
                raise BuildError(
                    f"{day.date} did not do what it was predicted to do. Investigate the "
                    "cause before touching the prediction."
                )
        else:
            print("\n  as predicted")

        snapshot(f"{index:02d}-{day.date.isoformat()}")

    clear_clock()
    return failures


def measure_levels() -> int:
    """Walk the story with no agent and no model, and print what each night scores.

    Exists because the first build stacked an illness injection on every red night and
    produced residuals of +5.5, +10.5 and +15.0 bpm. The measured effect of an infection
    on resting heart rate in this project's own cohort work is 1.60 bpm, so +15 is not a
    severe illness, it is three overlapping injections. The decay of a single event is a
    measurable thing and this measures it instead of guessing at it.
    """
    shutil.copyfile(SNAPSHOT_DIR / "00-seeded.sqlite", DEMO_DB)
    write_state(REAL_END, 1)
    print(f"{'night':<12} {'level':<7} {'flagged':<8} residual")
    for day in DAYS:
        set_clock_to(day.date)
        advance_to(day, agent=False)
        conn = connect_demo()
        row = conn.execute(
            "SELECT level, flagged, residual_bpm FROM detections WHERE subject_id = ? "
            "AND night_date = ?",
            (SUBJECT, day.date.isoformat()),
        ).fetchone()
        conn.close()
        residual = (
            f"{row['residual_bpm']:+.2f}" if row and row["residual_bpm"] is not None else "n/a"
        )
        print(
            f"{day.date}  {row['level'] if row else '-':<7} {bool(row['flagged'])!s:<8} {residual}"
        )
    clear_clock()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__ or "")
    parser.add_argument("--stage", choices=("seed", "story", "levels", "all"), default="all")
    parser.add_argument("--only", help="run a single day, YYYY-MM-DD")
    parser.add_argument(
        "--from",
        dest="start",
        help="restore the snapshot before this day and run from it, YYYY-MM-DD",
    )
    parser.add_argument(
        "--keep-going",
        action="store_true",
        help="report every mismatch instead of stopping at the first",
    )
    args = parser.parse_args()

    try:
        if args.stage == "levels":
            return measure_levels()
        if args.stage in ("seed", "all"):
            seed()
        if args.stage in ("story", "all"):
            failures = run_story(
                date.fromisoformat(args.only) if args.only else None,
                stop_on_mismatch=not args.keep_going,
                start=date.fromisoformat(args.start) if args.start else None,
            )
            if failures:
                print(f"\n{failures} day(s) did not match their prediction.")
                return 1
    except BuildError as e:
        clear_clock()
        print(f"\nBUILD HALTED: {e}", file=sys.stderr)
        return 2
    finally:
        clear_clock()

    print("\nEvery day matched its prediction.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
