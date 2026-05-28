"""Opt-in attach bridge: route a live session to an external Robot Framework process.

`AttachExecutionContext` implements the same duck-typed surface the stepper, context,
and snapshot modules already call on the in-process engine (``execute``,
``get_variables``, ``set_variable``, ``imported_libraries``, ``query``, ``close``), so
no changes are needed there. It talks to a loopback-only bridge the operator runs on
their own Robot Framework process. Attach is disabled by default and gated by local
policy at session-open time (see ``rfmcp_mcp.security.attach_policy``).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from rfmcp_core.runtime.execution import StepExecution, _json_safe, _parse_instruction

DEFAULT_ATTACH_HOST = "127.0.0.1"
DEFAULT_ATTACH_PORT = 7317
_NETWORK_ERRORS = (urllib.error.URLError, OSError, ValueError)


class AttachExecutionContext:
    """Engine variant that proxies keyword/context/inspection ops to an external RF process."""

    def __init__(
        self,
        session_id: str,
        host: str | None = DEFAULT_ATTACH_HOST,
        port: int | None = DEFAULT_ATTACH_PORT,
        token: str = "",
        timeout: float = 5.0,
    ) -> None:
        self._session_id = session_id
        self._host = host or DEFAULT_ATTACH_HOST
        self._port = port or DEFAULT_ATTACH_PORT
        self._token = token
        self._timeout = timeout
        self._closed = False

    @property
    def started(self) -> bool:
        return not self._closed

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        # Bracket IPv6 literals (e.g. ::1) so the URL is RFC 3986-valid.
        host_part = f"[{self._host}]" if ":" in self._host else self._host
        url = f"http://{host_part}:{self._port}/{path.lstrip('/')}"
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, method="POST")
        request.add_header("Content-Type", "application/json")
        if self._token:
            request.add_header("Authorization", f"Bearer {self._token}")
        with urllib.request.urlopen(request, timeout=self._timeout) as response:  # noqa: S310 (loopback only)
            body = response.read().decode("utf-8")
        return json.loads(body) if body else {}

    def execute(self, instruction: str) -> StepExecution:
        assign_to, keyword, args = _parse_instruction(instruction)
        if not keyword:
            return StepExecution(
                ok=False,
                keyword="",
                error_message="No keyword was provided to execute.",
                error_type="EmptyInstruction",
            )
        try:
            response = self._post(
                "run_keyword",
                {"keyword": keyword, "args": args, "assign_to": assign_to},
            )
        except _NETWORK_ERRORS as exc:
            return StepExecution(
                ok=False,
                keyword=keyword,
                error_message=f"Attach bridge at {self._host}:{self._port} is unreachable: {exc}",
                error_type="AttachUnavailable",
            )
        if not response.get("ok", False):
            return StepExecution(
                ok=False,
                keyword=keyword,
                error_message=response.get("error") or "The attached keyword failed.",
                error_type=response.get("error_type") or "AttachKeywordFailed",
            )
        return StepExecution(
            ok=True,
            keyword=keyword,
            return_value=response.get("return_value"),
            assigned=assign_to,
        )

    def get_variables(self, keys: list[str] | None = None) -> dict[str, Any]:
        try:
            response = self._post("get_variables", {"keys": list(keys or [])})
        except _NETWORK_ERRORS:
            return {}
        variables = response.get("variables", {}) or {}
        return {name: _json_safe(value) for name, value in variables.items()}

    def set_variable(self, name: str, value: Any) -> None:
        try:
            self._post("set_variable", {"name": name, "value": value})
        except _NETWORK_ERRORS as exc:
            raise RuntimeError(
                f"Attach bridge at {self._host}:{self._port} is unreachable: {exc}"
            ) from exc

    def imported_libraries(self) -> list[str]:
        try:
            response = self._post("get_libraries", {})
        except _NETWORK_ERRORS:
            return []
        return list(response.get("libraries", []) or [])

    def query(self, keyword: str, args: list[str] | None = None) -> Any:
        try:
            response = self._post("run_keyword", {"keyword": keyword, "args": list(args or [])})
        except _NETWORK_ERRORS as exc:
            raise RuntimeError(
                f"Attach bridge at {self._host}:{self._port} is unreachable: {exc}"
            ) from exc
        if not response.get("ok", False):
            raise RuntimeError(response.get("error") or "The attached keyword failed.")
        return response.get("return_value")

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._post("close", {})
        except Exception:
            pass
