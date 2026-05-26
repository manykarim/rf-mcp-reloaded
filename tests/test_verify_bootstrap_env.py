from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts import verify_bootstrap_env
from rfmcp_core.utils import bootstrap


class VerifyBootstrapEnvTests(unittest.TestCase):
    def test_parse_uv_version_extracts_semver(self) -> None:
        self.assertEqual(verify_bootstrap_env._parse_uv_version("uv 0.11.16"), "0.11.16")

    def test_verify_environment_returns_no_errors_for_matching_versions(self) -> None:
        with (
            patch.object(bootstrap, "python_in_supported_range", return_value=True),
            patch.object(bootstrap, "python_pin_matches", return_value=True),
            patch.object(bootstrap, "python_version_string", return_value="3.11.7"),
            patch.object(
                bootstrap,
                "run_uv_version",
                return_value=(verify_bootstrap_env.REQUIRED_UV_VERSION, "uv 0.11.16"),
            ),
        ):
            self.assertEqual(verify_bootstrap_env.verify_environment(), [])

    def test_verify_environment_reports_python_pin_and_uv_mismatch(self) -> None:
        with (
            patch.object(bootstrap, "python_in_supported_range", return_value=True),
            patch.object(bootstrap, "python_pin_matches", return_value=False),
            patch.object(bootstrap, "python_version_string", return_value="3.12.3"),
            patch.object(bootstrap, "run_uv_version", return_value=("0.9.26", "uv 0.9.26")),
        ):
            errors = verify_bootstrap_env.verify_environment()

        self.assertEqual([error.check for error in errors], ["python-pin", "uv-version"])
        self.assertIn("Activate Python 3.11", errors[0].next_step)
        self.assertIn("uv 0.11.16", errors[1].next_step)

    def test_verify_environment_checks_workspace_root_relative_to_script(self) -> None:
        with (
            patch.object(bootstrap, "python_in_supported_range", return_value=True),
            patch.object(bootstrap, "python_pin_matches", return_value=True),
            patch.object(
                bootstrap,
                "run_uv_version",
                return_value=(verify_bootstrap_env.REQUIRED_UV_VERSION, "uv 0.11.16"),
            ),
        ):
            errors = verify_bootstrap_env.verify_environment(repo_root=bootstrap.REPO_ROOT / "missing")

        self.assertEqual([error.check for error in errors], ["workspace-root"])


if __name__ == "__main__":
    unittest.main()
