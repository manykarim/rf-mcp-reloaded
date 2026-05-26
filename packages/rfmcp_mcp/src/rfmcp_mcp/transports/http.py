from __future__ import annotations

import json
import sys

from fastmcp import FastMCP

from rfmcp_core.runtime.session import LiveRepairSessionStore
from rfmcp_mcp.security.attach_policy import PolicyGateError, validate_transport_policy
from rfmcp_mcp.server import build_server

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080


def create_http_server(
    host: str = DEFAULT_HOST,
    *,
    store: LiveRepairSessionStore | None = None,
) -> FastMCP:
    error = validate_transport_policy("http", host=host)
    if error is not None:
        raise PolicyGateError(error)
    return build_server(store)


def main(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    try:
        server = create_http_server(host)
    except PolicyGateError as exc:
        print(json.dumps(exc.error.model_dump(mode="json"), indent=2), file=sys.stderr)
        raise SystemExit(1) from exc
    server.run(transport="http", host=host, port=port)
