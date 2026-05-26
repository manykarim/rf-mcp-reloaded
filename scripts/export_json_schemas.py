from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CORE_SRC = REPO_ROOT / "packages" / "rfmcp_core" / "src"
if str(CORE_SRC) not in sys.path:
    sys.path.insert(0, str(CORE_SRC))

from rfmcp_core.models.hint_pack import HintPackManifest  # noqa: E402
from rfmcp_core.models.payloads import (  # noqa: E402
    FailureContext,
    ErrorEnvelope,
    GenerationResult,
    GroundingResult,
    HintPayload,
    HintResolutionResult,
    InspectionSnapshotResult,
    ProviderMetadata,
    RepairSessionSummary,
    RepairDiagnosticResult,
    RepairStepResult,
    RefactorResult,
    RobotContextMutationResult,
    RobotContextView,
    ScaffoldResult,
    SkillManifest,
    ValidationResult,
)


SCHEMAS = {
    "error-envelope.schema.json": ErrorEnvelope,
    "failure-context.schema.json": FailureContext,
    "generation-result.schema.json": GenerationResult,
    "grounding-result.schema.json": GroundingResult,
    "hint-pack.schema.json": HintPackManifest,
    "hint-payload.schema.json": HintPayload,
    "hint-resolution-result.schema.json": HintResolutionResult,
    "inspection-snapshot-result.schema.json": InspectionSnapshotResult,
    "provider-metadata.schema.json": ProviderMetadata,
    "repair-diagnostic-result.schema.json": RepairDiagnosticResult,
    "repair-session.schema.json": RepairSessionSummary,
    "repair-step-result.schema.json": RepairStepResult,
    "refactor-result.schema.json": RefactorResult,
    "robot-context-mutation-result.schema.json": RobotContextMutationResult,
    "robot-context-view.schema.json": RobotContextView,
    "scaffold-result.schema.json": ScaffoldResult,
    "skill-manifest.schema.json": SkillManifest,
    "validation-result.schema.json": ValidationResult,
}


def export_schemas(output_dir: Path | None = None) -> list[Path]:
    target_dir = output_dir or REPO_ROOT / "assets" / "schemas"
    target_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for file_name, model in sorted(SCHEMAS.items()):
        schema_path = target_dir / file_name
        schema = model.model_json_schema()
        schema_path.write_text(f"{json.dumps(schema, indent=2, sort_keys=True)}\n")
        written.append(schema_path)
    return written


def main() -> int:
    written = export_schemas()
    print(f"Exported {len(written)} schemas to assets/schemas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
