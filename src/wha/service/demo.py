"""Demo scenario runner service."""

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml

from wha.config import get_settings
from wha.db import apply_schema, connect
from wha.detect.detector import detect_range
from wha.errors import ConfigError
from wha.features.derivation import compute_range
from wha.ingest.store import normalise_and_store
from wha.ingest.synthetic import Synthetic
from wha.models import Detection, Scenario


@dataclass(frozen=True)
class DemoRunResult:
    scenario: str
    subject_id: str
    dry_run: bool
    nights: list[Detection]


def run_demo(
    scenario_name: str,
    dry_run: bool = True,
    live: bool = False,
    db_path: Path | None = None,
) -> DemoRunResult:
    """Run a scenario end-to-end. Dry run runs the deterministic batch with no LLM calls."""
    settings = get_settings()
    target_db = db_path if db_path is not None else settings.db_path

    # Try json first, then yaml
    scenario_file = Path(f"tests/fixtures/scenarios/{scenario_name}.json")
    if not scenario_file.exists():
        scenario_file = Path(f"tests/fixtures/scenarios/{scenario_name.replace('_', '-')}.json")
    if not scenario_file.exists():
        scenario_file = Path(f"tests/fixtures/scenarios/{scenario_name}.yaml")
    if not scenario_file.exists():
        scenario_file = Path(f"tests/fixtures/scenarios/{scenario_name.replace('-', '_')}.yaml")
    if not scenario_file.exists():
        raise ConfigError(
            f"Scenario fixture '{scenario_name}' not found under tests/fixtures/scenarios/"
        )

    content = scenario_file.read_text(encoding="utf-8")
    if scenario_file.suffix == ".json":
        scenario_data: dict[str, Any] = json.loads(content)
    else:
        scenario_data = yaml.safe_load(content)

    subj_id = f"demo-{scenario_name}"
    target_db.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(target_db)
    apply_schema(conn)

    # Insert subject
    conn.execute(
        """
        INSERT OR IGNORE INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
        VALUES (?, ?, 'synthetic', 'Asia/Singapore', '2026-09-01T00:00:00Z');
        """,
        (subj_id, f"Demo {scenario_name}"),
    )
    conn.commit()

    # Generate synthetic payload
    scenario_obj = Scenario.model_validate(scenario_data)
    syn = Synthetic(scenario=scenario_obj)
    raw_payload = syn.fetch(subject_id=subj_id)

    normalise_and_store(conn, raw_payload)

    # Determine date range from scenario
    days = int(scenario_obj.days)
    first_dt = date(2026, 8, 1)
    last_dt = first_dt + timedelta(days=days - 1)

    compute_range(conn, subj_id, first_dt, last_dt)
    detections = detect_range(conn, subj_id, first_dt, last_dt)

    conn.close()
    return DemoRunResult(
        scenario=scenario_name,
        subject_id=subj_id,
        dry_run=dry_run,
        nights=detections,
    )
