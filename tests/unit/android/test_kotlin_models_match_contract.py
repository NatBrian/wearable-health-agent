"""The Kotlin models must name the same fields as the Python models the facade
returns. A field renamed on the PC must fail a test here rather than a screen on
the phone. Dict-shaped facade payloads (no model behind them) are checked for
existence only; their keys are documented in docs/CONTRACTS.md section 12."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODELS_KT = ROOT / "android/app/src/main/java/dev/wha/app/core/Models.kt"

# Kotlin class -> ("pydantic", "module.Class") | ("dataclass", "module.Class") | None.
# None means the facade builds the shape inline (a dict); the class must exist so a
# typo still fails, but there is no model to compare fields against.
MIRRORED: dict[str, tuple[str, str] | None] = {
    "AnswerOption": ("pydantic", "wha.models.AnswerOption"),
    "AuditEventView": ("pydantic", "wha.models.AuditEventView"),
    "AuditPage": None,
    "Baseline": ("pydantic", "wha.models.Baseline"),
    "BeliefEntry": None,
    "BeliefState": ("pydantic", "wha.models.BeliefState"),
    "Citation": ("pydantic", "wha.models.Citation"),
    "ComponentStatus": ("pydantic", "wha.models.ComponentStatus"),
    "Detection": ("pydantic", "wha.models.Detection"),
    "DifferentialItem": ("pydantic", "wha.models.DifferentialItem"),
    "DoctorRow": ("dataclass", "wha.service.doctor.DoctorItem"),
    "EpisodeDetail": ("pydantic", "wha.models.EpisodeDetail"),
    "EpisodeOutcome": ("pydantic", "wha.models.EpisodeOutcome"),
    "EpisodeSummary": ("pydantic", "wha.models.EpisodeSummary"),
    "Exported": None,
    "Forecast": ("pydantic", "wha.models.Forecast"),
    "Handover": ("dataclass", "wha.service.handover.Handover"),
    "InteractionView": ("pydantic", "wha.models.InteractionView"),
    "JobResult": None,
    "LineageEdge": ("pydantic", "wha.models.LineageEdge"),
    "MeasurementRequest": ("pydantic", "wha.models.MeasurementRequest"),
    "MeasurementResult": ("pydantic", "wha.models.MeasurementResult"),
    "Message": None,
    "NightDetail": ("pydantic", "wha.models.NightDetail"),
    "NightPipeline": ("pydantic", "wha.models.NightPipeline"),
    "NightRow": ("pydantic", "wha.models.NightRow"),
    "NightlyFeatures": ("pydantic", "wha.models.NightlyFeatures"),
    "PendingInteraction": ("pydantic", "wha.models.PendingInteraction"),
    "PipelineHeadline": ("pydantic", "wha.models.PipelineHeadline"),
    "PipelineNightRef": ("pydantic", "wha.models.PipelineNightRef"),
    "PipelineStage": ("pydantic", "wha.models.PipelineStage"),
    "PipelineStepView": ("pydantic", "wha.models.PipelineStepView"),
    "Probe": ("pydantic", "wha.models.Probe"),
    "Question": ("pydantic", "wha.models.Question"),
    "Ready": None,
    "Recorded": None,
    "SayResult": ("pydantic", "wha.agent.conversation.ConversationReply"),
    "ServiceSettings": ("pydantic", "wha.models.Settings"),
    "SubjectProfile": ("pydantic", "wha.models.SubjectProfile"),
    "SystemStatus": ("pydantic", "wha.models.SystemStatus"),
    "Turn": None,
    "Urgency": None,
}


def _kotlin_classes() -> dict[str, set[str]]:
    """Every `data class Name(` in Models.kt and the `val` names in its header.

    Headers nest parentheses (emptyList(), JsonObject(emptyMap())), so the scan
    balances them rather than stopping at the first closing paren.
    """
    source = MODELS_KT.read_text(encoding="utf-8")
    out: dict[str, set[str]] = {}
    for match in re.finditer(r"data class (\w+)\(", source):
        name = match.group(1)
        depth = 1
        pos = match.end()
        while depth > 0:
            char = source[pos]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            pos += 1
        body = source[match.end() : pos - 1]
        out[name] = set(re.findall(r"val (\w+)", body))
    return out


def _python_fields(kind: str, qualname: str) -> set[str]:
    import importlib

    module_name, class_name = qualname.rsplit(".", 1)
    cls = getattr(importlib.import_module(module_name), class_name)
    if kind == "pydantic":
        return set(cls.model_fields)
    import dataclasses

    return {f.name for f in dataclasses.fields(cls)}


def test_every_kotlin_model_is_listed() -> None:
    kotlin = _kotlin_classes()
    unlisted = sorted(set(kotlin) - set(MIRRORED))
    assert not unlisted, f"Kotlin models with no parity entry: {unlisted}"


def test_every_python_field_has_a_kotlin_field() -> None:
    kotlin = _kotlin_classes()
    problems: list[str] = []
    for name, spec in MIRRORED.items():
        if spec is None:
            if name not in kotlin:
                problems.append(f"{name}: Kotlin class missing")
            continue
        kind, qualname = spec
        if name not in kotlin:
            problems.append(f"{name}: Kotlin class missing")
            continue
        missing = _python_fields(kind, qualname) - kotlin[name]
        if missing:
            problems.append(f"{name}: Python fields with no Kotlin field: {sorted(missing)}")
    assert not problems, "Kotlin models drifted from the Python models:\n  " + "\n  ".join(problems)
