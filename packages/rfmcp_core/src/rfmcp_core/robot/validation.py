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

    # Parse the artifact with Robot Framework's own model (robot.api) rather than
    # scanning text, so section detection, body checks, and syntax errors are real.
    from robot.api import get_model
    from robot.api.parsing import ModelVisitor

    class _ArtifactValidator(ModelVisitor):
        def __init__(self) -> None:
            self.has_suite_section = False
            self.has_keyword_section = False
            self.empty_body_tests: list[str] = []
            self.syntax_errors: list[str] = []

        def visit_TestCaseSection(self, node) -> None:  # noqa: N802 (robot visitor naming)
            self.has_suite_section = True
            self.generic_visit(node)

        def visit_KeywordSection(self, node) -> None:  # noqa: N802
            self.has_keyword_section = True
            self.generic_visit(node)

        def visit_TestCase(self, node) -> None:  # noqa: N802
            if not list(node.body):
                self.empty_body_tests.append(node.name)

        def visit_Error(self, node) -> None:  # noqa: N802
            self.syntax_errors.extend(node.errors)

    validator = _ArtifactValidator()
    validator.visit(get_model(str(path)))

    for error in validator.syntax_errors:
        issues.append(
            ValidationIssue(
                code="robot-syntax-error",
                message=f"Robot Framework reported a syntax error: {error}",
                severity=Severity.ERROR,
                path=target,
            )
        )

    if not validator.has_suite_section and not validator.has_keyword_section:
        issues.append(
            ValidationIssue(
                code="missing-required-section",
                message="Expected a '*** Test Cases ***', '*** Tasks ***', or '*** Keywords ***' section.",
                severity=Severity.ERROR,
                path=target,
            )
        )

    for test_name in validator.empty_body_tests:
        issues.append(
            ValidationIssue(
                code="missing-indented-body",
                message=f"Test case '{test_name}' has no body; add at least one keyword step.",
                severity=Severity.WARNING,
                path=target,
            )
        )

    return ValidationResult(ok=not any(issue.severity == Severity.ERROR for issue in issues), target=target, issues=issues)
