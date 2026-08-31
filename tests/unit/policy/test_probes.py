"""Unit tests for loading and validating data/knowledge/probes.yaml."""

from pathlib import Path

import pytest

from wha.errors import ConfigError
from wha.policy import load_probes


def test_real_probes_yaml_loads() -> None:
    """The canonical data/knowledge/probes.yaml loads and validates cleanly."""
    probes = load_probes()
    assert len(probes) >= 5


def test_option_ids_fit_callback_data() -> None:
    """Every probe option_id is at most 8 characters and callback_data is <= 64 bytes."""
    probes = load_probes()
    for probe in probes:
        for opt in probe.answer_space:
            assert len(opt.option_id) <= 8
            cb_data = f"{probe.probe_id}:{opt.option_id}".encode()
            assert len(cb_data) <= 64


def test_assumed_rows_carry_an_assumption_string() -> None:
    """Every ASSUMED probe carries a non-empty assumption explaining conservative bounds."""
    probes = load_probes()
    for probe in probes:
        if probe.provenance == "ASSUMED":
            assert probe.assumption is not None
            assert len(probe.assumption.strip()) > 0


def test_assumed_rows_appear_in_sweep_config() -> None:
    """All ASSUMED probes have likelihood tables that can be subjected to sensitivity sweeps."""
    probes = load_probes()
    assumed = [p for p in probes if p.provenance == "ASSUMED"]
    assert len(assumed) > 0
    for p in assumed:
        # Every assumed probe has present and absent likelihood mappings
        assert len(p.likelihood_present) >= 2
        assert len(p.likelihood_absent) >= 2


def test_probes_yaml_validates(tmp_path: Path) -> None:
    """Likelihoods summing to 0.9, unknown causes, and long option IDs all raise ConfigError."""
    # 1. Likelihood summing to 0.9
    bad_sum_yaml = """
schema_version: "1.0"
probes:
  - probe_id: probe_bad_sum
    target_cause: alcohol
    interruption_cost: 1.0
    fallback_text: "Did you drink?"
    answer_space:
      - {option_id: "none", label: "None"}
      - {option_id: "yes", label: "Yes"}
    likelihood:
      present: {"none": 0.4, "yes": 0.5}  # sums to 0.9
      absent: {"none": 0.8, "yes": 0.2}
    provenance: ASSUMED
    assumption: "Test"
"""
    bad_sum_file = tmp_path / "bad_sum.yaml"
    bad_sum_file.write_text(bad_sum_yaml, encoding="utf-8")
    with pytest.raises(ConfigError, match="sums to 0.9"):
        load_probes(bad_sum_file)

    # 2. Unknown cause
    bad_cause_yaml = """
schema_version: "1.0"
probes:
  - probe_id: probe_bad_cause
    target_cause: alien_invasion
    interruption_cost: 1.0
    fallback_text: "Aliens?"
    answer_space:
      - {option_id: "no", label: "No"}
      - {option_id: "yes", label: "Yes"}
    likelihood:
      present: {"no": 0.1, "yes": 0.9}
      absent: {"no": 0.9, "yes": 0.1}
    provenance: ASSUMED
    assumption: "Test"
"""
    bad_cause_file = tmp_path / "bad_cause.yaml"
    bad_cause_file.write_text(bad_cause_yaml, encoding="utf-8")
    with pytest.raises(ConfigError, match="Unknown target_cause"):
        load_probes(bad_cause_file)

    # 3. 12-char option ID (>8 chars)
    bad_opt_yaml = """
schema_version: "1.0"
probes:
  - probe_id: probe_bad_opt
    target_cause: alcohol
    interruption_cost: 1.0
    fallback_text: "Did you drink?"
    answer_space:
      - {option_id: "way_too_long", label: "No"}
      - {option_id: "yes", label: "Yes"}
    likelihood:
      present: {"way_too_long": 0.1, "yes": 0.9}
      absent: {"way_too_long": 0.9, "yes": 0.1}
    provenance: ASSUMED
    assumption: "Test"
"""
    bad_opt_file = tmp_path / "bad_opt.yaml"
    bad_opt_file.write_text(bad_opt_yaml, encoding="utf-8")
    with pytest.raises(ConfigError, match="exceeds 8 characters"):
        load_probes(bad_opt_file)
