"""Command-line interface for Wearable Health Early Warning Agent."""

import json
import sys
from pathlib import Path
from typing import Annotated

import typer

from wha.service import (
    ConfigError,
    SourceUnavailable,
    explain_belief,
    fetch_data,
    run_demo,
    run_doctor,
    run_ingest,
    run_nightly,
)

app = typer.Typer(
    name="wha",
    help="Wearable Health Early Warning Agent: agentic early-warning and causal attribution.",
    no_args_is_help=True,
)

demo_app = typer.Typer(help="Run demonstration scenarios.")
app.add_typer(demo_app, name="demo")

belief_app = typer.Typer(help="Explain causal belief evolution.")
app.add_typer(belief_app, name="belief")

data_app = typer.Typer(help="Fetch external datasets and foundation models.")
app.add_typer(data_app, name="data")


@app.command("doctor")
def doctor(
    db: Annotated[Path | None, typer.Option("--db", help="Path to database")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Check all system components, models, and knowledge tables."""
    try:
        items = run_doctor(db_path=db)
    except ConfigError as e:
        typer.echo(f"Configuration error: {e}", err=True)
        sys.exit(3)
    except Exception as e:  # noqa: BLE001
        typer.echo(f"Doctor error: {e}", err=True)
        sys.exit(1)

    if as_json:
        out = [{"name": i.name, "status": i.status, "detail": i.detail} for i in items]
        typer.echo(json.dumps(out, indent=2))
    else:
        for item in items:
            status_padded = item.status.ljust(6)
            name_padded = item.name.ljust(15)
            typer.echo(f"{name_padded} {status_padded} {item.detail}")

    has_fail = any(i.status == "fail" for i in items)
    if has_fail:
        sys.exit(1)
    sys.exit(0)


@app.command("ingest")
def ingest(
    subject: Annotated[str | None, typer.Option("--subject", "-s", help="Subject ID")] = None,
    days: Annotated[int, typer.Option("--days", "-d", help="Number of days to pull")] = 7,
    db: Annotated[Path | None, typer.Option("--db", help="Path to database")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Pull, store, and normalise samples from the configured data source."""
    try:
        count = run_ingest(subject_id=subject, days=days, db_path=db)
    except SourceUnavailable as e:
        typer.echo(f"Source unavailable: {e}", err=True)
        sys.exit(1)
    except Exception as e:  # noqa: BLE001
        typer.echo(f"Ingest failed: {e}", err=True)
        sys.exit(1)

    if as_json:
        typer.echo(json.dumps({"status": "ok", "stored_records": count}))
    else:
        typer.echo(f"Successfully stored and normalised {count} records.")
    sys.exit(0)


@app.command("nightly")
def nightly(
    subject: Annotated[str | None, typer.Option("--subject", "-s", help="Subject ID")] = None,
    date_val: Annotated[
        str | None, typer.Option("--date", help="Single night date (YYYY-MM-DD)")
    ] = None,
    range_val: Annotated[
        str | None, typer.Option("--range", help="Date range (YYYY-MM-DD:YYYY-MM-DD)")
    ] = None,
    db: Annotated[Path | None, typer.Option("--db", help="Path to database")] = None,
    no_ingest: Annotated[bool, typer.Option("--no-ingest", help="Skip source ingest")] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Run deterministic nightly feature extraction, baseline update, and detection."""
    target_date_range = date_val if date_val else range_val
    try:
        dets = run_nightly(
            subject_id=subject,
            date_or_range=target_date_range,
            db_path=db,
            no_ingest=no_ingest,
        )
    except Exception as e:  # noqa: BLE001
        typer.echo(f"Nightly run error: {e}", err=True)
        sys.exit(1)

    if as_json:
        out = [
            {
                "night_date": d.night_date.isoformat(),
                "level": d.level,
                "flagged": d.flagged,
                "residual_bpm": d.residual_bpm,
            }
            for d in dets
        ]
        typer.echo(json.dumps(out, indent=2))
    else:
        for d in dets:
            res_str = f"{d.residual_bpm} bpm" if d.residual_bpm is not None else "N/A"
            typer.echo(
                f"{d.night_date} | Level: {d.level.ljust(6)} | Flagged: {str(d.flagged).ljust(5)} | Residual: {res_str}"
            )
    sys.exit(0)


@demo_app.command("run")
def demo_run(
    scenario: Annotated[str, typer.Argument(help="Scenario name (e.g. illness-onset)")],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Run deterministic batch with no LLM calls")
    ] = False,
    live: Annotated[bool, typer.Option("--live", help="Run against live provider")] = False,
    db: Annotated[Path | None, typer.Option("--db", help="Path to database")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Run a demo scenario end-to-end."""
    try:
        res = run_demo(scenario_name=scenario, dry_run=dry_run, live=live, db_path=db)
    except Exception as e:  # noqa: BLE001
        typer.echo(f"Demo failed: {e}", err=True)
        sys.exit(1)

    if as_json:
        out = {
            "scenario": res.scenario,
            "subject": res.subject_id,
            "dry_run": res.dry_run,
            "nights": [
                {
                    "date": n.night_date.isoformat(),
                    "level": n.level,
                    "flagged": n.flagged,
                    "residual_bpm": n.residual_bpm,
                }
                for n in res.nights
            ],
        }
        typer.echo(json.dumps(out, indent=2))
    else:
        typer.echo(f"--- Demo scenario '{res.scenario}' ({len(res.nights)} nights) ---")
        for n in res.nights:
            res_str = f"{n.residual_bpm} bpm" if n.residual_bpm is not None else "N/A"
            typer.echo(
                f"{n.night_date} | {n.level.ljust(6)} | Flagged: {str(n.flagged).ljust(5)} | Residual: {res_str}"
            )
    sys.exit(0)


@belief_app.command("explain")
def belief_explain(
    subject: Annotated[str | None, typer.Option("--subject", "-s", help="Subject ID")] = None,
    nights: Annotated[
        str | None, typer.Option("--nights", help="Night range (YYYY-MM-DD:YYYY-MM-DD)")
    ] = None,
    episode: Annotated[str | None, typer.Option("--episode", help="Episode ID")] = None,
    db: Annotated[Path | None, typer.Option("--db", help="Path to database")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Explain evolving causal belief over a range of nights."""
    try:
        records = explain_belief(
            subject_id=subject,
            date_or_range=nights,
            episode_id=episode,
            db_path=db,
        )
    except Exception as e:  # noqa: BLE001
        typer.echo(f"Belief explain error: {e}", err=True)
        sys.exit(1)

    if as_json:
        out = [
            {
                "night_date": r.night_date.isoformat(),
                "residual_bpm": r.residual_bpm,
                "p_illness": r.p_illness,
                "top_causes": [{"cause": c, "prob": p} for c, p in r.top_causes],
            }
            for r in records
        ]
        typer.echo(json.dumps(out, indent=2))
    else:
        typer.echo(f"Causal belief trace ({len(records)} nights):")
        for r in records:
            top_str = ", ".join(f"{c}={p:.2f}" for c, p in r.top_causes)
            typer.echo(f"{r.night_date} | p(illness)={r.p_illness:.3f} | Top causes: {top_str}")
    sys.exit(0)


@data_app.command("fetch")
def data_fetch_cmd(
    target: Annotated[
        str, typer.Argument(help="Dataset or model name (chronos, stanford, pmdata, corpus)")
    ],
) -> None:
    """Fetch and verify external datasets or model weights."""
    try:
        msg = fetch_data(target=target)
        typer.echo(msg)
    except Exception as e:  # noqa: BLE001
        typer.echo(f"Data fetch error: {e}", err=True)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    app()
