from __future__ import annotations

import asyncio
import io
import os
import sys
import tempfile
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

from rfmcp_core.models.payloads import (  # noqa: E402
    ContextAction,
    SessionAction,
    SnapshotKind,
    TransportKind,
)
from rfmcp_core.runtime.session import LiveSessionStore  # noqa: E402
from rfmcp_core.runtime.stepper import LiveStepper  # noqa: E402
from rfmcp_mcp.security.attach_policy import PolicyGateError, validate_transport_policy  # noqa: E402
from rfmcp_mcp.server import build_server  # noqa: E402
from rfmcp_mcp.tools._registry import ALLOWLISTED_TOOL_NAMES, MAX_USER_FACING_TOOLS  # noqa: E402
from rfmcp_mcp.tools.app_inspect_state import build_app_inspect_state_tool  # noqa: E402
from rfmcp_mcp.tools.rf_context import build_context_tool  # noqa: E402
from rfmcp_mcp.tools.rf_execute_step import build_execute_step_tool  # noqa: E402
from rfmcp_mcp.tools.rf_session import build_session_tool  # noqa: E402
from rfmcp_mcp.transports.http import create_http_server  # noqa: E402


class _InterruptEngine:
    """Test double: a live engine whose step execution is interrupted."""

    def execute(self, instruction: str):  # noqa: ANN001
        raise InterruptedError()

    def get_variables(self, keys=None):  # noqa: ANN001
        data = {"${CURRENT_TEST}": "Interrupted Session"}
        if keys:
            return {key: data[key] for key in keys if key in data}
        return data

    def set_variable(self, name, value) -> None:  # noqa: ANN001
        pass

    def imported_libraries(self) -> list[str]:
        return ["BuiltIn"]

    def close(self) -> None:
        pass


def _open(session_tool, **kwargs):
    return session_tool(action=SessionAction.OPEN, transport=TransportKind.STDIO, **kwargs)


def _get(session_tool, session_id: str):
    return session_tool(action=SessionAction.GET, session_id=session_id)


def _close(session_tool, session_id: str):
    return session_tool(action=SessionAction.CLOSE, session_id=session_id)


def _ctx_get(context_tool, session_id: str, keys: list[str] | None = None):
    return context_tool(session_id=session_id, action=ContextAction.GET, keys=keys)


def _ctx_set(context_tool, session_id: str, key: str, value):
    return context_tool(session_id=session_id, action=ContextAction.SET, key=key, value=value)


class McpLiveSessionSurfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        # Snapshot capture writes to disk; route it to a fresh tempdir per test.
        self._snapshots_tmp = tempfile.TemporaryDirectory()
        self._prev_snapshots_dir = os.environ.get("RFMCP_SNAPSHOTS_DIR")
        os.environ["RFMCP_SNAPSHOTS_DIR"] = self._snapshots_tmp.name

    def tearDown(self) -> None:
        if self._prev_snapshots_dir is None:
            os.environ.pop("RFMCP_SNAPSHOTS_DIR", None)
        else:
            os.environ["RFMCP_SNAPSHOTS_DIR"] = self._prev_snapshots_dir
        self._snapshots_tmp.cleanup()

    def test_allowlisted_surface_stays_small_and_session_only(self) -> None:
        self.assertLessEqual(len(ALLOWLISTED_TOOL_NAMES), MAX_USER_FACING_TOOLS)
        self.assertEqual(
            ALLOWLISTED_TOOL_NAMES,
            (
                "rf_session",
                "rf_execute_step",
                "rf_context",
                "rf_manage_session",
                "rf_export_suite",
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
        store = LiveSessionStore()
        LiveStepper(store)
        session_tool = build_session_tool(store)
        execute_step = build_execute_step_tool(store)

        opened = _open(session_tool)
        self.assertTrue(opened["ok"])
        session_id = opened["session"]["session_id"]

        unsupported = session_tool(action=SessionAction.OPEN, transport="tcp")
        self.assertFalse(unsupported["ok"])
        self.assertEqual(unsupported["error"]["code"], "unsupported-transport")

        session_status = _get(session_tool, session_id)
        self.assertTrue(session_status["ok"])
        self.assertEqual(session_status["session"]["status"], "open")

        stepped = execute_step(session_id, "No Operation")
        self.assertTrue(stepped["ok"])
        self.assertEqual(stepped["session"]["step_count"], 1)

        interrupt_store = LiveSessionStore()
        interrupt_store.engine_factory = lambda sid, libs: _InterruptEngine()
        interrupt_session = build_session_tool(interrupt_store)
        interrupt_execute = build_execute_step_tool(interrupt_store)
        interrupt_sid = _open(interrupt_session)["session"]["session_id"]
        interrupted = interrupt_execute(interrupt_sid, "Retry failing step")
        self.assertFalse(interrupted["ok"])
        self.assertEqual(interrupted["error"]["code"], "step-interrupted")
        self.assertEqual(interrupted["session"]["status"], "interrupted")

        closed = _close(session_tool, session_id)
        self.assertTrue(closed["ok"])
        restarted = _open(session_tool)
        self.assertTrue(restarted["ok"])
        restarted_id = restarted["session"]["session_id"]
        closed = _close(session_tool, restarted_id)
        self.assertEqual(closed["session"]["status"], "closed")

        after_close = execute_step(restarted_id, "Attempt after close")
        self.assertFalse(after_close["ok"])
        self.assertEqual(after_close["error"]["code"], "session-not-open")

        missing = _get(session_tool, "missing-session")
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["error"]["code"], "session-not-found")

    def test_session_action_get_close_require_session_id(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        missing_get = session_tool(action=SessionAction.GET)
        self.assertFalse(missing_get["ok"])
        self.assertEqual(missing_get["error"]["code"], "missing-session-id")
        missing_close = session_tool(action=SessionAction.CLOSE)
        self.assertFalse(missing_close["ok"])
        self.assertEqual(missing_close["error"]["code"], "missing-session-id")

    def test_live_step_executes_real_keywords_with_persistent_state(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        execute_step = build_execute_step_tool(store)

        session_id = _open(session_tool)["session"]["session_id"]

        # Real keyword execution with return-value assignment into the live namespace.
        assigned = execute_step(session_id, "${result} =    Evaluate    1 + 2")
        self.assertTrue(assigned["ok"])
        self.assertIn("${result}", assigned["detail"])

        # State persists across steps: ${result} resolves to the real integer 3.
        persisted = execute_step(session_id, "Should Be Equal    ${result}    ${3}")
        self.assertTrue(persisted["ok"])

        # A passing assertion passes.
        passed = execute_step(session_id, "Should Be Equal    1    1")
        self.assertTrue(passed["ok"])

        # A genuinely failing assertion surfaces a real failure, not a recorded no-op.
        failed = execute_step(session_id, "Should Be Equal    1    2")
        self.assertFalse(failed["ok"])
        self.assertEqual(failed["error"]["code"], "step-failed")
        self.assertIn("1 != 2", failed["error"]["message"])
        self.assertEqual(failed["error"]["provenance"]["source"], "live-execution")

        _close(session_tool, session_id)

    def test_context_tools_support_read_and_write(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        context_tool = build_context_tool(store)

        opened = _open(session_tool)
        session_id = opened["session"]["session_id"]

        baseline = _ctx_get(context_tool, session_id)
        self.assertTrue(baseline["ok"])
        # Real Robot Framework built-ins are present (live namespace, not a placeholder dict).
        self.assertIn("${/}", baseline["context"]["variables"])
        self.assertIn("BuiltIn", baseline["context"]["libraries"])

        updated = _ctx_set(context_tool, session_id, "${BROWSER}", {"name": "chromium", "headless": True})
        self.assertTrue(updated["ok"])
        self.assertEqual(updated["context"]["key"], "${BROWSER}")
        self.assertEqual(updated["context"]["value"], {"name": "chromium", "headless": True})

        narrowed = _ctx_get(context_tool, session_id, ["${BROWSER}"])
        self.assertTrue(narrowed["ok"])
        self.assertEqual(narrowed["context"]["variables"], {"${BROWSER}": {"name": "chromium", "headless": True}})

        missing = _ctx_get(context_tool, "missing-session")
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["error"]["code"], "session-not-found")
        self.assertEqual(missing["error"]["provenance"]["source"], "session-store")
        self.assertIn("context reads", missing["error"]["suggested_next_step"])

        _close(session_tool, session_id)
        blocked_write = _ctx_set(context_tool, session_id, "${AFTER_CLOSE}", True)
        self.assertFalse(blocked_write["ok"])
        self.assertEqual(blocked_write["error"]["code"], "session-not-open")
        self.assertEqual(blocked_write["error"]["provenance"]["source"], "session-store")
        self.assertIn("context mutation", blocked_write["error"]["suggested_next_step"])

        closed = _ctx_get(context_tool, session_id)
        self.assertFalse(closed["ok"])
        self.assertEqual(closed["error"]["code"], "session-not-open")
        self.assertEqual(closed["error"]["provenance"]["source"], "session-store")
        self.assertIn("context reads", closed["error"]["suggested_next_step"])

    def test_context_set_get_roundtrip_through_live_namespace(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        context_tool = build_context_tool(store)
        execute_step = build_execute_step_tool(store)

        session_id = _open(session_tool)["session"]["session_id"]

        written = _ctx_set(context_tool, session_id, "${X}", 7)
        self.assertTrue(written["ok"])

        read = _ctx_get(context_tool, session_id, ["${X}"])
        self.assertTrue(read["ok"])
        self.assertEqual(read["context"]["variables"], {"${X}": 7})

        # The value lives in the real namespace, so a keyword step resolves it.
        used = execute_step(session_id, "Should Be Equal    ${X}    ${7}")
        self.assertTrue(used["ok"])

    def test_context_mutation_rejects_invalid_keys_without_mutating_session_state(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        context_tool = build_context_tool(store)

        opened = _open(session_tool)
        session_id = opened["session"]["session_id"]

        invalid = _ctx_set(context_tool, session_id, "", "bad-value")
        self.assertFalse(invalid["ok"])
        self.assertEqual(invalid["error"]["code"], "invalid-context-key")
        self.assertEqual(invalid["error"]["provenance"]["source"], "runtime-context")
        self.assertIn("non-empty Robot Framework variable name", invalid["error"]["suggested_next_step"])

        # Non-empty but RF-syntactically invalid name (no ${} braces).
        malformed = _ctx_set(context_tool, session_id, "NOBRACES", "x")
        self.assertFalse(malformed["ok"])
        self.assertEqual(malformed["error"]["code"], "invalid-context-key")
        self.assertEqual(malformed["error"]["provenance"]["source"], "runtime-context")

        context = _ctx_get(context_tool, session_id)
        self.assertTrue(context["ok"])
        self.assertNotIn("", context["context"]["variables"])
        self.assertNotIn("NOBRACES", context["context"]["variables"])

    def test_interrupted_sessions_still_allow_context_reads(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        context_tool = build_context_tool(store)
        inspect_state = build_app_inspect_state_tool(store)

        store.engine_factory = lambda sid, libs: _InterruptEngine()
        execute_step = build_execute_step_tool(store)

        opened = _open(session_tool)
        session_id = opened["session"]["session_id"]

        interrupted = execute_step(session_id, "Pause after failure")
        self.assertFalse(interrupted["ok"])
        self.assertEqual(interrupted["session"]["status"], "interrupted")

        context = _ctx_get(context_tool, session_id)
        self.assertTrue(context["ok"])
        self.assertIn("${CURRENT_TEST}", context["context"]["variables"])

        blocked_write = _ctx_set(context_tool, session_id, "${AFTER_INTERRUPT}", True)
        self.assertFalse(blocked_write["ok"])
        self.assertEqual(blocked_write["error"]["code"], "session-not-open")
        self.assertEqual(blocked_write["error"]["provenance"]["source"], "session-store")

        snapshot = inspect_state(session_id=session_id, snapshot_kind=SnapshotKind.APP_CONTEXT)
        self.assertTrue(snapshot["ok"])
        # app_context is always inlined (compact JSON); summary carries library/variable counts.
        self.assertIn("BuiltIn", snapshot["snapshot"]["content"])
        self.assertGreater(snapshot["snapshot"]["manifest"]["summary"]["library_count"], 0)

    def test_context_write_policy_and_session_denials_are_structured(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        context_tool = build_context_tool(store)
        opened = _open(session_tool)
        session_id = opened["session"]["session_id"]

        with patch("rfmcp_core.runtime.context.capability_allowed", return_value=False):
            denied = _ctx_set(context_tool, session_id, "${MODE}", "readonly")
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["error"]["code"], "policy-context-write-disabled")
        self.assertEqual(denied["error"]["provenance"]["kind"], "observed")
        self.assertEqual(denied["error"]["provenance"]["source"], "local-policy")
        self.assertIn("local policy", denied["error"]["suggested_next_step"])

        store.configure_capabilities(session_id, allow_context_write=False)
        denied_by_session = _ctx_set(context_tool, session_id, "${MODE}", "readonly")
        self.assertFalse(denied_by_session["ok"])
        self.assertEqual(denied_by_session["error"]["code"], "session-context-write-disabled")
        self.assertEqual(denied_by_session["error"]["provenance"]["kind"], "observed")
        self.assertEqual(denied_by_session["error"]["provenance"]["source"], "session-store")
        self.assertIn("context reads only", denied_by_session["error"]["suggested_next_step"])

    def test_approved_inspection_snapshots_and_denials_are_structured(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        inspect_state = build_app_inspect_state_tool(store)
        opened = _open(session_tool)
        session_id = opened["session"]["session_id"]

        # app_context is real, always-available live session state (no external app needed).
        app_ctx = inspect_state(session_id=session_id, snapshot_kind=SnapshotKind.APP_CONTEXT)
        self.assertTrue(app_ctx["ok"])
        snap = app_ctx["snapshot"]
        self.assertEqual(snap["snapshot_kind"], "app_context")
        self.assertEqual(snap["provenance"]["kind"], "observed")
        self.assertEqual(snap["provenance"]["source"], "live-session")
        # Manifest carries the on-disk path + a kind-specific summary.
        self.assertTrue(snap["manifest"]["path"].endswith(".json"))
        self.assertEqual(snap["manifest"]["format"], "json")
        self.assertGreater(snap["manifest"]["summary"]["library_count"], 0)
        # app_context is small enough to always inline; the file should exist on disk too.
        self.assertIn("BuiltIn", snap["content"])
        self.assertTrue(Path(snap["manifest"]["path"]).exists())

        # A default session loads no browser/HTTP library, so DOM-family kinds have no live
        # source and must report a structured snapshot-unavailable error (not a fixture).
        for snapshot_kind in (
            SnapshotKind.DOM,
            SnapshotKind.SCREENSHOT,
            SnapshotKind.ARIA,
            SnapshotKind.CONSOLE_LOG,
        ):
            response = inspect_state(session_id=session_id, snapshot_kind=snapshot_kind)
            self.assertFalse(response["ok"], snapshot_kind.value)
            self.assertEqual(response["error"]["code"], "snapshot-unavailable", snapshot_kind.value)
            self.assertEqual(response["error"]["provenance"]["kind"], "observed", snapshot_kind.value)

        # dom_selector requires a selector — missing-selector is its own structured error.
        missing_selector = inspect_state(session_id=session_id, snapshot_kind=SnapshotKind.DOM_SELECTOR)
        self.assertFalse(missing_selector["ok"])
        self.assertEqual(missing_selector["error"]["code"], "missing-selector")

        # network_log is intentionally unavailable in v1 with HAR-recording guidance.
        net = inspect_state(session_id=session_id, snapshot_kind=SnapshotKind.NETWORK_LOG)
        self.assertFalse(net["ok"])
        self.assertEqual(net["error"]["code"], "snapshot-unavailable")
        self.assertIn("recordHar", net["error"]["suggested_next_step"])

        missing = inspect_state(session_id="missing-session", snapshot_kind=SnapshotKind.DOM)
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["error"]["code"], "session-not-found")
        self.assertEqual(missing["error"]["provenance"]["source"], "session-store")
        self.assertIn("inspection snapshot", missing["error"]["suggested_next_step"])

        store.configure_capabilities(session_id, allowed_snapshot_kinds=(SnapshotKind.DOM,))
        denied_by_session = inspect_state(session_id=session_id, snapshot_kind=SnapshotKind.SCREENSHOT)
        self.assertFalse(denied_by_session["ok"])
        self.assertEqual(denied_by_session["error"]["code"], "session-snapshot-disabled")
        self.assertEqual(denied_by_session["error"]["provenance"]["kind"], "observed")
        self.assertEqual(denied_by_session["error"]["provenance"]["source"], "session-store")
        self.assertIn("allowed snapshot kind", denied_by_session["error"]["suggested_next_step"])

        with patch("rfmcp_core.runtime.snapshot.capability_allowed", return_value=False):
            denied_by_policy = inspect_state(session_id=session_id, snapshot_kind=SnapshotKind.DOM)
        self.assertFalse(denied_by_policy["ok"])
        self.assertEqual(denied_by_policy["error"]["code"], "policy-inspection-disabled")
        self.assertEqual(denied_by_policy["error"]["provenance"]["kind"], "observed")
        self.assertEqual(denied_by_policy["error"]["provenance"]["source"], "local-policy")
        self.assertIn("local policy", denied_by_policy["error"]["suggested_next_step"])

        _close(session_tool, session_id)
        closed = inspect_state(session_id=session_id, snapshot_kind=SnapshotKind.DOM)
        self.assertFalse(closed["ok"])
        self.assertEqual(closed["error"]["code"], "session-not-open")
        self.assertEqual(closed["error"]["provenance"]["source"], "session-store")
        self.assertIn("inspection snapshots", closed["error"]["suggested_next_step"])

    def test_new_tools_map_policy_load_failures_to_structured_errors(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        context_tool = build_context_tool(store)
        inspect_state = build_app_inspect_state_tool(store)
        opened = _open(session_tool)
        session_id = opened["session"]["session_id"]

        with patch("rfmcp_core.runtime.context.load_local_policy_defaults", side_effect=FileNotFoundError()):
            context_error = _ctx_set(context_tool, session_id, "${MODE}", "readonly")
        self.assertFalse(context_error["ok"])
        self.assertEqual(context_error["error"]["code"], "policy-load-failed")
        self.assertEqual(context_error["error"]["provenance"]["source"], "local-policy")

        with patch("rfmcp_core.runtime.snapshot.load_local_policy_defaults", side_effect=FileNotFoundError()):
            snapshot_error = inspect_state(session_id=session_id, snapshot_kind=SnapshotKind.DOM)
        self.assertFalse(snapshot_error["ok"])
        self.assertEqual(snapshot_error["error"]["code"], "policy-load-failed")
        self.assertEqual(snapshot_error["error"]["provenance"]["source"], "local-policy")

    def test_new_tools_trap_unexpected_exceptions_with_shared_error_envelope(self) -> None:
        store = LiveSessionStore()
        context_tool = build_context_tool(store)
        inspect_state = build_app_inspect_state_tool(store)

        with patch("rfmcp_mcp.tools.rf_context.get_runtime_context", side_effect=RuntimeError("boom")):
            get_error = _ctx_get(context_tool, "session-1")
        self.assertFalse(get_error["ok"])
        self.assertEqual(get_error["error"]["code"], "tool-execution-failed")
        self.assertEqual(get_error["error"]["provenance"]["source"], "rf_context")

        with patch("rfmcp_mcp.tools.rf_context.set_runtime_context", side_effect=RuntimeError("boom")):
            set_error = _ctx_set(context_tool, "session-1", "${MODE}", "readonly")
        self.assertFalse(set_error["ok"])
        self.assertEqual(set_error["error"]["code"], "tool-execution-failed")
        self.assertEqual(set_error["error"]["provenance"]["source"], "rf_context")

        with patch("rfmcp_mcp.tools.app_inspect_state.capture_inspection_snapshot", side_effect=RuntimeError("boom")):
            snapshot_error = inspect_state(session_id="session-1", snapshot_kind=SnapshotKind.DOM)
        self.assertFalse(snapshot_error["ok"])
        self.assertEqual(snapshot_error["error"]["code"], "tool-execution-failed")
        self.assertEqual(snapshot_error["error"]["provenance"]["source"], "app_inspect_state")

    def test_attach_default_denied_by_policy(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        denied = _open(session_tool, attach_requested=True)
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["error"]["code"], "policy-attach-disabled")

    def test_attach_rejects_non_loopback_host(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        with patch("rfmcp_mcp.security.attach_policy.capability_allowed", return_value=True):
            denied = _open(session_tool, attach_requested=True, attach_host="10.0.0.5")
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["error"]["code"], "policy-attach-loopback-only")

    def test_attach_session_routes_to_external_bridge(self) -> None:
        from rfmcp_core.runtime.attach import AttachExecutionContext

        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        execute_step = build_execute_step_tool(store)
        context_tool = build_context_tool(store)
        inspect_state = build_app_inspect_state_tool(store)

        with patch("rfmcp_mcp.security.attach_policy.capability_allowed", return_value=True):
            opened = _open(session_tool, attach_requested=True, attach_host="127.0.0.1", attach_port=7317)
        self.assertTrue(opened["ok"])
        self.assertTrue(opened["session"]["attach_requested"])
        # The ephemeral token is returned so the operator can configure their listener.
        self.assertTrue(opened["session"]["attach_token"])
        session_id = opened["session"]["session_id"]

        engine = store.get_or_create_engine(session_id)
        self.assertIsInstance(engine, AttachExecutionContext)

        calls: list[str] = []

        def fake_post(path, payload):  # noqa: ANN001
            calls.append(path)
            if path == "run_keyword":
                return {"ok": True, "keyword": payload.get("keyword"), "return_value": "BRIDGED"}
            if path == "get_variables":
                return {"variables": {"${FROM_BRIDGE}": 1}}
            if path == "get_libraries":
                return {"libraries": ["BuiltIn", "Browser"]}
            return {"ok": True}

        with patch.object(engine, "_post", side_effect=fake_post):
            stepped = execute_step(session_id, "Log    hi")
            self.assertTrue(stepped["ok"])
            context = _ctx_get(context_tool, session_id)
            written = _ctx_set(context_tool, session_id, "${X}", 5)
            snapshot = inspect_state(session_id=session_id, snapshot_kind=SnapshotKind.APP_CONTEXT)

        # Every surface routed through the bridge transport.
        self.assertIn("run_keyword", calls)
        self.assertIn("get_variables", calls)
        self.assertIn("set_variable", calls)
        self.assertIn("get_libraries", calls)
        self.assertEqual(context["context"]["variables"], {"${FROM_BRIDGE}": 1})
        self.assertTrue(written["ok"])
        self.assertTrue(snapshot["ok"])
        # app_context content is the persisted JSON; Browser must appear among loaded libs.
        self.assertIn("Browser", snapshot["snapshot"]["content"])

    def test_attach_unreachable_bridge_returns_structured_failure(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        execute_step = build_execute_step_tool(store)
        with patch("rfmcp_mcp.security.attach_policy.capability_allowed", return_value=True):
            opened = _open(session_tool, attach_requested=True, attach_host="127.0.0.1", attach_port=1)
        session_id = opened["session"]["session_id"]
        stepped = execute_step(session_id, "Log    hi")  # port 1 is closed → unreachable
        self.assertFalse(stepped["ok"])
        self.assertEqual(stepped["error"]["code"], "step-failed")
        self.assertIn("unreachable", stepped["error"]["message"].lower())

    def test_build_server_registers_only_allowlisted_tools(self) -> None:
        server = build_server(LiveSessionStore())
        self.assertEqual(server.name, "rfmcp-reloaded")
        tools = asyncio.run(server.list_tools())
        self.assertEqual({tool.name for tool in tools}, set(ALLOWLISTED_TOOL_NAMES))
        rf_context = next(tool for tool in tools if tool.name == "rf_context")
        # 'value' carries a description for the agent and accepts any JSON-safe value
        # (no `type` constraint — the schema is unconstrained for the payload).
        value_schema = rf_context.parameters["properties"]["value"]
        self.assertIn("description", value_schema)
        self.assertNotIn("type", value_schema)

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
