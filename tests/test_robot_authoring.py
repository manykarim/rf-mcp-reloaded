from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for path in [
    REPO_ROOT / "packages" / "rfmcp_core" / "src",
    REPO_ROOT / "packages" / "rfmcp_cli" / "src",
]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rfmcp_core.robot import (  # noqa: E402
    escape_comment_cells,
    hoist_imports,
    render_keyword_call_line,
    render_suite_text,
)
from rfmcp_cli.workflows.generation import _normalize_body_line  # noqa: E402
from rfmcp_cli.workflows.refactor import _normalize_body_lines  # noqa: E402


class EscapeCommentCellsTests(unittest.TestCase):
    def test_leading_hash_cell_is_escaped(self) -> None:
        self.assertEqual(
            escape_comment_cells("Fill Text    #user-name    standard_user"),
            "Fill Text    \\#user-name    standard_user",
        )

    def test_multiple_hash_cells_each_escaped(self) -> None:
        self.assertEqual(
            escape_comment_cells("Click    #a    #b"),
            "Click    \\#a    \\#b",
        )

    def test_non_leading_hash_is_literal(self) -> None:
        self.assertEqual(escape_comment_cells("Log    color=#ff0000"), "Log    color=#ff0000")

    def test_already_escaped_cell_not_doubled(self) -> None:
        self.assertEqual(escape_comment_cells("Fill Text    \\#x    y"), "Fill Text    \\#x    y")

    def test_id_and_css_strategies_unaffected(self) -> None:
        self.assertEqual(
            escape_comment_cells("Fill Text    id=user-name    bob"),
            "Fill Text    id=user-name    bob",
        )
        self.assertEqual(
            escape_comment_cells('Click    [data-test="x"]'),
            'Click    [data-test="x"]',
        )


class GenerationBodyEscapingTests(unittest.TestCase):
    def test_generation_normalize_body_line_escapes_hash_selector(self) -> None:
        # generate_suite_artifact builds its body via _normalize_body_line (generation.py).
        self.assertEqual(
            _normalize_body_line("Fill Text    #checkout-email    a@b.c"),
            "    Fill Text    \\#checkout-email    a@b.c",
        )

    def test_refactor_normalize_body_lines_escapes_hash_selector(self) -> None:
        self.assertEqual(
            _normalize_body_lines(["Click    #login-button", ""]),
            ["    Click    \\#login-button"],
        )


class HoistImportsTests(unittest.TestCase):
    def test_library_import_is_hoisted_to_settings(self) -> None:
        settings, body = hoist_imports(["Import Library    Browser", "Click    id=go"])
        self.assertEqual(settings, ["Library    Browser"])
        self.assertEqual(body, ["Click    id=go"])

    def test_library_alias_args_preserved(self) -> None:
        settings, body = hoist_imports(["Import Library    Collections    WITH NAME    Coll"])
        self.assertEqual(settings, ["Library    Collections    WITH NAME    Coll"])
        self.assertEqual(body, [])

    def test_resource_and_variables_hoisted(self) -> None:
        settings, body = hoist_imports(
            [
                "Import Resource    /tmp/x.resource",
                "Import Variables    /tmp/v.py    arg1",
                "Log    hi",
            ]
        )
        self.assertEqual(settings, ["Resource    /tmp/x.resource", "Variables    /tmp/v.py    arg1"])
        self.assertEqual(body, ["Log    hi"])

    def test_non_import_keywords_stay_in_body(self) -> None:
        settings, body = hoist_imports(["Get Text    .h    ==    Hi", "${x} =    Set Variable    1"])
        self.assertEqual(settings, [])
        self.assertEqual(body, ["Get Text    .h    ==    Hi", "${x} =    Set Variable    1"])


class EscapeIsRobotApiCorrectTests(unittest.TestCase):
    """Validate the emit-side escaping against Robot Framework's own lexer (robot.api)."""

    @staticmethod
    def _argument_cells(line: str) -> list[str]:
        import io

        from robot.api import Token, get_tokens

        data = f"*** Test Cases ***\n_\n    {line}\n"
        return [
            token.value
            for token in get_tokens(io.StringIO(data), data_only=True)
            if token.type == Token.ARGUMENT
        ]

    def test_unescaped_hash_cell_is_swallowed_as_comment(self) -> None:
        # Robot's lexer treats a leading-# cell (and the rest of the row) as a comment.
        self.assertEqual(self._argument_cells("Fill Text    #user-name    bob"), [])

    def test_escaped_hash_cell_parses_as_real_arguments(self) -> None:
        escaped = escape_comment_cells("Fill Text    #user-name    bob")
        # After escaping, robot.api parses both cells as real arguments.
        self.assertEqual(len(self._argument_cells(escaped)), 2)


class RenderKeywordCallLineTests(unittest.TestCase):
    """Canonical single-keyword-call emission via robot.api.parsing.KeywordCall.from_params."""

    def test_assignment_uses_modern_rf7_syntax_without_trailing_equals(self) -> None:
        # Input written in legacy `${x} =` style — output must be canonical RF7 (no trailing ' =').
        line = render_keyword_call_line("${r} =    Evaluate    1 + 2")
        self.assertEqual(line, "    ${r}    Evaluate    1 + 2")

    def test_hash_selector_cell_is_escaped(self) -> None:
        line = render_keyword_call_line("Click    #login-button")
        self.assertEqual(line, "    Click    \\#login-button")

    def test_control_flow_header_returns_none(self) -> None:
        self.assertIsNone(render_keyword_call_line("FOR    ${item}    IN    one    two"))
        self.assertIsNone(render_keyword_call_line("END"))
        self.assertIsNone(render_keyword_call_line("IF    ${x}"))

    def test_indented_line_returns_none(self) -> None:
        # Nested-body lines must be handled by the caller (preserve leading whitespace).
        self.assertIsNone(render_keyword_call_line("    Log    ${item}"))


class RenderSuiteTextTests(unittest.TestCase):
    """Canonical .robot emission via robot.api.parsing (File.save + from_params)."""

    def test_canonical_sections_and_modern_syntax(self) -> None:
        text = render_suite_text(
            test_case_name="Live Test",
            body_steps=[
                "Import Library    Browser    chromium    WITH NAME    Br",
                "${r} =    Evaluate    1 + 2",
                "Should Be Equal    ${r}    ${3}",
            ],
            declared_variables={"${BASE_URL}": "https://example.com"},
            suite_setup="Log    suite-up",
            test_tags=["smoke"],
            test_case_tags=["regression"],
        )
        # Section ordering + modern AS alias (not deprecated WITH NAME).
        self.assertLess(text.index("*** Settings ***"), text.index("*** Variables ***"))
        self.assertLess(text.index("*** Variables ***"), text.index("*** Test Cases ***"))
        self.assertIn("Library    Browser    chromium    AS    Br", text)
        self.assertNotIn("WITH NAME", text)
        # Assignment in canonical RF7 form (no obsolete trailing ' =').
        self.assertIn("${r}    Evaluate    1 + 2", text)
        self.assertNotIn("${r} =", text)
        # Settings entries.
        self.assertIn("Suite Setup    Log    suite-up", text)
        self.assertIn("Test Tags    smoke", text)
        # Variables section.
        self.assertIn("${BASE_URL}    https://example.com", text)
        # Per-test [Tags] inside the test case.
        self.assertIn("    [Tags]    regression", text)

    def test_hash_selector_args_are_pre_escaped(self) -> None:
        # robot.api.parsing does not escape leading-# cells; render_suite_text must.
        text = render_suite_text(
            body_steps=['Fill Text    #login-button    bob'],
        )
        self.assertIn(r"Fill Text    \#login-button    bob", text)
        # And re-parsing yields the selector as an ARGUMENT, not a comment.
        import io

        from robot.api import Token, get_tokens

        args = [t.value for t in get_tokens(io.StringIO(text), data_only=True) if t.type == Token.ARGUMENT]
        self.assertIn(r"\#login-button", args)

    def test_round_trip_with_robot_api(self) -> None:
        # The rendered text must re-parse cleanly into the same structured intent.
        text = render_suite_text(
            test_case_name="RT",
            body_steps=[
                "Import Library    Collections",
                "Log    hi",
            ],
        )
        from robot.api import TestSuite

        suite = TestSuite.from_string(text)
        # Library import present.
        libs = [imp.name for imp in suite.resource.imports if imp.type == "LIBRARY"]
        self.assertEqual(libs, ["Collections"])
        # One test case named RT with one keyword call.
        self.assertEqual([t.name for t in suite.tests], ["RT"])
        body = list(suite.tests[0].body)
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0].name, "Log")
        self.assertEqual(list(body[0].args), ["hi"])


if __name__ == "__main__":
    unittest.main()
