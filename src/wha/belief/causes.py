"""Loader and validator for data/knowledge/causes.yaml."""

from pathlib import Path
from typing import Any

import yaml

from wha.errors import ConfigError
from wha.models import CauseId, CausePrior

REQUIRED_CAUSE_IDS = set(CauseId)
VALID_PROVENANCE = {"CITED", "DERIVED", "ASSUMED"}
VALID_GRADES = {"A", "B", "C", "D"}


def load_causes(path: Path | str | None = None) -> list[CausePrior]:
    """Load and validate causes from YAML configuration.

    Raises ConfigError if the file is missing, malformed, or violates contract invariants.
    """
    if path is None:
        file_path = Path("data/knowledge/causes.yaml")
    else:
        file_path = Path(path)

    if not file_path.exists():
        raise ConfigError(f"Causes configuration file not found: {file_path}")

    try:
        content = file_path.read_text(encoding="utf-8")
        data: dict[str, Any] = yaml.safe_load(content)
    except Exception as e:
        raise ConfigError(f"Failed to parse YAML from {file_path}: {e}") from e

    if not isinstance(data, dict):
        raise ConfigError(f"Invalid causes YAML root structure in {file_path}")

    causes_list = data.get("causes")
    if not isinstance(causes_list, list):
        raise ConfigError(f"Missing or invalid 'causes' list in {file_path}")

    if len(causes_list) != 12:
        raise ConfigError(f"Expected exactly 12 causes, found {len(causes_list)}")

    seen_causes: set[CauseId] = set()
    validated_priors: list[CausePrior] = []

    for idx, row in enumerate(causes_list):
        if not isinstance(row, dict):
            raise ConfigError(f"Cause entry at index {idx} is not a dictionary")

        raw_cause = row.get("cause")
        try:
            cause_id = CauseId(str(raw_cause))
        except ValueError as e:
            raise ConfigError(f"Invalid cause identifier '{raw_cause}' at index {idx}") from e

        if cause_id in seen_causes:
            raise ConfigError(f"Duplicate cause identifier '{cause_id}' at index {idx}")
        seen_causes.add(cause_id)

        # Base rate validation
        base_rate = row.get("base_rate")
        if not isinstance(base_rate, (int, float)) or not (0.0 < float(base_rate) < 1.0):
            raise ConfigError(f"Base rate for {cause_id} must be in (0, 1), got {base_rate}")

        # Effect standard deviation
        effect_sd = row.get("effect_sd_bpm")
        if not isinstance(effect_sd, (int, float)) or float(effect_sd) <= 0.0:
            raise ConfigError(f"effect_sd_bpm for {cause_id} must be > 0, got {effect_sd}")

        # Effect mean
        effect_mean = row.get("effect_mean_bpm")
        if not isinstance(effect_mean, (int, float)):
            raise ConfigError(f"Missing or invalid effect_mean_bpm for {cause_id}")

        # Profile
        profile = row.get("profile")
        if not isinstance(profile, list) or len(profile) == 0:
            raise ConfigError(f"Profile for {cause_id} must be a non-empty list")
        for p_val in profile:
            if not isinstance(p_val, (int, float)) or float(p_val) < 0.0:
                raise ConfigError(
                    f"Profile weights for {cause_id} must be non-negative, got {p_val}"
                )

        # Provenance
        provenance = row.get("provenance")
        if provenance not in VALID_PROVENANCE:
            raise ConfigError(
                f"Provenance for {cause_id} must be one of {VALID_PROVENANCE}, got {provenance}"
            )

        # Evidence grade
        grade = row.get("evidence_grade")
        if grade not in VALID_GRADES:
            raise ConfigError(
                f"evidence_grade for {cause_id} must be one of {VALID_GRADES}, got {grade}"
            )

        # Citation / documentation
        citation = str(
            row.get("citation") or row.get("derivation") or row.get("assumption") or ""
        ).strip()
        if not citation:
            raise ConfigError(f"Missing citation, derivation, or assumption for {cause_id}")

        prior = CausePrior(
            cause=cause_id,
            base_rate=float(base_rate),
            effect_mean_bpm=float(effect_mean),
            effect_sd_bpm=float(effect_sd),
            profile=[float(x) for x in profile],
            evidence_grade=grade,  # type: ignore[arg-type]
            citation=citation,
        )
        validated_priors.append(prior)

    if seen_causes != REQUIRED_CAUSE_IDS:
        missing = REQUIRED_CAUSE_IDS - seen_causes
        raise ConfigError(f"Missing required CauseId members: {missing}")

    return validated_priors
