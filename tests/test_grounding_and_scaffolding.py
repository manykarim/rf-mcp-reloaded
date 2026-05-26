from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parent.parent
for path in [
    REPO_ROOT / "packages" / "rfmcp_core" / "src",
    REPO_ROOT / "packages" / "rfmcp_cli" / "src",
]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rfmcp_cli.main import app  # noqa: E402
from rfmcp_cli.workflows.grounding import run_grounding, scaffold_resource, scaffold_suite  # noqa: E402
from rfmcp_core.contracts import (  # noqa: E402
    ErrorEnvelope,
    ProviderFailure,
    ProvenanceKind,
    ProvenanceRecord,
    Severity,
)


def provider_failure(provider_id: str = "robotframework.browser") -> ProviderFailure:
    return ProviderFailure(
        provider_id=provider_id,
        stage="load",
        error=ErrorEnvelope(
            code="provider-contract-invalid",
            message=f"Provider '{provider_id}' failed during load.",
            severity=Severity.ERROR,
            provenance=ProvenanceRecord(
                kind=ProvenanceKind.OBSERVED,
                source=provider_id,
                source_type="provider",
                source_id=provider_id,
                provider_id=provider_id,
            ),
            retryable=False,
            suggested_next_step="Inspect the provider package and retry after correcting the provider implementation.",
        ),
    )


class GroundingAndScaffoldingTests(unittest.TestCase):
    def test_run_grounding_returns_keyword_and_library_evidence(self) -> None:
        result = run_grounding("Log")

        self.assertTrue(result.ok)
        self.assertGreaterEqual(len(result.libraries), 1)
        self.assertEqual(result.libraries[0].name, "BuiltIn")
        self.assertTrue(any(keyword.keyword_name == "Log" for keyword in result.keywords))
        self.assertEqual(result.provider_failures, [])

    def test_run_grounding_surfaces_provider_failures_on_success(self) -> None:
        failure = provider_failure()
        with patch("rfmcp_cli.workflows.grounding.ProviderPluginManager.load_providers", return_value=([], [failure])):
            result = run_grounding("BuiltIn")

        self.assertTrue(result.ok)
        self.assertEqual(result.provider_failures, [failure])
        self.assertEqual(result.libraries[0].name, "BuiltIn")

    def test_run_grounding_returns_structured_failure_for_missing_query(self) -> None:
        result = run_grounding("NoSuchKeywordForGrounding")

        self.assertFalse(result.ok)
        self.assertIsNotNone(result.error)
        self.assertEqual(result.error.code, "no-grounding-matches")
        self.assertEqual(result.error.details["query"], "NoSuchKeywordForGrounding")

    def test_run_grounding_honors_library_filter(self) -> None:
        result = run_grounding("Log", libraries=["BuiltIn"])

        self.assertTrue(result.ok)
        self.assertEqual([library.name for library in result.libraries], ["BuiltIn"])
        self.assertTrue(result.keywords)
        self.assertTrue(all(keyword.library_name == "BuiltIn" for keyword in result.keywords))

    def test_run_grounding_returns_failure_when_library_filter_removes_matches(self) -> None:
        result = run_grounding("Log", libraries=["String"])

        self.assertFalse(result.ok)
        self.assertIsNotNone(result.error)
        self.assertEqual(result.error.code, "no-grounding-matches")

    def test_scaffold_suite_creates_deterministic_valid_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "example_suite.robot"
            result = scaffold_suite(
                str(target),
                libraries=["Browser", "BuiltIn", "Browser"],
                resources=["common.resource", "common.resource"],
            )
            written_content = target.read_text()

        self.assertTrue(result.ok)
        self.assertTrue(result.created)
        self.assertFalse(result.overwritten)
        self.assertTrue(result.artifact.validation.ok)
        self.assertEqual(
            result.artifact.content,
            "\n".join(
                [
                    "*** Settings ***",
                    "Documentation    Scaffolded suite for Example Suite.",
                    "Library    BuiltIn",
                    "Library    Browser",
                    "Resource    common.resource",
                    "",
                    "*** Test Cases ***",
                    "Smoke Test",
                    "    No Operation",
                    "",
                ]
            ),
        )
        self.assertEqual(written_content, result.artifact.content)
        self.assertTrue(any(candidate.hint_id.startswith("browser-provider-") for candidate in result.preventive_guidance))

    def test_scaffold_resource_creates_keyword_starter(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "helpers.resource"
            result = scaffold_resource(str(target), keyword_name="user_login")
            self.assertEqual(target.read_text(), result.artifact.content)

        self.assertTrue(result.ok)
        self.assertTrue(result.artifact.validation.ok)
        self.assertIn("*** Keywords ***", result.artifact.content)
        self.assertIn("User Login", result.artifact.content)
        self.assertTrue(any(candidate.hint_id == "inferred-resource-grounding-next-step" for candidate in result.preventive_guidance))

    def test_scaffold_suite_rejects_existing_target_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "existing.robot"
            target.write_text("*** Test Cases ***\nExisting\n    Log    hello\n")
            result = scaffold_suite(str(target))
            current_content = target.read_text()

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "target-exists")
        self.assertEqual(current_content, "*** Test Cases ***\nExisting\n    Log    hello\n")

    def test_scaffold_suite_force_overwrites_existing_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "existing.robot"
            target.write_text("*** Test Cases ***\nExisting\n    Log    hello\n")
            result = scaffold_suite(str(target), force=True)
            overwritten_content = target.read_text()

        self.assertTrue(result.ok)
        self.assertFalse(result.created)
        self.assertTrue(result.overwritten)
        self.assertEqual(overwritten_content, result.artifact.content)
        self.assertIn("Smoke Test", overwritten_content)

    def test_scaffold_rejects_non_robot_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "suite.txt"
            result = scaffold_suite(str(target))

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "unsupported-extension")

    def test_ground_command_json_output_is_machine_readable(self) -> None:
        runner = CliRunner()

        result = runner.invoke(app, ["ground", "Log", "--json"])

        self.assertEqual(result.exit_code, 0)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["query"], "Log")
        self.assertTrue(any(keyword["keyword_name"] == "Log" for keyword in payload["keywords"]))

    def test_scaffold_suite_command_json_output_is_machine_readable(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "generated.robot"
            result = runner.invoke(
                app,
                [
                    "scaffold-suite",
                    str(target),
                    "--library",
                    "Browser",
                    "--resource",
                    "shared.resource",
                    "--json",
                ],
            )

            self.assertEqual(result.exit_code, 0)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ok"])
            self.assertTrue(payload["artifact"]["validation"]["ok"])
            self.assertEqual(payload["artifact"]["kind"], "suite")
            self.assertEqual(payload["artifact"]["path"], str(target))
            self.assertIn("Library    Browser", payload["artifact"]["content"])

    def test_scaffold_resource_command_human_output_reports_failures(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "helpers.txt"
            result = runner.invoke(app, ["scaffold-resource", str(target)])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("unsupported-extension", result.stdout)
        self.assertIn("Scaffold target:", result.stdout)


if __name__ == "__main__":
    unittest.main()
