from __future__ import annotations

from fastmcp import FastMCP

from rfmcp_core.runtime.session import LiveSessionStore
from rfmcp_mcp.server import build_server


def create_stdio_server(store: LiveSessionStore | None = None) -> FastMCP:
    return build_server(store)


def main() -> None:
    create_stdio_server().run()
