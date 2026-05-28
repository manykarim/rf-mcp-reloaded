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

from typing import Annotated, Any

from pydantic import Field
from robot.variables import is_assign

from rfmcp_core.contracts import (
    ErrorEnvelope,
    ManageSessionAction,
    ProvenanceKind,
    ProvenanceRecord,
    SessionStatus,
    SettingScope,
    Severity,
    TagScope,
)
from rfmcp_core.runtime.execution import _json_safe
from rfmcp_core.runtime.session import LiveSessionStore
from rfmcp_core.runtime.stepper import LiveStepper

_IMPORT_ACTIONS = {
    ManageSessionAction.IMPORT_LIBRARY,
    ManageSessionAction.IMPORT_RESOURCE,
    ManageSessionAction.IMPORT_VARIABLES,
}


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


def _format_import_instruction(
    action: ManageSessionAction, target: str, args: list[str], alias: str | None
) -> str:
    cells: list[str]
    if action == ManageSessionAction.IMPORT_LIBRARY:
        cells = ["Import Library", target, *args]
        if alias:
            cells.extend(["WITH NAME", alias])
    else:  # IMPORT_RESOURCE / IMPORT_VARIABLES
        keyword = "Import Resource" if action == ManageSessionAction.IMPORT_RESOURCE else "Import Variables"
        cells = [keyword, target, *args]
    return "    ".join(cells)


def build_manage_session_tool(
    store: LiveSessionStore,
    *,
    stepper: LiveStepper | None = None,
):
    active_stepper = stepper or LiveStepper(store)

    def rf_manage_session(
        session_id: Annotated[
            str,
            Field(description="The id of an open live session (from rf_session action='open')."),
        ],
        action: Annotated[
            ManageSessionAction,
            Field(
                description=(
                    "Declarative action. Imports run through the live stepper "
                    "(hoisted into *** Settings ***); set_variable/get_variable touch "
                    "*** Variables *** entries; set_setup/set_teardown/set_tags record "
                    "suite or per-test-case metadata."
                ),
            ),
        ],
        name: Annotated[
            str | None,
            Field(
                default=None,
                description=(
                    "Target identifier. For imports: the library name or resource/variables "
                    "file path. For set_variable/get_variable: the variable name (e.g. '${X}')."
                ),
            ),
        ] = None,
        args: Annotated[
            list[str] | None,
            Field(
                default=None,
                description="Import arguments, passed positionally after the import target.",
            ),
        ] = None,
        alias: Annotated[
            str | None,
            Field(
                default=None,
                description="Library alias (action='import_library' only); rendered as 'AS <alias>'.",
            ),
        ] = None,
        value: Annotated[
            Any,
            Field(
                default=None,
                description=(
                    "Payload for write actions. set_variable: the variable value. "
                    "set_setup/set_teardown: the keyword-call string (e.g. 'Open Browser  chromium')."
                ),
            ),
        ] = None,
        scope: Annotated[
            SettingScope | TagScope | None,
            Field(
                default=None,
                description=(
                    "Scope for set_setup/set_teardown (suite|test|test_case) and set_tags (suite|test_case). "
                    "Defaults to 'suite'."
                ),
            ),
        ] = None,
        tags: Annotated[
            list[str] | None,
            Field(
                default=None,
                description="Tag list for action='set_tags'. Must be non-empty strings.",
            ),
        ] = None,
    ) -> dict:
        """Manage declarative session metadata that is destined for the final suite.

        Actions:

        - ``import_library`` / ``import_resource`` / ``import_variables``: route the import through the live
          stepper (so the keyword call is recorded) and hoist it into ``*** Settings ***`` when the suite
          is rendered. ``name`` carries the library name or absolute file path; ``args`` are positional;
          ``alias`` applies to ``import_library`` only.
        - ``set_variable`` / ``get_variable``: declare a ``*** Variables ***`` entry. ``set_variable`` writes
          ``name``/``value`` into the live namespace and records the declaration. ``get_variable`` returns
          the declared value when present and falls back to the live namespace.
        - ``set_setup`` / ``set_teardown``: declare a Suite or Test setup/teardown (``scope='suite'`` or
          ``'test'``) or a per-test-case ``[Setup]``/``[Teardown]`` (``scope='test_case'``). ``value``
          carries the keyword-call line.
        - ``set_tags``: declare ``Test Tags`` (``scope='suite'``) or per-test ``[Tags]``
          (``scope='test_case'``). ``tags`` is the list.
        """

        # Accept either ManageSessionAction members or plain strings (tests / non-FastMCP callers).
        if isinstance(action, str) and not isinstance(action, ManageSessionAction):
            try:
                action = ManageSessionAction(action)
            except ValueError:
                supported = ", ".join(member.value for member in ManageSessionAction)
                return _error(
                    "unsupported-action",
                    f"Action '{action}' is not supported by rf_manage_session.",
                    retryable=False,
                    next_step=f"Use one of: {supported}.",
                    details={"action": action, "supported": [m.value for m in ManageSessionAction]},
                )
        if isinstance(scope, str) and not isinstance(scope, (SettingScope, TagScope)):
            for cls in (SettingScope, TagScope):
                try:
                    scope = cls(scope)
                    break
                except ValueError:
                    continue
            # If neither matched, leave as string — the per-action scope validation below
            # will surface a structured invalid-scope error.

        action_value = action.value
        record = store.get_record(session_id)
        if record is None:
            return _error(
                "session-not-found",
                f"Live session '{session_id}' was not found.",
                retryable=True,
                next_step="Open a live session before managing it.",
                source="session-store",
                details={"session_id": session_id, "action": action_value},
            )
        if record.status != SessionStatus.OPEN:
            return _error(
                "session-not-open",
                f"Live session '{session_id}' is not open for management.",
                retryable=True,
                next_step="Open a new live session before managing imports or settings.",
                source="session-store",
                details={"session_id": session_id, "status": record.status.value, "action": action_value},
            )

        if action in _IMPORT_ACTIONS:
            if not name:
                return _error(
                    "missing-target",
                    f"Action '{action_value}' requires the target (library name or file path) in 'name'.",
                    retryable=False,
                    next_step="Provide the library name (import_library) or absolute file path (import_resource/import_variables) in 'name'.",
                    details={"action": action_value},
                )
            if action != ManageSessionAction.IMPORT_LIBRARY and alias:
                return _error(
                    "unsupported-alias",
                    f"Action '{action_value}' does not support an alias; aliases apply to import_library only.",
                    retryable=False,
                    next_step="Drop the alias parameter or switch to import_library.",
                    details={"action": action_value},
                )
            instruction = _format_import_instruction(action, name, list(args or []), alias)
            step_result = active_stepper.execute_step(session_id, instruction)
            payload = step_result.model_dump(mode="json")
            response: dict[str, Any] = {
                "ok": payload["ok"],
                "session": payload["session"],
                "action": action_value,
                "instruction": instruction,
            }
            if payload.get("error"):
                response["error"] = payload["error"]
            return response

        if action == ManageSessionAction.SET_VARIABLE:
            if not name or not is_assign(name):
                return _error(
                    "invalid-context-key",
                    f"'{name}' is not a valid Robot Framework variable name.",
                    retryable=False,
                    next_step="Use a valid variable name such as ${NAME}, @{LIST}, or &{MAP}.",
                    source="runtime-context",
                    details={"action": action_value, "name": name},
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
                    details={"action": action_value, "name": name},
                )
            summary = store.record_declared_variable(session_id, name, value) or record.to_summary()
            return {
                "ok": True,
                "session": summary.model_dump(mode="json"),
                "action": action_value,
                "name": name,
                "value": _json_safe(value),
            }

        if action == ManageSessionAction.GET_VARIABLE:
            if not name:
                return _error(
                    "missing-target",
                    "Action 'get_variable' requires the variable name in 'name'.",
                    retryable=False,
                    next_step="Provide a variable name such as ${X}.",
                    details={"action": action_value},
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
                    "action": action_value,
                    "name": name,
                    "value": _json_safe(record.declared_variables[name]),
                    "scope": "declared",
                }
            live = engine.get_variables([name])
            if name in live:
                return {
                    "ok": True,
                    "session": record.to_summary().model_dump(mode="json"),
                    "action": action_value,
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
                details={"action": action_value, "name": name},
            )

        if action in {ManageSessionAction.SET_SETUP, ManageSessionAction.SET_TEARDOWN}:
            kind = "setup" if action == ManageSessionAction.SET_SETUP else "teardown"
            requested_scope: SettingScope
            if scope is None:
                requested_scope = SettingScope.SUITE
            elif isinstance(scope, SettingScope):
                requested_scope = scope
            elif isinstance(scope, TagScope):
                # SettingScope and TagScope share suite/test_case; coerce when compatible.
                try:
                    requested_scope = SettingScope(scope.value)
                except ValueError:
                    return _error(
                        "invalid-scope",
                        f"scope '{scope.value}' is not supported for {action_value}.",
                        retryable=False,
                        next_step="Use one of: suite, test, test_case.",
                        details={"action": action_value, "scope": scope.value},
                    )
            else:
                return _error(
                    "invalid-scope",
                    f"scope '{scope}' is not supported for {action_value}.",
                    retryable=False,
                    next_step="Use one of: suite, test, test_case.",
                    details={"action": action_value, "scope": str(scope)},
                )
            text = (value or "").strip() if isinstance(value, str) else value
            if not isinstance(text, str) or not text:
                return _error(
                    "missing-target",
                    f"Action '{action_value}' requires the keyword-call string in 'value'.",
                    retryable=False,
                    next_step="Provide a keyword-call line such as 'Open Browser    chromium' in 'value'.",
                    details={"action": action_value},
                )
            summary = (
                store.set_session_setting(session_id, requested_scope.value, kind, text)
                or record.to_summary()
            )
            return {
                "ok": True,
                "session": summary.model_dump(mode="json"),
                "action": action_value,
                "scope": requested_scope.value,
                "value": text,
            }

        # action == ManageSessionAction.SET_TAGS
        tag_scope: TagScope
        if scope is None:
            tag_scope = TagScope.SUITE
        elif isinstance(scope, TagScope):
            tag_scope = scope
        elif isinstance(scope, SettingScope):
            try:
                tag_scope = TagScope(scope.value)
            except ValueError:
                return _error(
                    "invalid-scope",
                    f"scope '{scope.value}' is not supported for set_tags.",
                    retryable=False,
                    next_step="Use one of: suite, test_case.",
                    details={"action": action_value, "scope": scope.value},
                )
        else:
            return _error(
                "invalid-scope",
                f"scope '{scope}' is not supported for set_tags.",
                retryable=False,
                next_step="Use one of: suite, test_case.",
                details={"action": action_value, "scope": str(scope)},
            )
        if not tags or not all(isinstance(t, str) and t for t in tags):
            return _error(
                "missing-target",
                "Action 'set_tags' requires a non-empty list of tag strings in 'tags'.",
                retryable=False,
                next_step="Provide a list like ['smoke', 'cart'] in 'tags'.",
                details={"action": action_value, "tags": tags},
            )
        summary = store.set_session_tags(session_id, tag_scope.value, tags) or record.to_summary()
        return {
            "ok": True,
            "session": summary.model_dump(mode="json"),
            "action": action_value,
            "scope": tag_scope.value,
            "tags": list(tags),
        }

    return rf_manage_session
