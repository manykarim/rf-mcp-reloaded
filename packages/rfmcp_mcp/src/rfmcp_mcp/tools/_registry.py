from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from rfmcp_core.runtime.session import LiveRepairSessionStore
from rfmcp_mcp.tools.app_inspect_state import build_app_inspect_state_tool
from rfmcp_mcp.tools.rf_close_session import build_close_session_tool
from rfmcp_mcp.tools.rf_get_context import build_get_context_tool
from rfmcp_mcp.tools.rf_execute_step import build_execute_step_tool
from rfmcp_mcp.tools.rf_get_session import build_get_session_tool
from rfmcp_mcp.tools.rf_open_session import build_open_session_tool
from rfmcp_mcp.tools.rf_set_context import build_set_context_tool

MAX_USER_FACING_TOOLS = 7


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    live_state_justification: str
    factory: Callable[[LiveRepairSessionStore], Callable[..., dict]]


TOOL_DEFINITIONS: tuple[ToolDefinition, ...] = (
    ToolDefinition(
        name="rf_open_repair_session",
        description="Open a bounded live repair session for stepwise investigation.",
        live_state_justification="Creates the live repair context that later steps rely on without recreating runtime state.",
        factory=build_open_session_tool,
    ),
    ToolDefinition(
        name="rf_get_repair_session",
        description="Inspect the current status of a live repair session.",
        live_state_justification="Reads the current live repair context and session status without switching to stateless workflows.",
        factory=build_get_session_tool,
    ),
    ToolDefinition(
        name="rf_execute_repair_step",
        description="Execute one bounded repair step within the active live repair session.",
        live_state_justification="Consumes and updates live repair context across steps, which CLI workflows cannot preserve.",
        factory=build_execute_step_tool,
    ),
    ToolDefinition(
        name="rf_close_repair_session",
        description="Close a bounded live repair session explicitly.",
        live_state_justification="Ends the active live repair context deliberately so operators do not leave privileged state hanging.",
        factory=build_close_session_tool,
    ),
    ToolDefinition(
        name="rf_get_context",
        description="Read bounded Robot Framework runtime context for the active repair session.",
        live_state_justification="Exposes live runtime variables and libraries that only exist inside the active repair session.",
        factory=build_get_context_tool,
    ),
    ToolDefinition(
        name="rf_set_context",
        description="Mutate bounded Robot Framework runtime context for the active repair session.",
        live_state_justification="Updates live runtime variables inside the current repair session without restarting the context.",
        factory=build_set_context_tool,
    ),
    ToolDefinition(
        name="app_inspect_state",
        description="Capture an approved inspection snapshot from the active repair session.",
        live_state_justification="Reads approved live application state such as DOM, accessibility, screenshots, or last API response from the current repair session.",
        factory=build_app_inspect_state_tool,
    ),
)

ALLOWLISTED_TOOL_NAMES = tuple(definition.name for definition in TOOL_DEFINITIONS)

if len(ALLOWLISTED_TOOL_NAMES) > MAX_USER_FACING_TOOLS:
    raise RuntimeError("MCP tool boundary exceeded the allowed v1 surface.")
