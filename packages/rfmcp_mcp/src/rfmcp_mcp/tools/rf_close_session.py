from __future__ import annotations

from rfmcp_core.contracts import ErrorEnvelope, ProvenanceKind, ProvenanceRecord, Severity
from rfmcp_core.runtime.session import LiveRepairSessionStore


def build_close_session_tool(store: LiveRepairSessionStore):
    def rf_close_repair_session(session_id: str) -> dict:
        summary = store.close_session(session_id)
        if summary is None:
            error = ErrorEnvelope(
                code="session-not-found",
                message=f"Repair session '{session_id}' was not found.",
                severity=Severity.ERROR,
                provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="repair-session-store"),
                retryable=True,
                suggested_next_step="Open a live repair session before requesting a close operation.",
                details={"session_id": session_id},
            )
            return {"ok": False, "error": error.model_dump(mode="json")}
        return {"ok": True, "session": summary.model_dump(mode="json")}

    return rf_close_repair_session
