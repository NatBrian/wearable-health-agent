"""Loader and validator for data/knowledge/probes.yaml."""

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from wha.errors import ConfigError
from wha.models import AnswerOption, CauseId

VALID_PROVENANCE = {"CITED", "DERIVED", "ASSUMED"}


class ProbeDefinition(BaseModel):
    """Full schema for a probe loaded from probes.yaml."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    probe_id: str
    target_cause: CauseId
    interruption_cost: float
    fallback_text: str
    answer_space: list[AnswerOption]
    likelihood_present: dict[str, float] = Field(default_factory=dict)
    likelihood_absent: dict[str, float] = Field(default_factory=dict)
    provenance: Literal["CITED", "DERIVED", "ASSUMED"]
    assumption: str | None = None
    citation: str | None = None
    # Asked once and never again, across every investigation rather than within one.
    #
    # `probes.yaml` has carried `one_time: true` since it was written, and this model
    # forbids extra fields while `load_probes` builds it field by field, so the flag was
    # dropped silently on load. probe_medication is priced at 0.4 of an interruption
    # BECAUSE of that promise, so the price was wrong and the system could spend part of
    # somebody's weekly allowance asking the same setup question in every new episode.
    one_time: bool = False


def load_probes(path: Path | str | None = None) -> list[ProbeDefinition]:
    """Load and validate all probe definitions from YAML.

    Raises ConfigError if the file is missing, malformed, or violates contract invariants.
    """
    file_path = Path(path) if path is not None else Path("data/knowledge/probes.yaml")
    if not file_path.exists():
        raise ConfigError(f"Probes configuration file not found: {file_path}")

    try:
        content = file_path.read_text(encoding="utf-8")
        data: dict[str, Any] = yaml.safe_load(content)
    except Exception as e:
        raise ConfigError(f"Failed to parse YAML from {file_path}: {e}") from e

    if not isinstance(data, dict):
        raise ConfigError(f"Invalid probes YAML root structure in {file_path}")

    probes_list = data.get("probes")
    if not isinstance(probes_list, list):
        raise ConfigError(f"Missing or invalid 'probes' list in {file_path}")

    validated_probes: list[ProbeDefinition] = []

    for idx, item in enumerate(probes_list):
        if not isinstance(item, dict):
            raise ConfigError(f"Probe at index {idx} is not a dictionary")

        probe_id = str(item.get("probe_id", "")).strip()
        if not probe_id:
            raise ConfigError(f"Missing probe_id at index {idx}")

        raw_cause = item.get("target_cause")
        try:
            target_cause = CauseId(str(raw_cause))
        except ValueError as e:
            raise ConfigError(f"Unknown target_cause '{raw_cause}' in probe '{probe_id}'") from e

        cost = item.get("interruption_cost")
        if not isinstance(cost, (int, float)) or float(cost) < 0.0:
            raise ConfigError(f"Invalid interruption_cost in probe '{probe_id}': {cost}")

        fallback_text = str(item.get("fallback_text", "")).strip()
        if not fallback_text:
            raise ConfigError(f"Missing fallback_text in probe '{probe_id}'")

        raw_answers = item.get("answer_space")
        if not isinstance(raw_answers, list) or len(raw_answers) < 2:
            raise ConfigError(f"answer_space in probe '{probe_id}' must contain at least 2 options")

        answer_options: list[AnswerOption] = []
        option_ids: list[str] = []

        for opt in raw_answers:
            if not isinstance(opt, dict):
                raise ConfigError(f"Invalid answer option in probe '{probe_id}'")
            raw_opt_id = opt.get("option_id")
            opt_id = str(raw_opt_id).strip()
            label = str(opt.get("label", "")).strip()

            if not opt_id or not label:
                raise ConfigError(f"Option in probe '{probe_id}' missing option_id or label")

            # Option IDs must be at most 8 chars
            if len(opt_id) > 8:
                raise ConfigError(
                    f"option_id '{opt_id}' in probe '{probe_id}' exceeds 8 characters ({len(opt_id)})"
                )

            # Check 64-byte callback_data limit
            callback_data = f"{probe_id}:{opt_id}".encode()
            if len(callback_data) > 64:
                raise ConfigError(
                    f"callback_data for '{probe_id}:{opt_id}' exceeds 64 bytes ({len(callback_data)} bytes)"
                )

            answer_options.append(AnswerOption(option_id=opt_id, label=label))
            option_ids.append(opt_id)

        # Validate likelihood tables
        lik = item.get("likelihood")
        if not isinstance(lik, dict):
            raise ConfigError(f"Missing likelihood table in probe '{probe_id}'")

        raw_present = lik.get("present")
        raw_absent = lik.get("absent")

        if not isinstance(raw_present, dict) or not isinstance(raw_absent, dict):
            raise ConfigError(
                f"Likelihood in probe '{probe_id}' must have both 'present' and 'absent' mappings"
            )

        present_dict = {str(k): float(v) for k, v in raw_present.items()}
        absent_dict = {str(k): float(v) for k, v in raw_absent.items()}

        # Check options match
        if set(present_dict.keys()) != set(option_ids):
            raise ConfigError(
                f"Present likelihood keys in probe '{probe_id}' do not match answer_space options"
            )
        if set(absent_dict.keys()) != set(option_ids):
            raise ConfigError(
                f"Absent likelihood keys in probe '{probe_id}' do not match answer_space options"
            )

        # Validate probabilities and sum to 1.0
        sum_present = sum(present_dict.values())
        sum_absent = sum(absent_dict.values())

        if abs(sum_present - 1.0) > 1e-3:
            raise ConfigError(
                f"Present likelihood in probe '{probe_id}' sums to {sum_present}, expected 1.0"
            )
        if abs(sum_absent - 1.0) > 1e-3:
            raise ConfigError(
                f"Absent likelihood in probe '{probe_id}' sums to {sum_absent}, expected 1.0"
            )

        provenance = item.get("provenance")
        if provenance not in VALID_PROVENANCE:
            raise ConfigError(
                f"Invalid provenance '{provenance}' in probe '{probe_id}', must be one of {VALID_PROVENANCE}"
            )

        assumption = item.get("assumption")
        if provenance == "ASSUMED" and (not assumption or not str(assumption).strip()):
            raise ConfigError(f"Probe '{probe_id}' is ASSUMED but carries no assumption string")

        citation = item.get("citation")
        if provenance == "CITED" and (not citation or not str(citation).strip()):
            raise ConfigError(f"Probe '{probe_id}' is CITED but carries no citation string")

        validated_probes.append(
            ProbeDefinition(
                probe_id=probe_id,
                target_cause=target_cause,
                interruption_cost=float(cost),
                fallback_text=fallback_text,
                answer_space=answer_options,
                likelihood_present=present_dict,
                likelihood_absent=absent_dict,
                provenance=provenance,  # type: ignore[arg-type]
                assumption=str(assumption).strip() if assumption else None,
                citation=str(citation).strip() if citation else None,
                one_time=bool(item.get("one_time", False)),
            )
        )

    return validated_probes
