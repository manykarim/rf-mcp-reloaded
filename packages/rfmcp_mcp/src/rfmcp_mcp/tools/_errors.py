from __future__ import annotations

from rfmcp_core.contracts import ErrorEnvelope, ProvenanceKind, ProvenanceRecord, Severity


def unexpected_tool_error(tool_name: str, exc: Exception) -> ErrorEnvelope:
    return ErrorEnvelope(
        code="tool-execution-failed",
        message=f"Tool '{tool_name}' failed unexpectedly.",
        severity=Severity.ERROR,
        provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source=tool_name),
        retryable=True,
        suggested_next_step="Retry the tool call. If the failure persists, inspect local logs and fix the underlying implementation error.",
        details={"error": type(exc).__name__},
    )
