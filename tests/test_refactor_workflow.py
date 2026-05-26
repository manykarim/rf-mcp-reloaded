from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from typer.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parent.parent
for path in [
    REPO_ROOT / "packages" / "rfmcp_core" / "src",
    REPO_ROOT / "packages" / "rfmcp_cli" / "src",
]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rfmcp_cli.main import app  # noqa: E402
from rfmcp_cli.workflows.refactor import regenerate_existing_artifact, refactor_existing_artifact  # noqa: E402


class RefactorWorkflowTests(unittest.TestCase):
    def test_refactor_suite_reports_changes_and_runnable_proof(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "suite.robot"
            target.write_text(
                "*** Settings ***\n"
                "Documentation    Original suite.\n\n"
                "*** Test Cases ***\n"
                "Old Name\n"
                "    Set Test Variable    ${message}    hello\n"
                "    Log    ${message}\n"
            )
            result = refactor_existing_artifact(
                str(target),
                rename_to="New Name",
                documentation="Updated suite.",
                steps=["Log To Console    updated"],
                assertions=["Should Be Equal As Strings    ${message}    hello"],
            )
            written = target.read_text()

        self.assertTrue(result.ok)
        self.assertTrue(result.validation.ok)
        self.assertEqual(result.run_verification.status, "passed")
        self.assertIn("New Name", written)
        self.assertIn("Updated suite.", written)
        self.assertTrue(any(change.kind == "rename" for change in result.changes))
        self.assertTrue(any(change.kind == "append-body-line" for change in result.changes))
        self.assertFalse(result.manual_follow_up)

    def test_regenerate_suite_replaces_body_and_stays_runnable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "suite.robot"
            target.write_text(
                "*** Test Cases ***\n"
                "Example\n"
                "    Log    old value\n"
            )
            result = regenerate_existing_artifact(
                str(target),
                rename_to="Generated Name",
                documentation="Regenerated suite.",
                steps=["Set Test Variable    ${message}    hello"],
                assertions=["Should Be Equal As Strings    ${message}    hello"],
            )
            written = target.read_text()

        self.assertTrue(result.ok)
        self.assertEqual(result.run_verification.status, "passed")
        self.assertIn("*** Settings ***", written)
        self.assertIn("Documentation    Regenerated suite.", written)
        self.assertIn("Generated Name", written)
        self.assertIn("Should Be Equal As Strings    ${message}    hello", written)
        self.assertIn("---", result.artifact.diff)

    def test_refactor_resource_returns_manual_follow_up(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "helpers.resource"
            target.write_text(
                "*** Keywords ***\n"
                "Example Keyword\n"
                "    Log    hello\n"
            )
            result = refactor_existing_artifact(
                str(target),
                rename_to="Updated Keyword",
                steps=["Log    again"],
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.run_verification.status, "not-applicable")
        self.assertTrue(result.manual_follow_up)
        self.assertIn("imports", result.manual_follow_up[0])

    def test_regenerate_suite_failure_surfaces_diagnostics_and_hints(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "browser.robot"
            original_content = (
                "*** Test Cases ***\n"
                "Browser Test\n"
                "    Log    hello\n"
            )
            target.write_text(original_content)
            result = regenerate_existing_artifact(
                str(target),
                steps=["New Page    https://example.com"],
            )
            written = target.read_text()

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "refactor-run-failed")
        self.assertIsNotNone(result.diagnostics)
        self.assertIsNotNone(result.hint_resolution)
        self.assertIn("rfmcp repair-diagnostics", result.correction_path[1])
        self.assertEqual(written, original_content)
        self.assertTrue(any("rolled back on disk" in item for item in result.manual_follow_up))

    def test_refactor_command_json_output_is_machine_readable(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "suite.robot"
            target.write_text(
                "*** Test Cases ***\n"
                "Example\n"
                "    Log    hello\n"
            )
            result = runner.invoke(
                app,
                [
                    "refactor",
                    str(target),
                    "--rename-to",
                    "Updated",
                    "--add-step",
                    "Log To Console    updated",
                    "--json",
                ],
            )

        self.assertEqual(result.exit_code, 0)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["request"]["mode"], "refactor")
        self.assertTrue(payload["changes"])

    def test_regenerate_command_json_output_is_machine_readable(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "suite.robot"
            target.write_text(
                "*** Test Cases ***\n"
                "Example\n"
                "    Log    hello\n"
            )
            result = runner.invoke(
                app,
                [
                    "regenerate",
                    str(target),
                    "--step",
                    "Log To Console    updated",
                    "--json",
                ],
            )

        self.assertEqual(result.exit_code, 0)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["request"]["mode"], "regenerate")
        self.assertTrue(payload["changes"])

    def test_refactor_requires_at_least_one_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "suite.robot"
            target.write_text(
                "*** Test Cases ***\n"
                "Example\n"
                "    Log    hello\n"
            )
            result = refactor_existing_artifact(str(target))

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "missing-refactor-input")

    def test_regenerate_requires_non_empty_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "suite.robot"
            target.write_text(
                "*** Test Cases ***\n"
                "Example\n"
                "    Log    hello\n"
            )
            result = regenerate_existing_artifact(str(target), steps=["  "], assertions=["\t"])

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "missing-regenerate-input")

    def test_refactor_preserves_missing_trailing_newline(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "suite.robot"
            target.write_text(
                "*** Test Cases ***\n"
                "Example\n"
                "    Log    hello",
                encoding="utf-8",
            )
            result = refactor_existing_artifact(
                str(target),
                steps=["Log To Console    updated"],
            )
            written = target.read_text(encoding="utf-8")

        self.assertTrue(result.ok)
        self.assertFalse(written.endswith("\n"))
        self.assertIn("Log To Console    updated", written)

    def test_refactor_supports_tasks_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "tasks.robot"
            target.write_text(
                "*** Tasks ***\n"
                "Example Task\n"
                "    Log    hello\n",
                encoding="utf-8",
            )
            result = refactor_existing_artifact(
                str(target),
                rename_to="Updated Task",
                steps=["Log To Console    updated"],
            )
            written = target.read_text(encoding="utf-8")

        self.assertTrue(result.ok)
        self.assertTrue(result.validation.ok)
        self.assertEqual(result.run_verification.status, "passed")
        self.assertIn("Updated Task", written)
        self.assertIn("Log To Console    updated", written)

    def test_regenerate_preserves_nested_robot_indentation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "loop.robot"
            target.write_text(
                "*** Test Cases ***\n"
                "Example\n"
                "    Log    hello\n",
                encoding="utf-8",
            )
            result = regenerate_existing_artifact(
                str(target),
                steps=[
                    "FOR    ${item}    IN    one    two",
                    "    Log    ${item}",
                    "END",
                ],
            )
            written = target.read_text(encoding="utf-8")

        self.assertTrue(result.ok)
        self.assertEqual(result.run_verification.status, "passed")
        self.assertIn("    FOR    ${item}    IN    one    two", written)
        self.assertIn("        Log    ${item}", written)
        self.assertIn("    END", written)

    def test_refactor_rejects_malformed_replace_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "suite.robot"
            target.write_text(
                "*** Test Cases ***\n"
                "Example\n"
                "    Log    hello\n",
                encoding="utf-8",
            )
            result = refactor_existing_artifact(
                str(target),
                replace=["Log    hello"],
            )

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "invalid-replace-input")

    def test_refactor_replace_happy_path_updates_matching_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "suite.robot"
            target.write_text(
                "*** Test Cases ***\n"
                "Example\n"
                "    Log    hello\n",
                encoding="utf-8",
            )
            result = refactor_existing_artifact(
                str(target),
                replace=["Log    hello=Log    updated"],
            )
            written = target.read_text(encoding="utf-8")

        self.assertTrue(result.ok)
        self.assertEqual(result.run_verification.status, "passed")
        self.assertIn("Log    updated", written)
        self.assertTrue(any(change.kind == "replace-body-line" for change in result.changes))

    def test_refactor_reports_replace_targets_that_do_not_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "suite.robot"
            original_content = (
                "*** Test Cases ***\n"
                "Example\n"
                "    Log    hello\n"
            )
            target.write_text(original_content, encoding="utf-8")
            result = refactor_existing_artifact(
                str(target),
                replace=["No Match=Updated"],
            )
            written = target.read_text(encoding="utf-8")

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "replace-target-not-found")
        self.assertEqual(written, original_content)

    def test_refactor_documentation_uses_existing_settings_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "suite.robot"
            target.write_text(
                "*** Settings ***\n"
                "Library    OperatingSystem\n\n"
                "*** Test Cases ***\n"
                "Example\n"
                "    Log    hello\n",
                encoding="utf-8",
            )
            result = refactor_existing_artifact(
                str(target),
                documentation="Updated suite.",
                steps=["Log To Console    updated"],
            )
            written = target.read_text(encoding="utf-8")

        self.assertTrue(result.ok)
        self.assertEqual(written.count("*** Settings ***"), 1)
        self.assertIn("Documentation    Updated suite.", written)

    def test_refactor_documentation_only_is_treated_as_a_valid_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "suite.robot"
            target.write_text(
                "*** Settings ***\n"
                "Library    OperatingSystem\n\n"
                "*** Test Cases ***\n"
                "Example\n"
                "    Log    hello\n",
                encoding="utf-8",
            )
            result = refactor_existing_artifact(
                str(target),
                documentation="Documentation only update.",
            )
            written = target.read_text(encoding="utf-8")

        self.assertTrue(result.ok)
        self.assertEqual(result.run_verification.status, "passed")
        self.assertIn("Documentation    Documentation only update.", written)

    def test_refactor_path_not_found_is_structured(self) -> None:
        result = refactor_existing_artifact("/tmp/definitely-missing.robot", rename_to="Updated")

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "path-not-found")

    def test_refactor_empty_artifact_is_structured(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "empty.robot"
            target.write_text("", encoding="utf-8")
            result = refactor_existing_artifact(str(target), rename_to="Updated")

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "empty-artifact")


if __name__ == "__main__":
    unittest.main()
