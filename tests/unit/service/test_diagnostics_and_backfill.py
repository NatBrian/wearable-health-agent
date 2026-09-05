"""Diagnostics must not claim what they have not checked, and history must not alert.

Four defects found by a user running the system for the first time:

1. `doctor --live` reported the benchmark cohorts present because it asked only whether
   the directory existed, and `wha data fetch <name>` creates an empty one.
2. It printed "Schema v1 verified" from a hardcoded string while `doctor` read v3 from
   the database.
3. The two commands were separate diagnostics sharing a name, so the operator had to
   guess which to run.
4. A first sync backfills weeks of history, and every one of those nights was eligible to
   open an episode and message the person about a night from before they owned the system.
"""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from wha.db import connect
from wha.db.iso import to_iso
from wha.db.migrations import apply_schema
from wha.models import Detection, DetectionLevel, Forecast, ForecastStatus
from wha.service.checks import dataset_present, read_schema_version
from wha.service.doctor import run_doctor
from wha.service.episode_lifecycle import monitoring_since, open_episodes_for_flagged_nights

# -- 1 and 2: the two diagnostics establish their facts in one place ------------------


def test_an_empty_dataset_directory_is_not_a_dataset(tmp_path: Path) -> None:
    """`wha data fetch stanford` creates the directory and nothing else."""
    (tmp_path / "stanford").mkdir()
    assert dataset_present(tmp_path, "stanford") is False

    (tmp_path / "stanford" / "subject_01.csv").write_text("data", encoding="utf-8")
    assert dataset_present(tmp_path, "stanford") is True


def test_absent_dataset_directory_is_not_present(tmp_path: Path) -> None:
    assert dataset_present(tmp_path, "pmdata") is False


def test_schema_version_is_read_from_the_database(tmp_path: Path) -> None:
    """It was a hardcoded 'v1' string, so the two doctors disagreed about one file."""
    db_file = tmp_path / "v.db"
    conn = connect(db_file)
    apply_schema(conn)
    version = read_schema_version(conn)
    conn.close()

    assert version != "unknown"
    row_version = None
    conn = connect(db_file)
    row_version = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()[0]
    conn.close()
    assert version == str(row_version)


def test_both_diagnostics_report_the_same_schema_version(tmp_path: Path) -> None:
    """The regression the user hit: v1 from one command, v3 from the other."""
    from wha.service.status import check_live_production_suite

    db_file = tmp_path / "same.db"
    conn = connect(db_file)
    apply_schema(conn)
    expected = read_schema_version(conn)
    conn.close()

    doctor_items = run_doctor(db_path=db_file)
    doctor_detail = next(i.detail for i in doctor_items if i.name == "database")

    with patch("wha.service.status.connect", return_value=connect(db_file)):
        live = check_live_production_suite()
    live_detail = next(
        c["detail"] for c in live["mandatory"] if c["component"].startswith("Database")
    )

    assert f"schema v{expected}" in doctor_detail
    assert f"Schema v{expected} verified" in live_detail


def test_no_diagnostic_requires_the_deleted_forecaster() -> None:
    """`wha doctor --live` reported a subsystem that had been deleted, as MANDATORY.

    The forecaster went in item 22, and the diagnostic row did not. On any machine without
    the 182 MB of weights the row set mandatory_ok False, so `--live` printed NOT
    PRODUCTION READY and told the operator to run `wha data fetch chronos`, a command that
    now answers "There is nothing to fetch". The item's own success check was "`wha doctor`
    no longer lists Chronos"; it was verified against plain `wha doctor`, which has no such
    row, and not against `--live`, which did.

    This replaces the test that guarded the dead check, which is why the check survived
    deletion: it had a passing test, so it looked load-bearing.
    """
    from wha.service import checks as checks_module
    from wha.service import status as status_module

    assert not hasattr(checks_module, "chronos_weights_cached")
    assert not hasattr(checks_module, "CHRONOS_MODEL_ID")

    for module, label in ((status_module, "status"), (checks_module, "checks")):
        source = Path(module.__file__).read_text(encoding="utf-8")
        rows = [
            line
            for line in source.splitlines()
            if '"component"' in line and "chronos" in line.lower()
        ]
        assert not rows, f"{label}.py still declares a Chronos diagnostic row: {rows}"


# -- 4: history is scored but never alerts -------------------------------------------


def _subject_created_on(db_file: Path, created: datetime, subject_id: str = "me") -> None:
    conn = connect(db_file)
    apply_schema(conn)
    conn.execute(
        """INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
           VALUES (?, ?, 'live', 'Asia/Singapore', ?)""",
        (subject_id, subject_id, to_iso(created)),
    )
    conn.commit()
    conn.close()


def _flagged(night: date, subject_id: str = "me") -> Detection:
    return Detection(
        subject_id=subject_id,
        night_date=night,
        level=DetectionLevel.RED,
        flagged=True,
        deviation_bpm=5.0,
        explained_bpm=0.0,
        residual_bpm=5.0,
        robust_z=3.0,
        forecast=Forecast(status=ForecastStatus.NOT_RUN),
        reasons=[],
    )


def test_monitoring_since_is_the_first_sync_date(tmp_path: Path) -> None:
    db_file = tmp_path / "since.db"
    _subject_created_on(db_file, datetime(2026, 9, 3, 1, 30, tzinfo=UTC))
    conn = connect(db_file)
    assert monitoring_since(conn, "me") == date(2026, 9, 3)
    assert monitoring_since(conn, "nobody") is None
    conn.close()


def test_a_flagged_night_from_before_the_first_sync_opens_no_episode(tmp_path: Path) -> None:
    """The user's question: would it have messaged me about last Tuesday? It would have."""
    db_file = tmp_path / "backfill.db"
    first_sync = datetime(2026, 9, 3, 1, 30, tzinfo=UTC)
    _subject_created_on(db_file, first_sync)

    conn = connect(db_file)
    opened = open_episodes_for_flagged_nights(conn, "me", [_flagged(date(2026, 8, 27))])
    count = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
    conn.close()

    assert opened == []
    assert count == 0


def test_a_flagged_night_after_the_first_sync_still_opens_an_episode(tmp_path: Path) -> None:
    """The guard must not silence live monitoring, only backfilled history."""
    db_file = tmp_path / "live.db"
    first_sync = datetime(2026, 9, 3, 1, 30, tzinfo=UTC)
    _subject_created_on(db_file, first_sync)

    conn = connect(db_file)
    opened = open_episodes_for_flagged_nights(conn, "me", [_flagged(date(2026, 9, 5))])
    conn.close()

    assert len(opened) == 1


def test_a_whole_backfilled_week_opens_nothing(tmp_path: Path) -> None:
    """`wha ingest --days 7` then `wha nightly` on a new install must not alert."""
    db_file = tmp_path / "week.db"
    first_sync = datetime(2026, 9, 3, 1, 30, tzinfo=UTC)
    _subject_created_on(db_file, first_sync)
    nights = [_flagged(date(2026, 9, 3) - timedelta(days=n)) for n in range(1, 8)]

    conn = connect(db_file)
    opened = open_episodes_for_flagged_nights(conn, "me", nights)
    conn.close()

    assert opened == []


def test_an_unknown_subject_is_not_silenced(tmp_path: Path) -> None:
    """No subject row means no first-sync date, and monitoring must not be suppressed."""
    db_file = tmp_path / "unknown.db"
    conn = connect(db_file)
    apply_schema(conn)
    opened = open_episodes_for_flagged_nights(conn, "ghost", [_flagged(date(2026, 8, 1), "ghost")])
    conn.close()

    assert len(opened) == 1


# -- a demo invents a person, and must not file them among the real ones --------------


def test_a_demo_does_not_write_into_the_configured_database(tmp_path: Path) -> None:
    """Eleven demo runs put eleven synthetic subjects beside a real person's record.

    Nothing at query level marked the difference, so any query that did not filter by
    subject silently mixed fabricated readings with measured ones.
    """
    from unittest.mock import patch

    from wha.service.demo import DEMO_DB_PATH, run_demo

    real_db = tmp_path / "real.db"
    conn = connect(real_db)
    apply_schema(conn)
    conn.execute(
        """INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
           VALUES ('me', 'me', 'live', 'Asia/Singapore', ?)""",
        (to_iso(datetime.now(UTC)),),
    )
    conn.commit()
    conn.close()

    # WHA_DB_PATH is what `connect()` falls back to, so if the demo ever reaches for the
    # configured database again this points it straight at the real one.
    demo_db = tmp_path / "demo.db"
    with (
        patch.dict("os.environ", {"WHA_DB_PATH": str(real_db)}),
        patch("wha.service.demo.DEMO_DB_PATH", demo_db),
    ):
        run_demo(scenario_name="cold-start", dry_run=True)

    conn = connect(real_db)
    subjects = [r[0] for r in conn.execute("SELECT subject_id FROM subjects")]
    samples = conn.execute("SELECT COUNT(*) FROM heart_rate_samples").fetchone()[0]
    conn.close()

    assert subjects == ["me"], f"the demo leaked subjects into the real database: {subjects}"
    assert samples == 0, "the demo wrote synthetic readings into the real database"
    assert demo_db.exists(), "the demo must still have run, just somewhere else"
    assert DEMO_DB_PATH != real_db


def test_a_frozen_scenario_means_the_same_thing_whatever_ran_before_it(tmp_path: Path) -> None:
    """The demo database is reset per run, so scenario results are not order-dependent.

    The weekly interruption budget counts across every subject, which is right for a
    single-user application. In a shared demo database that made it a global allowance of
    two questions across all eleven scenarios: run back to back, the first two asked their
    question and the rest silently asked nothing and reached the wrong disposition. Each
    of those passed when run alone, so the suite reported a different result depending on
    the order it was run in.
    """
    from unittest.mock import patch

    from wha.service.demo import run_demo

    demo_db = tmp_path / "demo.db"
    demo_db.write_bytes(b"")
    stale = tmp_path / "stale-marker"

    with patch("wha.service.demo.DEMO_DB_PATH", demo_db):
        run_demo(scenario_name="cold-start", dry_run=True)
        first = connect(demo_db)
        subjects_after_first = {r[0] for r in first.execute("SELECT subject_id FROM subjects")}
        first.close()

        run_demo(scenario_name="alcohol-night", dry_run=True)
        second = connect(demo_db)
        subjects_after_second = {r[0] for r in second.execute("SELECT subject_id FROM subjects")}
        second.close()

    assert subjects_after_first == {"demo-cold-start"}
    # The earlier run's subject, and therefore its interactions and its share of the
    # weekly budget, is gone rather than carried into the next scenario.
    assert subjects_after_second == {"demo-alcohol-night"}
    assert not stale.exists()


def test_a_named_database_is_not_wiped_by_a_demo(tmp_path: Path) -> None:
    """Resetting is for the default demo file only. --db means the caller owns it."""
    from wha.service.demo import run_demo

    named = tmp_path / "mine.db"
    conn = connect(named)
    apply_schema(conn)
    conn.execute(
        """INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
           VALUES ('keep-me', 'keep me', 'synthetic', 'Asia/Singapore', ?)""",
        (to_iso(datetime.now(UTC)),),
    )
    conn.commit()
    conn.close()

    run_demo(scenario_name="cold-start", dry_run=True, db_path=named)

    conn = connect(named)
    subjects = {r[0] for r in conn.execute("SELECT subject_id FROM subjects")}
    conn.close()
    assert "keep-me" in subjects
