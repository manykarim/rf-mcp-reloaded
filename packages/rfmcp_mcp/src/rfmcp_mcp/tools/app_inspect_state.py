"""Live application-state inspection tool.

Captures approved inspection snapshots from the real loaded library instances
in the active session (DOM, accessibility, screenshot, last API response, app
context). Snapshots carry ``OBSERVED`` provenance and pass through the
allowlist defined per session.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from rfmcp_core.contracts import ErrorEnvelope, SnapshotKind
from rfmcp_core.runtime.session import LiveSessionStore
from rfmcp_core.runtime.snapshot import capture_inspection_snapshot
from rfmcp_mcp.tools._errors import unexpected_tool_error


def build_app_inspect_state_tool(store: LiveSessionStore):
    def app_inspect_state(
        session_id: Annotated[
            str,
            Field(description="The id of an open live session (from rf_session action='open')."),
        ],
        snapshot_kind: Annotated[
            SnapshotKind,
            Field(
                description=(
                    "Which approved live-app slice to capture: "
                    "dom | accessibility | screenshot | last_api_response | app_context."
                ),
            ),
        ],
    ) -> dict:
        """Capture an approved inspection snapshot from the session's loaded library state.

        Returns ``{ok: True, snapshot: InspectionSnapshotResult}`` on success or
        ``{ok: False, error: ErrorEnvelope}`` when the requested kind is not
        allowlisted for this session or no live source can provide it.
        """

        try:
            result = capture_inspection_snapshot(store, session_id, snapshot_kind.value)
            if isinstance(result, ErrorEnvelope):
                return {"ok": False, "error": result.model_dump(mode="json")}
            return {"ok": True, "snapshot": result.model_dump(mode="json")}
        except Exception as exc:
            error = unexpected_tool_error("app_inspect_state", exc)
            return {"ok": False, "error": error.model_dump(mode="json")}

    return app_inspect_state
