from __future__ import annotations

from rfmcp_core.contracts import SkillManifest

from rfmcp_skills.catalog import CanonicalSkillDefinition, WorkflowBoundaryStep
from rfmcp_skills.fallbacks import EXISTING_ARTIFACT_REFACTOR_ID, fallback_commands_for
from rfmcp_skills.inputs import RefactorSkillInput


ASSET_DIRECTORY = f"assets/skills/{EXISTING_ARTIFACT_REFACTOR_ID}"
BOUNDARY_DOC_PATH = "docs/existing-artifact-refactor.md"

MANIFEST = SkillManifest(
    schema_version="1.0",
    skill_id=EXISTING_ARTIFACT_REFACTOR_ID,
    title="Existing Artifact Refactor Workflow",
    description="Deterministically refactor or regenerate existing Robot Framework suites and resources with runnable proof or explicit manual follow-up.",
    fallback_commands=list(fallback_commands_for(EXISTING_ARTIFACT_REFACTOR_ID)),
)

WORKFLOW_STEPS = (
    WorkflowBoundaryStep(
        phase="skill-entry",
        surface="host",
        detail="Let the host gather refactor intent, but keep edit semantics and failure shaping in the canonical workflow definition.",
        reference="RefactorSkillInput",
    ),
    WorkflowBoundaryStep(
        phase="refactor",
        surface="cli",
        detail="Apply targeted deterministic edits to an existing artifact while preserving a structured diff and explicit change accounting.",
        reference="rfmcp refactor <target.robot> --replace 'OLD=NEW' --json",
    ),
    WorkflowBoundaryStep(
        phase="regenerate",
        surface="cli",
        detail="Replace the primary body through the deterministic regenerate path when a structural rewrite is safer than incremental edits.",
        reference="rfmcp regenerate <target.robot> --step '<step>' --assertion '<assertion>' --json",
    ),
    WorkflowBoundaryStep(
        phase="verify",
        surface="cli",
        detail="Use validation and executable proof for suites, or explicit manual follow-up guidance for resources, without pretending every host executes the same helper stack.",
        reference="rfmcp validate <target.robot> --json",
    ),
)


def existing_artifact_refactor_definition() -> CanonicalSkillDefinition:
    return CanonicalSkillDefinition(
        skill_id=MANIFEST.skill_id,
        manifest=MANIFEST,
        input_model=RefactorSkillInput,
        asset_directory=ASSET_DIRECTORY,
        boundary_doc_path=BOUNDARY_DOC_PATH,
        fallback_commands=tuple(MANIFEST.fallback_commands),
        workflow_steps=WORKFLOW_STEPS,
    )
