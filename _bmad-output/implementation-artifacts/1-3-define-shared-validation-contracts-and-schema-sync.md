# Story 1.3: Define Shared Validation Contracts and Schema Sync

Status: done

## Story

As a contributor,
I want one authoritative contract and schema-sync path for validation surfaces,
so that CLI, MCP, providers, and later host bundles consume stable payload shapes instead of drifting independently.

## Acceptance Criteria

1. **Given** the workspace packages exist  
   **When** the contract story is implemented  
   **Then** `rfmcp_core.models` defines the canonical contract shapes and `rfmcp_core.contracts` exposes the supported public façade  
   **And** the shared error envelope, hint payload schema, hint pack schema, and skill-manifest schema are explicitly defined for downstream surfaces  
   **And** generated JSON Schema artifacts are written to `assets/schemas/` from the model layer rather than maintained separately.

2. **Given** a contributor changes a contract model  
   **When** they run the schema export and verification scripts  
   **Then** schema artifacts regenerate deterministically and verification fails on drift  
   **And** the one-way contract evolution path is documented clearly enough that later stories do not redefine payloads locally.

## Tasks / Subtasks

- [x] Define canonical contract models in `rfmcp_core.models`. (AC: 1)
- [x] Expose the public contract façade in `rfmcp_core.contracts`. (AC: 1)
- [x] Add deterministic schema export and drift verification scripts. (AC: 1, 2)
- [x] Generate and commit `assets/schemas/` artifacts from the model layer. (AC: 1, 2)
- [x] Document contract usage and one-way evolution rules. (AC: 2)
- [x] Add tests for model exports and schema drift detection. (AC: 2)

## Dev Notes

- Keep the canonical shape definitions in `rfmcp_core.models`; `rfmcp_core.contracts` is the public façade and must not introduce competing field definitions.
- The explicit schemas required by this story are: shared error envelope, hint payload, hint pack, and skill manifest. A validation result shape is also useful for the upcoming CLI story and can be exported from the same authority.
- JSON Schema is committed under `assets/schemas/` and generated from the model layer only.
- Later stories will rely on these exact payloads for CLI `--json` output and diagnostics, so avoid ad hoc local data shapes.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv lock`
- `uv run --group dev python scripts/export_json_schemas.py`
- `uv run --group dev python scripts/verify_schema_sync.py`
- `uv run --group dev python -m unittest discover -s tests -v`

### Completion Notes List

- Added canonical contract models to `rfmcp_core.models` and the public façade to `rfmcp_core.contracts`.
- Added deterministic schema export and drift verification scripts for `assets/schemas/`.
- Generated committed schemas for the error envelope, hint payload, hint pack, skill manifest, and validation result.
- Documented contract authority and one-way contract evolution for contributors.
- Fixed the workspace metadata and root dev dependency setup needed for `uv run` schema workflows.

### File List

- README.md
- assets/schemas/error-envelope.schema.json
- assets/schemas/hint-pack.schema.json
- assets/schemas/hint-payload.schema.json
- assets/schemas/skill-manifest.schema.json
- assets/schemas/validation-result.schema.json
- docs/contract-evolution.md
- docs/contracts.md
- packages/rfmcp_cli/pyproject.toml
- packages/rfmcp_core/pyproject.toml
- packages/rfmcp_core/src/rfmcp_core/contracts/__init__.py
- packages/rfmcp_core/src/rfmcp_core/contracts/errors.py
- packages/rfmcp_core/src/rfmcp_core/contracts/hints.py
- packages/rfmcp_core/src/rfmcp_core/contracts/provenance.py
- packages/rfmcp_core/src/rfmcp_core/contracts/results.py
- packages/rfmcp_core/src/rfmcp_core/contracts/serialize.py
- packages/rfmcp_core/src/rfmcp_core/models/__init__.py
- packages/rfmcp_core/src/rfmcp_core/models/hint_pack.py
- packages/rfmcp_core/src/rfmcp_core/models/payloads.py
- packages/rfmcp_core/src/rfmcp_core/models/policy.py
- packages/rfmcp_mcp/pyproject.toml
- pyproject.toml
- scripts/export_json_schemas.py
- scripts/verify_schema_sync.py
- tests/test_schema_sync.py
- uv.lock

## Change Log

- 2026-05-25: Created Story 1.3 implementation brief from Epic 1 planning artifacts.
- 2026-05-25: Implemented shared contracts, schema sync scripts, committed schemas, and contract-evolution docs; promoted story to review.
- 2026-05-25: Completed Story 1.3 after wiring workspace package sources and re-running schema export, sync, and test checks.
