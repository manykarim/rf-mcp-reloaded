# Story 1.1: Initialize the Project From the Selected Starter Template

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a maintainer,
I want to initialize the repository from the selected `uv` starter and baseline toolchain,
so that the project begins from the approved workspace shape instead of an ad hoc scaffold.

## Acceptance Criteria

1. **Given** the current repository only contains a root `pyproject.toml`, `main.py`, and planning artifacts  
   **When** the workspace bootstrap story is implemented  
   **Then** the repository is initialized from the architecture-selected starter command `uv init --package rfmcp-reloaded`  
   **And** the root workspace configuration, shared `uv.lock`, and baseline tool versions match the architecture decision record  
   **And** the resulting layout is ready for follow-on package and contract work without inventing an alternate starter structure.

2. **Given** the local environment does not satisfy the baseline Python or `uv` expectations  
   **When** the bootstrap path is attempted  
   **Then** the failure is explicit about the mismatch  
   **And** the maintainer is given a deterministic next step rather than a silent partial setup.

## Tasks / Subtasks

- [x] Replace the placeholder project root with the approved `uv` workspace baseline. (AC: 1)
  - [x] Rewrite the root `pyproject.toml` to reflect the workspace bootstrap direction from the architecture.
  - [x] Remove or replace placeholder starter files that do not belong in the workspace baseline.
  - [x] Create the baseline repository folders and root files needed for follow-on package stories without pre-implementing those stories.
- [x] Add explicit bootstrap policy and environment verification. (AC: 1, 2)
  - [x] Add a deterministic bootstrap verification script that checks the required Python and `uv` baselines.
  - [x] Ensure version mismatch failures are explicit and include the next command or manual correction step.
- [x] Document the workspace bootstrap path for contributors. (AC: 1, 2)
  - [x] Update the root docs so maintainers know the intended bootstrap command, baseline versions, and verification commands.
  - [x] Document the current local mismatch behavior so the failure mode is intentional rather than surprising.
- [x] Lock and verify the workspace baseline. (AC: 1, 2)
  - [x] Generate `uv.lock` from the new root configuration.
  - [x] Run the bootstrap verification checks and record the results.

## Dev Notes

- Current repository state is still a placeholder single-package scaffold: root `pyproject.toml`, `main.py`, and planning artifacts only. Story 1.1 must replace that placeholder with the approved workspace baseline before package scaffolding begins in Story 1.2.
- The architecture selects a `uv` workspace monorepo as the project foundation, with the original starter command recorded as `uv init --package rfmcp-reloaded`. The persistent repository shape should align to the workspace monorepo, not remain a flat single-package app. [Source: `_bmad-output/planning-artifacts/architecture.md#Selected Starter: uv workspace monorepo`]
- Baseline implementation versions are already fixed in the architecture and must be reflected in bootstrap docs and enforcement: Python `>=3.11,<3.14`, `uv 0.11.16`, FastMCP `3.3.1`, MCP SDK `1.27.1`, `pluggy 1.6.0`, `pydantic 2.13.4`, `pydantic-settings 2.14.1`, `typer 0.25.1`, Robot Framework baseline `7.4.2`. Story 1.1 does not need to install all runtime packages yet, but it must encode these baselines clearly enough for later stories to inherit them without drift. [Source: `_bmad-output/planning-artifacts/architecture.md#ADR: Implementation Baseline Versions`]
- The architecture’s target tree shows the root should contain shared repo files, `packages/`, `scripts/`, `docs/`, `.github/workflows/`, `.python-version`, and `uv.lock`. Story 1.1 should establish the root-level skeleton and reserve package implementation for Story 1.2. [Source: `_bmad-output/planning-artifacts/architecture.md` lines around the repo tree]
- The bootstrap failure path is part of the story, not an optional extra. The current environment is already below the architecture baseline for `uv` (`uv 0.9.26` locally versus required `0.11.16`), so the verification script and docs must detect and explain that mismatch deterministically.
- Preserve planning artifacts and existing `_bmad-output/` content. This story is about initializing the code/workspace baseline around them, not deleting planning history.

### Project Structure Notes

- Root configuration belongs in repo-root files such as `pyproject.toml`, `.python-version`, `README.md`, `CONTRIBUTING.md`, and `scripts/`.
- Do not pre-create the full package set from Story 1.2 yet. It is acceptable to create empty structural directories such as `packages/` and `scripts/` when they are part of the workspace baseline.
- Keep all new files ASCII unless an existing file already requires otherwise.

### References

- `_bmad-output/planning-artifacts/epics.md` - Epic 1, Story 1.1
- `_bmad-output/planning-artifacts/architecture.md` - selected starter, baseline versions, target repo tree
- `_bmad-output/planning-artifacts/prds/prd-rfmcp-reloaded-2026-05-23/prd.md` - FR4, NFR2, NFR5

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv lock`
- `python3 scripts/verify_bootstrap_env.py`
- `cd scripts && python3 verify_bootstrap_env.py`
- `python3 -m unittest discover -s tests -v`
- `python3 -m compileall scripts tests`

### Completion Notes List

- Replaced the placeholder single-file scaffold with a root `uv` workspace configuration and baseline repo files.
- Added `scripts/verify_bootstrap_env.py` to make Python and `uv` mismatches explicit with deterministic next steps.
- Generated `uv.lock` and added unit coverage for the bootstrap verification script.
- Resolved the post-review verifier bug so workspace-root detection is anchored to the script location instead of the caller's current working directory.
- Verification currently fails intentionally on the local machine because the repo requires Python `3.11` and `uv 0.11.16`, while the local environment is Python `3.12.3` and `uv 0.9.26`.

### File List

- .editorconfig
- .github/workflows/.gitkeep
- .gitignore
- .python-version
- CHANGELOG.md
- CONTRIBUTING.md
- README.md
- packages/.gitkeep
- pyproject.toml
- scripts/__init__.py
- scripts/verify_bootstrap_env.py
- tests/test_verify_bootstrap_env.py
- uv.lock

## Change Log

- 2026-05-25: Created Story 1.1 implementation brief from Epic 1 planning artifacts.
- 2026-05-25: Implemented the workspace bootstrap baseline, verification script, docs, and tests; promoted story to review.
- 2026-05-25: Fixed the verifier root-path bug found during code review and re-ran the Story 1.1 checks.
