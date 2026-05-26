from __future__ import annotations

from rfmcp_core.contracts import SkillManifest

from rfmcp_skills.catalog import CanonicalSkillDefinition, WorkflowBoundaryStep
from rfmcp_skills.fallbacks import RUNNABLE_TEST_GENERATION_ID, fallback_commands_for
from rfmcp_skills.inputs import GenerationSkillInput


ASSET_DIRECTORY = f"assets/skills/{RUNNABLE_TEST_GENERATION_ID}"
BOUNDARY_DOC_PATH = "docs/runnable-test-generation.md"

MANIFEST = SkillManifest(
    schema_version="1.0",
    skill_id=RUNNABLE_TEST_GENERATION_ID,
    title="Runnable Test Generation Workflow",
    description="Ground, scaffold, generate, validate, and executable-proof a deterministic Robot Framework suite.",
    fallback_commands=list(fallback_commands_for(RUNNABLE_TEST_GENERATION_ID)),
)

WORKFLOW_STEPS = (
    WorkflowBoundaryStep(
        phase="skill-entry",
        surface="host",
        detail="Let the host collect or refine generation intent, but keep generation logic in the canonical workflow definition rather than host-specific prompts.",
        reference="GenerationSkillInput",
    ),
    WorkflowBoundaryStep(
        phase="ground",
        surface="cli",
        detail="Use deterministic grounding to gather real library and keyword context before scaffolding or body generation.",
        reference="rfmcp ground <keyword-or-library-query> --json",
    ),
    WorkflowBoundaryStep(
        phase="scaffold",
        surface="cli",
        detail="Create the initial suite structure through the deterministic scaffold path so generated work starts from a real Robot Framework file.",
        reference="rfmcp scaffold-suite <target.robot> --library <LibraryName> --json",
    ),
    WorkflowBoundaryStep(
        phase="generate",
        surface="cli",
        detail="Generate the suite body through the canonical CLI workflow, then return structured validation, execution proof, and correction-path evidence.",
        reference="rfmcp generate <target.robot> --step '<step>' --assertion '<assertion>' --json",
    ),
)


def runnable_test_generation_definition() -> CanonicalSkillDefinition:
    return CanonicalSkillDefinition(
        skill_id=MANIFEST.skill_id,
        manifest=MANIFEST,
        input_model=GenerationSkillInput,
        asset_directory=ASSET_DIRECTORY,
        boundary_doc_path=BOUNDARY_DOC_PATH,
        fallback_commands=tuple(MANIFEST.fallback_commands),
        workflow_steps=WORKFLOW_STEPS,
    )
