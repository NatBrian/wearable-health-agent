"""Diagnostic doctor checks across database, knowledge, bridge, llm, and models."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from wha.belief import load_causes
from wha.clock import OFFSET_ENV_VAR, clock_offset_days, local_today
from wha.config import get_settings
from wha.db import apply_schema, connect
from wha.detect.baseline import rung_for
from wha.policy import load_probes
from wha.service.checks import read_schema_version

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

    # 0. The clock. This is deliberately the first row, because every row under it is
    # dated by it. A shifted clock is legitimate while a demo timeline is being built and
    # is never legitimate in production, so it is reported rather than hidden.
    offset = clock_offset_days()
    raw = os.environ.get(OFFSET_ENV_VAR, "").strip()
    if offset:
        items.append(
            DoctorItem(
                name="clock",
                status="warn",
                detail=(
                    f"SHIFTED by {offset:+d} days, so today reads {local_today()}. "
                    f"Set by {OFFSET_ENV_VAR}. Unset it before trusting anything below."
                ),
            )
        )
    elif raw:
        items.append(
            DoctorItem(
                name="clock",
                status="warn",
                detail=(
                    f"{OFFSET_ENV_VAR} is set to {raw!r}, which is not a whole number of "
                    f"days and is being ignored. Today reads {local_today()}."
                ),
            )
        )
    else:
        items.append(DoctorItem(name="clock", status="ok", detail=f"today is {local_today()}"))

    # 1. Database check (creates and initializes if missing)
    try:
        target_db.parent.mkdir(parents=True, exist_ok=True)
        conn = connect(target_db)
        apply_schema(conn)

        subj_count = conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
        night_count = conn.execute("SELECT COUNT(*) FROM nightly_features").fetchone()[0]
        schema_version = read_schema_version(conn)
        items.append(
            DoctorItem(
                name="database",
                status="ok",
                detail=(
                    f"{target_db}, schema v{schema_version}, {night_count} nights, "
                    f"{subj_count} subjects"
                ),
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
                detail="chat id and token configured",
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

    # 6. The evaluation cohort.
    #
    # The cohort the detection EXPERIMENT uses. It is not needed to run the system, and
    # nothing in the product depends on it.
    #
    # This looked in data/datasets/ for "stanford" and "pmdata" and reported them
    # missing. The cohort lives in data/cohort/, fetched by
    # experiments/detection/cohort/fetch.py, and pmdata was never used by anything.
    # Reporting a real dataset as absent because it sits under a different name is the
    # kind of small untruth this project has had enough of.
    cohort_dir = Path("data") / "cohort"
    cohort_zip = cohort_dir / "COVID-19-Wearables.zip"
    cohort_labels = cohort_dir / "labels.json"
    if cohort_zip.is_file() and cohort_labels.is_file():
        items.append(
            DoctorItem(
                name="cohort",
                status="ok",
                detail="Mishra 2020 wearables and labels present in data/cohort",
            )
        )
    else:
        items.append(
            DoctorItem(
                name="cohort",
                status="miss",
                detail=(
                    "not fetched. This is only needed to re-run the detection experiment, "
                    "whose results and their limits are in experiments/detection/. "
                    "Run: uv run python experiments/detection/cohort/fetch.py"
                ),
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
