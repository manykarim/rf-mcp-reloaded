from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import yaml
from pydantic import ValidationError

from rfmcp_core.models.hint_pack import HintPackManifest


REPO_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_HINT_PACK_DIR = REPO_ROOT / "assets" / "hints" / "libraries"
DEFAULT_HINT_PACK_PACKAGE = "rfmcp_core.data.hints.libraries"
REPO_MARKERS = ("pyproject.toml",)


@dataclass(frozen=True)
class LoadedHintPack:
    manifest: HintPackManifest
    source_path: str


class HintPackValidationError(RuntimeError):
    pass


def _is_source_tree_hint_dir(path: Path) -> bool:
    return path.exists() and all((REPO_ROOT / marker).exists() for marker in REPO_MARKERS)


def load_hint_packs(root: Path | None = None) -> list[LoadedHintPack]:
    loaded: list[LoadedHintPack] = []
    seen_ids: dict[str, str] = {}

    if root is not None:
        pack_sources: list[tuple[str, str]] = []
        if not root.exists():
            return []
        for path in sorted(root.glob("*.y*ml")):
            pack_sources.append((str(path), path.read_text()))
    elif _is_source_tree_hint_dir(DEFAULT_HINT_PACK_DIR):
        pack_sources = []
        for path in sorted(DEFAULT_HINT_PACK_DIR.glob("*.y*ml")):
            pack_sources.append((str(path.relative_to(REPO_ROOT)), path.read_text()))
    else:
        try:
            package_root = resources.files(DEFAULT_HINT_PACK_PACKAGE)
            resource_entries = sorted(
                [
                    entry
                    for entry in package_root.iterdir()
                    if entry.is_file() and entry.name.endswith((".yaml", ".yml"))
                ],
                key=lambda entry: entry.name,
            )
        except (ModuleNotFoundError, FileNotFoundError) as exc:
            raise HintPackValidationError(
                f"Authoritative hint pack directory '{DEFAULT_HINT_PACK_DIR}' was not found and bundled pack resources are unavailable."
            ) from exc
        if not resource_entries:
            raise HintPackValidationError(
                f"Bundled authoritative hint packs were not found in package '{DEFAULT_HINT_PACK_PACKAGE}'."
            )
        pack_sources = [
            (f"package:{DEFAULT_HINT_PACK_PACKAGE}/{entry.name}", entry.read_text()) for entry in resource_entries
        ]

    if root is None and not pack_sources:
        raise HintPackValidationError("No authoritative hint packs were found for default hint resolution.")

    for source_path, text in pack_sources:
        try:
            payload = yaml.safe_load(text) or {}
            manifest = HintPackManifest.model_validate(payload)
        except (OSError, yaml.YAMLError, ValidationError) as exc:
            raise HintPackValidationError(
                f"Failed to load hint pack '{source_path}': {type(exc).__name__}: {exc}"
            ) from exc

        if manifest.pack_id in seen_ids:
            raise HintPackValidationError(
                f"Duplicate hint pack id '{manifest.pack_id}' in '{source_path}' and '{seen_ids[manifest.pack_id]}'."
            )
        seen_ids[manifest.pack_id] = source_path
        loaded.append(LoadedHintPack(manifest=manifest, source_path=source_path))
    return loaded
