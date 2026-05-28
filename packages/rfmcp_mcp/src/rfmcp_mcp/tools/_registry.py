from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from rfmcp_core.runtime.session import LiveSessionStore
from rfmcp_mcp.tools.app_inspect_state import build_app_inspect_state_tool
from rfmcp_mcp.tools.rf_close_session import build_close_session_tool
from rfmcp_mcp.tools.rf_get_context import build_get_context_tool
from rfmcp_mcp.tools.rf_execute_step import build_execute_step_tool
from rfmcp_mcp.tools.rf_get_session import build_get_session_tool
from rfmcp_mcp.tools.rf_manage_session import build_manage_session_tool
from rfmcp_mcp.tools.rf_open_session import build_open_session_tool
from rfmcp_mcp.tools.rf_set_context import build_set_context_tool

MAX_USER_FACING_TOOLS = 8


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    live_state_justification: str
    factory: Callable[[LiveSessionStore], Callable[..., dict]]


TOOL_DEFINITIONS: tuple[ToolDefinition, ...] = (
    ToolDefinition(
        name="rf_open_session",
        description="Open a bounded live Robot Framework session for stepwise work (repair, authoring, or exploration).",
        live_state_justification="Creates the live execution context that later steps rely on without recreating runtime state.",
        factory=build_open_session_tool,
    ),
    ToolDefinition(
        name="rf_get_session",
        description="Inspect the current status of a live session.",
        live_state_justification="Reads the current live context and session status without switching to stateless workflows.",
        factory=build_get_session_tool,
    ),
    ToolDefinition(
        name="rf_execute_step",
        description="Execute one bounded keyword step within the active live session.",
        live_state_justification="Runs a real keyword and updates live context across steps, which CLI workflows cannot preserve.",
        factory=build_execute_step_tool,
    ),
    ToolDefinition(
        name="rf_close_session",
        description="Close a bounded live session explicitly.",
        live_state_justification="Ends the active live context deliberately so operators do not leave privileged state hanging.",
        factory=build_close_session_tool,
    ),
    ToolDefinition(
        name="rf_get_context",
        description="Read bounded Robot Framework runtime context for the active live session.",
        live_state_justification="Exposes live runtime variables and libraries that only exist inside the active session.",
        factory=build_get_context_tool,
    ),
    ToolDefinition(
        name="rf_set_context",
        description="Mutate bounded Robot Framework runtime context for the active live session.",
        live_state_justification="Updates live runtime variables inside the current session without restarting the context.",
        factory=build_set_context_tool,
    ),
    ToolDefinition(
        name="app_inspect_state",
        description="Capture an approved inspection snapshot from the active live session.",
        live_state_justification="Reads approved live application state such as DOM, accessibility, screenshots, or last API response from the current session.",
        factory=build_app_inspect_state_tool,
    ),
    ToolDefinition(
        name="rf_manage_session",
        description="Manage the live session declaratively: import library/resource/variables, set/get *** Variables ***, and set Suite/Test setup/teardown and Test Tags.",
        live_state_justification="Mutates the live namespace (imports) and records suite-level declarations (Variables/Settings) that are inherent to the active session, which CLI workflows cannot persist across steps.",
        factory=build_manage_session_tool,
    ),
)

ALLOWLISTED_TOOL_NAMES = tuple(definition.name for definition in TOOL_DEFINITIONS)

if len(ALLOWLISTED_TOOL_NAMES) > MAX_USER_FACING_TOOLS:
    raise RuntimeError("MCP tool boundary exceeded the allowed v1 surface.")
