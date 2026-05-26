from __future__ import annotations

from dataclasses import dataclass
from difflib import unified_diff
from pathlib import Path
from typing import Literal

from rfmcp_core.contracts import (
    ErrorEnvelope,
    HintCandidate,
    ProvenanceKind,
    ProvenanceRecord,
    RefactorArtifact,
    RefactorChange,
    RefactorRequest,
    RefactorResult,
    RefactorRunVerification,
    Severity,
)
from rfmcp_core.robot.validation import validate_robot_artifact

from rfmcp_cli.workflows.generation import _build_failure_context, _correction_path, _run_robot_execution


ArtifactKind = Literal["suite", "resource"]
SUITE_SECTION_MARKERS = ("*** Test Cases ***", "*** Tasks ***")
RESOURCE_SECTION_MARKER = "*** Keywords ***"


@dataclass(frozen=True)
class BodySection:
    kind: ArtifactKind
    header_index: int
    body_start: int
    body_end: int
    name_index: int


def _refactor_error(
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
            source="rfmcp-cli.refactor",
            source_type="workflow",
            source_id=code,
        ),
        retryable=retryable,
        suggested_next_step=suggested_next_step,
        details=details,
    )


def _infer_kind(path: Path, content: str) -> ArtifactKind:
    if path.suffix == ".resource":
        return "resource"
    if any(marker in content for marker in SUITE_SECTION_MARKERS):
        return "suite"
    return "resource"


def _load_target(target: str) -> tuple[Path, str] | ErrorEnvelope:
    path = Path(target)
    if not path.exists():
        return _refactor_error(
            "path-not-found",
            f"Refactor target '{target}' was not found.",
            "Confirm the existing file path before retrying refactor or regenerate.",
            details={"target": target},
        )
    if path.suffix not in {".robot", ".resource"}:
        return _refactor_error(
            "unsupported-extension",
            "Refactor and regenerate currently expect a .robot or .resource file.",
            "Point the command at an existing Robot Framework suite or resource file and retry.",
            details={"target": target, "suffix": path.suffix},
        )
    content = path.read_text(encoding="utf-8")
    if not content.strip():
        return _refactor_error(
            "empty-artifact",
            "Refactor and regenerate require a non-empty Robot Framework artifact.",
            "Add at least one Robot Framework section before retrying refactor or regenerate.",
            details={"target": target},
        )
    return path, content


def _find_body_section(kind: ArtifactKind, lines: list[str]) -> BodySection | None:
    section_markers = SUITE_SECTION_MARKERS if kind == "suite" else (RESOURCE_SECTION_MARKER,)
    try:
        header_index = next(index for index, line in enumerate(lines) if line.strip() in section_markers)
    except StopIteration:
        return None
    for name_index in range(header_index + 1, len(lines)):
        stripped = lines[name_index].strip()
        if not stripped:
            continue
        if not lines[name_index].startswith((" ", "\t")):
            body_start = name_index + 1
            body_end = len(lines)
            for index in range(body_start, len(lines)):
                candidate = lines[index]
                stripped_candidate = candidate.strip()
                if stripped_candidate.startswith("***") and stripped_candidate.endswith("***"):
                    body_end = index
                    break
                if stripped_candidate and not candidate.startswith((" ", "\t")):
                    body_end = index
                    break
            return BodySection(
                kind=kind,
                header_index=header_index,
                body_start=body_start,
                body_end=body_end,
                name_index=name_index,
            )
    return None


def _set_documentation(lines: list[str], documentation: str) -> tuple[list[str], RefactorChange]:
    settings_index: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "*** Settings ***":
            settings_index = index
            continue
        if settings_index is not None:
            if stripped.startswith("Documentation    "):
                before = stripped.removeprefix("Documentation    ")
                lines[index] = f"Documentation    {documentation}"
                return lines, RefactorChange(kind="documentation", summary="Updated top-level documentation.", before=before, after=documentation)
            if stripped.startswith("***") and stripped.endswith("***"):
                insertion = [f"Documentation    {documentation}"]
                if lines[index - 1].strip():
                    insertion.append("")
                lines[index:index] = insertion
                return lines, RefactorChange(kind="documentation", summary="Inserted documentation into existing settings section.", before=None, after=documentation)
        if settings_index is None and stripped.startswith("***") and stripped.endswith("***"):
            lines[index:index] = ["*** Settings ***", f"Documentation    {documentation}", ""]
            return lines, RefactorChange(kind="documentation", summary="Created settings section with top-level documentation.", before=None, after=documentation)
    if settings_index is not None:
        lines.append(f"Documentation    {documentation}")
        return lines, RefactorChange(kind="documentation", summary="Inserted documentation into existing settings section.", before=None, after=documentation)
    lines.insert(0, "*** Settings ***")
    lines.insert(1, f"Documentation    {documentation}")
    lines.insert(2, "")
    return lines, RefactorChange(kind="documentation", summary="Created settings section with top-level documentation.", before=None, after=documentation)


def _normalize_body_lines(lines: list[str]) -> list[str]:
    return [f"    {line.rstrip()}" for line in lines if line.strip()]


def _build_diff(original_content: str, updated_content: str, target: str) -> str:
    diff = "\n".join(
        unified_diff(
            original_content.splitlines(),
            updated_content.splitlines(),
            fromfile=f"{target}:before",
            tofile=f"{target}:after",
            lineterm="",
        )
    )
    return diff or f"No textual changes detected for {target}."


def _manual_follow_up(kind: ArtifactKind, target: str) -> list[str]:
    if kind == "resource":
        return [f"Run a suite that imports {target} to prove the refactored resource in context."]
    return []


def _rollback_note() -> str:
    return "Attempted changes were rolled back on disk because validation or execution failed. Review the diff before retrying."


def _restore_original_content(path: Path, original_content: str) -> None:
    path.write_text(original_content, encoding="utf-8")


def _suggested_next_step(correction_path: list[str], fallback: str) -> str:
    if len(correction_path) > 1:
        return correction_path[1]
    if correction_path:
        return correction_path[0]
    return fallback


def _preventive_guidance(mode: Literal["refactor", "regenerate"], kind: ArtifactKind) -> list[HintCandidate]:
    return [
        HintCandidate(
            hint_id=f"inferred-{mode}-{kind}-verify",
            summary="Review the generated diff before trusting the edited artifact.",
            recovery="Inspect the structured diff, then rerun validation and execution proof before accepting the refactor.",
            provenance=ProvenanceRecord(
                kind=ProvenanceKind.INFERRED,
                source="rfmcp-cli.refactor",
                source_type="workflow",
                source_id=f"inferred-{mode}-{kind}-verify",
            ),
            confidence=0.7,
            tags=["refactor", "regenerate", "verification"],
        )
    ]


def _apply_refactor(
    target: str,
    *,
    mode: Literal["refactor", "regenerate"],
    rename_to: str | None,
    documentation: str | None,
    replace: list[str] | None,
    steps: list[str] | None,
    assertions: list[str] | None,
) -> RefactorResult:
    loaded = _load_target(target)
    if isinstance(loaded, ErrorEnvelope):
        path = Path(target)
        kind = "resource" if path.suffix == ".resource" else "suite"
        empty = "# Refactor target unavailable.\n"
        artifact = RefactorArtifact(path=target, kind=kind, original_content=empty, updated_content=empty, diff=empty)
        return RefactorResult(
            ok=False,
            request=RefactorRequest(mode=mode, target=target, rename_to=rename_to, documentation=documentation, replace=list(replace or []), steps=list(steps or []), assertions=list(assertions or [])),
            artifact=artifact,
            changes=[],
            validation=validate_robot_artifact(target),
            run_verification=RefactorRunVerification(status="failed", detail=loaded.message),
            preventive_guidance=[],
            manual_follow_up=[],
            correction_path=[],
            error=loaded,
        )

    path, original_content = loaded
    kind = _infer_kind(path, original_content)
    lines = original_content.splitlines()
    changes: list[RefactorChange] = []
    replace_specs: list[tuple[str, str]] = []

    for replacement in replace or []:
        if "=" not in replacement:
            error = _refactor_error(
                "invalid-replace-input",
                "Refactor replacements must use the form OLD=NEW.",
                "Rewrite the replacement as an exact OLD=NEW body-line mapping and rerun refactor.",
                details={"target": target, "replacement": replacement},
            )
            artifact = RefactorArtifact(path=target, kind=kind, original_content=original_content, updated_content=original_content, diff=_build_diff(original_content, original_content, target))
            return RefactorResult(
                ok=False,
                request=RefactorRequest(mode=mode, target=target, rename_to=rename_to, documentation=documentation, replace=list(replace or []), steps=list(steps or []), assertions=list(assertions or [])),
                artifact=artifact,
                changes=[],
                validation=validate_robot_artifact(target),
                run_verification=RefactorRunVerification(status="failed", detail=error.message),
                preventive_guidance=_preventive_guidance(mode, kind),
                manual_follow_up=[],
                correction_path=[],
                error=error,
            )
        before, after = replacement.split("=", 1)
        replace_specs.append((before.strip(), after.strip()))

    doc_change: RefactorChange | None = None
    if documentation:
        lines, doc_change = _set_documentation(lines, documentation)

    section = _find_body_section(kind, lines)
    if section is None:
        error = _refactor_error(
            "unsupported-refactor-structure",
            f"Could not locate a refactorable {kind} body in '{target}'.",
            "Point the workflow at a suite or resource with at least one test case or keyword body.",
            details={"target": target, "kind": kind},
        )
        artifact = RefactorArtifact(path=target, kind=kind, original_content=original_content, updated_content=original_content, diff=_build_diff(original_content, original_content, target))
        return RefactorResult(
            ok=False,
            request=RefactorRequest(mode=mode, target=target, rename_to=rename_to, documentation=documentation, replace=list(replace or []), steps=list(steps or []), assertions=list(assertions or [])),
            artifact=artifact,
            changes=[],
            validation=validate_robot_artifact(target),
            run_verification=RefactorRunVerification(status="failed", detail=error.message),
            preventive_guidance=_preventive_guidance(mode, kind),
            manual_follow_up=[],
            correction_path=[],
            error=error,
        )

    if rename_to:
        before = lines[section.name_index].strip()
        lines[section.name_index] = rename_to
        changes.append(RefactorChange(kind="rename", summary=f"Renamed {kind} entry.", before=before, after=rename_to))

    current_body = lines[section.body_start:section.body_end]
    working_body = current_body.copy()

    if mode == "refactor":
        unmatched_replacements: list[str] = []
        for before, after in replace_specs:
            for index, body_line in enumerate(working_body):
                if body_line.strip() == before:
                    working_body[index] = f"    {after}"
                    changes.append(RefactorChange(kind="replace-body-line", summary=f"Replaced body line '{before}'.", before=before, after=after))
                    break
            else:
                unmatched_replacements.append(before)
        if unmatched_replacements:
            error = _refactor_error(
                "replace-target-not-found",
                "One or more requested replacement lines were not found in the existing body.",
                "Confirm the exact existing body lines before retrying refactor replacements.",
                details={"target": target, "missing_lines": "\n".join(unmatched_replacements)},
            )
            artifact = RefactorArtifact(path=target, kind=kind, original_content=original_content, updated_content=original_content, diff=_build_diff(original_content, original_content, target))
            return RefactorResult(
                ok=False,
                request=RefactorRequest(mode=mode, target=target, rename_to=rename_to, documentation=documentation, replace=list(replace or []), steps=list(steps or []), assertions=list(assertions or [])),
                artifact=artifact,
                changes=[],
                validation=validate_robot_artifact(target),
                run_verification=RefactorRunVerification(status="failed", detail=error.message),
                preventive_guidance=_preventive_guidance(mode, kind),
                manual_follow_up=[],
                correction_path=[],
                error=error,
            )
        for body_line in _normalize_body_lines(list(steps or []) + list(assertions or [])):
            working_body.append(body_line)
            changes.append(RefactorChange(kind="append-body-line", summary=f"Appended body line '{body_line.strip()}'.", before=None, after=body_line.strip()))
    else:
        regenerated_body = _normalize_body_lines(list(steps or []) + list(assertions or []))
        if not regenerated_body:
            error = _refactor_error(
                "missing-regenerate-input",
                "Regenerate requires at least one non-empty step or assertion.",
                "Provide one or more --step or --assertion values and rerun regenerate.",
                details={"target": target},
            )
            artifact = RefactorArtifact(path=target, kind=kind, original_content=original_content, updated_content=original_content, diff=_build_diff(original_content, original_content, target))
            return RefactorResult(
                ok=False,
                request=RefactorRequest(mode=mode, target=target, rename_to=rename_to, documentation=documentation, replace=list(replace or []), steps=list(steps or []), assertions=list(assertions or [])),
                artifact=artifact,
                changes=changes,
                validation=validate_robot_artifact(target),
                run_verification=RefactorRunVerification(status="failed", detail=error.message),
                preventive_guidance=_preventive_guidance(mode, kind),
                manual_follow_up=[],
                correction_path=[],
                error=error,
            )
        working_body = regenerated_body
        changes.append(
            RefactorChange(
                kind="regenerate-body",
                summary=f"Regenerated the first {kind} body from deterministic input lines.",
                before="\n".join(line.strip() for line in current_body if line.strip()) or None,
                after="\n".join(line.strip() for line in regenerated_body),
            )
        )

    if doc_change is not None:
        changes.insert(0, doc_change)

    if mode == "refactor" and not changes:
        error = _refactor_error(
            "missing-refactor-input",
            "Refactor requires at least one rename, documentation change, replacement, added step, or added assertion.",
            "Provide at least one deterministic change input and rerun refactor.",
            details={"target": target},
        )
        artifact = RefactorArtifact(path=target, kind=kind, original_content=original_content, updated_content=original_content, diff=_build_diff(original_content, original_content, target))
        return RefactorResult(
            ok=False,
            request=RefactorRequest(mode=mode, target=target, rename_to=rename_to, documentation=documentation, replace=list(replace or []), steps=list(steps or []), assertions=list(assertions or [])),
            artifact=artifact,
            changes=[],
            validation=validate_robot_artifact(target),
            run_verification=RefactorRunVerification(status="failed", detail=error.message),
            preventive_guidance=_preventive_guidance(mode, kind),
            manual_follow_up=[],
            correction_path=[],
            error=error,
        )

    lines[section.body_start:section.body_end] = working_body
    updated_content = "\n".join(lines) + ("\n" if original_content.endswith("\n") else "")
    path.write_text(updated_content, encoding="utf-8")
    artifact = RefactorArtifact(
        path=target,
        kind=kind,
        original_content=original_content,
        updated_content=updated_content,
        diff=_build_diff(original_content, updated_content, target),
    )
    validation = validate_robot_artifact(target)
    correction_path = _correction_path(target)
    preventive_guidance = _preventive_guidance(mode, kind)
    manual_follow_up = _manual_follow_up(kind, target)

    if not validation.ok:
        _restore_original_content(path, original_content)
        diagnostics, hint_resolution = _build_failure_context(target, failure_message=None)
        error = _refactor_error(
            "refactor-validation-failed",
            "Refactored artifact failed structural validation.",
            _suggested_next_step(correction_path, f"rfmcp validate {target} --json"),
            retryable=True,
            details={"target": target, "mode": mode},
        )
        return RefactorResult(
            ok=False,
            request=RefactorRequest(mode=mode, target=target, rename_to=rename_to, documentation=documentation, replace=list(replace or []), steps=list(steps or []), assertions=list(assertions or [])),
            artifact=artifact,
            changes=changes,
            validation=validation,
            run_verification=RefactorRunVerification(status="failed", detail=error.message),
            preventive_guidance=preventive_guidance,
            diagnostics=diagnostics,
            hint_resolution=hint_resolution,
            manual_follow_up=manual_follow_up + [_rollback_note()],
            correction_path=correction_path,
            error=error,
        )

    if kind == "resource":
        return RefactorResult(
            ok=True,
            request=RefactorRequest(mode=mode, target=target, rename_to=rename_to, documentation=documentation, replace=list(replace or []), steps=list(steps or []), assertions=list(assertions or [])),
            artifact=artifact,
            changes=changes,
            validation=validation,
            run_verification=RefactorRunVerification(
                status="not-applicable",
                detail="Run verification is not directly applicable to a standalone resource file.",
            ),
            preventive_guidance=preventive_guidance,
            manual_follow_up=manual_follow_up,
            correction_path=[],
        )

    execution = _run_robot_execution(target)
    if execution.ok:
        return RefactorResult(
            ok=True,
            request=RefactorRequest(mode=mode, target=target, rename_to=rename_to, documentation=documentation, replace=list(replace or []), steps=list(steps or []), assertions=list(assertions or [])),
            artifact=artifact,
            changes=changes,
            validation=validation,
            run_verification=RefactorRunVerification(status="passed", execution=execution, detail=execution.detail),
            preventive_guidance=preventive_guidance,
            manual_follow_up=manual_follow_up,
            correction_path=[],
        )

    failure_message = execution.output_excerpt or execution.detail
    diagnostics, hint_resolution = _build_failure_context(target, failure_message=failure_message)
    correction_path = _correction_path(target, failure_message=failure_message)
    error = _refactor_error(
        "refactor-run-failed",
        "Refactored artifact did not complete robot execution successfully.",
        _suggested_next_step(correction_path, f"rfmcp validate {target} --json"),
        retryable=True,
        details={"target": target, "mode": mode},
    )
    _restore_original_content(path, original_content)
    return RefactorResult(
        ok=False,
        request=RefactorRequest(mode=mode, target=target, rename_to=rename_to, documentation=documentation, replace=list(replace or []), steps=list(steps or []), assertions=list(assertions or [])),
        artifact=artifact,
        changes=changes,
        validation=validation,
        run_verification=RefactorRunVerification(status="failed", execution=execution, detail=execution.detail),
        preventive_guidance=preventive_guidance,
        diagnostics=diagnostics,
        hint_resolution=hint_resolution,
        manual_follow_up=manual_follow_up + [_rollback_note()],
        correction_path=correction_path,
        error=error,
    )


def refactor_existing_artifact(
    target: str,
    *,
    rename_to: str | None = None,
    documentation: str | None = None,
    replace: list[str] | None = None,
    steps: list[str] | None = None,
    assertions: list[str] | None = None,
) -> RefactorResult:
    return _apply_refactor(
        target,
        mode="refactor",
        rename_to=rename_to,
        documentation=documentation,
        replace=replace,
        steps=steps,
        assertions=assertions,
    )


def regenerate_existing_artifact(
    target: str,
    *,
    rename_to: str | None = None,
    documentation: str | None = None,
    steps: list[str] | None = None,
    assertions: list[str] | None = None,
) -> RefactorResult:
    return _apply_refactor(
        target,
        mode="regenerate",
        rename_to=rename_to,
        documentation=documentation,
        replace=None,
        steps=steps,
        assertions=assertions,
    )
