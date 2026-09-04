"""Data and model weights fetching service."""

from pathlib import Path

from wha.config import get_settings
from wha.errors import ConfigError


def fetch_data(target: str) -> str:
    """Fetch external datasets or model weights."""
    target_clean = target.lower().strip()
    settings = get_settings()

    if target_clean == "chronos":
        # The forecast was removed on 5 September 2026, on a measurement: over 7,295
        # nights it separated illness worse than the residual the detector already has
        # (AUC 0.586 against 0.629) and caught at most one of 30 infections the detector
        # missed. Answering plainly rather than silently doing nothing, because a command
        # that reports success having done nothing is a defect this project has had before.
        return (
            "Chronos was removed on 5 September 2026. It separated illness worse than the "
            "baseline residual the detector already computes, measured on 7,295 nights. "
            "See tools/cohort/chronos.py. There is nothing to fetch."
        )

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
