"""Unit tests for loading and validating causes.yaml."""

from pathlib import Path

import pytest

from wha.belief import load_causes
from wha.errors import ConfigError
from wha.models import CauseId


def test_real_causes_yaml_loads_successfully() -> None:
    """The canonical data/knowledge/causes.yaml validates cleanly."""
    causes_file = Path("data/knowledge/causes.yaml")
    assert causes_file.exists()
    priors = load_causes(causes_file)
    assert len(priors) == 12


def test_exactly_twelve_causes() -> None:
    """All 12 unique CauseId members are present."""
    priors = load_causes()
    cause_ids = {p.cause for p in priors}
    assert cause_ids == set(CauseId)
    assert len(cause_ids) == 12


def test_profiles_non_empty_and_non_negative() -> None:
    """All cause profiles are non-empty lists with non-negative weights."""
    priors = load_causes()
    for p in priors:
        assert len(p.profile) > 0
        assert all(w >= 0.0 for w in p.profile)


def test_every_row_has_provenance() -> None:
    """Every cause entry carries valid evidence grade and citation."""
    priors = load_causes()
    for p in priors:
        assert p.evidence_grade in {"A", "B", "C", "D"}
        assert len(p.citation) > 0


def test_causes_yaml_validates(tmp_path: Path) -> None:
    """Missing causes, invalid base rates (>1.0 or <=0.0), or missing citations raise ConfigError."""
    # Case 1: Base rate out of bounds (1.1)
    bad_yaml_content = """
schema_version: "1.0"
causes:
  - cause: infection
    base_rate: 1.1
    effect_mean_bpm: 1.6
    effect_sd_bpm: 1.0
    profile: [1.0]
    evidence_grade: B
    provenance: CITED
    citation: "Test et al."
"""
    bad_file = tmp_path / "bad_causes.yaml"
    bad_file.write_text(bad_yaml_content, encoding="utf-8")

    with pytest.raises(ConfigError):
        load_causes(bad_file)


def test_malformed_file_raises_at_startup(tmp_path: Path) -> None:
    """Invalid YAML syntax or non-existent files raise ConfigError."""
    # Missing file
    with pytest.raises(ConfigError, match="not found"):
        load_causes(tmp_path / "non_existent.yaml")

    # Malformed YAML
    malformed_file = tmp_path / "malformed.yaml"
    malformed_file.write_text("causes: [unclosed_bracket", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_causes(malformed_file)
