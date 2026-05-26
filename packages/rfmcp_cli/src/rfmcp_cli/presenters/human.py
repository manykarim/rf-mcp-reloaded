from __future__ import annotations

from rfmcp_core.contracts import (
    GenerationResult,
    GroundingResult,
    HintResolutionResult,
    RefactorResult,
    RepairDiagnosticResult,
    ScaffoldResult,
    ValidationResult,
)


def render_validation_result(result: ValidationResult) -> str:
    lines = [f"Validation target: {result.target}"]
    if result.error is not None:
        lines.append(f"Status: failed ({result.error.code})")
        lines.append(result.error.message)
        lines.append(f"Next step: {result.error.suggested_next_step}")
        return "\n".join(lines)

    lines.append("Status: ok" if result.ok else "Status: failed")
    if result.issues:
        for issue in result.issues:
            lines.append(f"- [{issue.severity.value}] {issue.code}: {issue.message}")
    else:
        lines.append("No validation issues detected.")
    return "\n".join(lines)


def render_generation_result(result: GenerationResult) -> str:
    lines = [f"Generation target: {result.artifact.path}"]
    lines.append("Status: ok" if result.ok else "Status: failed")
    if result.request.tasks:
        lines.append(f"Tasks: {', '.join(result.request.tasks)}")
    if result.error is not None:
        lines.append(f"Error: {result.error.code}")
        lines.append(result.error.message)
        lines.append(f"Next step: {result.error.suggested_next_step}")
    lines.append("Validation: ok" if result.artifact.validation.ok else "Validation: failed")
    if result.artifact.validation.issues:
        for issue in result.artifact.validation.issues:
            lines.append(f"- [{issue.severity.value}] {issue.code}: {issue.message}")
    lines.append("Execution: ok" if result.execution.ok else "Execution: failed")
    if result.error is None or result.execution.detail != result.error.message:
        lines.append(result.execution.detail)
    if result.evidence:
        lines.append("Evidence:")
        for item in result.evidence:
            status = "fulfilled" if item.fulfilled else "not fulfilled"
            lines.append(f"- {item.kind}: {item.requested} [{status}]")
            if item.detail:
                lines.append(f"  Detail: {item.detail}")
    if result.preventive_guidance:
        lines.append("Guidance:")
        for candidate in result.preventive_guidance:
            lines.append(f"- {candidate.hint_id}: {candidate.summary}")
            lines.append(f"  Recovery: {candidate.recovery}")
    if result.hint_resolution is not None and result.hint_resolution.hint.candidates:
        lines.append("Corrective hints:")
        for candidate in result.hint_resolution.hint.candidates:
            lines.append(f"- {candidate.hint_id}: {candidate.summary}")
            lines.append(f"  Recovery: {candidate.recovery}")
    if result.correction_path:
        lines.append("Correction path:")
        for command in result.correction_path:
            lines.append(f"- {command}")
    return "\n".join(lines)


def render_refactor_result(result: RefactorResult) -> str:
    lines = [f"Refactor target: {result.artifact.path}", f"Mode: {result.request.mode}"]
    lines.append("Status: ok" if result.ok else "Status: failed")
    if result.error is not None:
        lines.append(f"Error: {result.error.code}")
        lines.append(result.error.message)
        lines.append(f"Next step: {result.error.suggested_next_step}")
    lines.append("Validation: ok" if result.validation.ok else "Validation: failed")
    if result.validation.issues:
        for issue in result.validation.issues:
            lines.append(f"- [{issue.severity.value}] {issue.code}: {issue.message}")
    lines.append(f"Run verification: {result.run_verification.status}")
    lines.append(result.run_verification.detail)
    if result.changes:
        lines.append("Changes:")
        for change in result.changes:
            lines.append(f"- {change.kind}: {change.summary}")
    if result.manual_follow_up:
        lines.append("Manual follow-up:")
        for item in result.manual_follow_up:
            lines.append(f"- {item}")
    if result.preventive_guidance:
        lines.append("Guidance:")
        for candidate in result.preventive_guidance:
            lines.append(f"- {candidate.hint_id}: {candidate.summary}")
            lines.append(f"  Recovery: {candidate.recovery}")
    if result.hint_resolution is not None and result.hint_resolution.hint.candidates:
        lines.append("Corrective hints:")
        for candidate in result.hint_resolution.hint.candidates:
            lines.append(f"- {candidate.hint_id}: {candidate.summary}")
            lines.append(f"  Recovery: {candidate.recovery}")
    if result.correction_path:
        lines.append("Correction path:")
        for command in result.correction_path:
            lines.append(f"- {command}")
    lines.append("Diff:")
    lines.append(result.artifact.diff)
    return "\n".join(lines)


def render_grounding_result(result: GroundingResult) -> str:
    lines = [f"Grounding query: {result.query}"]
    if result.error is not None:
        lines.append(f"Status: failed ({result.error.code})")
        lines.append(result.error.message)
        lines.append(f"Next step: {result.error.suggested_next_step}")
    else:
        lines.append("Status: ok" if result.ok else "Status: failed")
        if result.libraries:
            lines.append("Libraries:")
            for library in result.libraries:
                provider = f" [{library.provider_id}]" if library.provider_id else ""
                summary = library.description or "No description available."
                lines.append(
                    f"- {library.name}{provider}: {summary}"
                    f" ({library.keyword_count if library.keyword_count is not None else 'unknown'} keywords)"
                )
        else:
            lines.append("Libraries: none")
        if result.keywords:
            lines.append("Keywords:")
            for keyword in result.keywords:
                signature = f" {keyword.args_signature}" if keyword.args_signature else ""
                excerpt = f" - {keyword.documentation_excerpt}" if keyword.documentation_excerpt else ""
                lines.append(f"- {keyword.library_name}.{keyword.keyword_name}{signature}{excerpt}")
        else:
            lines.append("Keywords: none")
    if result.preventive_guidance:
        lines.append("Preventive guidance:")
        for candidate in result.preventive_guidance:
            lines.append(f"- {candidate.hint_id}: {candidate.summary}")
            lines.append(f"  Recovery: {candidate.recovery}")
    if result.provider_failures:
        lines.append("Provider failures:")
        for failure in result.provider_failures:
            lines.append(f"- {failure.provider_id} ({failure.stage}): {failure.error.code}")
    return "\n".join(lines)


def render_repair_diagnostic_result(result: RepairDiagnosticResult) -> str:
    lines = [f"Repair target: {result.context.target}", f"Verification mode: {result.verification_mode}"]
    lines.append("Status: ok" if result.ok else "Status: failed")
    if result.error is not None:
        lines.append(f"Error: {result.error.code}")
        lines.append(result.error.message)
        lines.append(f"Next step: {result.error.suggested_next_step}")
    if result.findings:
        for finding in result.findings:
            lines.append(
                f"- [{finding.severity.value}] {finding.code}: {finding.message}"
                f" ({finding.provenance.kind.value})"
            )
            lines.append(f"  Next step: {finding.suggested_next_step}")
    else:
        lines.append("No structured repair findings detected.")
    if result.hint is not None and result.hint.candidates:
        lines.append("Hint guidance:")
        for candidate in result.hint.candidates:
            lines.append(
                f"- {candidate.hint_id}: {candidate.summary}"
                f" ({candidate.provenance.kind.value})"
            )
            lines.append(f"  Recovery: {candidate.recovery}")
    if result.recovery_candidates:
        lines.append("Recovery candidates:")
        for candidate in result.recovery_candidates:
            lines.append(
                f"- {candidate.candidate_id}: {candidate.summary}"
                f" ({candidate.provenance.kind.value})"
            )
            lines.append(f"  Action: {candidate.action}")
    if result.provider_failures:
        lines.append("Provider failures:")
        for failure in result.provider_failures:
            lines.append(f"- {failure.provider_id} ({failure.stage}): {failure.error.code}")
    if result.hint_conflicts:
        lines.append("Hint conflicts:")
        for conflict in result.hint_conflicts:
            lines.append(
                f"- {conflict.hint_id}: kept {conflict.kept_source}, dropped {conflict.dropped_source}"
            )
    return "\n".join(lines)


def render_scaffold_result(result: ScaffoldResult) -> str:
    lines = [f"Scaffold target: {result.artifact.path}", f"Kind: {result.artifact.kind}"]
    if result.error is not None:
        lines.append(f"Status: failed ({result.error.code})")
        lines.append(result.error.message)
        lines.append(f"Next step: {result.error.suggested_next_step}")
        return "\n".join(lines)

    lines.append("Status: ok" if result.ok else "Status: failed")
    if result.created:
        lines.append("Artifact created.")
    elif result.overwritten:
        lines.append("Artifact overwritten.")
    lines.append("Validation: ok" if result.artifact.validation.ok else "Validation: failed")
    if result.artifact.validation.issues:
        for issue in result.artifact.validation.issues:
            lines.append(f"- [{issue.severity.value}] {issue.code}: {issue.message}")
    lines.append("Content:")
    lines.append(result.artifact.content)
    if result.preventive_guidance:
        lines.append("Preventive guidance:")
        for candidate in result.preventive_guidance:
            lines.append(f"- {candidate.hint_id}: {candidate.summary}")
            lines.append(f"  Recovery: {candidate.recovery}")
    return "\n".join(lines)


def render_hint_resolution_result(result: HintResolutionResult) -> str:
    lines = [f"Hint target: {result.context.target}", "Hint status: ok" if result.ok else "Hint status: failed"]
    if result.error is not None:
        lines.append(f"Error: {result.error.code}")
        lines.append(result.error.message)
        lines.append(f"Next step: {result.error.suggested_next_step}")
        return "\n".join(lines)

    lines.append(f"Packs: {', '.join(result.packs) if result.packs else 'none'}")
    lines.append(f"Providers: {', '.join(result.providers) if result.providers else 'none'}")
    for candidate in result.hint.candidates:
        lines.append(f"- {candidate.hint_id}: {candidate.summary}")
        lines.append(f"  Recovery: {candidate.recovery}")
        lines.append(f"  Source: {candidate.provenance.kind.value} / {candidate.provenance.source}")
    if result.provider_failures:
        lines.append("Provider failures:")
        for failure in result.provider_failures:
            lines.append(f"- {failure.provider_id} ({failure.stage}): {failure.error.code}")
    return "\n".join(lines)
