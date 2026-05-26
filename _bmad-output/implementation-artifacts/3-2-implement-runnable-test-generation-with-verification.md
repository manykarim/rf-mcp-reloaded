# Story 3.2: Implement Runnable Test Generation With Verification

Status: done

## Story

As an Automation Engineer,
I want a generation workflow that ends in executable proof,
so that newly created Robot Framework tests are treated as trustworthy only after validation and `robot` execution.

## Acceptance Criteria

1. **Given** grounded inputs and scaffolded files exist  
   **When** the generation workflow is implemented  
   **Then** the CLI can generate runnable test artifacts, validate them structurally, and execute them through the documented run-verification path  
   **And** the workflow produces structured evidence showing whether the requested steps, tasks, and assertions were fulfilled.

2. **Given** the generated output fails validation or execution  
   **When** the workflow reports the result  
   **Then** the operator receives actionable failure details through the shared contract surface  
   **And** the workflow exposes the next deterministic correction path instead of stopping at a generic failure  
   **And** preventive or corrective hint guidance is included when recurring authoring mistakes are detected.

## Tasks / Subtasks

- [x] Add shared generation-result payload contracts plus schema export coverage in `rfmcp_core` so generated outputs and runnable proof stay machine-usable. (AC: 1, 2)
- [x] Implement deterministic generation orchestration under `packages/rfmcp_cli/src/rfmcp_cli/workflows/generation.py`, reusing Story 3.1 grounding/scaffolding and shared validation/run-verification behavior. (AC: 1, 2)
- [x] Add a stable CLI generation command with human-readable and `--json` outputs through the existing presenter/serialization pattern. (AC: 1, 2)
- [x] Capture structured evidence for requested steps, tasks, assertions, validation outcome, execution outcome, and next correction path when generation fails. (AC: 1, 2)
- [x] Add tests covering generation contract shape, runnable proof, failure shaping, hint guidance, and CLI output contracts. (AC: 1, 2)

## Dev Notes

- Keep Story 3.2 on the deterministic CLI side. Do not add MCP generation helpers here.
- Reuse Story 3.1 outputs rather than inventing a second grounding or scaffolding path.
- Maintain the architecture-owned boundaries:
  - generation command entrypoints live in `packages/rfmcp_cli/src/rfmcp_cli/commands/`
  - orchestration belongs in `packages/rfmcp_cli/src/rfmcp_cli/workflows/`
  - typed payloads and schema authority stay in `packages/rfmcp_core/src/rfmcp_core/models/`, `contracts/`, and `assets/schemas/`
- The architecture already reserved likely file names for this slice:
  - `rfmcp_cli.workflows.generation`
  - `rfmcp_cli.commands.generate`
  - later skill definitions under `rfmcp_skills/definitions/generation.py`
- FR-6 is stricter than “generated file exists”:
  - the workflow must prove runnable output via validation and `robot`
  - the structured result must show whether requested steps, tasks, and assertions were actually fulfilled
- Carry forward Story 3.1 and Epic 2 lessons:
  - deterministic claims need proof, not prose
  - error surfaces must remain attributable and machine-usable
  - hints for recurring authoring mistakes must stay visibly distinct from execution truth
  - package/runtime verification matters as much as source-level tests

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run --group dev python -m unittest tests.test_generation_workflow -v`
- `uv run --group dev python -m unittest discover -s tests -v`
- `uv run --group dev python scripts/export_json_schemas.py`
- `uv run --group dev python scripts/verify_schema_sync.py`
- `uv build --package rfmcp-cli --wheel --out-dir /tmp/rfmcp-cli-dist --clear`
- `uv run --group dev rfmcp generate <tmp>/generated.robot --task "verify greeting output" --step 'Set Test Variable    ${message}    hello' --assertion 'Should Be Equal As Strings    ${message}    hello' --json`
- `timeout 300s claude -p --model sonnet --dangerously-skip-permissions --tools '' < /tmp/story32_review_bundle.txt`
- `kilo run "Review the attached Story 3.2 bundle..." --auto -m minimax/MiniMax-M2.7 --dir /home/many/workspace/rfmcp-reloaded --file=/tmp/story32_review_bundle_full.txt`

### Completion Notes List

- Added a shared `GenerationResult` contract with execution proof, requested-input evidence, correction-path output, and optional repair diagnostics/hint-resolution attachments.
- Implemented deterministic `rfmcp generate` orchestration that reuses Story 3.1 scaffolding, validates the generated suite, executes `robot`, and produces structured success or failure evidence.
- Added review-driven hardening for missing or whitespace-only generation inputs, scaffold placeholder injection failures, non-contradictory evidence fulfillment, and scaffold mutation-flag invariants.
- Verified the workflow through unit tests, full-suite execution, schema-sync checks, CLI wheel build, and a real `rfmcp generate` success case with executable proof.

### File List

- _bmad-output/implementation-artifacts/3-2-implement-runnable-test-generation-with-verification.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- assets/schemas/generation-result.schema.json
- packages/rfmcp_cli/src/rfmcp_cli/commands/generate.py
- packages/rfmcp_cli/src/rfmcp_cli/main.py
- packages/rfmcp_cli/src/rfmcp_cli/presenters/human.py
- packages/rfmcp_cli/src/rfmcp_cli/presenters/structured.py
- packages/rfmcp_cli/src/rfmcp_cli/workflows/generation.py
- packages/rfmcp_core/src/rfmcp_core/contracts/__init__.py
- packages/rfmcp_core/src/rfmcp_core/contracts/results.py
- packages/rfmcp_core/src/rfmcp_core/models/__init__.py
- packages/rfmcp_core/src/rfmcp_core/models/payloads.py
- scripts/export_json_schemas.py
- tests/test_generation_workflow.py

## Change Log

- 2026-05-26: Created Story 3.2 implementation brief from Epic 3 planning artifacts, FR-6/FR-16 runnable-generation requirements, and the current CLI/core architecture boundaries.
- 2026-05-26: Implemented the generation command, contract-backed workflow, executable proof path, and Story 3.2 regression coverage.
- 2026-05-26: Completed Story 3.2 after Sonnet and MiniMax review loops plus final full-suite, schema-sync, packaging, and CLI verification.
