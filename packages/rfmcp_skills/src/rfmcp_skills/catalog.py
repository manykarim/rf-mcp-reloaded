from __future__ import annotations

from dataclasses import dataclass
from typing import Type

from pydantic import BaseModel

from rfmcp_core.contracts import SkillManifest


@dataclass(frozen=True)
class WorkflowBoundaryStep:
    phase: str
    surface: str
    detail: str
    reference: str


@dataclass(frozen=True)
class CanonicalSkillDefinition:
    skill_id: str
    manifest: SkillManifest
    input_model: Type[BaseModel]
    asset_directory: str
    boundary_doc_path: str
    fallback_commands: tuple[str, ...]
    workflow_steps: tuple[WorkflowBoundaryStep, ...]
    mcp_tools: tuple[str, ...] = ()


def registered_skill_definitions() -> tuple[CanonicalSkillDefinition, ...]:
    from rfmcp_skills.definitions import (
        browser_library_repair_definition,
        existing_artifact_refactor_definition,
        runnable_test_generation_definition,
    )

    return (
        browser_library_repair_definition(),
        runnable_test_generation_definition(),
        existing_artifact_refactor_definition(),
    )


def skill_definition_by_id(skill_id: str) -> CanonicalSkillDefinition | None:
    for definition in registered_skill_definitions():
        if definition.skill_id == skill_id:
            return definition
    return None
