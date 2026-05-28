"""Live-session management multiplexer.

Bundles the declarative authoring operations that are inherently live-state
(they mutate the session's namespace or record metadata destined for the
final suite's Settings/Variables sections):

- ``import_library`` / ``import_resource`` / ``import_variables`` — route through
  the same stepper as ``rf_execute_step``, so the call is recorded on the session
  and gets hoisted into ``*** Settings ***`` when the final suite is built.
- ``set_variable`` / ``get_variable`` — declarative ``*** Variables ***``
  entries (separate from transient ``rf_set_context`` runtime mutations).
- ``set_setup`` / ``set_teardown`` — Suite/Test/per-Test-Case setup or teardown
  keyword-call declarations (Settings or per-test ``[Setup]``/``[Teardown]``).
- ``set_tags`` — suite-level ``Test Tags`` or per-test ``[Tags]``.
"""

from __future__ import annotations

from typing import Any

from robot.variables import is_assign

from rfmcp_core.contracts import (
    ErrorEnvelope,
    ProvenanceKind,
    ProvenanceRecord,
    SessionStatus,
    Severity,
)
from rfmcp_core.runtime.execution import _json_safe
from rfmcp_core.runtime.session import LiveSessionStore
from rfmcp_core.runtime.stepper import LiveStepper

_IMPORT_ACTIONS = {"import_library", "import_resource", "import_variables"}
_SETUP_TEARDOWN_KINDS = {"setup", "teardown"}
_SETUP_TEARDOWN_SCOPES = {"suite", "test", "test_case"}
_TAGS_SCOPES = {"suite", "test_case"}
_SUPPORTED_ACTIONS: tuple[str, ...] = (
    "import_library",
    "import_resource",
    "import_variables",
    "set_variable",
    "get_variable",
    "set_setup",
    "set_teardown",
    "set_tags",
)


def _error(
    code: str,
    message: str,
    *,
    retryable: bool,
    next_step: str,
    source: str = "rf_manage_session",
    details: dict[str, Any] | None = None,
) -> dict:
    envelope = ErrorEnvelope(
        code=code,
        message=message,
        severity=Severity.ERROR,
        provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source=source),
        retryable=retryable,
        suggested_next_step=next_step,
        details=details or {},
    )
    return {"ok": False, "error": envelope.model_dump(mode="json")}


def _format_import_instruction(action: str, target: str, args: list[str], alias: str | None) -> str:
    cells: list[str]
    if action == "import_library":
        cells = ["Import Library", target, *args]
        if alias:
            cells.extend(["WITH NAME", alias])
    else:  # import_resource / import_variables
        keyword = "Import Resource" if action == "import_resource" else "Import Variables"
        cells = [keyword, target, *args]
    return "    ".join(cells)


def build_manage_session_tool(
    store: LiveSessionStore,
    *,
    stepper: LiveStepper | None = None,
):
    active_stepper = stepper or LiveStepper(store)

    def rf_manage_session(
        session_id: str,
        action: str,
        name: str | None = None,
        args: list[str] | None = None,
        alias: str | None = None,
        value: Any = None,
        scope: str | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        if action not in _SUPPORTED_ACTIONS:
            return _error(
                "unsupported-action",
                f"Action '{action}' is not supported by rf_manage_session.",
                retryable=False,
                next_step=f"Use one of: {', '.join(_SUPPORTED_ACTIONS)}.",
                details={"action": action, "supported": list(_SUPPORTED_ACTIONS)},
            )

        record = store.get_record(session_id)
        if record is None:
            return _error(
                "session-not-found",
                f"Live session '{session_id}' was not found.",
                retryable=True,
                next_step="Open a live session before managing it.",
                source="session-store",
                details={"session_id": session_id, "action": action},
            )
        if record.status != SessionStatus.OPEN:
            return _error(
                "session-not-open",
                f"Live session '{session_id}' is not open for management.",
                retryable=True,
                next_step="Open a new live session before managing imports or settings.",
                source="session-store",
                details={"session_id": session_id, "status": record.status.value, "action": action},
            )

        if action in _IMPORT_ACTIONS:
            if not name:
                return _error(
                    "missing-target",
                    f"Action '{action}' requires the target (library name or file path) in 'name'.",
                    retryable=False,
                    next_step="Provide the library name (import_library) or absolute file path (import_resource/import_variables) in 'name'.",
                    details={"action": action},
                )
            if action != "import_library" and alias:
                return _error(
                    "unsupported-alias",
                    f"Action '{action}' does not support an alias; aliases apply to import_library only.",
                    retryable=False,
                    next_step="Drop the alias parameter or switch to import_library.",
                    details={"action": action},
                )
            instruction = _format_import_instruction(action, name, list(args or []), alias)
            step_result = active_stepper.execute_step(session_id, instruction)
            payload = step_result.model_dump(mode="json")
            response: dict[str, Any] = {
                "ok": payload["ok"],
                "session": payload["session"],
                "action": action,
                "instruction": instruction,
            }
            if payload.get("error"):
                response["error"] = payload["error"]
            return response

        if action == "set_variable":
            if not name or not is_assign(name):
                return _error(
                    "invalid-context-key",
                    f"'{name}' is not a valid Robot Framework variable name.",
                    retryable=False,
                    next_step="Use a valid variable name such as ${NAME}, @{LIST}, or &{MAP}.",
                    source="runtime-context",
                    details={"action": action, "name": name},
                )
            engine = store.get_or_create_engine(session_id)
            if engine is None:
                return _error(
                    "session-not-open",
                    f"Live session '{session_id}' is no longer available.",
                    retryable=True,
                    next_step="Open a new live session.",
                    source="session-store",
                    details={"session_id": session_id, "status": SessionStatus.CLOSED.value},
                )
            try:
                engine.set_variable(name, value)
            except Exception as exc:  # noqa: BLE001
                return _error(
                    "context-write-failed",
                    f"Failed to set variable '{name}': {exc}",
                    retryable=True,
                    next_step="Verify the live session is reachable and retry.",
                    source="runtime-context",
                    details={"action": action, "name": name},
                )
            summary = store.record_declared_variable(session_id, name, value) or record.to_summary()
            return {
                "ok": True,
                "session": summary.model_dump(mode="json"),
                "action": action,
                "name": name,
                "value": _json_safe(value),
            }

        if action == "get_variable":
            if not name:
                return _error(
                    "missing-target",
                    "Action 'get_variable' requires the variable name in 'name'.",
                    retryable=False,
                    next_step="Provide a variable name such as ${X}.",
                    details={"action": action},
                )
            engine = store.get_or_create_engine(session_id)
            if engine is None:
                return _error(
                    "session-not-open",
                    f"Live session '{session_id}' is no longer available.",
                    retryable=True,
                    next_step="Open a new live session.",
                    source="session-store",
                    details={"session_id": session_id, "status": SessionStatus.CLOSED.value},
                )
            if name in record.declared_variables:
                return {
                    "ok": True,
                    "session": record.to_summary().model_dump(mode="json"),
                    "action": action,
                    "name": name,
                    "value": _json_safe(record.declared_variables[name]),
                    "scope": "declared",
                }
            live = engine.get_variables([name])
            if name in live:
                return {
                    "ok": True,
                    "session": record.to_summary().model_dump(mode="json"),
                    "action": action,
                    "name": name,
                    "value": live[name],
                    "scope": "live",
                }
            return _error(
                "variable-not-found",
                f"Variable '{name}' was not found in the live session.",
                retryable=True,
                next_step="Set the variable first via rf_manage_session(action='set_variable', name=...).",
                source="runtime-context",
                details={"action": action, "name": name},
            )

        if action in {"set_setup", "set_teardown"}:
            kind = "setup" if action == "set_setup" else "teardown"
            requested_scope = scope or "suite"
            if requested_scope not in _SETUP_TEARDOWN_SCOPES:
                return _error(
                    "invalid-scope",
                    f"scope '{requested_scope}' is not supported for {action}.",
                    retryable=False,
                    next_step=f"Use one of: {', '.join(sorted(_SETUP_TEARDOWN_SCOPES))}.",
                    details={"action": action, "scope": requested_scope},
                )
            text = (value or "").strip() if isinstance(value, str) else value
            if not isinstance(text, str) or not text:
                return _error(
                    "missing-target",
                    f"Action '{action}' requires the keyword-call string in 'value'.",
                    retryable=False,
                    next_step="Provide a keyword-call line such as 'Open Browser    chromium' in 'value'.",
                    details={"action": action},
                )
            summary = store.set_session_setting(session_id, requested_scope, kind, text) or record.to_summary()
            return {
                "ok": True,
                "session": summary.model_dump(mode="json"),
                "action": action,
                "scope": requested_scope,
                "value": text,
            }

        # action == "set_tags"
        requested_scope = scope or "suite"
        if requested_scope not in _TAGS_SCOPES:
            return _error(
                "invalid-scope",
                f"scope '{requested_scope}' is not supported for set_tags.",
                retryable=False,
                next_step=f"Use one of: {', '.join(sorted(_TAGS_SCOPES))}.",
                details={"action": action, "scope": requested_scope},
            )
        if not tags or not all(isinstance(t, str) and t for t in tags):
            return _error(
                "missing-target",
                "Action 'set_tags' requires a non-empty list of tag strings in 'tags'.",
                retryable=False,
                next_step="Provide a list like ['smoke', 'cart'] in 'tags'.",
                details={"action": action, "tags": tags},
            )
        summary = store.set_session_tags(session_id, requested_scope, tags) or record.to_summary()
        return {
            "ok": True,
            "session": summary.model_dump(mode="json"),
            "action": action,
            "scope": requested_scope,
            "tags": list(tags),
        }

    return rf_manage_session
