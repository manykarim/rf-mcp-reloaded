from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from rfmcp_core.runtime.session import LiveSessionStore
from rfmcp_mcp.tools.app_inspect_state import build_app_inspect_state_tool
from rfmcp_mcp.tools.rf_context import build_context_tool
from rfmcp_mcp.tools.rf_execute_step import build_execute_step_tool
from rfmcp_mcp.tools.rf_export_suite import build_export_suite_tool
from rfmcp_mcp.tools.rf_manage_session import build_manage_session_tool
from rfmcp_mcp.tools.rf_session import build_session_tool

MAX_USER_FACING_TOOLS = 6


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    live_state_justification: str
    factory: Callable[[LiveSessionStore], Callable[..., dict]]


TOOL_DEFINITIONS: tuple[ToolDefinition, ...] = (
    ToolDefinition(
        name="rf_session",
        description=(
            "Manage the lifecycle of a bounded live Robot Framework session "
            "(action=open|get|close). Returns a SessionSummary."
        ),
        live_state_justification=(
            "Creates, inspects, and disposes the live execution context that every other tool reuses."
        ),
        factory=build_session_tool,
    ),
    ToolDefinition(
        name="rf_execute_step",
        description=(
            "Execute one bounded Robot Framework keyword step within the active live session, "
            "preserving variables, imports, and library state between calls."
        ),
        live_state_justification=(
            "Runs a real keyword and updates live context across steps, which CLI workflows cannot preserve."
        ),
        factory=build_execute_step_tool,
    ),
    ToolDefinition(
        name="rf_context",
        description=(
            "Read or write runtime variables and library state inside the active live session "
            "(action=get|set). For declarative *** Variables *** entries, use rf_manage_session."
        ),
        live_state_justification=(
            "Exposes and mutates live runtime variables that only exist inside the active session."
        ),
        factory=build_context_tool,
    ),
    ToolDefinition(
        name="rf_manage_session",
        description=(
            "Manage the live session declaratively (action=import_library|import_resource|import_variables"
            "|set_variable|get_variable|set_setup|set_teardown|set_tags). Routes imports through the stepper "
            "and records Variables/Settings/Tags destined for the final suite."
        ),
        live_state_justification=(
            "Mutates the live namespace (imports) and records suite-level declarations that are inherent "
            "to the active session, which CLI workflows cannot persist across steps."
        ),
        factory=build_manage_session_tool,
    ),
    ToolDefinition(
        name="rf_export_suite",
        description=(
            "Render the session's recorded steps + declarative manifest into a canonical RF7 "
            ".robot suite. File-first by default (manifest with path/bytes/sha256); pass "
            "return_inline=True for an inline preview."
        ),
        live_state_justification=(
            "Reads the per-session manifest (steps + declared variables/setups/teardowns/tags) "
            "that only exists inside the active live session."
        ),
        factory=build_export_suite_tool,
    ),
    ToolDefinition(
        name="app_inspect_state",
        description=(
            "Capture an approved inspection snapshot (snapshot_kind=app_context|dom|dom_selector|aria|"
            "screenshot|console_log|network_log) from the loaded libraries of the active live session. "
            "Snapshots are persisted to disk; the response carries a small manifest (path/bytes/sha256/"
            "format/summary). Pass return_inline=True to include the payload in-band (capped per kind)."
        ),
        live_state_justification=(
            "Reads approved live application state from the loaded libraries of the current session."
        ),
        factory=build_app_inspect_state_tool,
    ),
)

ALLOWLISTED_TOOL_NAMES = tuple(definition.name for definition in TOOL_DEFINITIONS)

if len(ALLOWLISTED_TOOL_NAMES) > MAX_USER_FACING_TOOLS:
    raise RuntimeError("MCP tool boundary exceeded the allowed v1 surface.")
