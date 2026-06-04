"""Start the rfmcp MCP server over stdio (default) or loopback HTTP."""

from __future__ import annotations

from typing import Annotated

import typer

DEFAULT_HTTP_HOST = "127.0.0.1"
# Mirror the rfmcp_mcp.transports.http default so 'rfmcp serve --transport http'
# binds to the same port a direct invocation would.
DEFAULT_HTTP_PORT = 8080


def serve_command(
    transport: Annotated[
        str,
        typer.Option(
            "--transport",
            "-t",
            help="Transport for the MCP server: 'stdio' (default, for local agents) or 'http' (loopback only).",
        ),
    ] = "stdio",
    host: Annotated[
        str,
        typer.Option(
            "--host",
            help="HTTP transport bind host. Loopback only (enforced by policy). Ignored for stdio.",
        ),
    ] = DEFAULT_HTTP_HOST,
    port: Annotated[
        int,
        typer.Option(
            "--port",
            help="HTTP transport bind port. Ignored for stdio.",
        ),
    ] = DEFAULT_HTTP_PORT,
) -> None:
    """Start the rfmcp MCP server. Defaults to stdio for local agent integrations.

    Examples:

      rfmcp serve                              # stdio transport (Claude Code / Cursor / Kilo)
      rfmcp serve --transport http             # loopback HTTP on 127.0.0.1:8765
      rfmcp serve --transport http --port 9000 # custom port
    """

    if transport == "stdio":
        from rfmcp_mcp.transports.stdio import main as stdio_main

        stdio_main()
        return

    if transport == "http":
        from rfmcp_mcp.transports.http import main as http_main

        http_main(host=host, port=port)
        return

    typer.echo(
        f"Unsupported transport '{transport}'. Use 'stdio' or 'http'.",
        err=True,
    )
    raise typer.Exit(code=2)
