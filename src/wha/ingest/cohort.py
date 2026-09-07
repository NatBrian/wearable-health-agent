"""Cohort data loader and parquet caching for Stanford and PMData datasets."""

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import yaml

from wha.clock import now_utc
from wha.config import get_settings
from wha.errors import ConfigError
from wha.models import RawPayload


def load_cohort_labels(labels_file: Path | None = None) -> dict[str, Any]:
    """Ground truth symptom-onset labels for the cohort, keyed the way the eval reads them.

    THIS POINTED AT A FILE THAT HAS NEVER EXISTED AND NEVER WILL.

    `data/knowledge/cohort_labels.yaml` was to be authored by hand from supplementary
    information, and blocker A-25 recorded it as the reason detection accuracy could not be
    measured. That turned out to be wrong: the labels are in the Mishra et al. 2020
    supplementary workbook on the same date shift as the public files, and
    `experiments/detection/cohort/labels.py` extracts them. The blocker is closed and the YAML was never
    written, so `uv run wha eval detection` failed on every machine with

        Cohort labels file missing at 'data/knowledge/cohort_labels.yaml'

    It now reads what the committed pipeline actually produces, and when that is absent it
    names the two commands that produce it rather than describing a file nobody will make.
    """
    path = labels_file if labels_file is not None else Path("data/cohort/labels.json")
    if not path.exists():
        raise ConfigError(
            f"Cohort labels not found at '{path}'. They are extracted from the Mishra "
            "et al. 2020 supplementary workbook, which is a public download. Run:\n"
            "    uv run python experiments/detection/cohort/fetch.py\n"
            "    uv run python experiments/detection/cohort/labels.py\n"
            "See experiments/detection/cohort/README.md. The headline detection figures are already "
            "published in experiments/detection/."
        )

    if path.suffix == ".json":
        rows = json.loads(path.read_text(encoding="utf-8"))
        if not rows:
            raise ConfigError(f"Cohort labels at '{path}' are empty.")
        # experiments/detection/cohort/labels.py emits a flat list, one row per participant. The eval reads
        # a mapping under "stanford", so it is reshaped here rather than in either of them:
        # the tool's output format is what the published numbers were produced from and
        # must not drift, and the eval's shape is what its callers already expect.
        return {
            "stanford": {
                str(row["pid"]): {
                    "symptom_onset": row.get("symptom"),
                    "diagnosis": row.get("diagnosis"),
                    "category": row.get("category"),
                }
                for row in rows
                if row.get("pid")
            }
        }

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not data:
        raise ConfigError(f"Cohort labels file at '{path}' is empty.")
    return data


class CohortReplay:
    """Replay cohort participant data as normalised wearable raw payloads."""

    source_kind = "cohort"

    def __init__(
        self,
        dataset: Literal["stanford", "pmdata"],
        participant: str,
        data_dir: Path | None = None,
        labels_file: Path | None = None,
    ) -> None:
        self.dataset = dataset
        self.participant = participant
        settings = get_settings()
        self.data_dir = data_dir if data_dir is not None else settings.data_dir
        self.labels = load_cohort_labels(labels_file)

        # Ensure participant is present in labels
        dataset_labels = self.labels.get(dataset, {})
        if participant not in dataset_labels:
            raise ConfigError(
                f"Participant '{participant}' has no ground truth entry in cohort_labels.yaml for dataset '{dataset}'."
            )
        self.participant_meta = dataset_labels[participant]

    def _get_cache_path(self) -> Path:
        cache_dir = self.data_dir / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / f"{self.dataset}_{self.participant}.parquet"

    def get_parquet_table(self) -> pd.DataFrame:
        """Load parquet cache if present, otherwise convert and cache."""
        cache_path = self._get_cache_path()
        if cache_path.exists():
            return pd.read_parquet(cache_path)

        participant_dir = self.data_dir / self.dataset / self.participant
        if not participant_dir.exists():
            raise ConfigError(
                f"Dataset path '{participant_dir}' does not exist. Run: uv run wha data fetch {self.dataset}"
            )

        # Parse CSV files for participant
        hr_file = participant_dir / "hr.csv"
        if hr_file.exists():
            df = pd.read_csv(hr_file)
        else:
            df = pd.DataFrame({"ts_utc": [], "avg_bpm": []})

        df.to_parquet(cache_path)
        return df

    def fetch(self, subject_id: str | None = None, days: int | None = None) -> RawPayload:
        """Generate a RawPayload from the cohort parquet data."""
        subj = subject_id if subject_id is not None else f"cohort-{self.participant}"
        df = self.get_parquet_table()

        body: dict[str, Any] = {
            "participant": self.participant,
            "dataset": self.dataset,
            "samples_hr": df.to_dict(orient="records") if not df.empty else [],
            "metadata": self.participant_meta,
        }
        body_json = json.dumps(body, sort_keys=True, separators=(",", ":"))
        sha256 = hashlib.sha256(body_json.encode("utf-8")).hexdigest()

        return RawPayload(
            subject_id=subj,
            fetched_at_utc=now_utc(),
            source_kind=self.source_kind,
            sha256=sha256,
            body=body,
        )
