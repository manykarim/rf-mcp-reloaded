# Story 3.1: Implement Keyword Grounding and Suite Scaffolding Workflows

Status: done

## Story

As an Automation Engineer,
I want deterministic grounding and scaffolding commands,
so that new Robot Framework work starts from real library context and runnable file structures instead of plausible-looking guesses.

## Acceptance Criteria

1. **Given** a new suite or resource must be created  
   **When** the grounding and scaffolding workflows are implemented  
   **Then** the CLI can retrieve keyword or library grounding information and scaffold suite/resource files with stable command contracts  
   **And** the outputs are available in both readable and machine-usable forms.

2. **Given** an agent needs evidence before generating test steps  
   **When** it consumes the grounding results  
   **Then** the payload identifies the relevant libraries, keywords, and usage context clearly enough to reduce hallucinated test steps  
   **And** scaffolding produces deterministic starting files instead of ad hoc placeholders  
   **And** preventive hint guidance can be surfaced before generation when a known authoring pattern is error-prone.

## Tasks / Subtasks

- [x] Add shared grounding and scaffolding payload contracts plus schema export coverage in `rfmcp_core` so CLI results stay machine-usable and versioned. (AC: 1, 2)
- [x] Implement deterministic grounding and scaffolding workflow logic under `packages/rfmcp_cli/src/rfmcp_cli/workflows/` using existing provider metadata and Robot-aware file generation rules. (AC: 1, 2)
- [x] Add stable CLI commands for grounding and scaffolding, with human-readable and `--json` outputs wired through the existing presenter/serialization pattern. (AC: 1, 2)
- [x] Add deterministic template or file-generation behavior for suite/resource scaffolding that produces real starting files instead of placeholders and supports preventive guidance. (AC: 1, 2)
- [x] Add tests covering contract shapes, CLI output contracts, deterministic scaffold content, preventive guidance, and failure handling. (AC: 1, 2)

## Dev Notes

- Story 3.1 is the first Epic 3 authoring slice. Keep it strictly on the deterministic CLI side; do not add MCP tools for grounding, scaffolding, or generation helpers.
- Reuse the existing package boundaries from the architecture:
  - CLI command entrypoints live in `packages/rfmcp_cli/src/rfmcp_cli/commands/`
  - orchestration belongs in `packages/rfmcp_cli/src/rfmcp_cli/workflows/`
  - authoritative typed payloads and schema exports belong in `packages/rfmcp_core/src/rfmcp_core/models/` and `contracts/`
  - shared JSON Schema authority remains under `assets/schemas/`
- The architecture already reserved likely file names for this slice:
  - `rfmcp_cli.workflows.grounding`
  - generation-side command growth under `packages/rfmcp_cli/src/rfmcp_cli/commands/`
- Current CLI pattern to extend:
  - `packages/rfmcp_cli/src/rfmcp_cli/main.py`
  - `packages/rfmcp_cli/src/rfmcp_cli/commands/validate.py`
  - `packages/rfmcp_cli/src/rfmcp_cli/commands/repair_diagnostics.py`
  - `packages/rfmcp_cli/src/rfmcp_cli/presenters/human.py`
  - `packages/rfmcp_cli/src/rfmcp_cli/presenters/structured.py`
- Current grounding-adjacent sources already in repo:
  - provider metadata and library naming: `packages/rfmcp_provider_browser/src/rfmcp_provider_browser/metadata.py`
  - provider/plugin registry expectations: `packages/rfmcp_core/src/rfmcp_core/hints/plugin_manager.py`
  - curated Browser hints and recovery guidance: `assets/hints/libraries/robotframework.browser.yaml`
- Prefer deterministic local grounding over broad dynamic discovery. The payload should make library and keyword evidence explicit enough for later generation workflows to consume.
- Preventive hint guidance here should remain attributable. If a grounding or scaffold response includes warnings or next-step suggestions, they must be visibly distinct from authoritative observed facts.
- Carry forward Epic 2 lessons:
  - treat determinism claims as proof obligations
  - test package/runtime surfaces, not just source imports
  - separate example commands from executable rendered commands where relevant
  - keep host-level workflow descriptions honest about what the helper actually executes
- This story should leave Story 3.2 with concrete prerequisites:
  - a stable grounding result contract
  - deterministic suite/resource scaffold output
  - CLI commands that can be used manually when a host skill path fails

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv lock`
- `uv run --group dev python -m unittest tests.test_grounding_and_scaffolding -v`
- `uv run --group dev python -m unittest discover -s tests -v`
- `uv run --group dev python scripts/export_json_schemas.py`
- `uv run --group dev python scripts/verify_schema_sync.py`
- `uv build --package rfmcp-cli --wheel --out-dir /tmp/rfmcp-cli-dist --clear`
- `uv run --group dev rfmcp ground Log --json`
- `uv run --group dev rfmcp scaffold-suite <tmp>/demo.robot --library Browser --json`
- `uv run --group dev rfmcp scaffold-resource <tmp>/helpers.resource --json`
- `timeout 300s claude -p --model sonnet --dangerously-skip-permissions --tools '' < story31 bundle`
- `timeout 300s claude -p --model opus --dangerously-skip-permissions --tools '' < story31 bundle`
- `timeout 300s kilo run --auto -m minimax/MiniMax-M2.7 --dir /home/many/workspace/rfmcp-reloaded -f <story31 bundle> -- 'Review the attached Story 3.1 bundle...'`

### Completion Notes List

- Added shared `GroundingResult` and `ScaffoldResult` contracts, surfaced them through the model/contract facades, and exported authoritative JSON Schemas for both payloads.
- Implemented deterministic grounding and scaffolding workflow orchestration in `rfmcp_cli.workflows.grounding`, including provider-aware library cataloging, preventive hint guidance, suite/resource generation, overwrite handling, and structured failure envelopes.
- Added stable `ground`, `scaffold-suite`, and `scaffold-resource` CLI commands with human-readable and JSON presenters wired through the existing Typer and serializer patterns.
- Expanded validation to support `.resource` artifacts so resource scaffolding validates through the same structured contract path as suites.
- Closed Sonnet’s real findings by allowing resource-specific extensions, fixing retryability semantics, caching libdoc loads, and adding coverage for library filtering and forced overwrites.

### File List

- _bmad-output/implementation-artifacts/3-1-implement-keyword-grounding-and-suite-scaffolding-workflows.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- assets/schemas/grounding-result.schema.json
- assets/schemas/scaffold-result.schema.json
- packages/rfmcp_cli/pyproject.toml
- packages/rfmcp_cli/src/rfmcp_cli/commands/ground.py
- packages/rfmcp_cli/src/rfmcp_cli/commands/scaffold_resource.py
- packages/rfmcp_cli/src/rfmcp_cli/commands/scaffold_suite.py
- packages/rfmcp_cli/src/rfmcp_cli/main.py
- packages/rfmcp_cli/src/rfmcp_cli/presenters/human.py
- packages/rfmcp_cli/src/rfmcp_cli/presenters/structured.py
- packages/rfmcp_cli/src/rfmcp_cli/workflows/grounding.py
- packages/rfmcp_core/src/rfmcp_core/contracts/__init__.py
- packages/rfmcp_core/src/rfmcp_core/contracts/results.py
- packages/rfmcp_core/src/rfmcp_core/models/__init__.py
- packages/rfmcp_core/src/rfmcp_core/models/payloads.py
- packages/rfmcp_core/src/rfmcp_core/robot/validation.py
- scripts/export_json_schemas.py
- tests/test_grounding_and_scaffolding.py
- uv.lock

## Change Log

- 2026-05-26: Created Story 3.1 implementation brief from Epic 3 planning artifacts, PRD grounding/scaffolding requirements, architecture boundaries, and current CLI/core package structure.
- 2026-05-26: Implemented grounding and scaffolding contracts, CLI commands, deterministic workflow logic, schema exports, and Story 3.1 regression coverage.
- 2026-05-26: Closed Story 3.1 after Sonnet, Opus, and MiniMax review passes plus final full-suite, schema-sync, packaging, and CLI verification.
