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

    if path.suffix != ".robot":
        return ValidationResult(
            ok=False,
            target=target,
            error=ErrorEnvelope(
                code="unsupported-extension",
                message="Validation currently expects a .robot file.",
                severity=Severity.ERROR,
                provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="filesystem"),
                retryable=True,
                suggested_next_step="Point the command at a .robot file or rename the target before validating again.",
                details={"target": target, "suffix": path.suffix},
            ),
        )

    content = path.read_text()
    if "*** Test Cases ***" not in content and "*** Keywords ***" not in content:
        issues.append(
            ValidationIssue(
                code="missing-required-section",
                message="Expected either a '*** Test Cases ***' or '*** Keywords ***' section.",
                severity=Severity.ERROR,
                path=target,
            )
        )

    if "*** Test Cases ***" in content and "    " not in content:
        issues.append(
            ValidationIssue(
                code="missing-indented-body",
                message="Robot test cases should include at least one indented body line.",
                severity=Severity.WARNING,
                path=target,
            )
        )

    return ValidationResult(ok=not any(issue.severity == Severity.ERROR for issue in issues), target=target, issues=issues)
