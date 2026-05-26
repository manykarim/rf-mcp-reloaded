from __future__ import annotations

from rfmcp_core.contracts import ErrorEnvelope
from rfmcp_core.runtime.context import get_runtime_context
from rfmcp_core.runtime.session import LiveRepairSessionStore
from rfmcp_mcp.tools._errors import unexpected_tool_error


def build_get_context_tool(store: LiveRepairSessionStore):
    def rf_get_context(session_id: str, keys: list[str] | None = None) -> dict:
        try:
            result = get_runtime_context(store, session_id, keys)
            if isinstance(result, ErrorEnvelope):
                return {"ok": False, "error": result.model_dump(mode="json")}
            return {"ok": True, "context": result.model_dump(mode="json")}
        except Exception as exc:
            error = unexpected_tool_error("rf_get_context", exc)
            return {"ok": False, "error": error.model_dump(mode="json")}

    return rf_get_context
