"""Canonical skill definitions and fallback mappings."""

from rfmcp_skills.catalog import (
    CanonicalSkillDefinition,
    WorkflowBoundaryStep,
    registered_skill_definitions,
    skill_definition_by_id,
)
from rfmcp_skills.definitions import (
    BrowserLibraryRepairDefinition,
    BrowserLibraryRepairWorkflowResult,
    browser_library_repair_definition,
    existing_artifact_refactor_definition,
    run_browser_library_flagship_repair,
    runnable_test_generation_definition,
)
from rfmcp_skills.fallbacks import (
    BROWSER_LIBRARY_FLAGSHIP_REPAIR_ID,
    EXISTING_ARTIFACT_REFACTOR_ID,
    FALLBACK_COMMANDS_BY_SKILL_ID,
    RUNNABLE_TEST_GENERATION_ID,
    fallback_commands_for,
    render_fallback_commands,
)
from rfmcp_skills.inputs import GenerationSkillInput, RefactorSkillInput

__all__ = [
    "BROWSER_LIBRARY_FLAGSHIP_REPAIR_ID",
    "BrowserLibraryRepairDefinition",
    "BrowserLibraryRepairWorkflowResult",
    "CanonicalSkillDefinition",
    "EXISTING_ARTIFACT_REFACTOR_ID",
    "FALLBACK_COMMANDS_BY_SKILL_ID",
    "GenerationSkillInput",
    "RUNNABLE_TEST_GENERATION_ID",
    "RefactorSkillInput",
    "WorkflowBoundaryStep",
    "browser_library_repair_definition",
    "existing_artifact_refactor_definition",
    "fallback_commands_for",
    "registered_skill_definitions",
    "render_fallback_commands",
    "run_browser_library_flagship_repair",
    "runnable_test_generation_definition",
    "skill_definition_by_id",
]
