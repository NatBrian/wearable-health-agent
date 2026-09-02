"""Facts the diagnostics report, established in exactly one place.

`wha doctor` and `wha doctor --live` each used to establish these for themselves, and
drifted: one read the schema version from the database while the other printed a hardcoded
"v1", and one asked whether a dataset directory had anything in it while the other asked
only whether the directory existed. Because `wha data fetch stanford` creates an empty
directory, the second question always answered yes, and the command that ends with
"PRODUCTION READY" told the operator they had benchmark data they did not have.

A diagnostic that reports something it has not checked is worse than one that reports
nothing, so every claim in this module is answerable from what it actually inspects.
"""

import sqlite3
from pathlib import Path

CHRONOS_MODEL_ID = "amazon/chronos-bolt-small"

# Chronos-Bolt ships safetensors; the bin name is accepted for older snapshots.
_CHRONOS_WEIGHT_FILES = ("model.safetensors", "pytorch_model.bin")


def read_schema_version(conn: sqlite3.Connection) -> str:
    """The migration version recorded in the database, or 'unknown' if absent."""
    try:
        row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    except sqlite3.Error:
        return "unknown"
    if row is None:
        return "unknown"
    return str(row[0])


def dataset_present(data_dir: Path, name: str) -> bool:
    """Whether a benchmark cohort is actually usable.

    An empty directory is not a dataset. `wha data fetch <name>` creates the directory and
    nothing else, so existence alone is never evidence that the data arrived.
    """
    target = data_dir / name
    return target.is_dir() and any(target.iterdir())


def chronos_weights_cached() -> tuple[bool, str]:
    """Whether the Chronos weights are genuinely on disk, and where.

    The previous check asked whether `data/model_cache` contained any file. It contains a
    five-byte marker written by `wha data fetch chronos`, so it answered yes on a machine
    with no model. The weights are held in the HuggingFace cache, which is what this looks
    at. Resolved from the cache only: no network call and no model load.
    """
    try:
        from huggingface_hub import try_to_load_from_cache
    except ImportError:
        return False, "huggingface_hub is not installed, so the model cache cannot be read"

    for filename in _CHRONOS_WEIGHT_FILES:
        try:
            path = try_to_load_from_cache(CHRONOS_MODEL_ID, filename)
        except Exception:  # noqa: BLE001, S112
            continue
        if isinstance(path, str) and Path(path).is_file():
            size_mb = Path(path).stat().st_size / (1024 * 1024)
            return True, f"{CHRONOS_MODEL_ID} weights cached ({filename}, {size_mb:.0f} MB)"

    return False, (
        f"{CHRONOS_MODEL_ID} weights are not in the HuggingFace cache "
        "(run 'uv run wha data fetch chronos')"
    )
