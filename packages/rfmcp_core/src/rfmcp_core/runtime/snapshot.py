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
from rfmcp_core.runtime.execution import _json_safe
from rfmcp_core.runtime.session import LiveSessionStore


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
            message=f"Live session '{session_id}' was not found.",
            severity=Severity.ERROR,
            provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="session-store"),
            retryable=True,
            suggested_next_step="Open a live session before requesting an inspection snapshot.",
            details={"session_id": session_id},
        )
    return ErrorEnvelope(
        code="session-not-open",
        message=f"Live session '{session_id}' is not available for inspection snapshots.",
        severity=Severity.ERROR,
        provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="session-store"),
        retryable=True,
        suggested_next_step="Use an open or interrupted live session when requesting inspection snapshots.",
        details={"session_id": session_id, "status": status},
    )


# Candidate live keywords per snapshot kind, in resolution order. Empty means no
# first-class live source exists in v1, so the snapshot is reported unavailable.
_SNAPSHOT_KEYWORDS: dict[SnapshotKind, tuple[str, ...]] = {
    SnapshotKind.DOM: ("Get Page Source", "Get Source"),
    SnapshotKind.SCREENSHOT: ("Take Screenshot",),
    SnapshotKind.ACCESSIBILITY: (),
    SnapshotKind.LAST_API_RESPONSE: (),
}


def _observed(source: str) -> ProvenanceRecord:
    return ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source=source)


def _snapshot_unavailable(
    session_id: str,
    snapshot_kind: str,
    *,
    attempted: list[str],
    detail: str | None,
) -> ErrorEnvelope:
    return ErrorEnvelope(
        code="snapshot-unavailable",
        message=f"No live source could provide a '{snapshot_kind}' snapshot for this session.",
        severity=Severity.ERROR,
        provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="live-execution"),
        retryable=True,
        suggested_next_step="Load and drive a capable library (e.g. open a page with Browser or SeleniumLibrary) before requesting this snapshot, or request the app_context kind.",
        details={
            "session_id": session_id,
            "snapshot_kind": snapshot_kind,
            "attempted_keywords": attempted,
            "error": detail,
        },
    )


def capture_inspection_snapshot(
    store: LiveSessionStore,
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
            message=f"Snapshot kind '{snapshot_kind}' is not enabled for this live session.",
            severity=Severity.ERROR,
            provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="session-store"),
            retryable=True,
            suggested_next_step="Request an allowed snapshot kind for this session or open a session with the required inspection capability.",
            details={"session_id": session_id, "snapshot_kind": snapshot_kind},
        )

    engine = store.get_or_create_engine(session_id)
    if engine is None:  # session closed between the status check and here
        return _session_error(session_id, SessionStatus.CLOSED.value)

    # app_context is derivable from real, always-available live session state.
    if kind == SnapshotKind.APP_CONTEXT:
        try:
            libraries = engine.imported_libraries()
            variables = sorted(engine.get_variables().keys())
        except Exception as exc:
            return _snapshot_unavailable(session_id, snapshot_kind, attempted=[], detail=str(exc))
        payload = {
            "session_id": record.session_id,
            "step_count": record.step_count,
            "loaded_libraries": libraries,
            "variables": variables,
        }
        return InspectionSnapshotResult(
            session=record.to_summary(),
            snapshot_kind=kind,
            provenance=_observed("live-session"),
            payload=payload,
        )

    # DOM / screenshot / accessibility / last_api_response come from a real library
    # keyword if one is loaded and can produce them; otherwise report unavailable.
    candidates = _SNAPSHOT_KEYWORDS.get(kind, ())
    last_error: str | None = None
    for keyword in candidates:
        try:
            value = engine.query(keyword)
        except Exception as exc:
            last_error = str(exc) or exc.__class__.__name__
            continue
        return InspectionSnapshotResult(
            session=record.to_summary(),
            snapshot_kind=kind,
            provenance=_observed(f"keyword:{keyword}"),
            payload={"keyword": keyword, "value": _json_safe(value)},
        )

    return _snapshot_unavailable(session_id, snapshot_kind, attempted=list(candidates), detail=last_error)
