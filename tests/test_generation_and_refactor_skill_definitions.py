from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import jsonschema
from pydantic import ValidationError
import tomllib

REPO_ROOT = Path(__file__).resolve().parent.parent
for path in [
    REPO_ROOT / "packages" / "rfmcp_core" / "src",
    REPO_ROOT / "packages" / "rfmcp_skills" / "src",
]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rfmcp_skills import (  # noqa: E402
    EXISTING_ARTIFACT_REFACTOR_ID,
    RUNNABLE_TEST_GENERATION_ID,
    GenerationSkillInput,
    RefactorSkillInput,
    existing_artifact_refactor_definition,
    registered_skill_definitions,
    render_fallback_commands,
    runnable_test_generation_definition,
    skill_definition_by_id,
)


class GenerationAndRefactorSkillDefinitionTests(unittest.TestCase):
    def test_generation_definition_is_stable(self) -> None:
        definition = runnable_test_generation_definition()

        self.assertEqual(definition.skill_id, RUNNABLE_TEST_GENERATION_ID)
        self.assertEqual(definition.input_model, GenerationSkillInput)
        self.assertEqual(definition.asset_directory, "assets/skills/runnable-test-generation")
        self.assertEqual(definition.boundary_doc_path, "docs/runnable-test-generation.md")
        self.assertEqual(definition.workflow_steps[0].surface, "host")
        self.assertIn("rfmcp generate <target.robot>", definition.fallback_commands[-1])

    def test_refactor_definition_is_stable(self) -> None:
        definition = existing_artifact_refactor_definition()

        self.assertEqual(definition.skill_id, EXISTING_ARTIFACT_REFACTOR_ID)
        self.assertEqual(definition.input_model, RefactorSkillInput)
        self.assertEqual(definition.asset_directory, "assets/skills/existing-artifact-refactor")
        self.assertEqual(definition.boundary_doc_path, "docs/existing-artifact-refactor.md")
        self.assertEqual(definition.workflow_steps[-1].surface, "cli")
        self.assertIn("rfmcp refactor <target.robot>", definition.fallback_commands[0])

    def test_manifests_match_committed_schema(self) -> None:
        schema = json.loads((REPO_ROOT / "assets" / "schemas" / "skill-manifest.schema.json").read_text())

        jsonschema.validate(runnable_test_generation_definition().manifest.model_dump(mode="json"), schema)
        jsonschema.validate(existing_artifact_refactor_definition().manifest.model_dump(mode="json"), schema)

    def test_generation_input_contract_requires_body_request(self) -> None:
        with self.assertRaises(ValidationError):
            GenerationSkillInput(target="generated.robot")

        valid = GenerationSkillInput(target="generated.robot", steps=["Log    hello"])
        self.assertEqual(valid.target, "generated.robot")

    def test_refactor_input_contract_requires_real_change(self) -> None:
        with self.assertRaises(ValidationError):
            RefactorSkillInput(target="suite.robot")

        with self.assertRaises(ValidationError):
            RefactorSkillInput(target="suite.robot", mode="regenerate")

        valid = RefactorSkillInput(target="suite.robot", documentation="Updated suite.")
        self.assertEqual(valid.mode, "refactor")

    def test_catalog_exposes_new_definitions(self) -> None:
        definitions = registered_skill_definitions()
        ids = {definition.skill_id for definition in definitions}

        self.assertIn(RUNNABLE_TEST_GENERATION_ID, ids)
        self.assertIn(EXISTING_ARTIFACT_REFACTOR_ID, ids)
        self.assertIsNotNone(skill_definition_by_id(RUNNABLE_TEST_GENERATION_ID))
        self.assertIsNotNone(skill_definition_by_id(EXISTING_ARTIFACT_REFACTOR_ID))

    def test_rendered_fallbacks_quote_values(self) -> None:
        commands = render_fallback_commands(
            RUNNABLE_TEST_GENERATION_ID,
            target="/tmp/generated suite.robot",
            query="Browser Login",
            library="Browser",
            task="verify greeting output",
            step="Log To Console    updated",
            assertion="Should Be Equal As Strings    ${message}    hello",
        )

        self.assertIn("'/tmp/generated suite.robot'", commands[1])
        self.assertIn("'Browser Login'", commands[0])
        self.assertIn("'verify greeting output'", commands[2])

    def test_docs_are_honest_about_host_variance_and_cli_fallback(self) -> None:
        generation_doc = (REPO_ROOT / "docs" / "runnable-test-generation.md").read_text()
        refactor_doc = (REPO_ROOT / "docs" / "existing-artifact-refactor.md").read_text()
        generation_asset = (REPO_ROOT / "assets" / "skills" / "runnable-test-generation" / "README.md").read_text()
        refactor_asset = (REPO_ROOT / "assets" / "skills" / "existing-artifact-refactor" / "README.md").read_text()

        for content in (generation_doc, refactor_doc, generation_asset, refactor_asset):
            self.assertIn("host", content.lower())
            self.assertIn("cli fallback", content.lower())

    def test_skills_package_metadata_declares_new_assets(self) -> None:
        pyproject = tomllib.loads((REPO_ROOT / "packages" / "rfmcp_skills" / "pyproject.toml").read_text())
        wheel_force_include = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]

        self.assertEqual(
            wheel_force_include["../../assets/skills/runnable-test-generation/README.md"],
            "rfmcp_skills/data/assets/runnable-test-generation/README.md",
        )
        self.assertEqual(
            wheel_force_include["../../assets/skills/existing-artifact-refactor/README.md"],
            "rfmcp_skills/data/assets/existing-artifact-refactor/README.md",
        )
        self.assertEqual(
            wheel_force_include["../../docs/runnable-test-generation.md"],
            "rfmcp_skills/data/docs/runnable-test-generation.md",
        )
        self.assertEqual(
            wheel_force_include["../../docs/existing-artifact-refactor.md"],
            "rfmcp_skills/data/docs/existing-artifact-refactor.md",
        )

    def test_packaged_wheel_includes_new_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wheel_dir = Path(tmpdir)
            result = subprocess.run(
                ["uv", "build", "--package", "rfmcp-skills", "--wheel", "--out-dir", str(wheel_dir), "--clear"],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            wheel = next(wheel_dir.glob("*.whl"))
            with zipfile.ZipFile(wheel) as archive:
                names = set(archive.namelist())

        self.assertIn("rfmcp_skills/data/assets/runnable-test-generation/README.md", names)
        self.assertIn("rfmcp_skills/data/assets/existing-artifact-refactor/README.md", names)
        self.assertIn("rfmcp_skills/data/docs/runnable-test-generation.md", names)
        self.assertIn("rfmcp_skills/data/docs/existing-artifact-refactor.md", names)
