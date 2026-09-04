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
        # Fetches the consumer health layer. This used to return a sentence saying the
        # target had been "verified", having checked nothing and downloaded nothing, so
        # the command reported success while the layer stayed absent.
        import json
        from dataclasses import asdict

        from wha.retrieve.medlineplus import ATTRIBUTION, fetch

        snapshot = fetch()
        manifest = Path("data/knowledge/corpus-sources.json")
        manifest.write_text(
            json.dumps(
                {
                    "medlineplus": {
                        **asdict(snapshot),
                        "licence": "Free, no registration, attribution only",
                        "attribution": ATTRIBUTION,
                        "note": (
                            "The raw release is kept out of version control under "
                            "data/corpus/. This file records which snapshot the corpus was "
                            "built from, so a citation can be traced to a specific release "
                            "rather than to whatever the site served that day."
                        ),
                    }
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return (
            f"MedlinePlus {snapshot.snapshot_date}: {snapshot.topics_kept} English topics "
            f"kept of {snapshot.topics_total}. Provenance written to {manifest}."
        )

    raise ConfigError(
        f"Unknown data fetch target '{target}'. Valid targets: chronos, stanford, pmdata, corpus"
    )
