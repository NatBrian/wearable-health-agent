"""Demo scenario runner service.

This is the command the project is judged by, so it must exercise the whole path and it
must fail loudly. Previously it ingested, derived features, detected, printed a table
and returned success unconditionally: no episode was opened, no question asked, no
disposition reached, and the fixture's ``expect`` block was never compared against
anything. Every scenario "passed", including the two whose entire purpose is to show an
escalation and an investigation.

It also read a hardcoded date window that did not match the window the generator
produces, so the last two nights, the ones carrying the injected illness, were never
computed at all.
"""

import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml

from wha.db import apply_schema, connect
from wha.detect.detector import detect_range
from wha.errors import ConfigError
from wha.features.derivation import compute_range
from wha.ingest.store import normalise_and_store
from wha.ingest.synthetic import Synthetic
from wha.models import Detection, Disposition, Scenario
from wha.service.episode_lifecycle import (
    get_open_episode,
    open_episodes_for_flagged_nights,
)
from wha.service.symptom_report import report_symptoms


@dataclass(frozen=True)
class ExpectationResult:
    """One line of the fixture contract, and whether the run satisfied it."""

    name: str
    expected: Any
    actual: Any
    ok: bool


@dataclass(frozen=True)
class DemoRunResult:
    scenario: str
    subject_id: str
    dry_run: bool
    nights: list[Detection]
    episode_ids: list[str] = field(default_factory=list)
    disposition: str | None = None
    questions_asked: int = 0
    escalated: bool = False
    expectations: list[ExpectationResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True only when every checked expectation held."""
        return all(e.ok for e in self.expectations)


def _load_scenario(scenario_name: str) -> Scenario:
    """Locate and parse a frozen scenario fixture."""
    candidates = [
        Path(f"tests/fixtures/scenarios/{scenario_name}.json"),
        Path(f"tests/fixtures/scenarios/{scenario_name.replace('_', '-')}.json"),
        Path(f"tests/fixtures/scenarios/{scenario_name}.yaml"),
        Path(f"tests/fixtures/scenarios/{scenario_name.replace('-', '_')}.yaml"),
    ]
    scenario_file = next((p for p in candidates if p.exists()), None)
    if scenario_file is None:
        raise ConfigError(
            f"Scenario fixture '{scenario_name}' not found under tests/fixtures/scenarios/"
        )

    content = scenario_file.read_text(encoding="utf-8")
    data: dict[str, Any] = (
        json.loads(content) if scenario_file.suffix == ".json" else yaml.safe_load(content)
    )
    return Scenario.model_validate(data)


def _observed_range(conn: Any, subject_id: str, scenario: Scenario) -> tuple[date, date]:
    """Derive the window from the data that was actually stored.

    The generator anchors its output to a fixed timestamp and counts backwards, so the
    dates it produces are not the calendar dates a caller would guess. Reading the span
    back from the samples keeps the two in step, which a hardcoded window did not.
    """
    row = conn.execute(
        "SELECT MIN(DATE(ts_utc)), MAX(DATE(ts_utc)) FROM heart_rate_samples WHERE subject_id = ?",
        (subject_id,),
    ).fetchone()
    if row and row[0] and row[1]:
        return date.fromisoformat(row[0]), date.fromisoformat(row[1])

    first = date(2026, 8, 1)
    return first, first + timedelta(days=int(scenario.days) - 1)


def _evaluate_expectations(
    scenario: Scenario,
    detections: list[Detection],
    episode_ids: list[str],
    disposition: str | None,
    questions_asked: int,
    escalated: bool,
    dry_run: bool = False,
) -> list[ExpectationResult]:
    """Compare the run against the fixture's frozen contract.

    Only keys the fixture actually states are checked, so a scenario that says nothing
    about escalation is not held to a default. A dry run deliberately stops after the
    deterministic monitor, so it is held only to the detection half of the contract
    rather than being failed for a phase it was asked not to execute.
    """
    expect = scenario.expect or {}
    results: list[ExpectationResult] = []
    agent_keys = {"disposition", "asks_at_least", "escalates"}
    if dry_run:
        expect = {k: v for k, v in expect.items() if k not in agent_keys}

    def check(name: str, expected: Any, actual: Any) -> None:
        results.append(ExpectationResult(name, expected, actual, expected == actual))

    flagged = [d for d in detections if d.flagged]

    if "flagged_on_day" in expect:
        expected_day = expect["flagged_on_day"]
        if expected_day is None:
            check("flagged_on_day", None, len(flagged) or None)
        else:
            # Fixture day numbers are the generator's own day index, the same index the
            # injections use. The generator's first night falls one day after the first
            # calendar date its samples cover, because it anchors at 08:00 UTC and the
            # subject's local nocturnal window belongs to the following date.
            first_night = min(d.night_date for d in detections) if detections else None
            actual_day = (
                (flagged[0].night_date - first_night).days - 1
                if flagged and first_night is not None
                else None
            )
            check("flagged_on_day", expected_day, actual_day)

    if "opens_episode" in expect:
        check("opens_episode", expect["opens_episode"], bool(episode_ids))

    if "disposition" in expect:
        check("disposition", expect["disposition"], disposition)

    if "asks_at_least" in expect:
        expected_min = int(expect["asks_at_least"])
        results.append(
            ExpectationResult(
                "asks_at_least",
                expected_min,
                questions_asked,
                questions_asked >= expected_min,
            )
        )

    if "escalates" in expect:
        check("escalates", expect["escalates"], escalated)

    return results


# Where `wha demo run` writes when no database is named. Kept out of the configured
# database so a demonstration can never be mistaken for, or mixed with, a real record.
DEMO_DB_PATH = Path("data/demo.sqlite")


def run_demo(
    scenario_name: str,
    dry_run: bool = False,
    live: bool = False,
    db_path: Path | None = None,
) -> DemoRunResult:
    """Run a scenario end to end and check it against its frozen expectations.

    ``dry_run`` stops after the deterministic monitor, which is the detection half only.
    ``live`` allows a real model; without it the cassette provider keeps the run
    deterministic so the frozen expectations hold.
    """
    # A demo invents a person. Writing them into the configured database put eleven
    # synthetic subjects alongside a real one's health record, with nothing at query level
    # marking the difference, so any query that did not filter by subject silently mixed
    # real readings with fabricated ones. Demos now get their own file unless a caller
    # names a database explicitly.
    target_db = db_path if db_path is not None else DEMO_DB_PATH

    scenario = _load_scenario(scenario_name)
    subj_id = f"demo-{scenario_name}"

    target_db.parent.mkdir(parents=True, exist_ok=True)

    # Each run starts from an empty database, because a frozen scenario has to mean the
    # same thing whatever ran before it. The weekly interruption budget is counted across
    # all subjects, correctly, since this is a single-user application. In a shared demo
    # database that made the budget a global two questions across every scenario: running
    # the eleven back to back, the first two asked their question and the rest silently
    # asked nothing and reached the wrong disposition. Run alone each of those passed, so
    # the suite reported a different result depending on the order it was run in.
    #
    # Only the default demo database is reset. A caller who named one with --db keeps it.
    if db_path is None and target_db.exists():
        target_db.unlink()
    conn = connect(target_db)
    apply_schema(conn)

    try:
        conn.execute(
            """INSERT OR IGNORE INTO subjects
                 (subject_id, label, source_kind, timezone, created_at_utc)
               VALUES (?, ?, 'synthetic', ?, '2026-09-01T00:00:00Z')""",
            (subj_id, f"Demo {scenario_name}", scenario.timezone),
        )
        conn.commit()

        raw_payload = Synthetic(scenario=scenario).fetch(subject_id=subj_id)
        normalise_and_store(conn, raw_payload)

        first_dt, last_dt = _observed_range(conn, subj_id, scenario)
        compute_range(conn, subj_id, first_dt, last_dt)
        detections = detect_range(conn, subj_id, first_dt, last_dt)

        episode_ids = open_episodes_for_flagged_nights(conn, subj_id, detections)

        disposition: str | None = None
        questions_asked = 0
        escalated = False

        # A scenario whose person volunteers alarming words must reach the safety floor
        # whether or not the detector flagged a night. Escalation that depended on an
        # open episode would mean reporting chest pain on an ordinary night did nothing.
        oracle = dict(scenario.oracle or {})
        if not dry_run and oracle.get("free_text") and not episode_ids:
            report = report_symptoms(subj_id, str(oracle["free_text"]), conn=conn)
            if report.escalated:
                disposition = report.disposition
                escalated = True
                if report.episode_id:
                    episode_ids = [report.episode_id]

        if not dry_run and episode_ids and disposition is None:
            disposition, questions_asked, escalated = _run_episode_to_completion(
                conn,
                subj_id,
                episode_ids[0],
                target_db,
                oracle=oracle,
                live=live,
            )

        # A subject whose baseline is not yet established has a disposition even though no
        # episode opens: the system's answer is that it does not have enough data yet.
        if disposition is None and not episode_ids:
            rung_row = conn.execute(
                """SELECT rung FROM baselines WHERE subject_id = ?
                   ORDER BY night_date DESC LIMIT 1""",
                (subj_id,),
            ).fetchone()
            rung = str(rung_row["rung"]) if rung_row else "COLD"
            if rung == "COLD":
                disposition = Disposition.INSUFFICIENT_DATA.value

        expectations = _evaluate_expectations(
            scenario,
            detections,
            episode_ids,
            disposition,
            questions_asked,
            escalated,
            dry_run=dry_run,
        )

        return DemoRunResult(
            scenario=scenario_name,
            subject_id=subj_id,
            dry_run=dry_run,
            nights=detections,
            episode_ids=episode_ids,
            disposition=disposition,
            questions_asked=questions_asked,
            escalated=escalated,
            expectations=expectations,
        )
    finally:
        conn.close()


def _oracle_response(oracle: dict[str, Any], payload: Any) -> Any:
    """Answer one interrupt as the scenario's simulated person.

    The ``oracle`` block in every fixture exists for exactly this and was never read.
    Without it an episode parks on its first question and no scenario can ever reach a
    disposition, which is why the harness reported nothing at all.
    """
    if not isinstance(payload, dict):
        return {"decision": "approve"}

    kind = payload.get("kind")

    if kind == "question":
        # A scenario may specify that the person never replies at all.
        if oracle.get("__no_response__"):
            return {"timed_out": True}

        probe_id = payload.get("probe_id") or ""
        answer = oracle.get(probe_id)
        response: dict[str, Any] = {"probe_id": probe_id}
        if answer is None:
            # The fixture states no answer for this probe, so the person declines.
            response["declined"] = True
        else:
            response["option_id"] = answer
        if oracle.get("free_text"):
            response["free_text"] = oracle["free_text"]
        return response

    if kind == "human_review":
        # The oracle stands in for the person, which is the whole point of a frozen
        # scenario: the run has to be unattended and deterministic. This is NOT the
        # production path. There, nothing answers on the person's behalf; the episode
        # parks until they decide or REVIEW_TIMEOUT_HOURS closes it UNREVIEWED. See
        # `_resume_value` in wha/service/scheduler.py, which used to do what this line
        # does and recorded it as a human decision.
        return {"decision": "approve"}

    return {"decision": "approve"}


def _run_episode_to_completion(
    conn: Any,
    subject_id: str,
    episode_id: str,
    db_path: Path,
    oracle: dict[str, Any],
    live: bool = False,
    max_ticks: int = 24,
) -> tuple[str | None, int, bool]:
    """Advance an episode until it closes or stops making progress.

    Interrupts are answered from the fixture's oracle, so the run is deterministic and
    unattended. Returns the disposition, how many questions were put to the person, and
    whether the episode escalated.
    """
    from wha.agent.graph import get_agent_graph, get_pending_interrupt
    from wha.service.episodes import step_episode

    graph = get_agent_graph(db_path)

    for _ in range(max_ticks):
        row = conn.execute(
            "SELECT state, step_count FROM episodes WHERE episode_id = ?",
            (episode_id,),
        ).fetchone()
        if row is None or row["state"] == "CLOSED":
            break

        pending = get_pending_interrupt(graph, episode_id)
        before = row["step_count"]

        if pending is not None:
            step_episode(
                episode_id,
                db_path=db_path,
                resume=_oracle_response(oracle, pending),
            )
        else:
            step_episode(episode_id, db_path=db_path)

        after = conn.execute(
            "SELECT step_count FROM episodes WHERE episode_id = ?",
            (episode_id,),
        ).fetchone()["step_count"]
        still_parked = get_pending_interrupt(graph, episode_id)
        if after == before and still_parked is None:
            break

    final = conn.execute(
        "SELECT state, disposition FROM episodes WHERE episode_id = ?",
        (episode_id,),
    ).fetchone()
    disposition = final["disposition"] if final else None

    asked = conn.execute(
        "SELECT COUNT(*) AS n FROM interactions WHERE episode_id = ?",
        (episode_id,),
    ).fetchone()["n"]

    return disposition, int(asked), disposition == "ESCALATED"


__all__ = [
    "DemoRunResult",
    "ExpectationResult",
    "get_open_episode",
    "run_demo",
]
