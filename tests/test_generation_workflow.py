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
from rfmcp_cli.workflows.generation import generate_suite_artifact  # noqa: E402
from rfmcp_core.contracts import ScaffoldArtifact, ScaffoldResult, ValidationResult  # noqa: E402


class GenerationWorkflowTests(unittest.TestCase):
    def test_generate_suite_success_produces_runnable_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "generated.robot"
            result = generate_suite_artifact(
                str(target),
                tasks=["verify greeting output"],
                steps=[
                    "Set Test Variable    ${message}    hello",
                    "Log    ${message}",
                ],
                assertions=["Should Be Equal As Strings    ${message}    hello"],
                test_case_name="Greeting Proof",
            )

            written = target.read_text()

        self.assertTrue(result.ok)
        self.assertTrue(result.artifact.validation.ok)
        self.assertTrue(result.execution.ok)
        self.assertIn("Greeting Proof", written)
        self.assertIn("Set Test Variable    ${message}    hello", written)
        self.assertTrue(result.evidence)
        self.assertTrue(all(item.fulfilled for item in result.evidence))
        self.assertEqual(result.correction_path, [])

    def test_generate_command_json_output_is_machine_readable(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "generated.robot"
            result = runner.invoke(
                app,
                [
                    "generate",
                    str(target),
                    "--task",
                    "verify greeting output",
                    "--step",
                    "Set Test Variable    ${message}    hello",
                    "--assertion",
                    "Should Be Equal As Strings    ${message}    hello",
                    "--json",
                ],
            )

        self.assertEqual(result.exit_code, 0)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["execution"]["ok"])
        self.assertEqual(payload["artifact"]["kind"], "suite")
        self.assertTrue(any(item["kind"] == "assertion" for item in payload["evidence"]))

    def test_generate_suite_failure_surfaces_diagnostics_and_hints(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "browser_failure.robot"
            result = generate_suite_artifact(
                str(target),
                tasks=["open a browser page"],
                steps=["New Page    https://example.com"],
            )

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "generation-run-failed")
        self.assertFalse(result.execution.ok)
        self.assertIsNotNone(result.diagnostics)
        self.assertIsNotNone(result.hint_resolution)
        self.assertIn("rfmcp repair-diagnostics", result.correction_path[1])
        self.assertTrue(result.hint_resolution.hint.candidates)

    def test_generate_requires_step_or_assertion(self) -> None:
        result = generate_suite_artifact("missing.robot", tasks=["empty generation"])

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "missing-generation-input")
        self.assertEqual(result.execution.command, [])

    def test_generate_rejects_whitespace_only_body_requests(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "missing.robot"
            result = generate_suite_artifact(str(target), steps=["   "], assertions=["\t"])

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "missing-generation-input")

    def test_generate_propagates_scaffold_failure_for_unsupported_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "generated.txt"
            result = generate_suite_artifact(
                str(target),
                steps=["Log    hello"],
            )

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "unsupported-extension")

    def test_generate_reports_injection_failure_when_placeholder_is_missing(self) -> None:
        scaffold_result = ScaffoldResult(
            ok=True,
            artifact=ScaffoldArtifact(
                path="broken.robot",
                kind="suite",
                content="*** Test Cases ***\nGenerated Test\n    Log    hello\n",
                validation=ValidationResult(ok=True, target="broken.robot"),
            ),
            preventive_guidance=[],
            created=True,
            overwritten=False,
        )
        with patch("rfmcp_cli.workflows.generation.scaffold_suite", return_value=scaffold_result):
            result = generate_suite_artifact("broken.robot", steps=["Log    hello"])

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "generation-injection-failed")

    def test_scaffold_result_rejects_created_and_overwritten_together(self) -> None:
        with self.assertRaises(ValueError):
            ScaffoldResult(
                ok=True,
                artifact=ScaffoldArtifact(
                    path="broken.robot",
                    kind="suite",
                    content="*** Test Cases ***\nExample\n    Log    hello\n",
                    validation=ValidationResult(ok=True, target="broken.robot"),
                ),
                preventive_guidance=[],
                created=True,
                overwritten=True,
            )


if __name__ == "__main__":
    unittest.main()
