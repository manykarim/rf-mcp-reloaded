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

from rfmcp_core.contracts import SessionAction, SnapshotKind, TransportKind  # noqa: E402
from rfmcp_core.runtime.session import LiveSessionStore  # noqa: E402
from rfmcp_core.runtime.stepper import _diagnostic_next_step, _looks_like_locator  # noqa: E402
from rfmcp_mcp.tools.app_inspect_state import build_app_inspect_state_tool  # noqa: E402
from rfmcp_mcp.tools.rf_execute_step import build_execute_step_tool  # noqa: E402
from rfmcp_mcp.tools.rf_session import build_session_tool  # noqa: E402


def _open(session_tool) -> str:
    return session_tool(action=SessionAction.OPEN, transport=TransportKind.STDIO)["session"]["session_id"]


class LocatorRecognitionTests(unittest.TestCase):
    def test_recognises_common_locator_shapes(self) -> None:
        for locator in [
            "css=#login",
            "xpath=//button",
            "id=user-name",
            "[data-test=add-to-cart]",
            "//div[@class='shadow']",
            ".add-to-cart-btn",
            "#login-button",
            "text=Click me",
            "data-test=submit",
        ]:
            self.assertTrue(_looks_like_locator(locator), locator)

    def test_skips_non_locators(self) -> None:
        for value in ["chromium", "standard_user", "${VAR}", "@{LIST}", "&{MAP}", "", "1 + 2"]:
            self.assertFalse(_looks_like_locator(value), value)


class DiagnosticSuggestionTests(unittest.TestCase):
    def test_generic_suggestion_when_no_browser_library(self) -> None:
        msg = _diagnostic_next_step("Should Be Equal    ${x}    1", ["BuiltIn"], "sid-1")
        self.assertIn("Inspect runtime context", msg)
        self.assertNotIn("app_inspect_state", msg)

    def test_dom_selector_suggestion_when_locator_present(self) -> None:
        msg = _diagnostic_next_step("Click    #login-button", ["BuiltIn", "Browser"], "sid-1")
        self.assertIn("app_inspect_state", msg)
        self.assertIn("snapshot_kind='dom_selector'", msg)
        self.assertIn("selector='#login-button'", msg)
        self.assertIn("snapshot_kind='aria'", msg)  # fallback hint also surfaced

    def test_aria_suggestion_when_no_locator_present(self) -> None:
        msg = _diagnostic_next_step("New Browser    chromium    headless=True", ["Browser"], "sid-2")
        self.assertIn("app_inspect_state(session_id='sid-2', snapshot_kind='aria')", msg)
        self.assertNotIn("dom_selector", msg)

    def test_works_for_selenium(self) -> None:
        msg = _diagnostic_next_step("Click Element    id=submit", ["SeleniumLibrary"], "sid-3")
        self.assertIn("dom_selector", msg)
        self.assertIn("selector='id=submit'", msg)


class BatchingTests(unittest.TestCase):
    def test_missing_input_returns_structured_error(self) -> None:
        store = LiveSessionStore()
        execute = build_execute_step_tool(store)
        result = execute(session_id="any")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "missing-input")

    def test_conflicting_input_returns_structured_error(self) -> None:
        store = LiveSessionStore()
        execute = build_execute_step_tool(store)
        result = execute(session_id="any", instruction="Log    hi", instructions=["Log    hi"])
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "conflicting-input")

    def test_single_mode_unchanged(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        execute = build_execute_step_tool(store)
        sid = _open(session_tool)
        result = execute(session_id=sid, instruction="No Operation")
        self.assertTrue(result["ok"])
        # Single mode keeps the StepResult shape (session at top level, step_index, etc.).
        self.assertIn("step_index", result)
        self.assertIn("session", result)
        self.assertEqual(result["session"]["step_count"], 1)

    def test_batch_runs_each_instruction_and_returns_one_session(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        execute = build_execute_step_tool(store)
        sid = _open(session_tool)
        result = execute(
            session_id=sid,
            instructions=["No Operation", "${r} =    Evaluate    1 + 2", "Should Be Equal    ${r}    ${3}"],
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["executed"], 3)
        self.assertEqual(len(result["results"]), 3)
        self.assertIsNone(result["failed_index"])
        # Session summary appears ONCE (top level) — the per-step entries skip it.
        self.assertEqual(result["session"]["step_count"], 3)
        for entry in result["results"]:
            self.assertIn("step_index", entry)
            self.assertIn("instruction", entry)
            self.assertNotIn("session", entry)

    def test_batch_stops_on_first_failure_by_default(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        execute = build_execute_step_tool(store)
        sid = _open(session_tool)
        result = execute(
            session_id=sid,
            instructions=[
                "No Operation",
                "Should Be Equal    1    2",  # fails
                "Should Not Be Run",  # should not execute
            ],
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["failed_index"], 1)
        self.assertEqual(result["executed"], 2)
        self.assertTrue(result["results"][0]["ok"])
        self.assertFalse(result["results"][1]["ok"])
        self.assertEqual(result["results"][1]["error"]["code"], "step-failed")

    def test_batch_continues_when_stop_on_failure_is_false(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        execute = build_execute_step_tool(store)
        sid = _open(session_tool)
        result = execute(
            session_id=sid,
            instructions=["No Operation", "Should Be Equal    1    2", "No Operation"],
            stop_on_failure=False,
        )
        self.assertFalse(result["ok"])  # one step failed
        self.assertEqual(result["executed"], 3)
        self.assertEqual(result["failed_index"], 1)  # first failure index
        self.assertEqual([r["ok"] for r in result["results"]], [True, False, True])

    def test_batch_response_smaller_than_sequential_for_same_steps(self) -> None:
        import json
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        execute = build_execute_step_tool(store)
        sid = _open(session_tool)
        steps = ["No Operation"] * 5

        sequential = [execute(session_id=sid, instruction=step) for step in steps]
        sequential_bytes = sum(len(json.dumps(r).encode()) for r in sequential)

        sid2 = _open(session_tool)
        batched = execute(session_id=sid2, instructions=steps)
        batched_bytes = len(json.dumps(batched).encode())

        # Batched response is meaningfully smaller because the session summary
        # appears once instead of five times.
        self.assertLess(batched_bytes, sequential_bytes)


class ClosedShadowProbeTests(unittest.TestCase):
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

    def _build_stub_engine(self, probe_result):
        class _Stub:
            def query(self, keyword: str, args=None):  # noqa: ANN001
                if keyword == "Evaluate JavaScript":
                    # The probe is the only JS call hit by the dom path here.
                    return probe_result
                if keyword in {"Get Page Source", "Get Source"}:
                    return "<html><body><my-widget></my-widget></body></html>"
                raise RuntimeError(f"unexpected keyword: {keyword}")

            def get_variables(self, keys=None):  # noqa: ANN001
                return {}

            def imported_libraries(self) -> list[str]:
                return ["BuiltIn", "Browser"]

            def close(self) -> None:
                pass

        return _Stub()

    def test_dom_summary_includes_closed_shadow_probe_when_present(self) -> None:
        store = LiveSessionStore()
        store.engine_factory = lambda sid, libs: self._build_stub_engine(
            {
                "custom_element_count": 5,
                "open_shadow_root_count": 2,
                "possible_closed_shadow_root_count": 3,
                "total_open_shadow_roots": 2,
            }
        )
        session_tool = build_session_tool(store)
        inspect = build_app_inspect_state_tool(store)
        sid = _open(session_tool)

        result = inspect(session_id=sid, snapshot_kind=SnapshotKind.DOM)
        self.assertTrue(result["ok"])
        summary = result["snapshot"]["manifest"]["summary"]
        self.assertIn("closed_shadow_probe", summary)
        self.assertTrue(summary["has_possible_closed_shadow_roots"])
        self.assertEqual(summary["closed_shadow_probe"]["custom_element_count"], 5)
        self.assertEqual(summary["closed_shadow_probe"]["possible_closed_shadow_root_count"], 3)

    def test_probe_failure_does_not_break_dom_capture(self) -> None:
        # An engine that raises on Evaluate JavaScript must still return a DOM snapshot.
        class _NoJsEngine:
            def query(self, keyword: str, args=None):  # noqa: ANN001
                if keyword == "Evaluate JavaScript":
                    raise RuntimeError("not supported in this driver")
                if keyword in {"Get Page Source", "Get Source"}:
                    return "<html><body>x</body></html>"
                raise RuntimeError(f"unexpected: {keyword}")

            def get_variables(self, keys=None):  # noqa: ANN001
                return {}

            def imported_libraries(self) -> list[str]:
                return ["BuiltIn"]

            def close(self) -> None:
                pass

        store = LiveSessionStore()
        store.engine_factory = lambda sid, libs: _NoJsEngine()
        session_tool = build_session_tool(store)
        inspect = build_app_inspect_state_tool(store)
        sid = _open(session_tool)
        result = inspect(session_id=sid, snapshot_kind=SnapshotKind.DOM)
        self.assertTrue(result["ok"])
        summary = result["snapshot"]["manifest"]["summary"]
        # Probe softly degrades — closed_shadow_probe absent when JS isn't available.
        self.assertNotIn("closed_shadow_probe", summary)


if __name__ == "__main__":
    unittest.main()
