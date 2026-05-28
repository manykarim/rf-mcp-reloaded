from __future__ import annotations

from rfmcp_core.contracts import ErrorEnvelope
from rfmcp_core.runtime.session import LiveSessionStore
from rfmcp_core.runtime.snapshot import capture_inspection_snapshot
from rfmcp_mcp.tools._errors import unexpected_tool_error


def build_app_inspect_state_tool(store: LiveSessionStore):
    def app_inspect_state(session_id: str, snapshot_kind: str) -> dict:
        try:
            result = capture_inspection_snapshot(store, session_id, snapshot_kind)
            if isinstance(result, ErrorEnvelope):
                return {"ok": False, "error": result.model_dump(mode="json")}
            return {"ok": True, "snapshot": result.model_dump(mode="json")}
        except Exception as exc:
            error = unexpected_tool_error("app_inspect_state", exc)
            return {"ok": False, "error": error.model_dump(mode="json")}

    return app_inspect_state
