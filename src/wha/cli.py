"""Command-line interface for Wearable Health Early Warning Agent."""

import json
import os
import sys
from pathlib import Path
from typing import Annotated

import typer

from wha.service import (
    DEFAULT_INGEST_DAYS,
    DEMO_DB_PATH,
    ConfigError,
    SourceUnavailable,
    build_corpus_file,
    describe_device_capability,
    explain_belief,
    fetch_data,
    get_monitoring_since,
    get_service_settings,
    list_episodes,
    run_demo,
    run_doctor,
    run_evaluation_suite,
    run_ingest,
    run_nightly,
    search_corpus,
    send_message,
    source_label,
    step_episode,
    write_evaluation_report,
)
from wha.service.doctor import DoctorItem

app = typer.Typer(
    name="wha",
    help="Wearable Health Early Warning Agent: agentic early-warning and causal attribution.",
    no_args_is_help=True,
)

demo_app = typer.Typer(help="Run demonstration scenarios.")
app.add_typer(demo_app, name="demo")

belief_app = typer.Typer(help="Explain causal belief evolution.")
app.add_typer(belief_app, name="belief")

episode_app = typer.Typer(help="Manage and step agent episodes.")
app.add_typer(episode_app, name="episode")

data_app = typer.Typer(help="Fetch external datasets and foundation models.")
app.add_typer(data_app, name="data")

llm_app = typer.Typer(help="Manage LLM provider and cassette fixtures.")
app.add_typer(llm_app, name="llm")

corpus_app = typer.Typer(help="Inspect the clinical corpus the agent retrieves from.")
app.add_typer(corpus_app, name="corpus")


# Reported by both halves of `doctor --live`. The offline row and the live row make the
# same claim for these, so only the live row is printed.
LIVE_PROBE_DUPLICATES = {"database", "knowledge", "chronos", "datasets"}


@app.command("doctor")
def doctor(
    db: Annotated[Path | None, typer.Option("--db", help="Path to database")] = None,
    live: Annotated[
        bool, typer.Option("--live", help="Execute live network and hardware probe checks")
    ] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Check all system components, models, and knowledge tables.

    ``--live`` is this same check plus the probes that need the network and the phone. It
    used to be a wholly separate diagnostic that merely shared the name: different checks,
    a different output format, its own verdict, and nothing telling you which to run.
    """
    try:
        items = run_doctor(db_path=db)
    except ConfigError as e:
        typer.echo(f"Configuration error: {e}", err=True)
        sys.exit(3)
    except Exception as e:  # noqa: BLE001
        typer.echo(f"Doctor error: {e}", err=True)
        sys.exit(1)

    if live:
        _render_live_report(as_json=as_json, offline_items=items)
        return

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


@app.command("check-live")
def check_live(
    as_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Execute live diagnostic tests across mandatory and optional production subsystems.

    Alias for ``wha doctor --live``.
    """
    try:
        items = run_doctor()
    except Exception:  # noqa: BLE001
        items = []
    _render_live_report(as_json=as_json, offline_items=items)


def _render_live_report(as_json: bool, offline_items: list[DoctorItem]) -> None:
    """Print the configuration checks and the live probes as one report with one verdict.

    The configuration checks belong in this report rather than in a separate command.
    Running only the live probes meant ``--live`` could print PRODUCTION READY while
    ``doctor`` reported a local failure, and nothing told the operator to run both.
    """
    from wha.service.status import check_live_production_suite

    try:
        res = check_live_production_suite()
    except Exception as e:  # noqa: BLE001
        typer.echo(f"Live diagnostic error: {e}", err=True)
        sys.exit(1)

    offline_failed = [i for i in offline_items if i.status == "fail"]

    if as_json:
        res = dict(res)
        res["configuration"] = [
            {"name": i.name, "status": i.status, "detail": i.detail} for i in offline_items
        ]
        res["configuration_ok"] = not offline_failed
        typer.echo(json.dumps(res, default=str, indent=2))
    else:
        typer.echo("=" * 80)
        typer.echo("CLINICAL PRODUCTION SYSTEM DIAGNOSTIC & HEALTH SUITE")
        typer.echo("=" * 80)
        typer.echo("\n[CONFIGURATION AND LOCAL STATE]")
        for i in offline_items:
            # Facts the live probes restate below are dropped rather than printed twice.
            # Bridge, LLM and Telegram deliberately stay: the offline row says credentials
            # are configured, the live row says the service answered, and those are
            # different claims. Database, knowledge, chronos and datasets said the same
            # thing in both sections, which made the report longer without being clearer.
            if i.name in LIVE_PROBE_DUPLICATES:
                continue
            symbol = {"ok": "[PASS]", "fail": "[FAIL]", "warn": "[WARN]"}.get(i.status, "[INFO]")
            typer.echo(f"  {symbol:<8}  {i.name:<36} -> {i.detail}")
        typer.echo("\n[MANDATORY PRODUCTION SUBSYSTEMS]")
        for c in res["mandatory"]:
            status_symbol = "[PASS]" if c["ok"] else "[FAIL]"
            component_name = c["component"]
            detail = c["detail"]
            typer.echo(f"  {status_symbol:<8}  {component_name:<36} -> {detail}")

        typer.echo("\n[OPTIONAL / ADVISORY SUBSYSTEMS]")
        for c in res["optional"]:
            # Advisory by definition, so absence is INFO. The same fact appeared as INFO
            # in one section and WARN in the other.
            status_symbol = "[INFO]"
            component_name = c["component"]
            detail = c["detail"]
            typer.echo(f"  {status_symbol:<8}  {component_name:<36} -> {detail}")

        typer.echo("\n" + "=" * 80)
        if res["mandatory_ok"] and not offline_failed:
            typer.echo("RESULT: ALL MANDATORY SUBSYSTEMS OPERATIONAL. PRODUCTION READY.")
        elif offline_failed:
            names = ", ".join(i.name for i in offline_failed)
            typer.echo(f"RESULT: CRITICAL - LOCAL CONFIGURATION FAILED: {names}")
        else:
            typer.echo("RESULT: CRITICAL - ONE OR MORE MANDATORY SUBSYSTEMS FAILED.")
        typer.echo("=" * 80)

    if not res["mandatory_ok"] or offline_failed:
        sys.exit(1)
    sys.exit(0)


@app.command("tell")
def tell(
    text: Annotated[str, typer.Argument(help="How you are feeling, in your own words")],
    subject: Annotated[str | None, typer.Option("--subject", "-s", help="Subject ID")] = None,
) -> None:
    """Tell the system how you are feeling, without waiting to be asked.

    The deterministic safety floor runs on free text: phrases like chest pain or not being
    able to keep fluids down escalate immediately, before any model is consulted. That
    floor could only ever be reached through a question the agent chose to ask, and the
    agent frequently chooses not to ask. Someone with chest pain had no way to say so.

    ONE PATH, as of 5 September 2026. This used to call `report_symptoms`, a second
    implementation of "check what the person said and escalate" that behaved differently
    from the conversation engine the dashboard and Telegram use. "I have chest pain" typed
    here went straight to an ambulance; typed in the dashboard it opened a Marburg
    conversation. It now goes through `send_message`, so all three surfaces behave the same
    way and repeat reports append to one investigation instead of opening a new one each
    time.
    """
    reply = send_message(subject_id=subject or get_service_settings().subject, text=text)

    typer.echo("")
    if reply.urgency == "urgent":
        typer.echo("  THIS NEEDS MEDICAL ATTENTION")
    elif reply.urgency == "same_day":
        typer.echo("  YOU SHOULD SEE A DOCTOR TODAY")

    typer.echo(f"  {reply.text}")

    if reply.uncited:
        typer.echo("")
        typer.echo("  Not from a cited source, worth checking:")
        for note in reply.uncited:
            typer.echo(f"    {note}")

    if reply.citations:
        typer.echo("")
        typer.echo("  Sources:")
        for citation in reply.citations:
            typer.echo(f"    {citation.title} ({source_label(citation.source_id)})")

    typer.echo("")
    sys.exit(0)


@app.command("ingest")
def ingest(
    subject: Annotated[str | None, typer.Option("--subject", "-s", help="Subject ID")] = None,
    # The watch holds roughly a month, and how many nights arrive decides how much the
    # baseline is the person rather than a population prior: 3 to 6 nights is
    # PRIOR_DOMINATED and below the 5-night floor Chronos needs. A default of 7 left
    # someone who typed the documented command short of data their watch was already
    # holding, and gave a different result from the startup catch up. Asking for more days than the watch has is harmless: the
    # bridge returns what it has and the missing nights are simply unusable.
    days: Annotated[
        int, typer.Option("--days", "-d", help="Number of days to pull")
    ] = DEFAULT_INGEST_DAYS,
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
        # Which nights the system was actually watching, and which are history it was
        # handed on first sync. Without this the two are indistinguishable in the output,
        # and a first run looks like a week of live monitoring that never happened.
        started = get_monitoring_since(subject_id=subject, db_path=db)
        history = 0
        for d in dets:
            res_str = f"{d.residual_bpm} bpm" if d.residual_bpm is not None else "N/A"
            if started is not None and d.night_date < started:
                origin = "history "
                history += 1
            else:
                origin = "watched "
            typer.echo(
                f"{d.night_date} | {origin}| Level: {d.level.ljust(6)} | "
                f"Flagged: {str(d.flagged).ljust(5)} | Residual: {res_str}"
            )
        if started is not None and history:
            typer.echo("")
            typer.echo(
                f"{history} night(s) marked history: recorded before monitoring began on "
                f"{started}. They build your baseline and cannot raise an alert."
            )
    sys.exit(0)


@demo_app.command("list")
def demo_list() -> None:
    """List available scenario demonstration fixtures."""
    scenarios_dir = Path("tests/fixtures/scenarios")
    if not scenarios_dir.exists():
        typer.echo("No scenario fixtures directory found.")
        sys.exit(1)

    scenarios = sorted([f.stem for f in scenarios_dir.glob("*.json")])
    typer.echo("Available scenario fixtures:")
    for s in scenarios:
        typer.echo(f"  - {s}")
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
            "episode_ids": res.episode_ids,
            "disposition": res.disposition,
            "questions_asked": res.questions_asked,
            "escalated": res.escalated,
            "expectations": [
                {"name": e.name, "expected": e.expected, "actual": e.actual, "ok": e.ok}
                for e in res.expectations
            ],
            "ok": res.ok,
        }
        typer.echo(json.dumps(out, indent=2))
    else:
        where = db if db is not None else DEMO_DB_PATH
        typer.echo(f"--- Demo scenario '{res.scenario}' ({len(res.nights)} nights) ---")
        typer.echo(f"    Synthetic subject '{res.subject_id}', written to {where}.")
        for n in res.nights:
            res_str = f"{n.residual_bpm} bpm" if n.residual_bpm is not None else "N/A"
            typer.echo(
                f"{n.night_date} | {n.level.ljust(6)} | Flagged: {str(n.flagged).ljust(5)} | Residual: {res_str}"
            )

        typer.echo("")
        typer.echo(f"Episodes opened : {len(res.episode_ids)}")
        typer.echo(f"Disposition     : {res.disposition or '-'}")
        typer.echo(f"Questions asked : {res.questions_asked}")
        typer.echo(f"Escalated       : {res.escalated}")

        if res.expectations:
            typer.echo("")
            typer.echo("Frozen expectations:")
            for e in res.expectations:
                mark = "PASS" if e.ok else "FAIL"
                typer.echo(f"  [{mark}] {e.name}: expected {e.expected!r}, got {e.actual!r}")

    # The exit code is the contract. Returning zero regardless of the expectations meant
    # every scenario reported success while doing nothing the fixture asked for.
    if not res.ok:
        failed = [e.name for e in res.expectations if not e.ok]
        typer.echo(
            f"Scenario '{res.scenario}' did not meet its frozen expectations: {', '.join(failed)}",
            err=True,
        )
        sys.exit(1)

    sys.exit(0)


@belief_app.command("explain")
def belief_explain(
    subject: Annotated[str | None, typer.Option("--subject", "-s", help="Subject ID")] = None,
    nights: Annotated[
        str | None, typer.Option("--nights", help="Night range (YYYY-MM-DD:YYYY-MM-DD)")
    ] = None,
    episode: Annotated[str | None, typer.Option("--episode", help="Episode ID or 'latest'")] = None,
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


@episode_app.command("step")
def episode_step_cmd(
    episode_id: Annotated[str, typer.Argument(help="Episode ID to advance by one step")],
    db: Annotated[Path | None, typer.Option("--db", help="Path to database")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Advance one episode by one step synchronously."""
    try:
        res = step_episode(episode_id=episode_id, db_path=db)
    except Exception as e:  # noqa: BLE001
        typer.echo(f"Episode step error: {e}", err=True)
        sys.exit(1)

    if as_json:
        typer.echo(json.dumps(res, indent=2))
    else:
        typer.echo(
            f"Episode '{episode_id}' stepped. Status: {res.get('status', 'stepped')}, Step count: {res.get('step_count')}"
        )
    sys.exit(0)


@episode_app.command("list")
def episode_list_cmd(
    subject: Annotated[str | None, typer.Option("--subject", "-s", help="Subject ID")] = None,
    db: Annotated[Path | None, typer.Option("--db", help="Path to database")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """List open and historical episodes for a subject."""
    try:
        subj_id = subject or "me"
        episodes = list_episodes(subject_id=subj_id, db_path=db)
    except Exception as e:  # noqa: BLE001
        typer.echo(f"Episode list error: {e}", err=True)
        sys.exit(1)

    if as_json:
        out = [ep.model_dump(mode="json") for ep in episodes]
        typer.echo(json.dumps(out, indent=2))
    else:
        typer.echo(f"Episodes for subject '{subj_id}' ({len(episodes)} total):")
        for ep in episodes:
            cause_str = f"{ep.top_cause} ({ep.top_probability:.2f})" if ep.top_cause else "N/A"
            typer.echo(
                f"{ep.episode_id} | State: {ep.state.ljust(12)} | Disp: {str(ep.disposition).ljust(18)} | Top cause: {cause_str}"
            )
    sys.exit(0)


@llm_app.command("record")
def llm_record_cmd(
    scenario: Annotated[
        str, typer.Option("--scenario", help="Scenario fixture name to record")
    ] = "illness-onset",
) -> None:
    """Record LLM prompt cassettes for a scenario against live provider."""
    typer.echo(f"Recording cassettes for scenario '{scenario}'...")
    try:
        run_demo(scenario_name=scenario, dry_run=False, live=True)
        typer.echo(f"Cassettes recorded successfully for scenario '{scenario}'.")
    except Exception as e:  # noqa: BLE001
        typer.echo(f"Recording failed: {e}", err=True)
        sys.exit(1)
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


@data_app.command("capability")
def data_capability_cmd(
    subject: Annotated[str | None, typer.Option("--subject", "-s", help="Subject ID")] = None,
    db: Annotated[Path | None, typer.Option("--db", help="Path to database")] = None,
) -> None:
    """Show what your watch sends, and how far each channel gets.

    Answers a question the dashboard cannot: which of the sixty-odd Health Connect
    channels your device actually populates, which of those this build parses, and which
    reach the decision.
    """
    try:
        typer.echo(describe_device_capability(subject_id=subject, db_path=db))
    except Exception as e:  # noqa: BLE001
        typer.echo(f"Capability check failed: {e}", err=True)
        sys.exit(1)
    sys.exit(0)


@corpus_app.command("build")
def corpus_build_cmd(
    out: Annotated[
        Path | None, typer.Option("--out", help="Where to write the rendered corpus")
    ] = None,
) -> None:
    """Render the corpus to YAML so a human can read exactly what the agent may cite.

    The running system does not read this file. It builds the same documents in memory
    from causes.yaml, red_flags.yaml, probes.yaml and constants.py. The file exists so
    that the passages behind a clinical claim can be reviewed and diffed rather than
    taken on trust, which for a health system is the whole point of having a corpus.
    """
    try:
        target, by_layer = build_corpus_file(out_path=out)
    except Exception as e:  # noqa: BLE001
        typer.echo(f"Corpus build failed: {e}", err=True)
        sys.exit(1)

    typer.echo(f"Wrote {sum(by_layer.values())} documents to {target}")
    for layer in sorted(by_layer):
        typer.echo(f"  layer {layer}: {by_layer[layer]} documents")
    sys.exit(0)


@corpus_app.command("search")
def corpus_search_cmd(
    query: Annotated[str, typer.Argument(help="What to look up")],
    top_k: Annotated[int, typer.Option("--top-k", help="How many passages")] = 5,
) -> None:
    """Search the corpus the way the agent does, to see what it would find."""
    try:
        results = search_corpus(query, top_k=top_k)
    except Exception as e:  # noqa: BLE001
        typer.echo(f"Corpus search failed: {e}", err=True)
        sys.exit(1)

    if not results:
        typer.echo("No passages matched.")
        sys.exit(0)
    for r in results:
        typer.echo(f"[{r['rank']}] {r['chunk_id']}  (layer {r['layer']}, score {r['score']:.4f})")
        typer.echo(f"     {r['title']}")
        typer.echo(f"     {r['text'][:200]}")
        typer.echo("")
    sys.exit(0)


@app.command("eval-report")
def eval_report_cmd(
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Where to write the report")
    ] = None,
) -> None:
    """Run the offline evaluation suites and write experiments/detection/RESULTS.md.

    Evaluation results live in a file rather than a dashboard page. The dashboard is for
    a person checking their own health; how our own code scores against our own comparator
    policies is evidence for someone assessing the system, and reads better in the
    repository.

    It is written UNDER experiments/, never at the repository root. It used to be
    EVALUATION.md beside the README, where a reader met it as though it stated how well
    the system works. It does not: it is a self-scored run against labels we supplied.
    """
    try:
        written = write_evaluation_report(output_path=output)
    except Exception as e:  # noqa: BLE001
        typer.echo(f"Evaluation report failed: {e}", err=True)
        sys.exit(1)

    typer.echo(f"Wrote {written}")
    sys.exit(0)


@app.command("eval")
def eval_cmd(
    suite: Annotated[
        str,
        typer.Argument(help="Evaluation suite name (detection, baseline-age, policy, ablation)"),
    ],
    as_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Execute offline evaluation suites and benchmark comparisons."""
    try:
        res = run_evaluation_suite(suite=suite)
    except ConfigError as e:
        typer.echo(f"Evaluation skipped / error: {e}", err=True)
        sys.exit(1)
    except Exception as e:  # noqa: BLE001
        typer.echo(f"Evaluation failed: {e}", err=True)
        sys.exit(1)

    if as_json:
        typer.echo(res.model_dump_json(indent=2))
    else:
        typer.echo(f"=== Evaluation Suite: {res.suite} ===")
        for k, v in res.metrics.items():
            typer.echo(f"{k.ljust(30)}: {v}")
        if res.caveats:
            typer.echo("\nCaveats:")
            for c in res.caveats:
                typer.echo(f"- {c}")


def _run_api(host: str, port: int) -> None:
    """Serve the HTTP boundary in-process, so `wha serve` remains one command."""
    import uvicorn

    from wha.api.app import app as api_app

    uvicorn.run(api_app, host=host, port=port, log_level="warning")


@app.command("serve")
def serve_cmd(
    port: Annotated[int, typer.Option("--port", "-p", help="Port to bind the HTTP API")] = 8500,
    host: Annotated[
        str, typer.Option("--host", help="Host address to bind the HTTP API")
    ] = "127.0.0.1",
    no_scheduler: Annotated[
        bool, typer.Option("--no-scheduler", help="Disable background scheduler")
    ] = False,
    db: Annotated[Path | None, typer.Option("--db", help="Path to database")] = None,
) -> None:
    """Start the HTTP API and the background scheduler.

    The Streamlit dashboard that used to run alongside this was archived to
    ``archive/streamlit-ui-2026-09-27/`` on 27 September 2026, once the React frontend under
    ``frontend/`` became a working, independent client of this same API. This command no
    longer launches a dashboard process at all; run the frontend separately with
    ``npm run dev`` inside ``frontend/``.
    """
    import socket

    from wha.service import create_scheduler

    if db is not None:
        # The API resolves its own db path from this env var (see wha.config.Settings),
        # not from this command's arguments, so --db has to reach it this way to have any
        # effect on what the API actually serves. Set before create_scheduler() runs, since
        # get_settings() caches its first read for the rest of the process.
        os.environ["WHA_DB_PATH"] = str(db)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        in_use = s.connect_ex((host, port)) == 0
        if in_use:
            typer.echo(f"Port {port} is already in use.", err=True)
            sys.exit(2)

    scheduler = None
    if not no_scheduler:
        from wha.service.scheduler import scheduled_job_summary

        scheduler = create_scheduler(db_path=db)
        scheduler.start()
        # Read off the scheduler rather than written by hand: the hardcoded list said three
        # jobs while four were running, so the only place describing the background work
        # was already wrong.
        typer.echo(f"Background scheduler started ({scheduled_job_summary(scheduler)}).")
        typer.echo(
            "Pulling from your watch and scoring the nights it returns. "
            "This runs now and then repeats on a schedule."
        )

    # Bound to localhost and unauthenticated on purpose: one person, one machine, their own
    # health record. Exposing it on a network would need authentication first.
    typer.echo(f"API on http://{host}:{port} (docs at /docs).")
    typer.echo("No dashboard is started by this command. For the frontend:")
    typer.echo("  cd frontend && npm run dev")

    try:
        _run_api(host=host, port=port)
    except KeyboardInterrupt:
        typer.echo("\nShutting down serve...")
    finally:
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=False)
    sys.exit(0)


if __name__ == "__main__":
    app()
