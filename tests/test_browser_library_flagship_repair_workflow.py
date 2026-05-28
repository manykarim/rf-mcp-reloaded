from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import jsonschema
import tomllib

REPO_ROOT = Path(__file__).resolve().parent.parent
for path in [
    REPO_ROOT / "packages" / "rfmcp_core" / "src",
    REPO_ROOT / "packages" / "rfmcp_cli" / "src",
    REPO_ROOT / "packages" / "rfmcp_skills" / "src",
    REPO_ROOT / "packages" / "rfmcp_provider_browser" / "src",
]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rfmcp_skills.definitions.browser_library_repair import (  # noqa: E402
    DEFAULT_FAILURE_MESSAGE,
    RobotExecutionResult,
    browser_library_repair_definition,
    run_browser_library_flagship_repair,
)
from rfmcp_skills.fallbacks import (  # noqa: E402
    BROWSER_LIBRARY_FLAGSHIP_REPAIR_ID,
    fallback_commands_for,
    render_fallback_commands,
)


class BrowserLibraryFlagshipRepairWorkflowTests(unittest.TestCase):
    def _write_robot_file(self, content: str) -> str:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        target = Path(tmpdir.name) / "browser_repair.robot"
        target.write_text(content)
        return str(target)

    def _write_browser_library_stub(self, target: str) -> None:
        Path(target).with_name("Browser.py").write_text(
            "class Browser:\n"
            "    def new_page(self, url):\n"
            "        return url\n\n"
            "    def click(self, selector):\n"
            "        return selector\n"
        )

    def test_definition_and_fallback_mapping_are_stable(self) -> None:
        from rfmcp_skills import browser_library_repair_definition as top_level_definition

        definition = browser_library_repair_definition()

        self.assertEqual(definition.skill_id, BROWSER_LIBRARY_FLAGSHIP_REPAIR_ID)
        self.assertEqual(top_level_definition().skill_id, definition.skill_id)
        self.assertEqual(definition.manifest.skill_id, BROWSER_LIBRARY_FLAGSHIP_REPAIR_ID)
        self.assertEqual(tuple(definition.manifest.fallback_commands), fallback_commands_for(BROWSER_LIBRARY_FLAGSHIP_REPAIR_ID))
        self.assertEqual(definition.asset_directory, "assets/skills/browser-library-flagship-repair")
        self.assertIn("rf_session", definition.mcp_tools)
        self.assertIn("rfmcp validate <target.robot> --json", definition.fallback_commands)
        rendered = render_fallback_commands(
            BROWSER_LIBRARY_FLAGSHIP_REPAIR_ID,
            target="/tmp/example suite.robot",
            failure_message='No keyword with name "New Page" found.',
        )
        self.assertIn("'/tmp/example suite.robot'", rendered[0])
        self.assertIn('\'No keyword with name "New Page" found.\'', rendered[0])

    def test_manifest_matches_committed_schema(self) -> None:
        definition = browser_library_repair_definition()
        schema = json.loads((REPO_ROOT / "assets" / "schemas" / "skill-manifest.schema.json").read_text())
        jsonschema.validate(definition.manifest.model_dump(mode="json"), schema)

    def test_skills_package_metadata_declares_runtime_assets_and_robot_dependency(self) -> None:
        pyproject = tomllib.loads((REPO_ROOT / "packages" / "rfmcp_skills" / "pyproject.toml").read_text())

        self.assertIn("robotframework>=7.4,<7.5", pyproject["project"]["dependencies"])
        self.assertEqual(
            pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]["../../assets/skills/browser-library-flagship-repair/README.md"],
            "rfmcp_skills/data/assets/browser-library-flagship-repair/README.md",
        )
        self.assertEqual(
            pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]["../../docs/browser-library-flagship-repair.md"],
            "rfmcp_skills/data/docs/browser-library-flagship-repair.md",
        )

    def test_packaged_wheel_includes_flagship_assets(self) -> None:
        wheel_path = REPO_ROOT / "dist" / "rfmcp_skills-test-wheel"
        wheel_path.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: [item.unlink() for item in wheel_path.glob("*.whl")])
        result = subprocess.run(
            ["uv", "build", "--package", "rfmcp-skills", "--wheel", "--out-dir", str(wheel_path), "--clear"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        wheel = next(wheel_path.glob("*.whl"))
        with zipfile.ZipFile(wheel) as archive:
            names = set(archive.namelist())
        self.assertIn("rfmcp_skills/data/assets/browser-library-flagship-repair/README.md", names)
        self.assertIn("rfmcp_skills/data/docs/browser-library-flagship-repair.md", names)

    def test_workflow_repairs_missing_browser_import_and_records_events(self) -> None:
        target = self._write_robot_file(
            "*** Test Cases ***\n"
            "Broken Browser Test\n"
            "    New Page    https://example.com\n"
            "    Click    text=Login\n"
        )
        self._write_browser_library_stub(target)
        with tempfile.TemporaryDirectory() as tmpdir:
            benchmark_log = Path(tmpdir) / "flagship-repair.jsonl"
            result = run_browser_library_flagship_repair(
                target,
                failure_message=DEFAULT_FAILURE_MESSAGE,
                live_state_available=True,
                benchmark_log=benchmark_log,
            )

            self.assertTrue(result.ok)
            self.assertEqual(result.applied_patch, "prepend-browser-settings-section")
            self.assertTrue(result.validation_after.ok)
            self.assertTrue(result.rerun_ok)
            self.assertIn("browser-library-missing", {finding.code for finding in result.diagnostics.findings})
            self.assertIn("browser-official-docs", {candidate.hint_id for candidate in result.hints.hint.candidates})
            repaired_content = Path(target).read_text()
            self.assertIn("Library    Browser", repaired_content)
            self.assertIn("Robot execution succeeded", result.rerun_detail)

            payloads = [json.loads(line) for line in benchmark_log.read_text().splitlines()]
            self.assertEqual(
                [payload["event_type"] for payload in payloads],
                ["boundary", "diagnose", "hint-resolution", "baseline-proof", "repair", "rerun-proof"],
            )
            self.assertTrue(all(payload["benchmark"] for payload in payloads))
            self.assertEqual(payloads[0]["surface"], "mcp")
            self.assertEqual(payloads[3]["metadata"]["baseline_ok"], "false")
            self.assertEqual(payloads[3]["metadata"]["expected_failure_matched"], "true")
            self.assertEqual(payloads[4]["metadata"]["synthetic_patch"], "true")
            self.assertEqual(payloads[-1]["metadata"]["rerun_ok"], "true")

    def test_workflow_is_deterministic_for_same_input(self) -> None:
        target_a = self._write_robot_file(
            "*** Test Cases ***\n"
            "Broken Browser Test\n"
            "    New Page    https://example.com\n"
        )
        target_b = self._write_robot_file(
            "*** Test Cases ***\n"
            "Broken Browser Test\n"
            "    New Page    https://example.com\n"
        )
        self._write_browser_library_stub(target_a)
        self._write_browser_library_stub(target_b)
        with tempfile.TemporaryDirectory() as tmpdir:
            log_a = Path(tmpdir) / "a.jsonl"
            log_b = Path(tmpdir) / "b.jsonl"
            result_a = run_browser_library_flagship_repair(target_a, benchmark_log=log_a, live_state_available=False)
            result_b = run_browser_library_flagship_repair(target_b, benchmark_log=log_b, live_state_available=False)
            payloads_a = [json.loads(line) for line in log_a.read_text().splitlines()]
            payloads_b = [json.loads(line) for line in log_b.read_text().splitlines()]
            events_a = [payload["event_type"] for payload in payloads_a]
            events_b = [payload["event_type"] for payload in payloads_b]

        self.assertEqual(Path(target_a).read_text(), Path(target_b).read_text())
        self.assertEqual(result_a.applied_patch, result_b.applied_patch)
        self.assertEqual(result_a.definition.fallback_commands, result_b.definition.fallback_commands)
        self.assertEqual(events_a, events_b)
        self.assertEqual(payloads_a[0]["surface"], "cli")
        self.assertEqual(payloads_a[0]["metadata"]["tools"], "none")

    def test_workflow_is_idempotent_for_equivalent_browser_import_spacing(self) -> None:
        target = self._write_robot_file(
            "*** Settings ***\n"
            "Library  Browser\n\n"
            "*** Test Cases ***\n"
            "Browser Test\n"
            "    New Page    https://example.com\n"
        )
        self._write_browser_library_stub(target)

        result = run_browser_library_flagship_repair(
            target,
            benchmark_log=None,
            live_state_available=False,
            failure_message=None,
        )

        self.assertTrue(result.ok)
        self.assertIsNone(result.applied_patch)
        self.assertEqual(Path(target).read_text().count("Library  Browser"), 1)

    def test_workflow_is_idempotent_when_browser_import_is_already_present(self) -> None:
        target = self._write_robot_file(
            "*** Settings ***\n"
            "Library    Browser\n\n"
            "*** Test Cases ***\n"
            "Browser Test\n"
            "    New Page    https://example.com\n"
        )
        self._write_browser_library_stub(target)
        result = run_browser_library_flagship_repair(
            target,
            benchmark_log=None,
            live_state_available=False,
            failure_message=None,
        )

        self.assertTrue(result.ok)
        self.assertIsNone(result.applied_patch)
        self.assertTrue(result.rerun_ok)

    def test_workflow_inserts_into_existing_settings_case_insensitively(self) -> None:
        target = self._write_robot_file(
            "*** SETTINGS ***\n"
            "Documentation    Example\n\n"
            "*** Test Cases ***\n"
            "Browser Test\n"
            "    New Page    https://example.com\n"
        )
        self._write_browser_library_stub(target)
        result = run_browser_library_flagship_repair(target, benchmark_log=None, live_state_available=False)

        self.assertTrue(result.ok)
        repaired_content = Path(target).read_text()
        self.assertEqual(repaired_content.count("*** SETTINGS ***"), 1)
        self.assertEqual(repaired_content.count("*** Settings ***"), 0)
        self.assertIn("Library    Browser", repaired_content)

    def test_unsupported_flagship_scenario_returns_structured_error(self) -> None:
        target = self._write_robot_file(
            "*** Test Cases ***\n"
            "Other Failure\n"
            "    Log    hello\n"
        )
        result = run_browser_library_flagship_repair(
            target,
            failure_message="Expected 1 argument, got 2.",
            live_state_available=False,
        )

        self.assertFalse(result.ok)
        self.assertIsNotNone(result.error)
        self.assertEqual(result.error.code, "unsupported-flagship-scenario")

    def test_baseline_failure_must_match_expected_message(self) -> None:
        target = self._write_robot_file(
            "*** Test Cases ***\n"
            "Broken Browser Test\n"
            "    New Page    https://example.com\n"
        )
        self._write_browser_library_stub(target)
        log_dir = tempfile.TemporaryDirectory()
        self.addCleanup(log_dir.cleanup)
        benchmark_log = Path(log_dir.name) / "baseline-abort.jsonl"

        with patch(
            "rfmcp_skills.definitions.browser_library_repair._run_robot_execution",
            side_effect=[
                RobotExecutionResult(
                    ok=False,
                    detail="Robot execution failed.",
                    output="ModuleNotFoundError: No module named robot",
                ),
            ],
        ):
            result = run_browser_library_flagship_repair(
                target,
                failure_message=DEFAULT_FAILURE_MESSAGE,
                live_state_available=False,
                benchmark_log=benchmark_log,
            )

        self.assertFalse(result.ok)
        self.assertIsNotNone(result.error)
        self.assertEqual(result.error.code, "baseline-failure-not-reproduced")
        payloads = [json.loads(line) for line in benchmark_log.read_text().splitlines()]
        self.assertEqual(payloads[-1]["event_type"], "baseline-abort")

    def test_docs_map_mcp_boundary_and_cli_takeover(self) -> None:
        asset_doc = (REPO_ROOT / "assets" / "skills" / "browser-library-flagship-repair" / "README.md").read_text()
        workflow_doc = (REPO_ROOT / "docs" / "browser-library-flagship-repair.md").read_text()

        self.assertIn("rf_session", asset_doc)
        self.assertIn("rf_context", workflow_doc)
        self.assertIn("rfmcp repair-diagnostics", workflow_doc)
        self.assertIn("rfmcp validate", asset_doc)
        self.assertIn("python -m robot --output NONE --report NONE --log NONE", workflow_doc)


if __name__ == "__main__":
    unittest.main()
