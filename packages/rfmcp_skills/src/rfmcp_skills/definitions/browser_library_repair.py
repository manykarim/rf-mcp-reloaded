from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from rfmcp_core.contracts import (
    ErrorEnvelope,
    HintResolutionResult,
    ProvenanceKind,
    ProvenanceRecord,
    RepairDiagnosticResult,
    Severity,
    SkillManifest,
    ValidationResult,
)
from rfmcp_core.hints import resolve_hints
from rfmcp_core.observability.events import JsonlEventWriter, WorkflowEvent
from rfmcp_core.robot import build_failure_context, run_repair_diagnostics
from rfmcp_core.robot.validation import validate_robot_artifact

from rfmcp_skills.catalog import CanonicalSkillDefinition, WorkflowBoundaryStep
from rfmcp_skills.fallbacks import (
    BROWSER_LIBRARY_FLAGSHIP_REPAIR_ID,
    fallback_commands_for,
)
from rfmcp_skills.inputs import RefactorSkillInput

DEFAULT_FAILURE_MESSAGE = "No keyword with name 'New Page' found."
BROWSER_LIBRARY_IMPORT = "Library    Browser"
BROWSER_KEYWORDS = ("New Browser", "New Page", "Click", "Type Text", "Get Title", "Close Browser")
ASSET_DIRECTORY = f"assets/skills/{BROWSER_LIBRARY_FLAGSHIP_REPAIR_ID}"
BOUNDARY_DOC_PATH = "docs/browser-library-flagship-repair.md"
MCP_TOOLS = (
    "rf_open_repair_session",
    "rf_get_context",
    "app_inspect_state",
    "rf_execute_repair_step",
    "rf_close_repair_session",
)
ROBOT_EXECUTION_TIMEOUT_SECONDS = 30


BrowserLibraryRepairDefinition = CanonicalSkillDefinition


@dataclass(frozen=True)
class BrowserLibraryRepairWorkflowResult:
    ok: bool
    definition: BrowserLibraryRepairDefinition
    diagnostics: RepairDiagnosticResult
    hints: HintResolutionResult
    validation_before: ValidationResult
    validation_after: ValidationResult
    applied_patch: str | None
    repaired_content: str
    rerun_ok: bool
    rerun_detail: str
    benchmark_log: str | None = None
    error: ErrorEnvelope | None = None


@dataclass(frozen=True)
class RobotExecutionResult:
    ok: bool
    detail: str
    output: str


MANIFEST = SkillManifest(
    schema_version="1.0",
    skill_id=BROWSER_LIBRARY_FLAGSHIP_REPAIR_ID,
    title="Browser Library Flagship Repair Workflow",
    description="Diagnose, repair, and deterministically re-verify a Browser Library missing-import failure.",
    fallback_commands=list(fallback_commands_for(BROWSER_LIBRARY_FLAGSHIP_REPAIR_ID)),
)

WORKFLOW_STEPS = (
    WorkflowBoundaryStep(
        phase="live-triage",
        surface="mcp",
        detail="If the host supports live-state repair, use bounded MCP triage before this deterministic CLI workflow takes over.",
        reference=", ".join(MCP_TOOLS),
    ),
    WorkflowBoundaryStep(
        phase="diagnose",
        surface="cli",
        detail="Run deterministic repair diagnostics to classify the Browser failure and preserve structured findings.",
        reference="rfmcp repair-diagnostics {target} --failure-message \"No keyword with name 'New Page' found.\" --json",
    ),
    WorkflowBoundaryStep(
        phase="hint-resolution",
        surface="cli",
        detail="Resolve curated, provider, official-docs, and inferred guidance to choose the repair path.",
        reference="rfmcp repair-hints {target} --failure-message \"No keyword with name 'New Page' found.\" --json",
    ),
    WorkflowBoundaryStep(
        phase="repair",
        surface="cli",
        detail="Apply the deterministic Browser import repair when the flagship missing-import scenario is detected.",
        reference="Add `Library    Browser` under *** Settings ***.",
    ),
    WorkflowBoundaryStep(
        phase="rerun-proof",
        surface="cli",
        detail="Capture a baseline execution failure, then return to deterministic validation and executable rerun proof after the repair.",
        reference="python -m robot --output NONE --report NONE --log NONE {target}; rfmcp validate {target} --json",
    ),
)


def browser_library_repair_definition() -> BrowserLibraryRepairDefinition:
    return BrowserLibraryRepairDefinition(
        skill_id=MANIFEST.skill_id,
        manifest=MANIFEST,
        input_model=RefactorSkillInput,
        asset_directory=ASSET_DIRECTORY,
        boundary_doc_path=BOUNDARY_DOC_PATH,
        fallback_commands=tuple(MANIFEST.fallback_commands),
        workflow_steps=WORKFLOW_STEPS,
        mcp_tools=MCP_TOOLS,
    )


def _emit_event(path: Path | None, event: WorkflowEvent) -> None:
    if path is None:
        return
    JsonlEventWriter(path).write(event)


def _split_robot_cells(raw_line: str) -> list[str]:
    return [part.strip() for part in re.split(r"\t+|\s{2,}", raw_line.strip()) if part.strip()]


def _has_browser_library_import(content: str) -> bool:
    section = ""
    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("***") and stripped.endswith("***"):
            section = stripped.casefold()
            continue
        if section != "*** settings ***":
            continue
        cells = _split_robot_cells(raw_line)
        if len(cells) > 1 and cells[0].casefold() == "library" and cells[1].casefold() == "browser":
            return True
    return False


def _insert_browser_library_import(content: str) -> tuple[str, str | None]:
    if _has_browser_library_import(content):
        return content, None

    lines = content.splitlines()
    for index, line in enumerate(lines):
        if line.strip().casefold() == "*** settings ***":
            index += 1
            updated_lines = lines[:index] + [BROWSER_LIBRARY_IMPORT] + lines[index:]
            return "\n".join(updated_lines) + ("\n" if content.endswith("\n") else ""), "insert-browser-library-into-settings"

    prefix = f"*** Settings ***\n{BROWSER_LIBRARY_IMPORT}\n\n"
    return prefix + content, "prepend-browser-settings-section"


def _flagship_error(code: str, message: str, suggested_next_step: str, *, retryable: bool = True) -> ErrorEnvelope:
    return ErrorEnvelope(
        code=code,
        message=message,
        severity=Severity.ERROR,
        provenance=ProvenanceRecord(
            kind=ProvenanceKind.OBSERVED,
            source=BROWSER_LIBRARY_FLAGSHIP_REPAIR_ID,
            source_type="skill-workflow",
            source_id=BROWSER_LIBRARY_FLAGSHIP_REPAIR_ID,
        ),
        retryable=retryable,
        suggested_next_step=suggested_next_step,
    )


def _supports_flagship_missing_import(
    diagnostics: RepairDiagnosticResult,
    *,
    failure_message: str | None,
) -> bool:
    if any(finding.code == "browser-library-missing" for finding in diagnostics.findings):
        return True

    libraries = {item.casefold() for item in diagnostics.context.libraries}
    keywords = {item.casefold() for item in diagnostics.context.observed_keywords}
    matched_keyword = (diagnostics.context.keyword or "").casefold()
    browser_keywords = {keyword.casefold() for keyword in BROWSER_KEYWORDS}
    keyword_signal = matched_keyword in browser_keywords or bool(keywords.intersection(browser_keywords))

    if (
        diagnostics.context.error_code == "unknown-keyword"
        and "browser" not in libraries
        and keyword_signal
    ):
        return True

    if failure_message is not None:
        return False

    return "browser" in libraries and keyword_signal


def _run_robot_execution(target: str) -> RobotExecutionResult:
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
        return RobotExecutionResult(ok=False, detail=detail, output=detail)

    if completed.returncode == 0:
        output = (completed.stdout or "").strip()
        return RobotExecutionResult(ok=True, detail="Robot execution succeeded.", output=output)

    output = "\n".join(part for part in (completed.stdout or "", completed.stderr or "") if part).strip()
    detail = output.splitlines()[-1] if output else "Robot execution failed."
    return RobotExecutionResult(ok=False, detail=detail, output=output)


def _baseline_matches_expected_failure(execution: RobotExecutionResult, failure_message: str | None) -> bool:
    if failure_message is None:
        return execution.ok
    if execution.ok:
        return False
    normalize = lambda text: re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()
    haystacks = [normalize(execution.detail), normalize(execution.output)]
    needle = normalize(failure_message)
    return any(needle in haystack for haystack in haystacks)


def run_browser_library_flagship_repair(
    target: str,
    *,
    failure_message: str = DEFAULT_FAILURE_MESSAGE,
    live_state_available: bool = True,
    benchmark_log: Path | None = None,
) -> BrowserLibraryRepairWorkflowResult:
    definition = browser_library_repair_definition()
    benchmark_path = Path(benchmark_log) if benchmark_log is not None else None
    path = Path(target)
    validation_before = validate_robot_artifact(target)
    base_context = build_failure_context(
        target,
        failure_message=failure_message,
        live_state_available=live_state_available,
        validation_result=validation_before,
    )
    hints = resolve_hints(base_context)
    diagnostics = run_repair_diagnostics(
        target,
        failure_message=failure_message,
        live_state_available=live_state_available,
        validation_result=validation_before,
        hint_resolution=hints,
    )
    initial_content = path.read_text() if path.exists() and path.suffix == ".robot" else ""

    if validation_before.error is not None:
        _emit_event(
            benchmark_path,
            WorkflowEvent(
                surface="cli",
                workflow=definition.skill_id,
                event_type="validation-error",
                detail=validation_before.error.message,
                provenance_kind=ProvenanceKind.OBSERVED,
                benchmark=True,
                metadata={"code": validation_before.error.code},
            ),
        )
        return BrowserLibraryRepairWorkflowResult(
            ok=False,
            definition=definition,
            diagnostics=diagnostics,
            hints=hints,
            validation_before=validation_before,
            validation_after=validation_before,
            applied_patch=None,
            repaired_content=initial_content,
            rerun_ok=False,
            rerun_detail=validation_before.error.message,
            benchmark_log=str(benchmark_path) if benchmark_path is not None else None,
            error=validation_before.error,
        )

    _emit_event(
        benchmark_path,
        WorkflowEvent(
            surface="mcp" if live_state_available else "cli",
            workflow=definition.skill_id,
            event_type="boundary",
            detail="Host-provided live-state MCP triage is available before deterministic CLI proof." if live_state_available else "Deterministic CLI fallback is active for the whole flagship repair flow.",
            provenance_kind=ProvenanceKind.OBSERVED,
            benchmark=True,
            metadata={"tools": ",".join(definition.mcp_tools) if live_state_available else "none"},
        ),
    )
    _emit_event(
        benchmark_path,
        WorkflowEvent(
            surface="cli",
            workflow=definition.skill_id,
            event_type="diagnose",
            detail="Structured repair diagnostics completed.",
            provenance_kind=ProvenanceKind.OBSERVED,
            benchmark=True,
            metadata={"finding_codes": ",".join(finding.code for finding in diagnostics.findings)},
        ),
    )
    _emit_event(
        benchmark_path,
        WorkflowEvent(
            surface="cli",
            workflow=definition.skill_id,
            event_type="hint-resolution",
            detail="Structured repair hints resolved.",
            provenance_kind=ProvenanceKind.CURATED if hints.hint.candidates else ProvenanceKind.INFERRED,
            benchmark=True,
            metadata={
                "hint_ids": ",".join(candidate.hint_id for candidate in hints.hint.candidates),
                "provider_failures": str(len(hints.provider_failures)),
            },
        ),
    )

    if not _supports_flagship_missing_import(diagnostics, failure_message=failure_message):
        error = _flagship_error(
            "unsupported-flagship-scenario",
            "The Browser flagship workflow only auto-applies when diagnostics identify the Browser library missing-import scenario.",
            "Use repair-diagnostics and repair-hints output to choose a manual repair path for this failure mode.",
        )
        _emit_event(
            benchmark_path,
            WorkflowEvent(
                surface="cli",
                workflow=definition.skill_id,
                event_type="unsupported",
                detail=error.message,
                provenance_kind=ProvenanceKind.OBSERVED,
                benchmark=True,
                metadata={"code": error.code},
            ),
        )
        return BrowserLibraryRepairWorkflowResult(
            ok=False,
            definition=definition,
            diagnostics=diagnostics,
            hints=hints,
            validation_before=validation_before,
            validation_after=validation_before,
            applied_patch=None,
            repaired_content=initial_content,
            rerun_ok=False,
            rerun_detail=error.message,
            benchmark_log=str(benchmark_path) if benchmark_path is not None else None,
            error=error,
        )

    baseline_execution = _run_robot_execution(target)
    baseline_matches_expected = _baseline_matches_expected_failure(baseline_execution, failure_message)
    _emit_event(
        benchmark_path,
        WorkflowEvent(
            surface="cli",
            workflow=definition.skill_id,
            event_type="baseline-proof",
            detail=baseline_execution.detail,
            provenance_kind=ProvenanceKind.OBSERVED,
            benchmark=True,
            metadata={
                "baseline_ok": json.dumps(baseline_execution.ok),
                "expected_failure_matched": json.dumps(baseline_matches_expected),
            },
        ),
    )
    if failure_message is not None and not baseline_matches_expected:
        error = _flagship_error(
            "baseline-failure-not-reproduced",
            "The Browser flagship workflow could not reproduce the expected pre-repair failure before applying a patch.",
            "Confirm the failing suite and failure message, then rerun the workflow against the unrepaired artifact.",
            retryable=False,
        )
        _emit_event(
            benchmark_path,
            WorkflowEvent(
                surface="cli",
                workflow=definition.skill_id,
                event_type="baseline-abort",
                detail=error.message,
                provenance_kind=ProvenanceKind.OBSERVED,
                benchmark=True,
                metadata={"code": error.code},
            ),
        )
        return BrowserLibraryRepairWorkflowResult(
            ok=False,
            definition=definition,
            diagnostics=diagnostics,
            hints=hints,
            validation_before=validation_before,
            validation_after=validation_before,
            applied_patch=None,
            repaired_content=initial_content,
            rerun_ok=False,
            rerun_detail=error.message,
            benchmark_log=str(benchmark_path) if benchmark_path is not None else None,
            error=error,
        )

    original_content = initial_content
    repaired_content, applied_patch = _insert_browser_library_import(original_content)
    if applied_patch is not None:
        path.write_text(repaired_content)

    _emit_event(
        benchmark_path,
        WorkflowEvent(
            surface="cli",
            workflow=definition.skill_id,
            event_type="repair",
            detail=applied_patch or "browser-library-import-already-present",
            provenance_kind=ProvenanceKind.CURATED,
            benchmark=True,
            metadata={
                "patched": json.dumps(applied_patch is not None),
                "synthetic_patch": json.dumps(applied_patch is not None),
            },
        ),
    )

    validation_after = validate_robot_artifact(target)
    rerun_execution = _run_robot_execution(target)
    _emit_event(
        benchmark_path,
        WorkflowEvent(
            surface="cli",
            workflow=definition.skill_id,
            event_type="rerun-proof",
            detail=rerun_execution.detail,
            provenance_kind=ProvenanceKind.OBSERVED,
            benchmark=True,
            metadata={"validation_ok": json.dumps(validation_after.ok), "rerun_ok": json.dumps(rerun_execution.ok)},
        ),
    )
    guidance_available = bool(hints.hint.candidates or hints.recovery_candidates)

    return BrowserLibraryRepairWorkflowResult(
        ok=hints.ok and diagnostics.error is None and guidance_available and validation_after.ok and rerun_execution.ok and baseline_matches_expected,
        definition=definition,
        diagnostics=diagnostics,
        hints=hints,
        validation_before=validation_before,
        validation_after=validation_after,
        applied_patch=applied_patch,
        repaired_content=path.read_text(),
        rerun_ok=rerun_execution.ok,
        rerun_detail=rerun_execution.detail,
        benchmark_log=str(benchmark_path) if benchmark_path is not None else None,
    )
