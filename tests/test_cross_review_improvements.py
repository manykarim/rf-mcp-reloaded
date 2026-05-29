"""Tests for the improvements landed after the claude/kilo cross review.

Covers:
- Session-level ``has_possible_closed_shadow_roots`` / ``possible_closed_shadow_root_count``
  fields (proposal #6 — surfaces on every ``rf_session(action='get')``).
- ``_diagnostic_next_step`` rewrites its suggestion when the session has seen
  closed-shadow signals (proposal #1).
- ``_aria_summary`` emits ready-to-paste Playwright role locators (proposal #4)
  and tags the summary with a ``closed_shadow_advisory`` when the session has
  observed closed-shadow signals (proposal #4's guard).
"""

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
from rfmcp_core.runtime.snapshot import _aria_selector_hints, _aria_summary  # noqa: E402
from rfmcp_core.runtime.stepper import _diagnostic_next_step  # noqa: E402
from rfmcp_mcp.tools.app_inspect_state import build_app_inspect_state_tool  # noqa: E402
from rfmcp_mcp.tools.rf_execute_step import build_execute_step_tool  # noqa: E402
from rfmcp_mcp.tools.rf_session import build_session_tool  # noqa: E402


SAMPLE_ARIA = """
- document:
  - banner:
    - heading "Logo" [level=1]
  - main:
    - textbox "Email":
      - /placeholder: Enter email
    - textbox "Password"
    - combobox "Country":
      - option "Germany" [selected]
    - button "Submit"
    - link "Forgot Password":
      - /url: /reset
""".strip()


class AriaSelectorHintTests(unittest.TestCase):
    def test_extracts_role_name_pairs_into_playwright_locators(self) -> None:
        hints = _aria_selector_hints(SAMPLE_ARIA)
        # Sample contains 5 labeled interactive elements (textbox×2, combobox, button, link).
        roles = {(h["role"], h["name"]) for h in hints}
        # Includes 'option' because an agent may want to click a specific option
        # (e.g. role=option[name="Germany"]) inside a combobox.
        self.assertEqual(
            roles,
            {
                ("textbox", "Email"),
                ("textbox", "Password"),
                ("combobox", "Country"),
                ("option", "Germany"),
                ("button", "Submit"),
                ("link", "Forgot Password"),
            },
        )
        # Each hint includes a ready-to-paste locator.
        email = next(h for h in hints if h["name"] == "Email")
        self.assertEqual(email["locator"], 'role=textbox[name="Email"]')

    def test_limit_is_respected_and_duplicates_deduped(self) -> None:
        # Build a YAML with duplicate role/name combinations and verify the dedupe + limit.
        repeated = "\n".join(f'    - button "Save"' for _ in range(8))
        # Different button to verify we still capture distinct names.
        repeated += '\n    - button "Cancel"\n'
        hints = _aria_selector_hints(repeated, limit=5)
        names = [h["name"] for h in hints]
        # Duplicates collapse to a single 'Save' entry; we still see 'Cancel'.
        self.assertEqual(names, ["Save", "Cancel"])

    def test_summary_includes_selector_hints(self) -> None:
        summary = _aria_summary(SAMPLE_ARIA)
        self.assertIn("selector_hints", summary)
        self.assertGreater(len(summary["selector_hints"]), 0)
        self.assertEqual(summary["selector_hints"][0]["role"], "textbox")


class SessionShadowSignalTests(unittest.TestCase):
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

    def test_session_summary_initially_reports_no_closed_shadow_signal(self) -> None:
        store = LiveSessionStore()
        session_tool = build_session_tool(store)
        opened = session_tool(action=SessionAction.OPEN, transport=TransportKind.STDIO)
        sid = opened["session"]["session_id"]
        self.assertFalse(opened["session"]["has_possible_closed_shadow_roots"])
        self.assertEqual(opened["session"]["possible_closed_shadow_root_count"], 0)

    def test_dom_snapshot_promotes_probe_count_into_session_signal(self) -> None:
        store = LiveSessionStore()
        store.engine_factory = lambda sid, libs: self._build_stub_engine(
            {
                "custom_element_count": 14,
                "open_shadow_root_count": 1,
                "possible_closed_shadow_root_count": 13,
                "total_open_shadow_roots": 1,
            }
        )
        session_tool = build_session_tool(store)
        inspect = build_app_inspect_state_tool(store)
        sid = session_tool(action=SessionAction.OPEN, transport=TransportKind.STDIO)["session"]["session_id"]

        # Take a DOM snapshot — this should propagate the probe count to session state.
        inspect(session_id=sid, snapshot_kind=SnapshotKind.DOM)

        summary = session_tool(action=SessionAction.GET, session_id=sid)["session"]
        self.assertTrue(summary["has_possible_closed_shadow_roots"])
        self.assertEqual(summary["possible_closed_shadow_root_count"], 13)
        # Version bumped from the signal write — agents see the change via delta-get.
        self.assertGreater(summary["version"], 0)


class DiagnosticNextStepClosedShadowTests(unittest.TestCase):
    def test_normal_locator_suggestion_when_no_closed_shadow(self) -> None:
        msg = _diagnostic_next_step("Click    #login-button", ["Browser"], "sid-1")
        # Normal path — recommend dom_selector with the failing selector.
        self.assertIn("snapshot_kind='dom_selector'", msg)
        self.assertIn("#login-button", msg)
        self.assertNotIn("closed shadow", msg.lower())

    def test_closed_shadow_signal_rewrites_to_aria_advisory(self) -> None:
        msg = _diagnostic_next_step(
            "Click    [data-test='accept']",
            ["Browser"],
            "sid-2",
            has_possible_closed_shadow_roots=True,
            possible_closed_shadow_root_count=13,
        )
        # The advisory replaces the dom_selector hint.
        self.assertIn("snapshot_kind='aria'", msg)
        self.assertNotIn("snapshot_kind='dom_selector'", msg)
        # Counts and "closed shadow" language are included so the agent sees why.
        self.assertIn("13", msg)
        self.assertIn("closed shadow", msg.lower())
        # The original selector is still referenced for context.
        self.assertIn("data-test='accept'", msg.replace("\\'", "'"))

    def test_closed_shadow_signal_without_locator_still_points_at_aria(self) -> None:
        msg = _diagnostic_next_step(
            "New Browser    chromium    headless=True",
            ["Browser"],
            "sid-3",
            has_possible_closed_shadow_roots=True,
            possible_closed_shadow_root_count=5,
        )
        self.assertIn("snapshot_kind='aria'", msg)
        self.assertIn("closed shadow", msg.lower())


class AriaSummaryClosedShadowGuardTests(unittest.TestCase):
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

    def test_aria_summary_includes_advisory_when_session_flagged(self) -> None:
        sample_aria = SAMPLE_ARIA

        class _Stub:
            def query(self, keyword: str, args=None):  # noqa: ANN001
                if keyword == "Get Aria Snapshot":
                    return sample_aria
                raise RuntimeError(f"unexpected: {keyword}")

            def get_variables(self, keys=None):  # noqa: ANN001
                return {}

            def imported_libraries(self) -> list[str]:
                return ["BuiltIn", "Browser"]

            def close(self) -> None:
                pass

        store = LiveSessionStore()
        store.engine_factory = lambda sid, libs: _Stub()
        session_tool = build_session_tool(store)
        inspect = build_app_inspect_state_tool(store)
        sid = session_tool(action=SessionAction.OPEN, transport=TransportKind.STDIO)["session"]["session_id"]

        # Without any shadow signal: no advisory.
        first = inspect(session_id=sid, snapshot_kind=SnapshotKind.ARIA)
        self.assertNotIn("closed_shadow_advisory", first["snapshot"]["manifest"]["summary"])

        # Simulate a prior DOM snapshot that observed closed shadow roots.
        store.record_shadow_signal(sid, possible_closed_count=13)

        # Now the ARIA summary surfaces the advisory.
        second = inspect(session_id=sid, snapshot_kind=SnapshotKind.ARIA)
        summary = second["snapshot"]["manifest"]["summary"]
        self.assertIn("closed_shadow_advisory", summary)
        self.assertIn("13", summary["closed_shadow_advisory"])
        # The selector_hints field is still present — the advisory complements,
        # not replaces, the actionable hints.
        self.assertIn("selector_hints", summary)


if __name__ == "__main__":
    unittest.main()
