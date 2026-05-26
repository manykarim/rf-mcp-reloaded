from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_PACKAGE_DIRS = {
    "rfmcp_core": [
        "pyproject.toml",
        "src/rfmcp_core/__init__.py",
        "src/rfmcp_core/contracts/__init__.py",
        "src/rfmcp_core/models/__init__.py",
    ],
    "rfmcp_mcp": [
        "pyproject.toml",
        "src/rfmcp_mcp/__init__.py",
        "src/rfmcp_mcp/transports/__init__.py",
        "src/rfmcp_mcp/tools/__init__.py",
    ],
    "rfmcp_cli": [
        "pyproject.toml",
        "src/rfmcp_cli/__init__.py",
        "src/rfmcp_cli/commands/__init__.py",
        "src/rfmcp_cli/workflows/__init__.py",
    ],
    "rfmcp_skills": [
        "pyproject.toml",
        "src/rfmcp_skills/__init__.py",
        "src/rfmcp_skills/definitions/__init__.py",
    ],
    "rfmcp_bundles": [
        "pyproject.toml",
        "src/rfmcp_bundles/__init__.py",
        "src/rfmcp_bundles/builders/__init__.py",
        "src/rfmcp_bundles/manifests/__init__.py",
    ],
}

REQUIRED_PROVIDER_DIRS = {
    "rfmcp_provider_browser",
    "rfmcp_provider_selenium",
    "rfmcp_provider_requests",
    "rfmcp_provider_appium",
    "rfmcp_provider_database",
}

REQUIRED_ROOT_DOCS = [
    "README.md",
    "CONTRIBUTING.md",
    "docs/project-structure.md",
]


@dataclass(frozen=True)
class StructureError:
    path: str
    message: str


def _missing_paths(base_dir: Path, relative_paths: Iterable[str], repo_root: Path) -> list[StructureError]:
    errors: list[StructureError] = []
    for relative_path in relative_paths:
        candidate = base_dir / relative_path
        if not candidate.exists():
            errors.append(
                StructureError(
                    path=str(candidate.relative_to(repo_root)),
                    message="required scaffold path is missing",
                )
            )
    return errors


def verify_workspace_structure(repo_root: Path = REPO_ROOT) -> list[StructureError]:
    errors: list[StructureError] = []
    packages_root = repo_root / "packages"

    for package_name, relative_paths in REQUIRED_PACKAGE_DIRS.items():
        package_root = packages_root / package_name
        if not package_root.exists():
            errors.append(
                StructureError(
                    path=str(package_root.relative_to(repo_root)),
                    message="required workspace package is missing",
                )
            )
            continue
        errors.extend(_missing_paths(package_root, relative_paths, repo_root))

    for provider_name in sorted(REQUIRED_PROVIDER_DIRS):
        provider_root = packages_root / provider_name
        expected = [
            "pyproject.toml",
            f"src/{provider_name}/__init__.py",
            f"src/{provider_name}/metadata.py",
            f"src/{provider_name}/plugin.py",
        ]
        if not provider_root.exists():
            errors.append(
                StructureError(
                    path=str(provider_root.relative_to(repo_root)),
                    message="required provider scaffold is missing",
                )
            )
            continue
        errors.extend(_missing_paths(provider_root, expected, repo_root))

    errors.extend(_missing_paths(repo_root, REQUIRED_ROOT_DOCS, repo_root))
    return errors


def main() -> int:
    errors = verify_workspace_structure()
    if not errors:
        print("Workspace structure OK")
        print("- All required package and provider scaffolds are present.")
        print("- Next step: continue with contract, CLI, or provider implementation.")
        return 0

    print("Workspace structure verification failed.")
    for error in errors:
        print(f"[missing] {error.path}: {error.message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
