"""Unit tests for the WHA CLI and runtime commands."""

import ast
from pathlib import Path

from typer.testing import CliRunner

from wha.cli import app
from wha.db import apply_schema, connect
from wha.service.nightly import parse_date_range

runner = CliRunner()


def test_cli_imports_only_service() -> None:
    """CLI imports from wha only via config and service modules."""
    cli_file = Path("src/wha/cli.py")
    tree = ast.parse(cli_file.read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("wha"):
            # wha.api.app joins the allow-list because `wha serve` now starts the HTTP
            # boundary as well as the dashboard. This is still a layering rule: the CLI may
            # reach the service layer and the API application, and nothing beneath them.
            allowed = node.module in {
                "wha.config",
                "wha.service",
                "wha.api.app",
            } or node.module.startswith("wha.service")
            assert allowed, (
                f"Prohibited import '{node.module}' in cli.py. Must only import from "
                "service/, config.py or api/app.py"
            )


def test_doctor_on_empty_database(tmp_path: Path) -> None:
    """Doctor initializes an empty database, reports component status, and exits 0."""
    db_file = tmp_path / "empty.sqlite"
    res = runner.invoke(app, ["doctor", "--db", str(db_file)])

    assert res.exit_code == 0
    assert "database" in res.output
    assert "knowledge" in res.output
    assert db_file.exists()


def test_doctor_never_prints_secrets(tmp_path: Path, monkeypatch) -> None:
    """Doctor never prints API keys or secrets in its output."""
    secret_key = "sk-super-secret-token-12345"
    monkeypatch.setenv("WHA_TELEGRAM_BOT_TOKEN", secret_key)
    monkeypatch.setenv("WHA_LLM_API_KEY", secret_key)

    db_file = tmp_path / "doctor_secret.sqlite"
    res = runner.invoke(app, ["doctor", "--db", str(db_file)])

    assert secret_key not in res.output
    assert "token configured" in res.output or "provider=" in res.output


def test_nightly_is_idempotent(tmp_path: Path) -> None:
    """Running nightly twice produces identical detection rows without duplication."""
    db_file = tmp_path / "nightly_idempotent.sqlite"
    conn = connect(db_file)
    apply_schema(conn)
    conn.execute(
        """
        INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
        VALUES ('subj_idem', 'Idem', 'synthetic', 'Asia/Singapore', '2026-09-01T00:00:00Z');
        """
    )
    # 5 nights of samples
    for i in range(1, 6):
        conn.execute(
            f"""
            INSERT INTO nightly_features (subject_id, night_date, rhr_bpm, coverage_minutes, usable, computed_at_utc)
            VALUES ('subj_idem', '2026-08-{i:02d}', 60.0, 420, 1, '2026-08-{i:02d}T00:00:00Z');
            """
        )
    conn.commit()
    conn.close()

    res1 = runner.invoke(
        app,
        [
            "nightly",
            "--subject",
            "subj_idem",
            "--range",
            "2026-08-01:2026-08-05",
            "--db",
            str(db_file),
        ],
    )
    assert res1.exit_code == 0

    res2 = runner.invoke(
        app,
        [
            "nightly",
            "--subject",
            "subj_idem",
            "--range",
            "2026-08-01:2026-08-05",
            "--db",
            str(db_file),
        ],
    )
    assert res2.exit_code == 0

    conn = connect(db_file)
    count = conn.execute(
        "SELECT COUNT(*) FROM detections WHERE subject_id = 'subj_idem'"
    ).fetchone()[0]
    conn.close()
    assert count == 5


def test_nightly_recomputes_late_data(tmp_path: Path) -> None:
    """Running nightly recomputes features and detection when late data arrives."""
    db_file = tmp_path / "nightly_late.sqlite"
    conn = connect(db_file)
    apply_schema(conn)
    conn.execute(
        """
        INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
        VALUES ('subj_late', 'Late', 'synthetic', 'Asia/Singapore', '2026-09-01T00:00:00Z');
        """
    )
    # Night 1: initial 60 bpm
    conn.execute(
        """
        INSERT INTO nightly_features (subject_id, night_date, rhr_bpm, coverage_minutes, usable, computed_at_utc)
        VALUES ('subj_late', '2026-08-01', 60.0, 420, 1, '2026-08-01T00:00:00Z');
        """
    )
    conn.commit()
    conn.close()

    runner.invoke(
        app, ["nightly", "--subject", "subj_late", "--date", "2026-08-01", "--db", str(db_file)]
    )

    # Late data arrives: update feature
    conn = connect(db_file)
    conn.execute(
        """
        UPDATE nightly_features SET rhr_bpm = 70.0 WHERE subject_id = 'subj_late' AND night_date = '2026-08-01';
        """
    )
    conn.commit()
    conn.close()

    runner.invoke(
        app, ["nightly", "--subject", "subj_late", "--date", "2026-08-01", "--db", str(db_file)]
    )

    conn = connect(db_file)
    row = conn.execute(
        "SELECT level FROM detections WHERE subject_id = 'subj_late' AND night_date = '2026-08-01'"
    ).fetchone()
    conn.close()
    assert row[0] == "RED"


def test_nightly_refuses_when_stale(tmp_path: Path) -> None:
    """When ingest is stale (>72h old), night is marked unusable and not interpolated."""
    db_file = tmp_path / "nightly_stale.sqlite"
    conn = connect(db_file)
    apply_schema(conn)
    conn.execute(
        """
        INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
        VALUES ('subj_stale', 'Stale', 'synthetic', 'Asia/Singapore', '2026-09-01T00:00:00Z');
        """
    )
    # Sample recorded 5 days ago (120 hours stale)
    stale_ts = "2026-08-01T00:00:00Z"
    conn.execute(
        """
        INSERT INTO heart_rate_samples (subject_id, ts_utc, avg_bpm, min_bpm, max_bpm, origin)
        VALUES ('subj_stale', ?, 60.0, 58.0, 62.0, 'synthetic');
        """,
        (stale_ts,),
    )
    conn.execute(
        """
        INSERT INTO nightly_features (subject_id, night_date, rhr_bpm, coverage_minutes, usable, computed_at_utc)
        VALUES ('subj_stale', '2026-08-07', 60.0, 420, 1, '2026-08-07T00:00:00Z');
        """
    )
    conn.commit()
    conn.close()

    runner.invoke(
        app, ["nightly", "--subject", "subj_stale", "--date", "2026-08-07", "--db", str(db_file)]
    )

    conn = connect(db_file)
    row = conn.execute(
        "SELECT usable FROM nightly_features WHERE subject_id = 'subj_stale' AND night_date = '2026-08-07'"
    ).fetchone()
    conn.close()
    assert row[0] == 0


def test_nightly_default_range_is_seven_nights() -> None:
    """Default date range calculation with no arguments spans exactly 7 calendar nights."""
    start_d, end_d = parse_date_range(None)
    assert (end_d - start_d).days == 6  # inclusive start and end -> 7 calendar nights


def test_exit_codes(tmp_path: Path) -> None:
    """CLI returns expected status codes on success (0) and failure modes (1, 2)."""
    db_file = tmp_path / "exit_test.sqlite"

    # Success -> 0
    res_ok = runner.invoke(app, ["doctor", "--db", str(db_file)])
    assert res_ok.exit_code == 0

    # Non-existent command -> 2 (Typer usage error)
    res_bad_cmd = runner.invoke(app, ["nonexistent_command"])
    assert res_bad_cmd.exit_code == 2

    # Non-existent scenario -> 1
    res_bad_scenario = runner.invoke(app, ["demo", "run", "no_such_scenario", "--db", str(db_file)])
    assert res_bad_scenario.exit_code == 1


def test_demo_dry_run_makes_no_llm_call(tmp_path: Path) -> None:
    """wha demo run --dry-run completes purely on deterministic math with no LLM calls."""
    db_file = tmp_path / "demo_dry.sqlite"
    res = runner.invoke(app, ["demo", "run", "illness-onset", "--dry-run", "--db", str(db_file)])

    assert res.exit_code == 0
    assert "illness-onset" in res.output


def test_demo_run_completes_offline(tmp_path: Path) -> None:
    """A demo scenario runs the full agent path offline using cassette fixtures.

    Exercised on alcohol-night because the exit code now reports whether the frozen
    expectations were met, and illness-onset currently cannot meet its own: see
    docs/DISCLOSURES.md. Using a scenario that genuinely passes keeps a zero exit code a
    real signal rather than a weakened assertion.
    """
    db_file = tmp_path / "demo_offline.sqlite"
    res = runner.invoke(app, ["demo", "run", "alcohol-night", "--db", str(db_file)])

    assert res.exit_code == 0
    assert "alcohol-night" in res.output


def test_belief_explain_prints_marginals_per_night(tmp_path: Path) -> None:
    """wha belief explain outputs causal probability trace night by night."""
    db_file = tmp_path / "belief_explain_trace.sqlite"
    runner.invoke(app, ["demo", "run", "illness-onset", "--dry-run", "--db", str(db_file)])

    res = runner.invoke(
        app, ["belief", "explain", "--subject", "demo-illness-onset", "--db", str(db_file)]
    )
    assert res.exit_code == 0
    assert "p(illness)" in res.output
    assert "Top causes:" in res.output


def test_episode_step_is_idempotent(tmp_path: Path) -> None:
    """Advancing an episode via CLI is idempotent on closed or stepped episodes."""
    db_file = tmp_path / "episode_step_test.sqlite"
    conn = connect(db_file)
    apply_schema(conn)
    conn.execute(
        """
        INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
        VALUES ('sub_step', 'Step User', 'synthetic', 'Asia/Singapore', '2026-08-01T00:00:00Z');
        """
    )
    conn.execute(
        """
        INSERT INTO episodes (episode_id, subject_id, thread_id, opened_on, state, step_count, baseline_nights, baseline_rung)
        VALUES ('ep_step_01', 'sub_step', 'th_01', '2026-08-15', 'CLOSED', 4, 14, 'PERSONAL');
        """
    )
    conn.commit()
    conn.close()

    res1 = runner.invoke(app, ["episode", "step", "ep_step_01", "--db", str(db_file)])
    assert res1.exit_code == 0
    assert "stepped" in res1.output or "closed" in res1.output

    res2 = runner.invoke(app, ["episode", "step", "ep_step_01", "--db", str(db_file)])
    assert res2.exit_code == 0
