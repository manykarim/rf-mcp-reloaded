from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from rfmcp_core.contracts import (
    ErrorEnvelope,
    InspectionSnapshotResult,
    ProvenanceKind,
    ProvenanceRecord,
    Severity,
    SessionStatus,
    SnapshotKind,
)
from rfmcp_core.policy.capabilities import PolicyCapability
from rfmcp_core.policy.enforcement import capability_allowed
from rfmcp_core.policy.loader import load_local_policy_defaults
from rfmcp_core.runtime.session import LiveRepairSessionStore


def _policy_load_error(exc: Exception) -> ErrorEnvelope:
    return ErrorEnvelope(
        code="policy-load-failed",
        message="Local policy defaults could not be loaded for inspection snapshot access.",
        severity=Severity.ERROR,
        provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="local-policy"),
        retryable=False,
        suggested_next_step="Restore a valid local policy file before using inspection snapshot tools.",
        details={"error": type(exc).__name__},
    )


def _session_error(session_id: str, status: str | None = None) -> ErrorEnvelope:
    if status is None:
        return ErrorEnvelope(
            code="session-not-found",
            message=f"Repair session '{session_id}' was not found.",
            severity=Severity.ERROR,
            provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="repair-session-store"),
            retryable=True,
            suggested_next_step="Open a live repair session before requesting an inspection snapshot.",
            details={"session_id": session_id},
        )
    return ErrorEnvelope(
        code="session-not-open",
        message=f"Repair session '{session_id}' is not available for inspection snapshots.",
        severity=Severity.ERROR,
        provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="repair-session-store"),
        retryable=True,
        suggested_next_step="Use an open or interrupted repair session when requesting inspection snapshots.",
        details={"session_id": session_id, "status": status},
    )


def _synthetic_snapshot_payload(
    *,
    session_id: str,
    step_count: int,
    snapshot_kind: SnapshotKind,
    data: Any,
) -> dict[str, Any]:
    return {
        "synthetic": True,
        "source": "repair-session-fixture",
        "session_id": session_id,
        "step_count": step_count,
        "snapshot_kind": snapshot_kind.value,
        "data": data,
    }


def capture_inspection_snapshot(
    store: LiveRepairSessionStore,
    session_id: str,
    snapshot_kind: str,
) -> InspectionSnapshotResult | ErrorEnvelope:
    try:
        kind = SnapshotKind(snapshot_kind)
    except ValueError:
        return ErrorEnvelope(
            code="unsupported-snapshot-kind",
            message=f"Snapshot kind '{snapshot_kind}' is not part of the approved inspection surface.",
            severity=Severity.ERROR,
            provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="inspection-surface"),
            retryable=False,
            suggested_next_step="Use one of the approved snapshot kinds: dom, accessibility, screenshot, last_api_response, or app_context.",
            details={"snapshot_kind": snapshot_kind},
        )

    try:
        policy = load_local_policy_defaults()
    except (OSError, ValueError, ValidationError) as exc:
        return _policy_load_error(exc)
    if not capability_allowed(policy, PolicyCapability.INSPECTION_SNAPSHOT):
        return ErrorEnvelope(
            code="policy-inspection-disabled",
            message="Inspection snapshots are disabled by local policy.",
            severity=Severity.ERROR,
            provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="local-policy"),
            retryable=False,
            suggested_next_step="Enable approved inspection snapshots in local policy or continue without snapshot capture.",
            details={"session_id": session_id, "snapshot_kind": snapshot_kind},
        )

    record = store.get_record(session_id)
    if record is None:
        return _session_error(session_id)
    if record.status == SessionStatus.CLOSED:
        return _session_error(session_id, record.status.value)
    if kind not in record.allowed_snapshot_kinds:
        return ErrorEnvelope(
            code="session-snapshot-disabled",
            message=f"Snapshot kind '{snapshot_kind}' is not enabled for this repair session.",
            severity=Severity.ERROR,
            provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="repair-session-store"),
            retryable=True,
            suggested_next_step="Request an allowed snapshot kind for this session or open a session with the required inspection capability.",
            details={"session_id": session_id, "snapshot_kind": snapshot_kind},
        )

    payload: dict[str, Any]
    if kind == SnapshotKind.DOM:
        payload = _synthetic_snapshot_payload(
            session_id=record.session_id,
            step_count=record.step_count,
            snapshot_kind=kind,
            data={"html": "<body data-rfmcp='repair-session'></body>", "selector": "body"},
        )
    elif kind == SnapshotKind.ACCESSIBILITY:
        payload = _synthetic_snapshot_payload(
            session_id=record.session_id,
            step_count=record.step_count,
            snapshot_kind=kind,
            data={"role": "document", "name": "Repair Session"},
        )
    elif kind == SnapshotKind.SCREENSHOT:
        payload = _synthetic_snapshot_payload(
            session_id=record.session_id,
            step_count=record.step_count,
            snapshot_kind=kind,
            data={"media_type": "image/png", "data_url": "data:image/png;base64,cmZtY3Atc25hcHNob3Q="},
        )
    elif kind == SnapshotKind.LAST_API_RESPONSE:
        payload = _synthetic_snapshot_payload(
            session_id=record.session_id,
            step_count=record.step_count,
            snapshot_kind=kind,
            data={"status": 200, "body": {"ok": True, "source": "repair-session"}},
        )
    else:
        payload = _synthetic_snapshot_payload(
            session_id=record.session_id,
            step_count=record.step_count,
            snapshot_kind=kind,
            data={"current_view": "repair-session", "libraries": list(record.libraries)},
        )

    return InspectionSnapshotResult(session=record.to_summary(), snapshot_kind=kind, payload=payload)
