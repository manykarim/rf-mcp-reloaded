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

from rfmcp_cli.commands.validate import run_validate  # noqa: E402
from rfmcp_cli.main import app  # noqa: E402


class ValidateCommandTests(unittest.TestCase):
    def test_run_validate_surfaces_bootstrap_failure(self) -> None:
        with patch("rfmcp_cli.commands.validate.verify_environment") as verify_environment:
            verify_environment.return_value = [
                type(
                    "BootstrapError",
                    (),
                    {
                        "check": "uv-version",
                        "actual": "0.9.26",
                        "expected": "0.11.16",
                        "next_step": "Install uv 0.11.16",
                    },
                )()
            ]
            result = run_validate("tests/fixture.robot")

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "bootstrap-uv-version")

    def test_cli_json_output_is_machine_readable(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            robot_file = Path(tmpdir) / "suite.robot"
            robot_file.write_text("*** Test Cases ***\nExample\n    Log    hello\n")
            with patch("rfmcp_cli.commands.validate.verify_environment", return_value=[]):
                result = runner.invoke(app, ["validate", str(robot_file), "--json"])

        self.assertEqual(result.exit_code, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["target"], str(robot_file))
        self.assertTrue(payload["ok"])

    def test_cli_human_output_reports_missing_section(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            robot_file = Path(tmpdir) / "suite.robot"
            robot_file.write_text("Just text\n")
            with patch("rfmcp_cli.commands.validate.verify_environment", return_value=[]):
                result = runner.invoke(app, ["validate", str(robot_file)])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("missing-required-section", result.stdout)


if __name__ == "__main__":
    unittest.main()
