from __future__ import annotations

from pathlib import Path

from rfmcp_core.contracts import (
    ErrorEnvelope,
    ProvenanceKind,
    ProvenanceRecord,
    Severity,
    ValidationIssue,
    ValidationResult,
)


SUPPORTED_ARTIFACT_SUFFIXES = (".robot", ".resource")
SUITE_SECTION_MARKERS = ("*** Test Cases ***", "*** Tasks ***")
RESOURCE_SECTION_MARKER = "*** Keywords ***"


def validate_robot_artifact(target: str) -> ValidationResult:
    path = Path(target)
    issues: list[ValidationIssue] = []

    if not path.exists():
        return ValidationResult(
            ok=False,
            target=target,
            error=ErrorEnvelope(
                code="path-not-found",
                message=f"Robot artifact '{target}' was not found.",
                severity=Severity.ERROR,
                provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="filesystem"),
                retryable=False,
                suggested_next_step="Confirm the file path and rerun the validate command.",
                details={"target": target},
            ),
        )

    if path.suffix not in SUPPORTED_ARTIFACT_SUFFIXES:
        return ValidationResult(
            ok=False,
            target=target,
            error=ErrorEnvelope(
                code="unsupported-extension",
                message="Validation currently expects a .robot or .resource file.",
                severity=Severity.ERROR,
                provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="filesystem"),
                retryable=True,
                suggested_next_step="Point the command at a .robot or .resource file, or rename the target before validating again.",
                details={"target": target, "suffix": path.suffix},
            ),
        )

    content = path.read_text()
    has_suite_section = any(marker in content for marker in SUITE_SECTION_MARKERS)
    has_resource_section = RESOURCE_SECTION_MARKER in content

    if not has_suite_section and not has_resource_section:
        issues.append(
            ValidationIssue(
                code="missing-required-section",
                message="Expected a '*** Test Cases ***', '*** Tasks ***', or '*** Keywords ***' section.",
                severity=Severity.ERROR,
                path=target,
            )
        )

    if has_suite_section and "    " not in content:
        issues.append(
            ValidationIssue(
                code="missing-indented-body",
                message="Robot test cases should include at least one indented body line.",
                severity=Severity.WARNING,
                path=target,
            )
        )

    return ValidationResult(ok=not any(issue.severity == Severity.ERROR for issue in issues), target=target, issues=issues)
