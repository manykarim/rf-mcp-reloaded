from __future__ import annotations

from pathlib import Path
import shlex
import subprocess
import sys

from rfmcp_core.contracts import (
    ErrorEnvelope,
    ExecutionProof,
    GenerationEvidenceItem,
    GenerationRequest,
    GenerationResult,
    HintResolutionResult,
    ProvenanceKind,
    ProvenanceRecord,
    RepairDiagnosticResult,
    ScaffoldArtifact,
    Severity,
    ValidationResult,
)
from rfmcp_core.hints import resolve_hints
from rfmcp_core.robot import escape_comment_cells, render_suite_text, run_repair_diagnostics
from rfmcp_core.robot.validation import validate_robot_artifact

from rfmcp_cli.workflows.grounding import _generic_scaffold_guidance

ROBOT_EXECUTION_TIMEOUT_SECONDS = 30


def _generation_error(
    code: str,
    message: str,
    suggested_next_step: str,
    *,
    retryable: bool = False,
    details: dict[str, str] | None = None,
) -> ErrorEnvelope:
    return ErrorEnvelope(
        code=code,
        message=message,
        severity=Severity.ERROR,
        provenance=ProvenanceRecord(
            kind=ProvenanceKind.OBSERVED,
            source="rfmcp-cli.generation",
            source_type="workflow",
            source_id=code,
        ),
        retryable=retryable,
        suggested_next_step=suggested_next_step,
        details=details,
    )


def _normalize_body_line(raw: str) -> str:
    stripped = raw.strip()
    return f"    {escape_comment_cells(stripped)}" if stripped else ""


def _build_documentation(tasks: list[str], documentation: str | None, test_case_name: str) -> str:
    if documentation:
        return documentation
    if tasks:
        return f"Generated suite for {', '.join(tasks)}."
    return f"Generated suite for {test_case_name}."


def _inject_test_body(content: str, body_lines: list[str]) -> str | None:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == "No Operation":
            return "\n".join(lines[:index] + body_lines + lines[index + 1 :]) + "\n"
    return None


def _run_robot_execution(target: str) -> ExecutionProof:
    path = Path(target)
    command = [
        sys.executable,
        "-m",
        "robot",
        "--output",
        "NONE",
        "--report",
        "NONE",
        "--log",
        "NONE",
        path.name,
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=path.parent,
            capture_output=True,
            text=True,
            check=False,
            timeout=ROBOT_EXECUTION_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        detail = f"Robot execution timed out after {ROBOT_EXECUTION_TIMEOUT_SECONDS} seconds."
        return ExecutionProof(ok=False, command=command, detail=detail, output_excerpt=detail)

    output = "\n".join(part for part in (completed.stdout or "", completed.stderr or "") if part).strip()
    if completed.returncode == 0:
        detail = "Robot execution succeeded."
        return ExecutionProof(
            ok=True,
            command=command,
            return_code=completed.returncode,
            detail=detail,
            output_excerpt=output or None,
        )

    detail = output.splitlines()[-1] if output else "Robot execution failed."
    return ExecutionProof(
        ok=False,
        command=command,
        return_code=completed.returncode,
        detail=detail,
        output_excerpt=output or None,
    )


def _correction_path(target: str, *, failure_message: str | None = None) -> list[str]:
    commands = [f"rfmcp validate {shlex.quote(target)} --json"]
    if failure_message:
        commands.append(
            "rfmcp repair-diagnostics "
            f"{shlex.quote(target)} --failure-message {shlex.quote(failure_message)} --no-live-state --json"
        )
        commands.append(
            "rfmcp repair-hints "
            f"{shlex.quote(target)} --failure-message {shlex.quote(failure_message)} --no-live-state --json"
        )
    else:
        commands.append(f"rfmcp repair-diagnostics {shlex.quote(target)} --no-live-state --json")
        commands.append(f"rfmcp repair-hints {shlex.quote(target)} --no-live-state --json")
    return commands


def _suggested_next_step(correction_path: list[str], fallback: str) -> str:
    if len(correction_path) > 1:
        return correction_path[1]
    if correction_path:
        return correction_path[0]
    return fallback


def _build_evidence(
    request: GenerationRequest,
    *,
    artifact_content: str,
    execution_ok: bool,
) -> list[GenerationEvidenceItem]:
    evidence: list[GenerationEvidenceItem] = []
    for task in request.tasks:
        present_in_artifact = task in artifact_content
        evidence.append(
            GenerationEvidenceItem(
                kind="task",
                requested=task,
                present_in_artifact=present_in_artifact,
                fulfilled=execution_ok and present_in_artifact,
                detail="Execution completed successfully for the requested task." if execution_ok and present_in_artifact else "Execution did not complete successfully for the requested task.",
            )
        )
    for step in request.steps:
        present_in_artifact = step in artifact_content
        evidence.append(
            GenerationEvidenceItem(
                kind="step",
                requested=step,
                present_in_artifact=present_in_artifact,
                fulfilled=execution_ok and present_in_artifact,
                detail="Generated step executed successfully." if execution_ok and present_in_artifact else "Generated step could not be verified as executed successfully.",
            )
        )
    for assertion in request.assertions:
        present_in_artifact = assertion in artifact_content
        evidence.append(
            GenerationEvidenceItem(
                kind="assertion",
                requested=assertion,
                present_in_artifact=present_in_artifact,
                fulfilled=execution_ok and present_in_artifact,
                detail="Generated assertion passed during robot execution." if execution_ok and present_in_artifact else "Generated assertion did not pass during robot execution.",
            )
        )
    return evidence


def _build_failure_context(
    target: str,
    *,
    failure_message: str | None,
) -> tuple[RepairDiagnosticResult, HintResolutionResult]:
    diagnostics = run_repair_diagnostics(target, failure_message=failure_message, live_state_available=False)
    return diagnostics, resolve_hints(diagnostics.context)


def generate_suite_artifact(
    target: str,
    *,
    tasks: list[str] | None = None,
    steps: list[str] | None = None,
    assertions: list[str] | None = None,
    suite_name: str | None = None,
    test_case_name: str = "Generated Test",
    libraries: list[str] | None = None,
    resources: list[str] | None = None,
    documentation: str | None = None,
    force: bool = False,
) -> GenerationResult:
    request = GenerationRequest(
        tasks=list(tasks or []),
        steps=list(steps or []),
        assertions=list(assertions or []),
        libraries=list(libraries or []),
        resources=list(resources or []),
    )
    if not request.steps and not request.assertions:
        error = _generation_error(
            "missing-generation-input",
            "Generation requires at least one requested step or assertion.",
            "Provide one or more --step or --assertion values and rerun generation.",
            details={"target": target},
        )
        return GenerationResult(
            ok=False,
            request=request,
            artifact=ScaffoldArtifact(
                path=target,
                kind="suite",
                content="# Generation input missing.\n",
                validation=ValidationResult(ok=False, target=target, error=error),
            ),
            evidence=[],
            execution=ExecutionProof(ok=False, command=[], detail=error.message),
            preventive_guidance=[],
            correction_path=[],
            error=error,
        )

    body_steps = [item for item in [*request.steps, *request.assertions] if item.strip()]
    if not body_steps:
        error = _generation_error(
            "missing-generation-input",
            "Generation requires at least one non-empty requested step or assertion.",
            "Provide one or more non-empty --step or --assertion values and rerun generation.",
            details={"target": target},
        )
        return GenerationResult(
            ok=False,
            request=request,
            artifact=ScaffoldArtifact(
                path=target,
                kind="suite",
                content="# Generation input missing.\n",
                validation=ValidationResult(ok=False, target=target, error=error),
            ),
            evidence=[],
            execution=ExecutionProof(ok=False, command=[], detail=error.message),
            preventive_guidance=[],
            correction_path=[],
            error=error,
        )

    path = Path(target)
    if path.suffix != ".robot":
        error = _generation_error(
            "unsupported-extension",
            "Generation expects a .robot file target.",
            "Point the generate command at a .robot file path and retry.",
            details={"target": target, "suffix": path.suffix},
        )
        return GenerationResult(
            ok=False,
            request=request,
            artifact=ScaffoldArtifact(
                path=target,
                kind="suite",
                content=f"# Generation refused: {error.code}.\n",
                validation=ValidationResult(ok=False, target=target, error=error),
            ),
            evidence=[],
            execution=ExecutionProof(ok=False, command=[], detail=error.message),
            preventive_guidance=[],
            correction_path=[],
            error=error,
        )

    if path.exists() and not force:
        error = _generation_error(
            "target-exists",
            f"Generation target '{target}' already exists.",
            "Rerun with force enabled or choose a new target path.",
            retryable=True,
            details={"target": target},
        )
        return GenerationResult(
            ok=False,
            request=request,
            artifact=ScaffoldArtifact(
                path=target,
                kind="suite",
                content=f"# Generation refused: {error.code}.\n",
                validation=ValidationResult(ok=False, target=target, error=error),
            ),
            evidence=[],
            execution=ExecutionProof(ok=False, command=[], detail=error.message),
            preventive_guidance=[],
            correction_path=[],
            error=error,
        )

    # BuiltIn is implicit in scaffold output; mirror that for canonical Settings.
    deduped_libraries = list(dict.fromkeys(["BuiltIn", *request.libraries]))
    preventive_guidance = _generic_scaffold_guidance("suite", libraries=deduped_libraries)

    # Render the suite via robot.api.parsing (canonical RF7 format: modern AS aliases,
    # no obsolete `${x} =`, proper section ordering, 4-space separators).
    content = render_suite_text(
        test_case_name=test_case_name,
        documentation=_build_documentation(request.tasks, documentation, test_case_name),
        libraries=deduped_libraries,
        resources=list(request.resources),
        body_steps=body_steps,
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    validation = validate_robot_artifact(target)
    artifact = ScaffoldArtifact(path=target, kind="suite", content=content, validation=validation)
    correction_path = _correction_path(target)

    if not validation.ok:
        diagnostics, hint_resolution = _build_failure_context(target, failure_message=None)
        correction_path = _correction_path(target)
        error = _generation_error(
            "generation-validation-failed",
            "Generated artifact failed structural validation.",
            _suggested_next_step(correction_path, f"rfmcp validate {shlex.quote(target)} --json"),
            retryable=True,
            details={"target": target},
        )
        return GenerationResult(
            ok=False,
            request=request,
            artifact=artifact,
            evidence=_build_evidence(request, artifact_content=content, execution_ok=False),
            execution=ExecutionProof(ok=False, command=[], detail=error.message),
            preventive_guidance=preventive_guidance,
            diagnostics=diagnostics,
            hint_resolution=hint_resolution,
            correction_path=correction_path,
            error=error,
        )

    execution = _run_robot_execution(target)
    if execution.ok:
        return GenerationResult(
            ok=True,
            request=request,
            artifact=artifact,
            evidence=_build_evidence(request, artifact_content=content, execution_ok=True),
            execution=execution,
            preventive_guidance=preventive_guidance,
            correction_path=[],
        )

    failure_message = execution.output_excerpt or execution.detail
    diagnostics, hint_resolution = _build_failure_context(target, failure_message=failure_message)
    correction_path = _correction_path(target, failure_message=failure_message)
    error = _generation_error(
        "generation-run-failed",
        "Generated artifact did not complete robot execution successfully.",
        _suggested_next_step(correction_path, f"rfmcp validate {shlex.quote(target)} --json"),
        retryable=True,
        details={"target": target, "return_code": str(execution.return_code or "")},
    )
    return GenerationResult(
        ok=False,
        request=request,
        artifact=artifact,
        evidence=_build_evidence(request, artifact_content=content, execution_ok=False),
        execution=execution,
        preventive_guidance=preventive_guidance,
        diagnostics=diagnostics,
        hint_resolution=hint_resolution,
        correction_path=correction_path,
        error=error,
    )
