from __future__ import annotations

from fastmcp import FastMCP

from rfmcp_core.runtime.session import LiveRepairSessionStore
from rfmcp_mcp.tools._registry import TOOL_DEFINITIONS

SERVER_INSTRUCTIONS = (
    "Expose only live-state repair-session tools. "
    "Do not treat MCP as a surface for stateless generation, grounding, scaffolding, or validation helpers."
)


def build_server(store: LiveRepairSessionStore | None = None) -> FastMCP:
    session_store = store or LiveRepairSessionStore()
    server = FastMCP("rfmcp-reloaded", instructions=SERVER_INSTRUCTIONS)
    for definition in TOOL_DEFINITIONS:
        server.tool(name=definition.name, description=definition.description)(definition.factory(session_store))
    return server


def main() -> None:
    build_server().run()
