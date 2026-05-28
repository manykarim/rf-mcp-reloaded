from __future__ import annotations

from rfmcp_core.contracts import ErrorEnvelope, ProvenanceKind, ProvenanceRecord, Severity
from rfmcp_core.runtime.session import LiveSessionStore


def build_get_session_tool(store: LiveSessionStore):
    def rf_get_session(session_id: str) -> dict:
        summary = store.get_summary(session_id)
        if summary is None:
            error = ErrorEnvelope(
                code="session-not-found",
                message=f"Live session '{session_id}' was not found.",
                severity=Severity.ERROR,
                provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="session-store"),
                retryable=True,
                suggested_next_step="Open a live session before requesting its status.",
                details={"session_id": session_id},
            )
            return {"ok": False, "error": error.model_dump(mode="json")}
        return {"ok": True, "session": summary.model_dump(mode="json")}

    return rf_get_session
