from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from rfmcp_core.contracts import (
    ErrorEnvelope,
    ProvenanceKind,
    ProvenanceRecord,
    RobotContextMutationResult,
    RobotContextView,
    Severity,
    SessionStatus,
)
from rfmcp_core.policy.capabilities import PolicyCapability
from rfmcp_core.policy.enforcement import capability_allowed
from rfmcp_core.policy.loader import load_local_policy_defaults
from rfmcp_core.runtime.session import LiveRepairSessionStore


def _policy_load_error(exc: Exception) -> ErrorEnvelope:
    return ErrorEnvelope(
        code="policy-load-failed",
        message="Local policy defaults could not be loaded for runtime context access.",
        severity=Severity.ERROR,
        provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="local-policy"),
        retryable=False,
        suggested_next_step="Restore a valid local policy file before using runtime context tools.",
        details={"error": type(exc).__name__},
    )


def _session_error(
    session_id: str,
    *,
    operation: str,
    status: str | None = None,
) -> ErrorEnvelope:
    if status is None:
        return ErrorEnvelope(
            code="session-not-found",
            message=f"Repair session '{session_id}' was not found.",
            severity=Severity.ERROR,
            provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="repair-session-store"),
            retryable=True,
            suggested_next_step=f"Open a live repair session before requesting runtime context {operation}.",
            details={"session_id": session_id, "operation": operation},
        )
    return ErrorEnvelope(
        code="session-not-open",
        message=f"Repair session '{session_id}' is not open for runtime context {operation}.",
        severity=Severity.ERROR,
        provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="repair-session-store"),
        retryable=True,
        suggested_next_step=f"Reopen a repair session before requesting runtime context {operation}.",
        details={"session_id": session_id, "status": status, "operation": operation},
    )


def get_runtime_context(
    store: LiveRepairSessionStore,
    session_id: str,
    keys: list[str] | None = None,
) -> RobotContextView | ErrorEnvelope:
    record = store.get_record(session_id)
    if record is None:
        return _session_error(session_id, operation="reads")
    if record.status == SessionStatus.CLOSED:
        return _session_error(session_id, operation="reads", status=record.status.value)

    variables = dict(record.rf_context)
    if keys:
        variables = {key: variables[key] for key in keys if key in variables}
    return RobotContextView(session=record.to_summary(), variables=variables, libraries=list(record.libraries))


def set_runtime_context(
    store: LiveRepairSessionStore,
    session_id: str,
    key: str,
    value: Any,
) -> RobotContextMutationResult | ErrorEnvelope:
    try:
        policy = load_local_policy_defaults()
    except (OSError, ValueError, ValidationError) as exc:
        return _policy_load_error(exc)
    if not capability_allowed(policy, PolicyCapability.CONTEXT_WRITE):
        return ErrorEnvelope(
            code="policy-context-write-disabled",
            message="Runtime context mutation is disabled by local policy.",
            severity=Severity.ERROR,
            provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="local-policy"),
            retryable=False,
            suggested_next_step="Enable runtime context mutation in local policy or continue with read-only diagnostics.",
            details={"session_id": session_id},
        )

    record = store.get_record(session_id)
    if record is None:
        return _session_error(session_id, operation="mutation")
    if record.status != SessionStatus.OPEN:
        return _session_error(session_id, operation="mutation", status=record.status.value)
    if not record.allow_context_write:
        return ErrorEnvelope(
            code="session-context-write-disabled",
            message="This repair session is read-only for runtime context mutation.",
            severity=Severity.ERROR,
            provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="repair-session-store"),
            retryable=True,
            suggested_next_step="Open or reconfigure a session that allows context mutation, or continue with context reads only.",
            details={"session_id": session_id},
        )

    try:
        result = RobotContextMutationResult(session=record.to_summary(), key=key, value=value)
    except ValidationError:
        return ErrorEnvelope(
            code="invalid-context-key",
            message="Runtime context keys must be non-empty strings.",
            severity=Severity.ERROR,
            provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="runtime-context"),
            retryable=False,
            suggested_next_step="Provide a non-empty Robot Framework variable name before retrying the context mutation.",
            details={"session_id": session_id, "key": key},
        )

    summary = store.set_context_value(session_id, key, value) or record.to_summary()
    return result.model_copy(update={"session": summary})
