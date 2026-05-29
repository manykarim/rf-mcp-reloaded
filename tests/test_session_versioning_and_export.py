from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for path in [
    REPO_ROOT / "packages" / "rfmcp_core" / "src",
    REPO_ROOT / "packages" / "rfmcp_mcp" / "src",
]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rfmcp_core.contracts import (  # noqa: E402
    ContextAction,
    ManageSessionAction,
    SessionAction,
    TransportKind,
)
from rfmcp_core.runtime.session import LiveSessionStore  # noqa: E402
from rfmcp_mcp.tools.rf_context import build_context_tool  # noqa: E402
from rfmcp_mcp.tools.rf_execute_step import build_execute_step_tool  # noqa: E402
from rfmcp_mcp.tools.rf_export_suite import build_export_suite_tool  # noqa: E402
from rfmcp_mcp.tools.rf_manage_session import build_manage_session_tool  # noqa: E402
from rfmcp_mcp.tools.rf_session import build_session_tool  # noqa: E402


def _open(session_tool) -> tuple[dict, str]:
    opened = session_tool(action=SessionAction.OPEN, transport=TransportKind.STDIO)
    return opened, opened["session"]["session_id"]


class SessionVersioningTests(unittest.TestCase):
    def test_open_session_starts_at_version_zero(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        opened, _ = _open(session_tool)
        self.assertEqual(opened["session"]["version"], 0)

    def test_step_execution_bumps_version(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        execute_step = build_execute_step_tool(store)
        _, sid = _open(session_tool)
        before = session_tool(action=SessionAction.GET, session_id=sid)
        self.assertEqual(before["session"]["version"], 0)
        result = execute_step(sid, "No Operation")
        self.assertTrue(result["ok"])
        after = session_tool(action=SessionAction.GET, session_id=sid)
        self.assertGreater(after["session"]["version"], before["session"]["version"])

    def test_context_set_and_manage_session_bump_version(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        context_tool = build_context_tool(store)
        manage = build_manage_session_tool(store)
        _, sid = _open(session_tool)

        v0 = session_tool(action=SessionAction.GET, session_id=sid)["session"]["version"]
        context_tool(session_id=sid, action=ContextAction.SET, key="${X}", value=1)
        v1 = session_tool(action=SessionAction.GET, session_id=sid)["session"]["version"]
        self.assertGreater(v1, v0)

        manage(sid, ManageSessionAction.SET_VARIABLE, name="${BASE_URL}", value="https://example.com")
        v2 = session_tool(action=SessionAction.GET, session_id=sid)["session"]["version"]
        self.assertGreater(v2, v1)

        manage(sid, ManageSessionAction.SET_TAGS, scope="suite", tags=["smoke"])
        v3 = session_tool(action=SessionAction.GET, session_id=sid)["session"]["version"]
        self.assertGreater(v3, v2)

    def test_close_session_bumps_version(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        _, sid = _open(session_tool)
        before = session_tool(action=SessionAction.GET, session_id=sid)["session"]["version"]
        session_tool(action=SessionAction.CLOSE, session_id=sid)
        # Record is still in the store, status=closed, version bumped.
        record = store.get_record(sid)
        self.assertGreater(record.version, before)

    def test_get_with_since_version_short_circuits_when_unchanged(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        execute_step = build_execute_step_tool(store)
        _, sid = _open(session_tool)
        execute_step(sid, "No Operation")
        current = session_tool(action=SessionAction.GET, session_id=sid)
        version = current["session"]["version"]

        same = session_tool(action=SessionAction.GET, session_id=sid, since_version=version)
        self.assertTrue(same["ok"])
        self.assertTrue(same["unchanged"])
        # Tiny payload: only the three identity fields.
        self.assertEqual(set(same["session"].keys()), {"session_id", "version", "status"})

    def test_get_with_stale_since_version_returns_full_summary(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        execute_step = build_execute_step_tool(store)
        _, sid = _open(session_tool)
        execute_step(sid, "No Operation")
        execute_step(sid, "No Operation")
        full = session_tool(action=SessionAction.GET, session_id=sid, since_version=0)
        self.assertTrue(full["ok"])
        self.assertNotIn("unchanged", full)
        self.assertEqual(full["session"]["step_count"], 2)


class ExportSuiteTests(unittest.TestCase):
    def test_export_requires_executed_steps(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        export = build_export_suite_tool(store)
        _, sid = _open(session_tool)
        result = export(session_id=sid)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "no-steps-to-export")

    def test_export_writes_canonical_rf7_to_target(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        execute_step = build_execute_step_tool(store)
        export = build_export_suite_tool(store)
        _, sid = _open(session_tool)
        execute_step(sid, "${r} =    Evaluate    1 + 2")
        execute_step(sid, "Should Be Equal    ${r}    ${3}")

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.robot"
            result = export(
                session_id=sid,
                target_path=str(target),
                test_case_name="Greeting Proof",
                documentation="Demo",
                return_inline=True,
            )
            self.assertTrue(result["ok"])
            # Manifest carries path / bytes / sha / summary.
            self.assertEqual(result["manifest"]["path"], str(target))
            self.assertEqual(result["manifest"]["format"], "robot")
            self.assertEqual(result["manifest"]["summary"]["step_count"], 2)
            self.assertTrue(target.exists())
            text = target.read_text()
            # Canonical RF7: no obsolete '${r} =', proper sections.
            self.assertIn("*** Test Cases ***", text)
            self.assertIn("Greeting Proof", text)
            self.assertIn("${r}    Evaluate    1 + 2", text)
            self.assertNotIn("${r} =", text)
            # Inline content also returned.
            self.assertEqual(result["content"], text)

    def test_export_refuses_existing_target_without_force(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        execute_step = build_execute_step_tool(store)
        export = build_export_suite_tool(store)
        _, sid = _open(session_tool)
        execute_step(sid, "No Operation")

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.robot"
            target.write_text("placeholder", encoding="utf-8")
            blocked = export(session_id=sid, target_path=str(target))
            self.assertFalse(blocked["ok"])
            self.assertEqual(blocked["error"]["code"], "target-exists")
            forced = export(session_id=sid, target_path=str(target), force=True)
            self.assertTrue(forced["ok"])

    def test_export_inline_only_does_not_touch_disk(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        execute_step = build_execute_step_tool(store)
        export = build_export_suite_tool(store)
        _, sid = _open(session_tool)
        execute_step(sid, "No Operation")

        result = export(session_id=sid, return_inline=True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["manifest"]["path"], "<in-memory-preview>")
        self.assertTrue(result["manifest"]["summary"]["in_memory_preview"])
        self.assertIn("*** Test Cases ***", result["content"])

    def test_export_rejects_non_robot_extension(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        execute_step = build_execute_step_tool(store)
        export = build_export_suite_tool(store)
        _, sid = _open(session_tool)
        execute_step(sid, "No Operation")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.txt"
            result = export(session_id=sid, target_path=str(target))
            self.assertFalse(result["ok"])
            self.assertEqual(result["error"]["code"], "unsupported-extension")

    def test_export_missing_session(self) -> None:
        store = LiveSessionStore()
        export = build_export_suite_tool(store)
        result = export(session_id="never-opened")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "session-not-found")


class ShadowDomWalkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._snapshots_tmp = tempfile.TemporaryDirectory()
        self._prev = os.environ.get("RFMCP_SNAPSHOTS_DIR")
        os.environ["RFMCP_SNAPSHOTS_DIR"] = self._snapshots_tmp.name

    def tearDown(self) -> None:
        if self._prev is None:
            os.environ.pop("RFMCP_SNAPSHOTS_DIR", None)
        else:
            os.environ["RFMCP_SNAPSHOTS_DIR"] = self._prev
        self._snapshots_tmp.cleanup()

    def test_dom_with_include_shadow_dom_uses_evaluate_javascript(self) -> None:
        # Stub engine that responds to Evaluate JavaScript by returning a fixed payload
        # containing a declarative shadow-root template — proving the dom path took the
        # shadow walker branch.
        shadow_html = (
            '<!DOCTYPE html><html><body>'
            '<my-widget><template shadowrootmode="open">'
            '<button id="shadow-btn">click me</button>'
            '</template></my-widget></body></html>'
        )
        calls: list[tuple[str, object]] = []

        class _StubEngine:
            def query(self, keyword: str, args=None):  # noqa: ANN001
                calls.append((keyword, args))
                if keyword == "Evaluate JavaScript":
                    return shadow_html
                if keyword in {"Get Page Source", "Get Source"}:
                    return "<html><body>plain</body></html>"
                raise RuntimeError(f"unexpected keyword: {keyword}")

            def get_variables(self, keys=None):  # noqa: ANN001
                return {}

            def imported_libraries(self) -> list[str]:
                return ["BuiltIn", "Browser"]

            def close(self) -> None:
                pass

        store = LiveSessionStore()
        store.engine_factory = lambda sid, libs: _StubEngine()
        session_tool = build_session_tool(store)
        from rfmcp_mcp.tools.app_inspect_state import build_app_inspect_state_tool
        inspect = build_app_inspect_state_tool(store)

        _, sid = _open(session_tool)
        # Without shadow flag: plain DOM, no shadow content.
        plain = inspect(session_id=sid, snapshot_kind="dom", return_inline=True)
        self.assertTrue(plain["ok"])
        self.assertIn("plain", plain["snapshot"]["content"])
        self.assertNotIn("shadowrootmode", plain["snapshot"]["content"])
        # First call should have hit Get Page Source, not Evaluate JavaScript.
        self.assertEqual(calls[0][0], "Get Page Source")

        # With include_shadow_dom: shadow root is in the persisted content + summary flag.
        walked = inspect(
            session_id=sid,
            snapshot_kind="dom",
            return_inline=True,
            include_shadow_dom=True,
        )
        self.assertTrue(walked["ok"])
        self.assertIn("shadowrootmode", walked["snapshot"]["content"])
        self.assertIn("shadow-btn", walked["snapshot"]["content"])
        self.assertTrue(walked["snapshot"]["manifest"]["summary"]["shadow_dom_walked"])
        self.assertIn("Evaluate JavaScript", walked["snapshot"]["provenance"]["source"])


if __name__ == "__main__":
    unittest.main()
