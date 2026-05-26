from __future__ import annotations

import asyncio
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
for path in [
    REPO_ROOT / "packages" / "rfmcp_core" / "src",
    REPO_ROOT / "packages" / "rfmcp_mcp" / "src",
]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rfmcp_core.runtime.session import LiveRepairSessionStore  # noqa: E402
from rfmcp_core.runtime.stepper import LiveRepairStepper  # noqa: E402
from rfmcp_core.models.payloads import SnapshotKind  # noqa: E402
from rfmcp_mcp.security.attach_policy import PolicyGateError, validate_transport_policy  # noqa: E402
from rfmcp_mcp.server import build_server  # noqa: E402
from rfmcp_mcp.tools._registry import ALLOWLISTED_TOOL_NAMES, MAX_USER_FACING_TOOLS  # noqa: E402
from rfmcp_mcp.tools.app_inspect_state import build_app_inspect_state_tool  # noqa: E402
from rfmcp_mcp.tools.rf_close_session import build_close_session_tool  # noqa: E402
from rfmcp_mcp.tools.rf_get_context import build_get_context_tool  # noqa: E402
from rfmcp_mcp.tools.rf_execute_step import build_execute_step_tool  # noqa: E402
from rfmcp_mcp.tools.rf_get_session import build_get_session_tool  # noqa: E402
from rfmcp_mcp.tools.rf_open_session import build_open_session_tool  # noqa: E402
from rfmcp_mcp.tools.rf_set_context import build_set_context_tool  # noqa: E402
from rfmcp_mcp.transports.http import create_http_server  # noqa: E402


class McpLiveRepairSurfaceTests(unittest.TestCase):
    def test_allowlisted_surface_stays_small_and_repair_only(self) -> None:
        self.assertLessEqual(len(ALLOWLISTED_TOOL_NAMES), MAX_USER_FACING_TOOLS)
        self.assertEqual(
            ALLOWLISTED_TOOL_NAMES,
            (
                "rf_open_repair_session",
                "rf_get_repair_session",
                "rf_execute_repair_step",
                "rf_close_repair_session",
                "rf_get_context",
                "rf_set_context",
                "app_inspect_state",
            ),
        )
        combined = " ".join(ALLOWLISTED_TOOL_NAMES)
        self.assertNotIn("validate", combined)
        self.assertNotIn("generate", combined)

    def test_http_transport_is_loopback_only(self) -> None:
        self.assertIsNone(validate_transport_policy("http", host="127.0.0.1"))
        self.assertIsNone(validate_transport_policy("http", host="localhost"))
        error = validate_transport_policy("http", host="0.0.0.0")
        self.assertIsNotNone(error)
        self.assertEqual(error.code, "policy-http-loopback-only")
        missing_host = validate_transport_policy("http", host=None)
        self.assertIsNotNone(missing_host)
        self.assertEqual(missing_host.code, "policy-http-loopback-only")

    def test_http_transport_policy_denial_is_covered(self) -> None:
        with patch("rfmcp_mcp.security.attach_policy.capability_allowed", return_value=False):
            error = validate_transport_policy("http", host="127.0.0.1")
        self.assertIsNotNone(error)
        self.assertEqual(error.code, "policy-http-disabled")
        self.assertFalse(error.retryable)

    def test_policy_load_failure_uses_structured_error(self) -> None:
        with patch("rfmcp_mcp.security.attach_policy.load_local_policy_defaults", side_effect=FileNotFoundError()):
            error = validate_transport_policy("http", host="127.0.0.1")
        self.assertIsNotNone(error)
        self.assertEqual(error.code, "policy-load-failed")
        self.assertFalse(error.retryable)

    def test_unsupported_transport_uses_structured_error(self) -> None:
        error = validate_transport_policy("tcp")
        self.assertIsNotNone(error)
        self.assertEqual(error.code, "unsupported-transport")
        self.assertFalse(error.retryable)

    def test_attach_request_is_rejected_by_default(self) -> None:
        error = validate_transport_policy("stdio", attach_requested=True)
        self.assertIsNotNone(error)
        self.assertEqual(error.code, "policy-attach-disabled")
        self.assertFalse(error.retryable)

    def test_live_session_tools_use_structured_error_path(self) -> None:
        store = LiveRepairSessionStore()
        stepper = LiveRepairStepper(store)
        open_session = build_open_session_tool(store)
        get_session = build_get_session_tool(store)
        execute_step = build_execute_step_tool(store)
        close_session = build_close_session_tool(store)

        opened = open_session("stdio")
        self.assertTrue(opened["ok"])
        session_id = opened["session"]["session_id"]

        unsupported = open_session("tcp")
        self.assertFalse(unsupported["ok"])
        self.assertEqual(unsupported["error"]["code"], "unsupported-transport")

        session_status = get_session(session_id)
        self.assertTrue(session_status["ok"])
        self.assertEqual(session_status["session"]["status"], "open")

        stepped = execute_step(session_id, "Inspect current failure context")
        self.assertTrue(stepped["ok"])
        self.assertEqual(stepped["session"]["step_count"], 1)

        def raise_interrupt(_session_id: str, _instruction: str) -> None:
            raise InterruptedError()

        interrupted_stepper = LiveRepairStepper(store, step_executor=raise_interrupt)
        interrupted_execute = build_execute_step_tool(store, stepper=interrupted_stepper)
        interrupted = interrupted_execute(session_id, "Retry failing step")
        self.assertFalse(interrupted["ok"])
        self.assertEqual(interrupted["error"]["code"], "repair-step-interrupted")
        self.assertEqual(interrupted["session"]["status"], "interrupted")

        closed = close_session(session_id)
        self.assertTrue(closed["ok"])
        restarted = open_session("stdio")
        self.assertTrue(restarted["ok"])
        restarted_id = restarted["session"]["session_id"]
        closed = close_session(restarted_id)
        self.assertEqual(closed["session"]["status"], "closed")

        after_close = execute_step(restarted_id, "Attempt after close")
        self.assertFalse(after_close["ok"])
        self.assertEqual(after_close["error"]["code"], "session-not-open")

        missing = get_session("missing-session")
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["error"]["code"], "session-not-found")

    def test_context_tools_support_read_and_write(self) -> None:
        store = LiveRepairSessionStore()
        open_session = build_open_session_tool(store)
        close_session = build_close_session_tool(store)
        get_context = build_get_context_tool(store)
        set_context = build_set_context_tool(store)

        opened = open_session("stdio")
        session_id = opened["session"]["session_id"]

        baseline = get_context(session_id)
        self.assertTrue(baseline["ok"])
        self.assertIn("${CURRENT_TEST}", baseline["context"]["variables"])

        updated = set_context(session_id, "${BROWSER}", {"name": "chromium", "headless": True})
        self.assertTrue(updated["ok"])
        self.assertEqual(updated["context"]["key"], "${BROWSER}")
        self.assertEqual(updated["context"]["value"], {"name": "chromium", "headless": True})

        narrowed = get_context(session_id, ["${BROWSER}"])
        self.assertTrue(narrowed["ok"])
        self.assertEqual(narrowed["context"]["variables"], {"${BROWSER}": {"name": "chromium", "headless": True}})

        missing = get_context("missing-session")
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["error"]["code"], "session-not-found")
        self.assertEqual(missing["error"]["provenance"]["source"], "repair-session-store")
        self.assertIn("context reads", missing["error"]["suggested_next_step"])

        close_session(session_id)
        blocked_write = set_context(session_id, "${AFTER_CLOSE}", True)
        self.assertFalse(blocked_write["ok"])
        self.assertEqual(blocked_write["error"]["code"], "session-not-open")
        self.assertEqual(blocked_write["error"]["provenance"]["source"], "repair-session-store")
        self.assertIn("context mutation", blocked_write["error"]["suggested_next_step"])

        closed = get_context(session_id)
        self.assertFalse(closed["ok"])
        self.assertEqual(closed["error"]["code"], "session-not-open")
        self.assertEqual(closed["error"]["provenance"]["source"], "repair-session-store")
        self.assertIn("context reads", closed["error"]["suggested_next_step"])

    def test_context_mutation_rejects_invalid_keys_without_mutating_session_state(self) -> None:
        store = LiveRepairSessionStore()
        open_session = build_open_session_tool(store)
        get_context = build_get_context_tool(store)
        set_context = build_set_context_tool(store)

        opened = open_session("stdio")
        session_id = opened["session"]["session_id"]

        invalid = set_context(session_id, "", "bad-value")
        self.assertFalse(invalid["ok"])
        self.assertEqual(invalid["error"]["code"], "invalid-context-key")
        self.assertEqual(invalid["error"]["provenance"]["source"], "runtime-context")
        self.assertIn("non-empty Robot Framework variable name", invalid["error"]["suggested_next_step"])

        context = get_context(session_id)
        self.assertTrue(context["ok"])
        self.assertNotIn("", context["context"]["variables"])

    def test_interrupted_sessions_still_allow_context_reads(self) -> None:
        store = LiveRepairSessionStore()
        open_session = build_open_session_tool(store)
        get_context = build_get_context_tool(store)
        set_context = build_set_context_tool(store)
        inspect_state = build_app_inspect_state_tool(store)

        def raise_interrupt(_session_id: str, _instruction: str) -> None:
            raise InterruptedError()

        interrupted_stepper = LiveRepairStepper(store, step_executor=raise_interrupt)
        execute_step = build_execute_step_tool(store, stepper=interrupted_stepper)

        opened = open_session("stdio")
        session_id = opened["session"]["session_id"]

        interrupted = execute_step(session_id, "Pause after failure")
        self.assertFalse(interrupted["ok"])
        self.assertEqual(interrupted["session"]["status"], "interrupted")

        context = get_context(session_id)
        self.assertTrue(context["ok"])
        self.assertIn("${CURRENT_TEST}", context["context"]["variables"])

        blocked_write = set_context(session_id, "${AFTER_INTERRUPT}", True)
        self.assertFalse(blocked_write["ok"])
        self.assertEqual(blocked_write["error"]["code"], "session-not-open")
        self.assertEqual(blocked_write["error"]["provenance"]["source"], "repair-session-store")

        snapshot = inspect_state(session_id, "dom")
        self.assertTrue(snapshot["ok"])
        self.assertEqual(snapshot["snapshot"]["payload"]["step_count"], 0)
        self.assertTrue(snapshot["snapshot"]["payload"]["synthetic"])

    def test_context_write_policy_and_session_denials_are_structured(self) -> None:
        store = LiveRepairSessionStore()
        open_session = build_open_session_tool(store)
        set_context = build_set_context_tool(store)
        opened = open_session("stdio")
        session_id = opened["session"]["session_id"]

        with patch("rfmcp_core.runtime.context.capability_allowed", return_value=False):
            denied = set_context(session_id, "${MODE}", "readonly")
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["error"]["code"], "policy-context-write-disabled")
        self.assertEqual(denied["error"]["provenance"]["kind"], "observed")
        self.assertEqual(denied["error"]["provenance"]["source"], "local-policy")
        self.assertIn("local policy", denied["error"]["suggested_next_step"])

        store.configure_capabilities(session_id, allow_context_write=False)
        denied_by_session = set_context(session_id, "${MODE}", "readonly")
        self.assertFalse(denied_by_session["ok"])
        self.assertEqual(denied_by_session["error"]["code"], "session-context-write-disabled")
        self.assertEqual(denied_by_session["error"]["provenance"]["kind"], "observed")
        self.assertEqual(denied_by_session["error"]["provenance"]["source"], "repair-session-store")
        self.assertIn("context reads only", denied_by_session["error"]["suggested_next_step"])

    def test_approved_inspection_snapshots_and_denials_are_structured(self) -> None:
        store = LiveRepairSessionStore()
        open_session = build_open_session_tool(store)
        inspect_state = build_app_inspect_state_tool(store)
        opened = open_session("stdio")
        session_id = opened["session"]["session_id"]

        expected_payloads = {
            "dom": {
                "synthetic": True,
                "source": "repair-session-fixture",
                "session_id": session_id,
                "step_count": 0,
                "snapshot_kind": "dom",
                "data": {"html": "<body data-rfmcp='repair-session'></body>", "selector": "body"},
            },
            "accessibility": {
                "synthetic": True,
                "source": "repair-session-fixture",
                "session_id": session_id,
                "step_count": 0,
                "snapshot_kind": "accessibility",
                "data": {"role": "document", "name": "Repair Session"},
            },
            "screenshot": {
                "synthetic": True,
                "source": "repair-session-fixture",
                "session_id": session_id,
                "step_count": 0,
                "snapshot_kind": "screenshot",
                "data": {"media_type": "image/png", "data_url": "data:image/png;base64,cmZtY3Atc25hcHNob3Q="},
            },
            "last_api_response": {
                "synthetic": True,
                "source": "repair-session-fixture",
                "session_id": session_id,
                "step_count": 0,
                "snapshot_kind": "last_api_response",
                "data": {"status": 200, "body": {"ok": True, "source": "repair-session"}},
            },
            "app_context": {
                "synthetic": True,
                "source": "repair-session-fixture",
                "session_id": session_id,
                "step_count": 0,
                "snapshot_kind": "app_context",
                "data": {"current_view": "repair-session", "libraries": ["BuiltIn", "Collections"]},
            },
        }
        for snapshot_kind, expected_payload in expected_payloads.items():
            response = inspect_state(session_id, snapshot_kind)
            self.assertTrue(response["ok"])
            self.assertEqual(response["snapshot"]["snapshot_kind"], snapshot_kind)
            self.assertEqual(response["snapshot"]["payload"], expected_payload)

        unsupported = inspect_state(session_id, "video")
        self.assertFalse(unsupported["ok"])
        self.assertEqual(unsupported["error"]["code"], "unsupported-snapshot-kind")
        self.assertEqual(unsupported["error"]["provenance"]["source"], "inspection-surface")
        self.assertIn("approved snapshot kinds", unsupported["error"]["suggested_next_step"])

        missing = inspect_state("missing-session", "dom")
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["error"]["code"], "session-not-found")
        self.assertEqual(missing["error"]["provenance"]["source"], "repair-session-store")
        self.assertIn("inspection snapshot", missing["error"]["suggested_next_step"])

        store.configure_capabilities(session_id, allowed_snapshot_kinds=(SnapshotKind.DOM,))
        denied_by_session = inspect_state(session_id, "screenshot")
        self.assertFalse(denied_by_session["ok"])
        self.assertEqual(denied_by_session["error"]["code"], "session-snapshot-disabled")
        self.assertEqual(denied_by_session["error"]["provenance"]["kind"], "observed")
        self.assertEqual(denied_by_session["error"]["provenance"]["source"], "repair-session-store")
        self.assertIn("allowed snapshot kind", denied_by_session["error"]["suggested_next_step"])

        with patch("rfmcp_core.runtime.snapshot.capability_allowed", return_value=False):
            denied_by_policy = inspect_state(session_id, "dom")
        self.assertFalse(denied_by_policy["ok"])
        self.assertEqual(denied_by_policy["error"]["code"], "policy-inspection-disabled")
        self.assertEqual(denied_by_policy["error"]["provenance"]["kind"], "observed")
        self.assertEqual(denied_by_policy["error"]["provenance"]["source"], "local-policy")
        self.assertIn("local policy", denied_by_policy["error"]["suggested_next_step"])

        close_session = build_close_session_tool(store)
        close_session(session_id)
        closed = inspect_state(session_id, "dom")
        self.assertFalse(closed["ok"])
        self.assertEqual(closed["error"]["code"], "session-not-open")
        self.assertEqual(closed["error"]["provenance"]["source"], "repair-session-store")
        self.assertIn("inspection snapshots", closed["error"]["suggested_next_step"])

    def test_new_tools_map_policy_load_failures_to_structured_errors(self) -> None:
        store = LiveRepairSessionStore()
        open_session = build_open_session_tool(store)
        set_context = build_set_context_tool(store)
        inspect_state = build_app_inspect_state_tool(store)
        opened = open_session("stdio")
        session_id = opened["session"]["session_id"]

        with patch("rfmcp_core.runtime.context.load_local_policy_defaults", side_effect=FileNotFoundError()):
            context_error = set_context(session_id, "${MODE}", "readonly")
        self.assertFalse(context_error["ok"])
        self.assertEqual(context_error["error"]["code"], "policy-load-failed")
        self.assertEqual(context_error["error"]["provenance"]["source"], "local-policy")

        with patch("rfmcp_core.runtime.snapshot.load_local_policy_defaults", side_effect=FileNotFoundError()):
            snapshot_error = inspect_state(session_id, "dom")
        self.assertFalse(snapshot_error["ok"])
        self.assertEqual(snapshot_error["error"]["code"], "policy-load-failed")
        self.assertEqual(snapshot_error["error"]["provenance"]["source"], "local-policy")

    def test_new_tools_trap_unexpected_exceptions_with_shared_error_envelope(self) -> None:
        store = LiveRepairSessionStore()
        get_context = build_get_context_tool(store)
        set_context = build_set_context_tool(store)
        inspect_state = build_app_inspect_state_tool(store)

        with patch("rfmcp_mcp.tools.rf_get_context.get_runtime_context", side_effect=RuntimeError("boom")):
            get_error = get_context("session-1")
        self.assertFalse(get_error["ok"])
        self.assertEqual(get_error["error"]["code"], "tool-execution-failed")
        self.assertEqual(get_error["error"]["provenance"]["source"], "rf_get_context")

        with patch("rfmcp_mcp.tools.rf_set_context.set_runtime_context", side_effect=RuntimeError("boom")):
            set_error = set_context("session-1", "${MODE}", "readonly")
        self.assertFalse(set_error["ok"])
        self.assertEqual(set_error["error"]["code"], "tool-execution-failed")
        self.assertEqual(set_error["error"]["provenance"]["source"], "rf_set_context")

        with patch("rfmcp_mcp.tools.app_inspect_state.capture_inspection_snapshot", side_effect=RuntimeError("boom")):
            snapshot_error = inspect_state("session-1", "dom")
        self.assertFalse(snapshot_error["ok"])
        self.assertEqual(snapshot_error["error"]["code"], "tool-execution-failed")
        self.assertEqual(snapshot_error["error"]["provenance"]["source"], "app_inspect_state")

    def test_build_server_registers_only_allowlisted_tools(self) -> None:
        server = build_server(LiveRepairSessionStore())
        self.assertEqual(server.name, "rfmcp-reloaded")
        tools = asyncio.run(server.list_tools())
        self.assertEqual({tool.name for tool in tools}, set(ALLOWLISTED_TOOL_NAMES))
        rf_set_context = next(tool for tool in tools if tool.name == "rf_set_context")
        self.assertEqual(rf_set_context.parameters["properties"]["value"], {})

    def test_http_server_rejects_non_loopback_bind(self) -> None:
        with self.assertRaises(PolicyGateError):
            create_http_server("0.0.0.0")

    def test_http_main_emits_structured_policy_error(self) -> None:
        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            with self.assertRaises(SystemExit) as exc:
                from rfmcp_mcp.transports.http import main

                main(host="0.0.0.0")
        self.assertEqual(exc.exception.code, 1)
        self.assertIn("policy-http-loopback-only", stderr.getvalue())
