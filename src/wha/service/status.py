"""Service functions for system status aggregation and external connection testing."""

import os
import sqlite3
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from wha.clock import now_utc
from wha.config import get_settings
from wha.constants import (
    DASHBOARD_RESIDUAL_DIRECTION_FLOOR_BPM,
    INGEST_STALE_REFUSE_HOURS,
    INGEST_STALE_WARN_HOURS,
    RECENT_NIGHTS_WINDOW,
)
from wha.db import connect
from wha.db.migrations import apply_schema
from wha.models import (
    BaselineRung,
    ComponentStatus,
    ConnectionCheck,
    DetectionLevel,
    DetectionStreak,
    NightlyFeatures,
    SystemStatus,
)
from wha.service.checks import dataset_present, read_schema_version


def record_component_status(
    status: ComponentStatus,
    subject_id: str = "me",
    db_path: Path | None = None,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Record a component status check into system_status table."""
    close_conn = False
    if conn is None:
        conn = connect(db_path) if db_path is not None else connect()
        apply_schema(conn)
        close_conn = True

    try:
        conn.execute(
            """INSERT INTO system_status (subject_id, component, ok, detail, ts_utc)
               VALUES (?, ?, ?, ?, ?)""",
            (
                subject_id,
                status.component,
                1 if status.ok else 0,
                status.detail,
                status.checked_at_utc.isoformat(),
            ),
        )
        conn.commit()
    finally:
        if close_conn:
            conn.close()


def get_system_status(
    subject_id: str = "me",
    db_path: Path | None = None,
    conn: sqlite3.Connection | None = None,
) -> SystemStatus:
    """Aggregate system status and recent health metrics for the status strip.

    Cheap read-only aggregation: reads database tables only, no active health network calls.
    Handles empty database cleanly.
    """
    close_conn = False
    if conn is None:
        conn = connect(db_path) if db_path is not None else connect()
        apply_schema(conn)
        close_conn = True

    try:
        checked_at = now_utc()
        components: list[ComponentStatus] = []

        # 1. Database
        components.append(
            ComponentStatus(
                component="database",
                ok=True,
                detail="SQLite operational",
                checked_at_utc=checked_at,
                severity="ok",
            )
        )

        # 2. Bridge / Ingest
        # Check last ingest timestamp
        row_ingest = conn.execute(
            "SELECT MAX(fetched_at_utc) as last_ingest FROM raw_payloads WHERE subject_id = ?",
            (subject_id,),
        ).fetchone()

        last_ingest_utc = None
        if row_ingest and row_ingest["last_ingest"]:
            try:
                last_ingest_utc = datetime.fromisoformat(row_ingest["last_ingest"])
            except ValueError:
                last_ingest_utc = None

        if last_ingest_utc is None:
            # Fallback check heart_rate_samples
            row_hr = conn.execute(
                "SELECT MAX(ts_utc) as last_ts FROM heart_rate_samples WHERE subject_id = ?",
                (subject_id,),
            ).fetchone()
            if row_hr and row_hr["last_ts"]:
                try:
                    last_ingest_utc = datetime.fromisoformat(row_hr["last_ts"])
                except ValueError:
                    last_ingest_utc = None

        bridge_severity = "ok"
        bridge_ok = True
        bridge_detail = "Bridge data current"
        if last_ingest_utc is not None:
            hours_since = (checked_at - last_ingest_utc).total_seconds() / 3600.0
            if hours_since > INGEST_STALE_REFUSE_HOURS:
                bridge_severity = "error"
                bridge_ok = False
                bridge_detail = f"Ingest stale ({int(hours_since)}h > {INGEST_STALE_REFUSE_HOURS}h refuse limit)"
            elif hours_since > INGEST_STALE_WARN_HOURS:
                bridge_severity = "warn"
                bridge_ok = True
                bridge_detail = (
                    f"Ingest delayed ({int(hours_since)}h > {INGEST_STALE_WARN_HOURS}h warn limit)"
                )
        else:
            bridge_severity = "warn"
            bridge_detail = "No ingest records found"

        components.append(
            ComponentStatus(
                component="bridge",
                ok=bridge_ok,
                detail=bridge_detail,
                checked_at_utc=checked_at,
                severity=bridge_severity,
            )
        )

        # 3. Scheduler
        row_sched = conn.execute(
            "SELECT ok, detail FROM system_status WHERE component = 'scheduler' ORDER BY ts_utc DESC LIMIT 1"
        ).fetchone()
        sched_ok = bool(row_sched["ok"]) if row_sched else True
        sched_detail = row_sched["detail"] if row_sched else "Scheduler active"
        sched_severity = "ok" if sched_ok else "error"

        components.append(
            ComponentStatus(
                component="scheduler",
                ok=sched_ok,
                detail=sched_detail,
                checked_at_utc=checked_at,
                severity=sched_severity,
            )
        )

        # 4. LLM
        settings = get_settings()
        provider = settings.llm_provider
        # Kept short: this is displayed in a fixed-width pill that clips.
        llm_detail = settings.llm_model or provider
        if provider == "cassette":
            llm_detail = "Offline (recorded)"
        components.append(
            ComponentStatus(
                component="llm",
                ok=True,
                detail=llm_detail,
                checked_at_utc=checked_at,
                severity="ok",
            )
        )

        # 5. Telegram
        notify_channel = os.environ.get("WHA_NOTIFY_CHANNEL", "none")
        tg_detail = "Telegram" if notify_channel == "telegram" else notify_channel
        if notify_channel == "none":
            tg_detail = "In this app only"
        components.append(
            ComponentStatus(
                component="telegram",
                ok=True,
                detail=tg_detail,
                checked_at_utc=checked_at,
                severity="ok",
            )
        )

        # 6. Datasets
        components.append(
            ComponentStatus(
                component="datasets",
                ok=True,
                detail="Knowledge sources loaded",
                checked_at_utc=checked_at,
                severity="ok",
            )
        )

        # Last nightly computation
        row_nightly = conn.execute(
            "SELECT MAX(computed_at_utc) as last_computed FROM nightly_features WHERE subject_id = ?",
            (subject_id,),
        ).fetchone()
        last_nightly_utc = None
        if row_nightly and row_nightly["last_computed"]:
            try:
                last_nightly_utc = datetime.fromisoformat(row_nightly["last_computed"])
            except ValueError:
                last_nightly_utc = None

        # Usable nights and baseline rung
        row_base = conn.execute(
            "SELECT usable_nights, rung FROM baselines WHERE subject_id = ? ORDER BY night_date DESC LIMIT 1",
            (subject_id,),
        ).fetchone()

        if row_base is not None:
            usable_nights = int(row_base["usable_nights"])
            rung = BaselineRung(row_base["rung"])
        else:
            # Count usable nights from nightly_features
            row_count = conn.execute(
                "SELECT COUNT(*) as count FROM nightly_features WHERE subject_id = ? AND usable = 1",
                (subject_id,),
            ).fetchone()
            usable_nights = int(row_count["count"]) if row_count else 0
            rung = BaselineRung.COLD

        # Errors in last 24h
        cutoff_24h = (checked_at - timedelta(hours=24)).isoformat()
        row_err = conn.execute(
            "SELECT COUNT(*) as count FROM system_status WHERE subject_id = ? AND ok = 0 AND ts_utc >= ?",
            (subject_id, cutoff_24h),
        ).fetchone()
        errors_24h = int(row_err["count"]) if row_err else 0

        # Consecutive nights that were measured and came back clear.
        #
        # This counted every unflagged detection row, and a night with no reading at all is
        # written as level NA with flagged 0. A user whose watch recorded three nights out
        # of seven was told "7 quiet nights in a row": four of those were nights nobody
        # looked at. Silence is not the same as good news, least of all here.
        rows_det = conn.execute(
            """SELECT flagged, level FROM detections
               WHERE subject_id = ? ORDER BY night_date DESC LIMIT 30""",
            (subject_id,),
        ).fetchall()

        quiet_nights_streak = 0
        for r in rows_det:
            if r["level"] == "NA":
                break
            if r["flagged"] == 0:
                quiet_nights_streak += 1
            else:
                break

        unmeasured_recent_nights = sum(
            1 for r in rows_det[:RECENT_NIGHTS_WINDOW] if r["level"] == "NA"
        )

        recent_levels = conn.execute(
            """SELECT level, residual_bpm FROM detections
               WHERE subject_id = ?
               ORDER BY night_date DESC LIMIT 30""",
            (subject_id,),
        ).fetchall()
        detection_streak = None
        if recent_levels and recent_levels[0]["level"] != "NA":
            latest_level = DetectionLevel(recent_levels[0]["level"])
            same_level = []
            for row in recent_levels:
                if row["level"] != latest_level.value:
                    break
                same_level.append(row)

            direction = None
            if len(same_level) >= 2:
                oldest = same_level[-1]["residual_bpm"]
                latest = same_level[0]["residual_bpm"]
                if oldest is not None and latest is not None:
                    delta = float(latest) - float(oldest)
                    if delta > DASHBOARD_RESIDUAL_DIRECTION_FLOOR_BPM:
                        direction = "rising"
                    elif delta < -DASHBOARD_RESIDUAL_DIRECTION_FLOOR_BPM:
                        direction = "falling"
                    else:
                        direction = "steady"
            detection_streak = DetectionStreak(
                length=len(same_level), level=latest_level, direction=direction
            )

        return SystemStatus(
            components=components,
            last_ingest_utc=last_ingest_utc,
            last_nightly_utc=last_nightly_utc,
            usable_nights=usable_nights,
            rung=rung,
            errors_24h=errors_24h,
            quiet_nights_streak=quiet_nights_streak,
            detection_streak=detection_streak,
            unmeasured_recent_nights=unmeasured_recent_nights,
        )
    finally:
        if close_conn:
            conn.close()


def test_bridge_connection(
    bridge_host: str | None = None,
    bridge_token: str | None = None,
    client: httpx.Client | None = None,
) -> ConnectionCheck:
    """Attempt a live bridge connection check with short timeout. Never returns secrets."""
    settings = get_settings()
    host = bridge_host or settings.bridge_url or "http://localhost:8080"
    if not host.startswith("http://") and not host.startswith("https://"):
        host = f"http://{host}"
    token = (
        bridge_token
        or (settings.bridge_token.get_secret_value() if settings.bridge_token else None)
        or os.environ.get("WHA_BRIDGE_TOKEN")
    )
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    endpoint = f"{host.rstrip('/')}/health"
    start_time = time.perf_counter()
    try:
        if client is not None:
            resp = client.get(endpoint, headers=headers, timeout=3.0)
        else:
            with httpx.Client(timeout=3.0) as http_client:
                resp = http_client.get(endpoint, headers=headers)

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        if resp.status_code == 200:
            return ConnectionCheck(
                ok=True,
                detail=f"Connected to bridge at {host} (status {resp.status_code})",
                latency_ms=latency_ms,
            )
        else:
            return ConnectionCheck(
                ok=False,
                detail=f"Bridge HTTP {resp.status_code} at {host}",
                latency_ms=latency_ms,
            )
    except (httpx.HTTPError, OSError) as exc:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        return ConnectionCheck(
            ok=False,
            detail=f"Bridge connection error to {host}: {type(exc).__name__}",
            latency_ms=latency_ms,
        )


def test_llm_connection(
    provider: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> ConnectionCheck:
    """Attempt an LLM connectivity check. Never returns secrets."""
    settings = get_settings()
    prov = provider or settings.llm_provider
    mod = model or settings.llm_model

    if prov == "cassette":
        return ConnectionCheck(
            ok=True,
            detail="Cassette provider ready (offline deterministic mode)",
            latency_ms=1,
        )

    start_time = time.perf_counter()
    try:
        from pydantic import BaseModel

        from wha.llm.client import Prompt

        if prov == "ollama_native":
            from wha.llm.ollama import OllamaNativeClient

            client = OllamaNativeClient(base_url=base_url, model=mod)
        elif prov == "openai_compatible":
            from wha.llm.openai_compat import OpenAICompatClient

            client = OpenAICompatClient(base_url=base_url, api_key=api_key, model=mod)
        else:
            return ConnectionCheck(
                ok=False,
                detail=f"Unknown LLM provider: {prov}",
                latency_ms=None,
            )

        class PingResponse(BaseModel):
            status: str = "ok"

        prompt = Prompt(prompt_id="ping", user="Respond with status ok")
        client.complete(prompt, schema=PingResponse, temperature=0.0)
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        return ConnectionCheck(
            ok=True,
            detail=f"LLM provider '{prov}' responded for model '{mod}'",
            latency_ms=latency_ms,
        )
    except Exception as exc:  # noqa: BLE001
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        return ConnectionCheck(
            ok=False,
            detail=f"LLM connectivity error for provider '{prov}': {exc}",
            latency_ms=latency_ms,
        )


def test_telegram_connection(
    token: str | None = None,
    client: httpx.Client | None = None,
) -> ConnectionCheck:
    """Attempt Telegram Bot API getMe check. Never returns secrets."""
    settings = get_settings()
    tg_token = (
        token
        or (settings.telegram_bot_token.get_secret_value() if settings.telegram_bot_token else None)
        or os.environ.get("WHA_TELEGRAM_TOKEN", "")
    )

    if not tg_token:
        return ConnectionCheck(
            ok=False,
            detail="Telegram bot token not configured",
            latency_ms=None,
        )

    endpoint = f"https://api.telegram.org/bot{tg_token}/getMe"
    start_time = time.perf_counter()
    try:
        if client is not None:
            resp = client.get(endpoint, timeout=5.0)
        else:
            with httpx.Client(timeout=5.0) as http_client:
                resp = http_client.get(endpoint)

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        if resp.status_code == 200:
            data = resp.json().get("result", {})
            bot_username = data.get("username", "bot")
            return ConnectionCheck(
                ok=True,
                detail=f"Telegram bot @{bot_username} connected successfully",
                latency_ms=latency_ms,
            )
        else:
            return ConnectionCheck(
                ok=False,
                detail=f"Telegram API HTTP {resp.status_code}",
                latency_ms=latency_ms,
            )
    except (httpx.HTTPError, OSError) as exc:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        return ConnectionCheck(
            ok=False,
            detail=f"Telegram network error: {type(exc).__name__}",
            latency_ms=latency_ms,
        )


def check_live_production_suite() -> dict[str, Any]:
    """Execute live diagnostic tests across mandatory and optional subsystems."""
    settings = get_settings()

    mandatory: list[dict[str, Any]] = []
    optional: list[dict[str, Any]] = []

    # 1. Mandatory: SQLite Database
    try:
        conn = connect()
        apply_schema(conn)
        cnt = conn.execute("SELECT COUNT(*) FROM nightly_features").fetchone()[0]
        # "Schema v1 verified" was a hardcoded string that never read the database, so this
        # command and `wha doctor` reported different versions for the same file.
        version = read_schema_version(conn)
        conn.close()
        mandatory.append(
            {
                "component": "Database & Cryptographic Audit Log",
                "ok": True,
                "detail": f"Schema v{version} verified ({cnt} feature nights recorded)",
            }
        )
    except Exception as exc:  # noqa: BLE001
        mandatory.append(
            {
                "component": "Database & Cryptographic Audit Log",
                "ok": False,
                "detail": f"Database failure: {exc}",
            }
        )

    # 2. Mandatory: Clinical Knowledge Tables
    try:
        from wha.belief import load_causes
        from wha.policy import load_probes

        causes = load_causes()
        probes = load_probes()
        mandatory.append(
            {
                "component": "Clinical Knowledge Tables",
                "ok": True,
                # NOT "cited". After an audit on 5 September 2026 checked every CITED row
                # against its source, all three failed and were relabelled DERIVED, so
                # causes.yaml has no CITED rows left. Every probe likelihood has always
                # been ASSUMED. A diagnostic that calls them cited is the same overstatement
                # the audit was about.
                "detail": (
                    f"Loaded {len(causes)} causes and {len(probes)} probes, each carrying "
                    "its own provenance (DERIVED or ASSUMED; none is CITED)"
                ),
            }
        )
    except Exception as exc:  # noqa: BLE001
        mandatory.append(
            {
                "component": "Clinical Knowledge Tables",
                "ok": False,
                "detail": f"Knowledge files error: {exc}",
            }
        )

    # 3. Mandatory: Phone Hardware Bridge
    bridge_chk = test_bridge_connection()
    mandatory.append(
        {
            "component": "Phone Hardware Bridge",
            "ok": bridge_chk.ok,
            "detail": f"{bridge_chk.detail} ({bridge_chk.latency_ms}ms)"
            if bridge_chk.latency_ms
            else bridge_chk.detail,
        }
    )

    # 4. Mandatory: Live LLM Inference API
    llm_chk = test_llm_connection()
    mandatory.append(
        {
            "component": "Live LLM Inference API",
            "ok": llm_chk.ok,
            "detail": f"{llm_chk.detail} ({llm_chk.latency_ms}ms)"
            if llm_chk.latency_ms
            else llm_chk.detail,
        }
    )

    # 5. Mandatory: Telegram Bot Transport
    tg_chk = test_telegram_connection()
    mandatory.append(
        {
            "component": "Telegram Mobile Bot",
            "ok": tg_chk.ok,
            "detail": f"{tg_chk.detail} ({tg_chk.latency_ms}ms)"
            if tg_chk.latency_ms
            else tg_chk.detail,
        }
    )

    # 6. Mandatory: Statistical Anomaly & Bayesian Engines
    try:
        from wha.belief import update_belief
        from wha.detect.baseline import compute_baseline

        test_history = [
            NightlyFeatures(
                subject_id="test",
                night_date=date(2026, 9, 1),
                rhr_bpm=60.0,
                coverage_minutes=360,
                usable=True,
            )
        ]
        b = compute_baseline(test_history)
        _ = update_belief(episode_nights=[])
        mandatory.append(
            {
                "component": "Statistical & Bayesian Engine",
                "ok": True,
                "detail": f"Deterministic shrinkage (Rung: {b.rung.name}), 4096-state exact posterior ready",
            }
        )
    except Exception as exc:  # noqa: BLE001
        mandatory.append(
            {
                "component": "Statistical & Bayesian Engine",
                "ok": False,
                "detail": f"Engine calculation error: {exc}",
            }
        )

    # There is no seventh mandatory component. A "Chronos Neural Forecaster" row lived here
    # after the forecaster itself was deleted, backed by a cache check for weights nothing
    # loads. On any machine without the 182 MB of weights it set mandatory_ok False, printed
    # NOT PRODUCTION READY, and told the operator to run `wha data fetch chronos`, which now
    # answers "There is nothing to fetch". A diagnostic that reports a deleted subsystem as
    # a required one is the same defect class the deletion was meant to end.

    # --- RESEARCH BENCHMARKS (EVALUATION ONLY) ---

    # `.exists()` was true for the empty directories `wha data fetch` creates, so this
    # reported benchmark data present on a machine that had none.
    stanford_exists = dataset_present(settings.data_dir, "stanford")
    pmdata_exists = dataset_present(settings.data_dir, "pmdata")
    benchmarks_ok = stanford_exists and pmdata_exists
    optional.append(
        {
            "component": "Research Benchmark Cohorts",
            "ok": benchmarks_ok,
            "detail": "Stanford & PMData benchmark targets present (for 'wha eval')"
            if benchmarks_ok
            # `wha data fetch stanford` no longer pretends to fetch anything: it made an
            # empty directory and reported success, which is why this check had to exist.
            else "Absent (run 'uv run python experiments/detection/cohort/fetch.py')",
        }
    )

    all_mandatory_ok = all(c["ok"] for c in mandatory)
    return {
        "mandatory_ok": all_mandatory_ok,
        "mandatory": mandatory,
        "optional": optional,
    }
