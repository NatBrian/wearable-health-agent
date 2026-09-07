"""Unit tests for cohort data loader and parquet caching."""

from pathlib import Path

import pytest
import yaml

from wha.errors import ConfigError
from wha.ingest.cohort import CohortReplay, load_cohort_labels


def test_cohort_missing_labels_is_a_hard_error_that_says_how_to_get_them(tmp_path: Path) -> None:
    """Still a hard error. The message changed because the file it named never existed.

    It pointed at `data/knowledge/cohort_labels.yaml`, to be authored by hand from
    supplementary information, and blocker A-25 recorded that as the reason detection
    accuracy could not be measured. That was wrong: the labels are in the Mishra et al.
    2020 supplementary workbook and `experiments/detection/cohort/labels.py` extracts them. So the old
    message told every reader to produce a file nobody was ever going to produce, and
    `uv run wha eval detection` failed on every machine.
    """
    missing_file = tmp_path / "nonexistent_labels.json"
    with pytest.raises(ConfigError, match="Cohort labels not found"):
        load_cohort_labels(missing_file)

    with pytest.raises(ConfigError, match="experiments/detection/cohort/labels.py"):
        load_cohort_labels(missing_file)


def test_parquet_cache_reused(tmp_path: Path) -> None:
    """Parquet cache is generated on first load and reused on subsequent loads."""
    data_dir = tmp_path / "datasets"
    participant_dir = data_dir / "stanford" / "p01"
    participant_dir.mkdir(parents=True)

    # Create dummy hr.csv
    hr_csv = participant_dir / "hr.csv"
    hr_csv.write_text("ts_utc,avg_bpm\n2026-08-01T00:00:00Z,62.0\n", encoding="utf-8")

    # Create labels file
    labels_file = tmp_path / "cohort_labels.yaml"
    labels_data = {
        "stanford": {
            "p01": {
                "covid_positive": True,
                "symptom_onset": "2026-08-10",
            }
        }
    }
    labels_file.write_text(yaml.dump(labels_data), encoding="utf-8")

    replay = CohortReplay(
        dataset="stanford",
        participant="p01",
        data_dir=data_dir,
        labels_file=labels_file,
    )

    # First load creates parquet
    df1 = replay.get_parquet_table()
    assert len(df1) == 1

    cache_file = data_dir / "cache" / "stanford_p01.parquet"
    assert cache_file.exists()

    # Second load reads from parquet cache
    df2 = replay.get_parquet_table()
    assert len(df2) == 1


def test_dataset_tests_skip_cleanly(tmp_path: Path) -> None:
    """Tests requiring the unauthenticated dataset download skip cleanly when not present."""
    stanford_dir = tmp_path / "datasets" / "stanford"
    dataset_present = stanford_dir.exists() and any(stanford_dir.iterdir())

    if not dataset_present:
        pytest.skip("Stanford dataset not present. Run: uv run wha data fetch stanford")
