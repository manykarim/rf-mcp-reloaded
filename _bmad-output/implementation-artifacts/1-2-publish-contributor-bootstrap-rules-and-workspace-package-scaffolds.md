# Story 1.2: Publish Contributor Bootstrap Rules and Workspace Package Scaffolds

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a contributor,
I want the workspace package scaffolds and contributor bootstrap rules to be explicit,
so that I can extend the project without guessing package ownership, provider boundaries, or verification commands.

## Acceptance Criteria

1. **Given** the starter workspace exists  
   **When** the contributor scaffolding story is implemented  
   **Then** the project includes the intended package skeletons for `rfmcp_core`, `rfmcp_mcp`, `rfmcp_cli`, `rfmcp_skills`, `rfmcp_bundles`, and the first provider packages  
   **And** the bootstrap documentation explains package boundaries, provider scaffolding expectations, and the baseline verification commands contributors must run.

2. **Given** a contributor adds or modifies a package scaffold incorrectly  
   **When** they follow the documented bootstrap rules  
   **Then** the project structure rules make the inconsistency visible  
   **And** the contributor can correct the mistake without relying on hidden maintainer knowledge.

## Tasks / Subtasks

- [x] Add the intended workspace package skeletons. (AC: 1)
  - [x] Create package scaffolds for `rfmcp_core`, `rfmcp_mcp`, `rfmcp_cli`, `rfmcp_skills`, and `rfmcp_bundles`.
  - [x] Create the first provider package scaffolds with explicit provider/plugin entry files.
  - [x] Ensure each package has a minimal `pyproject.toml` and importable `src/` package root.
- [x] Publish contributor bootstrap and package-boundary rules. (AC: 1)
  - [x] Expand contributor docs with package ownership, provider expectations, and verification commands.
  - [x] Add a structure reference doc that maps package responsibilities to the architecture.
- [x] Make scaffold inconsistencies visible. (AC: 2)
  - [x] Add a deterministic structure-verification script for required workspace packages and files.
  - [x] Add tests covering the expected success path and at least one failure path.
- [x] Re-lock and verify the scaffolded workspace. (AC: 1, 2)
  - [x] Re-run `uv lock`.
  - [x] Run the environment and structure verification commands and record the results.

## Dev Notes

- Story 1.1 already established the root workspace baseline; Story 1.2 now fills in the package and contributor skeletons that Story 1.1 deliberately deferred.
- The architecture’s target tree explicitly names the package set to scaffold: `rfmcp_core`, `rfmcp_mcp`, `rfmcp_cli`, `rfmcp_skills`, `rfmcp_bundles`, and provider packages such as browser, selenium, requests, appium, and database. The story can keep file contents skeletal, but the package names and boundaries must match the architecture. [Source: `_bmad-output/planning-artifacts/architecture.md` repo tree]
- Package boundaries must stay clear in docs: `rfmcp_mcp` for live-state MCP surfaces only, `rfmcp_cli` for stateless workflows and presentation, `rfmcp_core` for shared contracts and logic, `rfmcp_skills` for canonical workflow definitions, `rfmcp_bundles` for generated artifact rendering, and provider packages as optional extensions. [Source: `_bmad-output/planning-artifacts/architecture.md#Architectural Boundaries`]
- A deterministic structure-verification path is part of the story so contributors can detect broken scaffolds without tribal knowledge.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv lock`
- `python3 scripts/verify_workspace_structure.py`
- `python3 -m unittest discover -s tests -v`
- `python3 scripts/verify_bootstrap_env.py`

### Completion Notes List

- Added the planned workspace package scaffolds for core, MCP, CLI, skills, bundles, and the first provider packages.
- Added contributor-facing package ownership rules and a project-structure reference document.
- Added `scripts/verify_workspace_structure.py` plus unit tests to make scaffold mistakes visible without maintainer intervention.
- Fixed the structure verifier so repo-root resolution works in temporary test directories as well as the real repository.
- Re-ran `uv lock`, structure verification, and the test suite after the scaffold changes.

### File List

- CONTRIBUTING.md
- README.md
- docs/project-structure.md
- packages/rfmcp_bundles/pyproject.toml
- packages/rfmcp_bundles/src/rfmcp_bundles/__init__.py
- packages/rfmcp_bundles/src/rfmcp_bundles/builders/__init__.py
- packages/rfmcp_bundles/src/rfmcp_bundles/manifests/__init__.py
- packages/rfmcp_cli/pyproject.toml
- packages/rfmcp_cli/src/rfmcp_cli/__init__.py
- packages/rfmcp_cli/src/rfmcp_cli/commands/__init__.py
- packages/rfmcp_cli/src/rfmcp_cli/install/__init__.py
- packages/rfmcp_cli/src/rfmcp_cli/presenters/__init__.py
- packages/rfmcp_cli/src/rfmcp_cli/workflows/__init__.py
- packages/rfmcp_core/pyproject.toml
- packages/rfmcp_core/src/rfmcp_core/__init__.py
- packages/rfmcp_core/src/rfmcp_core/contracts/__init__.py
- packages/rfmcp_core/src/rfmcp_core/hints/__init__.py
- packages/rfmcp_core/src/rfmcp_core/models/__init__.py
- packages/rfmcp_core/src/rfmcp_core/observability/__init__.py
- packages/rfmcp_core/src/rfmcp_core/policy/__init__.py
- packages/rfmcp_core/src/rfmcp_core/robot/__init__.py
- packages/rfmcp_core/src/rfmcp_core/runtime/__init__.py
- packages/rfmcp_core/src/rfmcp_core/utils/__init__.py
- packages/rfmcp_mcp/pyproject.toml
- packages/rfmcp_mcp/src/rfmcp_mcp/__init__.py
- packages/rfmcp_mcp/src/rfmcp_mcp/security/__init__.py
- packages/rfmcp_mcp/src/rfmcp_mcp/tools/__init__.py
- packages/rfmcp_mcp/src/rfmcp_mcp/transports/__init__.py
- packages/rfmcp_provider_appium/pyproject.toml
- packages/rfmcp_provider_appium/src/rfmcp_provider_appium/__init__.py
- packages/rfmcp_provider_appium/src/rfmcp_provider_appium/metadata.py
- packages/rfmcp_provider_appium/src/rfmcp_provider_appium/plugin.py
- packages/rfmcp_provider_browser/pyproject.toml
- packages/rfmcp_provider_browser/src/rfmcp_provider_browser/__init__.py
- packages/rfmcp_provider_browser/src/rfmcp_provider_browser/metadata.py
- packages/rfmcp_provider_browser/src/rfmcp_provider_browser/plugin.py
- packages/rfmcp_provider_database/pyproject.toml
- packages/rfmcp_provider_database/src/rfmcp_provider_database/__init__.py
- packages/rfmcp_provider_database/src/rfmcp_provider_database/metadata.py
- packages/rfmcp_provider_database/src/rfmcp_provider_database/plugin.py
- packages/rfmcp_provider_requests/pyproject.toml
- packages/rfmcp_provider_requests/src/rfmcp_provider_requests/__init__.py
- packages/rfmcp_provider_requests/src/rfmcp_provider_requests/metadata.py
- packages/rfmcp_provider_requests/src/rfmcp_provider_requests/plugin.py
- packages/rfmcp_provider_selenium/pyproject.toml
- packages/rfmcp_provider_selenium/src/rfmcp_provider_selenium/__init__.py
- packages/rfmcp_provider_selenium/src/rfmcp_provider_selenium/metadata.py
- packages/rfmcp_provider_selenium/src/rfmcp_provider_selenium/plugin.py
- packages/rfmcp_skills/pyproject.toml
- packages/rfmcp_skills/src/rfmcp_skills/__init__.py
- packages/rfmcp_skills/src/rfmcp_skills/definitions/__init__.py
- scripts/verify_workspace_structure.py
- tests/test_verify_workspace_structure.py
- uv.lock

## Change Log

- 2026-05-25: Created Story 1.2 implementation brief from Epic 1 planning artifacts.
- 2026-05-25: Implemented the workspace package scaffolds, contributor rules, and structure verification; promoted story to review.
- 2026-05-25: Completed Story 1.2 after fixing the structure-verifier repo-root bug and re-running the scaffold checks.
