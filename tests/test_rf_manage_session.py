from __future__ import annotations

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

from rfmcp_core.runtime.session import LiveSessionStore  # noqa: E402
from rfmcp_mcp.tools._registry import ALLOWLISTED_TOOL_NAMES, MAX_USER_FACING_TOOLS  # noqa: E402
from rfmcp_mcp.tools.rf_manage_session import build_manage_session_tool  # noqa: E402
from rfmcp_mcp.tools.rf_open_session import build_open_session_tool  # noqa: E402


def _open(store: LiveSessionStore) -> str:
    return build_open_session_tool(store)("stdio")["session"]["session_id"]


class ManageSessionAllowlistTests(unittest.TestCase):
    def test_allowlist_includes_rf_manage_session_within_cap(self) -> None:
        self.assertIn("rf_manage_session", ALLOWLISTED_TOOL_NAMES)
        self.assertLessEqual(len(ALLOWLISTED_TOOL_NAMES), MAX_USER_FACING_TOOLS)


class ManageSessionImportTests(unittest.TestCase):
    def test_import_library_routes_through_stepper_and_records_step(self) -> None:
        store = LiveSessionStore()
        manage = build_manage_session_tool(store)
        session_id = _open(store)

        result = manage(session_id, "import_library", name="Collections", alias="Coll")
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["action"], "import_library")
        self.assertEqual(
            result["instruction"], "Import Library    Collections    WITH NAME    Coll"
        )
        # The step is recorded on the session so the suite-builder can hoist it.
        self.assertIn(
            "Import Library    Collections    WITH NAME    Coll",
            store.get_record(session_id).steps,
        )

    def test_import_resource_routes_through_stepper(self) -> None:
        store = LiveSessionStore()
        manage = build_manage_session_tool(store)
        session_id = _open(store)
        with tempfile.NamedTemporaryFile("w", suffix=".resource", delete=False) as handle:
            handle.write(
                "*** Variables ***\n${RES_VAR}    from-resource\n"
                "*** Keywords ***\nResource Greet\n    RETURN    hi\n"
            )
            resource_path = handle.name
        try:
            result = manage(session_id, "import_resource", name=resource_path)
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["instruction"], f"Import Resource    {resource_path}")
        finally:
            Path(resource_path).unlink(missing_ok=True)

    def test_alias_on_non_library_is_rejected(self) -> None:
        store = LiveSessionStore()
        manage = build_manage_session_tool(store)
        session_id = _open(store)
        result = manage(session_id, "import_resource", name="/tmp/x.resource", alias="bad")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "unsupported-alias")


class ManageSessionVariablesTests(unittest.TestCase):
    def test_set_variable_tracks_declaration_and_writes_live(self) -> None:
        store = LiveSessionStore()
        manage = build_manage_session_tool(store)
        session_id = _open(store)

        result = manage(session_id, "set_variable", name="${BASE_URL}", value="https://example.com")
        self.assertTrue(result["ok"])
        self.assertEqual(result["value"], "https://example.com")
        # Tracked for *** Variables *** hoist.
        self.assertEqual(
            store.get_record(session_id).declared_variables["${BASE_URL}"],
            "https://example.com",
        )
        # And available via get_variable (declared scope).
        got = manage(session_id, "get_variable", name="${BASE_URL}")
        self.assertTrue(got["ok"])
        self.assertEqual(got["scope"], "declared")
        self.assertEqual(got["value"], "https://example.com")

    def test_set_variable_rejects_invalid_name(self) -> None:
        store = LiveSessionStore()
        manage = build_manage_session_tool(store)
        session_id = _open(store)
        result = manage(session_id, "set_variable", name="NOBRACES", value=1)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "invalid-context-key")

    def test_get_variable_falls_back_to_live_namespace(self) -> None:
        # A variable set via the engine (e.g., by a keyword) is readable via get_variable too.
        store = LiveSessionStore()
        manage = build_manage_session_tool(store)
        session_id = _open(store)
        engine = store.get_or_create_engine(session_id)
        engine.set_variable("${LIVE}", 42)
        got = manage(session_id, "get_variable", name="${LIVE}")
        self.assertTrue(got["ok"])
        self.assertEqual(got["value"], 42)
        # Either scope is acceptable here (live-set vars also land in _assigned).
        self.assertIn(got["scope"], {"declared", "live"})


class ManageSessionSettingsTests(unittest.TestCase):
    def test_set_setup_teardown_records_per_scope(self) -> None:
        store = LiveSessionStore()
        manage = build_manage_session_tool(store)
        session_id = _open(store)

        manage(session_id, "set_setup", scope="suite", value="Open Browser    chromium")
        manage(session_id, "set_teardown", scope="suite", value="Close Browser")
        manage(session_id, "set_setup", scope="test", value="Log    test-setup")
        manage(session_id, "set_teardown", scope="test_case", value="Log    case-teardown")

        record = store.get_record(session_id)
        self.assertEqual(record.suite_setup, "Open Browser    chromium")
        self.assertEqual(record.suite_teardown, "Close Browser")
        self.assertEqual(record.test_setup, "Log    test-setup")
        self.assertEqual(record.test_case_teardown, "Log    case-teardown")

    def test_set_tags_supports_suite_and_test_case_scope(self) -> None:
        store = LiveSessionStore()
        manage = build_manage_session_tool(store)
        session_id = _open(store)

        manage(session_id, "set_tags", scope="suite", tags=["smoke", "cart"])
        manage(session_id, "set_tags", scope="test_case", tags=["regression"])

        record = store.get_record(session_id)
        self.assertEqual(record.test_tags, ["smoke", "cart"])
        self.assertEqual(record.test_case_tags, ["regression"])

    def test_unsupported_action_is_structured(self) -> None:
        store = LiveSessionStore()
        manage = build_manage_session_tool(store)
        session_id = _open(store)
        result = manage(session_id, "delete_universe")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "unsupported-action")

    def test_set_tags_requires_non_empty_string_list(self) -> None:
        store = LiveSessionStore()
        manage = build_manage_session_tool(store)
        session_id = _open(store)
        result = manage(session_id, "set_tags", scope="suite", tags=[])
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "missing-target")


class ManageSessionRenderingTests(unittest.TestCase):
    """The manifest collected by rf_manage_session renders into the final suite."""

    def test_render_pipeline_emits_settings_variables_and_test_case_settings(self) -> None:
        from rfmcp_core.robot import (
            hoist_imports,
            render_session_settings,
            render_test_case_settings,
            render_variables_section,
        )

        store = LiveSessionStore()
        manage = build_manage_session_tool(store)
        session_id = _open(store)

        # Import (recorded → hoist), Variables section, Settings setup/teardown/tags, per-test [Tags].
        manage(session_id, "import_library", name="Collections")
        manage(session_id, "set_variable", name="${BASE_URL}", value="https://example.com")
        manage(session_id, "set_setup", scope="suite", value="Log    suite-setup")
        manage(session_id, "set_teardown", scope="suite", value="Log    suite-teardown")
        manage(session_id, "set_tags", scope="suite", tags=["smoke"])
        manage(session_id, "set_tags", scope="test_case", tags=["cart"])

        record = store.get_record(session_id)
        imports, _body = hoist_imports(list(record.steps))
        settings_extra = render_session_settings(
            suite_setup=record.suite_setup,
            suite_teardown=record.suite_teardown,
            test_setup=record.test_setup,
            test_teardown=record.test_teardown,
            test_tags=record.test_tags,
        )
        variables = render_variables_section(record.declared_variables)
        case_settings = render_test_case_settings(
            setup=record.test_case_setup,
            teardown=record.test_case_teardown,
            tags=record.test_case_tags,
        )

        self.assertIn("Library    Collections", imports)
        self.assertEqual(
            settings_extra,
            [
                "Suite Setup    Log    suite-setup",
                "Suite Teardown    Log    suite-teardown",
                "Test Tags    smoke",
            ],
        )
        self.assertEqual(variables, ["${BASE_URL}    https://example.com"])
        self.assertEqual(case_settings, ["    [Tags]    cart"])


if __name__ == "__main__":
    unittest.main()
