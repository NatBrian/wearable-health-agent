"""Data and model weights fetching service."""

from pathlib import Path

from wha.errors import ConfigError


def fetch_data(target: str) -> str:
    """Fetch external datasets or model weights."""
    target_clean = target.lower().strip()

    if target_clean == "chronos":
        # The forecast was removed on 5 September 2026, on a measurement: over 7,295
        # nights it separated illness worse than the residual the detector already has
        # (AUC 0.586 against 0.629) and caught at most one of 30 infections the detector
        # missed. Answering plainly rather than silently doing nothing, because a command
        # that reports success having done nothing is a defect this project has had before.
        return (
            "Chronos was removed on 5 September 2026. It separated illness worse than the "
            "baseline residual the detector already computes, measured on 7,295 nights. "
            "See experiments/detection/cohort/chronos.py. There is nothing to fetch."
        )

    if target_clean == "stanford":
        # This made an empty directory and said "Dataset directory initialized", which is
        # the same "reports success having done nothing" defect the chronos branch above
        # names, in the same function. `wha doctor` then had to grow `dataset_present` to
        # tell an empty directory from a dataset, because `.exists()` was true either way.
        #
        # The data is a genuine public download and there is a committed script that does
        # it, verifies the byte count and extracts the labels. Naming it is more use than
        # making a folder.
        return (
            "Not fetched here. The Mishra et al. 2020 cohort is a 378 MB public download "
            "and experiments/detection/cohort/fetch.py does it, checking the byte count, with "
            "experiments/detection/cohort/labels.py extracting the symptom-onset labels afterwards:\n"
            "    uv run python experiments/detection/cohort/fetch.py\n"
            "    uv run python experiments/detection/cohort/labels.py\n"
            "This command previously created an empty directory and reported success."
        )

    if target_clean == "pmdata":
        # PMData was never wired to anything. `dataset_present` checks for it and `wha
        # doctor` reports it as an optional benchmark, and no code reads it.
        return (
            "Not fetched, and nothing reads it. PMData is listed as an optional benchmark "
            "in `wha doctor` and no code in this repository loads it. This command "
            "previously created an empty directory and reported success. The cohort that "
            "IS used is Mishra et al. 2020: see experiments/detection/cohort/README.md."
        )

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
