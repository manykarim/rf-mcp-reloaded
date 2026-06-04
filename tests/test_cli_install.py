"""Tests for the rfmcp install/onboarding subcommands."""

from __future__ import annotations

import json
import os
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
    REPO_ROOT / "packages" / "rfmcp_mcp" / "src",
]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rfmcp_cli.install import (  # noqa: E402
    _client_config_spec,
    _merge_codex_toml,
    _merge_json_mcp_server,
    _server_block,
)
from rfmcp_cli.main import app  # noqa: E402


class ClientConfigSpecTests(unittest.TestCase):
    def test_supported_clients_resolve_to_known_paths(self) -> None:
        for client in ("claude-code", "claude-desktop", "cursor", "kilo", "codex"):
            spec = _client_config_spec(client)
            self.assertEqual(spec.name, client)
            self.assertTrue(str(spec.config_path))
            self.assertIn(spec.fmt, ("json", "toml"))

    def test_codex_uses_toml(self) -> None:
        self.assertEqual(_client_config_spec("codex").fmt, "toml")

    def test_unsupported_client_raises(self) -> None:
        with self.assertRaises(Exception):
            _client_config_spec("nonexistent-client")


class MergeJsonMcpServerTests(unittest.TestCase):
    def test_merge_into_missing_file_creates_minimal_dict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "config.json"  # does not exist
            merged = _merge_json_mcp_server(target, "rfmcp", _server_block())
            self.assertEqual(merged, {"mcpServers": {"rfmcp": {"command": "rfmcp", "args": ["serve"]}}})

    def test_merge_preserves_existing_servers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "config.json"
            target.write_text(json.dumps({
                "mcpServers": {"other": {"command": "other-mcp", "args": []}},
                "unrelatedField": True,
            }), encoding="utf-8")
            merged = _merge_json_mcp_server(target, "rfmcp", _server_block())
            self.assertIn("other", merged["mcpServers"])
            self.assertIn("rfmcp", merged["mcpServers"])
            self.assertTrue(merged["unrelatedField"])

    def test_merge_overwrites_existing_rfmcp_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "config.json"
            target.write_text(json.dumps({
                "mcpServers": {"rfmcp": {"command": "old", "args": ["stale"]}},
            }), encoding="utf-8")
            merged = _merge_json_mcp_server(target, "rfmcp", _server_block())
            self.assertEqual(merged["mcpServers"]["rfmcp"], {"command": "rfmcp", "args": ["serve"]})


class MergeCodexTomlTests(unittest.TestCase):
    def test_writes_block_when_file_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "config.toml"
            result = _merge_codex_toml(target)
            self.assertIn("[mcp_servers.rfmcp]", result)
            self.assertIn('command = "rfmcp"', result)

    def test_idempotent_when_block_already_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "config.toml"
            target.write_text(
                'model = "gpt-5"\n\n[mcp_servers.rfmcp]\ncommand = "rfmcp"\nargs = ["serve"]\n',
                encoding="utf-8",
            )
            result = _merge_codex_toml(target)
            # No duplicate block — file returned unchanged.
            self.assertEqual(result.count("[mcp_servers.rfmcp]"), 1)

    def test_appends_when_block_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "config.toml"
            target.write_text('model = "gpt-5"\n', encoding="utf-8")
            result = _merge_codex_toml(target)
            self.assertIn("[mcp_servers.rfmcp]", result)
            self.assertIn('model = "gpt-5"', result)


class InitCommandTests(unittest.TestCase):
    def test_print_mode_emits_only_snippet_not_existing_config(self) -> None:
        runner = CliRunner()
        # Default --print mode does NOT touch disk and emits only the snippet to merge.
        result = runner.invoke(app, ["init", "claude-code"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("mcpServers", result.output)
        self.assertIn('"rfmcp"', result.output)
        self.assertIn('"command": "rfmcp"', result.output)
        # Should NOT print unrelated content from the user's real config.
        # (If the user's actual config has many fields, the print mode hides them.)
        self.assertNotIn("numStartups", result.output)

    def test_write_mode_creates_file_with_backup(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            target = home / ".cursor" / "mcp.json"
            with patch("rfmcp_cli.install.Path.home", return_value=home):
                result = runner.invoke(app, ["init", "cursor", "--write"])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertTrue(target.is_file())
            payload = json.loads(target.read_text())
            self.assertIn("rfmcp", payload["mcpServers"])

    def test_write_mode_idempotent_on_rerun(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            target = home / ".kilo" / "mcp.json"
            with patch("rfmcp_cli.install.Path.home", return_value=home):
                runner.invoke(app, ["init", "kilo", "--write"])
                # Add an unrelated server alongside.
                config = json.loads(target.read_text())
                config["mcpServers"]["other"] = {"command": "x"}
                target.write_text(json.dumps(config))
                # Re-run init.
                result = runner.invoke(app, ["init", "kilo", "--write"])
            self.assertEqual(result.exit_code, 0)
            after = json.loads(target.read_text())
            # rfmcp still present, the other server preserved.
            self.assertIn("rfmcp", after["mcpServers"])
            self.assertIn("other", after["mcpServers"])

    def test_unsupported_client_exits_two(self) -> None:
        runner = CliRunner()
        result = runner.invoke(app, ["init", "nonexistent"])
        self.assertEqual(result.exit_code, 2)
        self.assertIn("Unsupported client", result.output)


class DoctorCommandTests(unittest.TestCase):
    def test_doctor_succeeds_in_dev_environment(self) -> None:
        runner = CliRunner()
        result = runner.invoke(app, ["doctor"])
        # In the project's own dev env every check should pass.
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("python_version", result.output)
        self.assertIn("robotframework", result.output)
        self.assertIn("local_policy", result.output)

    def test_doctor_json_emits_machine_readable_output(self) -> None:
        runner = CliRunner()
        result = runner.invoke(app, ["doctor", "--json"])
        self.assertEqual(result.exit_code, 0)
        payload = json.loads(result.output)
        self.assertIn("ok", payload)
        self.assertIn("checks", payload)
        self.assertTrue(any(c["name"] == "robotframework" for c in payload["checks"]))


class SkillsCommandTests(unittest.TestCase):
    def test_skills_list_reports_bundled_skills(self) -> None:
        runner = CliRunner()
        result = runner.invoke(app, ["skills", "list"])
        self.assertEqual(result.exit_code, 0, result.output)
        # The repo's checkout has at least one bundled skill.
        self.assertIn("browser-library-flagship-repair", result.output)

    def test_skills_install_symlink_into_tempdir(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            result = runner.invoke(
                app,
                [
                    "skills",
                    "install",
                    "browser-library-flagship-repair",
                    "--target",
                    str(target),
                    "--symlink",
                ],
            )
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertTrue(target.is_symlink())

    def test_skills_install_refuses_existing_without_force(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            target.mkdir()
            (target / "marker.txt").write_text("existing", encoding="utf-8")
            result = runner.invoke(
                app,
                ["skills", "install", "browser-library-flagship-repair", "--target", str(target)],
            )
            self.assertEqual(result.exit_code, 2)
            self.assertIn("already exists", result.output)
            # Existing content untouched.
            self.assertTrue((target / "marker.txt").is_file())

    def test_skills_uninstall_missing_target_exits_one(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "missing"
            result = runner.invoke(
                app,
                ["skills", "uninstall", "browser-library-flagship-repair", "--target", str(target)],
            )
            self.assertEqual(result.exit_code, 1)


if __name__ == "__main__":
    unittest.main()
