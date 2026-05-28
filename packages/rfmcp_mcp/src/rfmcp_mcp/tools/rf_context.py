"""Runtime-context multiplexer for the bounded live Robot Framework session.

Replaces the former pair ``rf_get_context`` / ``rf_set_context``. Reads and
writes runtime variables and library state inside the active session's
namespace. For declarative ``*** Variables ***`` entries that should be
hoisted into the final suite, use ``rf_manage_session(action='set_variable')``
instead.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from rfmcp_core.contracts import ContextAction, ErrorEnvelope
from rfmcp_core.runtime.context import get_runtime_context, set_runtime_context
from rfmcp_core.runtime.session import LiveSessionStore
from rfmcp_mcp.tools._errors import unexpected_tool_error


def build_context_tool(store: LiveSessionStore):
    def rf_context(
        session_id: Annotated[
            str,
            Field(description="The id of an open live session (from rf_session action='open')."),
        ],
        action: Annotated[
            ContextAction,
            Field(description="Context verb: get | set."),
        ],
        key: Annotated[
            str | None,
            Field(
                default=None,
                description="Variable name to write (action='set' only), e.g. '${USERNAME}'. Required for action='set'.",
            ),
        ] = None,
        value: Annotated[
            Any,
            Field(
                default=None,
                description="JSON-safe value to assign (action='set' only). Required for action='set'.",
            ),
        ] = None,
        keys: Annotated[
            list[str] | None,
            Field(
                default=None,
                description="Optional filter for action='get'. When None, all live variables are returned.",
            ),
        ] = None,
    ) -> dict:
        """Read or write runtime context inside an open live session.

        Actions:

        - ``get``: returns ``{ok, context}`` with live runtime variables and loaded libraries from the
          session's namespace. ``keys`` narrows the variables map; omit it to read everything.
        - ``set``: assigns ``value`` to ``key`` inside the live namespace (transient). To declare a
          ``*** Variables ***`` entry that survives into the rendered suite, use
          ``rf_manage_session(action='set_variable')`` instead.
        """

        # Accept either ContextAction members or plain strings (tests / non-FastMCP callers).
        if isinstance(action, str) and not isinstance(action, ContextAction):
            try:
                action = ContextAction(action)
            except ValueError:
                from rfmcp_core.contracts import ProvenanceKind, ProvenanceRecord, Severity

                supported = ", ".join(member.value for member in ContextAction)
                error = ErrorEnvelope(
                    code="unsupported-action",
                    message=f"Action '{action}' is not supported by rf_context.",
                    severity=Severity.ERROR,
                    provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="rf_context"),
                    retryable=False,
                    suggested_next_step=f"Use one of: {supported}.",
                    details={"action": action},
                )
                return {"ok": False, "error": error.model_dump(mode="json")}

        try:
            if action == ContextAction.GET:
                result = get_runtime_context(store, session_id, keys)
                if isinstance(result, ErrorEnvelope):
                    return {"ok": False, "error": result.model_dump(mode="json")}
                return {"ok": True, "context": result.model_dump(mode="json")}

            # action == ContextAction.SET — let runtime emit the canonical invalid-context-key
            # envelope for missing or malformed keys.
            result = set_runtime_context(store, session_id, key or "", value)
            if isinstance(result, ErrorEnvelope):
                return {"ok": False, "error": result.model_dump(mode="json")}
            return {"ok": True, "context": result.model_dump(mode="json")}
        except Exception as exc:
            error = unexpected_tool_error("rf_context", exc)
            return {"ok": False, "error": error.model_dump(mode="json")}

    return rf_context
