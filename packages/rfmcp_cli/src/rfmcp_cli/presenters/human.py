from __future__ import annotations

from rfmcp_core.contracts import HintResolutionResult, RepairDiagnosticResult, ValidationResult


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
