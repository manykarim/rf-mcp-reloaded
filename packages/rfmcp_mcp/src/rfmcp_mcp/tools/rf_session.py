"""Lifecycle multiplexer for the bounded live Robot Framework session.

Replaces the former triplet ``rf_open_session`` / ``rf_get_session`` /
``rf_close_session``. The ``action`` parameter selects the lifecycle verb;
parameters that only apply to ``open`` (``transport``, attach options) are
ignored on the other actions.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from rfmcp_core.contracts import (
    ErrorEnvelope,
    ProvenanceKind,
    ProvenanceRecord,
    SessionAction,
    Severity,
    TransportKind,
)
from rfmcp_core.runtime.session import LiveSessionStore
from rfmcp_mcp.security.attach_policy import _is_loopback_host, validate_transport_policy


def _session_not_found(session_id: str, action: SessionAction) -> dict:
    error = ErrorEnvelope(
        code="session-not-found",
        message=f"Live session '{session_id}' was not found.",
        severity=Severity.ERROR,
        provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="session-store"),
        retryable=True,
        suggested_next_step="Open a live session before requesting its status or closing it.",
        details={"session_id": session_id, "action": action.value},
    )
    return {"ok": False, "error": error.model_dump(mode="json")}


def _missing_session_id(action: SessionAction) -> dict:
    error = ErrorEnvelope(
        code="missing-session-id",
        message=f"Action '{action.value}' requires a session_id.",
        severity=Severity.ERROR,
        provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="rf_session"),
        retryable=False,
        suggested_next_step="Pass the session_id returned by rf_session(action='open').",
        details={"action": action.value},
    )
    return {"ok": False, "error": error.model_dump(mode="json")}


def build_session_tool(store: LiveSessionStore):
    def rf_session(
        action: Annotated[
            SessionAction,
            Field(description="Lifecycle verb: open | get | close."),
        ],
        session_id: Annotated[
            str | None,
            Field(
                default=None,
                description="Existing session id. Required for action='get' and action='close'; ignored for action='open'.",
            ),
        ] = None,
        transport: Annotated[
            TransportKind,
            Field(
                default=TransportKind.STDIO,
                description="Transport hosting the MCP session. action='open' only. http requires a loopback host.",
            ),
        ] = TransportKind.STDIO,
        host: Annotated[
            str | None,
            Field(
                default=None,
                description="HTTP transport bind host. action='open' only. Must be loopback when transport='http'.",
            ),
        ] = None,
        attach_requested: Annotated[
            bool,
            Field(
                default=False,
                description="Opt-in attach bridge to a running RF process (action='open' only). Loopback enforced.",
            ),
        ] = False,
        attach_host: Annotated[
            str | None,
            Field(
                default=None,
                description="Attach-bridge target host. action='open' with attach_requested=True only. Defaults to 127.0.0.1.",
            ),
        ] = None,
        attach_port: Annotated[
            int | None,
            Field(
                default=None,
                description="Attach-bridge target port. action='open' with attach_requested=True only.",
            ),
        ] = None,
    ) -> dict:
        """Manage the lifecycle of a bounded live Robot Framework session.

        Actions:

        - ``open``: create a new live session. Returns ``{ok, session}`` whose ``session.session_id`` is used
          by every other tool in this surface. Transport / attach parameters apply here only.
        - ``get``: read the current summary for an existing session. Requires ``session_id``.
        - ``close``: terminate an existing session and release its execution context. Requires ``session_id``.
        """

        # Accept either Enum members or plain strings (tests / non-FastMCP callers).
        if isinstance(action, str) and not isinstance(action, SessionAction):
            try:
                action = SessionAction(action)
            except ValueError:
                supported = ", ".join(member.value for member in SessionAction)
                error = ErrorEnvelope(
                    code="unsupported-action",
                    message=f"Action '{action}' is not supported by rf_session.",
                    severity=Severity.ERROR,
                    provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="rf_session"),
                    retryable=False,
                    suggested_next_step=f"Use one of: {supported}.",
                    details={"action": action},
                )
                return {"ok": False, "error": error.model_dump(mode="json")}

        if action == SessionAction.OPEN:
            transport_value = transport.value if isinstance(transport, TransportKind) else transport
            error = validate_transport_policy(
                transport_value, host=host, attach_requested=attach_requested
            )
            if error is not None:
                return {"ok": False, "error": error.model_dump(mode="json")}

            if attach_requested:
                effective_attach_host = attach_host or "127.0.0.1"
                if not _is_loopback_host(effective_attach_host):
                    loopback_error = ErrorEnvelope(
                        code="policy-attach-loopback-only",
                        message="Attach bridges must target a loopback host.",
                        severity=Severity.ERROR,
                        provenance=ProvenanceRecord(
                            kind=ProvenanceKind.OBSERVED, source="transport-policy"
                        ),
                        retryable=True,
                        suggested_next_step="Point the attach bridge at 127.0.0.1 or localhost; off-host attach is not allowed.",
                        details={"attach_host": effective_attach_host},
                    )
                    return {"ok": False, "error": loopback_error.model_dump(mode="json")}
                summary = store.open_session(
                    transport_value,
                    attach_requested=True,
                    http_host=host,
                    attach_host=effective_attach_host,
                    attach_port=attach_port,
                )
                return {"ok": True, "session": summary.model_dump(mode="json")}

            summary = store.open_session(
                transport_value, attach_requested=attach_requested, http_host=host
            )
            return {"ok": True, "session": summary.model_dump(mode="json")}

        if not session_id:
            return _missing_session_id(action)

        if action == SessionAction.GET:
            summary = store.get_summary(session_id)
            if summary is None:
                return _session_not_found(session_id, action)
            return {"ok": True, "session": summary.model_dump(mode="json")}

        # action == SessionAction.CLOSE
        summary = store.close_session(session_id)
        if summary is None:
            return _session_not_found(session_id, action)
        return {"ok": True, "session": summary.model_dump(mode="json")}

    return rf_session
