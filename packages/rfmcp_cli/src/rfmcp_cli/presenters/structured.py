from __future__ import annotations

from rfmcp_core.contracts import (
    GenerationResult,
    GroundingResult,
    HintResolutionResult,
    RefactorResult,
    RepairDiagnosticResult,
    ScaffoldResult,
    ValidationResult,
)
from rfmcp_core.contracts.serialize import dump_json


def render_validation_result_json(result: ValidationResult) -> str:
    return dump_json(result)


def render_generation_result_json(result: GenerationResult) -> str:
    return dump_json(result)


def render_refactor_result_json(result: RefactorResult) -> str:
    return dump_json(result)


def render_grounding_result_json(result: GroundingResult) -> str:
    return dump_json(result)


def render_repair_diagnostic_result_json(result: RepairDiagnosticResult) -> str:
    return dump_json(result)


def render_scaffold_result_json(result: ScaffoldResult) -> str:
    return dump_json(result)


def render_hint_resolution_result_json(result: HintResolutionResult) -> str:
    return dump_json(result)
