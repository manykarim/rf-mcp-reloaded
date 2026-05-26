from __future__ import annotations

import re
from pathlib import Path

from rfmcp_core.contracts import (
    DiagnosticFinding,
    FailureCategory,
    FailureContext,
    HintResolutionResult,
    ProvenanceKind,
    ProvenanceRecord,
    RepairDiagnosticResult,
    Severity,
    ValidationResult,
)
from rfmcp_core.hints import resolve_hints
from rfmcp_core.hints.plugin_manager import ProviderPluginManager
from rfmcp_core.robot.validation import validate_robot_artifact


def _split_robot_cells(raw_line: str) -> list[str]:
    return [part.strip() for part in re.split(r"\t+|\s{2,}", raw_line.strip()) if part.strip()]


def _scan_robot_artifact(target: str) -> tuple[list[str], list[str]]:
    path = Path(target)
    if not path.exists() or path.suffix != ".robot":
        return [], []

    libraries: list[str] = []
    keywords: list[str] = []
    section = ""
    for raw_line in path.read_text().splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("***") and stripped.endswith("***"):
            section = stripped.casefold()
            continue

        cells = _split_robot_cells(raw_line)
        if not cells:
            continue
        if section == "*** settings ***" and cells[0].casefold() == "library" and len(cells) > 1:
            libraries.append(cells[1])
        elif section in {"*** test cases ***", "*** keywords ***"} and raw_line.startswith((" ", "\t")):
            keywords.append(cells[0])
    return libraries, keywords


def _classify_error_code(failure_message: str | None, explicit_error_code: str | None) -> str | None:
    if explicit_error_code:
        return explicit_error_code
    if not failure_message:
        return None
    lowered = failure_message.casefold()
    if "no keyword with name" in lowered:
        return "unknown-keyword"
    if re.search(r"expected\s+\d+(?:\s+to\s+\d+)?\s+arguments?,\s+got\s+\d+", lowered):
        return "keyword-arguments-mismatch"
    if "multiple keywords with name" in lowered or "give the full name" in lowered:
        return "ambiguous-keyword"
    return "execution-failed"


def build_failure_context(
    target: str,
    *,
    failure_message: str | None = None,
    error_code: str | None = None,
    live_state_available: bool = True,
    validation_result: ValidationResult | None = None,
) -> FailureContext:
    validation = validation_result or validate_robot_artifact(target)
    libraries, observed_keywords = _scan_robot_artifact(target)
    classified_error_code = _classify_error_code(failure_message, error_code)
    categories: list[FailureCategory] = []
    if classified_error_code in {"unknown-keyword", "ambiguous-keyword"}:
        categories.append(FailureCategory.KEYWORD)
    if classified_error_code == "keyword-arguments-mismatch":
        categories.append(FailureCategory.ARGUMENT)
    if validation.error is not None or any(issue.severity == Severity.ERROR for issue in validation.issues):
        categories.append(FailureCategory.EXECUTION)

    keyword_match = None
    if failure_message:
        match = re.search(r"'([^']+)'", failure_message)
        keyword_match = match.group(1) if match else None

    return FailureContext(
        target=target,
        error_code=classified_error_code,
        failure_message=failure_message,
        live_state_available=live_state_available,
        libraries=libraries,
        observed_keywords=observed_keywords,
        categories=list(dict.fromkeys(categories)),
        validation_issue_codes=([validation.error.code] if validation.error is not None else []) + [issue.code for issue in validation.issues],
        keyword=keyword_match,
    )


def run_repair_diagnostics(
    target: str,
    *,
    failure_message: str | None = None,
    error_code: str | None = None,
    live_state_available: bool = True,
    provider_manager: ProviderPluginManager | None = None,
    validation_result: ValidationResult | None = None,
    hint_resolution: HintResolutionResult | None = None,
) -> RepairDiagnosticResult:
    validation = validation_result or validate_robot_artifact(target)
    base_context = build_failure_context(
        target,
        failure_message=failure_message,
        error_code=error_code,
        live_state_available=live_state_available,
        validation_result=validation,
    )
    if hint_resolution is None:
        hint_resolution = resolve_hints(base_context, provider_manager=provider_manager)
    context = hint_resolution.context if hint_resolution.ok else base_context
    findings: list[DiagnosticFinding] = []

    def add_finding(finding: DiagnosticFinding) -> None:
        if finding.code not in {item.code for item in findings}:
            findings.append(finding)

    if validation.error is not None:
        add_finding(
            DiagnosticFinding(
                code=validation.error.code,
                message=validation.error.message,
                severity=validation.error.severity,
                category=FailureCategory.EXECUTION,
                provenance=validation.error.provenance,
                suggested_next_step=validation.error.suggested_next_step,
                details=validation.error.details,
            )
        )

    for issue in validation.issues:
        add_finding(
            DiagnosticFinding(
                code=issue.code,
                message=issue.message,
                severity=issue.severity,
                category=FailureCategory.EXECUTION,
                provenance=ProvenanceRecord(
                    kind=ProvenanceKind.OBSERVED,
                    source="validation-fallback",
                    source_type="validation",
                    source_id=issue.code,
                ),
                suggested_next_step="Correct the validation issue before retrying repair diagnostics or execution.",
                details={"path": issue.path, "line": issue.line, "column": issue.column},
            )
        )

    if context.library and all(library.casefold() != context.library.casefold() for library in context.libraries):
        add_finding(
            DiagnosticFinding(
                code=f"{context.library.casefold()}-library-missing",
                message=f"{context.library}-specific keywords are present, but the {context.library} library is not imported in *** Settings ***.",
                severity=Severity.ERROR,
                category=FailureCategory.LIBRARY,
                provenance=ProvenanceRecord(
                    kind=ProvenanceKind.INFERRED,
                    source="repair-diagnostics",
                    source_type="normalized-context",
                    source_id=f"{context.library.casefold()}-library-missing",
                ),
                suggested_next_step=f"Add `Library    {context.library}` under *** Settings *** before retrying the failing test.",
            )
        )

    if context.error_code == "unknown-keyword":
        add_finding(
            DiagnosticFinding(
                code="unknown-keyword",
                message="The failure message indicates a missing or misspelled keyword.",
                severity=Severity.ERROR,
                category=FailureCategory.KEYWORD,
                provenance=ProvenanceRecord(
                    kind=ProvenanceKind.INFERRED,
                    source="repair-diagnostics",
                    source_type="failure-message",
                    source_id="unknown-keyword",
                ),
                suggested_next_step="Compare the failing keyword spelling against the imported library keywords or project keyword resources.",
            )
        )
    elif context.error_code == "keyword-arguments-mismatch":
        add_finding(
            DiagnosticFinding(
                code="keyword-arguments-mismatch",
                message="The failure message indicates a keyword argument mismatch.",
                severity=Severity.ERROR,
                category=FailureCategory.ARGUMENT,
                provenance=ProvenanceRecord(
                    kind=ProvenanceKind.INFERRED,
                    source="repair-diagnostics",
                    source_type="failure-message",
                    source_id="keyword-arguments-mismatch",
                ),
                suggested_next_step="Review the keyword signature and update the argument count or names before rerunning the test.",
            )
        )
    elif context.error_code == "ambiguous-keyword":
        add_finding(
            DiagnosticFinding(
                code="ambiguous-keyword",
                message="The failure message indicates an ambiguous keyword match.",
                severity=Severity.WARNING,
                category=FailureCategory.KEYWORD,
                provenance=ProvenanceRecord(
                    kind=ProvenanceKind.INFERRED,
                    source="repair-diagnostics",
                    source_type="failure-message",
                    source_id="ambiguous-keyword",
                ),
                suggested_next_step="Qualify the keyword with the intended library or resource name before rerunning the test.",
            )
        )

    if not live_state_available:
        add_finding(
            DiagnosticFinding(
                code="live-state-unavailable",
                message="Live-state inspection is unavailable, so repair guidance is limited to deterministic CLI fallback analysis.",
                severity=Severity.WARNING,
                category=FailureCategory.EXECUTION,
                provenance=ProvenanceRecord(
                    kind=ProvenanceKind.INFERRED,
                    source="repair-diagnostics",
                    source_type="fallback",
                    source_id="live-state-unavailable",
                ),
                suggested_next_step="Use repair-hints output plus validation findings to continue the repair without MCP.",
            )
        )

    ok = validation.ok and not any(item.severity == Severity.ERROR for item in findings)
    return RepairDiagnosticResult(
        ok=ok and hint_resolution.ok,
        context=context,
        validation=validation,
        verification_mode="static-fallback",
        findings=findings,
        hint=hint_resolution.hint,
        recovery_candidates=hint_resolution.recovery_candidates,
        provider_failures=hint_resolution.provider_failures,
        hint_conflicts=hint_resolution.conflicts,
        error=hint_resolution.error,
    )
