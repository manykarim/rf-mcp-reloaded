from __future__ import annotations

from rfmcp_core.contracts import ErrorEnvelope, ProvenanceKind, ProvenanceRecord, Severity
from rfmcp_core.runtime.session import LiveSessionStore
from rfmcp_mcp.security.attach_policy import _is_loopback_host, validate_transport_policy


def build_open_session_tool(store: LiveSessionStore):
    def rf_open_session(
        transport: str = "stdio",
        host: str | None = None,
        attach_requested: bool = False,
        attach_host: str | None = None,
        attach_port: int | None = None,
    ) -> dict:
        error = validate_transport_policy(transport, host=host, attach_requested=attach_requested)
        if error is not None:
            return {"ok": False, "error": error.model_dump(mode="json")}

        if attach_requested:
            effective_attach_host = attach_host or "127.0.0.1"
            if not _is_loopback_host(effective_attach_host):
                loopback_error = ErrorEnvelope(
                    code="policy-attach-loopback-only",
                    message="Attach bridges must target a loopback host.",
                    severity=Severity.ERROR,
                    provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="transport-policy"),
                    retryable=True,
                    suggested_next_step="Point the attach bridge at 127.0.0.1 or localhost; off-host attach is not allowed.",
                    details={"attach_host": effective_attach_host},
                )
                return {"ok": False, "error": loopback_error.model_dump(mode="json")}
            summary = store.open_session(
                transport,
                attach_requested=True,
                http_host=host,
                attach_host=effective_attach_host,
                attach_port=attach_port,
            )
            return {"ok": True, "session": summary.model_dump(mode="json")}

        summary = store.open_session(transport, attach_requested=attach_requested, http_host=host)
        return {"ok": True, "session": summary.model_dump(mode="json")}

    return rf_open_session
