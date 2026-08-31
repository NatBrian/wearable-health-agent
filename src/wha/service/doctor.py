"""Diagnostic doctor checks across database, knowledge, bridge, llm, and models."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from wha.belief import load_causes
from wha.config import get_settings
from wha.db import apply_schema, connect
from wha.detect.baseline import rung_for
from wha.policy import load_probes

DoctorStatus = Literal["ok", "warn", "fail", "miss", "off", "info"]


@dataclass(frozen=True)
class DoctorItem:
    name: str
    status: DoctorStatus
    detail: str


def run_doctor(db_path: Path | None = None) -> list[DoctorItem]:
    """Execute all system health checks. Never raises and never prints secrets."""
    settings = get_settings()
    target_db = db_path if db_path is not None else settings.db_path
    items: list[DoctorItem] = []

    # 1. Database check (creates and initializes if missing)
    try:
        target_db.parent.mkdir(parents=True, exist_ok=True)
        conn = connect(target_db)
        apply_schema(conn)

        subj_count = conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
        night_count = conn.execute("SELECT COUNT(*) FROM nightly_features").fetchone()[0]
        items.append(
            DoctorItem(
                name="database",
                status="ok",
                detail=f"{target_db}, schema v1, {night_count} nights, {subj_count} subjects",
            )
        )
    except Exception as e:  # noqa: BLE001
        items.append(DoctorItem(name="database", status="fail", detail=str(e)))
        conn = None

    # 2. Knowledge tables check
    try:
        causes = load_causes()
        probes = load_probes()
        items.append(
            DoctorItem(
                name="knowledge",
                status="ok",
                detail=f"causes.yaml {len(causes)} rows, probes.yaml {len(probes)} rows",
            )
        )
    except Exception as e:  # noqa: BLE001
        items.append(
            DoctorItem(name="knowledge", status="fail", detail=f"Knowledge files error: {e}")
        )

    # 3. LiveBridge check
    if settings.bridge_url:
        items.append(
            DoctorItem(
                name="bridge",
                status="ok",
                detail=f"configured at {settings.bridge_url} (auth token configured: {bool(settings.bridge_token)})",
            )
        )
    else:
        items.append(
            DoctorItem(
                name="bridge",
                status="info",
                detail="WHA_BRIDGE_URL not configured (using synthetic data)",
            )
        )

    # 4. LLM provider check
    provider = settings.llm_provider
    if provider == "cassette":
        items.append(
            DoctorItem(
                name="llm",
                status="ok",
                detail=f"provider={provider} (offline tests mode)",
            )
        )
    else:
        api_configured = bool(settings.llm_api_key)
        items.append(
            DoctorItem(
                name="llm",
                status="ok" if api_configured else "warn",
                detail=f"provider={provider}, model={settings.llm_model} (key configured: {api_configured})",
            )
        )

    # 5. Telegram check
    if settings.telegram_bot_token and settings.telegram_chat_id:
        items.append(
            DoctorItem(
                name="telegram",
                status="ok",
                detail=f"chat_id={settings.telegram_chat_id} (token configured)",
            )
        )
    else:
        items.append(
            DoctorItem(
                name="telegram",
                status="off",
                detail="WHA_TELEGRAM_BOT_TOKEN not configured",
            )
        )

    # 6. Datasets check
    data_dir = settings.data_dir
    stanford_exists = (data_dir / "stanford").exists()
    pmdata_exists = (data_dir / "pmdata").exists()
    if stanford_exists and pmdata_exists:
        items.append(DoctorItem(name="datasets", status="ok", detail="stanford and pmdata present"))
    else:
        missing = []
        if not stanford_exists:
            missing.append("stanford")
        if not pmdata_exists:
            missing.append("pmdata")
        items.append(
            DoctorItem(
                name="datasets",
                status="miss",
                detail=f"{', '.join(missing)} absent. Run: uv run wha data fetch <name>",
            )
        )

    # 7. Chronos model check
    cache_dir = settings.model_cache_dir
    if cache_dir.exists() and any(cache_dir.iterdir()):
        items.append(DoctorItem(name="chronos", status="ok", detail="model cache present"))
    else:
        items.append(
            DoctorItem(
                name="chronos",
                status="info",
                detail="amazon/chronos-bolt-small not yet cached",
            )
        )

    # 8. Baseline for default subject
    if conn is not None:
        try:
            usable_nights = conn.execute(
                "SELECT COUNT(*) FROM nightly_features WHERE subject_id = ? AND usable = 1",
                (settings.subject,),
            ).fetchone()[0]
            rung = rung_for(usable_nights)
            items.append(
                DoctorItem(
                    name="baseline",
                    status="info",
                    detail=f"subject '{settings.subject}': {usable_nights} usable nights, rung {rung.name}",
                )
            )
        except Exception:  # noqa: BLE001, S110
            pass
        finally:
            conn.close()

    return items
