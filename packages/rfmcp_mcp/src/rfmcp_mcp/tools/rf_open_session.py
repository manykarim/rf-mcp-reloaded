from __future__ import annotations

from rfmcp_core.runtime.session import LiveRepairSessionStore
from rfmcp_mcp.security.attach_policy import validate_transport_policy


def build_open_session_tool(store: LiveRepairSessionStore):
    def rf_open_repair_session(
        transport: str = "stdio",
        host: str | None = None,
        attach_requested: bool = False,
    ) -> dict:
        error = validate_transport_policy(transport, host=host, attach_requested=attach_requested)
        if error is not None:
            return {"ok": False, "error": error.model_dump(mode="json")}

        summary = store.open_session(transport, attach_requested=attach_requested, http_host=host)
        return {"ok": True, "session": summary.model_dump(mode="json")}

    return rf_open_repair_session
