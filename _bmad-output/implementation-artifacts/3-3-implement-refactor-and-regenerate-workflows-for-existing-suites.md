# Story 3.3: Implement Refactor and Regenerate Workflows for Existing Suites

Status: done

## Story

As an Automation Engineer,
I want deterministic refactor and regenerate workflows for existing Robot Framework assets,
so that I can evolve suites and resources without losing clarity about what changed or whether the result still runs.

## Acceptance Criteria

1. **Given** an existing suite or resource needs structural changes  
   **When** the refactor workflow is implemented  
   **Then** the CLI exposes a stable path for refactor or regeneration tasks that reuses shared contracts, validation, and failure shaping  
   **And** the workflow reports the affected artifacts clearly enough for human review.

2. **Given** a refactor operation alters existing Robot Framework files  
   **When** validation and run verification complete  
   **Then** the workflow reports whether the change remains runnable and where manual follow-up is required  
   **And** the resulting contract shape is consistent with the generation and repair surfaces.

3. **Given** a refactor or regeneration attempt fails partially or introduces a risky change  
   **When** the workflow reports the result  
   **Then** the operator receives preventive or corrective hint guidance for the known failure pattern  
   **And** the output distinguishes between automatically recoverable issues and manual follow-up that must not be skipped.

## Tasks / Subtasks

- [x] Add shared refactor-result payload contracts plus schema export coverage in `rfmcp_core` so change summaries, runnable proof, and follow-up guidance stay machine-usable. (AC: 1, 2, 3)
- [x] Implement deterministic refactor/regenerate orchestration under `packages/rfmcp_cli/src/rfmcp_cli/workflows/refactor.py`, reusing generation/validation/repair building blocks where possible. (AC: 1, 2, 3)
- [x] Add stable CLI refactor and regenerate commands with human-readable and `--json` outputs through the existing presenter/serialization pattern. (AC: 1, 2, 3)
- [x] Report file diffs/change summaries, validation outcome, run-verification outcome, and manual follow-up requirements when the operation is risky or incomplete. (AC: 1, 2, 3)
- [x] Add tests covering contract shape, runnable proof, risky-change shaping, hint guidance, and CLI output contracts for existing suites/resources. (AC: 1, 2, 3)

## Dev Notes

- Keep Story 3.3 on the deterministic CLI side. Do not add MCP refactor helpers here.
- Reuse Story 3.2 generation and Story 2.3 repair-diagnostics/hinting rather than introducing a new failure surface.
- The architecture already reserves the likely locations for this slice:
  - `packages/rfmcp_cli/src/rfmcp_cli/workflows/refactor.py`
  - `packages/rfmcp_cli/src/rfmcp_cli/commands/refactor.py`
  - later skill definitions under `packages/rfmcp_skills/src/rfmcp_skills/definitions/refactor.py`
- The workflow should operate on existing `.robot` and `.resource` artifacts and preserve enough context for human review:
  - what was requested
  - what changed
  - whether the result validated
  - whether `robot` execution still passed
  - what deterministic correction path remains if it failed
- Keep contract shape aligned with Story 3.2 where possible so generation/refactor outputs stay consistent for later skill and E2E stories.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run --group dev python -m unittest tests.test_refactor_workflow -v`
- `python3 -m unittest discover -s tests -v`
- `uv run --group dev python scripts/export_json_schemas.py`
- `uv run --group dev python scripts/verify_schema_sync.py`
- `uv run --group dev rfmcp refactor <tmp>/suite.robot --rename-to Updated --add-step 'Log To Console    updated' --json`
- `timeout 300s copilot -p 'Review /tmp/story33_review_bundle_full.txt for Story 3.3...' --allow-all --no-ask-user --add-dir /tmp --model claude-sonnet-4.5 -s`
- `timeout 300s kilo run "Review the attached Story 3.3 implementation bundle..." --auto -m minimax/MiniMax-M2.7 --dir /home/many/workspace/rfmcp-reloaded --file=/tmp/story33_review_bundle.txt`

### Completion Notes List

- Added shared `RefactorResult` contracts and schema coverage for refactor/regenerate requests, diffs, runnable verification, manual follow-up, and correction-path output.
- Implemented deterministic `rfmcp refactor` and `rfmcp regenerate` workflows for suites and resources, reusing validation, execution proof, diagnostics, and hint-resolution building blocks from the generation and repair surfaces.
- Added stable CLI commands and presenters for human-readable and JSON output, including structured diffs, validation results, run-verification status, preventive guidance, corrective hints, and manual follow-up requirements.
- Closed the review loop with Copilot Sonnet after fixing trailing-newline preservation and adding regression coverage for artifacts that intentionally do not end with a newline.
- Verified the workflow with focused unit coverage, full-suite execution, schema-sync checks, and a real CLI refactor success path.

### File List

- _bmad-output/implementation-artifacts/3-3-implement-refactor-and-regenerate-workflows-for-existing-suites.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- assets/schemas/refactor-result.schema.json
- packages/rfmcp_cli/src/rfmcp_cli/commands/refactor.py
- packages/rfmcp_cli/src/rfmcp_cli/commands/regenerate.py
- packages/rfmcp_cli/src/rfmcp_cli/main.py
- packages/rfmcp_cli/src/rfmcp_cli/presenters/human.py
- packages/rfmcp_cli/src/rfmcp_cli/presenters/structured.py
- packages/rfmcp_cli/src/rfmcp_cli/workflows/refactor.py
- packages/rfmcp_core/src/rfmcp_core/contracts/__init__.py
- packages/rfmcp_core/src/rfmcp_core/contracts/results.py
- packages/rfmcp_core/src/rfmcp_core/models/__init__.py
- packages/rfmcp_core/src/rfmcp_core/models/payloads.py
- scripts/export_json_schemas.py
- tests/test_refactor_workflow.py

## Change Log

- 2026-05-26: Created Story 3.3 implementation brief from Epic 3 planning artifacts, refactor/regenerate acceptance criteria, and the current CLI/core workflow boundaries.
- 2026-05-26: Implemented refactor/regenerate contracts, CLI commands, deterministic workflow logic, schema exports, and Story 3.3 regression coverage.
- 2026-05-26: Closed Story 3.3 after MiniMax and Copilot Sonnet review passes plus final focused/full-suite verification.
