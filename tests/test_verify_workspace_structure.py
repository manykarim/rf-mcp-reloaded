from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import verify_workspace_structure


class VerifyWorkspaceStructureTests(unittest.TestCase):
    def test_workspace_structure_passes_for_real_repo(self) -> None:
        self.assertEqual(verify_workspace_structure.verify_workspace_structure(), [])

    def test_workspace_structure_reports_missing_provider_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            self._create_required_tree(repo_root)
            missing = repo_root / "packages/rfmcp_provider_browser/src/rfmcp_provider_browser/plugin.py"
            missing.unlink()

            errors = verify_workspace_structure.verify_workspace_structure(repo_root=repo_root)

        self.assertTrue(any(error.path.endswith("plugin.py") for error in errors))

    def _create_required_tree(self, repo_root: Path) -> None:
        for relative_doc in verify_workspace_structure.REQUIRED_ROOT_DOCS:
            path = repo_root / relative_doc
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("placeholder\n")

        for package_name, relative_paths in verify_workspace_structure.REQUIRED_PACKAGE_DIRS.items():
            package_root = repo_root / "packages" / package_name
            package_root.mkdir(parents=True, exist_ok=True)
            for relative_path in relative_paths:
                path = package_root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("placeholder\n")

        for provider_name in verify_workspace_structure.REQUIRED_PROVIDER_DIRS:
            provider_root = repo_root / "packages" / provider_name
            expected = [
                "pyproject.toml",
                f"src/{provider_name}/__init__.py",
                f"src/{provider_name}/metadata.py",
                f"src/{provider_name}/plugin.py",
            ]
            provider_root.mkdir(parents=True, exist_ok=True)
            for relative_path in expected:
                path = provider_root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("placeholder\n")


if __name__ == "__main__":
    unittest.main()
