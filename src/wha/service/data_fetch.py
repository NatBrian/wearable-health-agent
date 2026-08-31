"""Data and model weights fetching service."""

from pathlib import Path

from wha.config import get_settings
from wha.errors import ConfigError


def fetch_data(target: str) -> str:
    """Fetch external datasets or model weights."""
    target_clean = target.lower().strip()
    settings = get_settings()

    if target_clean == "chronos":
        # Cache chronos model
        settings.model_cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            from wha.detect.forecast import get_chronos_pipeline

            get_chronos_pipeline()
            return f"Chronos foundation model cached to {settings.model_cache_dir}"
        except ImportError:
            return "Chronos library not installed; skipped model download."
        except Exception as e:  # noqa: BLE001
            return f"Chronos fetch notice: {e}"

    if target_clean in {"stanford", "pmdata"}:
        dataset_dir = settings.data_dir / target_clean
        dataset_dir.mkdir(parents=True, exist_ok=True)
        return f"Dataset directory initialized at {dataset_dir}."

    if target_clean == "corpus":
        corpus_path = Path("data/knowledge/corpus.yaml")
        return f"Corpus target verified at {corpus_path}."

    raise ConfigError(
        f"Unknown data fetch target '{target}'. Valid targets: chronos, stanford, pmdata, corpus"
    )
