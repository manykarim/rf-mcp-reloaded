"""Tests for the shadow-piercing helper (cross-review proposal #2 refined).

When a Browser step fails with a flat CSS selector AND the session has
ARIA-derived role locators from a prior ``app_inspect_state(snapshot_kind='aria')``
capture, ``_diagnostic_next_step`` matches the failed selector against those
hints and suggests a role-locator alternative the agent can paste directly.

The reviewer-mandated guard: when the session has observed possibly-closed
shadow roots, the closed-shadow advisory takes precedence and the role-locator
suggestion is suppressed (role= selectors can't enter closed roots either).
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
from rfmcp_core.runtime.stepper import (  # noqa: E402
    _aria_locator_alternative,
    _diagnostic_next_step,
    _tokenize_selector,
)
from rfmcp_mcp.tools.app_inspect_state import build_app_inspect_state_tool  # noqa: E402
from rfmcp_mcp.tools.rf_session import build_session_tool  # noqa: E402


SAMPLE_HINTS = [
    {"role": "button", "name": "Accept All", "locator": 'role=button[name="Accept All"]'},
    {"role": "button", "name": "Reject All", "locator": 'role=button[name="Reject All"]'},
    {"role": "textbox", "name": "Origin", "locator": 'role=textbox[name="Origin"]'},
    {"role": "textbox", "name": "Destination", "locator": 'role=textbox[name="Destination"]'},
    {"role": "link", "name": "Sign In", "locator": 'role=link[name="Sign In"]'},
]


class TokenizeSelectorTests(unittest.TestCase):
    def test_attribute_selector_yields_meaningful_tokens(self) -> None:
        # Vendor prefix 'uc-' and generic 'button' get filtered as noise.
        tokens = _tokenize_selector('[data-test-id="uc-accept-all-button"]')
        # 'accept' survives; 'uc', 'all', 'button' are noise.
        self.assertIn("accept", tokens)
        self.assertNotIn("uc", tokens)
        self.assertNotIn("button", tokens)

    def test_text_selector_passes_through_words(self) -> None:
        tokens = _tokenize_selector("text=Origin City")
        self.assertIn("origin", tokens)
        self.assertIn("city", tokens)

    def test_plain_css_class_falls_back_to_split(self) -> None:
        tokens = _tokenize_selector(".sign-in-link")
        self.assertIn("sign", tokens)
        # 'link' is noise — skipped.
        self.assertNotIn("link", tokens)

    def test_pure_noise_selector_returns_no_tokens(self) -> None:
        # All tokens get filtered → empty list. Matcher should return None.
        tokens = _tokenize_selector("[class=btn]")
        self.assertEqual(tokens, [])


class AriaLocatorAlternativeTests(unittest.TestCase):
    def test_matches_accept_button_by_overlapping_token(self) -> None:
        alt = _aria_locator_alternative(
            '[data-test-id="uc-accept-all-button"]', SAMPLE_HINTS
        )
        self.assertIsNotNone(alt)
        self.assertEqual(alt["role"], "button")
        self.assertEqual(alt["name"], "Accept All")
        self.assertEqual(alt["locator"], 'role=button[name="Accept All"]')

    def test_matches_origin_textbox_by_text_keyword(self) -> None:
        alt = _aria_locator_alternative("text=Origin Address", SAMPLE_HINTS)
        self.assertIsNotNone(alt)
        self.assertEqual(alt["role"], "textbox")
        self.assertEqual(alt["name"], "Origin")

    def test_no_match_returns_none(self) -> None:
        alt = _aria_locator_alternative('[data-test-id="some-totally-unrelated"]', SAMPLE_HINTS)
        self.assertIsNone(alt)

    def test_empty_hints_returns_none(self) -> None:
        alt = _aria_locator_alternative("[data-test-id=accept]", [])
        self.assertIsNone(alt)

    def test_pure_noise_selector_returns_none(self) -> None:
        # Selector tokenizes to nothing — nothing to match against.
        alt = _aria_locator_alternative(".btn", SAMPLE_HINTS)
        self.assertIsNone(alt)


class DiagnosticIntegrationTests(unittest.TestCase):
    def test_suggestion_includes_role_locator_when_hint_matches(self) -> None:
        msg = _diagnostic_next_step(
            'Click    [data-test-id="uc-accept-all-button"]',
            ["Browser"],
            "sid-1",
            aria_selector_hints=SAMPLE_HINTS,
        )
        # The original dom_selector advice stays as the primary suggestion.
        self.assertIn("snapshot_kind='dom_selector'", msg)
        # The role-locator alternative is appended.
        self.assertIn('role=button[name="Accept All"]', msg)
        self.assertIn("matched ARIA hint", msg)

    def test_no_role_locator_when_no_aria_hint_matches(self) -> None:
        msg = _diagnostic_next_step(
            "Click    #completely-unrelated-element",
            ["Browser"],
            "sid-2",
            aria_selector_hints=SAMPLE_HINTS,
        )
        self.assertIn("snapshot_kind='dom_selector'", msg)
        # No role-locator hint surfaced.
        self.assertNotIn("matched ARIA hint", msg)

    def test_closed_shadow_signal_suppresses_role_locator_hint(self) -> None:
        # Reviewer-mandated guard: when closed shadow is suspected, do NOT
        # suggest a role-locator alternative (role= selectors can't enter
        # closed roots either). The closed-shadow advisory takes over.
        msg = _diagnostic_next_step(
            'Click    [data-test-id="uc-accept-all-button"]',
            ["Browser"],
            "sid-3",
            has_possible_closed_shadow_roots=True,
            possible_closed_shadow_root_count=13,
            aria_selector_hints=SAMPLE_HINTS,
        )
        # Closed-shadow advisory present.
        self.assertIn("closed shadow", msg.lower())
        # Role-locator NOT suggested under this path.
        self.assertNotIn('role=button[name="Accept All"]', msg)
        self.assertNotIn("matched ARIA hint", msg)


class StorePersistenceTests(unittest.TestCase):
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

    def test_aria_capture_promotes_selector_hints_into_session(self) -> None:
        # Stub engine returning a small ARIA tree with two labeled interactive nodes.
        sample = (
            "- document:\n"
            "  - main:\n"
            '    - button "Accept All"\n'
            '    - textbox "Origin"\n'
        )

        class _Stub:
            def query(self, keyword: str, args=None):  # noqa: ANN001
                if keyword == "Get Aria Snapshot":
                    return sample
                raise RuntimeError(keyword)

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

        # Pre-capture: no hints on record.
        self.assertEqual(store.get_record(sid).latest_aria_selector_hints, [])

        # Take ARIA snapshot — should land hints on the session record.
        result = inspect(session_id=sid, snapshot_kind=SnapshotKind.ARIA)
        self.assertTrue(result["ok"])

        hints = store.get_record(sid).latest_aria_selector_hints
        names = {h["name"] for h in hints}
        self.assertEqual(names, {"Accept All", "Origin"})

    def test_aria_hint_persistence_does_not_bump_version(self) -> None:
        # Helper state shouldn't trigger delta-get traffic.
        sample = '- button "Save"\n'

        class _Stub:
            def query(self, keyword: str, args=None):  # noqa: ANN001
                if keyword == "Get Aria Snapshot":
                    return sample
                raise RuntimeError(keyword)

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

        before = session_tool(action=SessionAction.GET, session_id=sid)["session"]["version"]
        inspect(session_id=sid, snapshot_kind=SnapshotKind.ARIA)
        after = session_tool(action=SessionAction.GET, session_id=sid)["session"]["version"]
        # Version unchanged — hints are helper state, not session-visible content.
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
